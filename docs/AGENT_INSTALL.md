# Agent installation guide

Use this guide when the user asks you to install Codex Profiles. Install the named profiles they need; do not assume there are exactly two accounts. Use the repository's current installer and command, without adding aliases or compatibility scripts.

## 1. Check the environment

- Confirm macOS, Python 3.10+, Xcode Command Line Tools and the official desktop app are available.
- Read `README.md` and `AGENTS.md`. Inspect `install.py --help` for the current options.
- Identify the repository from the user's provided URL, local path, or current working directory. If no source is available, ask for it rather than inventing a download URL.
- If prerequisites are missing, explain which are missing before proposing a system-level installation.

## 2. Identify profiles

- If `~/.local/bin/codex-profile` already exists, run `list` to inspect registered IDs and state directories.
- Ask how many additional accounts and which labels the user wants when this is unspecified. An ID such as `work` is separate from the account email and display name.
- Normal `codex` keeps its current account. Do not migrate that account just to add another one.
- Existing profile IDs are updated in place through the installer; an existing account directory can be registered explicitly with `--home` and `--desktop-data`.
- Never read or copy `auth.json`, cookies or tokens. Do not sign out the user's existing accounts.

## 3. Preview and install

For a new Work account, from the checkout:

```bash
python3 install.py --profile work --name "Work" --dry-run
python3 install.py --profile work --name "Work" --pin
```

Use the IDs and labels chosen by the user. `--pin` explicitly changes the Dock, backs up its preferences and keeps the official entry alongside the account launcher.

For subsequent accounts:

```bash
~/.local/bin/codex-profile add research --name "Research" --pin
```

If a launcher is already running and needs an upgrade, have the user quit that launcher before replacing it. Do not interrupt real Codex tasks or kill the official application.

## 4. Verify and hand over login

```bash
~/.local/bin/codex-profile list
~/.local/bin/codex-profile doctor work
```

Open the launcher path reported by the installer. Let the user complete ChatGPT login and verify the intended account. `status work` confirms the CLI authentication method; check the desktop window for the signed-in account.

Ask the user to check Cmd+Q followed by reopening the numbered Dock icon. Do not report the UI check as passed based only on process or directory checks. Do not invoke models merely to test installation.

## 5. Report the result

Give the user the exact launcher path and these commands with their actual profile IDs:

```bash
~/.local/bin/codex-profile desktop work
~/.local/bin/codex-profile cli work
codex
```

Explain that the last command retains the existing default account. State what was verified, whether login or the quit/reopen check is pending, and where the backups are stored. No extra wrappers, shell startup edits or credential migrations are needed.
