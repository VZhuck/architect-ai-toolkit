# NFR Trace — {document name}

Working provenance for the Non-Functional Requirements document. **Not a deliverable** — never published, never converted to Word, never placed in `sad/`. Deleting this file loses the audit trail but does not break the pipeline.

- Target document: `{nfrPath}`
- Draft: `{draftPath}`
- Sources analyzed: {n} files under `{path}`
- Last run: {date}

## Evidence

One row per requirement in the draft, carrying the verbatim sentence it came from so a reviewer can check the reading against the original.

| ID | Verbatim evidence | Source | Interpretation |
| --- | --- | --- | --- |
| QAR-01 | "..." | `file.md:L88` |  |

## Open Questions

Targets the sources never stated, values the sources contradict, and candidates that map to no catalog attribute. **These never enter the draft or the target document** — not as assumptions, not as TBD rows. They are resolved at a gate or they stay here.

| # | Question | Attribute | Proposed default | Status |
| --- | --- | --- | --- | --- |
| Q1 |  |  |  | open |

## Conflicts

Where two sources state different targets for the same thing, both are recorded. Neither is silently chosen.

| Attribute | Value A | Source A | Value B | Source B |
| --- | --- | --- | --- | --- |

## Dropped

Candidates deliberately excluded, with the reason, so the user can push back.

| Text | Source | Why dropped |
| --- | --- | --- |
|  |  | functional behaviour |

## Decision Log

| Date | Decision | Gate |
| --- | --- | --- |
