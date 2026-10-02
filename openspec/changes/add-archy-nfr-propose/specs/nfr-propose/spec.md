# Spec Delta

## Purpose

Draft the project's NFR document by treating the existing document (the golden copy, GC) as the source of truth and applying reviewed `archy-nfr-miner` registries as deltas. Conflicts and open questions come first, and the draft differs from GC only where a reviewed delta justifies it.

## ADDED Requirements

### Requirement: Taxonomy pre-flight
Before any stage runs, the `archy-nfr-propose` skill SHALL run the taxonomy initialization, take its reported target as `taxonomy_dir`, and read these files from it:
- `nfr-priorities.md`
- `business-drivers.md`
- `quality-attributes.md`
- `nfr-state.yaml`
- `nfr-registry-log.md`
- `nfr-req-tmpl.md`
- `nfr-draft-log.md`

If any of them is missing, the skill SHALL stop, name the missing file, and write nothing. It SHALL NOT fall back to any other vocabulary. Once Stage 0 resolves the draft folder, the pre-flight outcome (taxonomy version and loaded files) SHALL be the first `state_log` entry of that invocation.

#### Scenario: Taxonomy file missing
- **WHEN** `nfr-req-tmpl.md` is missing after initialization
- **THEN** the skill stops, names `nfr-req-tmpl.md`, and creates no draft folder

#### Scenario: Pre-flight recorded
- **WHEN** pre-flight succeeds and Stage 0 resolves a draft folder
- **THEN** that folder's `state.yaml` has a `state_log` entry with gate `pre-flight`, the taxonomy version, and status `finished`

