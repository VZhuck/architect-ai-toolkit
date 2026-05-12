---
name: convert-word-to-md
description: "Convert a Word document into a Markdown file using pandoc, extracting media into a workflow temp folder."
argument-hint: "souceDoc (Word document path), destPath (optional destination folder)"
---

# Convert Word To Markdown

Use this skill to convert a Word document into Markdown using `pandoc`.

## Parameters
- **souceDoc**: Path to the source `.doc` or `.docx` file
- **destPath**: Optional destination path. If it ends with `.md`, it is treated as the output markdown file path. If omitted, default is `.workflow-temp/mddoc/<source-doc-name>.md`.

## Workflow

### 1. Convert the document with pandoc
Run the helper script below. It resolves the input document, creates the destination folder when needed, extracts embedded media into a folder named after the output file name (without extension), and writes the markdown file.

```powershell

# Example helper snippet if you need to derive file name from {destPath}
$destPath = '{destPath}'
$destinationFolder = Split-Path -Path $destPath -Parent


# Relative spurce path based on destination folder for example: ..\..\docs\file-name.docx 
$sourceDocRelativePath = [System.IO.Path]::GetRelativePath($destinationFolder, {souceDoc})
$destFileName = Split-Path -Path $destPath -Leaf
$mediaDirName = Split-Path -Path $destPath -Leaf -NoExtension


Push-Location -Path $destinationFolder
try {
    pandoc -t markdown $sourceDocRelativePath --extract-media=$mediaDirName --columns=1000 --to=markdown-simple_tables-multiline_tables-grid_tables -o $destFileName
    if ($LASTEXITCODE -ne 0) {
        throw "pandoc conversion failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$destPath 

```
- When `destPath` is omitted or empty, the script defaults to `.workflow-temp/mddoc/<source-doc-name>.md`.
- If `destPath` is a folder path, markdown output defaults to `<destPath>/<source-doc-name>.md`.

## Example

```powershell

Push-Location -Path '.workflow-temp/mddoc/'
try {
    pandoc -t markdown '../../docs/file-name.docx' --extract-media='file-name' --columns=1000 --to=markdown-simple_tables-multiline_tables-grid_tables -o file-name.md 
    if ($LASTEXITCODE -ne 0) {
        throw "pandoc conversion failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

```

This produces:
- `.workflow-temp/mddoc/file-name.md`
- `.workflow-temp/mddoc/file-name/` (folder containing extracted media) `

## Return Value
- Returns the full path to the generated markdown file on success
- Throws an error if `pandoc` is unavailable or conversion fails