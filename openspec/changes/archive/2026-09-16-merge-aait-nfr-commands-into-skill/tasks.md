## 1. Path resolver reports the inference inputs

- [x] 1.1 Add `draft_exists` and `trace_exists` booleans to the JSON output of `skills/aait-nfr/scripts/resolve_nfr_paths.py`, alongside the existing `nfr_path_exists`
- [x] 1.2 Add the same two lines to the script's human-readable output, next to the existing `exists:` line for the target document
- [x] 1.3 Extend `skills/aait-nfr/tests/test_resolve_nfr_paths.py` to cover all four combinations of draft and trace presence
- [x] 1.4 Run `uv run pytest skills/aait-nfr/tests/` and confirm the suite passes

## 2. Publish stamps the trace

- [x] 2.1 Document the terminal publish row in the Decision Log table of `skills/aait-nfr/templates/nfr-trace.md`, naming the date and the promoted target
- [x] 2.2 Add a final step to `skills/aait-nfr/references/03-publish.md` that appends the publish row only after promotion succeeds, so a failed publish leaves the run in flight
- [x] 2.3 State in `03-publish.md` that the Decision Log accumulates across runs against the same living document and is never reset

## 3. Phase inference in SKILL.md

- [x] 3.1 Add a phase-inference section to `skills/aait-nfr/SKILL.md`: read draft and trace, infer the phase, announce the inferred phase and the state it was read from before acting
- [x] 3.2 Specify the inference rules — no draft means a new run at detect; draft plus no terminal publish row means in flight at the gate the Decision Log points to; a terminal publish row means the run is complete and a new detect run is offered
- [x] 3.3 State that `nfrPath` is a living document carrying no phase, and that its existence only selects merge-by-identifier over create at publish
- [x] 3.4 Specify the trace-absent fallback: a draft with no trace means the gate cannot be determined, so ask the user and never guess a gate or silently restart
- [x] 3.5 Specify that an explicit phase argument overrides inference, and that the skill states both the inferred phase and the override
- [x] 3.6 Specify that validate is reachable only by explicit request and is never selected by inference
- [x] 3.7 Print the phase map alongside the inferred state on every invocation

## 4. Absorb the command files

- [x] 4.1 Fold the `--nfr-path <path>` parsing rule into `SKILL.md` once, replacing the four identical copies
- [x] 4.2 Update the `phase` entry in the `SKILL.md` frontmatter `argument-hint` to read as optional, defaulting to inference
- [x] 4.3 Move the detect relay guardrails from `commands/aait/nfr-detect.md` into `references/01-detect.md` — relay the candidate funnel, coverage grid, and classification gate; never surface raw source contents
- [x] 4.4 Move the refine relay guardrails from `commands/aait/nfr-refine.md` into `references/02-refine.md` — every gate runs in this conversation, none may be delegated to a subagent
- [x] 4.5 Move the publish relay guardrails from `commands/aait/nfr-publish.md` into `references/03-publish.md` — relay validation result and diff, confirm the target is untouched on failure, never work around a failing check by editing the target directly
- [x] 4.6 Move the validate behaviour from `commands/aait/nfr-validate.md` into the Validation section of `SKILL.md` — optional `docPath` accepting a document this pipeline did not produce, plus the judgement checks the script cannot make
- [x] 4.7 Replace the six `/aait:…` cross-references in `skills/aait-nfr/` (five in `SKILL.md`, one in `references/02-refine.md`) with phase names

## 5. Remove the command layer

- [x] 5.1 Confirm nothing outside `commands/aait/` references `/aait:nfr-` by grepping the repo
- [x] 5.2 Delete `commands/aait/nfr-detect.md`, `nfr-refine.md`, `nfr-publish.md`, `nfr-validate.md` and the now-empty `commands/aait/`
- [x] 5.3 Confirm `commands/opsx/`, `commands/load-raw-req.md`, `commands/md-to-word.md`, `commands/summarize-meeting-decisions.md`, and every other skill are untouched by this change

## 6. Verify

- [x] 6.1 Walk each scenario in the `nfr-analysis` delta spec against the edited skill files and confirm the prose covers it
- [x] 6.2 Walk each scenario in the `nfr-document-validation` delta spec and confirm validate stays orthogonal to inference
- [x] 6.3 Run `openspec validate merge-aait-nfr-commands-into-skill` and resolve any findings
- [x] 6.4 Confirm `README.md` and `AGENTS.md` carry no `/aait:nfr-*` references, and update them if they do
