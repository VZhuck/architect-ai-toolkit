# Spec Delta

## Purpose

Mine non-functional requirements (quality attribute requirements, business drivers, constraints, assumptions) from source documents into a traceable, run-scoped NFR registry that uses the project's closed taxonomy, then take a human reviewer through the registry to confirm, correct, or drop entries.

## ADDED Requirements

### Requirement: Source path resolution
The `archy-nfr-miner` skill SHALL accept a `path` argument that is a directory, a single file, a glob mask, or a list of any of these (for example `"fileA.md", "fileB.pdf"`). It SHALL resolve `path` to a de-duplicated, sorted list of repo-relative files (`files_4_review`) with extensions `.md`, `.mdx`, `.docx`, or `.pdf`. Directories SHALL be scanned recursively. The resolution SHALL always exclude `working_dir_base`, the taxonomy directory, and hidden folders. When `path` is not given, the skill SHALL ask the user and SHALL NOT guess a path. When resolution yields no files, the skill SHALL stop and report what was resolved and excluded.

#### Scenario: Equivalent forms resolve to the same set
- **WHEN** the skill is invoked once with `docs/payments/`, once with `./docs/payments/*`, and once with `"docs/payments/SAD.docx", "docs/payments/nfr.md"`, where the folder holds exactly those two files
- **THEN** all three invocations resolve to the same `files_4_review`

#### Scenario: Own state is never mined
- **WHEN** the skill is invoked with `path` = `.`
- **THEN** no file under `working_dir_base` or the taxonomy directory appears in `files_4_review`

#### Scenario: Unsupported and empty input
- **WHEN** `path` matches only `.txt` and `.png` files
- **THEN** the skill stops before mining and reports that no supported files were resolved

#### Scenario: Missing path
- **WHEN** the skill is invoked without `path` and there are no unfinished runs
- **THEN** the skill asks the user for the path and does not pick one itself

### Requirement: Taxonomy pre-flight
Before any stage runs, the skill SHALL run the taxonomy initialization, take its reported target as `taxonomy_dir`, and read `nfr-priorities.md`, `business-drivers.md`, `quality-attributes.md`, `nfr-state.yaml`, and `nfr-registry-log.md` from it. If `taxonomy_dir` or any of these files is still missing after initialization, the skill SHALL stop, name the missing item, and ask where to find it. The skill SHALL NOT fall back to any other vocabulary (such as ISO 25010, generic "-ilities", or terms mined from the sources).

#### Scenario: Taxonomy present
- **WHEN** the initialization reports `up-to-date` and all five files exist
- **THEN** the skill states `taxonomy_dir`, the loaded files, the run folder, and the files it maintains, then continues to Stage 0

#### Scenario: Taxonomy file missing
- **WHEN** `quality-attributes.md` is missing from `taxonomy_dir` after initialization
- **THEN** the skill stops, names `quality-attributes.md`, asks where to find it, and writes no run state

### Requirement: Run-scoped working directory
The skill SHALL keep all intermediate state for a run in `{working_dir_base}/{run_id}/`, where `working_dir_base` defaults to `ai-workflow/nfr-state`. The run folder SHALL contain `state.yaml` (created from the taxonomy's `nfr-state.yaml` template), `nfr-registry-log.md` (created from the taxonomy's `nfr-registry-log.md` template), per-file mining output, and normalized sources. `run_id` SHALL be the optional `run` argument when given, otherwise `<common-parent-slug>-<yyyymmdd-hhmm>`. The run ID is a label only: runs SHALL be identified by their resolved file set.

#### Scenario: Default location
- **WHEN** the skill starts a new run for `docs/payments/` without `working_dir_base` or `run`
- **THEN** a folder `ai-workflow/nfr-state/docs-payments-<yyyymmdd-hhmm>/` is created, containing `state.yaml` and `nfr-registry-log.md`

#### Scenario: Explicit run name and base
- **WHEN** the skill is invoked with `working_dir_base=tmp/eval` and `run=case-01`
- **THEN** all run state is written under `tmp/eval/case-01/`

