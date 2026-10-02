# Spec Delta

## MODIFIED Requirements

### Requirement: Taxonomy ships NFR workflow templates
Besides the closed vocabularies, the skill's `taxonomy/` folder SHALL include these NFR workflow templates:
- `nfr-state.yaml`: state for a miner run or a propose draft
- `nfr-registry-log.md`: the NFR registry, with Open Questions, Conflicts, and Dropped sections
- `nfr-req-tmpl.md`: the NFR document template
- `nfr-draft-log.md`: the propose change log, with Change Set, Trace, Open Questions, Conflicts, and Dropped sections

These are copied and versioned like any other taxonomy file. Any change to a template SHALL bump the taxonomy version, so that projects that are already initialized receive it.

`nfr-state.yaml` SHALL describe the following:
- `files_4_review` holds source documents for a miner run, or input run registries for a propose draft.
- The file statuses include `merged`.
- The stages include `hand-off`.
- An optional `target_sad_docs` list gives, for each entry, `path`, `sha256`, `exists`, `draft`, and `format_source`.

`nfr-req-tmpl.md` SHALL have one H1 and exactly these four H2 sections, in this order: `Business Drivers & Goals`, `Quality Attributes`, `Assumptions`, and `Constraints`. Each section SHALL hold free intro text followed by one valid markdown table (a header row, a separator row, and data rows) whose first column is `ID`. The table columns SHALL be:

| Section | Columns |
| --- | --- |
| Business Drivers & Goals | `ID`, `Business Driver`, `Business Goal`, `Metric / Criteria`, `Priority` |
| Quality Attributes | `ID`, `Quality Attribute`, `Requirement`, `Metric / Criteria`, `Priority` |
| Assumptions | `ID`, `Assumption`, `Risk`, `Impact` |
| Constraints | `ID`, `Constraint`, `Impact` |

Sample IDs SHALL use the form `<TYPE>-###` (`BD-001`, `QAR-001`, `ASM-001`, `CSTR-001`). Sample category values SHALL be verbatim catalog names.

#### Scenario: Templates materialized
- **WHEN** the skill runs in a project with no taxonomy folder
- **THEN** `nfr-state.yaml`, `nfr-registry-log.md`, `nfr-req-tmpl.md`, and `nfr-draft-log.md` exist in the target alongside the vocabulary files

#### Scenario: Template change reaches initialized projects
- **WHEN** a project holds taxonomy version `1.1.1` and the skill declares `1.2.0` with a new `nfr-req-tmpl.md`
- **THEN** the run reports `updated`, and the target's `nfr-req-tmpl.md` matches the skill's copy

#### Scenario: Document template is parseable
- **WHEN** `nfr-req-tmpl.md` is parsed as markdown
- **THEN** each of its four H2 sections contains exactly one table with a separator row, an `ID` first column, and the columns listed for that section

#### Scenario: Template uses catalog names
- **WHEN** the `Quality Attributes` sample row of `nfr-req-tmpl.md` is read
- **THEN** its `Quality Attribute` value exists verbatim in `quality-attributes.md`
