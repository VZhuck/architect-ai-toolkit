<#
.SYNOPSIS
    Implements part of the sync-req agent workflow:
      1. Check prerequisites
    2. Read ADO work items into memory
    3. Return object representing latest requirements from ADO

.DESCRIPTION
    Designed to be invoked by the sync-req agent. Snapshot and cleanup of
    functional-requirements-raw are orchestrated by the agent workflow itself.

.PARAMETER CapabilityId
    Azure DevOps capability work item ID. Falls back to $env:ADO_CAPABILITY_ID.

.PARAMETER FeatureIds
    Comma-separated Azure DevOps feature work item IDs. Falls back to $env:ADO_FEATURE_IDS.

.PARAMETER RepoRoot
    Repository root path. Defaults to two levels up from this script.
#>

using module .\AdoRequirements.psm1

[CmdletBinding()]
param(
    [string]$CapabilityId,
    [string]$FeatureIds,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'

#1. Load Env Variables
& "$PSScriptRoot\load-env-vars.ps1" -EnvPath (Join-Path $RepoRoot '.env')

# 2. Validate Prerequisites
& "$PSScriptRoot\test-ado-prerequisites.ps1" 

# 3. Resolve input parameters with env var fallback
if ([string]::IsNullOrWhiteSpace($CapabilityId)) { $CapabilityId = $env:ADO_CAPABILITY_ID }
if ([string]::IsNullOrWhiteSpace($FeatureIds)) { $FeatureIds = $env:ADO_FEATURE_IDS }

# 4. Fetch ADO work items
$capability = & "$PSScriptRoot\fetch-ado-workitem.ps1" -WorkItemId $CapabilityId

$features = @()
foreach ($featureId in ($FeatureIds.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
    $features += & "$PSScriptRoot\fetch-ado-workitem.ps1" -WorkItemId $featureId
}

$adoRequirementsLatest = [AdoRequirements]::new($capability, $features)

# 5. Return latest ADO requirements (capability and features)
return $adoRequirementsLatest