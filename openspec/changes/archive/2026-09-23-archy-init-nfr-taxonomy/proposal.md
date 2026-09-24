# Proposal

## Why

NFR skills depend on closed vocabularies (business drivers, quality attributes, and similar catalogs) that every skill must use verbatim. Today, no single mechanism places these catalogs where consuming skills and humans can read them. As a result, each skill would have to embed its own copy or call another skill at runtime, and neither approach is deterministic. We need one versioned source in the toolkit and a predictable operational copy in each consumer project.

## What Changes

- New skill `archy-init-nfr-taxonomy` that ships a `taxonomy/` folder, which is the toolkit's canonical NFR catalogs. The exact files are defined later.
- The skill materializes every taxonomy file into the project's operational folder `ai-workflow/nfr-taxonomy/`. The destination can be changed with a target override.
- The taxonomy version is declared in the skill's `SKILL.md` frontmatter (`metadata.version`). A version marker in the target records which version was installed.
- Re-run behavior:
  - If the installed version equals the skill version, nothing is written.
  - If the version differs or no marker exists, every taxonomy file is overwritten and the marker is updated.
  - A force option recopies even when the versions match.
- Every run returns a structured JSON result (version, previous version, status, copied/skipped/overwritten files). Callers can consume it directly.
- No slash command is added. The skill is invoked directly as `/archy-init-nfr-taxonomy`.

## Capabilities

### New Capabilities
- `nfr-taxonomy-init`: Materializes the toolkit's versioned NFR taxonomy files into a project's operational taxonomy folder and reports the outcome as structured output.

### Modified Capabilities
None. The new skill follows the existing `toolkit-naming-conventions` requirements without changing them.

## Impact

- New: `skills/archy-init-nfr-taxonomy/` (`SKILL.md`, `scripts/`, `taxonomy/`, `tests/`).
- Consumer projects: gain `ai-workflow/nfr-taxonomy/` (with a `.taxonomy-version` marker), which becomes the path contract for NFR skills such as `archy-nfr`.
- No new dependencies. The script uses only the Python standard library and runs via `uv run`.
- `skills/archy-nfr/README.md` references the new taxonomy location.
