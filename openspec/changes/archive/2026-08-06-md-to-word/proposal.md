## Why

`skills/word-to-md` converts a SAD Word document into rule-compliant markdown section files, but there is no supported way back to `.docx`. The only prior art was a deleted PowerShell script (`.ai-automation/scripts/covert-markdown-to-word.ps1`), which is gone from the repo and doesn't fit the current pure-Python, `uv`-run skill convention. Architects need a Python-only skill to regenerate a Word deliverable from the maintained markdown, using a real Word template and a native (not materialized) table of contents.

## What Changes

- Add a new `md-to-word` skill (`skills/md-to-word/{SKILL.md,scripts/,tests/}`) that concatenates a folder of `<n>.<Title>.md` section files (as produced by `word-to-md`) into a single `.docx` via `pandoc`, invoked through `subprocess` (matching `word-to-md`'s convention; the unused `pypandoc` dependency is not used).
- Resolve the Word template in this order: explicit `--template` CLI argument → `.env`'s `SAD_TEMPLATE` key (plain regex parse, no `python-dotenv`) → no `--reference-doc` at all (pandoc's default styling, with a warning — not a hard error).
- Split `00.Index.md` into its cover-page preamble (title block, doc version, classification, cover image) and its materialized numbered TOC list; keep the cover, discard the list. A new `index_split.py` module exposes this as a standalone, unit-testable function.
- Invoke `pandoc -s --toc --toc-depth 3` so the output `.docx` gets a genuine native Word TOC field (an `sdt`-wrapped `fldChar`/`instrText "TOC \o \"1-3\""`, editable via Word's "Update Field") in place of the discarded materialized list.
- Add `commands/md-to-word.md` plus the usual `.claude/skills` and `.claude/commands` symlinks, following the existing `word-to-md` / `load-raw-req` pattern.
- Add a `SAD_TEMPLATE=` entry to `.env.example`.

## Capabilities

### New Capabilities
- `md-to-word-conversion`: converting a folder of rule-compliant markdown SAD section files back into a single templated `.docx` with a native Word TOC.

### Modified Capabilities
(none — no existing capability's requirements change)

## Impact

- New files under `skills/md-to-word/` (skill doc, scripts, tests) and `commands/md-to-word.md`.
- New symlinks under `.claude/skills/md-to-word` and `.claude/commands/md-to-word.md`.
- `.env.example` gains `SAD_TEMPLATE`.
- No changes to `skills/word-to-md` or any existing capability.
- Runtime dependency: `pandoc` on `PATH` (already required by `word-to-md`); no new Python packages.
