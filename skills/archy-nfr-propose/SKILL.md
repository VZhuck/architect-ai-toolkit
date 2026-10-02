---
name: archy-nfr-propose
description: "Draft the project's NFR document: take the existing NFR document (golden copy, GC) as the source of truth, apply reviewed archy-nfr-miner registries as deltas (dedupe across runs, match against GC, surface conflicts and open questions first), write a format-preserving draft plus a change log, validate it, and walk the user through review. Resumable across conversations; never writes the target document."
argument-hint: "nfr_doc (optional, repo-relative; default $NFR_PATH, else NFR_PATH in the repo-root .env), runs (optional run ids/folders; default: choose from ai-workflow/nfr-state), draft (optional draft folder name)"
---

# NFR Propose

Turn reviewed miner runs into the next version of the NFR document. GC (the existing document) is the source of truth, and the runs are **deltas**. Everything happens in a **draft folder**:
- `draft.md` is exactly what the document will become.
- `nfr-draft-log.md` records why each row changed, and what is still open.

A draft is identified by its target document plus its set of input runs, so invoking the skill again with the same inputs, in any conversation, resumes it.

```
 pre-flight -> Stage 0 resolve -> Stage 1 merge + draft -> Stage 2 review -> hand-off
 (taxonomy)    (GC, runs, draft)  (dedupe, match, write,   (main thread)     (/archy-nfr-apply)
                                   validate)
```

## Parameters

- **nfr_doc** (optional): the target NFR document. If it is not given, the resolver takes `NFR_PATH` from the environment, then from the `.env` file at the repository root. There is no built-in default. A relative path is relative to the **repository root** (the git top level), never to `<skill-dir>`. **Never guess it**, and never suggest a path of your own. If no source sets it, ask.
- **runs** (optional): miner runs to apply, as run IDs (`payments-20260924-1402`), run folders, or registry paths, comma-separated. If omitted, the user chooses them in Stage 0.
- **draft** (optional): an explicit draft folder name, mostly for tests and evals.

**Paths used below:**
- `<skill-dir>`: the folder containing this `SKILL.md` (`skills/archy-nfr-propose` in this repository; usually `.claude/skills/archy-nfr-propose` once installed).
- The taxonomy skill is `<skill-dir>/../archy-init-nfr-taxonomy`.
- The review loop is `<skill-dir>/../archy-nfr-miner/references/nfr-review.md`.
- `<draft_dir>` is `ai-workflow/nfr-draft/<draft_id>`.

The scripts declare their own dependencies (PEP 723). Run them with `uv run <script>`.

## Pre-flight (before anything else)

1. **Taxonomy.** Run `uv run python <skill-dir>/../archy-init-nfr-taxonomy/scripts/init_taxonomy.py`. Its JSON `target` is `taxonomy_dir`. If files were `overwritten`, mention it: local tailoring was replaced. If the init skill is not installed, stop and say so.
2. **Load** these seven files from `taxonomy_dir`: `nfr-priorities.md`, `business-drivers.md`, `quality-attributes.md`, `nfr-state.yaml`, `nfr-registry-log.md`, `nfr-req-tmpl.md`, and `nfr-draft-log.md`.
3. **Review loop.** Check that `<skill-dir>/../archy-nfr-miner/references/nfr-review.md` exists.

**Hard stop** if anything above is missing. Name the missing file and write nothing. A taxonomy file deleted after init comes back by re-running `archy-init-nfr-taxonomy` with `force`, and a missing review loop means `archy-nfr-miner` must be installed. Never fall back to another vocabulary.

No draft folder exists yet, so **keep the pre-flight result** (taxonomy version and loaded files) and write it as the first `state_log` entry once Stage 0 has the folder: `gate: pre-flight`, `status: finished`.

## Stage 0: Resolve

