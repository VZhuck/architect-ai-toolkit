<#
.SYNOPSIS
    Reads all *.md files from a folder into a hashtable in memory.

.DESCRIPTION
    Iterates the provided folder and loads each markdown file as
    filename -> raw content. Result is assigned to $script:FolderFiles
    and also returned as the script output.

.PARAMETER FolderPath
    Absolute or relative path to the folder containing *.md files.

.OUTPUTS
    [hashtable] keyed by file name with raw file content as value.

.EXAMPLE
    $files = & .\read-folder-files.ps1 -FolderPath 'C:\repo\functional-requirements-raw'
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$FolderPath
)

$ErrorActionPreference = 'Stop'

Write-Host "Reading *.md files from $FolderPath ..."

$files = @{}
if (Test-Path $FolderPath) {
    Get-ChildItem -Path $FolderPath -Filter '*.md' -File -ErrorAction SilentlyContinue | ForEach-Object {
        $files[$_.Name] = Get-Content -Path $_.FullName -Raw
    }
}

Write-Host "  Loaded $($files.Count) file(s)."
return $files
