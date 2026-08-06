# jira-raw-requirements Specification

## Purpose

TBD - created by archiving change load-raw-req-jira. Update Purpose after archive.

## Requirements

### Requirement: TWG availability guard
The skill SHALL verify the `twg` CLI is available before performing any Jira fetch, and SHALL guide the user to the TWG CLI installation documentation when it is not.

#### Scenario: twg is installed
- **WHEN** the skill runs `twg -v` and it succeeds
- **THEN** the skill proceeds to the freshness check and fetch steps

#### Scenario: twg is missing
- **WHEN** the skill runs `twg -v` and the command is not found
- **THEN** the skill stops and reports the TWG CLI installation URL (`https://developer.atlassian.com/platform/teamwork-graph/twg-cli/getting-started/installation/`) without attempting any Jira call

### Requirement: Flat key list, resolved by issue type
The `/load-raw-req` command SHALL accept one or more Jira work item keys (Capability, Epic, Story, or any other issue type) as a flat, order-independent list — there SHALL be no primary/anchor-vs-extra distinction among passed keys — separated by whitespace, commas, or a mix of both, without requiring the caller to declare any key's issue type. The render template for each key SHALL be selected from the `issuetype` field returned by Jira for that key.

#### Scenario: Multiple keys, space-separated
- **WHEN** `/load-raw-req CAP-123 ABC-45 ABC-99` is invoked
- **THEN** CAP-123, ABC-45, and ABC-99 are all fetched and rendered in the same run, with no key treated differently from another

#### Scenario: Multiple keys, comma-separated
- **WHEN** `/load-raw-req CAP-123, ABC-45, ABC-99` is invoked
- **THEN** the same three keys are fetched and rendered in the same run, identically to the space-separated form

#### Scenario: Known issue type
- **WHEN** a fetched item's `issuetype` is Capability, Epic, or Story
- **THEN** the corresponding named template (`capability.md`, `epic.md`, or `story.md`) is used to render its output file

#### Scenario: Unmatched issue type
- **WHEN** a fetched item's `issuetype` does not match Capability, Epic, or Story
- **THEN** the `default.md` template is used to render the content, and the output filename uses the item's real issue type as its prefix (e.g. `bug_ABC-42.md`)

### Requirement: One-level children expansion, applied per key
When invoked with `--children`, the command SHALL resolve exactly one level of child work items (Capability→Epic or Epic→Story) via `twg context jira workitem`'s typed children relationship for **every** key in the list that supports the relationship, and SHALL include those children in the same fetch batch.

#### Scenario: Children requested on an Epic
- **WHEN** `/load-raw-req EPIC-45 --children` is invoked
- **THEN** the Epic's immediate Story-level children are resolved and included in the fetch set, and each child is freshness-checked and rendered as its own output file

#### Scenario: Children requested on a Capability
- **WHEN** `/load-raw-req CAP-123 --children` is invoked
- **THEN** the Capability's immediate Epic-level children are resolved and included in the fetch set; Story-level grandchildren are NOT automatically included

#### Scenario: Children requested on multiple keys at once
- **WHEN** `/load-raw-req EPIC-45 EPIC-99 --children` is invoked
- **THEN** one level of children is resolved independently for both EPIC-45 and EPIC-99, and all resolved children from both are included in the same fetch batch

#### Scenario: No children flag
- **WHEN** the command is invoked without `--children`
- **THEN** only the explicitly given keys are fetched; no relationship resolution is performed

### Requirement: .env fallback for omitted keys
When the caller passes no keys at all, the skill SHALL read a single `JIRA_KEYS` value from a git-ignored `.env` file at the repo root and split it with the same space/comma-separated parsing rule as command arguments, using the full resulting list as the flat key list. Any explicitly passed keys SHALL take full precedence and skip `.env` entirely — there is no partial merge between passed arguments and `.env`.

#### Scenario: No arguments given, .env provides the full key list
- **WHEN** `/load-raw-req` is invoked with no arguments and `.env` defines `JIRA_KEYS=CAP-123,ABC-45,ABC-99`
- **THEN** the skill fetches all three keys as if they had been passed explicitly, with no key treated as special

#### Scenario: Explicit arguments override .env entirely
- **WHEN** `/load-raw-req CAP-999` is invoked and `.env` defines a different `JIRA_KEYS`
- **THEN** the skill uses only `CAP-999`, ignoring `.env`'s `JIRA_KEYS` completely

#### Scenario: No argument and no .env fallback available
- **WHEN** `/load-raw-req` is invoked with no arguments and no `.env` file (or no `JIRA_KEYS` in it) exists
- **THEN** the skill stops and asks the caller for at least one key rather than guessing or proceeding

