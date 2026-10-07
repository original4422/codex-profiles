#!/usr/bin/env python3
"""Account-scoped launchers. No authentication token reading or copying."""

import argparse
import json
import os
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import unquote, urlparse


class Profile(TypedDict, total=False):
    """Required state paths plus optional desktop application and launcher paths."""

    name: str
    home: str
    desktop_data: str
    app: str
    launcher: str


class Registry(TypedDict, total=False):
    version: int
    profiles: dict[str, Profile]
    applications_dir: str
    bin_dir: str


def validate_identifier(identifier: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", identifier):
        raise ValueError(
            "Profile ID must start with a lowercase letter and contain 1–32 letters, digits or hyphens."
        )


def new_profile(
    root: Path,
    identifier: str,
    *,
    name: str | None = None,
    home: str | None = None,
    desktop_data: str | None = None,
    app: str | None = None,
) -> Profile:
    """Create account-scoped paths; there is no special first or second account."""
    validate_identifier(identifier)
    profile: Profile = {
        "name": name if name is not None else f"Codex {identifier}",
        "home": absolute(home or root / "accounts" / identifier),
        "desktop_data": absolute(desktop_data or root / "desktop" / identifier),
    }
    if app:
        profile["app"] = absolute(app)
    return profile


def state_root() -> Path:
    return Path.home() / "Library/Application Support/Codex Profiles"


def clean_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    return {
        k: v
        for k, v in (os.environ if source is None else source).items()
        if not k.startswith("CODEX_")
        and k not in {"OPENAI_API_KEY", "OPENAI_BASE_URL", "ELECTRON_RUN_AS_NODE"}
    }


def absolute(value: str | Path) -> str:
    return str(Path(value).expanduser().absolute())


def overlaps(left: str | Path, right: str | Path) -> bool:
    a, b = Path(left).resolve(), Path(right).resolve()
    return a == b or a in b.parents or b in a.parents


def validate_profile(identifier: str, profile: Profile, others: Mapping[str, Profile]) -> None:
    validate_identifier(identifier)
    name = profile.get("name", "")
    if (
        not isinstance(name, str)
        or not name.strip()
        or any(ord(char) < 32 or char in "/\\" for char in name)
    ):
        raise ValueError(
            "Choose a nonempty display name without path separators or control characters."
        )
    for key in ("home", "desktop_data"):
        if not isinstance(profile.get(key), str) or not profile[key]:
            raise ValueError(f"Profile {identifier} requires a {key} path.")
    paths = [profile["home"], profile["desktop_data"]]
    for path in paths:
        if not Path(path).is_absolute() or Path(path).is_symlink():
            raise ValueError("Profile paths must be absolute, non-symlink directories.")
        if Path(path).resolve() in [Path("/"), Path.home().resolve()]:
            raise ValueError("A profile cannot use the filesystem root or your home directory.")
    if overlaps(*paths):
        raise ValueError("Codex home and desktop data must be separate directories.")
    for other_id, other in others.items():
        if other_id == identifier:
            continue
        if any(overlaps(x, other[y]) for x in paths for y in ["home", "desktop_data"]):
            raise ValueError(f"Profile directories overlap with account {other_id}.")


def load_registry(root: Path) -> Registry:
    path = root / "profiles.json"
    if not path.exists():
        raise ValueError("No profiles installed. Run: python3 install.py --profile work")
    data = json.loads(path.read_text())
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("profiles"), dict)
    ):
        raise ValueError("Invalid profiles.json: expected version 1 and a profiles object.")
    for identifier, profile in data["profiles"].items():
        validate_profile(identifier, profile, data["profiles"])
    return data


def prepare_profile(profile: Profile) -> None:
    # Existing account files are never rewritten, and auth.json is never read.
    for key in ["home", "desktop_data"]:
        directory = Path(profile[key])
        if directory.is_symlink():
            raise ValueError(f"Refusing symlinked profile directory: {directory}")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = Path(profile["home"]) / "config.toml"
    try:
        fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w") as output:
        output.write('cli_auth_credentials_store = "file"\nforced_login_method = "chatgpt"\n')


