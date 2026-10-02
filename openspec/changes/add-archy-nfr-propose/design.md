# Design

## Context

See `proposal.md` for motivation and `specs/nfr-propose/spec.md` for behavior.

The current state that shapes this design:

- **Miner runs.** `archy-nfr-miner` leaves `ai-workflow/nfr-state/<run>/` with `state.yaml` and `nfr-registry-log.md`.
  - Registry IDs are `NFR-###`, unique only within a run.
  - Review results live only in the registry: `Confirmed` entries, `Closed` questions, and resolved conflicts. `mined/` is pre-review scratch output from the map step.
- **Shared review loop.** `archy-nfr-miner/references/nfr-review.md` is already written as a reusable procedure with `scope`, `allowed_decisions`, and `stage_label` inputs. Its command grammar assumes `NFR-###` IDs and accepts the number alone.
- **Document template.** `taxonomy/nfr-req-tmpl.md` (untracked) is the target document shape: four H2 sections, each with intro text and one table. Today:
  - the BD table has no `ID` column
  - the ASM and CSTR tables have no separator row
  - the QAR sample uses the non-catalog name `Performance`
  - the section is spelled `Constrains`
- **Taxonomy shipping.** `init_taxonomy.py` copies every non-hidden file in `taxonomy/`. A new template only needs a version bump (currently `1.1.1`) to ship.
- **Env var.** `.env.example` already defines `NFR_PATH`. Nothing loads `.env` into the process environment automatically: the sibling skills `archy-md-to-word` and `archy-summarize-meeting-decisions` read the repo-root `.env` themselves.

## Goals / Non-Goals

**Goals:**
- GC is authoritative: its IDs, text, and layout survive unless a reviewed delta changes a specific row.
- The draft is exactly what `/archy-nfr-apply` will write, so apply can be a copy plus a drift check.
- Deterministic parsing, patching, and preservation checking. The model decides only matches and judgment calls.
- Resumable at stage, step, and input-run granularity, the same as the miner.

**Non-Goals:**
- Writing the GC file, or detecting GC drift at apply time. Both belong to `/archy-nfr-apply`.
- Re-mining sources, or reading `mined/` and `sources/`.
- Parsing GC layouts other than the template's section-and-table structure. The skill stops and asks instead.
- Handling several target documents in one draft. `target_sad_docs` is a list, but the skill uses entry 0 only.

## Decisions

### Skill layout
```
skills/archy-nfr-propose/
  SKILL.md                  orchestration: params, pre-flight, stages 0-2, hand-off (main thread)
  references/nfr-match.md   judgment brief: dedupe + delta-vs-GC matching, dispositions, anchors
  scripts/resolve_draft.py  GC path, run discovery, draft identity/resume, stale detection -> JSON
  scripts/gc_tables.py      parse GC/template -> records JSON; patch managed rows from a change set
  scripts/check_draft.py    preservation diff + table/ID/section checks -> JSON findings
  tests/                    pytest for all three scripts + fixtures
```
The review loop is reused from `../archy-nfr-miner/references/nfr-review.md`, so propose depends on the miner being installed next to it. This is the same arrangement as the miner's dependency on the taxonomy skill. The scripts use PEP 723 inline dependencies and run with `uv run`, as the miner's scripts do.
- *Alternative, copying `nfr-review.md` into propose:* two copies would drift apart. It was rejected.

### Pipeline
```
PRE-FLIGHT  init_taxonomy.py -> load 7 files            (result buffered)
STAGE 0     resolve_draft.py:
              GC      = nfr_doc | $NFR_PATH | .env NFR_PATH | ask (no default)
                        relative -> repo root              -> exists? gc : template
              runs    = runs | scan nfr-state/*/state.yaml -> multi-select (latest marked)
                        warn: no state.yaml / not finished -> include anyway?
              draft   = match (target, run set) -> resume | fresh | new
            -> state.yaml (+ buffered pre-flight log entry)
STAGE 1     1-parse   gc_tables.py parse GC (or template) -> gc_records.json
            1-carry   load registries: Confirmed/Auto/TBD/TO REVIEW + open Q/C (per run -> merged)
            2-dedupe  cross-run match (nfr-match.md anchors 95/85/70)
            3-match   delta vs GC -> SAME/UPDATE/CONFLICT/MOVED/NEW
            4-ids     next <TYPE>-### above max(GC, retired in prior logs)
            5-write   nfr-draft-log.md (change set, trace, Q, C, dropped)
                      gc_tables.py patch base -> draft.md (renderable rows only)
            6-validate check_draft.py + model checks, fix x2 -> degrade / stop
            7-summary one table per run + total
STAGE 2     nfr-review.md (id_format=typed, scope=change set)
              each apply pass -> gc_tables.py patch -> check_draft.py -> state_log
HAND-OFF    active_stage: hand-off -> suggest /archy-nfr-apply
```
Deduplication and matching run in the main thread and not in subagents. The inputs are compact registry rows rather than documents, and matching needs every run and GC at once. The miner parallelized only because per-file mining is independent.

