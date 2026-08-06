## Why

Solution architects need a repeatable way to pull raw Jira requirements (Capability, Epic, Story, or other story-level work items) into version-controlled markdown before drafting SAD/design artifacts. The existing ADO-based flow (`.ai-automation/skills/load-req`, `sync-req` agent) is subject to removal, is PowerShell/ADO-specific, and has no concept of Jira's issue-type variety, linked-work relationships, or epic/capability hierarchy. A Jira-native replacement is needed that reuses the already-installed `twg` CLI and its Jira skills rather than reimplementing Jira access.

## What Changes

- New `./skills/load-raw-req/` skill: validates `twg -v` is available (guides to the TWG CLI install docs if missing), accepts a flat list of Jira keys (no primary/extra distinction), performs a cheap `updated`-timestamp freshness check per key before doing any full fetch, and dispatches a single batched subagent to fetch content (`twg jira workitem get --full`) and relationships (`twg context jira workitem`) for the whole merged key set.
- New `./skills/load-raw-req/templates/{capability,epic,story,default}.md` — per-issue-type output templates; unmatched issue types fall back to `default.md` but keep their real issue type in the output filename.
- New `./commands/load-raw-req.md` slash command: single generic command (issue type is read off each fetched item, not passed by the caller); accepts a flat, order-independent list of keys and a `--children` flag that pulls exactly one level of children (Capability→Epic or Epic→Story) for **every** key in the list that supports it, via `twg context jira workitem`'s children relationship.
- Context-isolated fetch: raw Jira payloads (full description, comments, custom fields) are only ever read inside the dispatched subagent's own context; the orchestrator only receives a terse per-item status list.
- Output files at `./ai-workflow/raw-requirements/<issuetype>_<jiraWorkItemId>.md`, each with `id/title/issuetype/created/updated` frontmatter plus `Description`, `Acceptance Criteria`, `Children`, and `Linked Work Items` sections.
- New `./ai-workflow/raw-requirements/req-sync-log.md`: a single persistent table (Key, File Name, Title, TimeStamp, Status), one row per Jira key ever synced. Each run upserts only the rows for keys it touched; TimeStamp only advances on `created`/`updated` rows, never on `unchanged`.
- New top-level `./skills`, `./commands`, `./rules` directories become the canonical source; `./.claude/skills/load-raw-req`, `./.claude/commands/load-raw-req.md`, and `./.claude/rules` become symlinks into them for in-place testing.
- `.env` fallback: when the caller passes no keys at all, the skill reads a single `JIRA_KEYS` value (a flat list, same as command arguments) from a git-ignored `.env` at the repo root. Any explicit arguments take full precedence and skip `.env` entirely — there is no partial merge between passed arguments and `.env`.
- **BREAKING**: none — this is additive. The legacy `.ai-automation` ADO flow is explicitly out of scope and untouched by this change (separate future removal).

## Capabilities

### New Capabilities
- `jira-raw-requirements`: Fetching, freshness-checking, and rendering Jira Capability/Epic/Story (and other) work items into `ai-workflow/raw-requirements/` markdown files, including linked/children work item sections and a per-run sync log.

### Modified Capabilities
- None — no existing specs in this repo to modify.

## Impact

- New directories: `./skills/load-raw-req/`, `./commands/`, `./ai-workflow/raw-requirements/`.
- New symlinks: `./.claude/skills/load-raw-req`, `./.claude/commands/load-raw-req.md`, `./.claude/rules` → `./rules`.
- External dependency: `twg` CLI (already installed on this machine, globally authenticated via its own `auth.conf`) plus its `twg-jira` and `twg-context-discovery`-adjacent commands. No new repo-level Jira credentials/env vars are required for authentication.
- `.env.example` gains a `JIRA_KEYS` entry under a `# Raw Requirements` header (default-ID fallback only, not credentials); `.env` remains git-ignored.
- No changes to `.ai-automation/*` (ADO flow) — left as-is pending its own future removal.
