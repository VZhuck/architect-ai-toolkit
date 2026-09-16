# Phase 1 — detect

Mine the sources, classify what comes back, confirm the classification with the user, and write the first draft and trace.

**Writes the draft and trace only. Never `nfrPath`.**

Load `references/discriminators.md` and `references/miner-agent.md` alongside this file.

## 1. Collect the sources

`resolve_nfr_paths.py --path` already expanded the input into text-bearing files and skipped binaries, images, and lock files. If it reported more than 30 candidates, **list what was found and ask which subset matters** before dispatching anything. Mining 200 files to find 12 requirements wastes the user's budget.

## 2. Dispatch mining agents

One agent per source file, **all in a single message** so they run concurrently. Compose each prompt per `references/miner-agent.md`.

Fan-out is a quality decision as much as a context one: one agent reading thirty files reads files 20–30 visibly worse than files 1–10.

## 3. Merge and enforce the vocabulary

For each returned batch:

1. **Check every `attribute` against the catalogs.** Absent name → reject the batch, re-request that file. Never accept it, never silently correct it. This is where the closed vocabulary is enforced.
2. Deduplicate semantically across files. The same requirement in two meetings is one row carrying both locations.
3. Where two sources state different targets for the same thing, record both in the trace file's Conflicts table. Name both, choose neither.
4. Assign identifiers: `BD-01…` in catalog order, `QAR-01…` in the order attributes appear in `quality-attributes.md`.

On a maintenance run where the target document already exists and no draft is present, parse it for the highest identifier per prefix and continue from there. **Never reassign an existing identifier.**

## 4. Show the funnel

```
 47 mined ─┬─▶  3 business drivers
           ├─▶ 19 quality attribute requirements
           ├─▶  7 constraints
           ├─▶  4 assumptions
           ├─▶  9 open questions   (never reach the document)
           └─▶  5 dropped as functional
```

List the five dropped candidates explicitly, with the reason. Dropping silently is how a real requirement disappears.

## 5. Show the coverage grid

This is the most useful single view in the whole pipeline: it makes the *gaps* visible, and gaps are where phase 2's elicitation should aim.

```
Attribute                    Evidence   Requirement    Priority
──────────────────────────────────────────────────────────────
Conceptual Integrity         ·          ✗ GAP          P1  (catalog default)
Maintainability              ██         ✓ measured     P0
Reusability                  ·          ✗ GAP          P2  (catalog default)
Testability                  █          ⚠ proposed     P0
Performance & Scalability    ████       ✓ measured     P0
Resilience                   █          ⚠ proposed     P0
Security & Privacy           ███        ✓ measured     P0
Auditability & Compliance    ·          ✗ GAP          P2  ◄─ elicit
Interoperability             ██         ✓ measured     P1
Operability                  ·          ✗ GAP          P1  ◄─ elicit
Deployability                █          ⚠ proposed     P1
Usability & Accessibility    ·          ✗ GAP          P1  ◄─ elicit

  █ = one source supporting this attribute      · = no evidence found
  ✓ measured   threshold and conditions stated in the sources
  ⚠ proposed   inferred from a pain narrative, needs confirmation
  ✗ GAP        nothing in the sources speaks to this attribute
```

Mark `◄─ elicit` against gaps whose catalog baseline is `P1` or higher — a high-baseline attribute with no evidence is the gap most likely to matter.

A gap is not automatically a problem. Some attributes genuinely do not apply. The grid exists so the user decides that, rather than the absence going unnoticed.

## 6. Gate — confirm the classification

**Stop here. Present, ask, and wait for an answer in this conversation.**

Show:

- the mapping table: evidence → kind → catalog attribute, using catalog names verbatim
- open questions, each with the closest catalog attribute you considered
- every classification you are less than confident about, flagged explicitly
- the dropped list

Ask the user to confirm, correct, or extend. Batch the questions — do not drip-feed. If the user is unavailable, stop and report; do not guess forward.

Relay the funnel, the coverage grid, and this gate — and nothing beneath them. **Raw source file contents never reach this conversation**; that is the whole point of mining in subagents. Carry the candidate rows and their citations, not the material they came from.

## 7. Write the draft and trace

Only after the gate is answered.

- **Draft** — render from `templates/nfr-document.md`. Priorities are catalog baselines carrying `(proposed)`, never `🔒`; a lock is earned at the phase 2 priority gate, not assumed here. Every new row carries `*new*`.
- **Trace** — render from `templates/nfr-trace.md`: evidence rows, open questions, conflicts, dropped candidates, and a decision-log entry for the gate just answered.

Then tell the user the two paths and what phase 2 will ask about.