### Pre-flight state before a state file exists
The draft folder is only known after Stage 0, so pre-flight cannot write `state.yaml` directly. The skill keeps the pre-flight result in memory and makes it the first `state_log` entry once Stage 0 creates or resumes the folder. A hard stop in pre-flight writes nothing, which matches the miner.

### One state schema (`nfr-state.yaml`), extended
```yaml
active_skill: archy-nfr-propose
active_stage: stage-0|stage-1|stage-2|hand-off|finished
files_4_review:              # miner: source docs | propose: input run registries
  - path: ai-workflow/nfr-state/<run>/nfr-registry-log.md
    sha256: ...
    normalized: ""           # miner-only
    status: pending|merged|skipped|stale     # miner adds mined|failed
    reason: ""               # e.g. "run not finished (review-parked), included by user"
    images: 0                # miner-only
target_sad_docs:             # optional; propose only
  - path: <repo-relative nfr_doc>
    sha256: ...              # at draft start; resume compares, apply will too
    exists: true
    draft: draft.md
    format_source: gc|template
```
`finished` is left for `/archy-nfr-apply` to set after it writes the target.
- *Alternative, a separate `nfr-draft-state.yaml`:* two header formats would need two sets of logging rules. Future skills (explore, apply) would have to read both. It was rejected.

### GC path resolution
- **Order.** `--nfr-doc`, then the `NFR_PATH` process env var, then `NFR_PATH` from the repo-root `.env`. There is no built-in default. With none set, the resolver returns `needs_path: true`, and the skill asks without suggesting a path.
- **Repo root.** `--root`, which defaults to the git top level (`git rev-parse --show-toplevel`), else the working directory. Relative paths from every source resolve against it, never against the skill folder, and are recorded repo-relative.
- **Source.** The resolver reports `source: param|env|.env`, so the user sees where the path came from.
- **No example paths.** `SKILL.md` and the taxonomy templates show `<nfr_doc>` placeholders, not concrete paths, so the model has no path to fall back on when `needs_path` is set.

### Draft identity
A draft is identified by `(target path, sorted set of input registry paths)`. `resolve_draft.py` classifies existing drafts under `ai-workflow/nfr-draft/` the same way `resolve_run.py` does (`identical`, `superset`, `subset`, `partial`). For each draft it reports stale inputs (the registry sha256 changed) and GC drift (the target sha256 changed). A changed GC offers a rebuild, because patching a draft onto a moved base cannot be trusted.

### GC parsing and patching (`gc_tables.py`)
- **Section location.** Sections are found by exact H2 text. The table is the first markdown table after the heading and before the next H2.
- **Record identity.** The key column is `ID`. Every other column is looked up by header name, so column order and extra custom columns are tolerated.
- **Column mapping.** Header names map to registry fields through a fixed table:

  | Registry field | BD | QAR | ASM | CSTR |
  | --- | --- | --- | --- | --- |
  | statement | Business Goal | Requirement | Assumption | Constraint |
  | category | Business Driver | Quality Attribute | - | - |
  | Metrics | Metric / Criteria | Metric / Criteria | - | - |
  | Priority | Priority | Priority | Impact | Impact |
  | extra | - | - | Risk | - |

  `Risk` comes from the entry's interpretation, or from its answered question about what breaks if the assumption is false.
- **`patch`.** Takes a change set of `{op: add|update|remove, section, id, cells, after_id?}` and rewrites only the targeted rows. It edits the file by line ranges and never reformats it, so that untouched bytes stay identical.
- **No GC.** The base is `nfr-req-tmpl.md` with its sample rows removed.
- **Rendering.** The model builds the change set. The script owns all text surgery.
- *Alternative, the model edits `draft.md` directly:* it would be cheaper to build, but whitespace drift and accidental rewrites are likely, and there would be no clear point to validate. It was rejected, since preservation is the core promise.

