## 1. Verify twg relationship contracts

- [x] 1.1 Confirmed live against `vzhuck` site (KAN-1 Epic / KAN-2 Story): children relationship is `jira_work_item_has_child_jira_work_item` (direction `outbound`, `targetType: JiraIssue`) via `twg context jira workitem <id> --relationships jira_work_item_has_child_jira_work_item --detail summary`. Capability→Epic assumed to use the same generic relationship name (graph edge is issue-type agnostic); re-verify if a real Capability-hierarchy site shows otherwise.
- [x] 1.2 Confirmed: linked-issue data comes from `twg jira workitem get <id> --full` (or `--field issuelinks`), not `context`. Its `issuelinks[]` array gives the exact link type label (`type.outward`/`type.inward`, e.g. "relates to") plus target key/summary/status/issuetype directly — richer than context's generic `jira_work_item_links_jira_work_item` relationship summary, so no separate context call is needed for links.

## 2. Scaffold canonical directories

- [x] 2.1 Create `./skills/load-raw-req/SKILL.md`
- [x] 2.2 Create `./skills/load-raw-req/templates/capability.md`
- [x] 2.3 Create `./skills/load-raw-req/templates/epic.md`
- [x] 2.4 Create `./skills/load-raw-req/templates/story.md`
- [x] 2.5 Create `./skills/load-raw-req/templates/default.md`
- [x] 2.6 Create `./commands/load-raw-req.md`
- [x] 2.7 Ensure `./rules/` exists as the canonical rules directory (already present)

## 3. Symlink into .claude for in-place testing

- [x] 3.1 Create symlink `./.claude/skills/load-raw-req` → `../../skills/load-raw-req`
- [x] 3.2 Create symlink `./.claude/commands/load-raw-req.md` → `../../commands/load-raw-req.md`
- [x] 3.3 Create symlink `./.claude/rules` → `../rules`

## 4. Implement SKILL.md orchestration logic

- [x] 4.1 Implement `twg -v` guard with install-link guidance on failure
- [x] 4.2 Implement flat KEYS list parsing (accepts space-separated, comma-separated, or mixed; no primary/extra distinction)
- [x] 4.2.1 Implement `.env` fallback (single `JIRA_KEYS` value, same flat-list parsing) for when no arguments are passed at all; created git-ignored `.env` with test values and added `JIRA_KEYS` under a `# Raw Requirements` header in `.env.example`
- [x] 4.3 Implement per-key freshness pre-check (read existing file frontmatter `updated`, compare against cheap `twg jira workitem get <key> --fields updated`)
- [x] 4.4 Implement one-level `--children` resolution via `twg context jira workitem`, applied to every key in KEYS that supports it (Epic/Capability), merging resolved child keys into the fetch set
- [x] 4.5 Implement the single batched subagent dispatch (full fetch + context relationships + render + write, for the whole merged ID set)
- [x] 4.6 Ensure the subagent handles partial failures (e.g. inaccessible/deleted ID) by skipping and noting the failure rather than aborting the whole batch
- [x] 4.7 Ensure the orchestrator only receives the terse per-item status list back from the dispatch (no raw payload)

## 5. Implement rendering and output

- [x] 5.1 Implement issue-type → template selection (capability/epic/story/default) based on fetched `issuetype`
- [x] 5.2 Implement output filename derivation: `<issuetype-or-real-type-for-default>_<id>.md`
- [x] 5.3 Implement frontmatter generation (`id`, `title`, `issuetype`, `created`, `updated`)
- [x] 5.4 Implement HTML/ADF-to-markdown conversion for Description, and custom-field discovery for Acceptance Criteria (no fixed Jira field exists for it, unlike ADO)
- [x] 5.5 Implement conditional `Children` table rendering (key, title, type, status) — omitted when empty
- [x] 5.6 Implement conditional `Linked Work Items` table rendering (key, link type, title, URL) — omitted when empty
- [x] 5.7 Write output files to `./ai-workflow/raw-requirements/`

## 6. Implement req-sync-log.md

- [x] 6.1 Implement per-item status classification (created/updated/unchanged/failed) from the freshness check results
- [x] 6.2 Implement single-table format (Key, File Name, Title, TimeStamp, Status) — parse existing table, upsert rows by Key
- [x] 6.3 Implement TimeStamp update rule: only advance TimeStamp for created/updated rows; leave it untouched for unchanged/failed rows
- [x] 6.4 Upsert `./ai-workflow/raw-requirements/req-sync-log.md` on every run — only rows for touched keys change; other rows (and their TimeStamp) are left exactly as they were

## 7. Implement /load-raw-req command

- [x] 7.1 Define command argument parsing: flat KEYS list (space/comma/mixed-separated, no primary/extra distinction), optional `--children` flag
- [x] 7.2 Wire the command to invoke the `load-raw-req` skill with parsed arguments
- [x] 7.3 Add a no-op/informational message when `--children` is passed on a key whose issue type has no defined children level

## 8. Validate end-to-end

- [x] 8.1 Ran against real KAN-1 (Epic, substituting for Capability — no Capability issue type exists on the test site) with `--children`; verified `epic_KAN-1.md` + sync log render correctly, including a real linked item (KAN-3, "relates to")
- [x] 8.2 Ran against KAN-1 Epic with children resolution; `story_KAN-2.md` created and KAN-1's `Children` table populated with the resolved child
- [x] 8.3 Re-checked KAN-2 via `--fields updated`: live value matched stored frontmatter exactly, confirming the unchanged path would skip rewrite
- [x] 8.4 Edited KAN-2's description via `twg jira workitem update`, reran the freshness check: `updated` changed (`...21:56:57` → `...18:42:22`), rewrote `story_KAN-2.md` with new content/timestamp and updated `req-sync-log.md` to show `KAN-2: updated`, `KAN-1`/`KAN-3: unchanged`
- [x] 8.5 KAN-3 (issue type Task, unmatched) rendered via `default.md` content, filename `task_KAN-3.md` uses its real issue type
- [x] 8.6 Confirmed via `.claude/skills/load-raw-req/SKILL.md`, `.claude/commands/load-raw-req.md` reading through correctly, and the skill appearing in the live skill listing immediately after the symlink was created — no copy/sync step needed
