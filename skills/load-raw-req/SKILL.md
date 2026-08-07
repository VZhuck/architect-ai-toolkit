---
name: load-raw-req
description: "Load Jira Capability/Epic/Story (or other) work items via the twg CLI and generate markdown files in ai-workflow/raw-requirements/, with optional one-level children expansion. Isolates raw Jira payloads inside a dispatched subagent."
argument-hint: "[KEY...] (Jira keys, space- and/or comma-separated; falls back to .env JIRA_KEYS when none are given), [--children] (pull one level of children for every key that supports it, e.g. Epic/Capability)"
---

# Load Raw Requirements (Jira)

Fetch Jira work items via the `twg` CLI and render them into `ai-workflow/raw-requirements/` markdown files. This skill is Jira-native and does not read or write anything under `.ai-automation/` (the legacy ADO flow).

## Parameters
- **KEYS**: one or more Jira issue keys to fetch (e.g. `CAP-123`, `EPIC-45`, `ABC-789`), in any order — there is no primary/extra distinction. Issue type is read off each fetched item — do not ask the caller to declare it. Accepts space-separated, comma-separated, or mixed (`ABC-45 ABC-99`, `ABC-45, ABC-99`, `ABC-45,ABC-99` are all equivalent — split on any run of whitespace/commas). Optional if `.env` provides a fallback (see step 2).
- **--children** (optional flag): for every key in `KEYS` that supports it (Capability, Epic), resolve exactly one level of children and add them to the fetch. No-op with an informational note for keys that have no children level (e.g. a Story).

## Workflow

### 1. Validate `twg` is available
```bash
twg -v
```
- If this fails (command not found), stop immediately and report: install TWG CLI from `https://developer.atlassian.com/platform/teamwork-graph/twg-cli/getting-started/installation/`. Do not attempt any Jira call.

