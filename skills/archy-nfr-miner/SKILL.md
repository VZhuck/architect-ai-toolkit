---
name: archy-nfr-miner
description: "Mine non-functional requirements (quality attribute requirements, business drivers, constraints, assumptions) from .md/.mdx/.docx/.pdf sources into a run-scoped NFR registry against the project's closed NFR taxonomy, then walk the user through reviewing it. Resumable across conversations."
argument-hint: "path (dir, file, glob mask, or list like \"fileA.md\", \"fileB.pdf\"), working_dir_base (optional, default 'ai-workflow/nfr-state'), run (optional run folder name)"
---

# NFR Miner

Mine NFRs from source documents into a registry (`nfr-registry-log.md`) that uses only the project's closed taxonomy. Then review the registry with the user. Work is kept in a **run folder**. A run is identified by the set of files it covers, so invoking the skill again with the same input, in any conversation, resumes the same run.

```
 pre-flight -> Stage 0 restore -> Stage 1 mine -> Stage 2 review -> hand-off
 (taxonomy)    (which run/step)   (normalize, map,  (main thread)
                                   reduce, validate)
```

## Parameters

- **path** (required): a directory (scanned recursively), a file, a glob mask, or a list such as `"docs/SAD.docx", "specs/*.md"`. **Never guess it.** If it is missing, go to Stage 0's no-path branch.
- **working_dir_base** (optional): where run folders live. Default: `ai-workflow/nfr-state`.
- **run** (optional): an explicit run folder name, mostly for tests and evals.

Split `path` into separate values: on commas outside quotes, or on the quote pairs. Strip the quotes. Each value becomes one `--path` for the resolver.

**Paths used below:**
- `<skill-dir>`: the folder containing this `SKILL.md`. In this repository that is `skills/archy-nfr-miner`; once installed it is usually `.claude/skills/archy-nfr-miner`.
- The taxonomy skill is its sibling: `<skill-dir>/../archy-init-nfr-taxonomy`.

The scripts declare their own dependencies (PEP 723). Run them with `uv run <script>`, not `uv run python <script>`. The first run needs network access to fetch the dependencies.

## Pre-flight (before anything else)

1. **Taxonomy.** Run `uv run python <skill-dir>/../archy-init-nfr-taxonomy/scripts/init_taxonomy.py`. Its JSON `target` is `taxonomy_dir`. If files were `overwritten`, mention it: local tailoring was replaced. If the init skill is not installed, stop and say so.
2. **Load the taxonomy.** Read these five files from `taxonomy_dir`:
   - `nfr-priorities.md`
   - `business-drivers.md`
   - `quality-attributes.md`
   - `nfr-state.yaml`
   - `nfr-registry-log.md`

   **Hard stop if `taxonomy_dir` or any of these files is missing.** Name the missing file, ask where to find it, and write nothing. A file deleted after init is not restored while the version marker matches: point out that re-running `archy-init-nfr-taxonomy` with `force` restores the shipped copy. Never fall back to ISO 25010, generic "-ilities", or vocabulary mined from the sources.
3. **State the resolved paths:** `taxonomy_dir` and its version, the loaded files, `working_dir_base`, and (after Stage 0) the run folder with the files it maintains.

## Stage 0: Restore or create the run

1. **Resolve** by running
   `uv run <skill-dir>/scripts/resolve_run.py --path <p1> [--path <p2> ...] --working-dir-base <working_dir_base> --taxonomy-dir <taxonomy_dir> [--run <run>]`.

   It prints `files` (path, sha256, ext), `excluded`, `unsupported`, `unmatched`, `suggested_run_id`, `run_exists`, and `runs`: the existing runs that overlap, best match first.
   - Exit code 2 means no supported files. Stop, and show `unmatched`, `unsupported`, and `excluded`.
   - Mention any `unmatched` values, even when other files resolved.
2. **No path given:** run it with `--list-runs` only. If there are unfinished runs, list them (run ID, path arguments, stage and step, file statuses) and ask which one to continue, or ask for a path. If there are none, ask for the path.
3. **Match.** Act on the first entry of `runs`:

   | `match` | Ask |
   | --- | --- |
   | `identical` | "Resume run X at <stage/step> (<k>/<n> files mined)?" Options: **resume** or **fresh**. If `finished`: **re-open review** or **fresh** |
   | `superset` | "Run X covers <n> of these; add <added> to it?" Options: **add** or **new run** |
   | `subset` | "Run X already includes these files." Options: **resume X** or **new run** for just these |
   | `partial` | List the overlapping runs. Default: **new run** |
   | no runs | New run, without asking |

   If `stale` is non-empty in the run you resume, say which sources changed and offer to re-mine just those files. Set their status to `stale`.

   **Fresh** means renaming the old folder to `<run_id>-archived-<yyyymmdd-hhmm>`, then creating a new run.
