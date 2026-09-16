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

One row per gate answered, and a terminal `publish` row once a run reaches the target document. The `publish` row is what tells a later invocation that a run finished: a draft with no `publish` row after its last gate is still in flight, and is resumed rather than restarted.

This log **accumulates across runs** against the same living document. It is never reset — a second source batch appends its gates and its own `publish` row beneath the first run's.

| Date | Decision | Gate |
| --- | --- | --- |
| 2026-09-16 | Promoted to `sad/08.Non-Functional-Requirements.md` — 19 requirements, 3 added | publish |
