# Repository Safety & Privacy Guidelines

## 1. Zero Hardcoded Absolute User Paths
- **Rule**: Never commit files containing host-specific absolute user paths (e.g. `C:\Users\<username>\`, `/Users/<username>/`, `/home/<username>/`).
- **Standard**:
  - For user content directories, use `%LOCALAPPDATA%\caster` or `~/.caster`.
  - For repository-internal references, use relative paths from the repository root (e.g. `castervoice/asynch/hud/`).
  - In Python code, dynamically resolve runtime paths via `castervoice.lib.settings` or `os.path.expanduser("~")`.

## 2. Secrets & Credential Sanitization
- **Rule**: Never stage or commit API tokens, passwords, private SSH/TLS keys, or connection credentials.
- **IPC Sockets**: Internal IPC communication must bind strictly to loopback (`127.0.0.1` / `localhost`).

## 3. Pre-Commit Safety Check Workflow
Before generating commit messages or committing changes:
1. Inspect staged changes with `git diff --cached`.
2. Verify that no absolute Windows/POSIX user paths or usernames are present in staged files.
3. Confirm that all documentation artifacts intended for the local user directory reside in `%LOCALAPPDATA%\caster\docs\` rather than polluting the core engine repository.
4. Ensure conventional commit messages format all paths as repo-relative.
