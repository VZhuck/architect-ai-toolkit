# nfr-document-validation

## Purpose

Audit a Non-Functional Requirements document deterministically against the quality-attribute catalogs, the document template, and `rules/sad-sections.instructions.md`, so that any NFR document — whether produced by this pipeline or not — can be checked standalone, and so that publishing to the target document is gated on those checks passing.

## Requirements

### Requirement: Validation is deterministic and independently runnable

The toolkit SHALL provide `validate_nfr.py`, a script that audits an NFR document against the catalogs and returns a non-zero exit code when any check fails. The script SHALL be runnable on any NFR document without source material, a draft, or a trace file. `/aait:nfr-validate` SHALL accept an optional document path and SHALL fall back to the resolved `nfrPath` when none is given. The script SHALL NOT modify the document it validates.

#### Scenario: Standalone audit

- **WHEN** a user runs `/aait:nfr-validate` against an existing NFR document with no prior detect or refine run in the session
- **THEN** the script reports every failing check with the offending row, and the document is unchanged

#### Scenario: Auditing a document from outside this pipeline

- **WHEN** `/aait:nfr-validate` is given a path to an NFR document this pipeline did not produce, with no draft or trace file present
- **THEN** the script validates that document and reports its findings

#### Scenario: Validate with no path argument

- **WHEN** `/aait:nfr-validate` is invoked with no document path
- **THEN** the resolved `nfrPath` is validated

#### Scenario: Clean document

- **WHEN** every check passes
- **THEN** the script exits zero and reports that the document is valid

#### Scenario: Failure reporting

- **WHEN** one or more checks fail
- **THEN** the script exits non-zero and each failure names the check, the section, and the row that failed

### Requirement: Catalog fidelity is verified by exact match

The validator SHALL confirm that every attribute name appearing in the Business Drivers & Goals and Quality Attribute Requirements tables is an exact string match for a row in `business-drivers.md` or `quality-attributes.md` respectively. The Business Drivers & Goals table SHALL contain no more rows than the business catalog has drivers.

#### Scenario: Paraphrased attribute name

- **WHEN** a requirement row names `Security` where the catalog defines `Security & Privacy`
- **THEN** validation fails, naming the row and the expected catalog spelling

#### Scenario: Business table exceeds the catalog

- **WHEN** the business catalog defines four drivers and the document's Business Drivers & Goals table contains five rows
- **THEN** validation fails

### Requirement: Business and technical content stay separated

The validator SHALL confirm that Business Drivers & Goals cells contain no technical mechanism or measurement vocabulary, and that each such cell carries a monetary amount or a date. Regulation and standard names SHALL NOT by themselves cause a failure.

#### Scenario: Technical metric in a driver cell

- **WHEN** a driver cell contains a latency, uptime, RTO, RPO, TPS, encryption, or PII-handling statement
- **THEN** validation fails and the row is reported as belonging in Quality Attribute Requirements

#### Scenario: Driver with neither money nor a date

- **WHEN** a driver cell states a business goal with no monetary amount and no date
- **THEN** validation fails

#### Scenario: Driver naming a regulation

- **WHEN** a driver cell reads "ContosoX incurs €2m penalty if PCI-DSS 4.0 certification is not achieved by 30/06/2027"
- **THEN** validation passes, because the regulation name is not mechanism vocabulary and the cell carries both an amount and a date

### Requirement: Requirements are verifiably measurable

The validator SHALL confirm that every quality attribute requirement states a threshold with a unit, or is explicitly marked `(proposed)` or `TBD`.

#### Scenario: Requirement with no threshold

- **WHEN** a requirement reads "the system should be fast" with no `(proposed)` or `TBD` marker
- **THEN** validation fails

#### Scenario: Explicitly pending requirement

- **WHEN** a requirement carries a `(proposed)` or `TBD` marker
- **THEN** validation passes for the measurability check and the requirement is listed in the report as pending stakeholder confirmation

### Requirement: The P0 budget is enforced

The validator SHALL confirm that no more than seven rows across the document carry `P0`.

#### Scenario: Budget exceeded

- **WHEN** nine rows carry `P0`
- **THEN** validation fails, reporting the count and listing the rows

### Requirement: Priority locks are verified against version control

The validator SHALL confirm that every priority marked `🔒` is unchanged from the git `HEAD` version of the document. Where no `HEAD` version exists, the check SHALL degrade to a warning rather than block promotion.

#### Scenario: Locked priority altered

- **WHEN** a row marked `P0 🔒` in `HEAD` reads `P1 🔒` in the candidate document
- **THEN** validation fails, naming the row and both values

#### Scenario: Document not yet committed

- **WHEN** the target document has no version in git `HEAD`, or the repository is not a git repository
- **THEN** the lock check emits a warning and does not fail validation

### Requirement: Document structure conforms to the template and SAD rules

The validator SHALL confirm that the document contains the four expected sections, that Assumptions follow the two-line `- Assumption (Impact)` shape, and that the file complies with `rules/sad-sections.instructions.md` — exactly one H1 at file start, an empty line before headings, and markdown tables.

#### Scenario: Missing section

- **WHEN** the document has no Constraints section
- **THEN** validation reports the missing section

#### Scenario: Malformed assumption

- **WHEN** an assumption states no impact, or does not follow the two-line shape
- **THEN** validation fails, naming the assumption

#### Scenario: SAD rule violation

- **WHEN** the document contains a second H1, or a heading with no preceding empty line
- **THEN** validation fails, citing the rule

#### Scenario: Legacy headings

- **WHEN** the document uses the retired headings `Business Quality Attribures`, `Quality Attributes`, or `Constrains`
- **THEN** validation reports the mismatch with the corrected heading names and does not rewrite the document

### Requirement: Publishing is gated on validation

`/aait:nfr-publish` SHALL run the validator against the rendered draft before writing to `nfrPath`, and SHALL promote the draft only when the validator exits zero.

#### Scenario: Validation fails during publish

- **WHEN** the validator exits non-zero on the rendered draft
- **THEN** the failures are reported, the target document is left untouched, and nothing is promoted

#### Scenario: Validation passes during publish

- **WHEN** the validator exits zero
- **THEN** the diff against the current target document is shown and the draft is promoted

### Requirement: Script checks are followed by a judgement checklist

After the script passes, the skill SHALL apply a short checklist for properties a script cannot judge — whether each metric is genuinely measurable and whether each driver is genuinely a business outcome — and SHALL report any concern before promotion.

#### Scenario: Script passes but a metric is not genuinely testable

- **WHEN** a requirement carries a numeric threshold that could not in practice be measured
- **THEN** the concern is raised to the user before promotion, even though the script check passed