### 2. Resolve KEYS and the fetch set (orchestrator-side — cheap calls only)
- If the caller passed any keys as arguments, use those as `KEYS` and skip `.env` entirely — there is no partial merge between passed arguments and `.env`.
- If the caller passed no keys at all, read a `.env` file at the repo root and use its `JIRA_KEYS` value (same space/comma-separated parsing rule) as `KEYS`.
- If `KEYS` is still empty (no arguments, and `.env` missing or `JIRA_KEYS` unset), stop and ask the caller for at least one key; do not guess or proceed without one.
- `.env` is git-ignored — treat it as local/optional; a missing `.env` file when keys were passed explicitly is not an error.
- The fetch set starts as `KEYS`. If `--children` was passed, for **every** key in `KEYS`:
  - Run `twg context jira workitem {key} --relationships jira_work_item_has_child_jira_work_item --detail summary -o json`.
  - Read `data.relationshipSummary[].targets[].key` (or derive the key from the target's `url`/`ari` if `key` is absent) for every target where `relationshipName == jira_work_item_has_child_jira_work_item`.
  - Add each resolved child key to the fetch set.
  - If that key's issue type has no children relationship returned (e.g. a Story), report this as informational and continue without error — do not fail the run over it.

### 3. Freshness pre-check (orchestrator-side — cheap calls only)
For every key in the fetch set:
- Look for an existing output file matching `./ai-workflow/raw-requirements/*_{key}.md` and read its `updated` frontmatter value, if the file exists.
- Run `twg jira workitem get {key} --fields updated -o json` and read `data[0].updated`.
- If no existing file: mark the key `created`.
- If an existing file's `updated` matches the live value: mark the key `unchanged` and drop it from the full-fetch batch (do not include it in step 4).
- If an existing file's `updated` differs: mark the key `updated` and keep it in the full-fetch batch.

If every key resolves to `unchanged`, skip step 4 entirely and go straight to step 5 (still upsert `req-sync-log.md` to reflect the all-unchanged run).

### 4. Dispatch one batched subagent for the full fetch and render
Dispatch exactly one subagent (Task tool) carrying:
- The list of keys needing a full fetch (i.e. everything not marked `unchanged` in step 3).
- The keys (from step 2) that had children resolved via `--children`, and their resolved child keys — so the subagent knows which item gets a `Children` table.
- The four template file contents from `./skills/load-raw-req/templates/`.
- The target output directory `./ai-workflow/raw-requirements/`.

The subagent's job, entirely inside its own context (never surfaced to the orchestrator):
1. `twg jira workitem get {keys...} --full -o json` — batched multi-key call for full content (description, `issuetype`, `created`, `updated`, `issuelinks`).
2. For each item:
   - Pick the template by `issuetype.name`: `Capability` → `templates/capability.md`, `Epic` → `templates/epic.md`, `Story` → `templates/story.md`, anything else → `templates/default.md`.
   - Convert Jira's ADF/HTML `description` to markdown. Strip HTML tags/inline styles. Preserve content over exact fidelity.
   - Acceptance Criteria has no fixed Jira field (unlike ADO) — it is project-specific. Discover it via `twg jira workitem field` custom-field metadata (matching a display name such as "Acceptance Criteria") if the project defines one, and render its content under that heading. If no such field exists for the project, leave the `## Acceptance Criteria` heading present with no fabricated content rather than inventing criteria from the description.
   - Build the `Children` table (key, title, type, status) from step 2's resolved children when this item had `--children` applied to it; omit the section entirely if empty.
   - Build the `Linked Work Items` table from the item's `issuelinks[]`: key = the linked issue's key, link type = `type.outward` (or `type.inward` depending on which side is populated), title = linked issue's summary, URL = linked issue's browse URL. Omit the section entirely if empty.
   - Write frontmatter: `id`, `title` (from `summary`), `issuetype` (from `issuetype.name`), `created`, `updated`.
   - Determine the output filename: `<issuetype-name-lowercased>_<key>.md` if `issuetype.name` is Capability/Epic/Story, otherwise `<real-issuetype-name-lowercased>_<key>.md` using `default.md`'s content (the filename always reflects the real issue type, even on the fallback template).
   - Write the file to `./ai-workflow/raw-requirements/`.
3. If a given key fails (deleted/inaccessible/permission error), skip only that key, note the failure, and continue with the rest of the batch — do not abort the whole dispatch.
4. Upsert `./ai-workflow/raw-requirements/req-sync-log.md` (see step 5 format below) for every key touched by this run — both the ones just fetched and the `unchanged` ones already known from step 3. Keys not touched by this run are left completely untouched in the log.
5. Return to the orchestrator ONLY a terse per-key status list: `[{key, issuetype, file, status: created|updated|unchanged|failed}]`. Never return raw Jira field content, descriptions, or comments to the orchestrator.

### 5. `req-sync-log.md` format
A single persistent table, one row per Jira key ever synced by this skill — not scoped to one run. Every invocation upserts (inserts or replaces) only the rows for keys it touched; every other row is left exactly as it was:

```markdown
# Raw Requirements Sync Log

| Key | File Name | Title | TimeStamp | Status |
|-----|-----------|-------|-----------|--------|
| KAN-1 | epic_KAN-1.md | Test EPIC | 2026-08-05T18:40:00-0400 | created |
| KAN-2 | story_KAN-2.md | Test story | 2026-08-05T18:43:00-0400 | updated |
| KAN-3 | task_KAN-3.md | Test related task | 2026-08-05T18:40:00-0400 | unchanged |
```

Column rules:
- **Key**: the Jira issue key. One row per key, never duplicated — re-syncing a key replaces its existing row in place rather than appending a new one.
- **File Name**: the output file under `./ai-workflow/raw-requirements/` holding that key's local cache of the Jira content.
- **Title**: the item's `summary`, refreshed whenever the row is updated.
- **TimeStamp**: the ISO timestamp of the run that last *synced* (created or updated — i.e. actually fetched and wrote) this key. **Do not update this value when the row's status is `unchanged`** — leave the existing TimeStamp exactly as it was. Only `created`/`updated` rows get the current run's timestamp.
- **Status**: `created` (first time this key was written), `updated` (content changed since the last sync), `unchanged` (checked this run, no change), or `failed` (fetch failed — TimeStamp also not updated in this case). Status always reflects the result of the most recent run that touched this key, even when TimeStamp doesn't move.

If the file doesn't exist yet, create it with just the header and the rows for this run. If it exists, parse the existing table, upsert rows by Key, and rewrite the whole file with the merged table (existing row order preserved; new keys appended at the end).

### 6. Relay result
Report back to the caller only the terse per-key status list from the subagent (plus the freshness-skip list from step 3). Never surface raw Jira payloads in the orchestrating conversation.

## Notes for implementers
- `twg context jira workitem`'s `jira_work_item_has_child_jira_work_item` relationship was confirmed live against an Epic→Story pair; it is assumed to also apply to Capability→Epic since the graph edge is issue-type agnostic. Re-verify against a real Capability hierarchy before relying on this for that level.
- `issuelinks` on `twg jira workitem get --full` is the authoritative source for the Linked Work Items table — richer than `context`'s generic `jira_work_item_links_jira_work_item` relationship summary (it includes the exact link type label and target status/issuetype directly).
- `twg` auth/site resolution is handled entirely by `twg`'s own `auth.conf` — this skill does not manage or read any Jira credentials itself. Pass `-s <site>` only when the caller has specified a non-default site.
