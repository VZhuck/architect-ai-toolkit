---
name: sad-from-markdown
description: "Split a single solution-architecture markdown document into multiple markdown files by heading structure."
argument-hint: sourceMd (single markdown file), targetFolder (optional output folder)
---

# SAD From Markdown

Use this skill to convert one large markdown document into a folder of smaller markdown files organized by heading structure.

## When to Use

- Requested to split single markdown document into multiple files based on heading structure.
  - You need one file per major markdown section.
  - You need to markdown file as a sourceMd parameter and an optional targetFolder parameter for output.
  - You want to preserve images, but prefer Mermaid for diagrams where practical.
  - You need to turn HTML or text tables into markdown tables.

## Inputs

- `sourceMd`: Path to the source markdown file.
- `targetFolder`: Optional output folder.
  - Default: 'sad'
  - If provided, write all generated markdown files there.
- `sourceMediaFolder`: not provided in arguments, but can be calculated as the parent folder of `sourceMd` + `sourceMd` filename without extension. This is the convention used for media folder
  - If this folder exists, copy all media files to the target folder as well.
  - For example: if `sourceMd` is `.workflow-temp/mddoc/markdown-doc.md`, then `sourceMediaFolder` would be `.workflow-temp/mddoc/markdown-doc/`.

## Workflow

use workflow as described below. Do not prompt for confirmation at each step, but do check for expected conditions and file existence before proceeding to next step. If any issues are encountered, provide a clear error message indicating the problem.

### Split source markdown with @./scripts/split-markdown-by-heading.py script

- Execute script, which will programativcally split markdown document by H1 headings, creating one file per section.

  ```python
  # Activate virtual environment if not already active
  .\venv\Scripts\Activate.ps1

  # copy media files if sourceMediaFolder exists
  python .ai-automation/scripts/copy-dir.py --source-dir {sourceMediaFolder} --target-base-dir {targetFolder}

  # Split markdown by H1 headings
  python .ai-automation/scripts/split-markdown-by-heading.py --source-md {sourceMd} --target-folder {targetFolder} --headers "#"
  ```

- Do not apply any markdown formating logic yet

Move to next step `### Move related folder if present` to copy related media folder if exists

### Move related folder if present

1. Check if the parent folder of `{sourceMd}` contains a subfolder with the same name as the source file (without extension).
2. If such a subfolder exists, use the copy-dir.py script to copy the folder and all its files to the target location:
   ```python
  python .ai-automation/scripts/copy-dir.py --source-dir <source-folder-path> --target-base-dir {targetFolder}
   ```

Move to next steps to do post-processing on generated files (table of contents, fixing tables, images, links, etc.). Use LLM capabilities to intelligently update content and formatting as needed, but do not summarize or remove content. The goal is to preserve all original content while improving formatting and structure for the new multi-file format.

### Update index file with cross-file links

- Replace single-document anchor links with cross-file links
- use ordered List for H1 headers linking to files: `1. [Project Details](01.Project-Details.md)`
- use nested unordered list with proper numbered text prefix for H2, H3, H4, etc. headers: `- 1.1 [Business Drivers](01.Executive-Summary.md#business-drivers)`
- Include all headings and subheadings in the index file as a nested list

Example:

```markdown
1. [Executive Summary](01.Executive-Summary.md)


    - 1.1 [Business Drivers](01.Executive-Summary.md#business-drivers)
    - 1.2 [Approach](01.Executive-Summary.md#approach)

2. [Requirements](02.Requirements.md)


    - 2.1 [Functional Requirements](02.Requirements.md#functional-requirements)
    - 2.2 [NFR](02.Requirements.md#nfr)
```

### Read & update each file with LLM capabilities

- This is a required post-processing step after splitting and is NOT performed by `split-markdown-by-heading.py`.
- Apply this step to every generated file in the target folder.
- Use LLM as it can understand the content and make intelligent decisions how to better present content.
- Follow @../instructions/sad-sections.instructions.md
- Do NOT summarize. Do proper tables, images, diagrams, links conversion as described below to.
- Preserve empty lines between paragraphs. Do not collapse paragraph boundaries while reformatting content.

