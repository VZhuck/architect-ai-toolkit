## Why

The legacy Word→Markdown pipeline (`.ai-automation/skills/convert-word-to-md` + `sad-from-markdown`, deleted from this repo but recoverable from git history at `a53675a`) split the work into a thin PowerShell/pandoc wrapper followed by an **LLM-only** normalization pass — table conversion, TOC/index generation, and filename conventions were all left to per-run LLM judgment rather than deterministic code. That makes the output non-reproducible and untestable. We need a Python, pytest-covered skill that converts a `.docx` straight into a folder of markdown section files that already comply with `rules/sad-sections.instructions.md`, minimizing what's left to LLM judgment.

## What Changes

- Add `skills/word-to-md/` — a self-contained Python skill (SKILL.md + `scripts/` + `tests/`) that:
  - Extracts a `.docx` to raw markdown + media via `pandoc` into an intermediate `ai-workflow/word-to-md/<doc-stem>/` folder.
  - Deterministically normalizes the raw markdown to match the SAD section rules: drops pandoc's auto-TOC, folds pre-heading cover content into an index preamble, converts HTML tables to markdown pipe tables unless they contain `colspan`/`rowspan` (in which case they're kept as HTML with an explanatory comment), unescapes HTML entities, splits by H1 into `<n>.<Title>.md` files, and generates a mechanical `00.Index.md` with nested cross-file links.
  - Is runnable standalone via CLI (argparse) or via `pytest`, not only as an agent-orchestrated skill.
- Add a `pytest` suite under `skills/word-to-md/tests/` exercising the full pipeline against `test-data/Northwind-Cloud-Landing-Zone-SAD.docx`, plus narrow unit tests for the table normalizer covering the merged-cell branch the sample doc doesn't exercise.
- **BREAKING**: Migrate Python dependency management from `requirements.txt` to `uv` (`pyproject.toml` + `uv.lock`). All Python scripts in the repo are invoked via `uv run ...` going forward instead of an activated venv + `pip install -r requirements.txt`.
- Fix an ambiguity in `rules/sad-sections.instructions.md`'s "File Naming Format" section: clarify that the title portion of `<n>.<Title>.md` preserves source heading word casing and hyphenates spaces (Title-Case-Hyphenated), rather than the loosely-used term "kebab-case" which implies lowercasing.

## Capabilities

### New Capabilities
- `word-to-md-conversion`: Converting a Word document into rule-compliant, split markdown section files (pandoc extraction + deterministic Python normalization + heading split + index generation).
- `python-env-management`: Repo-wide Python dependency/environment management via `uv`, replacing `requirements.txt` + ad hoc venv activation.

### Modified Capabilities
- none (no existing `openspec/specs/` capability covers Python tooling or document conversion today; `jira-raw-requirements` is unrelated).

## Impact

- New: `skills/word-to-md/SKILL.md`, `skills/word-to-md/scripts/*.py`, `skills/word-to-md/tests/*.py`, `.claude/skills/word-to-md` (symlink to `../../skills/word-to-md`).
- New: `pyproject.toml`, `uv.lock` at repo root.
- Removed: `requirements.txt` (superseded by `pyproject.toml`).
- Modified: `rules/sad-sections.instructions.md` (naming-convention clarification only — no behavior change to existing hand-authored SAD content).
- Existing `.ai-automation/scripts/*.py` (`split-markdown-by-heading.py`, `copy-dir.py`) and any docs referencing `pip install -r requirements.txt` need their invocation instructions updated to `uv run`.
- Out of scope: Mermaid/diagram conversion, the Markdown→Word direction (unaffected), and non-Python (`.ps1`) scripts beyond what the `uv` migration touches.
