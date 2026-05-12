<#
.SYNOPSIS
    Removes all files from a specified folder.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$FolderPath
)

Write-Host 'Cleaning functional-requirements-raw folder...'

if (-not (Test-Path $FolderPath)) {
    New-Item -ItemType Directory -Path $FolderPath | Out-Null
    Write-Host '  Created functional-requirements-raw directory.'
    return
}

Get-ChildItem -Path $FolderPath -File -Force | Remove-Item -Force
Write-Host "Folder cleaned: $FolderPath"

return $true