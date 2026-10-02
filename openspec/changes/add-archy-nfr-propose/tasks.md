# Tasks

## 1. Taxonomy templates (archy-init-nfr-taxonomy 1.2.0)

- [x] 1.1 Fix `taxonomy/nfr-req-tmpl.md`:
  - add an `ID` column with `BD-001` to Business Drivers
  - add separator rows to the Assumptions and Constraints tables
  - use `Performance & Scalability` in the QAR sample
  - rename `Constrains`/`Constrain` to `Constraints`/`Constraint`
  - give the BD sample a real goal
  - fix the intro typos ("hat", "rechnology stake", "negoatiable", "claude native")

  Verify by reading the file against the nfr-taxonomy-init delta, "Taxonomy ships NFR workflow templates"
- [x] 1.2 Add `taxonomy/nfr-draft-log.md` with the sections Change Set, Trace, Retired, Open Questions, Conflicts, and Dropped, following design.md "Draft log". Verify that every table has a header and a separator row
- [x] 1.3 Extend `taxonomy/nfr-state.yaml`:
  - an optional `target_sad_docs` (`path`, `sha256`, `exists`, `draft`, `format_source`)
  - the status `merged`
  - the stage `hand-off`
  - comments describing `files_4_review` for miner vs. propose

  Verify that it parses with `uv run python -c "import yaml,sys;yaml.safe_load(open(sys.argv[1]))" <file>`
- [x] 1.4 Bump `metadata.version` in `skills/archy-init-nfr-taxonomy/SKILL.md` to `1.2.0`, and track `nfr-req-tmpl.md` in git. Verify with `git status` and `uv run pytest skills/archy-init-nfr-taxonomy/tests`
- [x] 1.5 Add tests: the materialized taxonomy contains `nfr-req-tmpl.md` and `nfr-draft-log.md`; `nfr-req-tmpl.md` has the four H2 sections, each with a table whose first column is `ID` and which has the specified columns; the QAR sample category exists verbatim in `quality-attributes.md`. Verify that the tests pass

## 2. Shared review loop

- [x] 2.1 Add the `id_format` input (`nfr` default, `typed`) to `skills/archy-nfr-miner/references/nfr-review.md`. With `typed`, IDs are `<TYPE>-###`, matched case-insensitively, and number-only shorthand is rejected. Verify that the miner's `SKILL.md` Stage 2 inputs still read correctly (`id_format` omitted means `nfr`) and that the worked examples are unchanged for the miner

## 3. Skill scaffold

- [x] 3.1 Create `skills/archy-nfr-propose/` with a `SKILL.md` frontmatter: `name: archy-nfr-propose`, a description, and an `argument-hint` for `nfr_doc`, `runs`, and `draft`. Verify that `uv run pytest tests/` (naming conventions) passes
- [x] 3.2 Create `references/`, `scripts/`, and `tests/`, and verify the tree matches design.md "Skill layout"

## 4. resolve_draft.py

- [x] 4.1 Implement GC resolution (`--nfr-doc`, else `NFR_PATH`, else `needs_path: true`) with `exists` and `sha256`, and verify with tests for the param, the env var, a missing file, and no path at all
- [x] 4.2 Implement run discovery over `ai-workflow/nfr-state/*/`:
  - for each run: `run_id`, registry path and sha256, `active_stage`/`active_step`, `update_on`, row counts by status, and `latest: true` on the most recent
  - flag `no_state` and `not_finished`

  Verify with fixture runs covering finished, parked, no-state, and several runs (latest flag)
- [x] 4.3 Implement draft matching over `ai-workflow/nfr-draft/*/state.yaml` by `(target path, input set)`: `identical`, `superset`, `subset`, `partial`, `none`, stale inputs, and GC drift. Verify with fixtures for each class, a changed registry sha, and a changed GC sha
- [x] 4.4 Add PEP 723 metadata and JSON output (exit code 2 when there are no runs), and verify with `uv run skills/archy-nfr-propose/scripts/resolve_draft.py --list` on a fixture tree

## 5. gc_tables.py

- [x] 5.1 Implement `parse` to produce, per section, the table's line range, its headers, and records keyed by `ID`, with fields mapped per design.md "GC parsing and patching". Verify with tests on the fixed template, a GC with a custom column and custom text, and a GC with shuffled columns
- [x] 5.2 Implement parse errors: a missing section, a missing table, a missing `ID` column, a duplicate ID, and a row with the wrong column count. Verify that each reports the section and line and exits non-zero
- [x] 5.3 Implement `patch` from a change-set JSON (`add`/`update`/`remove`, `after_id` for QAR category placement), rewriting only the targeted line ranges. Verify byte-identity of untouched lines with a test on a GC containing CRLF-free custom text, trailing spaces, and an extra H2
- [x] 5.4 Implement the template base (`--from-template`, which removes the sample rows), and verify that the output has four empty tables and unchanged intro text

## 6. check_draft.py

- [x] 6.1 Implement the preservation diff (base vs. draft): every changed line must be a managed-table row claimed by the change set. Verify with tests: a legitimate add and update pass, while a changed intro word and a changed unclaimed row fail with line numbers
- [x] 6.2 Implement the structural checks: table validity and column counts, IDs unique and matching `<TYPE>-###` in the right section, catalog-verbatim categories (read from `--taxonomy-dir`), and no `TO REVIEW` or dropped target ID rendered. Verify with one failing fixture per check

