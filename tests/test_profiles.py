import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("profiles", ROOT / "src/profiles.py")
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


class ProfileTests(unittest.TestCase):
    def test_dock_repairs_duplicate_official_icons_and_is_idempotent(self):
        original = profiles.dock_tile(
            Path("/Applications/ChatGPT.app"), "ChatGPT", "com.openai.codex"
        )
        unrelated = profiles.dock_tile(Path("/Applications/Notes.app"), "Notes", "com.apple.Notes")
        launcher = Path("/Users/test/Applications/Codex 第二账号.app")
        result = profiles.pin_tiles(
            [original, unrelated, original], launcher, "B", "local.codex.profiles.b"
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], original)
        self.assertEqual(result[1], unrelated)
        self.assertEqual(
            result[2]["tile-data"]["file-data"]["_CFURLString"], launcher.as_uri() + "/"
        )
        self.assertEqual(
            profiles.pin_tiles(result, launcher, "B", "local.codex.profiles.b"), result
        )

    def test_launch_and_relaunch_use_identical_isolation(self):
        profile = {
            "name": "Test",
            "home": "/Users/test/account B",
            "desktop_data": "/Users/test/ui B",
        }
        args, env = profiles.desktop_invocation(
            profile,
            Path("/Applications/ChatGPT.app"),
            {
                "HOME": "/Users/test",
                "PATH": "/usr/bin",
                "CODEX_HOME": "/wrong",
                "CODEX_THREAD_ID": "parent",
                "OPENAI_API_KEY": "never-forward",
            },
        )
        self.assertIn("CODEX_HOME=/Users/test/account B", args)
        self.assertIn("CODEX_ELECTRON_USER_DATA_PATH=/Users/test/ui B", args)
        self.assertIn("--user-data-dir=/Users/test/ui B", args)
        self.assertNotIn("CODEX_THREAD_ID", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertEqual(env["HOME"], "/Users/test")
        self.assertEqual(
            profiles.desktop_invocation(profile, Path("/Applications/ChatGPT.app"), env),
            (args, env),
        )

    def test_profiles_cannot_share_or_nest_state_directories(self):
        a = {"name": "Test", "home": "/tmp/account-a", "desktop_data": "/tmp/ui-a"}
        for home in ["/tmp/account-a", "/tmp/account-a/nested", "/tmp"]:
            with self.assertRaises(ValueError):
                profiles.validate_profile(
                    "b", {"name": "Test", "home": home, "desktop_data": "/elsewhere/ui-b"}, {"a": a}
                )

    def test_existing_credentials_and_configuration_are_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            home, ui = Path(temp) / "account", Path(temp) / "ui"
            home.mkdir()
            (home / "auth.json").write_text("private fixture")
            (home / "config.toml").write_text("custom config")
            profiles.prepare_profile({"name": "Test", "home": str(home), "desktop_data": str(ui)})
            self.assertEqual((home / "auth.json").read_text(), "private fixture")
            self.assertEqual((home / "config.toml").read_text(), "custom config")

    def test_symlink_profiles_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / "target").mkdir()
            (base / "alias").symlink_to(base / "target")
            with self.assertRaises(ValueError):
                profiles.prepare_profile(
                    {"name": "Test", "home": str(base / "alias"), "desktop_data": str(base / "ui")}
                )

    def test_cli_routes_by_account_preserving_cwd_and_arguments(self):
        profile = {"name": "Test", "home": "/tmp/account-b", "desktop_data": "/tmp/ui-b"}
        with (
            patch.object(profiles.shutil, "which", return_value="/bin/codex"),
            patch.object(profiles.os, "execvpe") as execute,
        ):
            before = os.getcwd()
            profiles.run_cli(profile, ["exec", "literal $HOME; command"])
            binary, args, env = execute.call_args.args
            self.assertEqual(binary, "/bin/codex")
            self.assertEqual(args, ["/bin/codex", "exec", "literal $HOME; command"])
            self.assertEqual(env["CODEX_HOME"], "/tmp/account-b")
            self.assertEqual(os.getcwd(), before)

    def test_existing_account_is_focused_by_pid_without_new_desktop(self):
        with (
            patch.object(profiles, "find_app", return_value=Path("/Applications/ChatGPT.app")),
            patch.object(profiles, "find_profile_pid", return_value="42"),
            patch.object(profiles.subprocess, "run") as run,
        ):
            profiles.launch_desktop(
                Path("/private/state"), {"name": "Test", "home": "/account", "desktop_data": "/ui"}
            )
            self.assertEqual(run.call_args.args[0], ["/private/state/engine/bin/FocusApp", "42"])

    def test_quit_account_is_restarted_with_its_own_directories(self):
        profile = {"name": "Test", "home": "/account-b", "desktop_data": "/ui-b"}
        with (
            patch.object(profiles, "find_app", return_value=Path("/Applications/ChatGPT.app")),
            patch.object(profiles, "find_profile_pid", return_value=None),
            patch.object(profiles.subprocess, "run") as run,
        ):
            profiles.launch_desktop(Path("/private/state"), profile)
            self.assertIn("CODEX_HOME=/account-b", run.call_args.args[0])
            self.assertIn("CODEX_ELECTRON_USER_DATA_PATH=/ui-b", run.call_args.args[0])

    def test_real_cli_entry_point_isolates_two_profiles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "codex"
            fake.write_text(
                "#!"
                + sys.executable
                + '\nimport os,sys,json\nprint(json.dumps({"home":os.environ.get("CODEX_HOME"),"parent":os.environ.get("CODEX_THREAD_ID"),"key":os.environ.get("OPENAI_API_KEY"),"cwd":os.getcwd(),"args":sys.argv[1:]}))\n'
            )
            fake.chmod(0o700)
            registry = {
                "version": 1,
                "profiles": {
                    key: {
                        "name": "Test",
                        "home": str(root / ("account " + key)),
                        "desktop_data": str(root / ("desktop " + key)),
                    }
                    for key in ["a", "b"]
                },
            }
            (root / "profiles.json").write_text(json.dumps(registry))
            env = {
                **os.environ,
                "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
                "CODEX_THREAD_ID": "unrelated-parent",
                "OPENAI_API_KEY": "test-only",
            }
            for key in ["a", "b"]:
                output = subprocess.check_output(
                    [
                        sys.executable,
                        str(ROOT / "src/profiles.py"),
                        "--root",
                        str(root),
                        "cli",
                        key,
                        "exec",
                        "literal $HOME; do not execute",
                    ],
                    cwd=root,
                    env=env,
                    text=True,
                )
                result = json.loads(output)
                self.assertEqual(result["home"], registry["profiles"][key]["home"])
                self.assertIsNone(result["parent"])
                self.assertIsNone(result["key"])
                self.assertEqual(Path(result["cwd"]).resolve(), root.resolve())
                self.assertEqual(result["args"], ["exec", "literal $HOME; do not execute"])


if __name__ == "__main__":
    unittest.main()
