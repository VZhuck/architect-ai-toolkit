---
description: "Audit any Non-Functional Requirements document against the quality-attribute catalogs and the SAD section rules via the aait-nfr skill."
argument-hint: "[docPath] [--nfr-path <path>]"
---

# /aait:nfr-validate

Parse `$ARGUMENTS`:
1. Extract `--nfr-path <path>` if present (the value is the next token).
2. Whatever single token remains, if any, is `docPath` — the document to audit. If nothing remains, `docPath` is omitted.

Examples:
```
/aait:nfr-validate                                       # audits the resolved nfrPath
/aait:nfr-validate sad/08.Non-Functional-Requirements.md
/aait:nfr-validate ../other-project/nfr.md               # a document this pipeline did not produce
/aait:nfr-validate --nfr-path sad/08.Non-Functional-Requirements.md
```

Invoke the `aait-nfr` skill in its **validate** phase. When `docPath` is given, audit that document. Otherwise audit the resolved `nfrPath` — the skill's script applies the `.env` `NFR_PATH` fallback, then falls back to listing `sad/`. This command does not read `.env` directly.

The validator needs no sources, draft, or trace file, so it runs against any NFR document, including one produced elsewhere. It never modifies the document it audits.

Relay the report: failing checks with their rows, then warnings — `(proposed)` values pending confirmation, and locked priorities that could not be verified because the document has no git `HEAD` version yet. Add the judgement checks the script cannot make: whether each metric is genuinely measurable, and whether each business driver is genuinely a business outcome.
