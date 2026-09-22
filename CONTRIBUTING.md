# Contributing

Codex Profiles is a small macOS utility. Favor clear account isolation and predictable launch behavior over additional layers or dependencies.

## Set up

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check
```

Python 3.10+ and Xcode Command Line Tools are required. There are no third-party Python runtime dependencies. Development uses pinned Ruff and the toolchain's `swift-format`.

## Make a change

1. Describe the concrete user problem and the smallest change that solves it.
2. Add a regression test when behavior changes. Use temporary state, fixtures and explicit paths; never use real credentials in tests.
3. Run `make format`, `make check`, and `make smoke` for installer or account-routing changes.
4. Keep README examples, CLI help and the changelog consistent.
5. Explain what changed and how it was verified in the pull request.

## Design rules

- A profile is an account, not a desktop/CLI mode. Both clients select the same profile ID.
- Do not special-case a first/second account or set a count limit.
- Keep `install.py` and `codex-profile` as the only installation and management entry points.
- Propose compatibility layers, legacy aliases or historical format adapters before implementing them.
- Never copy tokens or silently relocate account directories.
- Installer changes must leave unrelated apps and commands alone.
- Visual assets are code-generated. Edit `scripts/render_overview.py` and regenerate the SVG; do not replace it with an uneditable screenshot.

## Report a problem

Include macOS, Python and official app versions, the command or exact Dock entry used, expected behavior, actual behavior and a minimal reproduction. `doctor` is useful for paths but cannot verify the account email in a window.

Remove personal paths if needed. Never attach `auth.json`, cookies, tokens, complete account directories or private task logs.
