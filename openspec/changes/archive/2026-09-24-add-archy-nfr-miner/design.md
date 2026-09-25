# Design

## Context

See proposal.md for motivation, and `specs/nfr-miner/spec.md` for behavior.

The current state that shapes this design:

- `archy-init-nfr-taxonomy` (v1.0.0) copies `taxonomy/` into `ai-workflow/nfr-taxonomy/` and prints JSON with `target`. The two templates the miner needs (`nfr-state.yaml`, `nfr-state-log.md`) sit in `taxonomy/` but are untracked, and the version was not bumped for them.
- Existing skills resolve their Python dependencies from the toolkit's `pyproject.toml`. That file is absent once a skill is installed into another project.
- `archy-word-to-md` always splits output per H1 section. It cannot produce one file per document.
- Claude Code session IDs change with every new conversation and after `/clear`. They survive only an explicit `--resume`.

## Goals / Non-Goals

**Goals:**
- Precise, reproducible citations back to a source line or page.
- Resumable at file granularity across conversations and reboots.
- Mining that parallelizes safely across files.
- A review procedure reusable by later NFR skills.

**Non-Goals:**
- OCR, mining images or diagrams, and non-English specific handling.
- Editing any golden-copy NFR document. That belongs to `/archy-nfr-propose`.
- Suggesting NFRs that the sources never mention. That belongs to `/archy-nfr-explore`.

## Decisions

### Skill layout
```
skills/archy-nfr-miner/
  SKILL.md                     orchestration: args, pre-flight, stages 0-2 (main thread)
  references/nfr-mine-file.md  per-file mining brief (subagent or inline)
  references/nfr-review.md     reusable review loop (main thread only)
  scripts/resolve_run.py       path resolution, exclusions, sha256, run matching -> JSON
  scripts/normalize_sources.py docx/pdf -> single .md per source -> JSON
  tests/                       pytest for both scripts + fixtures
```
Deterministic work goes in scripts, and judgment stays in markdown. The subagent brief lives in its own file, so the Agent prompt is just "follow `references/nfr-mine-file.md` for `<source>`, write to `<out>`". The brief is never paraphrased.

### Run identity = resolved file set (not session ID)
`resolve_run.py` normalizes every `--path` (repeatable) to a sorted set of repo-relative paths and hashes each file. It then classifies every existing `state.yaml` under `working_dir_base` as `identical`, `superset`, `subset`, `partial`, or `none`, and reports stale files. The skill only turns that JSON into a question for the user.
- *Alternative, session-keyed folders:* lost on `/clear` or a new conversation, and cannot be shared with explore or propose.
- *Alternative, path-slug keyed:* breaks for masks and lists (`docs/*.md` versus `./docs/*.md`, and list order).

Script contract (sketch):
```json
{"files":[{"path":"docs/a.docx","sha256":"...","ext":".docx"}],
 "excluded":["ai-workflow/nfr-state/..."],
 "runs":[{"run_id":"docs-20260924-1402","match":"identical","stale":["docs/a.docx"],
          "active_stage":"stage-1","active_step":"1-map","finished":false}]}
```

### Stage 1 as map/reduce
```
 0 normalize (main)  -> sources/<rel>.<ext>.md, per-file status
 1 map               -> mined/<rel>.md per file, local ids (L-1, L-2...), no shared writes
                        1 file or small input: inline; else subagents, max 5 parallel
 2 reduce (main)     -> assign NFR-###, dedupe (keep all citations), conflicts
 3 validate (main)   -> checks + auto-fix x2 -> degrade to TO REVIEW
 4 summary (main)    -> one table: a row per file (pre-merge) + TOTAL (merged) row
```
Only the main thread writes `state.yaml` and `nfr-registry-log.md`. This removes write races and ID collisions. Cross-file conflict detection needs the merged view anyway.
- *Alternative, sequential mining in the main thread:* simpler, but slow and heavy on context for large folders. It is still used for single-file input.

### Normalization tools
- **DOCX**: pandoc through `pypandoc-binary`, which bundles pandoc so nothing needs installing system-wide. Command: `-t gfm --wrap=none --track-changes=accept`, with no media extraction. `--wrap=none` puts one paragraph on one line, which keeps line references stable. Tables with merged cells fall back to HTML rows.
  - Rejected: system pandoc (an install burden), `python-docx` (loses footnotes and text boxes), `mammoth` (its markdown output is deprecated), and depending on `archy-word-to-md` (it splits output, and installing it separately couples the skills).
- **PDF**: `pdfplumber` (MIT). For each page it emits `<!-- page N -->`, then the tables as pipe tables (newlines inside cells become `<br>`), then the page text with the table regions cropped out so nothing is mined twice. If no page has text, the file fails with "no extractable text".
  - Rejected: `pymupdf4llm` (AGPL, a licensing risk for a distributed toolkit), `pypdf` (poor layout and tables), and model reading (not deterministic, so line references drift).