def find_app(profile: Profile) -> Path:
    candidates = (
        [Path(profile["app"])]
        if profile.get("app")
        else [
            Path("/Applications/ChatGPT.app"),
            Path.home() / "Applications/ChatGPT.app",
            Path("/Applications/Codex.app"),
            Path.home() / "Applications/Codex.app",
        ]
    )
    for app in candidates:
        info_path = app / "Contents/Info.plist"
        if not info_path.is_file():
            continue
        info = plistlib.loads(info_path.read_bytes())
        if info.get("CFBundleIdentifier") != "com.openai.codex":
            continue
        executable = info.get("CFBundleExecutable")
        if executable and os.access(app / "Contents/MacOS" / executable, os.X_OK):
            return app
    raise ValueError("Official ChatGPT/Codex app not found. Set the profile app path with --app.")


def desktop_invocation(
    profile: Profile, app: Path, source: Mapping[str, str] | None = None
) -> tuple[list[str], dict[str, str]]:
    env = clean_environment(source)
    env["CODEX_HOME"] = profile["home"]
    env["CODEX_ELECTRON_USER_DATA_PATH"] = profile["desktop_data"]
    return [
        "/usr/bin/open",
        "-n",
        "--env",
        "CODEX_HOME=" + profile["home"],
        "--env",
        "CODEX_ELECTRON_USER_DATA_PATH=" + profile["desktop_data"],
        str(app),
        "--args",
        "--user-data-dir=" + profile["desktop_data"],
    ], env


def find_profile_pid(profile: Profile, app: Path) -> str | None:
    """Match an existing process by the data files it actually has open, not app name."""
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    executable = str(app / "Contents/MacOS" / info["CFBundleExecutable"])
    prefix = str(Path(profile["desktop_data"]).resolve()) + "/"
    rows = subprocess.check_output(["/bin/ps", "-axo", "pid=,comm="], text=True).splitlines()
    for row in rows:
        parts = row.strip().split(None, 1)
        if len(parts) != 2 or parts[1] != executable:
            continue
        opened = subprocess.run(
            ["/usr/sbin/lsof", "-p", parts[0], "-Fn"], capture_output=True, text=True, timeout=10
        ).stdout.splitlines()
        if any(line.startswith("n" + prefix) for line in opened):
            return parts[0]
    return None


def launch_desktop(root: Path, profile: Profile) -> None:
    app = find_app(profile)
    pid = find_profile_pid(profile, app)
    if pid:
        # Especially important for the original/default profile: its existing
        # macOS process may not hold Electron's explicit-profile singleton lock.
        helper = root / "engine/bin/FocusApp"
        subprocess.run([str(helper), pid], check=True, env=clean_environment())
        return
    args, env = desktop_invocation(profile, app)
    subprocess.run(args, env=env, check=True)


def run_cli(profile: Profile, arguments: list[str]) -> None:
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("Codex CLI not found on PATH. Install the standalone Codex CLI.")
    env = clean_environment()
    env["CODEX_HOME"] = profile["home"]
    os.execvpe(executable, [executable, *arguments], env)


def dock_tile(app: Path, name: str, bundle_id: str) -> dict:
    return {
        "tile-type": "file-tile",
        "tile-data": {
            "file-data": {"_CFURLString": app.as_uri() + "/", "_CFURLStringType": 15},
            "file-label": name,
            "bundle-identifier": bundle_id,
            "file-type": 41,
        },
    }


def tile_path(tile: dict) -> str:
    return unquote(
        urlparse(tile.get("tile-data", {}).get("file-data", {}).get("_CFURLString", "")).path
    ).rstrip("/")


def pin_tiles(tiles: list[dict], app: Path, name: str, bundle_id: str) -> list[dict]:
    """Keep one original-app pin, replace its duplicates with the account pin."""
    result, seen_official, pinned = [], set(), False
    target = str(app).rstrip("/")
    for tile in tiles:
        path = tile_path(tile)
        if path == target:
            if not pinned:
                result.append(tile)
                pinned = True
            continue
        official = tile.get("tile-data", {}).get("bundle-identifier") == "com.openai.codex"
        if official and path in seen_official:
            if not pinned:
                result.append(dock_tile(app, name, bundle_id))
                pinned = True
            continue
        if official:
            seen_official.add(path)
        result.append(tile)
    if not pinned:
        result.append(dock_tile(app, name, bundle_id))
    return result


