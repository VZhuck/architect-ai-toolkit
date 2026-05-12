<#
.SYNOPSIS
    Fetch a single Azure DevOps work item.

.DESCRIPTION
    Calls `az boards work-item show` for the given work item id and returns
    an object containing id, title, descriptionHtml, and acceptanceCriteriaHtml.

    Requires $env:ADO_ORGANIZATION_URL to be set and `az` to be authenticated.

.PARAMETER WorkItemId
    Azure DevOps work item ID.

.OUTPUTS
    AdoWorkItem object.
#>
using module .\AdoWorkItem.psm1

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$WorkItemId
)

$ErrorActionPreference = 'Stop'

Write-Host "Fetching ADO work item $WorkItemId..."

$workItem = az boards work-item show --id $WorkItemId --organization $env:ADO_ORGANIZATION_URL --output json | ConvertFrom-Json
if (-not $workItem) { throw "ERROR:true; Unable to fetch work item $WorkItemId" }

return [AdoWorkItem]::new($workItem)