### Requirement: Run discovery and resume
In Stage 0, the skill SHALL compare the resolved file set with the `files_4_review` of every existing run under `working_dir_base`, and act on the best match as follows:
- identical: offer to resume at the recorded stage and step, or to start fresh
- superset: offer to add the new files to that run, or to start a new run
- subset: offer to resume that run, or to start a new run for these files only
- partial overlap: list the overlapping runs and default to a new run
- no overlap: start a new run without asking

When `path` is not given, the skill SHALL list unfinished runs and ask which to continue. Every session that touches a run SHALL append its session ID to the run's state.

#### Scenario: Resume after reboot
- **WHEN** a run for `docs/payments/` stopped after mining 2 of 3 files, and the user starts a new conversation and invokes the skill with `docs/payments/*`
- **THEN** the skill reports the existing run's position (stage, step, per-file status) and offers to resume or start fresh
- **AND** on resume, only the unmined file is mined

#### Scenario: Mask grows
- **WHEN** an existing run covers 3 files and the new invocation resolves to those 3 plus `nfr-v2.md`
- **THEN** the skill offers to add `nfr-v2.md` to the existing run as pending, or to start a new run

#### Scenario: Session recorded
- **WHEN** a second conversation resumes a run
- **THEN** the run's state lists both session IDs

### Requirement: Changed source detection
The skill SHALL record a sha256 for each file in `files_4_review`. On resume, a file whose content hash has changed SHALL be reported as stale, and the skill SHALL offer to re-mine only that file. On re-mining, entries whose verbatim evidence is still present SHALL keep their NFR IDs. Entries whose evidence has disappeared SHALL become `TO REVIEW`, with an open question.

#### Scenario: One source edited
- **WHEN** `SAD.docx` was mined and then edited, and the run is resumed
- **THEN** the skill reports `SAD.docx` as changed and offers to re-mine only that file

### Requirement: Source normalization
Before mining, the skill SHALL convert each `.docx` and `.pdf` source into exactly one markdown file at `{run}/sources/<repo-relative-path>.<ext>.md` (for example `sources/docs/payments/SAD.docx.md`). `.md` and `.mdx` sources SHALL be mined in place. Conversion SHALL be deterministic and tool-based, not model-read. It SHALL keep each paragraph on one line so that line references stay stable, and SHALL keep tables as tables. PDF output SHALL mark each page start with `<!-- page N -->`. `.docx` tracked changes SHALL be accepted. A binary source whose hash has not changed since its last conversion SHALL NOT be converted again. A source that cannot be converted, or that has no extractable text, SHALL be marked `failed` with a reason, and the run SHALL continue with the other files. Images and diagrams are not mined; their count SHALL be logged per file.

#### Scenario: Docx converted once
- **WHEN** `docs/payments/SAD.docx` is normalized twice without changes
- **THEN** `sources/docs/payments/SAD.docx.md` exists, and the second pass reports it as skipped

#### Scenario: PDF page markers
- **WHEN** a three-page text PDF is normalized
- **THEN** its markdown contains `<!-- page 1 -->`, `<!-- page 2 -->`, and `<!-- page 3 -->` in order

#### Scenario: Scanned PDF
- **WHEN** a PDF has no text layer on any page
- **THEN** the file is marked `failed` with reason "no extractable text", and the other files are still mined

### Requirement: Evidence-only mining
Mining a file SHALL require no human interaction, so that each file can be mined independently (for example, in its own subagent). The miner SHALL record only requirements that the source states. It SHALL NOT invent a requirement that no source mentions. Where it cannot make a judgment, it SHALL make the conservative choice, record the reason, and continue. Each candidate SHALL carry the verbatim sentence it came from and a citation:
- `.md` / `.mdx` sources: `file.md:L88`
- `.docx` sources: `SAD.docx (SAD.docx.md:L42)`
- `.pdf` sources: `notes.pdf p12 (notes.pdf.md:L310)`

#### Scenario: Citation points at the evidence
- **WHEN** an entry cites `SAD.docx (SAD.docx.md:L42)`
- **THEN** line 42 of `sources/.../SAD.docx.md` contains the entry's verbatim evidence

#### Scenario: No invented requirements
- **WHEN** no source mentions availability
- **THEN** the registry contains no entry about availability