def pin_dock(root: Path, profile: Profile) -> None:
    app = Path(profile["launcher"])
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    before = subprocess.check_output(["/usr/bin/defaults", "export", "com.apple.dock", "-"])
    data = plistlib.loads(before)
    old = data.get("persistent-apps", [])
    new = pin_tiles(old, app, profile["name"], info["CFBundleIdentifier"])
    if old == new:
        print("Dock already points to the account launcher.")
        return
    backups = root / "backups"
    backups.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = backups / ("dock-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".plist")
    backup.write_bytes(before)
    current = plistlib.loads(
        subprocess.check_output(["/usr/bin/defaults", "export", "com.apple.dock", "-"])
    )
    if current.get("persistent-apps", []) != old:
        raise ValueError("Dock changed while preparing the update; retry.")
    # Write only persistent-apps, preserving all other Dock preferences.
    subprocess.run(
        [
            "/usr/bin/defaults",
            "write",
            "com.apple.dock",
            "persistent-apps",
            "-array",
            *[plistlib.dumps(t).decode() for t in new],
        ],
        check=True,
    )
    subprocess.run(
        ["/usr/bin/killall", "-u", str(os.getuid()), "Dock"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Pinned {app.name}; previous Dock preferences saved to {backup}")


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(
        description="Open an account in the official desktop app or Codex CLI."
    )
    parser.add_argument("--root", type=Path, default=state_root(), help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    for command in ["desktop", "status", "doctor", "terminal", "pin"]:
        commands.add_parser(command).add_argument("profile")
    cli = commands.add_parser("cli")
    cli.add_argument("profile")
    cli.add_argument("arguments", nargs=argparse.REMAINDER)
    add = commands.add_parser("add")
    add.add_argument("profile")
    add.add_argument("--name")
    add.add_argument("--pin", action="store_true", help="Pin the new launcher to the Dock.")
    add.add_argument("--dry-run", action="store_true", help="Show the plan without writing files.")
    add.add_argument("--home")
    add.add_argument("--desktop-data")
    add.add_argument("--app")
    options = parser.parse_args()
    root = options.root.expanduser().absolute()
    data = load_registry(root)
    if options.command == "list":
        for identifier, profile in data["profiles"].items():
            print(
                f"{identifier}: {profile['name']}\n  CODEX_HOME={profile['home']}\n  desktop={profile['desktop_data']}"
            )
        return
    if options.command == "add":
        if options.profile in data["profiles"]:
            raise ValueError("That account profile already exists.")
        validate_identifier(options.profile)
        command = [
            sys.executable,
            "-B",  # Installed previews must not create bytecode caches.
            str(root / "engine/install.py"),
            "--root",
            str(root),
            "--profile",
            options.profile,
            "--new",
        ]
        for option in ("name", "home", "desktop_data", "app"):
            value = getattr(options, option)
            if value:
                command.extend(["--" + option.replace("_", "-"), value])
        if options.pin:
            command.append("--pin")
        if options.dry_run:
            command.append("--dry-run")
        subprocess.run(command, check=True)
        return
    if options.profile not in data["profiles"]:
        raise ValueError("Unknown account profile; run codex-profile list.")
    profile = data["profiles"][options.profile]
    if options.command == "doctor":
        app = find_app(profile)
        print(
            f"Profile: {options.profile}\nCODEX_HOME: {profile['home']}\nDesktop data: {profile['desktop_data']}\nApp: {app}"
        )
        print("File-based login cache present:", (Path(profile["home"]) / "auth.json").exists())
        launcher = profile.get("launcher")
        if launcher:
            print("Launcher:", launcher)
            dock = plistlib.loads(
                subprocess.check_output(["/usr/bin/defaults", "export", "com.apple.dock", "-"])
            )
            print(
                "Dock points to account launcher:",
                any(tile_path(t) == launcher for t in dock.get("persistent-apps", [])),
            )
        return
    if options.command == "pin":
        if "launcher" not in profile:
            raise ValueError(
                "This profile has no launcher. Build one with install.py --profile "
                + options.profile
            )
        pin_dock(root, profile)
        return
    prepare_profile(profile)
    if options.command == "desktop":
        launch_desktop(root, profile)
    elif options.command == "terminal":
        directory = root / "terminals"
        directory.mkdir(mode=0o700, exist_ok=True)
        script = directory / (options.profile + ".command")
        script.write_text(
            '#!/bin/bash\ncd "$HOME"\nexec '
            + shlex.join(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--root",
                    str(root),
                    "cli",
                    options.profile,
                ]
            )
            + "\n"
        )
        script.chmod(0o700)
        subprocess.run(["/usr/bin/open", "-a", "Terminal", str(script)], check=True)
    else:
        run_cli(profile, ["login", "status"] if options.command == "status" else options.arguments)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"codex-profile: {error}", file=sys.stderr)
        sys.exit(1)
