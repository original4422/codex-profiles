# Architecture

## Components

- `install.py`: plan, build, sign and install one named profile; rollback failed replacement.
- `src/profiles.py`: profile validation, registry persistence, client launching and Dock registration.
- `src/AccountLauncher.swift`: persistent native Dock entry; initial launch and reopen use the same account ID.
- `src/FocusApp.swift`: activate an already matched process by PID.
- `src/MakeIcon.swift`: generate a numbered icon, fitting multiple digits to the available width.

Runtime Python dependencies: standard library only. Ruff is a development dependency; Swift tools come from Xcode Command Line Tools.

## Profile lifecycle

Installation creates exactly the requested profile. `codex-profile add` invokes the installed copy of the same installer, so first installation and subsequent additions have one implementation. IDs determine new app filenames; registered launcher paths remain stable on updates.

There is no account pool, automatic rotation, global active-account switch or request forwarding. A launcher selects a profile, and the official client handles authentication and requests.

## Desktop launch

The manager searches the official app's main processes and checks which desktop data directory each process has open. If a matching process exists, it activates that PID. Otherwise it uses `open -n` with:

- `CODEX_HOME`: account configuration, authentication and Codex state.
- `CODEX_ELECTRON_USER_DATA_PATH`: desktop data directory.
- `--user-data-dir`: Chromium data directory.

The explicit desktop environment variable is needed by the inspected app version, which sets Electron's userData path itself. The official application may change this internal behavior in future releases.

## State and replacement

Each profile has separate Codex and desktop directories. Validation rejects shared/nested profile paths, unsafe IDs and invalid display names. New account directories have private permissions; existing user files are preserved.

An installation lock prevents concurrent writers from losing registrations. Native artifacts are built before replacement. Existing engine, launcher, command and registry artifacts are moved to a backup directory; replacement failure restores them. The optional Dock operation is separate: installation can succeed even if updating Dock preferences fails.

## Boundaries

The manager never reads or copies authentication tokens. It removes inherited Codex task/identity environment variables before launching a selected client. Account directories isolate application state, not filesystem access or all system services. Multiple official desktop instances are not an upstream compatibility guarantee.

Supporting a different operating system, upstream app behavior or historical interface must be proposed explicitly; do not add speculative adapters.
