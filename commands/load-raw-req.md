---
description: "Load Jira Capability/Epic/Story (or other) work items into ai-workflow/raw-requirements/ via the load-raw-req skill."
argument-hint: "[KEY...] [--children]"
---

# /load-raw-req

Parse `$ARGUMENTS`:
1. Remove the `--children` flag if present (anywhere in the string) — record it separately.
2. Split what remains on any run of whitespace and/or commas (i.e. spaces, commas, or "comma then space" all count as the same separator), and drop empty tokens.
3. Every resulting token is a `KEY` — a flat list, in any order. There is no primary/extra distinction; `--children`, if passed, applies to every key that supports it.
4. If the list is empty (no arguments given, or only `--children` was given), fall through to `.env` — do not treat this as an error yet.

This means all of the following are equivalent ways to pass the same three keys:
```
/load-raw-req CAP-123 ABC-45 ABC-99
/load-raw-req CAP-123, ABC-45, ABC-99
/load-raw-req CAP-123,ABC-45,ABC-99
```

More examples:
```
/load-raw-req CAP-123
/load-raw-req EPIC-45 --children
/load-raw-req ABC-789
/load-raw-req EPIC-45 EPIC-99 --children     # --children applies to every key that supports it
/load-raw-req                                # no keys given → falls back to .env JIRA_KEYS
/load-raw-req --children                     # same fallback, --children still applies
```

Do not ask the caller which Jira issue type any key is — that is determined after fetch, from each item's own `issuetype` field.

Invoke the `load-raw-req` skill with the parsed list of `KEY`s (or none, if omitted) and the `--children` flag. The skill itself resolves the `.env` fallback (`JIRA_KEYS`) when no keys were passed — this command does not read `.env` directly. Relay the skill's final per-key status list (and `req-sync-log.md` summary) back to the user. Do not surface any raw Jira payload in this conversation — the skill's dispatched subagent is responsible for keeping that isolated.
