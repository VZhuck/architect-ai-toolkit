# Proposal

## Why

NFRs are scattered through SADs, meeting notes, and specs in `.md`, `.docx`, and `.pdf` form, and extracting them by hand is slow and inconsistent. The toolkit now ships a closed NFR taxonomy (`archy-init-nfr-taxonomy`), so a skill can mine requirements against that fixed vocabulary, keep a traceable registry with verbatim evidence, and hand a reviewed registry to later NFR skills (explore, propose).

## What Changes

- New skill `archy-nfr-miner` that mines NFRs (quality attribute requirements, business drivers, constraints, assumptions) from one or more source documents into a registry, then runs a human review loop over it.
  - `path` accepts a directory, a file, a glob mask, or a list of files (`"fileA.md", "fileB.pdf"`); `working_dir_base` defaults to `ai-workflow/nfr-state`.
  - Work is organized in **runs**, not sessions: a run's identity is its resolved file set (repo-relative paths plus sha256), so re-invoking with the same input after a reboot or `/clear` resumes the same run. Session IDs are recorded inside the run's state for traceability.
  - Pre-flight runs the taxonomy init script and hard-stops if any required taxonomy file is still missing.
  - Stage 0 restores or creates run state, matching existing runs by file-set overlap and detecting changed sources.
  - Stage 1 normalizes binary sources to one markdown file each (docx via pandoc, pdf via pdfplumber with page markers), mines each file in a subagent (map), then merges in the main thread (neutral `NFR-###` IDs, dedupe, conflicts, validation with auto-fix), and shows a single summary table (a row per file plus a merged total).
  - Stage 2 runs a reusable, main-thread review loop (`references/nfr-review.md`) with an overview table of all entries, a guided per-NFR review through multi-tab asks, compact commands (short and long forms), and park/resume.
  - Deterministic scripts (`resolve_run.py`, `normalize_sources.py`) with PEP 723 inline dependencies so the skill is self-contained when installed; no dependency on `archy-word-to-md`.
- Taxonomy templates updated (taxonomy version bumped to `1.1.0`):
  - `nfr-state-log.md` renamed to `nfr-registry-log.md`; registry gains `Metrics`, `Confidence`, and `Comments` columns; NFR IDs become `NFR-###`; `## Dropped` gains `NFR ID` and `Dropped by` columns; Open Questions reference an `NFR-###` and record who proposed a default.
  - `nfr-state.yaml` extended with run identity, path arguments, session IDs, per-file status/sha/normalized path, and stage/step position.

## Capabilities

### New Capabilities
- `nfr-miner`: mining NFRs from source documents into a run-scoped registry — argument and run resolution, source normalization, per-file mining, merge/validation, summary, and the human review loop.

### Modified Capabilities
- `nfr-taxonomy-init`: the shipped taxonomy SHALL include the NFR workflow templates (`nfr-state.yaml`, `nfr-registry-log.md`) that NFR skills instantiate per run.

## Impact

- New: `skills/archy-nfr-miner/` (`SKILL.md`, `references/nfr-mine-file.md`, `references/nfr-review.md`, `scripts/`, `tests/`).
- Changed: `skills/archy-init-nfr-taxonomy/SKILL.md` (version `1.1.0`), `taxonomy/nfr-state.yaml`, `taxonomy/nfr-state-log.md` → `taxonomy/nfr-registry-log.md`.
- Dependencies: `pypandoc-binary` and `pdfplumber`, declared inline in the miner's scripts (PEP 723) and run via `uv run`; no system pandoc required.
- Runtime output: run folders under `ai-workflow/nfr-state/<run-id>/` (`state.yaml`, `nfr-registry-log.md`, `mined/`, `sources/`).
- Out of scope: `/archy-nfr-explore`, `/archy-nfr-propose`, OCR of scanned PDFs, mining images/diagrams.
