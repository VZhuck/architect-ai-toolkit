---
description: "Validate a refined NFR draft and promote it to the target Non-Functional Requirements document via the aait-nfr skill."
argument-hint: "[--nfr-path <path>]"
---

# /aait:nfr-publish

Parse `$ARGUMENTS`:
1. Extract `--nfr-path <path>` if present (the value is the next token).
2. No other arguments are accepted.

Examples:
```
/aait:nfr-publish
/aait:nfr-publish --nfr-path sad/08.Non-Functional-Requirements.md
```

Invoke the `aait-nfr` skill in its **publish** phase with `--nfr-path` (or none, if omitted — the skill's script resolves the `.env` `NFR_PATH` fallback, then falls back to listing `sad/`). This command does not read `.env` directly.

The skill re-reads the catalogs, renders the draft, merges it into any existing document by identifier while holding locked priorities, runs the validator, shows the diff, and promotes **only on a clean validation**.

Relay the validation result and the diff to the user. If validation fails, relay every failing check and its row, and confirm that the target document was left untouched. Running this command before refining is safe by design — an under-refined draft fails validation rather than reaching the deliverable. Do not work around a failing check by editing the target document directly.

This is the only command that writes to the target NFR document.
