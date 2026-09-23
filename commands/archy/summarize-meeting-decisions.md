---
description: "Summarize a meeting note into technical decisions and log user-confirmed ones to the ADL via the archy-summarize-meeting-decisions skill."
argument-hint: "[meetingFilePath] [--adl-path <path>]"
---

# /archy:summarize-meeting-decisions

Parse `$ARGUMENTS`:
1. Extract `--adl-path <path>` if present (the value is the next token).
2. Whatever single token remains, if any, is `meetingFilePath`. If nothing remains, `meetingFilePath` is omitted.

Examples:
```
/archy:summarize-meeting-decisions                                        # no meetingFilePath, no --adl-path
/archy:summarize-meeting-decisions notes/2026-08-06-standup.md
/archy:summarize-meeting-decisions notes/2026-08-06-standup.md --adl-path sad/07.Decision-Acceptance-Board.md
/archy:summarize-meeting-decisions --adl-path sad/07.Decision-Acceptance-Board.md
```

Invoke the `archy-summarize-meeting-decisions` skill with the resolved `meetingFilePath` (or none, if omitted — the skill itself lists `.env`'s `MEETING_NOTES_FOLDER` and asks the user to pick a file) and `--adl-path` (or none, if omitted — the skill falls back to `.env`'s `ADL_PATH`). This command does not read `.env` directly. Relay the skill's final extracted-decisions table, the user's selection, and the ADL update summary back to the user.
