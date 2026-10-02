# Proposal

## Why

`archy-nfr-miner` produces reviewed NFR registries per run, but nothing turns them into the project's actual NFR document. Merging by hand is error-prone: runs number their entries independently (`NFR-001` in every run), the same requirement shows up in several runs and in the existing document, and a newer source can silently contradict a committed target. A skill is needed that treats the existing NFR document (the golden copy, GC) as the source of truth, applies the runs as deltas, surfaces conflicts and unresolved questions first, and produces a reviewable draft that differs from GC only where the deltas justify it.

## What Changes

- New skill `archy-nfr-propose`, with the same stage shape as the miner: pre-flight, Stage 0 (resolve), Stage 1 (merge and draft, with auto-validation), Stage 2 (review, park and resume), and hand-off. Every stage updates the draft's `state.yaml`.
  - **Pre-flight**: same taxonomy init and load as the miner, plus the new templates `nfr-req-tmpl.md` and `nfr-draft-log.md`.
  - **Stage 0**:
    - Resolves the GC document from the `nfr_doc` parameter, else `NFR_PATH` (the process env, then the repo-root `.env`), with relative paths taken from the repo root, not the skill folder. There is no hardcoded fallback path. When no GC exists, a new document is created from `nfr-req-tmpl.md` at that path; with no path at all, the skill asks.
    - Discovers input runs under `ai-workflow/nfr-state/` and lets the user multi-select them, with the most recent marked. It warns when a run has no `state.yaml` or is not `finished`.
    - Creates or resumes a draft folder under `ai-workflow/nfr-draft/<draft_id>/`.
  - **Stage 1**:
    - Input is only each run's `nfr-registry-log.md`. Closed questions and dropped rows are not carried over.
    - Deduplicates across runs, automatically or through a question, depending on match confidence.
    - Matches each delta against GC records: `SAME` (dropped as no new information), additive `UPDATE`, `NEW`, `MOVED` (type change), or `CONFLICT` when a delta's value differs from GC.
    - Issues new IDs in GC format (`<TYPE>-###`), continuing GC numbering. GC IDs never change. The run's original `NFR-###` is kept in a trace.
    - Writes two files: `draft.md`, which is the future NFR document (GC with only its managed table rows changed, everything else byte-identical), and `nfr-draft-log.md`, which holds the change set, trace, open questions, conflicts, and dropped rows.
    - Auto-validation, including a scripted preservation check, must pass before Stage 2.
  - **Stage 2**: reuses the miner's review loop over the change set. Each apply pass re-patches and re-validates the draft.
  - **Hand-off**: sets `active_stage: hand-off` and suggests `/archy-nfr-apply` to move the draft into the target document.
- Taxonomy changes (version `1.1.1` → `1.2.0`):
  - Add `nfr-req-tmpl.md`, the GC document template. Fix it as follows:
    - add an `ID` column (`BD-###`) to Business Drivers
    - add the missing table separator rows to the Assumptions and Constraints tables
    - use the catalog name `Performance & Scalability` in the QAR sample
    - rename `Constrains` to `Constraints`
    - give the Business Drivers sample a real goal
    - fix the typos in the intro text
  - Add `nfr-draft-log.md`, the propose log template.
  - Extend `nfr-state.yaml`:
    - an optional `target_sad_docs[]` list
    - the file status `merged`
    - the stage `hand-off`
    - `files_4_review` documented as holding source files (miner) or run registries (propose)
- `archy-nfr-miner/references/nfr-review.md` generalized so that callers can pass their ID format. Behavior for the miner is unchanged.

## Capabilities

### New Capabilities
- `nfr-propose`: drafting the NFR document from a golden copy plus the reviewed miner registries. Covers GC and run resolution, the draft folder and state, cross-run dedupe, delta-vs-GC matching and ID issuance, format-preserving draft rendering, validation, review, and hand-off.

### Modified Capabilities
- `nfr-taxonomy-init`: the shipped taxonomy SHALL also include the NFR document template (`nfr-req-tmpl.md`) and the propose log template (`nfr-draft-log.md`). The state template SHALL support propose drafts (`target_sad_docs`, the `merged` status, and the `hand-off` stage).

## Impact

- New: `skills/archy-nfr-propose/`:
  - `SKILL.md`
  - `references/nfr-match.md`
  - `scripts/resolve_draft.py`, `scripts/gc_tables.py`, `scripts/check_draft.py`
  - `tests/`
- Changed:
  - `skills/archy-init-nfr-taxonomy/SKILL.md` (version `1.2.0`)
  - `taxonomy/nfr-req-tmpl.md` (fixed; currently untracked)
  - `taxonomy/nfr-draft-log.md` (new)
  - `taxonomy/nfr-state.yaml`
  - taxonomy init tests
- Changed: `skills/archy-nfr-miner/references/nfr-review.md` gains an `id_format` input. The miner passes the current format.
- Env: `NFR_PATH` (process env, else the repo-root `.env`; shown in `.env.example`) is the default GC path, relative to the repo root. The skill has no hardcoded fallback.
- Runtime output: `ai-workflow/nfr-draft/<draft_id>/`, containing `state.yaml`, `draft.md`, and `nfr-draft-log.md`. The skill never writes the GC document. That is the job of `/archy-nfr-apply`.
- Out of scope:
  - `/archy-nfr-apply`, including writing the draft into GC and checking GC drift at apply time
  - `/archy-nfr-explore`
  - more than one target document per draft; the schema allows it, but the skill handles exactly one
  - GC documents in formats other than the template's markdown tables
