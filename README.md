# architect-ai-toolkit
Set of skills and tool for solution architecture

## Installation Guide

### Installing Skills

There are two ways to install this repository's skills, commands, and rules into your own repository.

#### Option 1: Via ossify-cogents (recommended)

This repo is published as an [ossify-cogents](https://github.com/VZhuck/ossify-cogents) source. Run the one-line installer from the root of your target repository:

**macOS/Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/VZhuck/architect-ai-toolkit/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/VZhuck/architect-ai-toolkit/main/scripts/install.ps1 | iex
```

This checks for `uv` (required — install it from the [uv docs](https://docs.astral.sh/uv/getting-started/installation/) if missing), installs the `ossify-cogents` CLI if it isn't already on your `PATH`, fetches this repo's `ossify-cogents.json` into your current directory, and runs `ossify-cogents install`.

If your repository already has an `ossify-cogents.json`, the installer will refuse to overwrite it. Pass `--force` (macOS/Linux) or `-Force` (Windows) to overwrite it anyway:

```bash
curl -fsSL https://raw.githubusercontent.com/VZhuck/architect-ai-toolkit/main/scripts/install.sh | bash -s -- --force
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/VZhuck/architect-ai-toolkit/main/scripts/install.ps1))) -Force
```

#### Option 2: Manual copy

Copy the `skills/`, `commands/`, and `rules/` folders from this repository directly into your target repository. No script required.

### Naming Convention and Migration

All toolkit skills and commands are namespaced under `archy`, so they don't clash with skills from other sources:

- Skills live in `skills/archy-<name>/`, and each `SKILL.md` declares `name: archy-<name>`.
- Commands live in `commands/archy/<name>.md` and are invoked as `/archy:<name>`.

The convention is enforced by `tests/test_naming_conventions.py` (`uv run pytest tests/`).

| Old name | New command | New skill |
| --- | --- | --- |
| `load-raw-req` | `/archy:load-raw-req` | `archy-load-raw-req` |
| `md-to-word` | `/archy:md-to-word` | `archy-md-to-word` |
| `summarize-meeting-decisions` | `/archy:summarize-meeting-decisions` | `archy-summarize-meeting-decisions` |
| `word-to-md` | — (skill only) | `archy-word-to-md` |

If you installed an earlier version, reinstall, then delete the old unprefixed copies (`.claude/skills/<name>/` and `.claude/commands/<name>.md`) so they don't show up twice.

### Creating a Python Environment
Skills require a Python environment configured in your target repository (the repo where you will run skills). Dependencies are managed with [uv](https://docs.astral.sh/uv/) via `pyproject.toml`/`uv.lock` — there is no separate manual install step.

1. Ensure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.
2. Copy `pyproject.toml` and `uv.lock` from this repository to your target repository (if not already present).
3. Run any script with `uv run`, e.g.:
	```bash
	uv run python skills/archy-word-to-md/scripts/docx_to_md.py --source path/to/file.docx
	uv run pytest skills/archy-word-to-md/tests/
	```
	`uv` automatically creates/syncs `.venv` from `uv.lock` on first use.
