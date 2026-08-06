---
name: md-to-word
description: "Convert a folder of rule-compliant markdown SAD section files (00.Index.md + numbered <n>.<Title>.md, as produced by word-to-md) into a single Word (.docx) document, using pandoc for rendering and a deterministic Python step to replace the materialized index list with a native Word TOC field."
argument-hint: "sourceFolder (markdown section folder, default 'sad'), template (optional reference .docx path, falls back to .env's SAD_TEMPLATE), output (optional output .docx path)"
---

# Markdown To Word

Convert a folder of split, rule-compliant markdown files back into a single `.docx` — the reverse of `word-to-md`. Everything this skill does is implemented as a plain Python script, runnable manually or under `pytest`.

## Parameters

- **sourceFolder**: Folder containing `00.Index.md` and `<n>.<Title>.md` section files. Default: `sad`.
- **template**: Optional reference `.docx` template passed to pandoc's `--reference-doc`. Default: the `SAD_TEMPLATE` key in a repo-root `.env` file. If neither resolves, pandoc's default styling is used and a warning is printed.
- **output**: Optional output `.docx` path. Default: `ai-workflow/md-to-word/<sourceFolder-name>.docx`.

## Workflow

### 1. Run the script

```bash
uv run python skills/md-to-word/scripts/md_to_word.py --source {sourceFolder}
uv run python skills/md-to-word/scripts/md_to_word.py --source {sourceFolder} --template {template}
uv run python skills/md-to-word/scripts/md_to_word.py --source {sourceFolder} --output {output}
```

This runs in one process:

- **Template resolution**: `--template` argument, else the repo-root `.env`'s `SAD_TEMPLATE` key (plain key=value parsing, no `python-dotenv` dependency), else no `--reference-doc` at all. If a template path resolves from either source but doesn't exist on disk, the script raises an error rather than silently continuing.
- **Index split**: `00.Index.md` contains a cover-page preamble (title block, doc version, classification, cover image) followed by a materialized nested list of numbered section/subsection links. The cover preamble is kept; the materialized list is dropped, because pandoc's `--toc` generates a real, updatable Word TOC field in its place.
- **Mermaid rendering**: pandoc has no native mermaid support and would otherwise emit a ` ```mermaid ` fenced block as literal code text in the output. Any file containing one is first run through `mermaid-cli` (`mmdc`), which extracts each diagram, renders it to a PNG, and rewrites the fence as a normal image reference — before pandoc ever sees it. Requires `mmdc` (`@mermaid-js/mermaid-cli`) on `PATH`; only enforced for files that actually contain a mermaid fence.
- **Concatenation**: the cover-only content plus every `<n>.<Title>.md` file (sorted by numeric filename prefix) — all staged into a temporary working directory alongside a copy of `media/`, so the originals are never modified — are passed to a single `pandoc -s --toc --toc-depth=3 [--reference-doc <template>] ... -o <output>.docx` invocation.

### 2. Review the output

- Open the generated `.docx` in Word and confirm the table of contents is a native field (right-click → "Update Field" should work) rather than static text.
- If a template was supplied, confirm heading/body styles match the template rather than pandoc's defaults.

## Notes for implementers

- `skills/md-to-word/scripts/index_split.py` exposes `split_cover_and_toc_list(text: str) -> tuple[str, str]` as a standalone, unit-testable function — feed it any `00.Index.md`-shaped text to see the cover/list split independent of a real conversion.
- `skills/md-to-word/scripts/md_to_word.py` wires template resolution, index splitting, and the pandoc invocation together and is the CLI entry point; `convert(source_folder, template=None, output=None)` is also importable directly.
- Tests: `uv run pytest skills/md-to-word/tests/`.
