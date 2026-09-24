# Tasks

## 1. Skill scaffold

- [x] 1.1 Create `skills/archy-init-nfr-taxonomy/SKILL.md` with frontmatter `name: archy-init-nfr-taxonomy`, `description`, `argument-hint` (target, force optional), and `metadata:` / `version: 1.0.0`; verify with `uv run pytest tests/test_naming_conventions.py`
- [x] 1.2 Add placeholder catalogs `skills/archy-init-nfr-taxonomy/taxonomy/business-drivers.md` and `taxonomy/quality-attributes.md` (title and a "content defined later" note); verify the folder lists at least one non-hidden file

## 2. Copy script

- [x] 2.1 Implement `skills/archy-init-nfr-taxonomy/scripts/init_taxonomy.py` with `read_skill_version(skill_md)` (regex over the frontmatter, error if missing) and `init_taxonomy(target, force, source=None, skill_md=None) -> dict`. Validate before writing, apply the version policy (up-to-date / initialized / updated), preserve subpaths, skip dotfiles and `__pycache__`, and write `.taxonomy-version`. Verify with the tests in 3.x
- [x] 2.2 Add `main()` with argparse `--target` (default `ai-workflow/nfr-taxonomy`, resolved against the current directory via the `_resolve_relative` pattern) and `--force`. Print the JSON result, exit non-zero with a message on error. Verify with manual runs into a scratch folder: first run `initialized`, second run `up-to-date`, `--force` run `updated`

## 3. Tests

- [x] 3.1 Create `skills/archy-init-nfr-taxonomy/tests/test_init_taxonomy.py` (sys.path insert, like `archy-md-to-word` tests). Add a test that copies from the real skill taxonomy, enumerates the source dynamically, and asserts it is non-empty, that all files are byte-identical at the same relative paths, and that the marker equals the SKILL.md version
- [x] 3.2 Add fixture-skill tests covering: same-version re-run preserves the edited file (`up-to-date`, all skipped); older marker overwrites the edited file and updates the marker (`updated`, `previous_version` set); missing marker with existing files overwrites them; `force` with the same version restores the file; unrelated target file is untouched; dotfiles are not copied; nested target directories are created
- [x] 3.3 Add error tests: missing version, empty or missing source → error raised and target not created. Add a `main()` test that asserts stdout parses as JSON with all required fields. Verify all tests pass with `uv run pytest skills/archy-init-nfr-taxonomy/tests/`

## 4. Docs and validation

- [x] 4.1 Complete the SKILL.md workflow: run the script from the skill's own directory, relay the result, highlight `overwritten` files and `previous_version`, and document the "bump `metadata.version` when the taxonomy changes" rule; review that the SKILL.md steps match the script flags
- [x] 4.2 Update `skills/archy-nfr/README.md` to reference `ai-workflow/nfr-taxonomy/` as the taxonomy location, produced by the `archy-init-nfr-taxonomy` skill; verify with `uv run pytest tests/`
- [x] 4.3 Run `uv run pytest tests/ skills/archy-init-nfr-taxonomy/tests/` and `openspec validate archy-init-nfr-taxonomy --strict`; both pass
