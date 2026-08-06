## Context

The repo already has a similar-shaped flow for Azure DevOps (`.ai-automation/skills/load-req` + `sync-req` agent + `functional-requirements-raw.instructions.md`), which this change deliberately does not reuse or extend — it's PowerShell/ADO-specific and slated for removal. This change is Jira-native and builds entirely on the `twg` CLI (v1.1.1, already installed and authenticated machine-wide via its own `auth.conf`) and its bundled global skills (`twg`, `twg-jira`, `twg-context-discovery`). No repo-level Jira credentials are introduced.

The repo is also mid-migration from `.ai-automation`-rooted assets (mapped into `.claude`/`.github` via `install.py`/`create-links.ps1`) to flatter top-level `./skills`, `./commands`, `./rules` directories, symlinked into `./.claude/*` for in-place testing. This change is the first consumer of that new layout.

## Goals / Non-Goals

**Goals:**
- Fetch Jira Capability/Epic/Story (and other story-level) work items into `ai-workflow/raw-requirements/` markdown, matching the ADO flow's spirit (structured, source-of-truth-preserving raw requirement files) but adapted to Jira's fields and hierarchy.
- Keep the orchestrating conversation's context free of raw Jira payloads (full descriptions, comments, custom fields) — only a subagent that does the actual `twg` calls sees that data; the orchestrator sees terse status only.
- Support one level of children expansion (Capability→Epic, Epic→Story) via `--children`, without guessing JQL — using `twg context jira workitem`'s typed relationships.
- Track per-item freshness cheaply via Jira's `updated` field, avoiding any backup/diff machinery.
- Land the skill/command/rules files under the new top-level `./skills`, `./commands`, `./rules` layout, symlinked into `.claude/*`.

**Non-Goals:**
- No changes to or removal of the legacy `.ai-automation` ADO flow (tracked separately).
- No multi-level cascade (`--children` never recurses past one level; Capability→Story requires two invocations or an explicit ID list).
- No full content-diff changelog (`req-sync-log.md` reports status only, not a prose summary of what changed).
- No new Jira write/mutation capability — this is read-only.
- No vendoring of `twg` itself or reimplementing its Jira access; it is invoked as an external CLI dependency.

## Decisions

**One generic `/load-raw-req` command, not per-type commands.**
Issue type is read off the fetched item (`issuetype` field from `twg jira workitem get`) and used to select the render template, rather than requiring the caller to declare "capability" vs "epic" vs "story" up front. Avoids duplicating the same flow three times and avoids asking the user for information Jira already has. Trade-off: slightly less explicit in command-palette autocomplete than three dedicated commands would be.

**Batched single-subagent dispatch, not per-item fan-out.**
The orchestrating `SKILL.md` does the cheap freshness pre-check and children-resolution itself (small payloads), then dispatches exactly one subagent per invocation that does the full `workitem get --full` + `context jira workitem` calls for the entire merged ID set and writes all files. This keeps the raw Jira payload out of the orchestrator's context (the actual isolation goal) while still letting `twg jira workitem get` batch multiple keys in a single call, rather than N isolated subagents each paying dispatch overhead and losing that batching.

**Freshness via `updated` timestamp comparison, not content diff.**
Each output file's frontmatter carries `updated` (Jira's last-modified timestamp). Before a full fetch, a cheap `twg jira workitem get <id> --fields updated` call compares against the stored value; unchanged items are skipped entirely (no write, no full fetch). This is simpler than the ADO flow's backup-to-`.workflow-temp` + LLM diff approach, at the cost of being unable to describe *what* changed — `req-sync-log.md` reports `created/updated/unchanged` status only, never a change narrative.

