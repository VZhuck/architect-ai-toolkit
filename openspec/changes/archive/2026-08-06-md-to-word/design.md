## Context

`skills/word-to-md` converts a source `.docx` into rule-compliant markdown section files (`00.Index.md` + `<n>.<Title>.md`), per `rules/sad-sections.instructions.md`. There is currently no supported reverse path. The only prior art is a deleted PowerShell script (`.ai-automation/scripts/covert-markdown-to-word.ps1`, still visible in git history at commit `81f7696`), which shelled out to `pandoc --reference-doc <template> <files...> -o out.docx` from inside the source folder, with a `--toc` flag present but commented out.

The repo has since moved off `.ai-automation/` entirely: skills live at `skills/<name>/`, commands at `commands/<name>.md`, both symlinked into `.claude/skills/` and `.claude/commands/` respectively (see `skills/word-to-md/`, `skills/load-raw-req/`, `commands/load-raw-req.md`). `pandoc` is required on `PATH` (already a `word-to-md` prerequisite). `pypandoc` sits in `pyproject.toml` as a declared dependency but is unused everywhere — `word-to-md` calls `pandoc` via raw `subprocess`, not `pypandoc`.

`00.Index.md` is not a pure TOC: `build_index()` in `skills/word-to-md/scripts/sad_structure.py` writes a cover preamble (title block, doc version, classification, cover image — anything that appeared before the first heading in the source docx) followed by a materialized nested list of numbered section/subsection links. Feeding this file straight into `pandoc --toc` would produce a document with cover content, a duplicate materialized list, and a native TOC all at once.

## Goals / Non-Goals

**Goals:**
- Convert a `word-to-md`-shaped markdown folder back into a single `.docx`, with a real Word template and a native, updatable Word TOC field.
- Keep the skill pure Python, invoked the same way as `word-to-md` (`uv run python skills/md-to-word/scripts/md_to_word.py ...`), with all scripts/tests inside `skills/md-to-word/`.
- Preserve the cover-page content that currently lives in `00.Index.md`'s preamble.

**Non-Goals:**
- Round-trip fidelity guarantees beyond what `pandoc` itself provides (no custom OOXML post-processing of styles, no diagram re-rendering).
- Changing anything in `skills/word-to-md` itself (its `00.Index.md` output format is a fixed input contract for this skill, not something this change modifies).
- Supporting input folders that don't follow the `<n>.<Title>.md` / `00.Index.md` naming convention.

## Decisions

**Call `pandoc` via `subprocess`, not `pypandoc`.**
`word-to-md` already does this, and `pypandoc` is an unused dependency in `pyproject.toml`. Using `subprocess` keeps both directions consistent and avoids introducing a second way of shelling out to the same tool. Alternative considered: use `pypandoc.convert_file` since it's already a declared dependency — rejected to avoid an inconsistent pattern between the two mirror skills.

**Split `00.Index.md` into cover vs. materialized-list, keep only the cover.**
The materialized list exists so the markdown is readable/navigable on its own (e.g. on GitHub); it has no purpose once `pandoc --toc` generates a real Word TOC field, and including both would duplicate the TOC. The split point is the first line matching a numbered list link pattern (`^\d+\.\s+\[`), mirroring the same "split by structural pattern" idiom `sad_structure.split_cover_and_body` already uses for the forward direction (there, the split point is the first heading; here, it's the first TOC list item). Everything before that line is the cover preamble; kept. Everything from that line onward is the materialized list; dropped. This is implemented in a new, standalone-testable module (`skills/md-to-word/scripts/index_split.py`, `split_cover_and_toc_list(text) -> (cover, dropped)`), not inline in the CLI script, so it can be unit tested against synthetic index text without a real docx/pandoc round trip.
Alternative considered: require `word-to-md` to emit an explicit marker (e.g. an HTML comment) between cover and list so the split is unambiguous by construction — rejected because it would require modifying `word-to-md`'s output contract (and `openspec/specs/word-to-md-conversion/spec.md`) for the benefit of a script that only needs to infer a boundary that's already structurally distinguishable via regex.

**Use `pandoc -s --toc --toc-depth 3` for a native Word TOC.**
Manually verified: `pandoc -s --toc --reference-doc <template>` on a docx target emits a genuine OOXML TOC field (`w:sdt` containing `w:fldChar`/`w:instrText` with `TOC \o "1-3"`), which Word treats as an updatable native field (right-click → Update Field), not a static list. Depth 3 matches the H1–H3 depth `word-to-md`'s index already covers.

**Template resolution: `--template` arg → `.env`'s `SAD_TEMPLATE` → no `--reference-doc`, with a warning.**
Mirrors the `.env`-fallback convention already used for `load-raw-req`'s `JIRA_KEYS` (plain regex parse of the repo-root `.env` file, no `python-dotenv` dependency — matching `pyproject.toml`, which does not declare `python-dotenv`). Falling back to pandoc's built-in default styling (rather than raising, as the old PowerShell script did) means a missing template degrades conversion quality instead of blocking it outright — reasonable for a document-generation utility where "produced but unstyled" is more useful than "produced nothing."

**Run `pandoc` with `cwd` set to the source folder.**
Section files reference images via relative `media/...` paths (as extracted by `word-to-md`). Running `pandoc` from inside the source folder, passing relative filenames, resolves those paths the same way the old PowerShell script did (`Push-Location $resolvedSourceDir`).

**Concatenation order: cover-only temp file, then `<n>.<Title>.md` files sorted by numeric filename prefix.**
Matches the numeric ordering already encoded in the filenames by `word-to-md`; no reliance on filesystem directory order.

**Default output path: `ai-workflow/md-to-word/<source-folder-name>.docx`.**
Mirrors `word-to-md`'s own `ai-workflow/word-to-md/<doc-stem>/` intermediate-folder convention, keeping generated artifacts out of the repo's tracked source folders by default.

## Risks / Trade-offs

- **Regex-based split of `00.Index.md` is heuristic, not structural.** → Mitigated by unit-testing `index_split.py` directly against the real sample output shape (as seen in `ai-workflow/sad-test/00.Index.md`) and by scoping this skill's input contract strictly to `word-to-md`'s own output format (not arbitrary hand-written markdown).
- **Missing `pandoc` on `PATH`, or missing/invalid template path.** → `pandoc` absence: fail fast with a clear error (same as `word-to-md`'s `extract_docx`). Template resolved but path doesn't exist: fail fast rather than silently degrading, since that's a config mistake rather than an absent-by-design template. Template *unresolved* (no arg and no `.env` key): warn and proceed without `--reference-doc`.
- **`--toc` depth mismatch if `word-to-md`'s index ever changes depth.** → Both are fixed at depth 3 today; if that changes, both skills need to move together (documented in this design so a future editor sees the coupling).

## Migration Plan

Purely additive — no existing files change behavior. New skill, new command, new symlinks, one new `.env.example` key. No rollback concerns beyond removing the new files.

## Open Questions

None outstanding — template resolution, TOC mechanism, and index-splitting approach were settled during exploration prior to this proposal.
