---
name: convert-md-to-word
description: "Convert ordered Markdown files from a source folder into a single Word document using pandoc."
argument-hint: "sourceMdDir (optional), targeOutputDir (optional), wordDocName (optional)"
---

# Convert Markdown To Word

Use this skill to convert Markdown files from a provided folder into a single `.docx` document by running the helper script at `.ai-automation/scripts/covert-markdown-to-word.ps1`.

## Parameters
- **sourceMdDir**: Optional source markdown folder. Default: `./sad`
- **targeOutputDir**: Optional output folder for the Word document. Default: `./.workflow-temp/sad-word/`
- **wordDocName**: Optional output file name. Default: `sad.docx`

## Workflow

### 1. Run the helper script
Use the repository helper script directly.

```powershell
$sourceMdDir = '{sourceMdDir}'
$targeOutputDir = '{targeOutputDir}'
$wordDocName = '{wordDocName}'

& .ai-automation/scripts/covert-markdown-to-word.ps1 -SourceMdDir $sourceMdDir -TargeOutputDir $targeOutputDir -WordDocName $wordDocName

Write-Line "Markdown files from '$sourceMdDir' have been converted to Word document '$wordDocName' in folder '$targeOutputDir'."
```

Notes:
- If parameters are omitted, script defaults are used.
- The script resolves source and target directories, executes `pandoc` from inside the source directory, creates a temporary `.docx`, and then moves it to the target folder.

## Return Value
- Returns the final generated Word document path through script output logs.
- Throws an error if pandoc is missing, no markdown files are found, or conversion fails.
