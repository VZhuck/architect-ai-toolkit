## Why

The four `commands/aait/*.md` files are a manual phase selector bolted onto a pipeline that already tracks its own position: `references/02-refine.md` opens with "Where the state comes from", and every refine gate writes its result into the draft immediately "so the work survives the conversation". The commands restate an identical `--nfr-path` parsing rule four times and contribute nothing the draft and trace do not already record.

Keeping them also keeps a hazard. All four descriptions fire on the same trigger words — NFR, quality attributes, "-ilities" — so a model-invoked run can land on the wrong phase, including `publish`, the only phase that writes the deliverable. Collapsing to one entry point removes the ambiguity at its source. (Custom commands are not deprecated; they are merged into skills. This is de-duplication, not a forced migration.)

## What Changes

- **BREAKING** `/aait:nfr-detect`, `/aait:nfr-refine`, `/aait:nfr-publish`, and `/aait:nfr-validate` are removed. `commands/aait/` is deleted. The `aait:` namespace goes with it — local skills are invoked flat, and directory namespacing is a commands-only feature.
- `aait-nfr` becomes the single entry point. Phase becomes an optional argument rather than part of an invocation name.
- **The happy path takes no argument.** `/aait-nfr` reads the in-flight draft and trace, announces the phase it inferred, and resumes at the correct gate — matching the skill's existing habit of stating resolved paths "so the user can correct you cheaply".
- Phase is inferred from the in-flight run only. `nfrPath` is a living document fed by successive source batches; it carries no phase, and its existence selects merge-by-identifier versus create at publish time, nothing more.
- An explicit phase argument remains available as an override for cases inference cannot reach.
- `validate` stays orthogonal: callable at any time, against any document including one this pipeline never produced, with no draft or trace required.
- **Publish stamps the trace.** `references/03-publish.md` currently neither clears nor marks the draft after promotion, so a completed run's draft would be misread as in-flight on the next run. Publish gains a terminal `publish` row appended to the trace's existing Decision Log table. The draft persists, provenance stays intact, and the Evidence table keeps accumulating across runs.
- `scripts/resolve_nfr_paths.py` reports whether the draft and trace exist. It reports `nfr_path_exists` today; those two booleans carry most of the inference.
- The four command files dissolve: the repeated `--nfr-path` rule collapses into `SKILL.md`, per-phase relay and guardrail prose folds into the matching `references/0N-*.md`, and the six `/aait:…` cross-references inside `skills/aait-nfr/` are updated.
- The skill's opening line prints the phase map alongside the inferred state, so the pipeline's four phases stay discoverable without four command entries advertising them.

## Capabilities

### New Capabilities

None. Phase inference is the `aait-nfr` skill orchestrating its own pipeline and belongs inside `nfr-analysis` rather than in a spec of its own.

### Modified Capabilities

- `nfr-analysis`: gains a requirement that phase is inferred from the in-flight draft and trace, with a no-argument resume path, an announced inference, and an explicit override. Parameter resolution extends to reporting draft and trace existence. Provenance gains the terminal publish stamp that makes "in flight" decidable. Scenarios keyed to `/aait:nfr-*` command names are restated against phases of the single skill.
- `nfr-document-validation`: `validate` and `publish` are restated as phases of the single skill rather than as `/aait:nfr-validate` and `/aait:nfr-publish` commands. Validation behaviour itself is unchanged.

## Impact

- **Removed**: `commands/aait/nfr-detect.md`, `commands/aait/nfr-refine.md`, `commands/aait/nfr-publish.md`, `commands/aait/nfr-validate.md`, and the now-empty `commands/aait/`.
- **Modified**: `skills/aait-nfr/SKILL.md` (phase inference, phase map, `--nfr-path` parsing, cross-references), `skills/aait-nfr/references/01-detect.md`, `02-refine.md`, `03-publish.md` (relay guardrails absorbed; publish stamps the trace), `skills/aait-nfr/scripts/resolve_nfr_paths.py` (report draft and trace existence), `skills/aait-nfr/templates/nfr-trace.md` (Decision Log documents its terminal publish row).
- **Tests**: `skills/aait-nfr/tests/test_resolve_nfr_paths.py` covers the two new booleans.
- **Users**: anyone invoking `/aait:nfr-*` must switch to `/aait-nfr`. Nothing is currently wired — neither `commands/aait/` nor `skills/aait-nfr/` is symlinked into `.claude/` — so no working entry point breaks.
- **Out of scope**: the missing `.claude/` symlinks, `commands/opsx/`, `commands/load-raw-req.md`, `commands/md-to-word.md`, `commands/summarize-meeting-decisions.md`, and every other skill.
