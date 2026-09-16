# nfr-analysis

## Purpose

Mine requirements, meeting notes, RFPs, and transcripts for non-functional requirement signals, classify them against closed catalogs of business drivers and quality attributes, agree measurable targets and priorities with the user, and maintain a project's Non-Functional Requirements document across repeated runs without losing human edits or confirmed priorities.

## Requirements

### Requirement: Parameter resolution

The `aait-nfr` skill SHALL accept exactly two parameters, `path` and `nfrPath`, in addition to the optional `phase` argument. `path` is a directory or exact file to analyze. `nfrPath` is the target Non-Functional Requirements document to create or maintain. The skill SHALL resolve `nfrPath` in three steps: an explicit `--nfr-path` argument, then the `.env` key `NFR_PATH`, then by listing the markdown documents in `sad/` and asking the user to select an existing document or name a new one. The skill SHALL NOT accept draft or trace paths as parameters; both SHALL be derived from the resolved `nfrPath` and SHALL be written under `ai-workflow/nfr/`. The path resolver SHALL report whether the derived draft and trace files exist, so that phase can be inferred without a separate filesystem probe. The skill SHALL NOT guess an unresolvable path.

#### Scenario: nfrPath omitted and NFR_PATH is set

- **WHEN** the skill is invoked without `--nfr-path` and `.env` contains `NFR_PATH=./sad/08.Non-Functional-Requirements.md`
- **THEN** the skill resolves `nfrPath` to that value and states the resolved sources, catalog folder, draft, trace, and target paths in one line before proceeding

#### Scenario: nfrPath omitted, NFR_PATH unset, existing document chosen

- **WHEN** the skill is invoked without `--nfr-path`, `.env` has no `NFR_PATH` value, and `sad/` contains markdown documents
- **THEN** the skill lists those documents and asks the user to select one or name a new document, and does not proceed with a guessed or defaulted path

#### Scenario: nfrPath omitted, NFR_PATH unset, new document requested

- **WHEN** the user chooses to create a new document rather than select an existing one
- **THEN** the skill proposes a filename under `sad/` conforming to `rules/sad-sections.instructions.md` — a zero-padded section-number prefix and a Title-Case-Hyphenated title with leading numbering stripped, such as `08.Non-Functional-Requirements.md` — derived from the next free section number, and lets the user adjust it before it is used

#### Scenario: sad directory absent or empty

- **WHEN** `.env` has no `NFR_PATH` value and `sad/` does not exist or contains no markdown documents
- **THEN** the skill asks the user for the target document path directly and does not create a directory or a document without an answer

#### Scenario: path omitted

- **WHEN** the detect phase is entered with no `path` argument
- **THEN** the skill asks the user which directory or file to analyze and does not default to a conventional location

#### Scenario: derived working paths

- **WHEN** `nfrPath` resolves to `./sad/08.Non-Functional-Requirements.md`
- **THEN** the draft path is `ai-workflow/nfr/08.Non-Functional-Requirements.draft.md` and the trace path is `ai-workflow/nfr/08.Non-Functional-Requirements.trace.md`, and neither file is written inside `sad/`

#### Scenario: Draft and trace existence reported

- **WHEN** the path resolver runs against a resolved `nfrPath`
- **THEN** its output states whether the derived draft and trace files exist, alongside the existing report of whether the target document exists

### Requirement: Phase is inferred from the in-flight run

The `aait-nfr` skill SHALL be the single entry point for the pipeline and SHALL accept an optional `phase` argument. When invoked without a phase, the skill SHALL infer the phase from the in-flight run — the draft and trace derived from the resolved `nfrPath` — and SHALL announce the inferred phase and the state it was read from before acting. An explicit `phase` argument SHALL override inference. `nfrPath` SHALL NOT be treated as a phase signal: it is a living document fed by successive source batches, and its existence SHALL only select merge-by-identifier over create at publish time. A run SHALL be considered in flight when the draft exists and the trace's Decision Log carries no terminal publish row after the last recorded gate. The skill SHALL print the phase map alongside the inferred state so the pipeline's phases remain discoverable from a single entry point.

#### Scenario: No draft exists

- **WHEN** the skill is invoked with no phase argument and no draft exists for the resolved `nfrPath`
- **THEN** the skill reports that no run is in flight and asks which sources to analyze, and does not begin mining until the user answers

#### Scenario: Draft in flight resumes at the recorded gate

- **WHEN** the skill is invoked with no phase argument, a draft exists, and the trace's Decision Log records gate 1 as answered with no terminal publish row
- **THEN** the skill announces that the run is mid-refine at gate 2 and resumes there, rather than re-mining the sources or re-asking gate 1

