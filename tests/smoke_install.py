"""Build four real launcher bundles in a temporary sandbox; never launch Codex."""

import json
import os
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="codex-profiles-smoke-") as temporary:
        root = Path(temporary)
        fake = root / "Fixture.app/Contents"
        (fake / "MacOS").mkdir(parents=True)
        (fake / "Info.plist").write_bytes(
            plistlib.dumps(
                {"CFBundleIdentifier": "com.openai.codex", "CFBundleExecutable": "Fixture"}
            )
        )
        desktop = fake / "MacOS/Fixture"
        desktop.write_text("#!/bin/sh\nexit 0\n")
        desktop.chmod(0o700)
        cli = root / "cli-bin/codex"
        cli.parent.mkdir()
        cli.write_text('#!/bin/sh\nprintf "%s\\n" "$CODEX_HOME"\n')
        cli.chmod(0o700)
        state = root / "state"
        base = [
            sys.executable,
            str(REPO / "install.py"),
            "--root",
            str(state),
            "--applications-dir",
            str(root / "apps"),
            "--bin-dir",
            str(root / "bin"),
            "--app",
            str(fake.parent),
        ]
        for identifier in ("personal", "work", "research"):
            subprocess.run(
                [*base, "--profile", identifier, "--name", "Same display name"], check=True
            )
        manager = root / "bin/codex-profile"
        subprocess.run([str(manager), "add", "client", "--app", str(fake.parent)], check=True)
        registry = json.loads((state / "profiles.json").read_text())
        assert list(registry["profiles"]) == ["personal", "work", "research", "client"]
        for identifier, profile in registry["profiles"].items():
            app = Path(profile["launcher"])
            info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
            assert info["AccountProfile"] == identifier
            assert app.name == f"Codex {identifier}.app"
            assert info["CFBundleIdentifier"] == f"local.codex.profiles.{identifier}"
            subprocess.run(["codesign", "--verify", "--strict", str(app)], check=True)
            # Use a standalone fixture CLI, separate from the desktop bundle.
            result = subprocess.check_output(
                [str(manager), "cli", identifier],
                env={**os.environ, "PATH": str(cli.parent) + ":/usr/bin:/bin"},
                text=True,
            )
            assert result.strip() == profile["home"]
        # Real read-only planning must not create a fifth registered profile.
        subprocess.run([*base, "--profile", "preview", "--dry-run"], check=True)
        assert len(json.loads((state / "profiles.json").read_text())["profiles"]) == 4
        # Preview through the installed manager must leave the entire installation unchanged.
        before = {
            path.relative_to(root): (
                path.stat().st_mode,
                path.read_bytes() if path.is_file() else None,
            )
            for path in root.rglob("*")
        }
        preview = subprocess.check_output(
            [str(manager), "add", "preview", "--app", str(fake.parent), "--dry-run"], text=True
        )
        assert "Profile: preview" in preview
        assert "Dry run: no files or Dock settings changed." in preview
        after = {
            path.relative_to(root): (
                path.stat().st_mode,
                path.read_bytes() if path.is_file() else None,
            )
            for path in root.rglob("*")
        }
        assert before == after
        print(
            "PASS: four real launcher builds, add/preview workflows, signatures and isolated CLI routing."
        )


if __name__ == "__main__":
    main()
