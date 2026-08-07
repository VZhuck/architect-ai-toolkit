---
name: summarize-meeting-decisions
description: "Summarize a meeting note into technical decisions, semantically flag likely duplicates against the existing ADL, ask which to log, and append confirmed rows via a Python script."
argument-hint: "meetingFilePath (optional path to a meeting note; falls back to listing .env's MEETING_NOTES_FOLDER and asking which file to use), adlPath (optional path to the ADL file; falls back to .env's ADL_PATH)"
---

# Summarize Meeting Decisions

Read a meeting note, extract technical decisions, and log user-confirmed ones to the Architecture Decision Log (ADL). Ported from the legacy PowerShell rule at `.ai-automation/skills/summarize-meeting-decisions/SKILL.md` onto this repo's Python skill convention (see `md-to-word`, `load-raw-req`) — no PowerShell code. File mechanics are a small Python script; extracting decisions and judging duplicates is Claude's job, not the script's.

## Parameters

- **meetingFilePath** (optional): path to a specific meeting note. If omitted, the skill lists the files found in `.env`'s `MEETING_NOTES_FOLDER` and asks the user to pick one — it never auto-selects "most recent" and never tracks a freshness/sync-log of previously processed notes.
- **adlPath** (optional): path to the ADL markdown file. If omitted, falls back to `.env`'s `ADL_PATH`. If the resolved file doesn't exist yet, it is created on first write with a title and the standard decisions table header.

## Workflow

Execute all steps in order without pausing, except where a user confirmation is explicitly required.

### 1. Resolve inputs

```bash
uv run python skills/summarize-meeting-decisions/scripts/resolve_paths.py
```

If `meetingFilePath` and/or `adlPath` were provided by the caller, add the matching flag(s):

```bash
uv run python skills/summarize-meeting-decisions/scripts/resolve_paths.py --meeting-file "{meetingFilePath}" --adl-path "{adlPath}"
```

Do not pass `--meeting-file` or `--adl-path` with an empty string — the script treats any given value as an explicit path, not "not given". Omit the flag entirely when the parameter wasn't provided by the caller; the script applies the `.env` fallbacks itself (`MEETING_NOTES_FOLDER`, `ADL_PATH`).

- If `meetingFilePath` was not given, the script prints the candidate files found in `MEETING_NOTES_FOLDER`. Present that list to the user and ask which one to summarize. This is a required confirmation step — do not guess.
- If the script raises because no meeting note could be resolved at all (no argument, no usable `MEETING_NOTES_FOLDER`), or because an explicit `meetingFilePath` doesn't exist, or because no `adlPath` could be resolved (no argument, no `.env` `ADL_PATH`), stop and report the specific error — do not proceed or fabricate a path.
- Once resolved, read the meeting note's full content and the current content of the ADL file (empty/non-existent is fine — treat as "no existing decisions").

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
- If the same topic is discussed and decided more than once in the note, treat the last occurrence as final — the final decision may itself be "needs further discussion" rather than a resolved outcome.
- If no technical decisions are present, stop here and explicitly tell the user none were identified. Do not continue to step 3.

### 3. Flag likely duplicates against the existing ADL

Read the ADL content loaded in step 1. For each candidate decision from step 2, compare it against the ADL's existing rows using semantic judgment — does an existing row already describe the same decision, even if worded differently? This is a judgment call, not a string-equality check: ADL rows may have been written by hand with different phrasing than what this skill would generate for the same underlying decision, so exact-match comparison would systematically miss real duplicates.

Mark each candidate that looks like it duplicates an existing row, noting which existing row it matches. If the ADL has no existing decisions table (new or empty file), no candidates are flagged.

### 4. Ask user which decisions to log

This is a required user confirmation step.

1. Present extracted decisions as a numbered list and as the markdown table, with duplicate flags from step 3 shown alongside the candidates they apply to.
2. Ask: "Which decision numbers should be added to the ADL?"
3. Accept comma-separated indexes or `all`.
4. If the user provides invalid indexes, ask once more with the valid range.

### 5. Update the ADL

Run the write script once per confirmed row (or batch them in one call), using the resolved `adlPath` from step 1:

```bash
uv run python skills/summarize-meeting-decisions/scripts/update_adl.py --adl-path "{resolved adlPath}" --row "Area|Problem|Decision|Date|Approvers" --row "..."
```

The script performs no duplicate comparison itself — it appends exactly the rows passed to it. It creates the file (with title + table header) if it didn't already exist, and creates a `## Decisions` section if the existing file has none.

### 6. Return result

Report back:

- The extracted decisions table (from step 2).
- Which decision numbers were selected in step 4.
- Update summary: added count, count the user chose not to log, and the final resolved ADL path.

## Error handling

- If `meetingFilePath` is given but doesn't exist, or if it's omitted and `MEETING_NOTES_FOLDER` is unset/not a directory/empty, stop with a clear, specific error naming which case occurred.
- If `adlPath` can't be resolved from either the argument or `.env`'s `ADL_PATH`, stop with a clear error.
- If the ADL write fails (e.g. permissions), surface the script's error rather than reporting success.