#### Tables Normalization - Decision & Conversion Guide

**STEP 1: Check BEFORE converting - Only keep HTML if ANY of these are true:**

- Table has merged cells (colspan/rowspan attributes)
- Table has nested tables inside cells
- Table structure cannot be represented in markdown (unusual layouts)

**STEP 2: If NONE of the above → CONVERT to Markdown immediately:**

- Use standard markdown pipe syntax: `| Header | Header |`
- Replace paragraph breaks within cells with `<br>` tags
- Replace multi-item lists with bullet pseudo-format: `- Item 1<br>- Item 2`
- Use proper alignment indicators: `|---|` (default), `|-:|` (right), `|:-|` (left)
- Remove ALL `<colgroup>`, `<col style=...>` tags and style attributes
- Remove table-level `style="width:100%"` attributes

**STEP 3: If ANY condition in STEP 1 matches → KEEP HTML:**

- Add explanatory comment IMMEDIATELY ABOVE the `<table>` tag
- Comment format: `<!-- HTML format: [specific reason] -->`
- always add empty line before and after HTML tables for proper markdown rendering
- Examples:
  - `<!-- HTML format: contains merged cells (colspan) -->`
  - `<!-- HTML format: contains nested tables -->`
  - `<!-- HTML format: complex cell structure -->`

#### Table Conversion Examples

✅ **CONVERT** - Multi-paragraph cells (use `<br>`):

```markdown
| Service | Purpose                                                     |
| ------- | ----------------------------------------------------------- |
| AWS S3  | Storage system<br>Highly durable<br>99.9% availability      |
| Lambda  | Compute layer<br>Scales automatically<br>Pay per invocation |
```

✅ **CONVERT** - List cells (use bullet pseudo-format):

```markdown
| Team  | Responsibilities                                                          |
| ----- | ------------------------------------------------------------------------- |
| TeamA | - Infrastructure management<br>- Security policies<br>- IAM configuration |
| TeamB | - skill <br>- will crate bulle A<br> - And bullet B                       |
```

❌ **KEEP HTML** - Merged cells (colspan/rowspan not supported in markdown):

```markdown
<!-- empty line is added before <table> even if does not exists -->

<!-- HTML format: contains merged cells (colspan) -->
<table>
  <tr><td colspan="2">Header spanning 2 columns</td></tr>
  <tr><td>Cell 1</td><td>Cell 2</td></tr>
</table>

<!-- empty line is added after <table> even if does not exists -->
```

#### Tables - Compliance Checklist

Before finalizing each file, verify:

- [ ] No HTML tables exist unless they have merged cells or nested tables
- [ ] All markdown tables have `<br>` for paragraph breaks (not HTML tags)
- [ ] All markdown tables use `|---|`, `|-:|`, or `|:-|` for alignment
- [ ] All HTML tables have explanatory comment ABOVE the `<table>` tag
- [ ] No `<colgroup>` or `<col style=...>` tags remain in markdown tables
- [ ] All column width information is removed from markdown tables
- [ ] No `&` HTML entities in markdown tables (use plain characters: `&` not `&amp;`)

#### Images & Diagrams

1. if image is not a diagram, leave as is but verify relative path is correct and file exists
2. if image is a diagram, attempt to match to existing file in `./diagrams/`:

- If match found, update path to point to `diagrams/filename.svg`
- if match not found, use LLM capability to convert to Mermaid diagram. If conversion fails or is uncertain, keep as image with a valid relative path

## Completion Criteria

The skill is complete when:

- the source markdown has been split into the expected file set
- the index/TOC file contains working cross-file links to all sections and subsections
- tables have been assessed:
  - Simple tables converted to markdown format
  - Tables with merged cells or inner tables kept as HTML with explanatory notes
  - no converted tables have lost content or meaning
- images have been normalized:
  - inline width/height attributes removed
  - relative paths verified as correct
  - external diagram files referenced from `./diagrams/` where matches exist
- no broken relative asset links remain in generated files
- empty lines between paragraphs are preserved across all generated files
