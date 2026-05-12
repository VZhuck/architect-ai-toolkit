<#
.SYNOPSIS
    Load environment variables from a .env file into the current process scope.

.PARAMETER EnvPath
    Path to the .env file. Defaults to .env in the repository root (two levels
    up from this script).

.EXAMPLE
    . .\load-env-vars.ps1
.EXAMPLE
    .\load-env-vars.ps1 -EnvPath 'C:\repo\.env'
#>

[CmdletBinding()]
param(
    [string] $EnvPath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path '.env')
)

$ErrorActionPreference = 'Stop'

# Help Function
function Import-EnvFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$EnvPath
    )

    Write-Host "Loading env variables from $EnvPath ..."
    if (-not (Test-Path $EnvPath)) { throw "ERROR:true; .env file not found at $EnvPath" }

    Get-Content $EnvPath | ForEach-Object {
        if ([string]::IsNullOrWhiteSpace($_) -or $_.Trim().StartsWith('#') -or ($_ -notmatch '=')) { return }
        $name, $value = $_.Split('=', 2)
        [System.Environment]::SetEnvironmentVariable($name.Trim(), $value, 'Process')
    }

    if (-not (Test-Path Env:ADO_ORGANIZATION_URL) -or -not (Test-Path Env:ADO_PAT)) {
        throw 'ERROR:true; env variables ADO_ORGANIZATION_URL and/or ADO_PAT are NOT available'
    }

    if (-not (Test-Path Env:ADO_CAPABILITY_ID)) {
        throw 'ERROR:true; env variables ADO_CAPABILITY_ID is NOT available'
    }

    Write-Host '  Env variables loaded.'
    return $true
}

# Execute when invoked directly (not dot-sourced)
if ($MyInvocation.InvocationName -ne '.') {
    Import-EnvFile -EnvPath $EnvPath
}


