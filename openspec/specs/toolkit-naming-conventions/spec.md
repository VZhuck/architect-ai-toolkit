# toolkit-naming-conventions Specification

## Purpose

Namespace every skill and slash command shipped by this toolkit under `archy`, so installed items are clearly attributable to the toolkit and do not collide with skills or commands from other sources in a consumer repository.

## Requirements

### Requirement: Skill folders use the archy- prefix
Every skill directory directly under the top-level `skills/` folder SHALL be named `archy-<name>`, where `<name>` is lowercase kebab-case.

#### Scenario: Conforming skill folder
- **WHEN** a skill lives at `skills/archy-md-to-word/`
- **THEN** it satisfies the naming convention

#### Scenario: Unprefixed skill folder is rejected
- **WHEN** a new skill is added at `skills/md-to-pdf/`
- **THEN** the naming convention check fails and names `skills/md-to-pdf` as non-conforming

### Requirement: SKILL.md name matches its folder
Every `skills/archy-<name>/SKILL.md` SHALL declare a frontmatter `name:` exactly equal to its folder name, `archy-<name>`.

#### Scenario: Matching name
- **WHEN** `skills/archy-word-to-md/SKILL.md` declares `name: archy-word-to-md`
- **THEN** it satisfies the naming convention

#### Scenario: Stale or mismatched name is rejected
- **WHEN** `skills/archy-word-to-md/SKILL.md` declares `name: word-to-md`
- **THEN** the naming convention check fails and reports the expected name `archy-word-to-md`

### Requirement: Commands live in the archy namespace
Every slash command file SHALL live at `commands/archy/<name>.md`, so it is invoked as `/archy:<name>`. No command file SHALL exist directly under `commands/` or in any other subfolder.

#### Scenario: Namespaced command invocation
- **WHEN** the toolkit is installed and the user types `/archy:md-to-word sad`
- **THEN** the `commands/archy/md-to-word.md` command runs with `sad` as its argument

#### Scenario: Top-level command file is rejected
- **WHEN** a command file is added at `commands/md-to-pdf.md`
- **THEN** the naming convention check fails and names that file as non-conforming

### Requirement: Commands reference skills by their full archy- name
A command that delegates to a skill SHALL name that skill by its full `archy-<name>` identifier, and that identifier SHALL correspond to an existing `skills/archy-<name>/` folder.

#### Scenario: Command resolves to an existing skill
- **WHEN** `/archy:load-raw-req CAP-123` is invoked
- **THEN** the command invokes the `archy-load-raw-req` skill, which exists at `skills/archy-load-raw-req/`

#### Scenario: Dangling skill reference is rejected
- **WHEN** a command file tells the agent to invoke a skill by an old or unprefixed name such as `md-to-word`
- **THEN** the naming convention check fails and reports the unresolved skill reference

### Requirement: No stale unprefixed references
Repository content outside `openspec/` (including skills, commands, rules, `README.md`, `AGENTS.md`, and `.env.example`) SHALL NOT reference a toolkit skill by an unprefixed path of the form `skills/<name>/` when the skill exists as `skills/archy-<name>/`. It SHALL NOT reference a toolkit command by an un-namespaced invocation `/<name>` when the command exists as `commands/archy/<name>.md`. Content under `openspec/` is exempt, because specs and change artifacts cite historical and example names.

#### Scenario: Old skill path in documentation is rejected
- **WHEN** `README.md` contains `uv run python skills/word-to-md/scripts/docx_to_md.py`
- **THEN** the naming convention check fails and reports the file and the stale path

#### Scenario: Un-namespaced command invocation is rejected
- **WHEN** `.env.example` contains a comment referring to `/md-to-word`
- **THEN** the naming convention check fails and reports the file and suggests `/archy:md-to-word`

#### Scenario: Output folder paths are not mistaken for commands
- **WHEN** a skill documents its default output path `ai-workflow/md-to-word/<name>.docx`
- **THEN** the naming convention check does not report it

#### Scenario: OpenSpec content is ignored
- **WHEN** a file under `openspec/` references `skills/word-to-md/` or `/load-raw-req`
- **THEN** the naming convention check does not report it

### Requirement: Convention is checked automatically
The repository SHALL provide an automated check, runnable with `uv run pytest`, that verifies every requirement in this capability and fails with a message naming each violating file.

#### Scenario: Clean repository passes
- **WHEN** `uv run pytest` is run on a repository where all skills and commands conform
- **THEN** the naming convention tests pass

#### Scenario: Violation is reported precisely
- **WHEN** any single skill folder, SKILL.md name, command location, or command skill reference violates the convention
- **THEN** the test run fails and its output identifies the offending path
