---
name: repo-safety
description: Scans staged git changes for hardcoded user paths, usernames, secrets, and private directories before committing.
---

# Repository Safety Check Workflow

Use this workflow to audit staged changes for sensitive data, secrets, or machine-specific absolute user paths before committing.

## Safety Check Rules

1. **Path Sanitization**:
   - Check `git diff --cached` for any occurrences of `C:\Users\`, `/Users/`, or developer usernames.
   - Replace any machine-specific user paths with `%LOCALAPPDATA%\caster`, `~/.caster`, or repo-relative paths.

2. **Secret Detection**:
   - Verify no passwords, API keys, auth tokens, or private certificates are present.

3. **Documentation Separation**:
   - Ensure local user guides, scratch scripts, or personal notes reside in `%LOCALAPPDATA%\caster\docs\` rather than the public repository root.

4. **Verification**:
   - Run a quick scan:
     ```powershell
     git diff --cached | Select-String -Pattern "Users\\", "C:\\Users", "/Users/"
     ```
   - Ensure the output is completely clean before finalizing commits.
