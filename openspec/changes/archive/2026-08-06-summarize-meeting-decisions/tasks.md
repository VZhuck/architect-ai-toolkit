## 1. Scaffolding

- [x] 1.1 Create `skills/summarize-meeting-decisions/` directory with `SKILL.md` and a `scripts/` subfolder.
- [x] 1.2 Create `commands/summarize-meeting-decisions.md`.
- [x] 1.3 Create symlink `.claude/skills/summarize-meeting-decisions -> ../../skills/summarize-meeting-decisions`.
- [x] 1.4 Create symlink `.claude/commands/summarize-meeting-decisions.md -> ../../commands/summarize-meeting-decisions.md`.
- [x] 1.5 Add `MEETING_NOTES_FOLDER` key to `.env.example`, documented near the existing `ADL_PATH` key.

## 2. Path/env resolution script

- [x] 2.1 Implement `skills/summarize-meeting-decisions/scripts/resolve_paths.py` with an importable function that resolves `meetingFilePath` (arg, else lists `MEETING_NOTES_FOLDER` contents for the caller to choose from) using plain `key=value` `.env` parsing (no `python-dotenv`), matching `md_to_word.py`'s resolution style.
- [x] 2.2 In the same script, resolve `adlPath` (arg, else `.env`'s `ADL_PATH`).
- [x] 2.3 Raise clear, distinct errors for: explicit meeting path not found; no meeting path and no usable `MEETING_NOTES_FOLDER`; no ADL path resolvable from either source.
- [x] 2.4 Add a CLI entry point so the script is runnable standalone (`uv run python skills/summarize-meeting-decisions/scripts/resolve_paths.py ...`), matching the `md_to_word.py` pattern.

## 3. ADL write script

- [x] 3.1 Implement `skills/summarize-meeting-decisions/scripts/update_adl.py` with an importable function that appends given decision rows to the ADL file's decisions table.
- [x] 3.2 Handle ADL file not existing yet: create it with a markdown title and the `Area | Problem | Decision | Date | Approvers` table header before appending.
- [x] 3.3 Handle ADL file existing but with no `## Decisions` section: create that section with the standard header before appending.
- [x] 3.4 Handle ADL file existing with a decisions table already: append rows without altering existing rows or formatting.
- [x] 3.5 Ensure the function performs no duplicate comparison of any kind — it only appends exactly the rows it's given.
- [x] 3.6 Surface write failures (e.g. permission errors, invalid path) as clear exceptions rather than silently failing.

## 4. Skill workflow (SKILL.md)

- [x] 4.1 Write frontmatter (`name`, `description`, `argument-hint`) following the `md-to-word`/`load-raw-req` SKILL.md convention.
- [x] 4.2 Document parameters: `meetingFilePath` (optional) and `adlPath` (optional), with their fallback rules.
- [x] 4.3 Write the workflow steps: resolve paths (script) → extract decisions into the standard table (Claude) → read existing ADL table and semantically flag likely duplicates (Claude) → present numbered list/table with duplicate flags and ask which to log → run the write script with confirmed rows → report result.
- [x] 4.4 Port the extraction field rules from the legacy rule: exclude open questions/action items/status updates; `TBD` fallback for unresolved `Decision`/`Date`/`Approvers`; last-decision-wins on revisited topics; explicit "none identified" result with no further steps when no decisions are found.
- [x] 4.5 Document the required confirmation step: accept comma-separated indexes or `all`; re-prompt once with valid options on invalid input; never write without confirmation.
- [x] 4.6 Document error handling: missing meeting file, no folder fallback available, no ADL path resolvable, ADL write failure — each with a clear, distinct error message.
- [x] 4.7 Document the final report contents: extracted table, selected indexes, added count, skipped-by-user-choice count, final ADL path.

## 5. Command (summarize-meeting-decisions.md)

- [x] 5.1 Write frontmatter (`description`, `argument-hint`) following `load-raw-req.md`/`md-to-word.md`'s convention.
- [x] 5.2 Parse `$ARGUMENTS` into optional `meetingFilePath` and `adlPath`, invoke the skill with whatever was parsed (or neither), and relay its final result back to the caller without surfacing intermediate mechanics.

## 6. Verification

- [x] 6.1 Manually run the skill against a sample meeting note (e.g. add one under `test-data/`) with no `meetingFilePath` and a configured `MEETING_NOTES_FOLDER`, confirming the file picker prompt appears.
- [x] 6.2 Manually run the skill against a sample meeting note with an explicit `meetingFilePath`, confirming the folder fallback is skipped entirely.
- [x] 6.3 Manually run the skill twice against the same ADL file with a paraphrased duplicate decision, confirming the duplicate is flagged for user judgment rather than silently skipped or silently duplicated.
- [x] 6.4 Confirm `.claude/skills/summarize-meeting-decisions` and `.claude/commands/summarize-meeting-decisions.md` resolve correctly as symlinks (`ls -la`).