1. **Resolve** by running
   `uv run <skill-dir>/scripts/resolve_draft.py [--nfr-doc <nfr_doc>] [--run <r> ...] [--draft <draft>]`.
   It prints `target`, `runs`, `selected`, `unmatched`, `suggested_draft_id`, `draft_exists`, `drafts`, and `retired_ids`. Exit code 2 means there are no miner runs: stop, and suggest `/archy-nfr-miner`.
2. **Target.**
   - `target.needs_path`: ask for the target path (repo-relative) **without suggesting one**, and mention that setting `NFR_PATH` in the repo-root `.env` makes it the default. Then re-run with `--nfr-doc`.
   - Otherwise, name where the path came from (`target.source`: `param`, `env`, or `.env`).
   - `exists: true`: this file is GC, and its format wins.
   - `exists: false`: tell the user "No document at <path>: the draft will start from `nfr-req-tmpl.md`".
3. **Resume check.** If `drafts` has an entry, act on the first one:

   | `match` | Ask |
   | --- | --- |
   | `identical` | "Resume draft X at <stage/step>?" Options: **resume** or **fresh** |
   | `target-only` (no runs given) | list the drafts for this target (stage, step, inputs). Options: **resume X** or **new draft** |
   | `superset` | "Draft X covers <n> of these runs; add <added>?" Options: **add** or **new draft** |
   | `subset` | "Draft X already includes these runs." Options: **resume X** or **new draft** |
   | `partial` | list the overlapping drafts. Default: **new draft** |

   - **`stale_inputs` non-empty:** name the runs whose registry changed since they were merged, offer to merge them again, and set their status to `stale`.
   - **`target_drift` true:** say the document changed since the draft started, and offer to **rebuild** (Stage 1 from `1-parse`, with a new `base.md`).
   - **Fresh:** rename the old folder to `<draft_id>-archived-<yyyymmdd-hhmm>`.
4. **Choose runs** (when `runs` was not given and nothing is resumed). Offer `runs` with the ask-question tool, **multiSelect**. Each option label is the run ID. The most recent run (`latest`) comes first, marked "(most recent)". The description gives the stage/step, entry counts by status, open questions, and the warnings. With more than 4 runs, show a numbered table instead (the same columns, latest marked) and accept `1,3,5`. Re-run the resolver with the chosen `--run` values.
5. **Warn** for each chosen run that has a warning:
   - `not finished (<stage>/<step>)`: "Run X is not reviewed yet; finish it with `/archy-nfr-miner` first?" Options: **include anyway** or **skip**.
   - `no state.yaml`: "Run X has no state.yaml, so its review status is unknown." Options: **include anyway** or **skip**.

   An included run keeps the warning in `reason`. A skipped run is not recorded.
6. **Create the draft** (new or fresh) at `<draft_dir>` = `ai-workflow/nfr-draft/<suggested_draft_id>`. If `draft_exists` is true for a folder that is not the draft you matched, ask for another `draft` name.
   - Copy `taxonomy_dir/nfr-draft-log.md` to `<draft_dir>/nfr-draft-log.md`, keeping the sample rows until step `5-write` replaces them.
   - Create `state.yaml` from `taxonomy_dir/nfr-state.yaml`:

     | Field | Value |
     | --- | --- |
     | `run_id` | the draft folder name |
     | `path_args` | the parameters as the user gave them |
     | `taxonomy_dir` / `taxonomy_version` | from pre-flight (root-relative) |
     | `session_ids` | `[${CLAUDE_SESSION_ID}]` (or `unknown-<yyyymmdd-hhmm>` if not substituted) |
     | `active_skill` | `archy-nfr-propose` |
     | `active_stage` / `active_step` | `stage-1` / `1-parse` |
     | `files_4_review` | one per chosen run: `path` = registry path, `sha256` = `registry_sha256`, `normalized: ""`, `status: pending`, `reason` = warning or `""`, `images: 0` |
     | `target_sad_docs` | `[{path, sha256, exists, draft: draft.md, format_source}]` from `target` |
     | `state_log` | the buffered pre-flight entry, then `gate: stage-0`, `status: finished` |
     | `update_on` | now, with timezone |