### Matching brief (`references/nfr-match.md`)
The brief holds the judgment rules, so that `SKILL.md` stays orchestration only:
- the match-confidence anchors (95/85/70/<70), shared by cross-run dedupe and delta-vs-GC matching
- the disposition rules (additive vs. value-changing, and when a type change counts as `MOVED`)
- the conservative default: when unsure between `UPDATE` and `CONFLICT`, choose `CONFLICT`; when unsure between a match and `NEW`, choose `NEW` with a "possible duplicate of <ID>" question

### Draft log (`taxonomy/nfr-draft-log.md`)
The draft log follows the registry format. Rows are keyed by **target ID**, with an extra `Disposition` column:
```
## Change Set    | Target ID | Disposition | NFR Type | NFR Category | Statement | Metrics | Priority | Origin | Confidence | Status | Comments |
## Trace         | Origin (run/NFR-###) | Match | Disposition | Target ID | Note |
## Retired       | ID | Replaced by | Reason | Date |
## Open Questions / ## Conflicts / ## Dropped   (registry format; conflict A/B = GC vs delta or run vs run)
```
`## Retired` is how IDs stay unique across drafts. Step 4 (`4-ids`) scans prior draft logs for the same target and never issues an ID listed there.

### Review reuse with typed IDs
`nfr-review.md` gains an `id_format` input:
- `nfr` (the default, used by the miner): the current behavior, including number-only shorthand.
- `typed`: IDs are `<TYPE>-###`, matched case-insensitively (`qar-13` = `QAR-013`), and number-only shorthand is rejected. A bare number would be ambiguous across types.

Propose passes these inputs: `registry_file` = the draft log, `scope` = the change set without `SAME`, `stage_label` = `stage-2-review`, and `id_format` = `typed`. Conflict commands keep `c1 a|b|both`, where A is always GC (or the earlier run) and B the delta. After each apply pass, the propose `SKILL.md` runs patch and check. `nfr-review.md` stays unaware of drafts.

### Status mapping into the draft
Rendered: `Confirmed`, `Auto`, and `TBD` with disposition `NEW`, `UPDATE`, or confirmed `MOVED`. Never rendered: `TO REVIEW`, `CONFLICT` before resolution, `SAME`, and dropped rows. The registry template's rule "open questions never enter the draft" applies unchanged.

## Risks / Trade-offs

- **[Risk] A hand-edited GC breaks the table parser** (merged cells, HTML tables, a renamed heading). → The skill stops with a precise report (the Unparseable golden copy requirement). The SAD rules already prefer markdown tables. The HTML-table case is out of scope.
- **[Risk] Fuzzy matching against GC misses a match, which creates a duplicate `NEW` row.** → Conservative defaults, plus the "possible duplicate of <ID>" question at match 70. `NEW` rows go through review before hand-off.
- **[Risk] A retired ID is reused after an old draft folder is deleted.** → Retired IDs are also kept in the current log. As a known limit, IDs retired only in deleted drafts cannot be recovered. `/archy-nfr-apply` could later record retirements in GC.
- **[Trade-off] Propose depends on the miner's `references/nfr-review.md` being installed alongside it.** → Pre-flight checks the path and stops with an install hint when it is missing.
- **[Trade-off] Everything runs in the main thread.** → Registries are small compared with source documents. Revisit if drafts span dozens of runs.
- **[Risk] A GC with custom columns gets new rows with empty custom cells.** → This is documented behavior. Empty cells are visible in review.

## Migration Plan

1. Fix `nfr-req-tmpl.md`, add `nfr-draft-log.md`, extend `nfr-state.yaml`, and bump the taxonomy to `1.2.0`. Initialized projects receive the change on their next init, which reports `updated`.
2. Existing miner runs need no migration. Their `state.yaml` is valid under the extended schema, since `target_sad_docs` is optional.
3. Existing GC documents made before this change may lack the BD `ID` column. The parser reports the missing column, and the user adds it by hand. The skill does not auto-migrate GC.

Rollback: remove the skill folder and revert the taxonomy version. The miner is unaffected.

## Open Questions

- Should `/archy-nfr-apply` also write `## Retired` IDs into GC, for example as an appendix, so that retirement survives deleted drafts? This is deferred to the apply change.