- The output path mirrors the source's repo-relative path and adds `.md` (`sources/docs/p/SAD.docx.md`). This avoids collisions and makes the origin obvious.

### Self-contained dependencies (PEP 723)
Each script declares its dependencies inline (`# /// script` block) and runs via `uv run <skill-dir>/scripts/<x>.py`. uv provisions them on first use in any project. `resolve_run.py` needs only the standard library, apart from YAML parsing. It reads `state.yaml` with a tiny subset parser, or declares `pyyaml` inline.
- *Alternative:* add the dependencies to the toolkit's `pyproject.toml`. That only works inside this repository.

### Registry template changes (taxonomy v1.1.0)
- The file is renamed `nfr-state-log.md` → `nfr-registry-log.md`. `state_log` inside `state.yaml` stays as the event trail.
- Registry columns: `NFR ID | NFR Type | NFR Category | Verbatim evidence | Metrics | Source | Interpretation | Confidence | Priority | Status | Comments`. `Comments` was already defined in the taxonomy text but missing from the table.
- IDs use the form `NFR-###`, so they never encode a type and stay truthful when a reviewer retypes an entry.
- The `NFR ID` column in Open Questions references `NFR-###`. A `Default by` column records `SKILL` or `USER`.
- `## Dropped` gains `NFR ID` and `Dropped by` columns. It is the only home for dropped entries.
- The miner always assigns `NFR-###`, including to retyped entries. IDs from a golden copy (for example `QAR-01`) keep their typed form, and a retype regenerates them. That belongs to `/archy-nfr-propose` and is out of scope here.
- The `nfr-state.yaml` template gains `run_id`, `path_args`, `taxonomy_version`, `session_ids`, `active_stage`, and a per-file `{path, sha256, normalized, status}`.

### Confidence
One combined score with anchors at 95/85/70/50/<40, where the presence of a metric is part of the anchor (see the spec). `Confidence` is its own column, so validation is mechanical. Priority is rule-based: it is set only when the source states an impact that matches `nfr-priorities.md`. It has no score of its own and is not required for `Auto`.
- *Alternative, separate classification and priority scores:* rejected to keep the model simple.

### Review loop as a parameterized reference
`references/nfr-review.md` takes the inputs `registry_file`, `state_file`, `scope` (a row selector), `allowed_decisions`, and `stage_label`. It follows Present → Collect (guided, commands, or park) → Apply → Repeat.

- **Present:** one flat overview table of every entry in scope (`NFR ID | Type | Category | Statement | Status | Conf | Prio | Open`), grouped as conflicts, `TBD`, `TO REVIEW`, `Auto`, then Dropped, with one hint line of short commands. Boxed per-group boards were considered and rejected as too complex to scan and to render reliably.
- **Guided:** one entry at a time, as one multi-tab ask: a tab per open question, a tab per conflict, `Priority` if missing, and `Decision` last, followed by submit. An entry is reviewed together with all of its questions, so its answers are applied in one pass. The ask tool allows at most 4 tabs, so the overflow goes into a follow-up ask that keeps `Decision` last. Bulk asks follow for `Auto`, missing priorities, and dropped items. Without an ask tool, it falls back to one entry at a time as text.
- **Commands:** short aliases next to the self-describing long form. A bare number stands for `NFR-###`:
```
 a 3 | a @auto [TYPE] | d 5 <reason> | u 13 | p 1,3,8 High | t 9 <why> | n 11 <text>
 q4=<value> | q4 ok | q4 no | c1 a|b|both | park | done
 long: NFR-003 ok | NFR-005 drop <reason> | Q4 = "<value>" | C1 pick A | NFR-007 cat <name> ...
```
Every apply echoes a diff and appends to `state_log`. Explore and propose will reuse it later, with a different scope.

## Risks / Trade-offs

- [Model-reported confidence is still subjective] → Anchors tie the scores to observable features (explicit statement, metric present, vocabulary match), and validation re-checks `Auto` against the completeness rules.
- [Line references break if a converted file is regenerated with different tool versions] → Conversion is skipped while the source hash is unchanged. A re-mine re-anchors IDs by verbatim evidence.
- [pdfplumber reads complex multi-column layouts in the wrong order] → Verbatim evidence is still exact text. The reviewer sees the citation, and the limitation is documented.
- [Dedupe across files could merge requirements that are genuinely distinct] → Merge only identical type, category, and meaning. When in doubt, keep both entries and record a conflict or open question, and let the reviewer decide.
- [The first `uv run` needs network access to fetch wheels] → Documented in SKILL.md. The failure message tells the user to run it once while online.
- [The taxonomy bump overwrites local tailoring of the templates] → This is existing init behavior. It is called out in the init result as overwritten files.

## Migration Plan

1. Rename the template and update it, and bump `archy-init-nfr-taxonomy` to `1.1.0`. Projects on 1.0.0 get the new files on their next init run, which the miner triggers in pre-flight.
2. Add the new skill. There are no existing runs to migrate.
3. Rollback: revert the skill folder and the taxonomy commit. Run folders are plain files and can be deleted.
