<#
.SYNOPSIS
    Validates that the environment is ready to call Azure DevOps.

.DESCRIPTION
    Performs the following checks and fails fast on the first error:
      1. Azure CLI (`az`) is installed and functional.
      2. The `azure-devops` CLI extension is installed.
      3. Required environment variables `ADO_ORGANIZATION_URL` and `ADO_PAT` are set.
      4. The provided PAT can authenticate against the ADO organization.

    Assumes following env variables: ADO_ORGANIZATION_URL, ADO_PAT

.OUTPUTS
    [bool] $true on success. Throws a terminating error otherwise.

.EXAMPLE
    & .\test-ado-prerequisites.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

Write-Host '[1/4] Checking if az cli installed...'
az --version 1> $null 2> $null
if ($LASTEXITCODE -ne 0) { throw 'ERROR:true; Azure CLI is not installed or not functional.' }

Write-Host '[2/4] Checking if az devops extension is installed...'
az extension show --name azure-devops 1> $null 2> $null
if ($LASTEXITCODE -ne 0) { throw 'ERROR:true; azure-devops CLI extension is not installed.' }

Write-Host '[3/4] Resolving ADO Organization & PAT evn vars...'
if (-not (Test-Path Env:ADO_ORGANIZATION_URL) -or -not (Test-Path Env:ADO_PAT)) {
    throw 'ERROR:true; env variables ADO_ORGANIZATION_URL and/or ADO_PAT are NOT available'
}

Write-Host '[4/4] Verifying ADO access...'
$env:ADO_PAT | az devops login --organization $env:ADO_ORGANIZATION_URL 1> $null 2> $null
if ($LASTEXITCODE -ne 0) { throw "ERROR:true; Can't login into ADO." }

Write-Host 'Prerequisites OK.'
return $true