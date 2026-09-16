---
description: "Mine requirements, meeting notes, or transcripts for non-functional requirement signals and draft a classified NFR document via the aait-nfr skill."
argument-hint: "[path] [--nfr-path <path>]"
---

# /aait:nfr-detect

Parse `$ARGUMENTS`:
1. Extract `--nfr-path <path>` if present (the value is the next token).
2. Whatever single token remains, if any, is `path` — the directory or file to analyze. If nothing remains, `path` is omitted.

Examples:
```
/aait:nfr-detect docs/rfp
/aait:nfr-detect docs/rfp/requirements.docx
/aait:nfr-detect docs/rfp --nfr-path sad/08.Non-Functional-Requirements.md
/aait:nfr-detect                                  # no path — the skill asks which sources to analyze
```

Invoke the `aait-nfr` skill in its **detect** phase with the resolved `path` (or none, if omitted) and `--nfr-path` (or none, if omitted). This command does not read `.env` directly — the skill's script resolves the `NFR_PATH` fallback, and falls back again to listing `sad/` for the user to choose from.

If `path` was omitted, the skill asks which directory or file to analyze. Never guess it on the skill's behalf.

Relay the skill's candidate funnel, catalog coverage grid, and classification gate back to the user, and wait for their answer — the gate runs in this conversation, not in a subagent. Do not surface raw source file contents here; the skill's mining subagents keep those isolated.

This phase writes only the draft and trace files under `ai-workflow/nfr/`. It never writes the target NFR document.
