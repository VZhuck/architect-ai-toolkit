# Spec Delta

## Purpose

Provide a single, versioned source of the toolkit's NFR taxonomy catalogs and materialize them into a project's operational `ai-workflow/nfr-taxonomy/` folder. NFR skills and humans can then read the same closed vocabularies by path.

## ADDED Requirements

### Requirement: Skill ships a versioned taxonomy
The `archy-init-nfr-taxonomy` skill SHALL contain a `taxonomy/` folder holding the canonical NFR taxonomy files, and its `SKILL.md` frontmatter SHALL declare the taxonomy version as `metadata.version`.

#### Scenario: Version is declared
- **WHEN** `skills/archy-init-nfr-taxonomy/SKILL.md` is read
- **THEN** its frontmatter contains a non-empty `metadata.version` value

#### Scenario: Taxonomy folder is not empty
- **WHEN** the skill's `taxonomy/` folder is listed, ignoring dotfiles
- **THEN** it contains at least one file

### Requirement: All taxonomy files are copied to the operational folder
On first run, the skill SHALL copy every non-hidden file under its `taxonomy/` folder into the target folder, preserving relative subpaths and byte content. The default target SHALL be `ai-workflow/nfr-taxonomy/`, resolved against the current working directory. The skill SHALL create any missing target directories. Hidden files (names starting with `.`) and cache folders SHALL NOT be copied.

#### Scenario: First run into an empty project
- **WHEN** the skill runs in a project with no `ai-workflow/nfr-taxonomy/` folder
- **THEN** every non-hidden file from the skill's `taxonomy/` folder exists under `ai-workflow/nfr-taxonomy/` at the same relative path with identical content
- **AND** the result status is `initialized`, and every file is listed as copied

#### Scenario: Custom target
- **WHEN** the skill runs with a target override pointing to another folder
- **THEN** the files are copied to that folder instead of `ai-workflow/nfr-taxonomy/`

#### Scenario: Hidden files are ignored
- **WHEN** the skill's `taxonomy/` folder contains `.gitkeep`
- **THEN** `.gitkeep` is not copied and is not listed in the result

### Requirement: Installed version is recorded
After writing files, the skill SHALL write the skill's taxonomy version to a `.taxonomy-version` marker file in the target folder.

#### Scenario: Marker written
- **WHEN** a run copies or overwrites files
- **THEN** `<target>/.taxonomy-version` contains the version declared in the skill's `SKILL.md`

### Requirement: Same version is skipped
When the target's `.taxonomy-version` equals the skill's version and force is not requested, the skill SHALL NOT write any file.

#### Scenario: Re-run with the same version
- **WHEN** the skill runs a second time with an unchanged version and a locally edited taxonomy file in the target
- **THEN** the edited file is left untouched
- **AND** the result status is `up-to-date`, and every taxonomy file is listed as skipped

### Requirement: Different or missing version triggers overwrite
When the target has no `.taxonomy-version` marker or the marker holds a different version, the skill SHALL overwrite every taxonomy file in the target and update the marker. Files present in the target that are not part of the skill's taxonomy SHALL be left untouched.

#### Scenario: Upgrade to a new version
- **WHEN** the target marker holds `1.0.0`, the skill declares `1.1.0`, and a taxonomy file was edited locally
- **THEN** the edited file is replaced with the skill's content, and the marker holds `1.1.0`
- **AND** the result status is `updated`, and it reports previous version `1.0.0`

#### Scenario: Existing files without a marker
- **WHEN** the target folder already contains taxonomy files but no `.taxonomy-version`
- **THEN** all taxonomy files are overwritten, and the marker is written

#### Scenario: Unrelated files are preserved
- **WHEN** the target contains `project-notes.md`, which is not in the skill's taxonomy
- **THEN** `project-notes.md` is unchanged after any run

### Requirement: Force recopies regardless of version
When force is requested, the skill SHALL overwrite every taxonomy file and rewrite the marker, even if the versions match.

#### Scenario: Force with the same version
- **WHEN** the versions match, a taxonomy file was edited locally, and the skill runs with force
- **THEN** the file is restored to the skill's content, and it is listed as overwritten

### Requirement: Structured result
Every successful run SHALL print a single JSON object to stdout with the fields `version`, `previous_version` (null when no marker existed), `status` (`initialized`, `updated`, or `up-to-date`), `source`, `target`, `copied`, `skipped`, and `overwritten`. The file lists SHALL contain paths relative to the target.

#### Scenario: Result is machine-readable
- **WHEN** the skill's script completes successfully
- **THEN** its stdout parses as JSON containing all the listed fields

### Requirement: Clear failure when the taxonomy is unavailable
The skill SHALL exit with a non-zero status and a clear error message, and write nothing, when its `taxonomy/` folder is missing or empty or its version cannot be read.

#### Scenario: Missing version
- **WHEN** `SKILL.md` has no `metadata.version`
- **THEN** the script exits non-zero with an error naming the missing version, and the target is not modified
