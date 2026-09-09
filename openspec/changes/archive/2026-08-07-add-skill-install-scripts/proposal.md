## Why

The repo's old installation path (`create-links.ps1` + `install.py`, PowerShell symlinks into `.claude`/`.github`) has already been deleted from the working tree, and an `ossify-cogents.json` registry file has been drafted at the repo root, but the README still documents the removed symlink script and there is no supported way for a consumer to install this repo's skills/commands/rules into their own repo. Consumers need a documented, one-command path (via the `ossify-cogents` CLI) plus a manual fallback.

## What Changes

- **BREAKING**: Remove README instructions for the deleted `create-links.ps1` symlink workflow.
- Commit `ossify-cogents.json` (currently untracked) as the repo's ossify registry definition.
- Add `scripts/install.sh` (macOS/Linux) and `scripts/install.ps1` (Windows): each checks for `uv` (fails with a clear error if missing), installs `ossify-cogents` via `uv tool install` if missing, refuses to overwrite an existing `ossify-cogents.json` in the caller's working directory unless `--force`/`-Force` is passed, fetches this repo's `ossify-cogents.json` from GitHub `main` into the caller's working directory, and runs `ossify-cogents install`.
- Rewrite the README "Installation Guide" section with two documented options:
  1. **(Recommended)** one-line `curl | bash` (macOS/Linux) / `irm | iex` (Windows) install using the new scripts.
  2. **Manual**: copy the `skills/`, `commands/`, `rules/` folders directly into the consumer's repo — no script involved.

## Capabilities

### New Capabilities
- `skill-install-scripts`: Cross-platform install scripts that seed a consumer repo's `ossify-cogents.json` from this repo and invoke `ossify-cogents install`, plus the README documentation for both the scripted and manual install paths.

### Modified Capabilities
(none — no existing spec covers installation/distribution of skills)

## Impact

- Affected files: `README.md`, new `scripts/install.sh`, new `scripts/install.ps1`, `ossify-cogents.json` (moves from untracked to committed).
- No impact on existing skills' runtime behavior (`skills/`, `rules/`, `commands/` contents are unchanged).
- Consumers of this repo now depend on the `ossify-cogents` CLI (external tool, itself installed via `uv tool install`) for the recommended install path.
