# Changelog

## 0.3.0 — 2026-09-22 (development preview)

- Create any named profile on first installation; remove the fixed A/B bootstrap.
- Build additional launchers directly through `codex-profile add`.
- Use profile IDs for new app filenames and fit multi-digit icon labels.
- Add dry-run planning, serialized installations and replacement rollback.
- Add bilingual documentation, agent installation instructions and generated overview artwork.
- Standardize Python/Swift formatting and test four real profile installations.

## 0.2.0

- Replace the one-shot shell app with a persistent native Dock launcher.
- Give each launcher its own identity and generated numbered icon.
- Add account-scoped desktop, CLI, terminal, status and diagnostic commands.
- Keep A/B login directories and provide a single `codex-profile` command.
- Repair duplicate official-app Dock pins with preference backups.
- Focus existing account processes by their actual open profile data.
- Add regression tests and macOS CI.

## 0.1.0

- Initial local dual-account shell launcher.
