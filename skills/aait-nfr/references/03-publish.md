# Phase 3 — publish

Render, validate, merge, show the diff, promote. **This is the only phase that writes to `nfrPath`.**

## 1. Re-read the catalogs

Read `templates/business-drivers.md` and `templates/quality-attributes.md` again now, in this phase's context.

This is not redundant. Catalog drift at write time — an attribute quietly paraphrased thousands of tokens after it was first read — is the single most common way these documents stop being comparable across projects. Re-reading costs little and removes the failure.

## 2. Render

Build the complete document from the draft against `templates/nfr-document.md`.

Priority cell conventions:

| Marker | Meaning |
| --- | --- |
| `P0 🔒` | confirmed by the user; immutable on later runs |
| `P1` | proposed or inherited, not yet locked |
| `(proposed)` | value awaiting stakeholder confirmation |
| `TBD` | explicitly deferred |
| `*new*` | added this run, not yet reviewed |
| `—` | no business driver traces to this requirement |

Keep rows terse enough to scan. Long rationale belongs beneath the table, never inside a cell.

## 3. Merge, when the document already exists

Treat the existing document as authoritative:

- **Match rows by identifier** and update in place. Never reorder or re-word a row you are not changing.
- **Locked priorities (`🔒`) are immutable this run.** Report a mismatch; do not touch the cell.
- **Preserve human edits, comments, and any extra sections** the document has grown. If a stakeholder priority contradicts your reading of the sources, keep theirs and raise it.
- Metrics may be tightened in place. If the change is material — threshold moves, conditions differ — list the previous value in the summary.
- **Never delete a requirement because this batch of sources didn't mention it.** Absence of evidence is not retraction. Propose removal in the summary instead.
- If the existing document uses different heading spellings, keep the existing ones and report the mismatch.

## 4. Validate

```bash
uv run python <skillDir>/scripts/validate_nfr.py --doc "{draft}" --catalog-dir "<skillDir>/templates"
```

**Exit code 1 means nothing is promoted.** Report every failure with its row, fix what is genuinely fixable, and re-run. Do not edit the validator, widen its patterns, or reach for `nfrPath` to work around a failure. A failing check is the pipeline working.

If a check is wrong — a legitimate driver flagged as technical, say — stop and raise it with the user. That is a change to the validator, made deliberately, not a bypass.

Warnings do not block promotion. Report them: `(proposed)` values still pending, and locks that could not be verified because the document has no git `HEAD` version yet.

Then apply the judgement checks the script cannot make:

- Is each metric genuinely measurable in practice, or just numeric?
- Is each driver genuinely a business outcome, or a mechanism dressed up as one?
- Does anything contradict a decision in the trace file's decision log?

Raise any concern **before** promoting, even on a clean script run.

## 5. Show the diff, then promote

Show the user what will change before it changes — a diff of the rendered draft against the current target document, or the full document when creating it fresh.

Then write to `nfrPath`. Create parent directories if needed. When the target is a new document in `sad/`, the filename was agreed during path resolution and already conforms to `rules/sad-sections.instructions.md`.

## 6. Report

- paths used — sources, catalog folder, draft, trace, target — and how many sources were read
- requirements added / updated / unchanged
- the `P0` set, one line of reasoning each
- **locked-priority mismatches**: attribute, locked value, evidence-suggested value, source quote and date — and state plainly that no change was made
- unmapped candidates still needing a catalog decision from the user
- `(proposed)` and `TBD` values still needing stakeholder confirmation
- conflicts between sources — name both, pick neither
- anything still open in the trace file

Keep it scannable. The document is the deliverable; the summary just says where to look.
