## ADDED Requirements

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

## MODIFIED Requirements

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
