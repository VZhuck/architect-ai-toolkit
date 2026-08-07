# architect-ai-toolkit
Set of skills and tool for solution architecture

## Installation Guide

### Creating Soft Link Mappings

To set up the repository for your preferred AI platform, run the following PowerShell script from the repository root:

```powershell
# For GitHub Copilot
./create-links.ps1 -AiPlatform "GhCopilot"

# For Claude
./create-links.ps1 -AiPlatform "Claude"

# For both platforms (GitHub Copilot & Claude)
./create-links.ps1 -AiPlatform "All"
```

This will create the necessary symbolic links for agent, skill, and instruction files under the appropriate platform folders (e.g., `.github`, `.claude`).

To force replacement of existing links, add the `-Force` flag:

```powershell
./create-links.ps1 -AiPlatform "GhCopilot" -Force
```

### Creating a Python Environment
Skills require a Python environment configured in your target repository (the repo where you will run skills). Dependencies are managed with [uv](https://docs.astral.sh/uv/) via `pyproject.toml`/`uv.lock` — there is no separate manual install step.

1. Ensure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.
2. Copy `pyproject.toml` and `uv.lock` from this repository to your target repository (if not already present).
3. Run any script with `uv run`, e.g.:
	```bash
	uv run python skills/word-to-md/scripts/docx_to_md.py --source path/to/file.docx
	uv run pytest skills/word-to-md/tests/
	```
	`uv` automatically creates/syncs `.venv` from `uv.lock` on first use.
