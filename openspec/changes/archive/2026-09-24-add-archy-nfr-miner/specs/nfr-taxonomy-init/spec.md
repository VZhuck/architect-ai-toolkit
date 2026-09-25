# Spec Delta

## ADDED Requirements

### Requirement: Taxonomy ships NFR workflow templates
Besides the closed vocabularies, the skill's `taxonomy/` folder SHALL include the NFR workflow templates `nfr-state.yaml` (run state) and `nfr-registry-log.md` (NFR registry with Open Questions, Conflicts, and Dropped sections). These are copied and versioned like any other taxonomy file. Any change to a template SHALL bump the taxonomy version, so that projects that are already initialized receive it.

#### Scenario: Templates materialized
- **WHEN** the skill runs in a project with no taxonomy folder
- **THEN** `nfr-state.yaml` and `nfr-registry-log.md` exist in the target alongside the vocabulary files

#### Scenario: Template change reaches initialized projects
- **WHEN** a project holds taxonomy version `1.0.0` and the skill declares `1.1.0` with an updated `nfr-registry-log.md`
- **THEN** the run reports `updated`, and the target's `nfr-registry-log.md` matches the skill's copy
