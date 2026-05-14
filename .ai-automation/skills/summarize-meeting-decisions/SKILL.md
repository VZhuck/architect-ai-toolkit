---
name: summarize-meeting-decisions
description: "Summarize a meeting transcript into technical decisions, ask which to log, and update ADL using ADL_PATH."
argument-hint: "meetingFilePath (required path to meeting transcript file)"
---

# Summarize Meeting Decisions

Use this skill to summarize a meeting transcript, identify technical decisions, and update the Architecture Decision Log (ADL).

## Parameters

- **meetingFilePath**: Required path to the meeting transcript file.

## Required Environment Variable

- **ADL_PATH**: Absolute or repository-relative path to the decision log markdown file.

## Workflow

Execute all steps in order without pausing, except where explicitly required to ask the user.

### 1. Validate inputs and load files

```powershell
$meetingFilePath = '{meetingFilePath}'
& "$PSScriptRoot\load-env-vars.ps1" -EnvPath (Join-Path $PSScriptRoot '.env')

if ([string]::IsNullOrWhiteSpace($env:ADL_PATH)) {
  throw 'ADL_PATH environment variable is required.'
}

if (-not (Test-Path -Path $meetingFilePath -PathType Leaf)) {
  throw "meetingFilePath not found: $meetingFilePath"
}

try {
  $resolvedAdlPath = (Resolve-Path -Path $env:ADL_PATH -ErrorAction Stop).Path
} catch {
  # ADL may be intentionally new; resolve to absolute path relative to repo when possible.
  $resolvedAdlPath = [System.IO.Path]::GetFullPath($env:ADL_PATH)
}

```

If `ADL_PATH` points to a non-existing file, create it with a markdown title and a decisions table header before appending rows.

### 2. Extract technical decisions

Analyze the meeting content and extract only technical decisions (exclude open questions, action items, and status updates).

Build a markdown table with this exact header format:

| **Area** | **Problem** | **Decision** | **Date** | **Approvers** |
| -------- | ----------- | ------------ | -------- | ------------- |

Rules:

- One decision per row.
- `Area` should be a concise technical domain label (for example: Security, Data Flow, API, Infra, Monitoring).
- `Problem` should describe the specific technical issue being solved.
- `Decision` should describe what was decided.
- If `Decision`, `Date`, or `Approvers` cannot be identified, use `TBD`.
- If no technical decisions are present, return an empty result and explicitly say none were identified.
- If decision decision discussed on multiple occurance, terat last decisionsas final. Fianl decision also could be "need to be discussed further" if no final decision was made.

### 3. Ask user which decisions to log

This is a required user confirmation step.

1. Present extracted decisions as a numbered list and as the markdown table.
2. Ask: "Which decision numbers should be added to ADL_PATH?"
3. Accept comma-separated indexes or `all`.
4. If user provides invalid indexes, ask once more with valid options.

### 4. Update ADL

1. Append only user-selected decisions to the file at `ADL_PATH`.
2. Preserve existing ADL content and style.
3. Avoid duplicates by skipping rows where `Area + Problem + Decision` already exists.
4. Keep markdown table formatting valid.
5. If ADL has multiple sections, append to the main decisions table section or create a new section named `## Decisions`.

### 5. Return result

Return:

- Extracted decisions table.
- Which decisions were selected.
- ADL update summary:
  - Added count
  - Skipped duplicate count
  - Final ADL path

## Error handling

- Throw a clear error if `meetingFilePath` is missing or unreadable.
- Throw a clear error if `ADL_PATH` is missing.
- Throw a clear error if ADL update fails.