#### Scenario: Completed run is not mistaken for an in-flight one

- **WHEN** the skill is invoked with no phase argument, a draft exists, and the trace's Decision Log carries a terminal publish row
- **THEN** the skill reports that the previous run is complete and offers a new detect run against fresh sources, and does not offer to re-publish the completed draft

#### Scenario: Living document with no draft

- **WHEN** the resolved `nfrPath` exists and no draft is present
- **THEN** the skill treats this as a new maintenance run starting at detect, and the existence of the target document affects only identifier continuation and merge behaviour at publish

#### Scenario: Explicit phase overrides inference

- **WHEN** the skill is invoked with an explicit phase that differs from the inferred one
- **THEN** the requested phase runs, and the skill states both the inferred phase and the override it was given

#### Scenario: Draft present but trace absent

- **WHEN** a draft exists and the trace file has been deleted, so the gate cannot be determined
- **THEN** the skill SHALL say that it cannot determine the in-flight gate and ask the user which phase to run, and SHALL NOT guess a gate or silently restart the pipeline

#### Scenario: Validate needs no in-flight run

- **WHEN** the skill is invoked for the validate phase
- **THEN** validation runs against the requested document without requiring a draft, a trace, or an in-flight run, and phase inference is not consulted

### Requirement: Catalogs are a hard-closed vocabulary

The skill SHALL treat `templates/business-drivers.md` and `templates/quality-attributes.md` as closed vocabularies. It SHALL reproduce attribute names with exact wording and casing, and SHALL NOT invent, split, merge, paraphrase, or re-case an attribute name. A candidate that maps to no catalog row SHALL be recorded as an open question. The skill SHALL NOT add a row to either catalog file.

#### Scenario: Candidate fits no catalog attribute

- **WHEN** a mined candidate matches no row in either catalog
- **THEN** the candidate is written to the trace file's open-questions section with the closest catalog attribute proposed for the user's consideration, and no new catalog row is created

#### Scenario: Attribute name paraphrased

- **WHEN** a classification step would record `Security` or `Privacy and Data Minimization` in place of the catalog's `Security & Privacy`
- **THEN** the catalog name `Security & Privacy` is used verbatim instead

#### Scenario: Catalog file missing

- **WHEN** any of `business-drivers.md`, `quality-attributes.md`, or `qa-priorities.md` is missing or unreadable
- **THEN** the skill stops, names the missing file, and asks where to find it, and does not fall back to ISO 25010, generic "-ilities", or vocabulary mined from the sources

### Requirement: Source mining runs in isolated subagents

The detect phase SHALL dispatch one subagent per source file, in parallel, so that source file contents do not enter the main conversation. Each subagent SHALL return candidate rows in a fixed schema. The main thread SHALL validate every attribute name in a returned batch against the catalogs and SHALL reject a batch containing a name absent from them.

#### Scenario: Directory of sources

- **WHEN** `path` resolves to a directory containing text-bearing files
- **THEN** one mining subagent is dispatched per file in parallel, and only the merged candidate rows — not the file contents — appear in the main conversation

#### Scenario: Large source set

- **WHEN** the resolved directory holds more than approximately 30 candidate files
- **THEN** the skill lists what it found and asks which subset matters before dispatching agents

#### Scenario: Agent returns an off-catalog attribute name

- **WHEN** a mining subagent returns a candidate whose attribute name is not an exact match for a catalog row
- **THEN** the main thread rejects that batch and re-requests it, rather than accepting or silently correcting the name

#### Scenario: Non-text files present

- **WHEN** the resolved directory contains binaries, images, or lock files
- **THEN** those files are skipped and are not dispatched to a mining subagent

### Requirement: Candidates are classified by an ordered discriminator ladder

The skill SHALL classify each candidate by evaluating tests in a fixed order, taking the first match: functional behaviour (dropped), quality attribute requirement, constraint, assumption, business driver, then open question. The fitness-function test SHALL be evaluated before the business-outcome test.

#### Scenario: Compliance statement with a mechanism

- **WHEN** a candidate reads "System shall be compliant to GDPR; PII removed no later than 30 days after a request is received"
- **THEN** it is classified as a quality attribute requirement under `Security & Privacy`, because a fitness function could assert it, and it is not recorded as a business driver

#### Scenario: Penalty exposure with a date

- **WHEN** a candidate reads "CompanyX will face a penalty fee if ComplianceX is not completed by 30/06/2027"
- **THEN** it is classified as a business driver under `Risk & Compliance`, because it names a business consequence with a date and no mechanism

