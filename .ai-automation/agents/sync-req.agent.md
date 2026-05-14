---
description: "Use when syncing Azure Boards capability and feature work items into functional-requirements-raw, comparing them with repository versions, and updating req-sync-log.md."
name: "sync-req"
tools: [read, edit, search, execute]
argument-hint: "ADO_CAPABILITY_ID (Capability ID), ADO_FEATURE_IDS (comma-separated feature work item IDs)"
user-invocable: true
disable-model-invocation: false
---

# Sync Requirements

Use this agent to synchronize Azure Boards work items into `functional-requirements-raw/` using the repository rules in `.ai-automation/instructions/functional-requirements-raw.instructions.md`.

Critical Rules:
- only update `functional-requirements-raw/` files, do not change other repository folders or files.

## Workflow
Fail whole workflow any step fails

### 1. Backup `functional-requirements-raw` requirements files
- use `backup-folder` skill to backup files from `functional-requirements-raw/` to `.workflow-temp/functional-requirements-raw-temp/`

### 2. Load ADO requirements and generate markdown files
- use `load-req` skill to load ADO requirements and generate markdown files in `functional-requirements-raw` folder

### 3. Compare corresponding files `functional-requirements-raw` (source of truth) and `.workflow-temp/functional-requirements-raw-temp/` folders

- read files from `functional-requirements-raw/` and its counterpart from `.workflow-temp/functional-requirements-raw-temp/` (if exists) into powershell memory. Use following script:
```powershell
    $repoRoot = (Get-Location).Path
    $rawRequirementsPath = Join-Path $repoRoot 'functional-requirements-raw'
    $rawRequirementsTempPath = Join-Path $repoRoot '.workflow-temp' 'functional-requirements-raw-temp'

    $rawRequirementsFiles = & .ai-automation\scripts\read-folder-files.ps1 -FolderPath $rawRequirementsPath | ConvertTo-Json

    $backupRequirementsFiles = & .ai-automation\scripts\read-folder-files.ps1 -FolderPath $rawRequirementsTempPath | ConvertTo-Json
```
- Use $rawRequirementsFiles & $backupRequirementsFiles to generate `req-sync-log.md` with LLM. focus on content comparizon rather than formatting differences. The goal is to identify meaningful content changes that would require updating the status in `req-sync-log.md` to "updated". If there are no meaningful content changes, the status should remain "unchanged".

<!-- ### 4. Clean `.workflow-temp/functional-requirements-raw-temp` folder
- after comparison is complete, clean the backup folder

```powershell
$repoRoot = (Get-Location).Path
$rawRequirementsTempPath = Join-Path $repoRoot '.workflow-temp' 'functional-requirements-raw-temp'

& .ai-automation\scripts\remove-folder-files.ps1 -FolderPath $rawRequirementsTempPath
``` -->

## Output Format
- Return a concise status summary of the sync result.
- Return a `Files updated` list containing every repository file created, updated, or deleted during the process.
- Return `No repository files updated.` when the sync completes without file changes.