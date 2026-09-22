# Architecture

## Components

- `install.py`: plan, build, sign and install one named profile; rollback failed replacement.
- `src/profiles.py`: profile validation, registry loading, client launching and Dock registration.
- `src/AccountLauncher.swift`: persistent native Dock entry; initial launch and reopen use the same account ID.
- `src/FocusApp.swift`: activate an already matched process by PID.
- `src/MakeIcon.swift`: generate a numbered icon, fitting multiple digits to the available width.

Runtime Python dependencies: standard library only. Ruff is a development dependency; Swift tools come from Xcode Command Line Tools.

## Profile lifecycle

Installation creates exactly the requested profile. `codex-profile add` invokes the installed copy of the same installer, so first installation and subsequent additions have one implementation. IDs determine new app filenames; registered launcher paths remain stable on updates.

A launcher selects a profile, and the official client handles authentication and requests.

## Desktop launch

The manager searches the official app's main processes and checks which desktop data directory each process has open. If a matching process exists, it activates that PID. Otherwise it uses `open -n` with:

- `CODEX_HOME`: account configuration, authentication and Codex state.
- `CODEX_ELECTRON_USER_DATA_PATH`: desktop data directory.
- `--user-data-dir`: Chromium data directory.

The explicit desktop environment variable is needed by the inspected app version, which sets Electron's userData path itself.

## State and replacement

Each profile has separate Codex and desktop directories. Validation rejects shared/nested profile paths, unsafe IDs and invalid display names. New account directories have private permissions; existing user files are preserved.

An installation lock prevents concurrent writers from losing registrations. Native artifacts are built before replacement. Existing engine, launcher, command and registry artifacts are moved to a backup directory; replacement failure restores them. The optional Dock operation is separate: installation can succeed even if updating Dock preferences fails.

## Launch environment

The manager removes inherited Codex task and identity environment variables before launching a selected client. Each client uses its profile's account directories and the current user's filesystem permissions.
