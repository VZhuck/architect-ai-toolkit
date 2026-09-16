## 1. Settled decisions carried into implementation

No blockers remain. These are confirmed and must hold throughout:

- [x] 1.1 Use the namespaced command form `commands/aait/nfr-*.md` → `/aait:nfr-detect` etc. — `ossify-cogents` discovery recurses into the subfolder, so no flat-file fallback is needed
- [x] 1.2 `/aait:nfr-validate` takes an optional document path, falling back to the resolved `nfrPath`
- [x] 1.3 A maintenance run with no draft derives its next `BD-nn` / `QAR-nn` from the highest identifier per prefix in the target document; identifiers are never reassigned
- [x] 1.4 `nfrPath` resolves in three steps — `--nfr-path`, then `.env` `NFR_PATH`, then list `sad/` and ask the user for an existing document or a new one. Drafts and traces always stay in `ai-workflow/nfr/`; only the published document lands in `sad/`

## 2. Catalog migration

- [x] 2.1 Create `skills/aait-nfr/templates/` and move `skills/nfr/templates/qa-priorities.md` into it unchanged
- [x] 2.2 Move `business-qas.md` to `templates/business-drivers.md`: rename the H2 to `Business Drivers & Goals`, rename the first column to `Business Driver`, and repair the truncated Risk & Compliance description
- [x] 2.3 Add a baseline `Priority` column to `business-drivers.md`, matching the shape `quality-attributes.md` already uses
- [x] 2.4 Move `technical-qas.md` to `templates/quality-attributes.md`, verifying that all 12 attribute names, baseline priorities, and fitness functions survive byte-for-byte
- [x] 2.5 Write `templates/nfr-document.md` — the target document shape with `BD-nn` / `QAR-nn` tables, `Constraints` (typo corrected), and `Assumptions`, compliant with `rules/sad-sections.instructions.md`
- [x] 2.6 Write `templates/nfr-trace.md` — evidence→ID map, open questions, dropped candidates

## 3. Scripts

- [x] 3.1 Write `skills/aait-nfr/scripts/resolve_nfr_paths.py`, mirroring `summarize-meeting-decisions/scripts/resolve_paths.py`: resolve `path`, resolve `nfrPath` through the three-step ladder (explicit argument → `.env` `NFR_PATH` via plain `key=value` parsing, no `python-dotenv` → list `sad/` markdown documents for the caller to choose from), and derive the draft and trace paths under `ai-workflow/nfr/`
- [x] 3.2 Add new-document name proposal to `resolve_nfr_paths.py`: derive the next free section number in `sad/` and emit a `rules/sad-sections.instructions.md`-compliant filename for the user to accept or adjust; handle `sad/` being absent or empty by asking for a path outright
- [x] 3.3 Write `validate_nfr.py` catalog-fidelity checks: exact-match attribute names, business table row count capped at the catalog
- [x] 3.4 Add business/technical separation checks: narrow mechanism-and-measurement keyword scan on driver cells, and a money-or-date requirement per driver cell, with regulation names explicitly passing
- [x] 3.5 Add the measurability check: threshold with unit, or an explicit `(proposed)` / `TBD` marker
- [x] 3.6 Add the `P0` budget check (≤ 7 rows)
- [x] 3.7 Add the priority-lock check against the git `HEAD` version, degrading to a warning when no `HEAD` version or no repository exists
- [x] 3.8 Add structural checks: four expected sections, two-line assumption shape, and `rules/sad-sections.instructions.md` compliance (one H1, blank line before headings, markdown tables)
- [x] 3.9 Add legacy-heading detection reporting `Business Quality Attribures` / `Quality Attributes` / `Constrains` with their corrected names, without rewriting the document
- [x] 3.10 Ensure the script exits non-zero on any failure, names the failing check and row, and never modifies the document it validates

## 4. Skill