## 7. Matching brief (references/nfr-match.md)

- [x] 7.1 Write the brief:
  - the match-confidence anchors (95/85/70/<70)
  - the cross-run dedupe rules (auto-merge at ≥85 with no metric contradiction, a question at 70, a conflict on differing metrics)
  - the delta-vs-GC dispositions (`SAME`, additive `UPDATE`, value-changing `CONFLICT`, `MOVED`, `NEW`)
  - the conservative defaults
  - the ID rules (category change keeps the ID; a type change retires it)
  - the column mapping, including ASM `Risk`

  Verify each spec scenario under "Cross-run deduplication", "Delta matching against the golden copy", and "Identifier issuance" against the brief's rules

## 8. SKILL.md orchestration

- [x] 8.1 Pre-flight: init taxonomy, load the 7 files, check that `../archy-nfr-miner/references/nfr-review.md` exists, hard-stop on anything missing, and buffer the result for the first `state_log` entry. Verify against the spec's "Taxonomy pre-flight" scenarios
- [x] 8.2 Stage 0:
  - GC resolution and the ask when there is no path; the template-bootstrap notice
  - the run multi-select (latest marked, numbered fallback when there are more than 4)
  - warnings for unfinished runs or runs without `state.yaml`
  - draft resume, fresh, or new (with archiving); stale-input and GC-drift offers
  - creating the draft folder (`state.yaml`, `nfr-draft-log.md`)

  Verify against the spec's "Golden copy resolution", "Input run selection", and "Draft folder and resume" scenarios
- [x] 8.3 Stage 1, steps 1-parse through 5-write:
  - carry-over rules (no closed questions or dropped rows)
  - dedupe and matching via `nfr-match.md`
  - ID issuance (scanning prior `## Retired` for the same target)
  - writing the log and patching `draft.md` via `gc_tables.py`
  - per-run `merged` status and `state_log` entries at each step

  Verify by reading it against the spec's "Delta carry-over", "Delta matching", "Identifier issuance", and "Format-preserving draft"
- [x] 8.4 Stage 1, 6-validate and 7-summary: run `check_draft.py` plus the model checks, fix at most twice, degrade to `TO REVIEW` or stop on an unattributable preservation failure, then show the summary table per run with a total. Verify against the spec's "Draft validation" and "Stage 1 summary"
- [x] 8.5 Stage 2: call `nfr-review.md` with the draft-log inputs and `id_format=typed`; handle the conflict A/B semantics (GC vs. delta); after each apply pass, run patch and check and log it; park and resume. Verify against the spec's "Review and draft sync" scenarios
- [x] 8.6 Hand-off: set `active_stage: hand-off`, show the paths and the one-line counts, suggest `/archy-nfr-apply`, and never write the target. Verify against the spec's "Hand-off" scenario

## 9. Test data and end-to-end check

- [x] 9.1 Add `test-data/nfr-propose/`:
  - a GC fixture: `08.Non-Functional-Requirements.md` in template shape, with custom intro text and a custom column
  - two finished miner run folders whose registries cover `SAME`, `UPDATE`, `CONFLICT` vs. GC, a cross-run duplicate, a cross-run conflict, a `NEW` QAR, and a parked run

  Verify that `resolve_draft.py` lists them correctly
- [x] 9.2 Add `test-data/nfr-propose-EXPECTED.md` describing the expected dispositions, IDs, conflicts, and draft diff, and verify it against the spec scenarios
- [x] 9.3 Run the skill end to end on the fixtures with a local install (`.claude/skills/`) through Stage 1 and a short review, and verify:
  - `check_draft.py` passes
  - the GC fixture is unchanged
  - `state.yaml` has a `state_log` entry at every stage and step boundary
  - the result matches `nfr-propose-EXPECTED.md`
- [x] 9.4 Run `uv run pytest` over `tests/`, `skills/archy-init-nfr-taxonomy/tests`, `skills/archy-nfr-miner/tests`, and `skills/archy-nfr-propose/tests`, and verify that everything passes

## 10. GC path resolution

- [x] 10.1 `resolve_draft.py`: add the repo-root `.env` fallback for `NFR_PATH`, default `--root` to the git top level (else the working directory), resolve relative paths against it, and report `source: param|env|.env`. Verify with tests for param over env, env over `.env`, the `.env` fallback, running from a subfolder or the skill folder, and no path at all
- [x] 10.2 `SKILL.md`: document the lookup order and repo-root relativity; on `needs_path`, ask without suggesting a path and mention setting `NFR_PATH` in `.env`. Verify that it contains no concrete NFR document path
- [x] 10.3 `skills/archy-init-nfr-taxonomy/taxonomy/nfr-state.yaml`: replace the concrete path in the `target_sad_docs` comment with `<nfr_doc>`
- [x] 10.4 Run `uv run pytest` over `tests/` and the three NFR skills' tests, run `resolve_draft.py` from a subfolder working directory with `NFR_PATH` set only in `.env`, and verify it resolves the repo-relative target
