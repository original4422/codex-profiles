# Security

Codex Profiles runs the official client with account-scoped local paths.

## Report a vulnerability

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/original4422/codex-profiles/security/advisories/new).

A useful report includes the affected version, reproduction with synthetic data, impact and suggested mitigation.

## Sensitive files

Account credentials and conversation data stay in the profile directories. Runtime state, generated apps and local environment files are excluded by `.gitignore`. Updates replace the engine, launcher, command and registry files.