### Requirement: Golden copy resolution
The skill SHALL resolve the target NFR document (GC) path in this order: the `nfr_doc` parameter, else the `NFR_PATH` environment variable, else `NFR_PATH` from the `.env` file at the repository root. The skill SHALL NOT have a built-in default path. A relative path SHALL be resolved against the repository root (the project's git top level, or the working directory outside git), never against the skill folder, and SHALL be recorded repo-relative. If no source gives a path, the skill SHALL ask the user for it without suggesting one, and SHALL NOT guess one. If the resolved file exists, it is the GC, and its format takes precedence over the template. If it does not exist, the skill SHALL tell the user that a new document will be drafted from `nfr-req-tmpl.md` at that path, and SHALL record `exists: false` and `format_source: template`. The skill SHALL NOT write the GC file itself.

#### Scenario: Param wins
- **WHEN** `nfr_doc` is given and `NFR_PATH` is also set
- **THEN** `nfr_doc` is the target, and the resolver reports `source: param`

#### Scenario: Default from env
- **WHEN** `nfr_doc` is not given, `NFR_PATH=./docs/nfr.md` is set in the environment, and that file exists
- **THEN** that file is the GC, and `target_sad_docs[0]` records its path, sha256, `exists: true`, and `format_source: gc`

#### Scenario: Default from .env
- **WHEN** neither `nfr_doc` nor the `NFR_PATH` environment variable is set, and the repo-root `.env` defines `NFR_PATH`
- **THEN** that value is the target, and the resolver reports `source: .env`

#### Scenario: Relative to repo root
- **WHEN** the skill is installed at `.claude/skills/archy-nfr-propose`, the working directory is a subfolder of the repository, and `NFR_PATH=./docs/nfr.md`
- **THEN** the target resolves to `<repo>/docs/nfr.md`, not to a path under the skill folder or the subfolder, and it is recorded as `docs/nfr.md`

#### Scenario: No document yet
- **WHEN** the resolved path does not exist
- **THEN** the draft is created from `nfr-req-tmpl.md`, and `target_sad_docs[0]` records `exists: false` and `format_source: template`

#### Scenario: No path anywhere
- **WHEN** neither `nfr_doc` nor `NFR_PATH` (environment or repo-root `.env`) is set
- **THEN** the skill asks for the target path, without suggesting a default path, before creating any draft folder

### Requirement: Unparseable golden copy
The skill SHALL locate the four sections of the GC by their H2 headings (`Business Drivers & Goals`, `Quality Attributes`, `Assumptions`, `Constraints`) and read the first markdown table in each one. Each row is a record keyed by its `ID`. If a section, its table, or its `ID` column is missing, or if two rows share an ID, the skill SHALL stop, report what is missing, and ask the user to fix the GC. The skill SHALL NOT guess record boundaries.

#### Scenario: Duplicate GC ID
- **WHEN** two rows in the GC's Quality Attributes table both have `QAR-004`
- **THEN** the skill stops, names `QAR-004` and both rows, and writes no draft

### Requirement: Input run selection
The skill SHALL take its inputs only from miner run registries (`<run>/nfr-registry-log.md`), never from `mined/` or `sources/`. When the `runs` parameter is not given, the skill SHALL list the runs under `ai-workflow/nfr-state/` and let the user choose one or more. The list SHALL show each run's ID, stage and step, registry counts, and last update, and SHALL mark the most recently updated run. If there are more runs than the ask-question tool can show, the skill SHALL fall back to a numbered list answered as `1,3,5`. For each selected run that has no `state.yaml`, or whose `active_stage` is not `finished`, the skill SHALL warn the user, suggest finishing that run's review with `archy-nfr-miner`, and ask whether to include the run anyway. The chosen runs SHALL be recorded in `files_4_review`, each with its registry path and sha256.

#### Scenario: Multi-select with most recent marked
- **WHEN** `ai-workflow/nfr-state/` holds three finished runs
- **THEN** the skill offers all three for multi-selection, marking the most recently updated one

#### Scenario: Parked run
- **WHEN** the user selects a run whose `active_step` is `review-parked`
- **THEN** the skill warns that the run is unreviewed, suggests `archy-nfr-miner` to finish it, and includes it only if the user confirms

#### Scenario: Run without state
- **WHEN** a selected folder has `nfr-registry-log.md` but no `state.yaml`
- **THEN** the skill warns about the missing state, and if the run is included anyway, it is recorded with reason "no state.yaml"

### Requirement: Draft folder and resume
Each draft SHALL live in `ai-workflow/nfr-draft/<draft_id>/` and contain these files:
- `state.yaml`, created from the taxonomy's `nfr-state.yaml`, with `active_skill: archy-nfr-propose`
- `draft.md`, the future NFR document
- `nfr-draft-log.md`, created from the taxonomy's `nfr-draft-log.md`

`draft_id` SHALL be the optional `draft` parameter, or else `<target-doc-slug>-<yyyymmdd-hhmm>`. A draft SHALL be identified by its target document path together with its set of input registry paths. When an existing draft matches this identity, the skill SHALL offer to resume it at its recorded stage and step, or to start fresh. Starting fresh archives the old folder as `<draft_id>-archived-<yyyymmdd-hhmm>`. On resume, an input registry whose sha256 has changed SHALL be marked `stale`, and the skill SHALL offer to merge it again. A GC whose sha256 has changed since the draft started SHALL be reported, and the skill SHALL offer to rebuild the draft from the current GC.

#### Scenario: Resume in a new conversation
- **WHEN** a draft for the GC and runs A and B was parked in review, and the skill is invoked again with the same GC and the same runs
- **THEN** the skill offers to resume the review of that draft

#### Scenario: Run reviewed again after merge
- **WHEN** run A's registry changed after the draft merged it
- **THEN** run A is reported as `stale`, and the skill offers to merge it again

### Requirement: Delta carry-over
From each input registry, the skill SHALL carry over entries with status `Confirmed`, `Auto`, `TBD`, or `TO REVIEW`, together with their open questions (status `TO REVIEW`) and open conflicts. It SHALL NOT carry over closed questions or `## Dropped` rows. Every carried entry SHALL keep a reference to its origin in the form `<run_id>/NFR-###`.

#### Scenario: Resolved question not repeated
- **WHEN** run A's `Q3` is `Closed` and its answer was applied to `NFR-005`
- **THEN** the draft log has no question derived from `Q3`, and the delta for `NFR-005` carries the answered value

### Requirement: Cross-run deduplication
Before matching against GC, the skill SHALL compare carried entries across runs and give each pair of the same type a match confidence:
- 95: same category, same metric, near-identical wording
- 85: same category and the same measured subject; one side has no metric
- 70: same category and similar meaning, but different wording
- below 70: different requirements

At 85 or above, with no contradicting metric values, the pair SHALL be merged automatically: keep every origin reference, keep the metric that is present, and keep the higher confidence. At 70, the skill SHALL keep both entries as `TO REVIEW` with an open question asking whether they are the same requirement. When the two entries state different metric values for the same subject, the skill SHALL record a conflict and merge neither.

#### Scenario: Same requirement in two runs
- **WHEN** run A and run B both state "Checkout must respond within 300 ms at p95"
- **THEN** the draft log has one entry whose trace lists both `A/NFR-00x` and `B/NFR-00y`

#### Scenario: Different targets in two runs
- **WHEN** run A states "RTO 1 hour" and run B states "RTO 4 hours" for the payment API
- **THEN** a conflict row names both origins and values, and both entries are `TO REVIEW`

### Requirement: Delta matching against the golden copy
The skill SHALL match each deduplicated delta against the GC records of the same type and give it exactly one disposition:
- `SAME`: it matches a GC record and adds nothing. The delta is recorded in `## Dropped` with the reason "already in GC as <ID>", and the draft is not changed.
- `UPDATE`: it matches a GC record and only fills gaps (an empty metric or priority, for example) without changing any existing value. The GC record is enriched in place.
- `CONFLICT`: it matches a GC record and states a different value for a field the GC record already fills. The skill SHALL record a conflict with the GC value as A and the delta value as B, set the entry to `TO REVIEW`, add an open question, and leave the GC record unchanged until review.
- `MOVED`: it matches a GC record but belongs to a different NFR type. It SHALL be `TO REVIEW` with an open question, and it takes effect only when confirmed in review.
- `NEW`: it matches no GC record.

A GC record that no delta matches SHALL stay unchanged: a requirement missing from the runs is never treated as removed.

#### Scenario: No new information
- **WHEN** GC has `QAR-002` with "p95 < 300 ms" and a delta states the same
- **THEN** the delta's disposition is `SAME`, it is in `## Dropped` with "already in GC as QAR-002", and `draft.md` is unchanged for that row

#### Scenario: Delta disagrees with GC
- **WHEN** GC `QAR-002` states "p95 < 300 ms" and a delta states "p95 < 250 ms"
- **THEN** a conflict records A = "p95 < 300 ms" (GC `QAR-002`) and B = "p95 < 250 ms" (delta origin), and `draft.md` still shows "p95 < 300 ms"

#### Scenario: Gap filled
- **WHEN** GC `QAR-005` has no priority and a confirmed delta for the same requirement has priority `High`
- **THEN** the disposition is `UPDATE`, and the draft row for `QAR-005` shows `High` with its ID unchanged

#### Scenario: Absence is not removal
- **WHEN** GC holds `CSTR-001` and no selected run mentions it
- **THEN** `CSTR-001` appears unchanged in `draft.md`

### Requirement: Identifier issuance
GC IDs SHALL NEVER change. IDs SHALL have the form `<TYPE>-###`, with `BD`, `QAR`, `ASM`, or `CSTR` as the type. A `NEW` entry SHALL receive the next number for its type, above the highest ID of that type in GC and in the retired IDs recorded by earlier draft logs for the same target document. Moving a QAR to another quality-attribute category SHALL keep its ID. A confirmed `MOVED` entry SHALL retire its old ID and receive a new ID of the new type. A retired ID SHALL NOT be reused. Entries of type `TBD` SHALL NOT receive an ID or be rendered until their type is decided in review. The mapping from each origin `<run_id>/NFR-###` to its target ID and disposition SHALL be recorded in `## Trace` of `nfr-draft-log.md`.

#### Scenario: Next number
- **WHEN** GC's highest QAR ID is `QAR-012` and two `NEW` QAR entries are merged
- **THEN** they receive `QAR-013` and `QAR-014`

#### Scenario: Category change keeps ID
- **WHEN** review changes `QAR-007` from `Performance & Scalability` to `Resilience`
- **THEN** the draft row keeps `QAR-007` and shows `Resilience`

#### Scenario: Type change retires ID
- **WHEN** review confirms that `QAR-007` is a constraint
- **THEN** `QAR-007` is retired in the log, and a new `CSTR-###` row replaces it in the draft

### Requirement: Format-preserving draft
`draft.md` SHALL be a copy of the GC, or of `nfr-req-tmpl.md` without its sample rows when there is no GC, in which only the data rows of the four managed tables differ. Everything else SHALL be byte-identical to the base, including headings, intro text, other sections, custom columns, and row order of untouched rows. Only entries whose status is `Confirmed`, `Auto`, or `TBD`, and whose disposition is `NEW`, `UPDATE`, or a confirmed `MOVED`, SHALL be rendered. Open questions, `TO REVIEW` entries, unresolved conflicts, and dropped rows SHALL NOT appear in the draft. A new QAR row SHALL be inserted after the last row of the same quality-attribute category, or at the end of the table if there is none. Other new rows SHALL be appended to their table. For columns the skill does not know (custom GC columns), new rows SHALL leave the cell empty and updated rows SHALL keep the existing value.

#### Scenario: Custom text kept
- **WHEN** the GC has a custom paragraph under `## Quality Attributes` and an extra H2 `## Glossary`
- **THEN** both appear byte-identical in `draft.md`

#### Scenario: Open items stay out
- **WHEN** a delta is `TO REVIEW` with an open question
- **THEN** no row for it appears in `draft.md`

### Requirement: Draft validation
Before Stage 2, the skill SHALL validate the draft and its log:
- Preservation: diffing the base against `draft.md` changes only managed-table rows claimed by a `NEW`, `UPDATE`, or `MOVED` trace entry.
- Every managed table is a valid markdown table, and every row has the header's column count.
- Every rendered ID is unique, matches `<TYPE>-###`, and sits in its type's section.
- Every rendered QAR or BD category is a verbatim catalog name.
- Nothing that must stay out of the draft (see Format-preserving draft) was rendered.
- Every carried delta has exactly one `## Trace` row with a disposition.
- Every `TO REVIEW` entry and every conflict has an open question.

The preservation and table checks SHALL be deterministic (scripted). The skill SHALL try to fix failures at most twice. An entry that still fails SHALL be removed from the draft, set to `TO REVIEW` with an open question naming the check, and logged with `status: fail`. A preservation failure that cannot be attributed to an entry SHALL stop the skill before Stage 2.

#### Scenario: Stray edit detected
- **WHEN** rendering accidentally changes a word in the Assumptions intro text
- **THEN** validation reports the changed line, and the skill does not enter Stage 2 until it is fixed

### Requirement: Stage 1 summary
At the end of Stage 1, the skill SHALL show one table with one row per input run and a total row. The columns SHALL be the count of carried entries, then counts per disposition (`NEW`, `UPDATE`, `SAME`, `MOVED`, `CONFLICT`), then counts of merged cross-run duplicates, open questions, and conflicts. The total row SHALL be counted after deduplication.

#### Scenario: Totals after dedupe
- **WHEN** runs A and B carry 10 and 8 entries and 3 pairs are merged across them
- **THEN** the total row shows 15 entries after deduplication

### Requirement: Review and draft sync
Stage 2 SHALL run the shared NFR review loop in the main conversation. Its scope is every draft-log entry whose disposition is not `SAME`, plus open questions, conflicts, and `## Dropped`. Entries SHALL be addressed by their target ID (for example `QAR-013`). Entries without a target ID yet (type `TBD`) SHALL be addressed by their origin reference. The number-only shorthand SHALL NOT be accepted. Conflict resolutions SHALL behave as follows:
- picking the GC value leaves the GC record unchanged and moves the delta to `## Dropped` as superseded
- picking the delta value makes the entry an `UPDATE` of that GC record, keeping its ID
- keeping both requires the delta to be re-read as a distinct requirement (`NEW`)

After every apply pass, the skill SHALL re-render the affected rows in `draft.md`, re-run validation, and record the pass in `state_log`. Parking SHALL set `active_step: review-parked`, and the next invocation with the same GC and runs SHALL resume the review.

#### Scenario: Conflict resolved for delta
- **WHEN** the user resolves the conflict on `QAR-002` by picking B ("p95 < 250 ms")
- **THEN** `draft.md` shows `QAR-002` with "p95 < 250 ms", and the trace records `UPDATE` with the superseded GC value

#### Scenario: Park and resume
- **WHEN** the user parks the review and invokes the skill again with the same GC and runs in a new conversation
- **THEN** the skill resumes the review with only the undecided items

### Requirement: State tracking
Every stage and step boundary (pre-flight, Stage 0, each Stage 1 step, each review apply pass, and hand-off) SHALL update `state.yaml`: `active_stage`, `active_step`, per-input status (`pending`, `merged`, `skipped`, or `stale`), and `update_on`, and SHALL append a `state_log` entry. Every session that touches a draft SHALL append its session ID. Only the main thread SHALL write `state.yaml`, `draft.md`, and `nfr-draft-log.md`.

#### Scenario: Interrupted merge
- **WHEN** the process stops after run A is merged and before run B is
- **THEN** `state.yaml` shows run A as `merged`, run B as `pending`, and the Stage 1 step reached

### Requirement: Hand-off
When the review is complete, the skill SHALL set `active_stage: hand-off` and log it, show the paths of `draft.md`, `nfr-draft-log.md`, and the target document, give one line of counts (new, updated, moved, retired, still open, dropped), and suggest `/archy-nfr-apply` to move the draft into the target document. It SHALL NOT modify the target document.

#### Scenario: Review complete
- **WHEN** the review queue is empty
- **THEN** `state.yaml` shows `active_stage: hand-off`, the target document is unchanged, and the skill suggests `/archy-nfr-apply`
