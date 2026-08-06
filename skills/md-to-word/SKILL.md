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
- **Mermaid rendering**: pandoc has no native mermaid support and would otherwise emit a ` ```mermaid ` fenced block as literal code text in the output. Any file containing one is first run through `mermaid-cli` (`mmdc`), which extracts each diagram, renders it to a PNG, and rewrites the fence as a normal image reference — before pandoc ever sees it. Requires `mmdc` (`@mermaid-js/mermaid-cli`) on `PATH`; only enforced for files that actually contain a mermaid fence. Any `prefix:name` iconify icon reference found inside the fence (e.g. `icon: "logos:aws-lambda"` or `service db(logos:aws-rds)`) is auto-detected and passed to `mmdc --iconPacks @iconify-json/<prefix>` — without this, icons mermaid can't resolve render as a `?` placeholder instead of the actual glyph.
- **HTML table splicing**: word-to-md keeps tables with colspan/rowspan/nested tables as raw HTML. Pandoc's markdown reader treats that raw `<table>` as inert raw HTML and its docx writer silently drops it — losing the table *and* any images inside it. Each such block is instead rendered on its own via pandoc's HTML reader (`pandoc -f html -t docx`), which parses row/col spans and `<img>` tags correctly, and the resulting native `<w:tbl>` OOXML (plus its images) is spliced back into the section file as a raw `openxml` block before the main pandoc run, then the images are registered into the final docx's relationships/media/content-types in a small post-processing pass.
- **Page breaks**: a raw `openxml` page-break paragraph is inserted before every `<n>.<Title>.md` file (i.e. before each H1 section), so sections don't run into each other on the same page.
- **Concatenation**: the cover-only content plus every `<n>.<Title>.md` file (sorted by numeric filename prefix), separated by page breaks — all staged into a temporary working directory alongside a copy of `media/`, so the originals are never modified — are passed to a single `pandoc -s --toc --toc-depth=3 [--reference-doc <template>] ... -o <output>.docx` invocation.

### 2. Review the output

- Open the generated `.docx` in Word and confirm the table of contents is a native field (right-click → "Update Field" should work) rather than static text.
- If a template was supplied, confirm heading/body styles match the template rather than pandoc's defaults.
- Confirm each H1 section starts on its own page, and that any table that had colspan/rowspan (kept as HTML by word-to-md) still renders with merged cells and its images intact.

## Prerequisites

- `pandoc` on `PATH`.
- `mmdc` (`@mermaid-js/mermaid-cli`) on `PATH`, only required for files with a mermaid fence.
- `rsvg-convert` (from `librsvg`, e.g. `brew install librsvg`) on `PATH` if any section references a standalone `.svg` image (e.g. a draw.io export). Without it, pandoc still emits the `<a:blip>` but without the fallback raster Word needs to actually render it — the image silently fails to show up even though pandoc exits with a warning, not an error.

## Notes for implementers

- `skills/md-to-word/scripts/index_split.py` exposes `split_cover_and_toc_list(text: str) -> tuple[str, str]` as a standalone, unit-testable function — feed it any `00.Index.md`-shaped text to see the cover/list split independent of a real conversion.
- `skills/md-to-word/scripts/md_to_word.py` wires template resolution, index splitting, mermaid/icon-pack rendering, HTML-table splicing, page breaks, and the pandoc invocation together and is the CLI entry point; `convert(source_folder, template=None, output=None)` is also importable directly.
- Nested `<table>` inside `<table>` is not handled by the HTML-table splicing (the non-greedy regex matches up to the first closing `</table>`, i.e. the inner one) — out of scope for now since it wasn't part of the reported issues.
- Tests: `uv run pytest skills/md-to-word/tests/`.
