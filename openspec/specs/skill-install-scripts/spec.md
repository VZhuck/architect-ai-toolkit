# skill-install-scripts

## Purpose

Provide a scripted, one-line way to install this repo's skills, commands, and rules into a consumer repository via `ossify-cogents`, alongside a manual folder-copy fallback. TBD: expand with broader capability context as the surface area grows.

## Requirements

### Requirement: Committed ossify-cogents registry file
The repository SHALL include a committed `ossify-cogents.json` at the repo root registering this repo as an `ossify-cogents` source with discovery mappings for `agents/`, `skills/`, `commands/`, and `rules/` folders.

#### Scenario: Registry file present at repo root
- **WHEN** a consumer inspects this repository after cloning
- **THEN** `ossify-cogents.json` exists at the repo root and is tracked in git (not merely present locally)

### Requirement: Scripted install checks for uv and fails if absent
Both install scripts (`scripts/install.sh` and `scripts/install.ps1`) SHALL check whether `uv` is available on the caller's `PATH` before doing anything else, and SHALL exit with a non-zero status and an error message pointing to the `uv` installation docs if `uv` is not found.

#### Scenario: uv not installed
- **WHEN** a user runs `scripts/install.sh` (or `scripts/install.ps1`) on a machine without `uv` on `PATH`
- **THEN** the script exits non-zero, prints an error identifying `uv` as missing, and includes a link to the `uv` installation instructions
- **THEN** the script does not attempt to install `uv`, `ossify-cogents`, or write any files

### Requirement: Scripted install auto-installs ossify-cogents if missing
Given `uv` is available, both install scripts SHALL check whether the `ossify-cogents` executable is available on `PATH`, and if not, SHALL install it by running `uv tool install git+https://github.com/VZhuck/ossify-cogents.git` before proceeding.

#### Scenario: ossify-cogents not yet installed
- **WHEN** a user runs an install script with `uv` present but no `ossify-cogents` executable on `PATH`
- **THEN** the script runs `uv tool install git+https://github.com/VZhuck/ossify-cogents.git`
- **THEN** the script proceeds to the config-fetch step after the tool install succeeds

#### Scenario: ossify-cogents already installed
- **WHEN** a user runs an install script and `ossify-cogents` is already on `PATH`
- **THEN** the script does not attempt to reinstall it and proceeds directly to the config-fetch step

### Requirement: Scripted install refuses to overwrite an existing config without --force
Both install scripts SHALL check whether `ossify-cogents.json` already exists in the caller's current working directory before writing to it. If it exists and the `--force` (bash) / `-Force` (PowerShell) flag was not passed, the script SHALL exit with a non-zero status and an error message instructing the user to rerun with the force flag, without modifying the existing file.

#### Scenario: Existing config, no force flag
- **WHEN** a user runs an install script in a directory that already contains `ossify-cogents.json`, without passing `--force`/`-Force`
- **THEN** the script exits non-zero, prints an error stating the file already exists and that `--force`/`-Force` is required to overwrite it
- **THEN** the existing `ossify-cogents.json` in that directory is left unmodified

#### Scenario: Existing config, force flag passed
- **WHEN** a user runs an install script in a directory that already contains `ossify-cogents.json`, passing `--force` (bash) or `-Force` (PowerShell)
- **THEN** the script overwrites the existing `ossify-cogents.json` with the fetched copy from this repo and continues to the install step

#### Scenario: No existing config
- **WHEN** a user runs an install script in a directory with no `ossify-cogents.json`
- **THEN** the script writes the fetched `ossify-cogents.json` into that directory without requiring any force flag

### Requirement: Scripted install fetches this repo's config and runs ossify-cogents install
After the overwrite check passes, both install scripts SHALL fetch the `ossify-cogents.json` from this repository's `main` branch (via `raw.githubusercontent.com`), write it to the caller's current working directory, and then invoke `ossify-cogents install`.

#### Scenario: Successful end-to-end run
- **WHEN** a user runs an install script with `uv` present, and either `ossify-cogents` present or successfully installed, and the overwrite check passes
- **THEN** the script downloads this repo's `main`-branch `ossify-cogents.json` into the current working directory
- **THEN** the script invokes `ossify-cogents install` in that directory

### Requirement: README documents two install options
The README's installation guide SHALL document exactly two ways to install this repo's skills/commands/rules into a consumer repo: a recommended one-line scripted install via `ossify-cogents`, and a manual folder-copy fallback with no script.

#### Scenario: Recommended option documented
- **WHEN** a reader views the README's installation guide
- **THEN** it shows a one-line `curl | bash` command for macOS/Linux and a one-line `irm | iex` command for Windows, both referencing `scripts/install.sh` / `scripts/install.ps1` in this repo, labeled as recommended

#### Scenario: Manual option documented
- **WHEN** a reader views the README's installation guide
- **THEN** it shows a manual option describing copying the `skills/`, `commands/`, and `rules/` folders directly into the consumer's repository, with no script involved

#### Scenario: Stale symlink instructions removed
- **WHEN** a reader views the README after this change
- **THEN** it no longer references `create-links.ps1` or the deleted symlink-based install workflow