### Requirement: Context-isolated fetch dispatch
Raw Jira payloads (full description, comments, custom fields) SHALL only be read inside a dispatched subagent's own context. The orchestrating skill SHALL only receive a terse per-item status list back from that dispatch, never the raw payload.

#### Scenario: Single batched dispatch
- **WHEN** the skill has resolved the full set of keys to fetch (the flat passed/`.env` list plus any one-level children)
- **THEN** exactly one subagent dispatch performs `twg jira workitem get --full` and `twg context jira workitem` for the entire merged set, writes all output files and the sync log, and returns only a per-item status list to the orchestrator

### Requirement: Timestamp-based freshness check
Before performing a full fetch for a given ID, the skill SHALL compare the `updated` value in that ID's existing output file frontmatter (if any) against a cheap live `twg jira workitem get <id> --fields updated` call, and SHALL skip the full fetch and rewrite when the values match.

#### Scenario: Item unchanged since last run
- **WHEN** an output file already exists for an ID and its stored `updated` frontmatter matches the current live `updated` value
- **THEN** the skill does not perform a full fetch or rewrite for that ID, and reports its status as `unchanged`

#### Scenario: Item changed since last run
- **WHEN** an output file already exists for an ID and its stored `updated` frontmatter differs from the current live `updated` value
- **THEN** the skill performs a full fetch, rewrites the output file with the new content and `updated` value, and reports its status as `updated`

#### Scenario: Item fetched for the first time
- **WHEN** no output file exists yet for a given ID
- **THEN** the skill performs a full fetch, writes a new output file, and reports its status as `created`

### Requirement: Output file structure
Each rendered output file SHALL be written to `./ai-workflow/raw-requirements/<issuetype>_<jiraWorkItemId>.md` with frontmatter containing `id`, `title`, `issuetype`, `created`, and `updated`, followed by `Description` and `Acceptance Criteria` sections sourced from Jira, a `Children` section when child items were resolved, and a `Linked Work Items` section listing directly linked issues.

#### Scenario: Item with no children and no links
- **WHEN** a fetched item has no resolved children and no linked work items
- **THEN** the output file omits the `Children` and `Linked Work Items` sections rather than rendering them empty

#### Scenario: Item with children and links
- **WHEN** a fetched item has resolved children and/or linked work items
- **THEN** the output file includes a `Children` table (key, title, type, status) and/or a `Linked Work Items` table (key, link type, title, URL) as applicable

### Requirement: Persistent single-table sync log
`./ai-workflow/raw-requirements/req-sync-log.md` SHALL contain a single Markdown table with one row per Jira key ever synced by this skill, with columns Key, File Name, Title, TimeStamp, and Status. Every run SHALL upsert only the rows for the keys it touched (insert if new, replace in place if existing); rows for keys not touched by that run SHALL be left unchanged. TimeStamp SHALL be updated only when the row's Status is `created` or `updated` (i.e. the key was actually fetched and written this run) — it SHALL NOT be updated when Status is `unchanged` or `failed`. Status SHALL always reflect the result of the most recent run that touched that key.

#### Scenario: Run with mixed statuses
- **WHEN** a run touches a batch where some items are created, some updated, and some unchanged
- **THEN** each touched key's row is upserted with its current Status, TimeStamp is refreshed only for the created/updated rows, and the unchanged row keeps its prior TimeStamp while its Status reflects `unchanged`

#### Scenario: Keys from a previous run not touched by this run
- **WHEN** a run's fetch set does not include a key that has a row from an earlier run
- **THEN** that key's row (File Name, Title, TimeStamp, Status) is left completely untouched in the log

#### Scenario: Re-syncing a previously logged key
- **WHEN** a key that already has a row in the log is synced again in a later run
- **THEN** its existing row is replaced in place with the new Title/TimeStamp/Status rather than a duplicate row being appended

### Requirement: Canonical top-level layout with symlinks
The skill, command, and rules files SHALL live under top-level `./skills/load-raw-req/`, `./commands/load-raw-req.md`, and `./rules/`, with `./.claude/skills/load-raw-req`, `./.claude/commands/load-raw-req.md`, and `./.claude/rules` provided as symlinks into those canonical locations for in-place testing.

#### Scenario: Editing the canonical source is immediately testable
- **WHEN** a file under `./skills/load-raw-req/` or `./commands/load-raw-req.md` is edited
- **THEN** the change is immediately visible through the corresponding `.claude/*` symlink without any copy or sync step