4. **Create a run.** The run folder is `<working_dir_base>/<suggested_run_id>`. If `run_exists` is true and that folder is not the run you matched (an explicit `run` reused for other files), do not write into it: ask for another `run` name, or archive it as **fresh** does.
   - Copy `taxonomy_dir/nfr-registry-log.md` into it unchanged, keeping the template's sample rows until the reduce step replaces them.
   - Create `state.yaml` from `taxonomy_dir/nfr-state.yaml`, filling it with real values:

     | Field | Value |
     | --- | --- |
     | `run_id` | the run folder name |
     | `path_args` | the path values as the user typed them |
     | `taxonomy_dir` | resolved `taxonomy_dir`, root-relative (init prints it absolute) |
     | `taxonomy_version` | the version reported by init |
     | `session_ids` | `[${CLAUDE_SESSION_ID}]` |
     | `active_skill` | `archy-nfr-miner` |
     | `active_stage` / `active_step` | `stage-1` / `0-normalize` |
     | `files_4_review` | one entry per resolved file: `path`, `sha256`, `normalized: ""`, `status: pending`, `reason: ""`, `images: 0` |
     | `state_log` | a `started` entry |
     | `update_on` | now, with timezone |
   If `${CLAUDE_SESSION_ID}` appears literally (the host does not substitute it), record `unknown-<yyyymmdd-hhmm>` instead.
5. **Resume a run.** Append `${CLAUDE_SESSION_ID}` to `session_ids` if it is not already there. For **add**, append the new files as `pending`. Continue at `active_stage` / `active_step`. A `review-parked` step means going straight to Stage 2.

**State discipline.** At every step boundary below, update `active_step` and `update_on`, set the per-file statuses, and append a `state_log` entry (`date`, `skill`, `gate`, `change`, `status`). Only the main thread writes `state.yaml` and `nfr-registry-log.md`.

## Stage 1: Mine

The goal is to catch what the sources say, without proposing anything and without asking the user. When unsure, make the conservative choice, log it, and move on.

### 1.0 Normalize

Run `uv run <skill-dir>/scripts/normalize_sources.py --run-dir <run_dir> --file <path> ...` for every file with status `pending` or `stale`. For each result:
- `converted` / `unchanged` / `in-place`: store `normalized` (empty for `in-place`), `sha256`, and `images`. The file stays `pending`.
- `failed`: set status `failed` and store `reason` and `images`. The file is not mined, and the run continues.

Images and diagrams are never mined; `images` is their per-file count, kept in `state.yaml` and logged in this step's `state_log` entry (for example `images: SAD.docx 2, scan.pdf 1`).

### 1.1 Map: mine each file

Mine every `pending` or `stale` file with [references/nfr-mine-file.md](references/nfr-mine-file.md). Pass it:
- `source`: the file's path
- `read_from`: `<run_dir>/<normalized>`, or `source` itself for `.md`/`.mdx`
- `taxonomy_dir`
- `output`: `<run_dir>/mined/<source>.md`

- **One file:** mine it inline in this conversation, following the brief.
- **Several files:** start one subagent per file, **at most 5 at a time**. The prompt must be exactly: "Read and follow `<skill-dir>/references/nfr-mine-file.md` with source=…, read_from=…, taxonomy_dir=…, output=…". Do not paraphrase the brief.

When a file's output exists and its `## Summary` line is present, set the file to `mined`. If a subagent fails or its output is malformed, retry it once inline; if that fails too, set the file to `failed`.

### 1.2 Reduce: merge into the registry

Read every `mined/*.md` for this run, in `files_4_review` order.
1. **Dedupe** (before any ID is assigned). Merge candidates that state the same requirement (same type, same category, same meaning, same or no metric) into one candidate. Keep the first one's fields, join the `Source` citations with `; `, keep the higher confidence, and note "merged: <file> L-k" in `Interpretation`. Merged duplicates get no ID and no `## Dropped` row; they are counted as "merged duplicates" in the summary. When in doubt, keep both.
2. **Assign IDs.** Continue from the highest `NFR-###` already in `nfr-registry-log.md` (registry and `## Dropped`), or start at `NFR-001`. Give each remaining candidate and each dropped item, in file order then local order, the next ID. Keep a local-to-final map for each file.
   - When **re-mining a stale file**, an old entry citing that file keeps its ID if its verbatim evidence is still present in the new output. Update its line reference.
   - An old entry whose evidence is gone becomes `TO REVIEW`, with an open question: "Evidence no longer in <source>; keep, update, or drop?"
