## 1. Skill scaffolding

- [x] 1.1 Create `skills/md-to-word/{scripts,tests}/` directory structure, mirroring `skills/word-to-md/`.
- [x] 1.2 Write `skills/md-to-word/SKILL.md` (name, description, argument-hint frontmatter; parameters `sourceFolder`/`template`/`output`; workflow section referencing the CLI invocation).

## 2. Index splitting

- [x] 2.1 Implement `skills/md-to-word/scripts/index_split.py` exposing `split_cover_and_toc_list(text: str) -> tuple[str, str]`: split on the first line matching `^\d+\.\s+\[`, returning `(cover, dropped)`.
- [x] 2.2 Write `skills/md-to-word/tests/test_index_split.py` covering: cover text + list present; no list present (cover-only); no cover present (list starts at line 1); index content matching the real shape in `ai-workflow/sad-test/00.Index.md`.

## 3. Template resolution

- [x] 3.1 Implement template resolution in `md_to_word.py`: `--template` arg → else regex-parse repo-root `.env` for `SAD_TEMPLATE=` → else `None`.
- [x] 3.2 If a template path resolves (from either source) but doesn't exist on disk, raise a clear error before invoking `pandoc`.
- [x] 3.3 If no template resolves at all, print a warning and proceed without `--reference-doc`.
- [x] 3.4 Add `SAD_TEMPLATE=` (commented example value, e.g. pointing at `test-data/architecture-template.docx`) to `.env.example`.

## 4. Core conversion script

- [x] 4.1 Implement `skills/md-to-word/scripts/md_to_word.py` with a `convert(source_folder, template=None, output=None) -> Path` function:
  - Read `00.Index.md`, split via `index_split.split_cover_and_toc_list`, write the cover-only text to a temp `.md` file inside the source folder.
  - Collect all other `<n>.<Title>.md` files in the source folder, sorted by numeric filename prefix.
  - Resolve the output path: use `--output` if given, else `ai-workflow/md-to-word/<source-folder-name>.docx`; create parent directories as needed.
  - Build the `pandoc` command: `pandoc -s --toc --toc-depth 3 [--reference-doc <template>] <cover-tmp> <ordered-section-files...> -o <tmp-docx>`, run via `subprocess.run(..., cwd=source_folder, check=True)`.
  - Move the resulting temp `.docx` to the resolved output path; clean up the temp cover markdown file.
  - Raise a clear `RuntimeError` if `pandoc` is missing from `PATH` or the subprocess call fails (mirror `docx_to_md.py`'s `extract_docx` error handling).
- [x] 4.2 Add the CLI entry point (`argparse` with `--source` [default `sad`], `--template` [optional], `--output` [optional]) and `if __name__ == "__main__":` guard, matching `docx_to_md.py`'s structure.

## 5. Tests

- [x] 5.1 Write `skills/md-to-word/tests/test_md_to_word.py`: end-to-end conversion of a small synthetic section folder (with a `media/` image) produces a `.docx` at the expected default output path.
- [x] 5.2 Add a test asserting the generated `.docx`'s `word/document.xml` contains a `TOC` field instruction (`instrText` with `TOC \o`) and does not contain a rendered version of the discarded materialized link list text.
- [x] 5.3 Add a test for template resolution precedence (explicit arg overrides `.env`; `.env`-only fallback; neither present warns and omits `--reference-doc`; nonexistent resolved path raises).
- [x] 5.4 Run `uv run pytest skills/md-to-word/tests/` and confirm all tests pass.

## 6. Command wiring and symlinks

- [x] 6.1 Write `commands/md-to-word.md` (thin slash-command wrapper invoking the `md-to-word` skill), mirroring `commands/load-raw-req.md`'s structure.
- [x] 6.2 Create the `.claude/skills/md-to-word -> ../../skills/md-to-word` symlink.
- [x] 6.3 Create the `.claude/commands/md-to-word.md -> ../../commands/md-to-word.md` symlink.

## 7. Manual verification

- [x] 7.1 Run `uv run python skills/md-to-word/scripts/md_to_word.py --source ai-workflow/sad-test --template test-data/architecture-template.docx` and confirm the output `.docx` opens correctly, shows the cover content, and has a working "Update Field" TOC in Word (or an OOXML inspection equivalent to a manual open, e.g. re-checking `word/document.xml` for the `TOC` field).
- [x] 7.2 Confirm no changes were made to `skills/word-to-md/` or its tests.
