---
description: "Resolve open questions, agree measurable targets, and set priorities on a drafted NFR document via the aait-nfr skill."
argument-hint: "[--nfr-path <path>]"
---

# /aait:nfr-refine

Parse `$ARGUMENTS`:
1. Extract `--nfr-path <path>` if present (the value is the next token).
2. No other arguments are accepted — the sources were already mined in the detect phase.

Examples:
```
/aait:nfr-refine
/aait:nfr-refine --nfr-path sad/08.Non-Functional-Requirements.md
```

Invoke the `aait-nfr` skill in its **refine** phase with `--nfr-path` (or none, if omitted — the skill's script resolves the `.env` `NFR_PATH` fallback, then falls back to listing `sad/`). This command does not read `.env` directly.

The skill reads the draft and trace resolved from `nfrPath`. If no draft exists, the detect phase has not run — relay that and offer `/aait:nfr-detect` rather than mining silently.

This phase runs three gates in order: open questions, measurable targets, priorities. **Every gate runs in this conversation.** Relay each one to the user and wait for an answer before continuing — a subagent cannot ask a question, so no gate may be delegated. Each confirmed answer is written into the draft immediately, so an interruption never loses a decision the user already made.

This phase writes only the draft and trace files. It never writes the target NFR document.