### Requirement: Registry entry format
Each registry entry SHALL have the columns `NFR ID`, `NFR Type`, `NFR Category`, `Verbatim evidence`, `Metrics`, `Source`, `Interpretation`, `Confidence`, `Priority`, `Status`, and `Comments`. `NFR ID` SHALL be `NFR-` followed by a zero-padded number. It SHALL be unique within the run and SHALL never change or be reused. `NFR Type` SHALL be one of `QAR`, `BD`, `CSTR`, `ASM`, or `TBD`. For `QAR` and `BD`, `NFR Category` SHALL be a name taken verbatim from `quality-attributes.md` or `business-drivers.md` respectively. `Metrics` SHALL hold only a measurable target stated by the source, and SHALL be empty otherwise. `Interpretation` SHALL give the reasoning for the type, the category, the priority (when set), and the confidence.

#### Scenario: Category outside the vocabulary
- **WHEN** a statement maps to no name in `quality-attributes.md` or `business-drivers.md`
- **THEN** the entry's type is `TBD`, its status is `TO REVIEW`, and an open question is recorded

#### Scenario: IDs are type-neutral
- **WHEN** a reviewer later changes an entry's type from `TBD` to `QAR`
- **THEN** its `NFR ID` is unchanged

### Requirement: Confidence and automatic status
The miner SHALL give each entry one combined confidence score using these anchors:
- 95: explicit statement, unambiguous category, measurable metric stated
- 85: explicit statement, unambiguous category, and either no metric needed (`CSTR`, `ASM`) or a `BD` with a money, date, or market-position figure
- 70: category inferred between candidates, or a `QAR` without a metric
- 50: vague statement with nothing measurable
- below 40: functional or outside the vocabulary

The miner SHALL set status `Auto` only when confidence is at least 85 and the entry meets the completeness rules for its type:
- all types: verbatim evidence, a source citation, and a category in the vocabulary (for `QAR` and `BD`)
- `QAR`: a metric
- `BD`: a money, date, or market-position figure
- `CSTR`: what it restricts
- `ASM`: what is assumed, and what breaks if it is false
- `TBD`: never `Auto`

A priority is not required for `Auto`. The miner SHALL set a priority only when the source states a business impact that matches a definition in `nfr-priorities.md`, and SHALL quote that impact in `Interpretation`. Otherwise it SHALL leave the priority empty.

#### Scenario: Measured QAR becomes Auto without priority
- **WHEN** a source says "Checkout must complete in under two seconds at p95" and states no business impact
- **THEN** the entry is `QAR` / `Performance & Scalability`, with `Metrics` = `p95 < 2 s`, confidence 95, an empty priority, and status `Auto`

#### Scenario: Unmeasured QAR is not Auto
- **WHEN** a source says "the system should be fast"
- **THEN** the entry's confidence is at most 70, its status is `TO REVIEW`, and an open question asks for the target

### Requirement: Mining statuses, open questions, and dropped items
During mining, the skill SHALL set only the statuses `Auto`, `TO REVIEW`, or `Drop`. Every `TO REVIEW` entry SHALL have at least one row in `## Open Questions` that references its `NFR ID`. The miner MAY put a value in an open question's `Proposed default` only to fill a gap in a requirement that a source states, and SHALL mark such a value as proposed by `SKILL`. A proposed default SHALL NOT make an entry `Auto`. A missing priority alone SHALL NOT create an open question. Functional or out-of-scope statements SHALL get an `NFR ID` and SHALL be recorded only in `## Dropped`, together with the reason and who dropped them (`SKILL` or `USER`). An entry dropped later SHALL move from the registry to `## Dropped`.

#### Scenario: Functional statement
- **WHEN** a source says "the user can export invoices to CSV"
- **THEN** it appears in `## Dropped` with an `NFR ID`, reason "functional behaviour", and `Dropped by` = `SKILL`, and it does not appear in the registry

#### Scenario: Gap default is marked
- **WHEN** a source states an availability target without a measurement window
- **THEN** any proposed window in the open question is marked as proposed by `SKILL`, and the entry stays `TO REVIEW`

### Requirement: Merge, deduplication, and conflicts
After all files are mined, the skill SHALL merge the per-file results in the main thread: assign final `NFR ID`s, merge duplicates of the same requirement across files into one entry that keeps every citation, and record each case where two sources give different targets for the same type and category as a row in `## Conflicts` with both values and sources. It SHALL NOT silently choose between them. Only the main thread SHALL write the run's registry and state files.

