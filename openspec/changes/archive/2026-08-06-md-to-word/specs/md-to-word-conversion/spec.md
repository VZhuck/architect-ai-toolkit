## ADDED Requirements

### Requirement: Section concatenation into a single docx
The system SHALL convert a folder of `<n>.<Title>.md` markdown section files plus `00.Index.md` (as produced by `word-to-md`) into a single `.docx` file, by invoking `pandoc` via `subprocess` with the section files ordered by their numeric filename prefix, run with the source folder as the working directory so relative `media/...` image paths resolve.

#### Scenario: Successful conversion of a sample section folder
- **WHEN** the script is run with `--source ai-workflow/sad-test`
- **THEN** a single `.docx` file is produced containing the content of every `<n>.<Title>.md` file in that folder, in ascending numeric order, with embedded images resolved from the folder's `media/` subfolder

### Requirement: Template resolution with `.env` fallback
The system SHALL resolve the Word reference template in this order: an explicit `--template` CLI argument; if absent, the `SAD_TEMPLATE` key read from a `.env` file at the repository root (plain key=value parsing, no `python-dotenv` dependency); if neither resolves to a value, the system SHALL proceed without a `--reference-doc` argument (pandoc's default styling) and SHALL emit a warning rather than raising an error. If a template path resolves (from either source) but does not exist on disk, the system SHALL raise an error rather than silently falling through.

#### Scenario: Explicit template argument takes precedence
- **WHEN** the script is run with `--template test-data/architecture-template.docx` and `.env` also defines a different `SAD_TEMPLATE` value
- **THEN** the explicitly passed template is used for `--reference-doc`, not the `.env` value

#### Scenario: Falls back to .env when no argument given
- **WHEN** the script is run with no `--template` argument and `.env` defines `SAD_TEMPLATE=test-data/architecture-template.docx`
- **THEN** `test-data/architecture-template.docx` is used for `--reference-doc`

#### Scenario: No template resolved
- **WHEN** the script is run with no `--template` argument and no `.env` file, or a `.env` file without a `SAD_TEMPLATE` key
- **THEN** conversion proceeds without a `--reference-doc` argument, and a warning is printed noting that default pandoc styling is being used

#### Scenario: Resolved template path does not exist
- **WHEN** the script is run with `--template does/not/exist.docx`, or `.env`'s `SAD_TEMPLATE` points at a nonexistent path
- **THEN** the script raises an error before invoking `pandoc`, rather than silently falling back to no template

### Requirement: Cover content preserved, materialized TOC list discarded
The system SHALL split `00.Index.md`'s content at the first line matching a numbered list link pattern (`^\d+\.\s+\[`), preserve everything before that point (the cover-page preamble — title block, doc version, classification, cover image, etc.) as the document's opening content, and discard everything from that point onward (the materialized nested link list).

#### Scenario: Cover preamble carried into the output document
- **WHEN** converting a section folder whose `00.Index.md` has a cover preamble (title block, cover image) followed by a numbered list of section links
- **THEN** the generated `.docx`'s opening content includes the cover preamble's text and image, and does not contain the markdown-rendered numbered list of section links

### Requirement: Native Word TOC field in place of the materialized list
The system SHALL invoke `pandoc` with `-s --toc --toc-depth 3` so the output `.docx` contains a native Word table-of-contents field (an OOXML `TOC` field code, not a static rendered list), covering heading levels 1 through 3.

#### Scenario: Generated docx contains an updatable TOC field
- **WHEN** a `.docx` is generated from a section folder with H1/H2/H3 headings across its section files
- **THEN** the `.docx`'s `word/document.xml` contains a `TOC` field instruction (`instrText` containing `TOC \o "1-3"`), and no plain-text rendering of the discarded materialized list appears in its place

### Requirement: CLI-runnable script with importable convert function
The system SHALL provide a Python script at `skills/md-to-word/scripts/md_to_word.py`, invocable via CLI arguments (`--source`, optional `--template`, optional `--output`), and SHALL expose an importable `convert(source_folder, template=None, output=None)` function usable independent of the CLI, mirroring `docx_to_md.py`'s `convert()` in `word-to-md`.

#### Scenario: Manual CLI invocation with defaults
- **WHEN** a user runs `uv run python skills/md-to-word/scripts/md_to_word.py --source ai-workflow/sad-test`
- **THEN** the output `.docx` is written to `ai-workflow/md-to-word/sad-test.docx` (the default output path, derived from the source folder name)

#### Scenario: Manual CLI invocation with explicit output path
- **WHEN** a user runs `uv run python skills/md-to-word/scripts/md_to_word.py --source ai-workflow/sad-test --output dist/sad.docx`
- **THEN** the output `.docx` is written to `dist/sad.docx`