7. **Resume a draft.** Append the session ID. For **add**, append the new runs as `pending`. Log `gate: stage-0`. Continue at `active_stage` / `active_step`; `review-parked` goes straight to Stage 2.

**State discipline.** At every step boundary below, update `active_step`, `update_on`, and the per-run statuses, and append a `state_log` entry (`date`, `skill`, `gate`, `change`, `status`). Only the main thread writes `state.yaml`, `draft.md`, `nfr-draft-log.md`, `base.md`, and `changes.json`.

## Stage 1: Merge and draft

Follow [references/nfr-match.md](references/nfr-match.md) for every judgment in this stage. Never ask the user in this stage. The questions go to the log, and Stage 2 asks them.

### 1-parse

- **GC exists:** copy it byte for byte to `<draft_dir>/base.md`. Otherwise run `uv run <skill-dir>/scripts/gc_tables.py base --template <taxonomy_dir>/nfr-req-tmpl.md --out <draft_dir>/base.md`.
- Then run `gc_tables.py parse --doc <draft_dir>/base.md`. **On errors, stop.** List each error (section, line, message), ask the user to fix the document, and log `status: stopped`. Never guess record boundaries.
- Report `nonstandard_ids`, if any: they are kept, and new IDs still use `<TYPE>-###`.

### 1-carry

Read each `pending` or `stale` run registry in `files_4_review` order. Carry over:
- the `## NFR Registry` rows with status `Confirmed`, `Auto`, `TBD`, or `TO REVIEW`
- the `## Open Questions` rows with status `TO REVIEW`
- the `## Conflicts` rows

Each keeps its origin `<run_id>/NFR-###`. Skip `Closed` questions and `## Dropped` rows. Set each run to `merged` once it is carried (a `stale` run replaces its earlier trace rows).

### 2-dedupe, 3-match, 4-ids

Apply sections 2, 3, and 4 of `nfr-match.md`: dedupe across runs, give each delta a disposition against GC, and issue target IDs, using `retired_ids` from Stage 0.

### 5-write

1. Write `nfr-draft-log.md`, replacing the sample rows:
   - `## Change Set`: one row per target ID with disposition `NEW`, `UPDATE`, `CONFLICT`, or `MOVED`
   - `## Trace`: one row per carried delta, including `SAME` and merged ones
   - `## Retired`
   - `## Open Questions`: renumbered `Q1`, `Q2`, ..., with `Target ID` (or the origin for a `TBD` type)
   - `## Conflicts`: renumbered `C1`, ...
   - `## Dropped`
2. Build `<draft_dir>/changes.json` (section 6 of `nfr-match.md`), then render:
   `uv run <skill-dir>/scripts/gc_tables.py patch --doc <draft_dir>/base.md --changes <draft_dir>/changes.json --out <draft_dir>/draft.md`.
   Always render from `base.md`, never incrementally from an old `draft.md`.

### 6-validate

Run `uv run <skill-dir>/scripts/check_draft.py --base <draft_dir>/base.md --draft <draft_dir>/draft.md --changes <draft_dir>/changes.json --taxonomy-dir <taxonomy_dir> [--forbid <id> ...]`, then check yourself:
1. Every carried delta has exactly one `## Trace` row with a disposition.
2. Every `TO REVIEW` entry and every conflict has an open question.
3. Every `Change Set` row's `NFR Category` is verbatim in the catalog (QAR, BD).
4. Every renderable row is in `changes.json`, and nothing else is.

Fix what fails, re-render, and re-check, **at most twice**. An entry that still fails is taken out of `changes.json`, set to `TO REVIEW` with an open question naming the check, and logged with `status: fail`. A `preservation` error that no entry explains (the base itself changed, or the patch misbehaved) is a **hard stop**: do not enter Stage 2, show the error, and log `status: stopped`.

