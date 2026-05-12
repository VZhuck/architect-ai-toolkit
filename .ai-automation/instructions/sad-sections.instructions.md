---
applyTo: "sad/**/*.md"
description: "Standards and conventions for markdown files in SAD (Solution Architecture Document) folders."
---

# SAD Section Files Standards

Use this instruction to verify and maintain consistent formatting in files under any `sad` folder.

## File Naming Format

Files must use kebab-case with section number prefix for reading order.

| Pattern               | Usage                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| `00.Index.md`         | Contains table of contents with links to other files and specific section of the target file       |
| `<n>.<H1-Title>.md`   | One file per H1 section (typically < ~500 lines)                                                   |
| `<n>.0.<H1-Title>.md` | When H1 and H2 sections are split: first file has H1 content, subsequent files have H2 subsections |
| `<n.n>.<H2-Title>.md` | H2 subsection in separate file (used for large sections > ~1000 lines)                             |

Naming rules:
- Use hyphens to separate words (kebab-case)
- Remove Windows-invalid characters (`\ : * ? " < > |`)
- Prefix with zero-padded section number (e.g., `01.`, `02.`, `03.1`)

## File Structure

### Heading Hierarchy
- Maintain consistent hierarchy within the file
- Only one H1 per file
- Add empty line before headings for better readability and proper markdown rendering

### Paragraph Spacing
- Always preserve empty lines between paragraphs
- Do not collapse paragraph boundaries into hard line breaks solely for wrapping

### Markdown Tables (Preferred)
- Use standard markdown table syntax for simple tabular data
- use proper alignment indicators (`|---|`, `|-:|`, `|:-|`) instead of html attributes
- use <br> to support multi-line and multi-paragraph content in markdown table when required
- colgroup styling can be removed when converting to markdown, but ensure that column structure is preserved for readability

### HTML Tables (only in exceptional cases)
- Use HTML `<table>` tags only when content requires:
  - cell merges does not supported by markdown tables (e.g., multi-column spans) 
  - Nested tables 
- Add explanatory note above HTML tables as comment. Example:  `<!-- This table uses HTML formatting to preserve complex multi-paragraph cell content -->`
- Add empty line before and after HTML tables for proper markdown rendering

### Internal Cross-File Links
- Link to other SAD files in same folder: `[File main header title](02.High-Level-Design.md)`
- Link to headings in other files: `[Section title](02.High-Level-Design.md#section-heading)`
- Anchor format: heading text in lowercase with hyphens replacing spaces
- Always verify anchor exists before creating link. 

### External Links

- Use full URLs for external references
- Example: `[ADO Item](https://dev.azure.com/...)`
- Preserve URLs from source document

## Images and Diagrams

### Image Paths

- Use relative paths from the current file
- Format: `![alt text](media/image-name.png)` or `![alt text](../diagrams/diagram-name.svg)`
- Preserve inline width/height styling attributes (e.g., `![alt text](url){: width="250" } `)
- Verify file exists at relative path
- Alt text should describe the diagram/image purpose Example: `![Conceptual View](media/image1.png)`


## Consistency Checks
Before finalizing files:

- ✓ File naming follows pattern (`<n>.<Title>.md`)
- ✓ Exactly one H1 heading at file start
- ✓ H2+ headings have consistent hierarchy
- ✓ All images have relative paths and exist
- ✓ All cross-file links have correct anchors
- ✓ Tables are either markdown (simple) or HTML with explanatory note (complex)
- ✓ Empty lines between paragraphs are preserved for readability
