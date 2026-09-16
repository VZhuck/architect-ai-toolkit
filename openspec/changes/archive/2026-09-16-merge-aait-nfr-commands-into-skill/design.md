## Context

`skills/aait-nfr/` implements a four-phase NFR pipeline — detect, refine, publish, validate — backed by five reference files, three catalog templates, and two scripts. `commands/aait/` wraps it in four command files whose only distinct jobs are parsing `--nfr-path` (an identical rule restated four times) and naming the phase.

The pipeline already persists its own position. `references/02-refine.md` opens with a section called "Where the state comes from" and instructs each of the three gates to write its confirmed result into the draft before moving on, "so the work survives the conversation". It already performs a form of phase inference: *"If no draft exists, phase 1 has not run — say so and offer to run detect rather than mining silently."* The command layer duplicates a decision the skill is already equipped to make.

Two facts shape the design:

- **`nfrPath` is a living document.** It is fed by successive source batches over time. `01-detect.md` continues identifier numbering from an existing document on a maintenance run; `03-publish.md` merges by identifier while holding locked priorities and states that *"absence of evidence is not retraction"*. The document therefore has no phase — only a run does.
- **Nothing is wired.** Neither `commands/aait/` nor `skills/aait-nfr/` is symlinked into `.claude/`, so there is no working entry point to break. Wiring them is out of scope for this change.

## Goals / Non-Goals

**Goals:**

- One entry point, `aait-nfr`, with phase as an optional argument.
- A no-argument happy path that reads the in-flight run and resumes at the right gate.
- Inference that is announced, never silent, and always overridable.
- A decidable end-of-run signal, so a completed run is never mistaken for an in-flight one.
- Removal of `commands/aait/` with no loss of behaviour documented in its files.

**Non-Goals:**

- Wiring `.claude/skills/aait-nfr` or any symlink work.
- Touching `commands/opsx/`, the three other top-level commands, or any other skill.
- Changing classification, catalog, merge, or validation behaviour. The pipeline's substance is unchanged; only its entry surface is.
- Preserving the `aait:` namespace. Directory namespacing is a commands-only feature for project files, and it goes with the commands.

## Decisions

### One skill with an inferred phase, not four phase skills

Four skills named `aait-nfr-detect`, `-refine`, `-publish`, `-validate` were considered and rejected. They would have kept four `/`-entries, but every one of them fires on the same trigger words — NFR, quality attributes, "-ilities" — so model invocation could land on `publish`, the only phase that writes the deliverable. They would also have forced a choice between duplicating the shared core (path resolution, the three-catalog hard stop, the closed-vocabulary rule, the P0 cap, locked priorities) into four SKILL.md files, or adding a hop from each to a shared one.

A single skill collapses the trigger-word collision entirely and keeps the core in the one file that already holds it. Phase becomes an argument, which also satisfies the constraint that skill *names* carry no whitespace: `detect` is passed as an argument, not embedded in a name.

### Inference reads the run, not the document

Phase is derived from the draft and trace pair only. `nfrPath`'s existence is deliberately excluded as a signal — on a living document it is true almost always and says nothing about progress. It survives as an input to publish, where it selects merge-by-identifier over create.

```
  draft in flight?
        │
   yes ─┴─▶ resume at the gate the trace's Decision Log says is next
        │
    no ────▶ ask which sources ──▶ detect ──▶ refine ──▶ publish (merge)
                                                              │
   validate ── orthogonal, any doc, any time ─────────────────┘
```

### Publish stamps the trace's Decision Log

This is the one hole the inference design opens. `03-publish.md` currently neither clears nor marks the draft after promotion, so run 2 would read run 1's fully refined draft and conclude "ready to publish" — re-promoting completed work and never offering detect on the new sources. With four commands the user named the phase, so the gap was invisible.

Three fixes were weighed:

| Option | Why not chosen |
| --- | --- |
| Delete draft and trace on publish | The trace is the audit trail; the template itself warns that deleting it "loses the audit trail". |
| Per-run draft filenames (`{stem}.{date}.draft.md`) | The resolver derives one fixed path from the document stem; "which run is in flight" gets harder, not easier. |
| **Stamp the trace (chosen)** | One row in a table that already exists, with a `Gate` column already in the template. Draft persists, provenance intact, Evidence accumulates across runs. |

In-flight is then decidable: the draft exists **and** the Decision Log carries no terminal publish row after the last recorded gate.

### Inference defers when the trace is missing

The existing spec requires that "the pipeline SHALL remain operable if the trace file is absent", which conflicts with keying inference on the Decision Log. Resolved by deferring rather than guessing: a draft with no trace means the gate cannot be determined, so the skill says so and asks. Explicitly requested phases still run, preserving the existing trace-deleted publish behaviour.

### The command files dissolve, they are not deleted wholesale

Each of the four carries content worth keeping:

| Content | Destination |
| --- | --- |
| `--nfr-path <path>` parsing rule (identical ×4) | `SKILL.md`, once |
| Phase selection | Replaced by inference plus explicit override |
| Per-phase relay and guardrail prose | The matching `references/0N-*.md` |
| `validate` accepting a foreign document path | `SKILL.md` validate section |

### `resolve_nfr_paths.py` reports draft and trace existence

It already reports `nfr_path_exists`. Adding `draft_exists` and `trace_exists` keeps the whole inference input in one resolver call rather than scattering filesystem probes through the prose.

## Risks / Trade-offs

- **Inference picks the wrong phase** → It is announced before anything runs, alongside the state it was read from, and an explicit phase overrides it. The skill already states resolved paths "so the user can correct you cheaply"; this extends the same habit to phase.
- **Discoverability drops** → Four command entries advertised four phases without being invoked. Mitigated by printing the phase map alongside the inferred state on every invocation.
- **A hand-edited or externally truncated trace misleads inference** → The failure is visible, not silent: the announced phase is wrong on screen before any write, and publish still validates before touching the target document.
- **Breaking change for `/aait:nfr-*` callers** → Real, but nothing is wired into `.claude/` today, so no working invocation breaks.
- **Stamping adds a write to publish** → It happens only after successful promotion, so a failed publish leaves the run correctly in flight.

## Migration Plan

1. Fold the command content into `SKILL.md` and the phase references; add inference and the phase map.
2. Add the publish stamp and the resolver booleans, with test coverage.
3. Delete `commands/aait/` last, once nothing references it.
4. Rollback is `git revert`; no data migration, since existing drafts and traces stay readable. A pre-existing trace simply has no publish row, which inference reads as in-flight — correct for any run that never published, and correctable by the user for one that did.

## Open Questions

None outstanding. Entry-point shape, phase inference, the draft lifecycle, and scope were settled before this change was opened.
