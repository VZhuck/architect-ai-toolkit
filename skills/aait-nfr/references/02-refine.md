# Phase 2 — refine

Three gates: resolve open questions, make every requirement measurable, set priorities. Each confirmed answer is written into the draft immediately, so the work survives the conversation.

**Writes the draft and trace only. Never `nfrPath`.**

Load `references/discriminators.md` alongside this file.

## Where the state comes from

Read the draft and trace resolved in "Before doing anything". If no draft exists, phase 1 has not run — say so and offer to run detect rather than mining silently.

Each gate below ends by **writing the confirmed result into the draft before moving on**. Never batch three gates' worth of answers and write once at the end: an interruption then loses everything the user just decided.

All three gates run **in this conversation**. None may be delegated to a subagent — a subagent cannot ask the user a question, so it would guess forward and the answer would not be the user's. Present each gate, wait, then write.

Resuming is normal. When the Decision Log already records gates that were answered, pick up at the next one rather than re-asking what the user has settled.

## Gate 1 — open questions

Work through the trace file's Open Questions table. These are targets the sources never stated: availability, RTO/RPO, latency percentiles, concurrency and peak load, retention periods, cost caps, dependency SLAs. **These numbers are what the document exists to record; inventing them defeats its purpose.**

Present **one consolidated block**:

| # | Question | Attribute | Proposed default | Basis |
| --- | --- | --- | --- | --- |
| Q1 | What monthly availability is committed? | Resilience | 99.9% | catalog default; no source states one |
| Q2 | RTO / RPO after a region failure? | Resilience | RTO ≤ 15 min, RPO ≤ 5 min | sized to the Q1 proposal |
| Q3 | Peak concurrent users at month-end? | Performance & Scalability | 500 | "falls over every month-end" — notes 2026-08-06 |

A defensible starting value the user can accept, adjust, or reject beats a blank, **as long as the provenance is honest**. Say where each proposal came from.

Also surface here:

- **Conflicts** — two sources, different targets. Name both with their provenance. Do not pick a winner.
- **Unmapped candidates** — propose the closest catalog attribute, or recommend the user add a catalog row themselves. The tool never adds one.
- Anything the sources explicitly marked `TBD` or deferred to a named stakeholder.

**Stop and wait.** An unanswered question stays in the trace file. It does not become an assumption, and it does not become a `TBD` row in the draft.

Write accepted answers into the draft, then continue.

## Gate 2 — measurable requirements

A quality attribute without a metric is a slogan. Every requirement states **what is measured, the threshold with its unit, and the conditions**.

| Source says | Requirement becomes |
| --- | --- |
| "The system should be fast." | `p95 page load < 2s for the top 10 journeys at 500 concurrent users` |
| "We can't afford another outage like last December." | `99.95% monthly availability; RTO ≤ 15 min, RPO ≤ 5 min` *(proposed)* |
| "New devs take forever to get productive." | `New engineer ships a production change within 5 working days; local bootstrap < 30 min` |

Prefer scenario form — stimulus, environment, response, measure — where a bare number would be ambiguous.

Present for review, grouped so they can be read in one pass:

- every requirement still marked `(proposed)` or `TBD`
- every requirement where source evidence conflicts
- metrics inherited from an existing document that this batch of sources contradicts

**Stop and wait.** A `(proposed)` value may stay in the document after this gate — the marker is honest — but only once the user has seen it here and chosen to accept, adjust, or leave it pending.

Write the agreed wording into the draft, then continue.

## Gate 3 — priorities

Priority is what gives the document its value: it tells architects what to trade away.

Use the scale in `templates/qa-priorities.md` unless the target document already uses a different one — then match the document. Start from catalog baselines and adjust on evidence. **A stakeholder banging the table about latency is evidence. Silence is not.**

Show the budget:

```
P0 budget  [■■■■■□□]  5 / 7 used

  P0  Performance & Scalability   "checkout under two seconds" — RFP §4.2
  P0  Resilience                  "falls over every month-end" — notes 2026-08-06
  P0  Security & Privacy          PCI-DSS scope — BD-01
  P0  Maintainability             catalog default, unchallenged
  P0  Testability                 catalog default, unchallenged
  P1  Interoperability            ▲ raised from P2: three integration partners named
  P2  Auditability & Compliance   ▼ no evidence in sources; catalog default is P2
```

Present:

- a proposed priority for every row, each with a one-line reason: source evidence, or "catalog default"
- the chosen `P0` rows, called out explicitly
- every priority differing from the catalog baseline, marked `▲` or `▼`
- every priority differing from a locked value in the existing document

**If more than seven qualify for `P0`**, do not quietly inflate the list. Ask which the business would sacrifice first, or present the tie-break.

**Stop and wait.**

## After gate 3

Confirmed priorities become `P0 🔒` in the draft. Drop `(proposed)` from values the user accepted. Keep `*new*` on rows the user has not yet acknowledged.

Append a decision-log entry to the trace file for each gate answered — date, what was decided, which gate.

Then report:

- what was resolved at each gate
- what remains open in the trace file, and why it is not in the draft
- the `P0` set and the budget headroom
- that publish is the next step, and that it validates before writing anything
