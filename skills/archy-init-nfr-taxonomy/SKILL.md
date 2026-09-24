---
name: archy-init-nfr-taxonomy
description: "Initialize or refresh the project's NFR taxonomy: copy every catalog file shipped in this skill's taxonomy/ folder into ai-workflow/nfr-taxonomy/ (version-aware: skips when the installed version matches, overwrites on a version change) and return a JSON result of what was copied, skipped, or overwritten."
argument-hint: "target (optional destination folder, default 'ai-workflow/nfr-taxonomy'), force (optional, recopy even when versions match)"
metadata:
  version: 1.0.0
---

# Initialize NFR Taxonomy

Materialize the toolkit's canonical NFR taxonomy (closed vocabularies such as business drivers and quality attributes) into the project's operational folder, so that NFR skills and humans read the same catalogs by path. All file mechanics are in a stdlib-only Python script. This skill only runs it and relays the result.

## Parameters

- **target** (optional): Destination folder. Default: `ai-workflow/nfr-taxonomy`, resolved against the current working directory (the project root).
- **force** (optional): Recopy every taxonomy file even when the installed version already matches.

## Workflow

### 1. Run the script

The script lives in this skill's own directory (the folder containing this `SKILL.md`), at `scripts/init_taxonomy.py`. Run it from the project root, using the skill directory's actual path. In this repository, that is `skills/archy-init-nfr-taxonomy`. When the skill is installed, it is usually `.claude/skills/archy-init-nfr-taxonomy`.

```bash
uv run python <skill-dir>/scripts/init_taxonomy.py
```

Add `--target "{target}"` only when a target was given, and add `--force` only when force was requested. Do not pass an empty `--target`.

### 2. Relay the result

The script prints one JSON object:

```json
{"version": "1.0.0", "previous_version": null, "status": "initialized",
 "source": "...", "target": "...", "copied": [...], "skipped": [...], "overwritten": [...]}
```

Report to the user:

- `status` meanings:
  - `initialized`: first install; no version marker existed.
  - `updated`: the version changed, or force was requested.
  - `up-to-date`: the installed version matches, so nothing was written.
- The target folder and the version (plus `previous_version` when it's set).
- The files copied, skipped, and overwritten.
- If any files were overwritten, point them out explicitly: local edits to those files were replaced with the toolkit version.
- If the status is `up-to-date` and the user expected changes, mention that `force` recopies the files.

## Versioning rule

The taxonomy version is `metadata.version` in this file's frontmatter. The script writes it to `<target>/.taxonomy-version`. **Bump the version whenever any file in `taxonomy/` changes.** Otherwise, projects that already have the taxonomy will keep skipping the update.

- Same version: nothing is written, and local tailoring is kept.
- Different version, or no marker: every taxonomy file is overwritten. Files in the target that aren't part of the taxonomy are never touched.

## Error handling

If the script exits non-zero (missing `taxonomy/` folder, no taxonomy files, or no `metadata.version`), surface its error message. Don't report success. Nothing is written in that case.
