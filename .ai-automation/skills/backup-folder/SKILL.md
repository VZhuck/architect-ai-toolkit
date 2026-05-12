---
name: backup-folder
description: "Use when backing up files from a source folder to a backup folder. Cleans backup folder first, creates it if needed, then moves all files from source to backup."
argument-hint: "sourcePath (source folder path), backupPath (backup folder path)"
---

# Backup Folder

Use this skill to backup files from a source folder to a backup folder with a clean workflow.

## Parameters
- **sourcePath**: Path to the source folder containing files to backup
- **backupPath**: Path to the backup folder where files will be moved

## Workflow

### 1. Clean backup folder & create if needed
Remove any existing files in the backup folder, then ensure the backup folder exists:

```powershell
$sourcePath = '{sourcePath}'
$backupPath = '{backupPath}'

# Clean backup folder first
& .ai-automation\scripts\remove-folder-files.ps1 -FolderPath $backupPath

# Create backup folder if it doesn't exist
if (-not (Test-Path $backupPath)) {
    New-Item -ItemType Directory -Path $backupPath | Out-Null
}
```

### 2. Move files from source to backup
Move all files from the source folder to the backup folder:

```powershell

Get-ChildItem -Path $sourcePath -File -Force -ErrorAction SilentlyContinue |
    Move-Item -Destination $backupPath -Force

```

## Return Value
- Returns `$true` on successful completion
- Throws error if any step fails