3. **Conflicts.** For the same type and category, where two sources give different targets for the same thing, add a `## Conflicts` row (`C1`, `C2`, ...) with both values and sources. Keep both entries. Set both to `TO REVIEW`. Never choose between them silently. Add one open question per conflict, "C1: which target applies, <value A> or <value B>?", with both IDs in `NFR ID` (`NFR-004, NFR-009`), so that every `TO REVIEW` entry has a question. Resolving the conflict closes that question.
4. **Write** `nfr-registry-log.md`:
   - The registry rows get the final IDs and an empty `Comments`.
   - Open questions are renumbered `Q1`, `Q2`, ... with the final `NFR ID`, status `TO REVIEW`, and `Default by` carried over.
   - Dropped rows get the final ID, and `Dropped by` = `SKILL`.
   - Remove the template's sample rows.

### 1.3 Validate

Check the registry, fix what fails, and re-check, **at most twice**:
1. Every entry has a `Confidence` and an `Interpretation`.
2. Every `NFR ID` is unique, across the registry and `## Dropped`.
3. Every `Auto` entry has confidence ≥ 85 and is complete for its type (see the brief). Priority is not required.
4. Every status is `Auto`, `TO REVIEW`, or `Drop`; `Confirmed` and `TBD` are allowed only if they came from a review.
5. Every `TO REVIEW` entry has at least one open question.
6. Every dropped ID appears only in `## Dropped`, never in the registry.
7. Every `Source` line reference points to a line that contains the verbatim evidence. Open the file and check.
8. `QAR` and `BD` categories exist verbatim in the catalogs.

An entry that still fails after two attempts becomes `TO REVIEW`, gets an open question naming the failed check, and is logged with `status: fail`.

### 1.4 Summary

Show **one table**: a row per source file with counts taken from its `mined/*.md` **before** merging, then a `TOTAL (merged)` row counted from `nfr-registry-log.md` **after** merging.

```
| File                      | BD | QAR | CSTR | ASM | TBD | By status                           | Total |
| ------------------------- | -: | --: | ---: | --: | --: | ----------------------------------- | ----: |
| docs/payments/SAD.docx    |  1 |   5 |    0 |   1 |   0 | Auto: 4, TO REVIEW: 3, Dropped: 1   |     8 |
| docs/payments/nfr.md      |  2 |   8 |    0 |   0 |   1 | Auto: 6, TO REVIEW: 5, Dropped: 0   |    11 |
| docs/scan.pdf             |  - |   - |    - |   - |   - | failed: no extractable text         |     - |
| **TOTAL (merged)**        |  3 |  12 |    0 |   1 |   1 | Auto: 9, TO REVIEW: 8, Dropped: 1   |    18 |
```

- Type columns count registry candidates only. Dropped items have no type, so they appear only in `By status` and `Total`.
- `Total` = `Auto` + `TO REVIEW` + `Dropped`.
- A failed file is one row with `failed: <reason>` and `-` in every count.

Then one line:

```
mined 19 -> merged duplicates 1 -> registry 17 + dropped 1 | open questions 9 | conflicts 1 | without priority 12 | files failed 1 | images skipped 4
```

`images skipped` is the sum of `images` over `files_4_review`, including failed files. The `TOTAL (merged)` total must equal mined minus merged duplicates. If it does not, recount before moving on.

Set `active_stage: stage-2` and `active_step: review`.

## Stage 2: Review

Run [references/nfr-review.md](references/nfr-review.md) **in this conversation**, with:
- `registry_file` = `<run_dir>/nfr-registry-log.md`
- `state_file` = `<run_dir>/state.yaml`
- `taxonomy_dir`
- `scope` = the whole registry
- `allowed_decisions` = all
- `stage_label` = `stage-2-review`

If the user parks, stop there. The next invocation with the same path resumes the review.

## Hand-off

When the review is complete:
1. Set `active_stage: finished` and `active_step: ""`, and log it.
2. Show the paths of `state.yaml` and `nfr-registry-log.md`, with a one-line count: confirmed, TBD, still open, and dropped.
3. Suggest what to do next:
   - review the state and registry files
   - `/archy-nfr-explore`, to challenge the registry and find important NFRs that are missing
   - `/archy-nfr-propose`, to merge with the golden copy and draft the NFR document

## Run folder

```
<working_dir_base>/<run_id>/
  state.yaml               run identity, position, per-file status, state_log
  nfr-registry-log.md      registry, open questions, conflicts, dropped
  sources/<path>.md        normalized .docx/.pdf (one file each)
  mined/<path>.md          per-file mining output (map step)
```