**`--children` is exactly one level, applied uniformly to every key in the list, always.**
No `--children=deep`/recursive option, and no primary/extra distinction among the passed keys — `KEYS` is a flat, order-independent list, and `--children` resolves one level of children for every key in it that supports the relationship (Capability→Epic, Epic→Story), not just a designated "anchor." This removes an artificial asymmetry: earlier revisions treated the first key as a special anchor that alone received `--children` expansion, but there is no reason a multi-epic run (`EPIC-45 EPIC-99 --children`) shouldn't expand both. Recursion depth control was considered (`--children=1` vs `--children=deep`) but rejected in favor of the simplest flag shape — two-level traversal (e.g. Capability→Story) is achieved by invoking the command twice, or by naming the deeper keys explicitly in the flat list.

**Linked/children relationships via `twg context jira workitem`, not hand-rolled JQL.**
Rather than composing `parent = <epicKey>`-style JQL to find children, or guessing `issuelinks` field shapes, the subagent uses `twg context jira workitem <ids...>` (typed parity with `getTeamworkGraphContext`) to get both the children relationship and linked-issue relationships in one typed, safe call. This matches `twg-jira`'s own guidance to prefer typed context reads over ad hoc JQL for relationship questions.

**Templates: `capability.md`, `epic.md`, `story.md`, `default.md`.**
Exactly these three named templates plus a fallback. An item whose `issuetype` doesn't match one of the three named templates renders through `default.md` but keeps its real issue type in the output filename (e.g. `bug_ABC-42.md`), so the file name always reflects Jira ground truth even when the render is generic.

**Top-level `./skills`, `./commands`, `./rules` are canonical; `.claude/*` are symlinks.**
Matches the repo's existing symlink convention (previously `install.py`/`create-links.ps1` mapped `.ai-automation/*` into `.claude`/`.github`) but rooted one level up, since `.ai-automation` is being phased out. This change only needs to create three symlinks (`.claude/skills/load-raw-req`, `.claude/commands/load-raw-req.md`, `.claude/rules`) — it does not need to touch or extend `install.py`/`create-links.ps1`, since those are scoped to the `.ai-automation` layout being replaced.

## Risks / Trade-offs

- **[Risk]** Capability→Epic may not be a native Jira parent/child relationship (Capability is likely a custom hierarchy level, e.g. Advanced Roadmaps) → `twg context jira workitem`'s "children" edge may not surface it the same way it surfaces native Epic→Story. **Mitigation**: verify with live `twg help`/a real capability during implementation before assuming the same relationship name works for both levels; if it doesn't, document the actual command needed per level in `SKILL.md`.
- **[Risk]** Skipping unchanged items based purely on `updated` timestamp means a Jira edit that doesn't bump `updated` (rare, but e.g. some automation-driven field changes) would be silently missed → **Mitigation**: acceptable per explicit design choice; `req-sync-log.md` still shows `unchanged` transparently so a stale file is visible, not silent.
- **[Risk]** Batched single-subagent dispatch means one failing item (e.g. a deleted/inaccessible Jira key) could fail the whole batch → **Mitigation**: subagent should report partial success per item (skip and note the failure in status/log) rather than aborting the entire batch on one bad ID.
- **[Trade-off]** No prose changelog means "what changed" requires opening the Jira item directly; `req-sync-log.md` only tells you *that* something changed, not *what* — accepted trade-off for avoiding backup/diff complexity.

## Migration Plan

Additive only — no existing behavior changes, no rollback complexity. New files are created under `./skills/load-raw-req/`, `./commands/`, and three new symlinks are added under `.claude/`. If problems surface, the symlinks and new directories can simply be removed without affecting `.ai-automation` or any other existing flow.

## Open Questions

- Exact `twg context jira workitem` relationship name(s) for children at each hierarchy level (Capability→Epic vs Epic→Story) — confirm via live `twg help describe` during implementation.
- Exact field/shape for "linked work items" (issuelinks) returned by `twg context jira workitem` vs `twg jira workitem get --field issuelinks` — confirm which is authoritative before finalizing the render template's Linked Work Items table columns.