- [x] 4.1 Write `skills/aait-nfr/SKILL.md` — orchestrator only: parameters, path resolution, phase router naming the exact reference file per phase, and the rule that only publish writes to `nfrPath`. Keep it short enough that nothing competes with the phase reference once loaded
- [x] 4.2 Write `references/discriminators.md` — the ordered ladder with the fitness-function test ahead of the business test, worked examples for the GDPR/PII case and the penalty-fee case, and the compressed rule of thumb
- [x] 4.3 Write `references/miner-agent.md` — the brief handed to each mining subagent: the closed catalogs, the ladder, the output row schema, verbatim-evidence and provenance requirements, and the instruction to return nothing outside the schema
- [x] 4.4 Write `references/01-detect.md` — source collection and the >30-file check, parallel fan-out, batch merge and deduplication, off-catalog rejection at the boundary, the classification gate, and first write of draft and trace
- [x] 4.5 Write `references/02-refine.md` — the three gates (open questions, metrics, priorities), each written into the draft on confirmation, with the rule that unanswered questions stay in the trace file and never become assumptions
- [x] 4.6 Write `references/03-publish.md` — re-read catalogs in fresh context, render, validate, ID-matched merge preserving locks and human edits, diff, promote, and report
- [x] 4.7 Define the gate visualizations: candidate funnel after detect, catalog coverage grid with gaps marked, and the `P0` budget indicator

## 5. Commands

- [x] 5.1 Write `nfr-detect.md` — parse `path` and optional `--nfr-path`, invoke the skill's detect phase, relay the funnel and coverage grid, and keep source file contents out of the conversation
- [x] 5.2 Write `nfr-refine.md` — parse optional `--nfr-path`, invoke the refine phase, relay each gate
- [x] 5.3 Write `nfr-publish.md` — parse optional `--nfr-path`, invoke the publish phase, relay the validation result and diff
- [x] 5.4 Write `nfr-validate.md` — run the validator standalone and relay the report
- [x] 5.5 Add `.claude/` symlinks for the skill and all four commands, matching the existing convention

## 6. Tests

- [x] 6.1 Add `skills/aait-nfr/tests/test_resolve_nfr_paths.py` covering explicit paths, `.env` fallback, the `sad/` listing fallback, the proposed new-document name for a `sad/` holding `00.Index.md`–`07.*.md`, an absent or empty `sad/`, and derived draft/trace locations outside `sad/`
- [x] 6.2 Add validator fixtures: a clean document, and one document per failure mode (paraphrased attribute, technical content in a driver cell, driver with no money or date, unmeasurable requirement, eight `P0` rows, altered lock, malformed assumption, SAD violation, legacy headings)
- [x] 6.3 Add the regression fixture for the driver naming a regulation — "€2m penalty … PCI-DSS 4.0 … by 30/06/2027" must pass
- [x] 6.4 Add a lock-check test for the no-`HEAD` case asserting a warning rather than a failure
- [x] 6.5 Confirm `uv run pytest skills/aait-nfr/tests/` passes

## 7. End-to-end verification

- [x] 7.1 Run the full pipeline against `test-data/meeting-notes/` and confirm the draft and trace land in `ai-workflow/nfr/` and the target document is untouched until publish
- [x] 7.2 Verify the GDPR/PII sentence is classified as a quality attribute requirement and the penalty-fee sentence as a business driver
- [x] 7.3 Run `/aait:nfr-publish` on a deliberately under-refined draft and confirm validation fails and the target document is unchanged
- [x] 7.4 Run a maintenance pass and confirm rows match by identifier, locks hold, human edits survive, and unmentioned requirements are retained
- [x] 7.5 Confirm `md-to-word` on `sad/` does not pick up the draft or trace files

## 8. Cleanup and documentation

- [x] 8.1 Delete `skills/nfr/` once nothing references it
- [x] 8.2 Group `NFR_PATH` under an NFR heading in `.env.example`, alongside the other skill fallbacks
- [x] 8.3 Note the `aait` prefix convention for new skills and commands in `AGENTS.md`, stating that existing skills are not renamed
- [x] 8.4 Run `openspec validate add-aait-nfr-toolset --strict`
