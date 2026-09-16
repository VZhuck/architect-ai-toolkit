## MODIFIED Requirements

### Requirement: Validation is deterministic and independently runnable

The toolkit SHALL provide `validate_nfr.py`, a script that audits an NFR document against the catalogs and returns a non-zero exit code when any check fails. The script SHALL be runnable on any NFR document without source material, a draft, or a trace file. The `aait-nfr` skill's validate phase SHALL accept an optional document path and SHALL fall back to the resolved `nfrPath` when none is given. The validate phase SHALL be invocable at any time and SHALL NOT depend on phase inference or on an in-flight run. The script SHALL NOT modify the document it validates.

#### Scenario: Standalone audit

- **WHEN** a user invokes the validate phase against an existing NFR document with no prior detect or refine run in the session
- **THEN** the script reports every failing check with the offending row, and the document is unchanged

#### Scenario: Auditing a document from outside this pipeline

- **WHEN** the validate phase is given a path to an NFR document this pipeline did not produce, with no draft or trace file present
- **THEN** the script validates that document and reports its findings

#### Scenario: Validate with no path argument

- **WHEN** the validate phase is invoked with no document path
- **THEN** the resolved `nfrPath` is validated

#### Scenario: Validate is not reached by inference

- **WHEN** the skill is invoked with no phase argument
- **THEN** phase inference SHALL NOT select validate, which is reachable only by explicit request

#### Scenario: Clean document

- **WHEN** every check passes
- **THEN** the script exits zero and reports that the document is valid

#### Scenario: Failure reporting

- **WHEN** one or more checks fail
- **THEN** the script exits non-zero and each failure names the check, the section, and the row that failed

### Requirement: Publishing is gated on validation

The `aait-nfr` skill's publish phase SHALL run the validator against the rendered draft before writing to `nfrPath`, and SHALL promote the draft only when the validator exits zero.

#### Scenario: Validation fails during publish

- **WHEN** the validator exits non-zero on the rendered draft
- **THEN** the failures are reported, the target document is left untouched, and nothing is promoted

#### Scenario: Validation passes during publish

- **WHEN** the validator exits zero
- **THEN** the diff against the current target document is shown and the draft is promoted
