---
name: word-to-md
description: "Convert a Word (.docx) document into a folder of rule-compliant markdown section files (00.Index.md + numbered <n>.<Title>.md per H1), using pandoc for extraction and a deterministic Python normalizer for rules/sad-sections.instructions.md compliance."
argument-hint: "sourceDoc (Word document path), targetFolder (optional output folder, default 'sad')"
---

# Word To Markdown

Convert a `.docx` file into a folder of split, rule-compliant markdown files in one deterministic pass — no LLM-driven table/link/TOC cleanup step required. Everything this skill does is implemented as a plain Python script, runnable manually or under `pytest`.

## Parameters

- **sourceDoc**: Path to the source `.docx` file.
- **targetFolder**: Optional output folder for the final section files. Default: `sad`.
- **workdir**: Optional intermediate folder for pandoc's raw extraction. Default: `ai-workflow/word-to-md/<source-doc-name>`.

## Workflow

### 1. Run the script

```bash
uv run python skills/word-to-md/scripts/docx_to_md.py --source {sourceDoc} --target-folder {targetFolder}
```

This runs both stages in one process:

- **Stage A (extraction)**: `pandoc` converts the `.docx` to raw markdown + extracted media into `{workdir}/raw.md` and `{workdir}/media/`. Pandoc is used here (not a pure-Python docx parser) because it correctly surfaces `colspan`/`rowspan` on merged OOXML table cells, which Stage B's table decision depends on.
- **Stage B (normalization)**: deterministically brings the raw markdown into compliance with `rules/sad-sections.instructions.md`:
  - Discards pandoc's auto-generated "Table of Contents" block.
  - Folds any pre-heading cover-page content into `00.Index.md`'s preamble.
  - Converts every HTML `<table>` to a markdown pipe table (unescaping entities, joining list-cell content with `<br>` bullet pseudo-format, deriving column alignment from `text-align` styling) **unless** it contains `colspan`/`rowspan` or a nested `<table>`, in which case it is kept as HTML with an `<!-- HTML format: [reason] -->` comment above it.
  - Splits the document by H1 heading into `<n>.<Title>.md` files, where `<Title>` preserves the source heading's word casing (hyphens replace spaces) — not lowercased.
  - Generates `00.Index.md`: a nested list of every H1/H2/H3 heading with correct cross-file links and GitHub-style anchors.

### 2. Review the output

- Image paths and inline width/height attributes are preserved as pandoc emits them. This skill does **not** attempt diagram-to-Mermaid conversion or photo-vs-diagram classification — that still requires visual/LLM judgment and is out of scope here. If a generated image is actually a diagram worth redrawing as Mermaid, do that as a manual follow-up pass over the specific file.
- Verify the output against the Quality Checks in `rules/sad-sections.instructions.md`.

## Notes for implementers

- `skills/word-to-md/scripts/table_normalizer.py` exposes `normalize_table_html(table_html: str) -> str` as a standalone, unit-testable function — feed it any HTML table string to see the conversion decision independent of a real docx.
- `skills/word-to-md/scripts/sad_structure.py` exposes the cover/TOC split, H1 splitting, filename sanitizer, and anchor generator as standalone functions.
- `skills/word-to-md/scripts/docx_to_md.py` wires both stages together and is the CLI entry point; `convert(source, target_folder, workdir=None)` is also importable directly.
- Tests: `uv run pytest skills/word-to-md/tests/`.
