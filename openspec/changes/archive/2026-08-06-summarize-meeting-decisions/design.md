## Context

The legacy rule (`.ai-automation/skills/summarize-meeting-decisions/SKILL.md`) implements this workflow in PowerShell against `.env` variables `ADL_PATH` and a required `meetingFilePath` argument. It does env resolution, file existence checks, decision extraction (LLM-driven), a required user confirmation step, and an exact-string-match dedupe before appending rows to the ADL file.

This toolkit has since standardized on a different convention for skill+command pairs (`load-raw-req`, `md-to-word`): real implementation files live under `./skills/<name>/` and `./commands/<name>.md`, with `.claude/skills/<name>` and `.claude/commands/<name>.md` as `../../`-relative symlinks back to them. Scripting is Python (`uv run python ...`), not PowerShell, and `.env` fallback resolution is done with plain `key=value` parsing (no `python-dotenv` dependency), matching `md-to-word/scripts/md_to_word.py`.

## Goals / Non-Goals

**Goals:**
- Port the legacy rule's meeting-decision-to-ADL workflow onto the current skill/command convention, in Python.
- Preserve the legacy rule's table schema (`Area | Problem | Decision | Date | Approvers`), extraction rules (TBD fallback, "last decision wins" on revisited topics), and required user-confirmation gate before any ADL write.
- Add a folder-based fallback for the meeting note input, since the legacy rule only supported a single required file argument.

**Non-Goals:**
- Not implementing any automatic "pick the most recent file" or freshness/sync-log tracking (like `load-raw-req`'s `req-sync-log.md`) for the meeting-notes folder — out of scope per the confirmed design; the user is always asked to pick.
- Not implementing string-based or fuzzy-text duplicate detection in a script — duplicate judgment is intentionally left to Claude's reasoning, not scripted.
- Not adding a new Python dependency (e.g. `python-dotenv`) for `.env` parsing.

## Decisions

### 1. Duplicate detection is a Claude reasoning step, not a script function
The legacy rule dedupes by exact match on `Area + Problem + Decision`. This change deliberately does not port that logic into the Python script. ADL rows can originate from two places — this skill's own extraction, and manual edits by a human — which are highly likely to describe the same decision with different wording. An exact-match script would systematically miss those duplicates while giving false confidence that dedup happened. Instead, the skill instructs Claude to read the ADL's existing table and semantically compare each candidate row against it, surfacing likely duplicates to the user before the confirmation step (step 3 below). The Python script that performs the write has no comparison logic at all — it appends exactly the rows the user confirmed.

**Alternatives considered:** normalized string comparison (trim/casefold) — rejected, still misses paraphrased duplicates and was explicitly called out during exploration as insufficient for this skill's real usage pattern (mixed automated + manual ADL entries).

### 2. Folder fallback lists and asks, rather than auto-selecting
When `meetingFilePath` is omitted, the skill reads `MEETING_NOTES_FOLDER` from `.env`, lists the files in it, and asks the user to pick one (or more, if useful) via a required confirmation step — rather than guessing "most recent by mtime" or building a sync-log of already-processed notes.

**Alternatives considered:** most-recently-modified auto-pick (simplest, but risks summarizing the wrong meeting silently); `load-raw-req`-style freshness tracking (more machinery than this skill's single-meeting-at-a-time use case justifies).

### 3. Script scope: path/env resolution and ADL file I/O only
A single Python script (mirroring `md_to_word.py`'s CLI-entry-point-plus-importable-function shape) handles:
- Resolving `meetingFilePath` (arg, else list `MEETING_NOTES_FOLDER` contents for the caller to choose from) and `adlPath` (arg, else `.env`'s `ADL_PATH`).
- Reading the ADL file's current content (for Claude to reason over in the dedupe step) and, later, appending confirmed rows and writing the file back — creating it with a title + table header if it doesn't exist yet.

Everything else (transcript reading, decision extraction, duplicate judgment, user prompts) stays in the skill's Claude-driven instructions, matching the split already established for `load-raw-req` (script does freshness/file mechanics, Claude/subagent does content work).

### 4. New `.env.example` key: `MEETING_NOTES_FOLDER`
Placed near the existing `ADL_PATH` key, since both back the same skill's fallback resolution.

## Risks / Trade-offs

- **[Risk]** Asking the user to pick a file every time (no auto-select) adds a confirmation round-trip even for the common "just summarize the meeting I just had" case. → **Mitigation**: passing `meetingFilePath` explicitly skips the picker entirely; this is a deliberate trade-off favoring correctness over convenience, matching the confirmed design decision.
- **[Risk]** Claude's semantic duplicate detection is not guaranteed to catch every paraphrase, and could also flag false positives. → **Mitigation**: duplicate flags are advisory — the user still explicitly selects which decision numbers to log, so a missed or over-eager flag doesn't silently corrupt the ADL.
- **[Risk]** `MEETING_NOTES_FOLDER` is a new required-for-fallback env key; existing `.env` files won't have it. → **Mitigation**: only needed when `meetingFilePath` is omitted; the skill errors clearly (per proposal's ported error handling) if neither is available, rather than failing silently.

## Migration Plan

No migration needed — this is a net-new skill/command pair with no interaction with existing skills. The legacy PowerShell rule under `.ai-automation/` is left untouched by this change (not deleted, not modified); retiring it is a separate decision outside this proposal's scope.

## Open Questions

None outstanding — folder-fallback behavior, env var naming, and dedupe strategy were resolved during exploration prior to this proposal.
