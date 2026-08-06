## 1. Python environment migration to uv

- [x] 1.1 Create `pyproject.toml` declaring `pypandoc>=1.11`, `langchain-text-splitters>=0.3.0` (migrated from `requirements.txt`), plus new deps needed for HTML table parsing (e.g. `beautifulsoup4`, `lxml`)
- [x] 1.2 Run `uv lock` to generate `uv.lock`
- [x] 1.3 Verify existing scripts still run via `uv run python .ai-automation/scripts/split-markdown-by-heading.py --help` and `uv run python .ai-automation/scripts/copy-dir.py --help`
- [x] 1.4 Remove `requirements.txt`
- [x] 1.5 Update any docs/READMEs/SKILL.md files referencing `pip install -r requirements.txt` to the `uv run` equivalent

## 2. Docx extraction (Stage A)

- [x] 2.1 Create `skills/word-to-md/scripts/docx_to_md.py` with argparse CLI (`--source`, `--target-folder`, optional intermediate-folder override)
- [x] 2.2 Implement pandoc invocation matching the probed flags (`-t markdown --extract-media=... --columns=1000 --to=markdown-simple_tables-multiline_tables-grid_tables`), writing raw markdown + media into `ai-workflow/word-to-md/<doc-stem>/`
- [x] 2.3 Handle pandoc-missing/failure with a clear error (mirroring the legacy skill's behavior)

## 3. Rule normalization (Stage B)

- [x] 3.1 Implement TOC-block detection/removal (heading titled "Table of Contents" + self-referential anchor link list)
- [x] 3.2 Implement pre-heading cover-content extraction, to be folded into the index preamble
- [x] 3.3 Implement the table-normalizer as a standalone function: HTML table string → markdown pipe table (unescape entities, `<br>`-joined bullet pseudo-format for list cells, alignment indicators from text-align styling) OR annotated HTML (if `colspan`/`rowspan` present, keep HTML + `<!-- HTML format: [reason] -->` comment + surrounding blank lines)
- [x] 3.4 Implement H1-based file splitting producing `<n>.<Title>.md`, with title casing fixed to preserve source heading word casing (hyphens replace spaces, Windows-invalid characters stripped) — do not lowercase
- [x] 3.5 Implement `00.Index.md` generation: nested list of H1/H2/H3 headings with GitHub-style lowercase-hyphenated anchors and correct cross-file links, cover-content preamble included
- [x] 3.6 Wire Stages A+B together end-to-end in `docx_to_md.py`, writing final output to `--target-folder` (default `sad`) — manually verified against test-data/Northwind-Cloud-Landing-Zone-SAD.docx

## 4. Rules documentation fix

- [x] 4.1 Update `rules/sad-sections.instructions.md`'s "File Naming Format" section to state the title portion preserves source word casing and hyphenates spaces (Title-Case-Hyphenated), removing the ambiguous "kebab-case" wording

## 5. Skill packaging

- [x] 5.1 Write `skills/word-to-md/SKILL.md` describing parameters, workflow, and pointing at the script (following the `skills/load-raw-req/SKILL.md` documentation style)
- [x] 5.2 Create symlink `.claude/skills/word-to-md -> ../../skills/word-to-md`

## 6. Tests

- [x] 6.1 Add `skills/word-to-md/tests/test_docx_to_md.py`: end-to-end run against `test-data/Northwind-Cloud-Landing-Zone-SAD.docx`, asserting: `00.Index.md`, `01.Architecture-Overview.md`, `02.Cost-Benefit-Analysis.md` exist and are correctly named; the "Estimated Monthly Platform Cost" table is a markdown pipe table; the "Benefit Comparison by Landing Zone Area" table is converted to markdown with `<br>` bullet pseudo-format and unescaped entities (not left as HTML); every index link resolves to a real heading anchor in its target file; no HTML entities remain anywhere in output
- [x] 6.2 Add `skills/word-to-md/tests/test_table_normalizer.py`: unit tests against synthetic HTML snippets, including at least one with `colspan`/`rowspan` to cover the "keep as HTML with comment" branch not exercised by the sample docx
- [x] 6.3 Verify `uv run pytest skills/word-to-md/tests/` passes from a clean `.venv` — confirmed after `rm -rf .venv`, `uv run` auto-provisioned and all 16 tests passed

## 7. Final verification

- [x] 7.1 Run `uv run python skills/word-to-md/scripts/docx_to_md.py --source test-data/Northwind-Cloud-Landing-Zone-SAD.docx --target-folder <scratch-dir>` manually and visually confirm output against `rules/sad-sections.instructions.md`'s Quality Checks
- [x] 7.2 Confirm no regression to the Markdown→Word direction (`convert-md-to-word` uses raw `pandoc` CLI via PowerShell, not pypandoc/Python — untouched by this change; pypandoc dependency itself carried forward unchanged in pyproject.toml)
