---
name: aait-nfr
description: "Create and maintain a project's Non-Functional Requirements document — business drivers and goals, quality attribute requirements, constraints, and assumptions — from requirements, meeting notes, RFPs, or transcripts, classified against closed catalogs. Use whenever the user mentions NFRs, quality attribute requirements, quality attributes, '-ilities', SLAs/SLOs, performance or availability targets, architecture constraints, or asks to review source material for quality criteria, including refreshing or reprioritizing an existing NFR document."
argument-hint: "phase (optional — detect | refine | publish | validate; omit it and the phase is inferred from the in-flight run), path (directory or file to analyze — ask the user, never guess), nfrPath (target NFR document; falls back to .env NFR_PATH, else choose from sad/)"
---

# Non-Functional Requirements

Turn raw prose into a structured, measurable, prioritized Non-Functional Requirements document. Works the same for initial creation and for ongoing maintenance.

**Non-functional requirements** is the umbrella term. It covers four things, and this skill keeps them distinct:

| Section | What belongs there |
| --- | --- |
| Business Drivers & Goals | What the business gains or loses, and by when. Money or a date, never a mechanism. |
| Quality Attribute Requirements | Measurable properties the team is accountable for. One row per requirement. |
| Constraints | Non-negotiable givens that remove design options and cannot be traded off. |
| Assumptions | Design-time beliefs being proceeded on, each with its impact if wrong. |

## Arguments

Parse the invocation before doing anything else:

1. Extract `--nfr-path <path>` if present — the value is the next token. It never needs to be given; it overrides the `.env` fallback when it is.
2. Extract the phase if the caller named one — `detect`, `refine`, `publish`, or `validate`. **Omitting it is the normal case**, and means the phase is inferred (below).
3. Whatever single token remains, if any, is `path` for detect, or `docPath` for validate. If nothing remains, it is omitted — do not invent one.

Never read `.env` here. The resolver script below owns every fallback.

## Before doing anything

1. Resolve paths. `<skillDir>` is the directory holding this file; `<skillDir>/templates/` holds the catalogs.

   ```bash
   uv run python <skillDir>/scripts/resolve_nfr_paths.py --path "{path}" --nfr-path "{nfrPath}"
   ```

   Omit a flag entirely when the caller did not supply it — never pass an empty string. The script resolves `nfrPath` itself: explicit argument, then `.env` `NFR_PATH`, then it lists the documents in `sad/` and proposes a SAD-compliant name for a new one. **When it reports "needs user choice", ask the user and wait.** Never guess a target document.

2. Read all three catalogs. **Hard stop if any is missing or unreadable** — report which one and ask where to find it. Do not fall back to ISO 25010, generic "-ilities", or vocabulary mined from the sources.

   - `<skillDir>/templates/business-drivers.md`
   - `<skillDir>/templates/quality-attributes.md`
   - `<skillDir>/templates/qa-priorities.md`

3. State the resolved paths — sources, catalog folder, draft, trace, target — so the user can correct you cheaply. Say it once, in the opening block below, together with the phase you inferred.

## Where you are in the pipeline

When the caller named a phase, run that phase. When they did not — the normal case — infer it from the **in-flight run**: the draft and trace the resolver just reported on. Never infer silently; say what you read and what you concluded before you act.

The resolver reports `draft_exists` and `trace_exists`. Read the trace's Decision Log for the rest.

| What you find | Where you are | What to do |
| --- | --- | --- |
| No draft | No run in flight | Ask which sources to analyze, then **detect**. Never mine before they answer. |
| Draft, Decision Log has no terminal `publish` row | Mid-run | **Refine**, resuming at the gate after the last one logged. Do not re-mine, do not re-ask answered gates. |
| Draft, all three gates logged, no `publish` row | Refined, unpublished | Offer **publish**. |
| Draft, Decision Log ends in a `publish` row | Previous run finished | Say so and offer a fresh **detect** run against new sources. Never offer to re-publish it. |
| Draft but no trace | Undecidable | Say the gate cannot be determined and **ask which phase to run**. Never guess a gate, never silently restart the pipeline. |

Open with the phase map and the state behind your call, in the same breath as the resolved paths — one block the user can correct cheaply:

