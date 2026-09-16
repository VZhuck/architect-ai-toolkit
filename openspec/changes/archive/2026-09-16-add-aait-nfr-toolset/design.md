## Context

The predecessor skill (`skills/nfr/SKILL.md`, now empty; content preserved in the change discussion) attempted the whole job in one invocation: load catalogs → mine sources → sort → elicit → classify → set metrics → prioritize → write → merge, with four "hard STOP" human-in-the-loop gates expressed as prose. In use it failed in five reproducible ways:

| Observed failure | Root cause |
|---|---|
| Wrote the target document before gates were answered | Gates were prose. Nothing physically prevented the write. |
| Paraphrased or invented catalog attribute names | Catalogs loaded at step 1, used at step 7 — thousands of tokens of drift. |
| Filed technical requirements into the business table | The rule was a paragraph of guidance with no defined order of evaluation. |
| Parked unanswered elicitation questions in Assumptions | There was nowhere else for them to go. |
| Skipped gates entirely | Nine steps in one context; late instructions lose to early ones. |

The catalog templates it shipped are accurate and are carried forward. Everything structural is replaced.

Constraints the design must respect:

- `.env` sets `NFR_PATH=./sad/08.Non-Functional-Requirements.md`, so the deliverable lives in `sad/` and is governed by `rules/sad-sections.instructions.md` — one H1, blank line before headings, markdown tables preferred, relative image paths. The prior attempt ignored this.
- `md-to-word` converts an entire folder of SAD section files into the stakeholder Word document. Any working file placed in `sad/` would be swept into that deliverable.
- The repo's established convention is real files under `./skills` and `./commands`, symlinked into `.claude/`, with Python mechanics run via `uv run` and judgement left to Claude (`load-raw-req`, `md-to-word`, `summarize-meeting-decisions`).
- `ai-workflow/` is gitignored. Accepted: draft and trace files are local-only and do not transfer between machines.

## Goals / Non-Goals

**Goals:**

- Make the final write physically ungateable-around: the target document is only ever written after a script exits zero.
- Keep source material out of the main conversation while keeping every user-facing decision in it.
- Give each artifact exactly one job, so no file is simultaneously state, deliverable, and audit trail.
- Make the business-driver vs. quality-attribute-requirement distinction a deterministic ordered test rather than a judgement call.
- Support both initial creation and repeated maintenance of the same document without a separate code path.

**Non-Goals:**

- Renaming existing toolkit skills to the `aait` prefix. The prefix applies going forward only.
- Automatic catalog extension. Both catalogs are hard-closed; growing them is a human edit.
- Automated priority setting. Priority is the step that gives the document its value and stays a user decision.
- Enforcing command order. Ordering is a consequence of validation, not a precondition checked by the tool.
- Transferring working state between machines.

## Decisions

### D1 — One skill folder with progressive disclosure, not one skill per phase

`skills/aait-nfr/` holds a short orchestrator `SKILL.md` plus `references/{01-detect,02-refine,03-publish,discriminators,miner-agent}.md`, loaded only when that phase runs.

*Why:* the catalogs, templates, and validator are shared by every phase. Splitting them across four skill folders means four copies that drift apart. Progressive disclosure also directly addresses the instruction-density failure — the model never holds all nine steps at once, and `03-publish.md` re-reads the catalogs in fresh context instead of relying on a copy loaded at the start of the session.

*Alternative considered:* four sibling skill folders with a shared catalog path resolved from an env var. Rejected — fragile path coupling, and the installer copies whole folders, so shared assets would need duplicating anyway.

### D2 — Subagents for mining only; every gate on the main thread

`/aait:nfr-detect` fans out one subagent per source file, in parallel. Each returns candidate rows in a strict schema. No other phase uses a subagent.

*Why:* mining is high-input, low-output — roughly 150k tokens of sources in, ~3k tokens of candidates out — which is exactly the isolation pattern `load-raw-req` already uses for Jira payloads. Fan-out per file is a quality decision as much as a context one: a single agent reading thirty files reads files 20–30 visibly worse than files 1–10.

The gates cannot be delegated because **a subagent cannot ask the user a question**. An agent handed the refinement phase must guess-forward on every missing number — reproducing the original failure with the guessing now hidden from the user.

