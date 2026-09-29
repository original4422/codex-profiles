"""Installer planning and rollback tests; no real accounts or Dock mutations."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from src.profiles import load_registry, new_profile, validate_profile


def arguments(root: Path, identifier: str, **overrides) -> argparse.Namespace:
    values = dict(
        root=root,
        profile=identifier,
        name=None,
        home=None,
        desktop_data=None,
        app=None,
        new=False,
        applications_dir=root / "apps",
        bin_dir=root / "bin",
    )
    values.update(overrides)
    return argparse.Namespace(**values)


class InstallTests(unittest.TestCase):
    def test_first_install_only_registers_the_requested_account(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "state"
            registry, profile, app, command = install.plan_install(arguments(root, "research"))
            self.assertEqual(list(registry["profiles"]), ["research"])
            self.assertEqual(profile["home"], str(root / "accounts/research"))
            self.assertEqual(app.name, "Codex research.app")
            self.assertEqual(command.name, "codex-profile")
            self.assertFalse(root.exists())

    def test_twenty_five_accounts_round_trip_without_a_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = {"version": 1, "profiles": {}}
            for number in range(25):
                identifier = f"account-{number}"
                profile = new_profile(root, identifier)
                validate_profile(identifier, profile, registry["profiles"])
                registry["profiles"][identifier] = profile
            (root / "profiles.json").write_text(json.dumps(registry))
            restored = load_registry(root)
            self.assertEqual(len(restored["profiles"]), 25)
            self.assertEqual(len({p["home"] for p in restored["profiles"].values()}), 25)
            self.assertEqual(len({p["desktop_data"] for p in restored["profiles"].values()}), 25)

    def test_equal_display_names_have_different_launcher_filenames(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            one, _, app_one, _ = install.plan_install(arguments(root, "work", name="Shared name"))
            (root / "profiles.json").write_text(json.dumps(one))
            two, _, app_two, _ = install.plan_install(arguments(root, "client", name="Shared name"))
            self.assertNotEqual(app_one, app_two)
            self.assertEqual(len(two["profiles"]), 2)

    def test_existing_login_directories_are_not_moved_by_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry, profile, _, _ = install.plan_install(arguments(root, "work"))
            profile["home"] = str(root / "existing-account")
            profile["desktop_data"] = str(root / "existing-ui")
            (root / "profiles.json").write_text(json.dumps(registry))
            _, existing, _, _ = install.plan_install(arguments(root, "work"))
            self.assertEqual(existing["home"], profile["home"])
            with self.assertRaisesRegex(ValueError, "already uses"):
                install.plan_install(arguments(root, "work", home=str(root / "another-account")))

    def test_invalid_names_and_paths_are_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "state"
            for identifier in ("../escape", "", "UPPER", "work/child"):
                with self.assertRaises(ValueError):
                    install.plan_install(arguments(root, identifier))
            for name in ("../escape", "bad\nname", "   "):
                with self.assertRaises(ValueError):
                    install.plan_install(arguments(root, "work", name=name))
            self.assertFalse(root.exists())

    def test_install_failure_restores_previous_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            previous = root / "command"
            previous.write_text("previous command")
            new = root / "new"
            new.write_text("replacement")
            missing = root / "does-not-exist"
            with self.assertRaises(OSError):
                install.replace_artifacts(
                    [(new, previous), (missing, root / "second")], root / "backup"
                )
            self.assertEqual(previous.read_text(), "previous command")
            self.assertFalse((root / "second").exists())

    def test_account_paths_cannot_overlap_installation_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "state"
            for directory in (root, root / "engine", root / "backups/credentials"):
                with self.assertRaises(ValueError):
                    install.plan_install(arguments(root, "work", home=str(directory)))
            self.assertFalse(root.exists())

    def test_dry_run_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "state"
            options = arguments(root, "work", dry_run=True, pin=True)
            with (
                patch.object(install, "parse_args", return_value=options),
                patch.object(install, "preflight"),
                patch.object(install, "find_app", return_value=Path("/Applications/ChatGPT.app")),
                patch.object(install, "build_artifacts") as build,
                patch.object(install, "pin_dock") as pin,
            ):
                install.main()
            build.assert_not_called()
            pin.assert_not_called()
            self.assertFalse(root.exists())

    def test_invalid_registry_has_a_useful_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "profiles.json").write_text(json.dumps({"version": 99, "profiles": {}}))
            with self.assertRaisesRegex(ValueError, "Invalid profiles.json"):
                load_registry(root)


if __name__ == "__main__":
    unittest.main()
