## Context

This repo distributes skills/commands/rules to other repos. The prior distribution mechanism (`create-links.ps1` + `install.py`, symlinking into `.claude`/`.github`) has been deleted from the working tree but not replaced. A draft `ossify-cogents.json` already exists at the repo root, registering this repo as an `ossify-cogents` source with `skills: ["*"]`, `commands: ["*"]`, `rules: ["*"]` for the `claude` target platform.

`ossify-cogents` (external CLI, https://github.com/VZhuck/ossify-cogents) is the intended distribution mechanism going forward. Per its README:
- Binary name is `ossify-cogents`, installed via `uv tool install git+https://github.com/VZhuck/ossify-cogents.git` (requires Python 3.12+ and `uv`).
- `ossify-cogents install` operates on whatever `ossify-cogents.json` it finds in the current workspace (nearest `.git` root) — there is no flag to point `install` at a remote or alternate config file.

Because of that last constraint, an install script cannot just invoke `ossify-cogents install` with a URL argument. It must physically place this repo's `ossify-cogents.json` into the consumer's working directory first, then invoke `ossify-cogents install` normally.

## Goals / Non-Goals

**Goals:**
- One-line copy-pasteable install command per OS that gets a consumer from "nothing" to skills installed via `ossify-cogents`.
- Fail loudly and safely rather than silently clobbering a consumer's existing `ossify-cogents.json`.
- Keep the manual fallback (option 2) completely script-free — just folders to copy.

**Non-Goals:**
- Auto-installing `uv` itself. If `uv` is missing, the script errors out with a link to the uv install docs; it does not shell out to a second installer.
- Merging into an existing `ossify-cogents.json` (e.g. adding this repo's registry entry into an array that already has other sources). Out of scope for this change — `--force` only supports full overwrite.
- Cross-repo automation beyond the two scripts (e.g. no CI, no publishing pipeline for `ossify-cogents.json`).

## Decisions

**Decision: `uv` missing → hard fail; `ossify-cogents` missing → auto-install via `uv tool install`.**
`uv` is a general-purpose package/tool manager; silently installing it from a piped script is a much bigger, more invasive action than installing one CLI tool (`ossify-cogents`) *through* a package manager the user has already opted into. Failing fast on missing `uv` keeps the script's blast radius limited to what `uv tool install` does. Alternative considered: auto-bootstrap `uv` too (rejected — too invasive for a one-liner people will pipe into `bash`/`iex`).

**Decision: overwrite-protection on `ossify-cogents.json`, bypassed only by `--force` / `-Force`.**
The script writes into the *consumer's* working directory, which may already have its own `ossify-cogents.json` (own registries, own selections). Failing by default prevents silent data loss; `--force` is an explicit, single-purpose opt-in to overwrite (not a general "skip all checks" switch).

**Decision: scripts live at `scripts/install.sh` and `scripts/install.ps1` in this repo, fetched and run via `curl | bash` / `irm | iex`.**
Matches the existing `uv` and `ossify-cogents` installers' own UX convention (single piped command), and keeps the scripts version-controlled and reviewable in the same repo as the config they seed. Alternative considered: gist or separate installer repo (rejected — unnecessary indirection, `ossify-cogents.json` already lives here).

**Decision: manual option (option 2) is documentation-only, no script.**
Manual install is "copy `skills/`, `commands/`, `rules/` into your repo" — there's no decision logic or external dependency involved, so a script would add ceremony without reducing the number of user actions.

**Decision: fetch source is this repo's `main` branch via raw.githubusercontent.com.**
Matches how `ossify-cogents.json`'s own registry entries reference `{ "uri": ..., "ref": "main" }`, and needs no auth for a public repo.

## Risks / Trade-offs

- [Risk] `curl | bash` / `irm | iex` piping is a common phishing/tampering vector in general → Mitigation: script is fetched from this repo's own `raw.githubusercontent.com` URL over HTTPS, matching the same trust model `uv`'s and `ossify-cogents`'s own installers use; README shows the exact URL so it's inspectable before running.
- [Risk] `ossify-cogents install`'s behavior (what exactly gets copied where) is entirely defined by the `ossify-cogents.json` this change ships, and by `ossify-cogents` itself — this change does not control or test that tool's internals → Mitigation: out of scope; treat `ossify-cogents` as an external dependency, note this in the proposal's Impact section.
- [Risk] `ossify-cogents.json`'s `install.agents`/`skills`/`commands`/`rules` arrays use `["*"]` (install everything) — a consumer has no granular opt-out via the scripted path → Mitigation: not addressed by this change; consumers wanting a subset use option 2 (manual copy) or edit the fetched JSON before re-running `ossify-cogents install`.

## Migration Plan

1. Commit the existing untracked `ossify-cogents.json` as-is.
2. Add `scripts/install.sh` and `scripts/install.ps1`.
3. Replace the README's `create-links.ps1`-based "Creating Soft Link Mappings" section with the two-option install guide.
4. No rollback concerns beyond reverting the commit — no runtime/production system is touched, only repo docs/scripts.

## Open Questions

- None outstanding; overwrite semantics, bootstrap depth, and script location were confirmed during exploration.
