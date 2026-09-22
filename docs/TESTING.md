# Testing

## Local checks

```bash
make check  # Ruff, Python tests, Swift formatting and type checks
make smoke # Four real launcher builds with a fixture desktop app
```

Activate the development virtual environment first; see [CONTRIBUTING.md](../CONTRIBUTING.md).

Unit and subprocess tests cover profile isolation, 25-profile registry round-tripping, account-specific CLI arguments, environment cleanup, install planning, equal display names, failure rollback, Dock target repair, and PID-based launch decisions.

The macOS smoke test actually compiles and signs four launcher bundles in a temporary directory. It checks initial installation, subsequent `add`, distinct bundle IDs and paths, CLI routing for all four profiles, and read-only planning.

CI runs the checks on Python 3.10 and 3.14, and smoke builds on the newer interpreter. See the [GitHub Actions runs](https://github.com/original4422/codex-profiles/actions/workflows/check.yml) for hosted results.

## Local evidence

- Earlier launcher version: inspected official desktop `26.915.31945` and CLI `0.155.1`; verified separate desktop processes and data paths, account-specific process matching, and CLI authentication status.
- Current source: multi-profile unit/subprocess tests and four real isolated builds passed locally.
- UI account identity, Cmd+Q/reopen and reboot behavior require manual acceptance.

## Manual acceptance

Run these checks with idle accounts and test projects.

1. Create at least three profiles and log in to the intended accounts.
2. Open each numbered Dock launcher; verify the account shown in each official window.
3. Click an already running account's launcher; verify it focuses that account.
4. Cmd+Q in one official account window; click its numbered launcher again and verify the same identity.
5. Quit the numbered launcher itself; open it again from the Dock.
6. Restart macOS and repeat the launch/reopen checks.
7. Verify ordinary `codex` still uses its original account and `codex-profile cli <id>` selects the requested profile.
8. Inspect a two-digit numbered launcher icon for clipping.