#### Scenario: Cross-file conflict
- **WHEN** `SAD.docx` states "RTO 4 hours" and `nfr.md` states "RTO 1 hour"
- **THEN** `## Conflicts` records both values with their sources, and neither value is dropped

#### Scenario: Duplicate across files
- **WHEN** two files state the same requirement in the same words
- **THEN** the registry has one entry citing both sources

### Requirement: Registry validation
After merging, the skill SHALL check that:
- every entry has a confidence
- NFR IDs are unique
- every `Auto` entry meets the automatic-status rules
- every status set by mining is `Auto`, `TO REVIEW`, or `Drop`
- every `TO REVIEW` entry has an open question
- every dropped ID appears only in `## Dropped`
- every citation points to a line that contains the verbatim evidence

The skill SHALL try to fix a failing entry at most twice. An entry that still fails SHALL be set to `TO REVIEW`, given an open question, and logged as a failure in the run's state log.

#### Scenario: Unfixable Auto entry
- **WHEN** an `Auto` entry still has no metric after two fix attempts
- **THEN** its status is `TO REVIEW`, an open question exists for it, and the state log records the failed check

### Requirement: Mining summary
At the end of Stage 1, the skill SHALL show one summary table with one row per source file and the columns `File`, `BD`, `QAR`, `CSTR`, `ASM`, `TBD`, `By status`, and `Total`. The type columns SHALL count that file's registry candidates before merging. `By status` SHALL read `Auto: n, TO REVIEW: n, Dropped: n`, and `Total` SHALL be the sum of those statuses. Dropped items have no type, so they SHALL be counted only in `By status` and `Total`. A failed file SHALL be one row with `failed: <reason>` in `By status` and `-` in the counts. The last row, `TOTAL (merged)`, SHALL show the same counts after merging. The table SHALL be followed by one line with the counts of mined candidates, merged duplicates, registry entries, dropped items, open questions, conflicts, entries without priority, and failed files.

#### Scenario: One row per file
- **WHEN** `docs/payments/SAD.docx` yields 1 `BD`, 5 `QAR`, and 1 `ASM` candidate (4 `Auto`, 3 `TO REVIEW`) and 1 dropped item
- **THEN** its row is `| docs/payments/SAD.docx | 1 | 5 | 0 | 1 | 0 | Auto: 4, TO REVIEW: 3, Dropped: 1 | 8 |`

#### Scenario: Totals explain dedupe
- **WHEN** 47 candidates are mined and 5 are merged as duplicates
- **THEN** the summary shows 47 mined and 5 merged duplicates, and the `TOTAL (merged)` row's total equals 42

### Requirement: Run state tracking
The run's `state.yaml` SHALL record:
- `run_id`
- the original path arguments
- `taxonomy_dir` and the taxonomy version
- session IDs
- the active skill, stage, and step
- for each file: path, sha256, normalized path, and status (`pending`, `mined`, `failed`, `skipped`, or `stale`)
- a timestamp with timezone
- an append-only `state_log` of events (date, skill, gate, change, status)

The skill SHALL update the state at every stage and step boundary, so that an interruption can be resumed.

#### Scenario: Interrupted mid-mining
- **WHEN** the process stops after one of three files is mined
- **THEN** `state.yaml` shows that file as `mined`, the others as `pending`, and the active step as mining

### Requirement: Human review loop
Stage 2 SHALL run in the main conversation, never in a subagent. It SHALL start with one overview table that lists every entry in scope, including dropped items, with the columns `NFR ID`, `Type`, `Category`, `Statement` (short), `Status`, `Conf`, `Prio`, and `Open` (the `Q#` and `C#` IDs still open for the entry). Rows SHALL be grouped in this order:
1. entries with a conflict
2. `TBD` types
3. other `TO REVIEW` entries
4. `Auto` entries
5. dropped items

A single hint line of short commands SHALL follow the table. The skill SHALL then ask the user to pick a mode: guided, commands, or park.

