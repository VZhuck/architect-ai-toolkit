# Match Deltas

Judgment rules for Stage 1 of `archy-nfr-propose`: deduplicating carried entries across runs, matching each delta against the golden copy (GC), issuing target IDs, and mapping a delta to document cells. Run it in the main thread: it needs every run and GC at once.

Never ask the user during matching. When unsure, take the conservative choice below, write the reason in the entry's `Comments` or the trace `Note`, and raise an open question.

## Inputs

- **Deltas.** The carried rows of every selected run registry (status `Confirmed`, `Auto`, `TBD`, or `TO REVIEW`), each with its origin `<run_id>/NFR-###`, plus the run's open questions (status `TO REVIEW`) and open conflicts.
- **GC records.** The output of `gc_tables.py parse`: for each ID, its section, `fields` (`category`, `statement`, `metrics`, `priority`, `risk`), and the raw `cells`.
- **ID state.** `highest` per type from the parse, and `retired_ids` from `resolve_draft.py`.
- **Catalogs.** `quality-attributes.md`, `business-drivers.md`, `nfr-priorities.md`.

## 1. Match confidence

Compare two requirements **of the same NFR type** and give one score. This is not the entry's own `Confidence`.

| Match | Meaning |
| ---: | --- |
| 95 | same category, same metric, near-identical wording |
| 85 | same category and the same measured subject (the same API, flow, or data); one side has no metric |
| 70 | same category and similar meaning, but different wording or subject granularity |
| < 70 | different requirements |

"Subject" is what the requirement is about: "checkout latency" and "search latency" are different subjects in the same category. Two metrics that say the same thing in different units (`1 h` and `60 min`) are the same metric. Two metrics with different targets for the same measure (`RTO 1 h` and `RTO 4 h`) are **different values**, whatever the score.

Pick the nearest anchor. Compare across types only to detect `MOVED` (section 3).

## 2. Cross-run dedupe

Compare the deltas of different runs with each other (within one run, the miner has already deduplicated).

| Case | Action |
| --- | --- |
| match ≥ 85, no different values | **merge**: keep the first run's row (runs in `files_4_review` order), join the origins with `; `, keep the metric that is present, and keep the higher confidence and the stricter status (`Confirmed` > `Auto` > `TBD` > `TO REVIEW`). Trace `Note`: `merged across runs` |
| same subject, different values | **conflict** `C#`: A = the earlier run's value and origin, B = the later run's. Both entries become `TO REVIEW`, and one open question "C#: which target applies, A or B?" names both |
| match 70 | keep both as `TO REVIEW`, with one open question: "Are <origin A> and <origin B> the same requirement?" |
| < 70 | keep both |

Carry over a run's own open questions and conflicts unchanged, re-pointed to the new target IDs. Never carry a `Closed` question or a `## Dropped` row.

## 3. Delta vs GC dispositions

Match each deduplicated delta against the GC records **of its type**, and take the best match.

| Case | Disposition | Effect |
| --- | --- | --- |
| match ≥ 85 and the delta adds nothing GC lacks | `SAME` | row in `## Dropped`: `Why dropped` = "already in GC as <ID>", `Dropped by` = `SKILL`. Target ID = the GC ID. The draft is unchanged |
| match ≥ 85, and the delta only fills cells GC leaves empty (metric, priority, risk) | `UPDATE` | Target ID = the GC ID. The change set holds only the filled fields |
| match ≥ 85, and any field GC fills has a different value in the delta | `CONFLICT` | `## Conflicts`: A = the GC value (`Source A` = `GC <ID>`), B = the delta value and origin. Status `TO REVIEW`, plus the open question "C#: keep GC <A> or apply <B>?". Target ID = the GC ID. The draft is unchanged |
| match 70 against a GC record | `NEW` + question | status `TO REVIEW`; open question "Possible duplicate of <GC ID>: same requirement?" |
| a GC record of **another type** matches ≥ 85 by subject | `MOVED` | status `TO REVIEW`; open question "Move <GC ID> from <type> to <type>?". Target ID = the GC ID until confirmed |
| no match | `NEW` | next ID of its type (section 4) |

