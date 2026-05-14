---
name: load-req
description: "Load ADO requirements and generate markdown files in functional-requirements-raw folder following repository formatting rules."
argument-hint: "ADO_CAPABILITY_ID (Capability ID), ADO_FEATURE_IDS (comma-separated feature work item IDs)"
---

# Load Requirements

Use this skill to load Azure Boards capability and feature work items, then generate markdown files in `functional-requirements-raw/` folder.

## Parameters
- **ADO_CAPABILITY_ID**: Azure DevOps Capability work item ID
- **ADO_FEATURE_IDS**: Comma-separated list of Azure DevOps Feature work item IDs

## Workflow

### 1. Load ADO requirements into PowerShell memory
Fetch latest requirements from Azure Boards:

```powershell
$adoRequirementsLatest = & .ai-automation\scripts\get-ado-work-items.ps1 -CapabilityId {ADO_CAPABILITY_ID} -FeatureIds {ADO_FEATURE_IDS}

# Validate ADO object before proceeding
if (-not $adoRequirementsLatest -or -not $adoRequirementsLatest.Capability -or -not $adoRequirementsLatest.Features) {
    throw 'ADO requirements object validation failed.'
}
```

- `$adoRequirementsLatest` has this typed shape:
```powershell
AdoRequirements {
    Capability = AdoWorkItem {
        Id                 = '<capability-id>'
        Title              = '<title>'
        Description        = '<html description>'
        AcceptanceCriteria = '<html acceptance criteria>'
    }
    Features = @(
        AdoWorkItem {
            Id                 = '<feature-id>'
            Title              = '<title>'
            Description        = '<html description>'
            AcceptanceCriteria = '<html acceptance criteria>'
        }
    )
}
```
- Keep `$adoRequirementsLatest` in PowerShell memory for step 2

### 2. Generate markdown files and store them in `functional-requirements-raw` folder
- Create folder `functional-requirements-raw` if not exists
- Follow file naming and content rules from `.ai-automation/instructions/functional-requirements-raw.instructions.md`
- Do not generate `req-sync-log.md`
- Do not summarize or change the content from ADO work items; keep all details intact while converting from HTML to markdown and applying formatting rules. The goal is to have markdown files that are as close to the ADO content as possible, just in the correct format for the repository.
- Use LLM capability; do not use any scripts for markdown generation, as the formatting rules are complex and better handled with LLM's natural language capabilities


### 3. Clear powershell variable
- Clear powershell variable `$adoRequirementsLatest = $null` to remove ADO content from memory after markdown files are generated

## Return Value
- Returns `$true` on successful completion
- Throws error if any step fails