```
Target:   sad/08.Non-Functional-Requirements.md   (exists — maintenance run)
Draft:    ai-workflow/nfr/08.…draft.md            (exists, gates 1–2 logged)
Phases:   detect ─▶ refine ─▶ publish        validate (any time)
Inferred: refine, gate 3 (priorities). Say "publish" or "detect" to override.
```

Two rules this table does not bend on:

- **`nfrPath` is not a phase signal.** It is a living document fed by successive source batches, so it exists on almost every run and says nothing about progress. Its existence matters only at publish, where it selects merge-by-identifier over create.
- **Validate is never inferred.** It is orthogonal to the pipeline — it needs no draft, no trace, and no in-flight run, and it runs against any document, including one this pipeline never produced. Reach it only when the caller asks for it by name.

An explicit phase always wins. When it differs from what you inferred, say both — "the draft reads as mid-refine; running publish as asked" — so a mistaken override is visible before anything is written.

## The rules that hold in every phase

- **The catalogs are closed vocabularies.** Use attribute names verbatim: same wording, same casing, same ampersands. Never invent, split, merge, paraphrase, or re-case one. A candidate that fits no catalog row becomes an open question in the trace file — never a new catalog row.
- **Only publish writes to `nfrPath`.** Detect and refine write the draft and trace only.
- **Draft and trace live in `ai-workflow/nfr/`, never in `sad/`** — `md-to-word` would sweep them into the stakeholder Word document.
- **Open questions never enter the draft.** Not as assumptions, not as TBD rows. They are resolved at a gate or they stay in the trace file.
- **Gates run here, in this conversation.** Never delegate a gate to a subagent: a subagent cannot ask the user a question, so it would guess forward.
- **At most 7 rows carry `P0`** across the whole document.
- **Locked priorities (`🔒`) are immutable.** Report a mismatch; never change one without an explicit unlock in the current conversation.

## Phases

Read the reference for the phase being run, and only that one. Each names what to do, what to show, and where to stop.

| Phase | Takes | Reference | Writes |
| --- | --- | --- | --- |
| detect | `path` — ask, never guess | `references/01-detect.md` | draft, trace |
| refine | — sources were mined in detect | `references/02-refine.md` | draft, trace |
| publish | — | `references/03-publish.md` | **`nfrPath`**, and the trace's publish row |
| validate | optional `docPath` — any NFR document | run the validator, report findings | nothing |

Two references are loaded alongside whichever phase is running:

- `references/discriminators.md` — the ordered ladder that sorts a candidate into driver, requirement, constraint, assumption, dropped, or open question. Required by detect and refine.
- `references/miner-agent.md` — the brief handed to each mining subagent. Required by detect.

Phases are re-entrant and their order is not enforced. Running publish early is safe: the validator fails an under-refined draft rather than letting it reach the deliverable.

## Validation

```bash
uv run python <skillDir>/scripts/validate_nfr.py --doc "{document}" --catalog-dir "<skillDir>/templates"
```

Exit `0` passes, `1` fails, `2` means a file could not be read. The script never modifies the document.

In the **validate** phase, `--doc` is the `docPath` the caller gave, and falls back to the resolved `nfrPath` when they gave none. It needs no sources, draft, or trace, so it audits any NFR document — including one this pipeline did not produce. Report failing checks with their rows first, then the warnings: `(proposed)` values still awaiting confirmation, and locked priorities that could not be verified because the document has no git `HEAD` version yet.

After the script passes, apply the judgement checks it cannot make:

- Is each metric genuinely measurable in practice, or merely numeric?
- Is each business driver genuinely a business outcome, or a mechanism dressed up as one?
- Does anything contradict a decision recorded earlier in the trace file?

Raise any concern before promoting, even when the script passed.

## Judgement calls

- **Sparse sources.** If the material yields almost nothing, say so. Offer a short elicitation instead of padding the tables to cover the catalog.
- **Contradictions.** Later notes usually supersede earlier ones, but check dates and surface both when in doubt.
- **Ambitious targets.** "Five nines" beside a shoestring budget is a real finding. Record the requirement and note the tension; do not quietly soften it.
- **Confidentiality.** Source material contains names and opinions. Carry the requirement into the document, not the gossip.