*Cost accepted:* an agent only knows what it is handed, so `references/miner-agent.md` must carry the closed catalog, the discriminator ladder, and the output schema explicitly. Mitigated by D3.

### D3 — Validate agent output at the boundary

The main thread checks every attribute name returned by a mining agent against the catalog and rejects the batch if one was invented, split, merged, or re-cased.

*Why:* this is how the hard-closed policy is enforced rather than merely stated. Defense in depth — the agent is told the vocabulary is closed *and* the caller verifies it.

### D4 — The ordered discriminator ladder

Candidates are tested in this fixed order, first match wins:

```
 candidate statement
   │
   ├─ Behaviour the system performs?          ──yes──▶ FUNCTIONAL → drop, log why
   │
   ├─ Could a fitness function assert it?     ──yes──▶ QUALITY ATTRIBUTE REQUIREMENT
   │     p95<2s · RPO≤5min · WCAG 2.2 AA               → exactly one of the 12 attributes
   │     · "PII purged ≤30d of verified request"
   │
   ├─ Removes design options, untradeable?    ──yes──▶ CONSTRAINT
   │     EU regions only · must use enterprise IDAM
   │
   ├─ A belief we proceed on, with a stated
   │  impact if wrong?                        ──yes──▶ ASSUMPTION
   │
   ├─ Money / time-to-market / market access /
   │  penalty exposure, with a date?          ──yes──▶ BUSINESS DRIVER & GOAL
   │     "€2m penalty if not certified by 30/06/2027"
   │
   └─ none of the above                       ────────▶ OPEN QUESTION (never the document)
```

*Why the order matters:* testing "could a fitness function assert it?" **before** the business test is what stops `"System shall be GDPR compliant; PII removed within 30 days of request"` from landing in the business table. The prior skill stated both rules but not their sequence, so either destination was reachable.

The compressed form, which does most of the work: **if you could write a CI test for it, it is a quality attribute requirement, not a business driver.** A driver names what the business loses or gains and by when; it never names a mechanism.

### D5 — Three artifacts, one job each

```
  /aait:nfr-detect <path>
        │  fan-out miner agents → merge → reject off-catalog names
        │  GATE: confirm classification
        ▼
  ai-workflow/nfr/<doc>.draft.md      ◄── a real NFR document, same shape as the target
        ▲          │                      readable, reviewable, circulable
        │          │
  /aait:nfr-refine │  GATE: open questions → GATE: metrics → GATE: priorities
        └──────────┘  each confirmed gate is written straight into the draft
                   │
                   ▼
  /aait:nfr-publish
        │  re-read catalogs in fresh context
        │  validate_nfr.py  ──FAIL──▶ report; promote nothing
        │  merge into existing document: locks held, rows matched by ID
        │  show diff
        ▼
  sad/08.Non-Functional-Requirements.md
```

| File | Job | Written by |
|---|---|---|
| `ai-workflow/nfr/<doc>.draft.md` | working NFR document; session-to-session handoff | detect, refine |
| `ai-workflow/nfr/<doc>.trace.md` | evidence→ID map, open questions, dropped candidates | detect, refine |
| `nfrPath` | the deliverable | **publish only, after validation passes** |

*Why the draft is a full document rather than a worksheet:* keeping publish as a separate command means refined decisions must survive between sessions somewhere. Making that carrier a rendered NFR document — rather than a parallel worksheet format — means it can be circulated to a stakeholder for review before promotion, and it removes the sync problem between a worksheet and the document rendered from it.

*Why the trace file is deliberately non-load-bearing:* an earlier iteration of this design made a worksheet the enforcement mechanism ("do not write until status = confirmed"). That is the same class of weakness as the original prose gates. Enforcement moved to the validator (D6), which leaves the trace file to do only what it is genuinely good at — provenance and open questions, neither of which belongs in a stakeholder deliverable. Deleting the trace file loses the audit trail but does not break the pipeline.

*Why not in `sad/`:* `md-to-word` would sweep draft and trace into the stakeholder Word document.

### D6 — Enforcement is a script on the artifact, not a check on process state

`validate_nfr.py` runs against the rendered draft. Promotion happens only on exit code zero.

