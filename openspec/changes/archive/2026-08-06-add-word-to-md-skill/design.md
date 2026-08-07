## Context

Today, converting a Word SAD into split, rule-compliant markdown is two disconnected steps, only the first of which is code: `convert-word-to-md` (PowerShell, calls `pandoc -t markdown`) writes raw markdown to a temp folder, then `sad-from-markdown` splits it by heading via `split-markdown-by-heading.py` and hands the result to an LLM step that is explicitly documented as "do NOT script this" for table/TOC/link normalization. Both skills were deleted from this repo (recoverable at git commit `a53675a`) as part of a broader migration from `.ai-automation/` (PowerShell, ADO-oriented) to `skills/` + `rules/` (Python/Jira-oriented, e.g. `skills/load-raw-req/`).

A probe conversion of `test-data/Northwind-Cloud-Landing-Zone-SAD.docx` with plain `pandoc -t markdown --extract-media=... --to=markdown-simple_tables-multiline_tables-grid_tables` showed pandoc's raw output does not satisfy `rules/sad-sections.instructions.md` on its own: it emits its own TOC block (must be discarded, not kept), pre-heading cover text with no heading wrapper, and — notably — an HTML `<table>` for a table with list-in-cell content and `&amp;` entities even though that table has **no** `colspan`/`rowspan` (i.e., per the rules it should become a markdown pipe table, not stay HTML). This is the concrete gap this change closes with deterministic code instead of LLM judgment.

## Goals / Non-Goals

**Goals:**
- Convert a `.docx` into a folder of `rules/sad-sections.instructions.md`-compliant markdown files using deterministic Python, runnable both as a CLI script and under `pytest`.
- Push table normalization, TOC/index generation, and file naming/splitting fully into script — remove the "LLM-only, do not script" step for these concerns.
- Establish `uv` as the one way Python scripts in this repo are run and their dependencies managed, since this skill introduces new dependencies (e.g. an HTML parser) beyond `requirements.txt`'s current two.

**Non-Goals:**
- Diagram/photo classification or raster→Mermaid conversion (still genuinely requires visual/LLM judgment; explicitly deferred).
- Any change to the Markdown→Word direction (`pypandoc`-based `convert-md-to-word`) or non-Python `.ps1` scripts, beyond migrating their dependency install instructions to `uv`.
- Reimplementing docx parsing in pure Python (rejected — see Decisions).

## Decisions

**1. Pandoc for extraction, Python for rule normalization (not a pure-Python docx parser).**
`pandoc` is already a hard dependency (`pypandoc` in `requirements.txt`, used for the reverse MD→DOCX direction) and is proven to surface `colspan`/`rowspan` as real HTML attributes on merged OOXML table cells — exactly the signal `rules/sad-sections.instructions.md` uses to decide "keep as HTML" vs "convert to markdown". Reimplementing that detection via `python-docx`/`mammoth`/`markitdown` would mean re-deriving merge/list/style handling pandoc already gets right, for no behavioral gain. Extraction stays pandoc; only the post-processing (which pandoc doesn't do per our rules) becomes new Python code.

**2. Table normalization keys off `colspan`/`rowspan` presence, not "has a list" or "has an entity".**
Verified against the sample doc: a table with bulleted list cells and `&amp;` is *not* a merged-cell table and must convert to markdown (`<br>`-joined bullet pseudo-format, entities unescaped). Only actual `colspan="…"`/`rowspan="…"` attributes trigger the "keep HTML + explanatory comment" path. This is implemented as a pure function (HTML table string → decision + markdown-or-annotated-HTML string) so it can be unit-tested directly with synthetic snippets, independent of a real docx — the sample doc happens not to contain a merged-cell table, so that branch needs synthetic coverage.

**3. Fix the naming-convention ambiguity in the rules doc itself, don't paper over it in code.**
`rules/sad-sections.instructions.md` says "kebab-case" but its own examples (`01.Executive-Summary.md`) preserve title-case words. A deterministic splitter needs one exact answer; "infer intent" isn't available to code the way it was to an LLM doing this by hand. Decision: preserve source heading word casing, hyphenate spaces, strip Windows-invalid characters — matching the existing examples — and correct the rule's wording to say this explicitly rather than "kebab-case".

**4. Index generation is fully mechanical.**
Building `00.Index.md` (ordered top-level list of H1s, nested list of H2/H3 with GitHub-style lowercase-hyphenated anchors) requires no semantic judgment — it's a deterministic transform over the heading tree already produced by the splitter. Implemented in script, matching the format already documented in the rules and the old `sad-from-markdown` Step 3 example.

**5. `uv` migration bundled into this change, not split out.**
This skill is the first consumer that needs a new dependency (an HTML/table parser) beyond the current two in `requirements.txt`, and the user wants every script's execution to run inside a `uv`-managed env going forward. Bundling avoids a change that "installs infra nobody uses yet" and one that "adds a skill with an undocumented dependency." Structured as an early, independently-reviewable task within `tasks.md` since it changes how *every* existing Python script (`split-markdown-by-heading.py`, `copy-dir.py`) is invoked, not just this new skill.

**6. Skill is fully self-contained under `skills/word-to-md/`.**
Matches the `skills/load-raw-req/` convention (SKILL.md + local `templates/`): scripts and tests live under the skill's own folder (`scripts/`, `tests/`) rather than a repo-wide `tests/` directory, so the skill remains portable. A symlink `.claude/skills/word-to-md -> ../../skills/word-to-md` exposes it to Claude Code, mirroring the existing `load-raw-req` symlink. No `pytest.ini`/`pyproject` test-path config is required for `uv run pytest skills/word-to-md/tests/` to work; a bare `uv run pytest` from repo root also auto-discovers it.

## Risks / Trade-offs

- **[Risk]** The sample test docx doesn't exercise the merged-cell ("keep as HTML") branch → **Mitigation**: synthetic unit tests feed the table-normalizer function crafted HTML with `colspan`/`rowspan` directly, independent of any docx.
- **[Risk]** `uv` migration changes how *every* existing Python script is invoked (`uv run python ...` instead of `python ...` inside an activated venv) → **Mitigation**: keep it as one focused, early task in `tasks.md` with its own verification step (existing scripts still run under `uv run`), reviewable independently of the word-to-md logic.
- **[Risk]** Pandoc version/flag drift could change raw output shape (e.g. how it emits tables) between environments → **Mitigation**: pin the pandoc invocation flags exactly as probed (`--to=markdown-simple_tables-multiline_tables-grid_tables`), and let the pytest suite catch drift by asserting on the final normalized output, not on pandoc's raw intermediate.
- **[Risk]** Skipping Mermaid/diagram conversion leaves a known gap vs. the old workflow's aspiration → **Mitigation**: explicitly out of scope per this design; images pass through with paths/attributes preserved, no silent lossy behavior.

## Open Questions

- Should the `uv` migration also update `install.py`'s guidance/scripts, or is that tracked as a follow-up once `pyproject.toml` lands? (Default assumption for tasks.md: update any explicit `pip install -r requirements.txt` references found during implementation; broader `install.py` restructuring is out of scope unless it directly breaks.)
