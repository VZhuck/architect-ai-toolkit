## Why

The toolkit has a legacy PowerShell rule (`.ai-automation/skills/summarize-meeting-decisions/SKILL.md`) for turning a meeting transcript into logged Architecture Decision Log (ADL) rows, but the repo has moved to a Python-based skill/command convention (see `load-raw-req`, `md-to-word`) with real files under `./skills` and `./commands`, symlinked into `.claude/`. There is no equivalent skill in the new convention yet, so meeting-decision logging currently has no working path in this toolkit.

## What Changes

- Add a new `summarize-meeting-decisions` skill (`./skills/summarize-meeting-decisions/`) that reads a meeting note, extracts technical decisions into a markdown table, and appends user-selected rows to an ADL file — ported from the legacy PowerShell rule with no PowerShell code anywhere; file mechanics are a small Python script, decision extraction and duplicate judgment are done by Claude.
- Add a matching `/summarize-meeting-decisions` command (`./commands/summarize-meeting-decisions.md`) that parses optional `meetingFilePath`/`adlPath` arguments and invokes the skill, mirroring `commands/load-raw-req.md` and `commands/md-to-word.md`.
- Add symlinks `.claude/skills/summarize-meeting-decisions -> ../../skills/summarize-meeting-decisions` and `.claude/commands/summarize-meeting-decisions.md -> ../../commands/summarize-meeting-decisions.md`.
- Add a new `MEETING_NOTES_FOLDER` key to `.env.example`, documented near the existing `ADL_PATH` key, as the fallback source of meeting notes when no path is given.
- Behavior change from the legacy rule: duplicate detection against the existing ADL table is a semantic judgment made by Claude while presenting candidates for user confirmation, not a scripted exact-match comparison — because ADL rows may be hand-written with different wording than the skill would generate for the same decision, so exact-match string comparison would miss real duplicates.
- Behavior change from the legacy rule: when no `meetingFilePath` is given, the skill lists files found in `MEETING_NOTES_FOLDER` and asks the user to pick one, rather than auto-selecting a "most recent" file or tracking a freshness/sync log.

## Capabilities

### New Capabilities
- `meeting-decision-logging`: reading a meeting note, extracting technical decisions into a standard table, reconciling them against an existing ADL file with semantic duplicate detection, and appending user-confirmed rows — exposed via the `summarize-meeting-decisions` skill and its matching slash command.

### Modified Capabilities
(none — no existing spec's requirements change)

## Impact

- New files: `skills/summarize-meeting-decisions/SKILL.md`, `skills/summarize-meeting-decisions/scripts/*.py`, `commands/summarize-meeting-decisions.md`, plus their `.claude/` symlinks.
- Modified files: `.env.example` (new `MEETING_NOTES_FOLDER` key).
- No changes to existing skills, commands, or specs. No new third-party dependencies expected — path/env resolution and ADL table read/write can use the standard library, consistent with `md-to-word`'s plain `key=value` `.env` parsing.