*Why:* this is the single decision that fixes the "wrote too early" failure, and it holds no matter how long the conversation ran or how far back the instructions are. It also makes command ordering a non-problem: running `/aait:nfr-publish` before refining produces a draft with unmeasured requirements and unset priorities, which fails validation, so the deliverable is never corrupted. No precondition checking is required anywhere.

Deterministic checks:

- every attribute name is an exact string match against the catalog
- Business Drivers rows are a subset of the four catalog drivers
- no technical vocabulary in driver cells (`latency|ms|p9\d|uptime|RTO|RPO|encryption|PII|TPS|…`)
- every driver cell carries a monetary amount or a date
- `P0` count ≤ 7
- every requirement states a threshold with a unit, or is explicitly marked `(proposed)` / `TBD`
- priorities marked `🔒` are byte-identical to the git `HEAD` version of the target document
- Assumptions follow the two-line `- Assumption (Impact)` shape
- SAD compliance per `rules/sad-sections.instructions.md`: one H1, blank line before headings, markdown tables

A short model-side checklist follows the script for what a script cannot judge: is this metric genuinely measurable, and is this driver genuinely a business outcome.

### D7 — One row per requirement, with identifiers

```markdown
## Business Drivers & Goals

| ID | Business Driver | Goal / Business Impact | Priority |
|----|-----------------|------------------------|:--------:|
| BD-01 | Risk & Compliance | ContosoX incurs €2m penalty if PCI-DSS 4.0 certification is not achieved by 30/06/2027 | P0 🔒 |
| BD-02 | Increase Revenue  | Cart abandonment above 12% costs ~£400k/quarter | P0 🔒 |

## Quality Attribute Requirements

| ID | Quality Attribute | Requirement | Priority | Driver |
|----|-------------------|-------------|:--------:|--------|
| QAR-01 | Performance & Scalability | p95 checkout latency < 2s at 500 concurrent users | P0 🔒 | BD-02 |
| QAR-02 | Performance & Scalability | Sustains 1,000 TPS peak; scale-out lag < 60s | P1 | BD-02 |
| QAR-07 | Security & Privacy | PII erased within 30 days of a verified subject request | P0 🔒 | BD-01 |
```

*Why not one row per attribute:* a real system has three performance requirements, not one. The prior template's attribute-per-row shape forced them into a single cell, which destroyed traceability into design decisions and test plans. Stable `QAR-nn` identifiers are what let maintenance runs match rows for in-place update rather than re-deriving the table.

`QAR-07` above is the example the prior skill got wrong, now correctly filed: the mechanism is a quality attribute requirement, traced up to a lean business driver that states only money and a date.

*Trade-off accepted:* the table is longer than the attribute-per-row form and slightly less comparable across projects at a glance. The `Quality Attribute` column preserves grouping.

*Driver column:* may be `—`. Not every requirement traces to a driver; baseline hygiene requirements do not.

### D8 — Hard-closed catalogs

Unmapped candidates become open questions and stay there. The tool never adds a catalog row.

*Why:* divergent vocabulary is the main reason these documents stop being comparable across projects, and a silently invented row is worse than an open question because it looks authoritative. The escape valve is deliberate and human: the user edits `templates/quality-attributes.md` or `templates/business-drivers.md` themselves.

*Consequence:* this puts real pressure on catalog completeness. The 12 technical attributes were checked against common gaps — observability maps to Operability, localization and accessibility to Usability & Accessibility, portability to Maintainability, cloud spend to the Cost Optimization driver. No gap found, but unmapped candidates surfacing repeatedly in reports is the signal that the catalog needs a human edit.

### D9 — Terminology

| Retired | Adopted |
|---|---|
| Business Quality Attributes | **Business Drivers & Goals** |
| `templates/business-qas.md` | `templates/business-drivers.md` |
| `templates/technical-qas.md` | `templates/quality-attributes.md` |
| Quality Attributes *(document section)* | **Quality Attribute Requirements** |
| `## Constrains` *(typo)* | `## Constraints` |

"Non-functional requirements" is the umbrella covering all four sections. The catalogs list *attributes* — the vocabulary; the document records *requirements* — instances of it. The file renames follow that distinction.

