#!/usr/bin/env python3
"""Build and install one named account profile without touching login credentials."""

import argparse
import fcntl
import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from src.profiles import (
    Profile,
    Registry,
    absolute,
    find_app,
    load_registry,
    new_profile,
    overlaps,
    pin_dock,
    state_root,
    validate_profile,
)

SOURCE = Path(__file__).resolve().parent
VERSION = "0.3.0"
NATIVE_SOURCES = ("AccountLauncher", "MakeIcon", "FocusApp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", required=True, help="Named account, for example personal or work."
    )
    parser.add_argument("--name", help="Display name; defaults to Codex <profile>.")
    parser.add_argument("--home", help="Use an existing Codex account directory.")
    parser.add_argument("--desktop-data", help="Use an existing desktop data directory.")
    parser.add_argument("--app", help="Path to the official ChatGPT/Codex app.")
    parser.add_argument("--pin", action="store_true", help="Back up and update Dock pins.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show the plan without writing files."
    )
    parser.add_argument("--root", type=Path, default=state_root(), help="Manager state directory.")
    parser.add_argument("--applications-dir", type=Path, help="Launcher destination directory.")
    parser.add_argument("--bin-dir", type=Path, help="Command destination directory.")
    parser.add_argument("--new", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def plan_install(args: argparse.Namespace) -> tuple[Registry, Profile, Path, Path]:
    """Validate configuration before compilation or any mutation of the installation."""
    root = args.root
    registry = (
        load_registry(root) if (root / "profiles.json").exists() else {"version": 1, "profiles": {}}
    )
    profiles = registry["profiles"]
    if args.profile in profiles:
        if args.new:
            raise ValueError(f"Profile {args.profile!r} already exists.")
        profile = profiles[args.profile]
        for key in ("home", "desktop_data"):
            value = getattr(args, key)
            if value and Path(absolute(value)).resolve() != Path(profile[key]).resolve():
                raise ValueError(
                    f"Account {args.profile} already uses {profile[key]}; choose a new ID for another directory."
                )
        if args.name is not None:
            profile["name"] = args.name
        if args.app is not None:
            profile["app"] = absolute(args.app)
    else:
        profile = new_profile(
            root,
            args.profile,
            name=args.name,
            home=args.home,
            desktop_data=args.desktop_data,
            app=args.app,
        )
        profiles[args.profile] = profile
    for identifier, candidate in profiles.items():
        validate_profile(identifier, candidate, profiles)
    applications = (
        Path(
            args.applications_dir
            or registry.get("applications_dir")
            or Path.home() / "Applications"
        )
        .expanduser()
        .absolute()
    )
    binaries = (
        Path(args.bin_dir or registry.get("bin_dir") or Path.home() / ".local/bin")
        .expanduser()
        .absolute()
    )
    # IDs define filenames; display names can be equal without colliding on disk.
    app = Path(profile.get("launcher", applications / f"Codex {args.profile}.app"))
    if args.applications_dir and app.parent != applications:
        raise ValueError("An existing launcher cannot be relocated during an update.")
    command = binaries / "codex-profile"
    if app.is_symlink() or command.is_symlink() or (root / "engine").is_symlink():
        raise ValueError("Installation targets cannot be symbolic links.")
    if app.exists():
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        if info.get("CFBundleIdentifier") != f"local.codex.profiles.{args.profile}":
            raise ValueError(f"Refusing to replace an unrelated application: {app}")
        processes = subprocess.check_output(["/bin/ps", "-axo", "comm="], text=True).splitlines()
        if str(app / "Contents/MacOS/AccountLauncher") in [line.strip() for line in processes]:
            raise ValueError(
                "Quit this account's launcher before updating it; the official app can keep running."
            )
    if command.exists() and "# Managed by Codex Profiles\n" not in command.read_text():
        raise ValueError(f"Refusing to replace an unrelated command: {command}")
    for account in profiles.values():
        for key in ("home", "desktop_data"):
            path = Path(account[key]).resolve()
            reserved = (root / "engine", root / "backups", root / "terminals", app, command)
            if any(overlaps(path, target) for target in reserved):
                raise ValueError("Account data must not overlap the manager's installation files.")
    registry["applications_dir"] = str(applications)
    registry["bin_dir"] = str(binaries)
    return registry, profile, app, command


def build_icon(compiler: Path, badge: str, destination: Path, work: Path) -> None:
    full = work / "icon.png"
    subprocess.run([str(compiler), str(full), badge], check=True)
    iconset = work / "Account.iconset"
    iconset.mkdir()
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f"icon_{size}x{size}" + ("@2x" if scale == 2 else "") + ".png"
            subprocess.run(
                [
                    "/usr/bin/sips",
                    "-z",
                    str(size * scale),
                    str(size * scale),
                    str(full),
                    "--out",
                    str(iconset / name),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
    subprocess.run(
        ["/usr/bin/iconutil", "-c", "icns", str(iconset), "-o", str(destination)], check=True
    )


def build_artifacts(
    work: Path, root: Path, registry: Registry, profile: Profile, identifier: str, app: Path
) -> tuple[Path, Path, Path, Path]:
    engine = work / "engine"
    (engine / "src").mkdir(parents=True)
    (engine / "bin").mkdir()
    for name in ("__init__.py", "profiles.py", *(f"{name}.swift" for name in NATIVE_SOURCES)):
        shutil.copy2(SOURCE / "src" / name, engine / "src" / name)
    shutil.copy2(SOURCE / "install.py", engine / "install.py")
    for name in NATIVE_SOURCES:
        subprocess.run(
            [
                "xcrun",
                "swiftc",
                "-O",
                "-framework",
                "AppKit",
                str(SOURCE / "src" / f"{name}.swift"),
                "-o",
                str(engine / "bin" / name),
            ],
            check=True,
        )
    staging = work / "launcher.app"
    contents = staging / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Resources").mkdir()
    shutil.copy2(engine / "bin/AccountLauncher", contents / "MacOS/AccountLauncher")
    badge = str(list(registry["profiles"]).index(identifier) + 1)
    build_icon(engine / "bin/MakeIcon", badge, contents / "Resources/Account.icns", work)
    # A venv may disappear after development; launchers should use a durable interpreter.
    python = str(Path(sys._base_executable).absolute())
    info = {
        "CFBundleIdentifier": f"local.codex.profiles.{identifier}",
        "CFBundleName": profile["name"],
        "CFBundleDisplayName": profile["name"],
        "CFBundleExecutable": "AccountLauncher",
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "3",
        "CFBundleShortVersionString": VERSION,
        "CFBundleIconFile": "Account.icns",
        "NSHighResolutionCapable": True,
        "AccountProfile": identifier,
        "AccountPython": python,
        "AccountEngine": str(root / "engine/src/profiles.py"),
        "AccountRoot": str(root),
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(staging)], check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(staging)], check=True)
    command = work / "codex-profile"
    command.write_text(
        "#!/bin/bash\n# Managed by Codex Profiles\nexec "
        + shlex.join([python, str(root / "engine/src/profiles.py"), "--root", str(root)])
        + ' "$@"\n'
    )
    command.chmod(0o755)
    profile["launcher"] = str(app)
    config = work / "profiles.json"
    config.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    return engine, staging, command, config


def replace_artifacts(artifacts: list[tuple[Path, Path]], backups: Path) -> None:
    """Restore this installation if any replacement fails; account data is never a target."""
    backups.mkdir(parents=True, mode=0o700)
    completed: list[tuple[Path, Path]] = []
    try:
        for index, (source, target) in enumerate(artifacts):
            target.parent.mkdir(parents=True, exist_ok=True)
            previous = backups / f"{index}-{target.name}"
            if target.exists():
                shutil.move(str(target), previous)
            completed.append((target, previous))
            shutil.move(str(source), target)
    except (OSError, shutil.Error):
        for target, previous in reversed(completed):
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            if previous.exists():
                shutil.move(str(previous), target)
        raise


def preflight() -> None:
    if sys.platform != "darwin":
        raise ValueError("Desktop launchers require macOS.")
    if sys.version_info < (3, 10):  # noqa: UP036 -- validate direct source installs
        raise ValueError("Python 3.10 or later is required.")
    for tool in ("xcrun", "sips", "iconutil", "codesign"):
        if not shutil.which(tool):
            raise ValueError(f"Missing {tool}; install Xcode Command Line Tools first.")
    subprocess.run(["xcrun", "--find", "swiftc"], check=True, stdout=subprocess.DEVNULL)


def main() -> None:
    os.umask(0o077)
    args = parse_args()
    args.root = args.root.expanduser().absolute()
    if args.root.is_symlink():
        raise ValueError("The manager state directory cannot be a symbolic link.")
    preflight()
    registry, profile, app, command = plan_install(args)
    official = find_app(profile)
    print(
        f"Profile: {args.profile}\nOfficial app: {official}\nAccount home: {profile['home']}\nDesktop data: {profile['desktop_data']}\nLauncher: {app}\nCommand: {command}",
        flush=True,
    )
    if args.dry_run:
        print("Dry run: no files or Dock settings changed.")
        return
    args.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.root / ".install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # Re-read after acquiring the lock so concurrent additions cannot lose accounts.
        registry, profile, app, command = plan_install(args)
        with tempfile.TemporaryDirectory(prefix="codex-profiles-build-") as temp:
            artifacts = build_artifacts(Path(temp), args.root, registry, profile, args.profile, app)
            destinations = (args.root / "engine", app, command, args.root / "profiles.json")
            backup = args.root / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            replace_artifacts(list(zip(artifacts, destinations, strict=True)), backup)
    if args.pin:
        pin_dock(args.root, profile)
    print(
        f"Installed {args.profile}. Open {app} or run:\n  {command} cli {args.profile}\n  {command} add another-account --pin"
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        sys.exit(1)
