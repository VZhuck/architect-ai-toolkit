## 1. Registry file

- [x] 1.1 Commit the existing untracked `ossify-cogents.json` at the repo root as-is (verify its `agents`/`skills`/`commands`/`rules` folder mappings still match the current repo layout first)

## 2. Bash install script (macOS/Linux)

- [x] 2.1 Create `scripts/install.sh`: check `uv` on `PATH`, exit non-zero with an install-docs link if missing
- [x] 2.2 Check `ossify-cogents` on `PATH`; if missing, run `uv tool install git+https://github.com/VZhuck/ossify-cogents.git`
- [x] 2.3 Parse a `--force` flag; if `ossify-cogents.json` exists in the current working directory and `--force` was not passed, exit non-zero with an error instructing the user to rerun with `--force`
- [x] 2.4 Fetch `ossify-cogents.json` from this repo's `main` branch via `raw.githubusercontent.com` and write it to the current working directory (overwriting only if allowed per 2.3)
- [x] 2.5 Run `ossify-cogents install`
- [x] 2.6 Make the script executable (`chmod +x scripts/install.sh`) and verify it runs correctly via `bash scripts/install.sh` and via the `curl | bash` one-liner in a scratch directory

## 3. PowerShell install script (Windows)

- [x] 3.1 Create `scripts/install.ps1` mirroring the bash script's logic: check `uv` on `PATH`, exit with an install-docs link if missing
- [x] 3.2 Check `ossify-cogents` on `PATH`; if missing, run `uv tool install git+https://github.com/VZhuck/ossify-cogents.git`
- [x] 3.3 Parse a `-Force` switch parameter; if `ossify-cogents.json` exists in the current working directory and `-Force` was not passed, exit non-zero with an error instructing the user to rerun with `-Force`
- [x] 3.4 Fetch `ossify-cogents.json` from this repo's `main` branch and write it to the current working directory (overwriting only if allowed per 3.3)
- [x] 3.5 Run `ossify-cogents install`
- [x] 3.6 Verify it runs correctly via `pwsh scripts/install.ps1` and via the `irm | iex` one-liner in a scratch directory

## 4. README

- [x] 4.1 Remove the "Creating Soft Link Mappings" section (references the deleted `create-links.ps1`)
- [x] 4.2 Add an "Installing Skills" section with Option 1 (recommended): one-line `curl -fsSL <raw-url>/scripts/install.sh | bash` for macOS/Linux and `irm <raw-url>/scripts/install.ps1 | iex` for Windows, plus a note on the `--force`/`-Force` flag
- [x] 4.3 Add Option 2 (manual): instructions to copy the `skills/`, `commands/`, and `rules/` folders directly into the consumer's repository, no script
- [x] 4.4 Verify no remaining reference to `create-links.ps1` or `install.py` anywhere in `README.md`
