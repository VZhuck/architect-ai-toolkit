# Tasks

## 1. Taxonomy templates (archy-init-nfr-taxonomy 1.1.0)

- [x] 1.1 Rename `taxonomy/nfr-state-log.md` to `taxonomy/nfr-registry-log.md`, and verify with `git status` that the old name is gone and the new file is tracked
- [x] 1.2 Update the registry template: `NFR-###` IDs in the taxonomy text and sample rows; the columns `Metrics`, `Confidence`, and `Comments`; `NFR ID` and `Default by` in Open Questions; `NFR ID` and `Dropped by` in `## Dropped`; and the note that `## Dropped` is the only home for dropped entries. Verify by reading the file against design.md "Registry template changes"
- [x] 1.3 Extend `taxonomy/nfr-state.yaml` with `run_id`, `path_args`, `taxonomy_version`, `session_ids`, `active_stage`, `active_step`, and a per-file `{path, sha256, normalized, status}`, and verify that it parses with `uv run python -c "import yaml,sys;yaml.safe_load(open(sys.argv[1]))" <file>`
- [x] 1.4 Bump `metadata.version` in `skills/archy-init-nfr-taxonomy/SKILL.md` to `1.1.0`, and verify that `uv run pytest skills/archy-init-nfr-taxonomy/tests` passes
- [x] 1.5 Add a test asserting that the materialized taxonomy contains `nfr-state.yaml` and `nfr-registry-log.md`, and verify that it passes

## 2. Skill scaffold

- [x] 2.1 Create `skills/archy-nfr-miner/`, with `SKILL.md` frontmatter `name: archy-nfr-miner`, a description, and an `argument-hint` (path, working_dir_base, run), and verify that `uv run pytest tests/` (naming conventions) passes
- [x] 2.2 Create empty `references/`, `scripts/`, and `tests/` folders with placeholder files that are replaced later, and verify the tree matches design.md "Skill layout"

## 3. resolve_run.py

- [x] 3.1 Implement path resolution: repeatable `--path`, dir (recursive), file, glob, list; supported extensions; exclusions for `--working-dir-base`, `--taxonomy-dir`, and hidden folders; repo-relative, sorted, de-duplicated output. Verify with tests for equivalent forms, self-exclusion, and unsupported-only input (exit non-zero with a report)
- [x] 3.2 Add sha256 per file and PEP 723 inline metadata, and verify that `uv run skills/archy-nfr-miner/scripts/resolve_run.py --path test-data` prints valid JSON outside the project venv
- [x] 3.3 Implement run matching over `{working_dir_base}/*/state.yaml` (identical, superset, subset, partial, none, plus stale files, stage, step, and finished), and verify with fixture runs covering every match class and a changed-hash case

## 4. normalize_sources.py

- [x] 4.1 Implement DOCX conversion via `pypandoc-binary` (`-t gfm --wrap=none --track-changes=accept`, no media) to `sources/<rel>.<ext>.md`, and verify with a test that uses a generated docx containing a table and a tracked insertion
- [x] 4.2 Implement PDF conversion via `pdfplumber` with `<!-- page N -->` markers, pipe tables, and table regions cropped from the text, and verify with a generated three-page text PDF (markers in order, table rendered once)
- [x] 4.3 Implement the skip-when-unchanged logic (compare against the recorded sha), `failed` with a reason for conversion errors and image-only PDFs, and an image count per file. Verify with tests for skip, "no extractable text", and a corrupt file, where the other files still convert
- [x] 4.4 Emit a JSON result (per-file status, normalized path, reason, image count) with PEP 723 dependencies, and verify with `uv run` on `test-data/Northwind-Cloud-Landing-Zone-SAD.docx`

## 5. Mining brief (references/nfr-mine-file.md)

- [x] 5.1 Write the per-file brief covering: inputs (source, normalized path, taxonomy paths, output path); evidence-only rule; citation formats; types and verbatim vocabulary; `Metrics`; confidence anchors; completeness rules; priority rule; statuses; open questions and `SKILL` defaults; functional items to Dropped; local IDs; and no human interaction. Verify by checking each spec requirement for mining is addressed
- [x] 5.2 Define the per-file output format (`mined/<rel>.md`: registry, open-question, and dropped rows with local IDs, plus a short summary line), and verify that the reduce step in SKILL.md consumes exactly this format

## 6. Review loop (references/nfr-review.md)

- [x] 6.1 Write the parameterized loop: inputs, main-thread-only rule, overview, mode choice, queue order, compact grammar, apply semantics (Confirmed, Comments, move to Dropped, TBD, pending, category validation), diff echo, state_log append, repeat, and park. Verify by checking it against the spec's "Human review loop" scenarios
- [x] 6.2 Include worked examples of batch and one-by-one sessions, and verify they use `NFR-###` and `Q#` IDs consistently with the template
- [x] 6.3 Rework `references/nfr-review.md` to the overview table (columns, group order, hint line), guided multi-tab cards (tab order, overflow into a follow-up ask with `Decision` last, the bulk Auto, priority, and dropped asks, and the text fallback), and short command aliases next to the long form. Verify against the spec's "Human review loop" scenarios
- [x] 6.4 Replace the worked examples with one guided session (an entry with a question, a conflict, and no priority) and one command session using short aliases, and verify that the IDs match the template

## 7. SKILL.md orchestration

- [x] 7.1 Write argument parsing (quoted list, dir, mask) and pre-flight: run the init script, take `taxonomy_dir` from its JSON, read the five files, hard-stop without fallback, and state the resolved paths. Verify by manual run with a deleted `quality-attributes.md` (stops and names it)
- [x] 7.2 Write Stage 0: call `resolve_run.py`, turn the match class into the resume/new/add question, create the run folder from the templates, append the session ID, and handle no-path by listing unfinished runs. Verify by a manual resume after `/clear`
- [x] 7.3 Write Stage 1: normalize, map (inline for one file, otherwise subagents capped at 5 in parallel with the brief path), reduce (NFR-### assignment, dedupe keeping citations, conflicts), validate with auto-fix x2, update state at each step boundary. Verify on a multi-file fixture folder
- [x] 7.4 Write the summary rendering as one table (a row per file before merging, a failed file as one row, and a `TOTAL (merged)` row) followed by the counts line, and verify that the TOTAL equals mined minus merged duplicates on the fixture run
- [x] 7.5 Write Stage 2 (delegate to `references/nfr-review.md` with scope = whole registry) and the completion hand-off (state finished, file paths, next-step skills), and verify by running a review to completion

## 8. End-to-end verification

- [x] 8.1 Create a mixed fixture set in `test-data/nfr-miner/` (.md with measured and vague NFRs and a functional line, .docx with an RTO conflicting with the .md, text PDF, image-only PDF), and verify that a full run produces the expected conflict, dropped item, failed file, and Auto/TO REVIEW split
- [x] 8.2 Interrupt a run after mining one file, resume in a new conversation, and verify that only the pending files are mined and the session IDs list both sessions
- [x] 8.3 Run `uv run pytest` for the whole repo and `openspec validate add-archy-nfr-miner --strict`, and verify that both pass