#### Scenario: Technology mandate

- **WHEN** a candidate reads "must use the enterprise IDAM platform"
- **THEN** it is classified as a constraint, because it removes design options and cannot be traded off

#### Scenario: Functional behaviour

- **WHEN** a candidate describes behaviour the system performs, such as "user can reset their password"
- **THEN** it is dropped, and recorded in the trace file's dropped section with the reason, so the user can push back

#### Scenario: Unresolvable candidate

- **WHEN** a candidate matches none of the ladder's tests
- **THEN** it becomes an open question in the trace file and does not appear in the draft or target document

### Requirement: Business drivers stay lean

The Business Drivers & Goals section SHALL contain at most one row per catalog driver. Each row SHALL state a business consequence carrying a monetary amount or a date, and SHALL NOT state a technical mechanism, threshold, or measurement.

#### Scenario: Driver row count

- **WHEN** the business-drivers catalog contains four drivers
- **THEN** the Business Drivers & Goals table contains at most four rows

#### Scenario: Technical detail proposed as a driver

- **WHEN** a proposed driver row reads "PII shall be removed within 30 days of request"
- **THEN** it is rejected as a driver and re-filed as a quality attribute requirement traced to the relevant driver

### Requirement: Human-in-the-loop gates run on the main thread

The skill SHALL present each gate — classification confirmation, open-question resolution, metric agreement, and prioritization — in the main conversation and SHALL wait for the user's answer before continuing. The skill SHALL NOT delegate a gate to a subagent. The skill SHALL NOT record an unanswered elicitation question as an assumption or carry it into the target document as a placeholder row.

#### Scenario: Missing target value

- **WHEN** the sources state no availability target, RTO, RPO, or latency threshold for an attribute the document covers
- **THEN** the skill asks the user in one consolidated question block, offering a defensible starting value to accept, adjust, or reject, and records the item as an open question in the trace file until answered

#### Scenario: Conflicting values across sources

- **WHEN** two sources state different targets for the same attribute
- **THEN** both values are presented to the user with their provenance and neither is silently chosen

#### Scenario: Unanswered question at write time

- **WHEN** an open question is still unanswered
- **THEN** it remains in the trace file and is not written into the draft's Assumptions section

### Requirement: Requirements are recorded one row per requirement with stable identifiers

The document SHALL record business drivers as `BD-nn` rows and quality attribute requirements as `QAR-nn` rows, one row per requirement, with the catalog attribute as a column and a `Driver` column tracing each requirement to a `BD-nn` row or to `—`. Identifiers SHALL be stable across maintenance runs.

#### Scenario: Multiple requirements for one attribute

- **WHEN** the sources yield a latency target and a throughput target, both under `Performance & Scalability`
- **THEN** each is recorded as its own `QAR-nn` row sharing the same `Quality Attribute` column value

#### Scenario: Identifier sequence on a maintenance run

- **WHEN** a maintenance run adds requirements, no draft file exists, and the highest existing identifier in the target document is `QAR-19`
- **THEN** the skill parses the target document for the highest identifier per prefix, numbers new requirements from `QAR-20`, and reassigns no existing identifier

#### Scenario: Requirement with no business driver

- **WHEN** a requirement is baseline hygiene with no traceable business driver
- **THEN** its `Driver` column is `—`

### Requirement: Metrics are measurable

Each quality attribute requirement SHALL state what is measured, the threshold with its unit, and the conditions. Where a source gives no value, the skill SHALL propose a defensible one and mark it `(proposed)` or `TBD` until the user accepts, adjusts, or rejects it at a gate.

#### Scenario: Vague source statement

- **WHEN** a source reads "the system should be fast"
- **THEN** the recorded requirement states a threshold, unit, and conditions, such as "p95 page load < 2s for the top 10 journeys at 500 concurrent users"

#### Scenario: Proposed value not yet confirmed

- **WHEN** the skill proposes a target the user has not yet accepted
- **THEN** the requirement carries a `(proposed)` marker in the document

### Requirement: Prioritization respects the P0 budget

The skill SHALL apply the scale in `qa-priorities.md` unless the target document already uses a different one, in which case it SHALL match the document. At most seven attributes across the solution SHALL carry `P0`. The skill SHALL start from catalog baseline priorities and adjust using evidence from the sources.

#### Scenario: More than seven P0 candidates

- **WHEN** evidence would justify `P0` for more than seven attributes
- **THEN** the skill presents the tie-break to the user and asks which the business would sacrifice first, rather than expanding the list