### D10 — Three-step `nfrPath` resolution, ending in a choice not a guess

```
  --nfr-path argument          ──given──▶ use it
        │ absent
        ▼
  .env NFR_PATH                ──set────▶ use it
        │ unset
        ▼
  list *.md in sad/  ──▶ ask the user: pick an existing document,
                              or name a new one
                              │
                              └─ new file ▶ propose a SAD-compliant name
                                            (<n>.<Title-Case-Hyphenated>.md,
                                             e.g. 08.Non-Functional-Requirements.md)
```

The skill never invents a target path. The final step is a user choice between existing documents in `sad/` and a new one — the same shape `summarize-meeting-decisions` already uses when listing `MEETING_NOTES_FOLDER`, so the interaction is familiar.

*Why propose the filename rather than accept free text:* `sad/` is governed by `rules/sad-sections.instructions.md`, which requires a zero-padded section-number prefix and a Title-Case-Hyphenated title with leading numbering stripped from the heading text. A user typing a filename by hand will not reliably produce that. The skill proposes a compliant name derived from the next free section number and lets the user adjust it.

*Draft and trace remain derived* from whatever `nfrPath` resolves to, and stay in the gitignored working directory `ai-workflow/nfr/`. Only the published document ever lands in `sad/`.

## Risks / Trade-offs

- **Draft and trace are gitignored and machine-local** → accepted by the user. A half-refined draft cannot be handed to a colleague by pushing a branch.
- **A new target document created under `sad/` becomes input to `md-to-word`** → the proposed filename must satisfy `rules/sad-sections.instructions.md` so the document slots into the SAD reading order correctly rather than landing with a name that sorts unpredictably.
- **Parallel mining agents may read the same requirement inconsistently across two source files** → the merge step deduplicates by semantic equivalence and surfaces genuine conflicts (two meetings quoting different SLAs) as open questions, naming both rather than picking a winner.
- **The lock check compares against git `HEAD`** → fails or degrades on an uncommitted target document or outside a git repo. Degrade to a warning rather than blocking promotion when no `HEAD` version exists.
- **Technical-vocabulary keyword scanning on driver cells produces false positives** → a driver legitimately naming a regulation ("PCI-DSS certification by 30/06/2027") must pass. Scan for *mechanism and measurement* vocabulary, not for regulation names, and keep the list narrow.
- **Four commands is more surface than the repo's existing one-command skills** → justified by the pipeline genuinely having four re-entry points, and it mirrors the `/opsx:*` family the user already works in.
- **Progressive disclosure depends on the model actually loading the phase reference** → the orchestrator `SKILL.md` names the exact file to read per phase, and publish's correctness is backstopped by the validator regardless.

## Migration Plan

1. Move the three catalog templates into `skills/aait-nfr/templates/`, applying the D9 renames and fixing the truncated Risk & Compliance description and missing baseline `Priority` column in `business-drivers.md`.
2. Build the skill, commands, and scripts. Add `.claude/` symlinks per the existing convention.
3. Delete `skills/nfr/` once nothing references it.
4. Existing NFR documents written against the old headings (`Business Quality Attribures`, `Quality Attributes`, `Constrains`) will not match the new template. `/aait:nfr-validate` reports the mismatch with the corrected heading names; migration of any such document is a manual edit, not an automated rewrite.

Rollback is deletion of the new folders — no existing skill, command, or spec depends on this change.

## Resolved Questions

- **`ossify-cogents` discovery recurses into `commands/aait/`.** The namespaced form is confirmed: `/aait:nfr-detect`, `/aait:nfr-refine`, `/aait:nfr-publish`, `/aait:nfr-validate`. No flat-file fallback is needed.
- **`/aait:nfr-validate` accepts an optional document path.** Auditing an NFR document that this pipeline did not produce — a colleague's, or one from another project — is a real use, and the validator already requires no sources, draft, or trace to run. With no path argument it falls back to the resolved `nfrPath`.
- **A maintenance run derives its `BD-nn` / `QAR-nn` sequence from the target document** when no draft exists, by parsing the highest existing identifier per prefix and continuing from there. Identifiers are never reassigned.

## Open Questions

None outstanding.
