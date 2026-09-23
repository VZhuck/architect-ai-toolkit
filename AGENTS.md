# Overview
This repository serves as solution architecture repository, which keeps artifacts required for implementing specific project. 

# Environment Variables

Required environment variables include:
- PROJECT_IDS=007,101
- JIRA 
- ADO_ORGANIZATION_URL
- ADO_CAPABILITY_ID
- ADO_FEATURE_IDS
- ADO_PAT

## Repository Structure
The repository is structured as follows:

architect-ai-toolkit/
|- skills/                          # Canonical skill definitions, one folder per skill
|  |- archy-<name>/                 # SKILL.md (name: archy-<name>), scripts/, tests/, templates/
|- commands/
|  |- archy/                        # Slash commands, invoked as /archy:<name>
|- rules/                           # Scoped instruction files (e.g. sad-sections.instructions.md)
|- scripts/                         # install.sh / install.ps1 (ossify-cogents installer)
|- tests/                           # Repo-level tests (e.g. naming convention checks)
|- openspec/                        # OpenSpec specs and changes
|- test-data/                       # Sample docx/markdown inputs for skill tests
|- ossify-cogents.json              # ossify-cogents source registry for installing this toolkit
|- pyproject.toml / uv.lock         # Python dependencies, run scripts with `uv run`
|- .env.example                     # Example environment variables for local setup
|- README.md                        # Repository overview and usage
|- LICENSE                          # License file

`.claude/skills/` and `.claude/commands/` hold local, gitignored test installs (except the OpenSpec tooling). Always edit the canonical files under `skills/` and `commands/`.

## Naming Convention
All skills and commands shipped by this toolkit are namespaced under `archy`:
- A new skill goes in `skills/archy-<name>/`, and its `SKILL.md` frontmatter `name:` must equal the folder name (`archy-<name>`).
- A new command goes in `commands/archy/<name>.md` and is invoked as `/archy:<name>`. When it delegates to a skill, it names that skill by its full `archy-<name>` id.
- Never reference toolkit skills by unprefixed paths (`skills/<name>/`) or commands by un-namespaced invocations (`/<name>`).

`tests/test_naming_conventions.py` enforces this. Run `uv run pytest tests/` after adding or renaming a skill or command.
