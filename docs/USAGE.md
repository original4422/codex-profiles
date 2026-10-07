# Usage

## Account profiles

A profile is an account-scoped Codex directory plus an independent desktop data directory. Use any registered profile with the desktop app, the CLI, or both. There is no hardcoded count limit.

Profile IDs start with a lowercase letter and contain at most 32 lowercase letters, digits or hyphens. Launcher filenames and bundle IDs derive from the ID. Display names are independent, so two accounts may have the same display label without overwriting each other's launchers.

## Install and add

```bash
python3 install.py --profile work --name "Work" --pin
~/.local/bin/codex-profile add research --name "Research" --pin
```

Each command installs one profile. `--pin` is optional. It backs up the Dock settings, pins the account launcher and collapses duplicate fixed entries pointing at the same official app. Other applications keep their order.

Preview any installation with `--dry-run`. It performs checks and prints paths without creating files or modifying the Dock.

```bash
codex-profile add research --name "Research" --dry-run
```

Remove `--dry-run` to install the previewed profile. If combined with `--pin`, the preview leaves the Dock unchanged.

## Register an existing account

Explicitly provide its current directories:

```bash
python3 install.py --profile personal --name "Personal" \
  --home "$HOME/.codex" \
  --desktop-data "$HOME/Library/Application Support/Codex" \
  --pin
```

The installer preserves existing credentials and configuration. Different profile IDs cannot share or nest their data directories. An existing profile's account paths cannot be changed during an update; create another profile ID if you want different paths.

## Non-default official app location

```bash
python3 install.py --profile work --app "/path/to/ChatGPT.app"
```

Automatic discovery checks the system and user Applications folders for the official desktop bundles. The app must identify itself as `com.openai.codex` in `Info.plist` and contain the executable declared by `CFBundleExecutable`. Desktop discovery does not inspect the bundled CLI. CLI commands use the standalone `codex` on `PATH` and report a separate error when it is missing.

## Choose a client

```bash
codex-profile desktop work
codex-profile cli work
codex-profile cli work -C /path/to/project
codex-profile cli work login
codex-profile status work
codex-profile terminal work
```

CLI arguments are passed directly, without shell evaluation. The current working directory is preserved, except `terminal`, which starts a new terminal session in your home directory.

A profile's desktop and CLI can share authentication state. Signing out from one may affect the other. The ordinary `codex` command is unchanged by this manager.

## Installed files

Default locations:

| Path | Purpose |
| --- | --- |
| `~/Applications/Codex <id>.app` | Numbered account launcher |
| `~/.local/bin/codex-profile` | Single management command |
| `~/Library/Application Support/Codex Profiles/profiles.json` | Profile registry, not tokens |
| `…/Codex Profiles/accounts/<id>` | New profile's Codex state and credentials |
| `…/Codex Profiles/desktop/<id>` | New profile's desktop data |
| `…/Codex Profiles/engine` | Installed manager and native helpers |
| `…/Codex Profiles/backups` | Previous installation artifacts and Dock preferences |

The registry can point at existing account directories outside these defaults. Inspect `list` before moving or deleting state. Installed launchers use the copied engine, so the source checkout may be moved. Python itself must remain installed at its recorded location.

## Upgrade

Quit the account launcher you are updating, then run the current installer:

```bash
python3 install.py --profile work
```

Existing account paths and registered launcher paths are retained. Replacements are staged and compiled before installation; failures while replacing artifacts restore the previous installation. Account login and conversation directories are never replacement targets. Concurrent installations are serialized with a local lock.

The official app may keep running during a launcher update. Do not quit active Codex tasks just to update the launcher.

## Troubleshooting

- **Wrong account after clicking the Dock:** use the numbered launcher rather than the official running-app icon. Run `codex-profile doctor <id>` to inspect its Dock registration.
- **No profiles installed:** run `python3 install.py --profile work` from the source checkout.
- **Command not found:** use `~/.local/bin/codex-profile`, or add that directory to your PATH yourself.
- **Not logged in:** open the chosen launcher and complete ChatGPT login, or run `codex-profile cli <id> login`.
- **Official app not found:** pass `--app` during installation.
- **Update refuses to replace a running launcher:** quit the numbered launcher, not the official app.
- **Existing process is active but no window appears:** use that official app's window menu or reopen its window.

## Uninstall

Quit the numbered launcher, move its `.app` bundle to Trash and remove its Dock pin. Remove `~/.local/bin/codex-profile` if you no longer need the manager. Account directories remain available for a future installation.

The manager state directory may contain credentials and conversation history under `accounts/`. Do not delete the whole directory merely to remove a launcher.