### 7-summary

Show **one table**, with a row per run (counted before dedupe) and a `TOTAL (deduped)` row:

```
| Run                          | Carried | NEW | UPDATE | SAME | MOVED | CONFLICT | Merged dup | Open Q | Conflicts |
| ---------------------------- | ------: | --: | -----: | ---: | ----: | -------: | ---------: | -----: | --------: |
| payments-20260924-1402       |      10 |   4 |      2 |    2 |     0 |        1 |          - |      3 |         1 |
| security-20260926-0930       |       8 |   3 |      1 |    1 |     1 |        0 |          - |      2 |         0 |
| **TOTAL (deduped)**          |      15 |   6 |      3 |    3 |     1 |        1 |          3 |      5 |         2 |
```

Then one line:

```
draft: +6 rows, 3 updated, 0 removed | open: 5 questions, 2 conflicts | base: GC <nfr_doc> | check_draft: ok
```

The `TOTAL (deduped)` `Carried` value must equal the sum of the run rows minus `Merged dup`. If it does not, recount. Then set `active_stage: stage-2`, `active_step: review`.

## Stage 2: Review

Run `<skill-dir>/../archy-nfr-miner/references/nfr-review.md` **in this conversation** with these inputs:
- `registry_file` = `<draft_dir>/nfr-draft-log.md` (its `## Change Set` is the registry)
- `state_file` = `<draft_dir>/state.yaml`
- `taxonomy_dir`
- `scope` = the Change Set, open questions, conflicts, and `## Dropped` (not `SAME` trace rows)
- `allowed_decisions` = all
- `stage_label` = `stage-2-review`
- `id_format` = `typed`

In the propose context, the review commands mean:
- **`c# a`**: keep A. For a GC-vs-delta conflict, GC stays unchanged, and the delta moves to `## Dropped` ("superseded by GC <ID> (C#)").
- **`c# b`**: apply B. The entry becomes an `UPDATE` of that GC ID, and `Comments` records the superseded GC value.
- **`c# both`**: the delta is a different requirement and becomes `NEW` with the next ID.
- **Confirming a `MOVED` entry:** retire the old ID (`## Retired`) and issue a new one.
- **`d <GC-ID> <reason>` on a GC record** (removing it from the document): allowed only when the user asks explicitly. It adds a `remove` op and a `## Retired` row.
- **Setting the type of a `TBD` entry:** issue its target ID and match it (section 3 of `nfr-match.md`).

**After every apply pass:** rebuild `changes.json`, re-render `draft.md` from `base.md`, re-run 6-validate, and echo `draft: +a ~u -r rows, check_draft: ok|<errors>`. `nfr-review.md` logs the pass.

If the user parks, stop there. The next invocation with the same document and runs resumes the review.

## Hand-off

When the review is complete:
1. Run 6-validate one last time. It must pass.
2. Set `active_stage: hand-off` and `active_step: ""`, and log it. The target document is **not** touched, and `finished` is set by `/archy-nfr-apply`.
3. Show the paths of `draft.md`, `nfr-draft-log.md`, `state.yaml`, and the target, with one line of counts: new, updated, moved, retired, still open, and dropped.
4. Suggest what to do next:
   - review `draft.md` against the document (for example `git diff --no-index <target> <draft_dir>/draft.md`)
   - `/archy-nfr-apply`, to move the draft into the target document

## Draft folder

```
ai-workflow/nfr-draft/<draft_id>/
  state.yaml          identity (target + input runs), position, per-run status, state_log
  base.md             GC copy at draft start (or the template without sample rows)
  changes.json        the full change set against base.md (rebuilt, never appended)
  draft.md            base.md + changes.json: the future NFR document
  nfr-draft-log.md    change set, trace, retired IDs, open questions, conflicts, dropped
```
