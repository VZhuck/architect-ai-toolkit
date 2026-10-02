# NFR Draft Log

Change log for one `archy-nfr-propose` draft. The golden copy (GC) is the existing NFR document; the deltas are entries carried over from reviewed `archy-nfr-miner` registries. This log records what the draft changes in GC and why. `draft.md` shows only what this log allows.

## Draft Log Taxonomy

- **Target ID** - the ID in the NFR document, `<TYPE>-###` (`BD-001`, `QAR-001`, `ASM-001`, `CSTR-001`). A GC ID never changes. A `NEW` entry takes the next number of its type, above every GC ID and every ID in `## Retired`. Empty for a `TBD` type until review decides the type
- **Disposition** - what the delta does to GC:
  - SAME - matches a GC record and adds nothing; lives only in `## Dropped`
  - UPDATE - fills a gap in a GC record (for example an empty metric or priority) without changing an existing value; the ID is kept
  - CONFLICT - states a different value for a field the GC record already fills; GC is unchanged until review resolves `## Conflicts`
  - MOVED - belongs to a different NFR type than its GC record; on confirmation the old ID is retired and a new ID of the new type is issued
  - NEW - matches no GC record
- **NFR Type**, **NFR Category**, **Metrics**, **Priority**, **Confidence**, **Status**, **Comments** - as in `nfr-registry-log.md`
- **Statement** - the requirement text rendered into the document (`Business Goal`, `Requirement`, `Assumption`, or `Constraint` column)
- **Origin** - the delta references, `<run_id>/NFR-###`, joined with `; ` when runs were merged. `GC` when the row only restates the GC record. `USER` when added during review
- **Match** - the match confidence against the other side (95 same metric and wording, 85 same subject with one metric missing, 70 similar meaning, <70 different)

Only rows with status `Confirmed`, `Auto`, or `TBD` and disposition `NEW`, `UPDATE`, or a confirmed `MOVED` are rendered into `draft.md`. Open questions, `TO REVIEW` rows, unresolved conflicts, and dropped rows never are.

## Change Set

One row per target ID the draft adds or changes.

| Target ID | Disposition | NFR Type | NFR Category | Statement | Metrics | Priority | Origin | Confidence | Status | Comments |
| --------- | ----------- | -------- | ------------ | --------- | ------- | -------- | ------ | ---------- | ------ | -------- |
| QAR-013   | NEW         | QAR      | Performance & Scalability | Checkout API response time | p95 < 300 ms @ 500 TPS | | `payments-20260924-1402/NFR-003` | 95 | Auto | |

## Trace

One row per carried delta, including `SAME` and merged ones, so every origin ID can be followed to its target.

| Origin | Match | Disposition | Target ID | Note |
| ------ | ----- | ----------- | --------- | ---- |
| `payments-20260924-1402/NFR-003` | - | NEW | QAR-013 | |

## Retired

IDs removed from the document (a confirmed `MOVED`, or removed in review). A retired ID is never issued again.

| ID | Replaced by | Reason | Date |
| -- | ----------- | ------ | ---- |

## Open Questions

Unresolved questions carried over from the runs, plus new ones raised by the merge. **These never enter the draft.** Status is `TO REVIEW` while open and `Closed` once answered, accepted, or its entry is dropped.

| #  | Question | Target ID | Proposed default | Default by | Comments | Status    |
| -- | -------- | --------- | ---------------- | ---------- | -------- | --------- |
| Q1 |          | QAR-013   |                  | SKILL      |          | TO REVIEW |

## Conflicts

Two values for the same thing. Value A is the GC value (or the earlier run for a run-vs-run conflict), value B is the delta. Neither is silently chosen.

| #  | NFR Type | NFR Category | Target IDs | Value A | Source A | Value B | Source B |
| -- | -------- | ------------ | ---------- | ------- | -------- | ------- | -------- |

## Dropped

Deltas that do not change the document, with the reason, so the user can push back.

| Origin | Target ID | Text | Why dropped | Dropped by |
| ------ | --------- | ---- | ----------- | ---------- |
|        |           |      | already in GC as QAR-002 | SKILL |
