## Why

The toolkit has no working path from raw source material (RFPs, requirements, meeting notes, transcripts) to a structured Non-Functional Requirements document. A first attempt — a single monolithic `nfr-analysis` skill at `skills/nfr/SKILL.md` — did not perform accurately in practice and its `SKILL.md` is now empty; only its catalog templates survive and they are sound. The failure was structural, not editorial: nine steps and four human-in-the-loop gates lived in one skill as prose, so the model wrote the target document before the gates were answered, paraphrased catalog attribute names by the time it reached the write step, filed technical requirements into the business table, and parked unanswered elicitation questions in the Assumptions section. Prose instructing a model to stop cannot stop a model. This change replaces that approach with a four-command pipeline whose final write is gated by a script that can fail.

## What Changes

- Add a single `aait-nfr` skill (`./skills/aait-nfr/`) using progressive disclosure: a short orchestrator `SKILL.md` plus phase reference files loaded only when that phase runs, so the catalogs are re-read at write time rather than carried thousands of tokens from the load step.
- Add four commands under `./commands/aait/` — `/aait:nfr-detect`, `/aait:nfr-refine`, `/aait:nfr-publish`, `/aait:nfr-validate` — establishing `aait` as the prefix for new toolkit skills and commands. Existing skills (`md-to-word`, `load-raw-req`, `summarize-meeting-decisions`, `word-to-md`) are **not** renamed.
- `/aait:nfr-detect` fans out one mining subagent per source file, in parallel. Source files never enter the main conversation; only candidate rows do. Every attribute name a subagent returns is validated against the catalog by the main thread and the batch is rejected if one was invented.
- All human-in-the-loop gates (confirm classification, resolve open questions, agree metrics, set priorities) run on the main thread. A subagent cannot ask the user a question, so delegating a gate would reintroduce the guess-forward failure it is meant to prevent.
- Add `validate_nfr.py`, a deterministic validator that is the pipeline's actual enforcement mechanism. `/aait:nfr-publish` renders to a draft, validates it, and promotes it to the target document only on a pass. Command ordering is deliberately unenforced: running publish prematurely fails validation rather than corrupting the deliverable.
- Introduce three artifacts with one job each: `<doc>.draft.md` (working NFR document and session-to-session handoff), `<doc>.trace.md` (evidence-to-ID map, open questions, dropped candidates), and the target document at `nfrPath` (written only by publish, only after validation passes). Draft and trace live in gitignored `ai-workflow/nfr/` and are explicitly local-only; they must not live in `sad/`, where the `md-to-word` skill would sweep them into the stakeholder Word deliverable.
- Skill parameters are exactly two: `path` (directory or file to analyze; ask the user, never guess) and `nfrPath` (target document; default `.env` `NFR_PATH`, else ask). Draft and trace paths are derived from `nfrPath` and are never passed by the caller.
- **BREAKING (terminology)** — "business quality attributes" is retired in favour of **Business Drivers & Goals**; the catalog `templates/business-qas.md` is renamed `business-drivers.md` and `templates/technical-qas.md` is renamed `quality-attributes.md`. The document section "Quality Attributes" becomes **Quality Attribute Requirements**, and the `Constrains` heading typo is corrected to **Constraints**. "Non-functional requirements" becomes the umbrella term covering all four sections. Existing NFR documents written against the old headings will not match the new template.
- Quality attribute requirements are recorded **one row per requirement** with stable `QAR-nn` identifiers, the catalog attribute as a column, and a `Driver` column tracing up to a `BD-nn` business driver — not one row per attribute as the prior template assumed. Business drivers are capped at the four catalog rows and must state business consequence with money or a date, never a mechanism.
- Both catalogs are **hard-closed vocabularies**. A candidate that fits no catalog row becomes an open question; the tool never invents, splits, merges, or paraphrases an attribute name. Extending a catalog is a deliberate human edit to the template file.
- Fix two defects in the surviving catalog content: `business-qas.md`'s Risk & Compliance description is truncated mid-sentence, and unlike `technical-qas.md` the file carries no baseline `Priority` column.
- Remove the dead `skills/nfr/` folder once its templates have moved to `skills/aait-nfr/templates/`.

## Capabilities

### New Capabilities

- `nfr-analysis`: mining source material for non-functional requirement signals, classifying candidates against hard-closed business-driver and quality-attribute catalogs via an ordered discriminator ladder, eliciting missing targets through gated user confirmation, and maintaining a prioritized NFR document across create and update runs — exposed as the `aait-nfr` skill and its four slash commands.
- `nfr-document-validation`: deterministic, independently runnable verification of an NFR document — catalog fidelity, business/technical separation, measurability, the P0 budget, priority-lock integrity, and SAD section-file compliance — exposed as `validate_nfr.py` and the `/aait:nfr-validate` command.

### Modified Capabilities

(none — no existing spec's requirements change)

## Impact

- **New files**: `skills/aait-nfr/SKILL.md`, `skills/aait-nfr/references/*.md`, `skills/aait-nfr/templates/*.md`, `skills/aait-nfr/scripts/{resolve_nfr_paths.py,validate_nfr.py}`, `skills/aait-nfr/tests/*`, `commands/aait/nfr-{detect,refine,publish,validate}.md`, plus `.claude/` symlinks matching the existing convention.
- **Moved/renamed**: `skills/nfr/templates/business-qas.md` → `skills/aait-nfr/templates/business-drivers.md`; `skills/nfr/templates/technical-qas.md` → `skills/aait-nfr/templates/quality-attributes.md`; `skills/nfr/templates/qa-priorities.md` → `skills/aait-nfr/templates/qa-priorities.md`.
- **Deleted**: `skills/nfr/` (its `SKILL.md` is already empty).
- **Modified**: `.env.example` — `NFR_PATH` already exists; document it under an NFR heading alongside the other skill fallbacks.
- **Unverified dependency**: `ossify-cogents.json` discovers commands with `{ "type": "folder", "path": "commands" }`. Whether that discovery recurses into `commands/aait/` is unknown and must be verified before committing to the namespaced `/aait:nfr-*` form. Fallback is flat files (`commands/aait-nfr-detect.md` → `/aait-nfr-detect`).
- **Interaction with existing skills**: `md-to-word` converts a folder of SAD section files, so draft and trace files must stay outside `sad/`. The target document at `sad/08.Non-Functional-Requirements.md` is subject to `rules/sad-sections.instructions.md`, which the prior attempt ignored entirely; validation must cover it.
- **No new third-party dependencies** — path/env resolution and markdown table parsing use the standard library, consistent with `md-to-word` and `summarize-meeting-decisions`.