#### Scenario: Priority differs from catalog baseline

- **WHEN** a proposed priority differs from the catalog's baseline for that attribute
- **THEN** the difference is called out with the source evidence that justifies it

### Requirement: Confirmed priorities lock

A priority confirmed by the user and written to the target document SHALL be marked `🔒`. On subsequent runs the skill SHALL NOT change a locked priority automatically. Where new evidence contradicts a locked priority, the skill SHALL report the mismatch and leave the value unchanged. A locked priority SHALL change only when the user explicitly unlocks it in the current conversation.

#### Scenario: New evidence contradicts a lock

- **WHEN** a maintenance run finds evidence suggesting a locked `P2` should be `P0`
- **THEN** the skill reports the attribute, its locked value, the evidence-suggested value, and the source quote, and states plainly that no change was made

#### Scenario: New attribute added this run

- **WHEN** a requirement is added for the first time in this run
- **THEN** its priority is marked `*new*` and is not locked until the user confirms it

### Requirement: Maintenance runs merge rather than overwrite

When the target document already exists, the skill SHALL match rows by identifier and update in place, SHALL preserve human edits, comments, and additional sections, and SHALL NOT delete a requirement because the current batch of sources did not mention it.

#### Scenario: Existing document with hand-edited rows

- **WHEN** the target document contains rows edited by a stakeholder
- **THEN** those rows are preserved, unchanged rows are not reordered or re-worded, and any conflict with the skill's reading of the sources is raised in the summary

#### Scenario: Requirement absent from this batch of sources

- **WHEN** an existing requirement is not mentioned in the current sources
- **THEN** it is retained, and removal is proposed in the summary rather than performed

#### Scenario: Existing document uses different headings

- **WHEN** the target document uses heading spellings that differ from the template
- **THEN** the existing headings are kept and the mismatch is reported

### Requirement: The target document is written only by publish, only after validation passes

The detect and refine phases SHALL write only the draft and trace files. The publish phase SHALL render, run the validator, and promote to `nfrPath` only when validation passes, and SHALL append a terminal publish row to the trace's Decision Log once promotion succeeds. The skill SHALL NOT require phases to be run in order; a premature publish SHALL fail validation rather than write an incomplete document.

#### Scenario: Detect run alone

- **WHEN** the detect phase completes
- **THEN** the draft and trace files exist and the target document is unchanged

#### Scenario: Publish before refining

- **WHEN** the publish phase runs against a draft with unmeasured requirements and unset priorities
- **THEN** validation fails, the failures are reported, the target document is unchanged, and no publish row is written to the trace

#### Scenario: Validation passes

- **WHEN** the rendered draft passes validation
- **THEN** the skill shows the diff against the current target document, promotes the draft to `nfrPath`, and appends a terminal publish row to the trace's Decision Log

### Requirement: Provenance is recorded outside the deliverable

The skill SHALL record each requirement's verbatim source evidence and location, open questions, dropped candidates, and a Decision Log of answered gates and completed publishes in the trace file, and SHALL NOT place them in the target document. The Decision Log SHALL accumulate across successive runs against the same living document rather than being reset. The pipeline SHALL remain operable if the trace file is absent, at the cost of phase inference, which SHALL then defer to the user.

#### Scenario: Evidence recorded

- **WHEN** a requirement `QAR-01` is derived from a sentence in `rfp.docx`
- **THEN** the trace file records the verbatim sentence and its location against `QAR-01`, and the target document contains no provenance appendix

#### Scenario: Trace file deleted

- **WHEN** the trace file has been deleted and the publish phase is explicitly requested
- **THEN** publishing proceeds against the draft, and the summary notes that provenance is unavailable

#### Scenario: Publish stamps the Decision Log

- **WHEN** the publish phase promotes a draft successfully
- **THEN** a terminal publish row naming the date and the promoted target is appended to the trace's Decision Log, so a later invocation can tell a completed run from an in-flight one

#### Scenario: Successive runs accumulate

- **WHEN** a second source batch is mined into the same living document after an earlier run published
- **THEN** the trace retains the earlier run's evidence and decision-log rows and appends the new run's, rather than overwriting them

### Requirement: Sparse sources are reported, not padded

Where the sources yield little material, the skill SHALL say so and offer a short elicitation, and SHALL NOT pad the tables with generic attributes to fill the catalog.

#### Scenario: Sources yield almost nothing

- **WHEN** mining produces very few candidates
- **THEN** the skill reports the shortfall and offers targeted elicitation questions instead of generating rows for uncovered catalog attributes
