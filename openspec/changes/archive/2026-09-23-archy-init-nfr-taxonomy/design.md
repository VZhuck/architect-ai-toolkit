# Design

## Context

The toolkit's skills are installed into consumer projects by `ossify-cogents`, typically under `.claude/skills/<name>/`. Existing SKILL.md files invoke scripts with repo-relative paths (`uv run python skills/archy-.../scripts/...`). That only works inside this repository. `ai-workflow/` is the operational scratch area; it is gitignored in this repo, and consumer projects may or may not version it. The NFR draft output already treats the business-driver and quality-attribute catalogs as closed vocabularies. See proposal.md for motivation and specs/nfr-taxonomy-init/spec.md for the behavior contract.

## Goals / Non-Goals

**Goals:**
- A deterministic, stdlib-only script that owns all file mechanics. The SKILL.md only runs the script and relays its result.
- Works both from this repo and from an installed skill location.
- Tests stay valid as taxonomy files are added, renamed, or removed.

**Non-Goals:**
- Defining the actual taxonomy content. The first files are placeholders.
- Migrating or merging local edits across versions. A version change overwrites them.
- Updating NFR consumer skills to read the new folder. That is follow-up work.
- A `/archy:*` slash command.

## Decisions

**Copy files and return a JSON result, rather than only replying with the taxonomy content.**
Consumer skills read `ai-workflow/nfr-taxonomy/` by path, which is cheap and deterministic, and humans can review or tailor the files. The JSON result gives callers a structured answer as well.
*Alternative:* a reply-only skill that returns the taxonomy content. This was rejected because every consumer would need a model-mediated skill call, the taxonomy couldn't be tailored per project, and the result would be invisible to humans.

**Declare the version in `SKILL.md` frontmatter (`metadata.version`), with a `<target>/.taxonomy-version` marker.**
This gives one place to bump the version, next to the skill identity. The script reads it with a small regex over the frontmatter block, which avoids adding a PyYAML dependency.
*Alternative:* a `taxonomy/manifest.json`. This was rejected in favor of a single source; the version could move there later without changing behavior.

**Version-driven re-run policy:**
- Same version, no force: `up-to-date`, and nothing is written.
- Marker missing: `initialized`.
- Different version, or force: `updated`.
- In the initialized and updated cases, every taxonomy file is written, and each file is reported as `copied` if it didn't exist before or `overwritten` if it did.
The version, not the file content, is the signal. Local tailoring survives until the toolkit ships a new version.
*Alternative:* skip existing files, or compare hashes. This was rejected because it would silently keep stale catalogs after an upgrade.

**Resolve paths from the script, not the current directory.** The source is `Path(__file__).resolve().parents[1] / "taxonomy"` and the version comes from `parents[1] / "SKILL.md"`. The target defaults to `ai-workflow/nfr-taxonomy` resolved against the current directory (the project root), and `--target` overrides it. The `_resolve_relative` pattern from `skills/archy-summarize-meeting-decisions/scripts/resolve_paths.py` is reused. SKILL.md tells the agent to run the script from its own skill directory path, which keeps it correct wherever the skill is installed.

**The core function is separate from the CLI.** `init_taxonomy(target, force, source=None, skill_md=None) -> dict` is pure and testable, with injectable source and SKILL.md paths so tests can simulate version bumps without touching the real skill. `main()` handles argparse, JSON printing, and exit codes.

**Validate before writing.** A missing or empty source or a missing version raises an error before any directory is created.

**Tests enumerate the real `taxonomy/` dynamically.** One test copies from the real skill and asserts that every non-hidden file matches byte for byte. Version and force scenarios use a `tmp_path` fixture skill (a copied taxonomy plus a synthetic SKILL.md), so tests control the version.

## Risks / Trade-offs

- [Someone forgets to bump the version after editing the taxonomy, so projects keep the stale copy] → SKILL.md and the README state the rule, and `--force` is the escape hatch.
- [A version bump silently discards local tailoring] → the JSON result lists `overwritten` files and `previous_version`, and SKILL.md tells the agent to surface them to the user. Projects that version `ai-workflow/` can recover changes from git.
- [A file removed from the toolkit taxonomy stays orphaned in the target] → accepted for now. Deleting only unrelated or unknown files is risky. This can be revisited with a manifest-tracked file list.
- [Frontmatter regex is brittle] → it only reads `version:` nested under `metadata:` inside the leading `---` block, and a test covers the missing-version error.
