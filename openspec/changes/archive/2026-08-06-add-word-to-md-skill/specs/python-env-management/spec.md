## ADDED Requirements

### Requirement: uv-managed Python dependencies
The system SHALL manage Python dependencies via a `pyproject.toml` and `uv.lock` at the repo root, superseding `requirements.txt`, and SHALL preserve every dependency currently listed in `requirements.txt`.

#### Scenario: Existing dependencies preserved
- **WHEN** `pyproject.toml` is created
- **THEN** it declares at least `pypandoc>=1.11` and `langchain-text-splitters>=0.3.0`, matching `requirements.txt`'s prior contents, plus any new dependency the `word-to-md` skill requires

### Requirement: Zero-step script execution via uv run
The system SHALL allow any Python script in the repository to be run via `uv run python <script>` (or `uv run pytest <path>`) without a separate manual `pip install` or venv-activation step; `uv` SHALL create or sync the `.venv` from the lockfile automatically on first use.

#### Scenario: Fresh checkout runs a script with no setup step
- **WHEN** a user with `uv` installed but no existing `.venv` runs `uv run python skills/word-to-md/scripts/docx_to_md.py --source <docx>`
- **THEN** `uv` provisions the environment from `uv.lock` and the script runs successfully without any prior `pip install` command

#### Scenario: Existing scripts still run under uv
- **WHEN** `.ai-automation/scripts/split-markdown-by-heading.py` or `copy-dir.py` is invoked via `uv run python <script>`
- **THEN** it runs successfully using the dependencies declared in `pyproject.toml`

### Requirement: requirements.txt removed
The system SHALL remove `requirements.txt` once `pyproject.toml`/`uv.lock` supersede it, and any documentation referencing `pip install -r requirements.txt` SHALL be updated to the `uv run` equivalent.

#### Scenario: No stale install instructions remain
- **WHEN** the migration is complete
- **THEN** `requirements.txt` no longer exists and no remaining doc/skill instructs a reader to `pip install -r requirements.txt`
