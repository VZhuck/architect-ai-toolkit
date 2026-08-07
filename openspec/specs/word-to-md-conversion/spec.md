# word-to-md-conversion Specification

## Purpose

Convert a source Word (`.docx`) document into a folder of rule-compliant markdown section files (per `rules/sad-sections.instructions.md`), using `pandoc` for extraction and a deterministic Python normalizer for formatting, naming, table conversion, and index generation.

## Requirements

### Requirement: Docx extraction to intermediate markdown
The system SHALL convert a source `.docx` file into raw markdown plus extracted media using `pandoc`, writing the result into an intermediate folder under `ai-workflow/word-to-md/<doc-stem>/`.

#### Scenario: Successful extraction
- **WHEN** the script is run with `--source test-data/Northwind-Cloud-Landing-Zone-SAD.docx`
- **THEN** `ai-workflow/word-to-md/Northwind-Cloud-Landing-Zone-SAD/raw.md` and an accompanying media folder are created, containing the document's extracted images

### Requirement: Deterministic table normalization
The system SHALL convert each HTML `<table>` produced by pandoc into a markdown pipe table unless the table contains a `colspan` or `rowspan` attribute anywhere within it, in which case the table SHALL be kept as HTML with an explanatory `<!-- HTML format: [reason] -->` comment immediately above it and blank lines before and after it, per `rules/sad-sections.instructions.md`.

#### Scenario: Table with list cells and no merged cells is converted
- **WHEN** normalizing a table with bulleted-list cell content, HTML entities (e.g. `&amp;`), and no `colspan`/`rowspan` attributes (the "Benefit Comparison by Landing Zone Area" table in the sample docx)
- **THEN** the output is a markdown pipe table with list content joined via `<br>` in bullet pseudo-format and all HTML entities unescaped to plain characters

#### Scenario: Table with merged cells is kept as HTML
- **WHEN** normalizing a synthetic HTML table containing a `colspan` or `rowspan` attribute
- **THEN** the table is left as HTML, its entities are unescaped, and an explanatory comment is inserted immediately above it with blank lines before and after

### Requirement: TOC discarded, cover content folded into index
The system SHALL discard pandoc's auto-generated table-of-contents block (a heading titled "Table of Contents" followed by self-referential anchor links) and SHALL fold any content appearing before the first heading into the generated index file's preamble.

#### Scenario: Cover page and auto-TOC removed from section files
- **WHEN** normalizing a document with cover-page text before the first heading and a pandoc-generated TOC section
- **THEN** neither the raw pandoc TOC nor the cover text appears in any `<n>.<Title>.md` section file, and the cover text appears in `00.Index.md`'s preamble instead

### Requirement: Heading-based file splitting with corrected naming
The system SHALL split the normalized markdown by H1 heading into one file per section, named `<n>.<Title>.md` with a zero-padded section number, where `<Title>` preserves the source heading's word casing with spaces replaced by hyphens and Windows-invalid characters stripped.

#### Scenario: Section files named correctly for the sample document
- **WHEN** converting `test-data/Northwind-Cloud-Landing-Zone-SAD.docx`
- **THEN** the output folder contains `01.Architecture-Overview.md` and `02.Cost-Benefit-Analysis.md` (title-case-hyphenated, not lowercased)

### Requirement: Mechanical index generation
The system SHALL generate a `00.Index.md` file containing a nested list of every H1/H2/H3 heading across all generated section files, with correct cross-file links and GitHub-style lowercase-hyphenated anchors, without requiring LLM judgment.

#### Scenario: Index links resolve to real headings
- **WHEN** `00.Index.md` is generated for the sample document
- **THEN** every link target in the index resolves to a heading anchor that exists in its corresponding generated section file

### Requirement: CLI-runnable script
The system SHALL provide a Python script under `skills/word-to-md/scripts/` invocable directly via CLI arguments (source docx path, optional target folder), independent of any agent/skill orchestration.

#### Scenario: Manual invocation
- **WHEN** a user runs `uv run python skills/word-to-md/scripts/docx_to_md.py --source <docx> --target-folder <dir>`
- **THEN** the same rule-compliant output is produced as when the skill is invoked by an agent

### Requirement: No stray HTML entities or diagram conversion
The system SHALL NOT leave HTML entities (e.g. `&amp;`) in generated markdown output, and SHALL NOT attempt raster-diagram-to-Mermaid conversion or photo-vs-diagram classification.

#### Scenario: Entities clean, images pass through unmodified
- **WHEN** converting the sample document
- **THEN** no generated file contains an HTML entity, and both extracted images remain as image references with their original relative paths and inline width/height attributes preserved
