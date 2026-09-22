# Security

Codex Profiles runs the official client with account-scoped local paths. It does not provide an OS sandbox, request proxy, token pool or automatic account rotation.

## Report a vulnerability

Do not post credentials, cookies or private account data in public issues. If the hosting repository has private vulnerability reporting enabled, use it. Otherwise ask the maintainers for a private reporting channel before sharing sensitive details.

A useful report includes the affected version, reproduction with synthetic data, impact and suggested mitigation. Do not test against someone else's account.

## Sensitive files

All account credentials and conversation data belong outside the source repository. Runtime state, generated apps and local environment files are excluded by `.gitignore`. The installer never treats account data directories as replacement targets.