Conservative defaults:
- **Unsure between `UPDATE` and `CONFLICT`:** choose `CONFLICT`. Rewording a filled `Requirement` or `Business Goal` cell is a value change, not a gap.
- **Unsure between a match and `NEW`:** choose `NEW` with the possible-duplicate question.
- **A QAR whose category differs from the GC record's** (same subject, same type) is a `CONFLICT` on the category cell. It is not `MOVED`, because the ID stays.
- **Absence is not removal:** a GC record that no delta matches is left alone. Only the user removes a record, in review.

A delta whose type is `TBD` is never matched or rendered. It stays `TO REVIEW`, without a target ID, keyed by its origin until review sets a type.

## 4. Target IDs

- A GC ID never changes. `UPDATE`, `SAME`, `CONFLICT`, and an unconfirmed `MOVED` keep it.
- **`NEW` IDs.** A `NEW` entry takes `<TYPE>-<n>`, where `n` is one above the highest of: `highest[TYPE]` from the parse, every retired ID of that type, and every ID already issued in this draft. Pad to three digits (`QAR-013`). Issue in `files_4_review` order, then origin order.
- **Category change.** Moving a QAR between quality-attribute categories keeps its ID.
- **Confirmed `MOVED`.** The old ID goes to `## Retired` (`Replaced by` = the new ID, with the reason and date), and the entry gets a `NEW` ID of its new type. A retired ID is never issued again.
- **IDs of dropped entries.** An ID issued in this draft but dropped before hand-off never reached GC. It is not retired, but it is also not re-issued within this draft.

## 5. Cells

Map an entry to its section's columns:

| Field | BD | QAR | ASM | CSTR |
| --- | --- | --- | --- | --- |
| `category` | Business Driver | Quality Attribute | - | - |
| `statement` | Business Goal | Requirement | Assumption | Constraint |
| `metrics` | Metric / Criteria | Metric / Criteria | - | - |
| `priority` | Priority | Priority | Impact | Impact |
| `risk` | - | - | Risk | - |

- **`statement`.** For a QAR, the subject without the target ("Checkout API response time"), because the target goes in `metrics`. For a BD, the goal. For an ASM or CSTR, the full statement as one sentence. Stay faithful to the verbatim evidence and invent nothing.
- **`category`.** The catalog name, verbatim, without bold markers.
- **`priority`.** One of `Critical`, `High`, `Medium`, `Low`, or empty. Never guess one.
- **`risk`** (ASM). What breaks if the assumption is false, taken from the entry's interpretation or an answered question. If it is unknown, leave it empty and add the open question "What breaks if <assumption> is false?".
- **GC custom columns.** Never write them. The script leaves them empty on new rows and unchanged on updated rows.

## 6. Change set

`changes.json` in the draft folder is the whole change set against `base.md`, rebuilt from the Change Set rows that are renderable (the status is `Confirmed`, `Auto`, or `TBD`; the disposition is `NEW`, `UPDATE`, or a confirmed `MOVED`):

```json
{"changes": [
  {"op": "add", "id": "QAR-013", "after_id": "QAR-004",
   "fields": {"category": "Performance & Scalability", "statement": "Refund API response time", "metrics": "p95 < 1 s", "priority": ""}},
  {"op": "update", "id": "QAR-005", "fields": {"priority": "High"}},
  {"op": "remove", "id": "QAR-007"},
  {"op": "add", "id": "CSTR-004", "fields": {"statement": "...", "priority": "High"}}
]}
```

- **`add`.** For a QAR, `after_id` is the last GC row, or the last row already added, with the same category. Omit it when there is none.
- **`update`.** Holds only the fields the entry changes: the filled gaps, or the value picked in review.
- **Confirmed `MOVED`.** A `remove` of the old ID plus an `add` of the new one.
- **`--forbid`.** List every target ID that is **not in GC** and is `TO REVIEW`, in an open conflict, or dropped, as a `--forbid` argument to `check_draft.py`. A GC ID in conflict stays rendered with its GC values; the preservation check already proves the row is unchanged, because no `update` claims it.
