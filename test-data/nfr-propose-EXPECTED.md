# nfr-propose fixture set - expected outcome

Run `archy-nfr-propose` with:
- `nfr_doc=test-data/nfr-propose/sad/08.Non-Functional-Requirements.md`
- `runs=payments-20260924-1402, security-20260926-0930`, in that order
- the resolver called with `--state-base test-data/nfr-propose/nfr-state`, because `ai-workflow/` is gitignored and the fixture runs live in `test-data`

For the end-to-end check, copy the tree into a scratch project and use the default `ai-workflow/nfr-state`.

## Stage 0

| Check | Expected |
| --- | --- |
| Run list | 3 runs. `notes-20260927-1100` is marked most recent, with the warning `not finished (stage-2/review-parked)` |
| If `notes-20260927-1100` is chosen | the skill warns and suggests `/archy-nfr-miner`, and includes the run only on "include anyway" |
| Target | `exists: true`, `format_source: gc` |

## Stage 1 dispositions

Starting IDs: GC has `QAR-001..003`, `CSTR-001`, `BD-001`, and `ASM-001`, and there are no retired IDs.

| Origin | Statement | Disposition | Target ID | Status | In draft |
| --- | --- | --- | --- | --- | --- |
| payments/NFR-001 | checkout p95 < 300 ms @ 500 TPS | SAME | QAR-001 | - (`## Dropped`: "already in GC as QAR-001") | no change |
| payments/NFR-002 | payment API 99.9% monthly, prio Critical | UPDATE (fills the empty Priority) | QAR-002 | Confirmed | QAR-002 Priority = `Critical`; `Owner` stays `Platform` |
| payments/NFR-003 | RTO 1 h | NEW, cross-run conflict **C1** with security/NFR-004 | QAR-004 | TO REVIEW | no |
| payments/NFR-004 + security/NFR-002 | admin console p95 < 2 s | NEW, **merged across runs** (match 95) | QAR-005 | Auto | added after QAR-001 (last P&S row), `Owner` empty |
| payments/NFR-006 | "easy to operate" (no metric) | NEW | QAR-006 | TO REVIEW (carried Q2) | no |
| security/NFR-001 | PCI-DSS 4.0 | NEW | CSTR-002 | Confirmed | appended to Constraints |
| security/NFR-003 | encryption at rest AES-128 | **CONFLICT** vs GC QAR-003 (AES-256), **C2** | QAR-003 | TO REVIEW | QAR-003 unchanged (`AES-256`) |
| security/NFR-004 | RTO 4 h | NEW, C1 side B | QAR-007 | TO REVIEW | no |

Not carried:
- payments `Q1`, because it is `Closed`
- payments `NFR-007` (export CSV), because it is in `## Dropped` in the run

The log's open questions are Q2 from payments (QAR-006), the C1 question, and the C2 question: 3 questions and 2 conflicts in total.

`check_draft.py` runs with `--forbid QAR-004 --forbid QAR-006 --forbid QAR-007` and passes.

### Summary

| Run | Carried | NEW | UPDATE | SAME | MOVED | CONFLICT | Merged dup | Open Q | Conflicts |
| --- | ---: | --: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| payments-20260924-1402 | 5 | 3 | 1 | 1 | 0 | 0 | - | 1 | 0 |
| security-20260926-0930 | 4 | 3 | 0 | 0 | 0 | 1 | - | 0 | 0 |
| **TOTAL (deduped)** | 8 | 5 | 1 | 1 | 0 | 1 | 1 | 3 | 2 |

The `TOTAL (deduped)` row counts the merged `QAR-005` once, so its NEW count is 5 rather than 6. `Carried` = 5 + 4 − 1 merged = 8.

### Draft diff against GC

```
+| QAR-005 | Performance & Scalability | Admin console page load time | p95 < 2 s |  |  |      (after QAR-001)
~| QAR-002 | Resilience | Payment API availability | 99.9% monthly | Critical | Platform |
+| CSTR-002 | Payment processing complies with PCI-DSS 4.0. | High |                           (after CSTR-001)
```

Everything else is byte-identical, including the intro texts, the `Owner` column, and `## Glossary`.

## Short review (commands mode)

`c1 a; c2 a`

| Command | Result |
| --- | --- |
| `c1 a` | keep RTO 1 h: QAR-004 is `Confirmed` and rendered after QAR-002 (the last Resilience row); QAR-007 goes to `## Dropped` ("superseded by QAR-004 (C1)"); the C1 question closes |
| `c2 a` | keep GC AES-256: QAR-003 is unchanged; security/NFR-003 goes to `## Dropped` ("superseded by GC QAR-003 (C2)"); the C2 question closes |

Still open: QAR-006 (Q2). `check_draft.py` passes after each apply pass. The GC fixture file is unchanged throughout.