In guided mode, the skill SHALL review one entry at a time with a single multi-tab question, using the host's ask-question tool:
- Tabs SHALL come in this order: each open question, each conflict, `Priority` (only if the entry has none), and `Decision`. The submit step comes last.
- The first tab SHALL show the entry's verbatim evidence and source.
- Options for an open question SHALL be the proposed default (marked `SKILL` or `USER`), values found in the sources, `TBD`, and free text.
- Options for a conflict SHALL be value A, value B, or keeping both.
- Options for the decision SHALL be accept, drop, accept as TBD, or skip.
- When an entry needs more tabs than the tool allows, the extra tabs SHALL go into a follow-up question, and `Decision` SHALL always be in the last one.

After the entries that need an answer, the skill SHALL ask once to accept all `Auto` entries, ask for missing priorities with one tab per entry, and ask once to confirm the dropped items. If no ask-question tool is available, guided mode SHALL fall back to showing one entry at a time as text.

In command mode, the user answers with compact commands. Both a short and a long form SHALL be accepted, and wherever an NFR ID is expected, its number alone SHALL be accepted (`4` = `NFR-004`):

| Short | Long |
| --- | --- |
| `a 3`, `a @auto [TYPE]` | `NFR-003 ok`, `auto ok [TYPE]` |
| `d 5 <reason>` | `NFR-005 drop <reason>` |
| `u 13` | `NFR-013 restore` |
| `p 1,3,8 High` | `prio NFR-1,3,8 High` |
| `t 9 <why>` | `NFR-009 tbd "<why>"` |
| `n 11 <text>` | `NFR-011 note "<text>"` |
| `q4=<value>`, `q4 ok`, `q4 no` | `Q4 = "<value>"`, `Q4 ok`, `Q4 no` |
| `c1 a`, `c1 b`, `c1 both` | `C1 pick A`, `C1 pick B`, `C1 both` |

Decisions SHALL be applied as follows:
- approved: the entry becomes `Confirmed`
- noted: the note goes into `Comments`
- rejected: the entry moves to `## Dropped` with `Dropped by` = `USER`
- accepted gap: the entry becomes `TBD`
- skipped: the entry stays pending
- category changes: validated against the vocabulary

After each apply, the skill SHALL echo the changes (for example `NFR-007: TO REVIEW -> Confirmed, prio High`), log them, and then show only the items that are still pending or were revised. The loop SHALL end when the queue is empty or the user parks. Parking SHALL save the position so that Stage 0 can resume the review.

#### Scenario: Overview table
- **WHEN** Stage 2 starts on a registry with a conflict on `NFR-004`, an `Auto` entry `NFR-001`, and a dropped item `NFR-013`
- **THEN** one table lists all three, `NFR-004` first with `C1` in `Open`, then `NFR-001`, then `NFR-013` with status `Drop`, followed by the hint line and the mode question

#### Scenario: Guided card
- **WHEN** guided mode reaches `NFR-004`, which has open question `Q2`, conflict `C1`, and no priority
- **THEN** one question is asked with the tabs `Q2`, `C1`, `Priority`, and `Decision` in that order, followed by submit
- **AND** all four answers are applied in one pass and echoed

#### Scenario: Batch decisions
- **WHEN** the user replies `a 3; d 5 functional; q4=p95 < 300ms`
- **THEN** NFR-003 is `Confirmed`, NFR-005 is in `## Dropped` with `Dropped by` = `USER`, Q4's value is applied to its linked entry, and only the remaining items are shown again
- **AND** the long forms `NFR-003 ok`, `NFR-005 drop functional`, and `Q4 = "p95 < 300ms"` give the same result

#### Scenario: Invalid category rejected
- **WHEN** the user sets an entry's category to a name that is not in the vocabulary
- **THEN** the change is refused, and the valid category names for that type are shown

#### Scenario: Park and resume
- **WHEN** the user parks the review, then invokes the skill on the same path in a new conversation
- **THEN** Stage 0 offers to resume the review with only the undecided items

### Requirement: Completion hand-off
When the review is complete, the skill SHALL update the run state to finished, show the paths of `state.yaml` and `nfr-registry-log.md`, and suggest the next steps `/archy-nfr-explore` (challenge the registry and find missing NFRs) and `/archy-nfr-propose` (merge with the golden copy and draft the NFR document).

#### Scenario: Finished run
- **WHEN** the review queue is empty
- **THEN** `state.yaml` records the run as finished, and the skill lists both files and both next-step skills
