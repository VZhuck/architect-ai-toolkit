#!/usr/bin/env python3
"""Resolve inputs for the summarize-meeting-decisions skill.

Two independent resolutions, both falling back to a repo-root .env file
using plain key=value parsing (no python-dotenv), matching
skills/md-to-word/scripts/md_to_word.py's resolve_template style:

- meeting note: explicit --meeting-file path, else list the files found in
  .env's MEETING_NOTES_FOLDER for the caller to choose from.
- ADL file: explicit --adl-path, else .env's ADL_PATH.

Usage:
  uv run python skills/summarize-meeting-decisions/scripts/resolve_paths.py
  uv run python skills/summarize-meeting-decisions/scripts/resolve_paths.py --meeting-file notes/standup.md
  uv run python skills/summarize-meeting-decisions/scripts/resolve_paths.py --adl-path sad/07.Decision-Acceptance-Board.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ENV_KEY_RE_TEMPLATE = r"^\s*{key}\s*=\s*(.+?)\s*$"


def _read_env_key(repo_root: Path, key: str) -> str | None:
    """Read a single key=value entry from a .env file at the repo root, if present."""
    env_path = repo_root / ".env"
    if not env_path.exists():
        return None

    pattern = re.compile(_ENV_KEY_RE_TEMPLATE.format(key=re.escape(key)), re.MULTILINE)
    match = pattern.search(env_path.read_text(encoding="utf-8"))
    if not match:
        return None

    value = match.group(1).strip().strip('"').strip("'")
    return value or None


def _resolve_relative(path_str: str, repo_root: Path) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path


def resolve_meeting_input(
    meeting_file: str | None, repo_root: Path | None = None
) -> Path | list[Path]:
    """Resolve the meeting note input.

    Returns a single resolved Path when meeting_file is given (raises
    FileNotFoundError if it doesn't exist). Otherwise returns the sorted list
    of files found in .env's MEETING_NOTES_FOLDER, for the caller to choose
    from - raises FileNotFoundError if that key is unset or the folder
    doesn't exist.
    """
    if repo_root is None:
        repo_root = Path.cwd()

    if meeting_file:
        meeting_path = _resolve_relative(meeting_file, repo_root)
        if not meeting_path.is_file():
            raise FileNotFoundError(f"meetingFilePath not found: {meeting_path}")
        return meeting_path

    folder_value = _read_env_key(repo_root, "MEETING_NOTES_FOLDER")
    if folder_value is None:
        raise FileNotFoundError(
            "no meetingFilePath given and .env has no MEETING_NOTES_FOLDER value"
        )

    folder_path = _resolve_relative(folder_value, repo_root)
    if not folder_path.is_dir():
        raise FileNotFoundError(
            f"MEETING_NOTES_FOLDER resolved but is not a directory: {folder_path}"
        )

    candidates = sorted(p for p in folder_path.iterdir() if p.is_file())
    if not candidates:
        raise FileNotFoundError(f"MEETING_NOTES_FOLDER has no files: {folder_path}")

    return candidates


def resolve_adl_path(adl_path: str | None, repo_root: Path | None = None) -> Path:
    """Resolve the ADL file path: explicit arg, else .env's ADL_PATH.

    Raises FileNotFoundError if neither resolves. Does not require the
    resolved path to exist on disk yet - the caller creates it on first write.
    """
    if repo_root is None:
        repo_root = Path.cwd()

    source = "explicit --adl-path argument"
    if not adl_path:
        adl_path = _read_env_key(repo_root, "ADL_PATH")
        source = ".env ADL_PATH"

    if not adl_path:
        raise FileNotFoundError("no adlPath given and .env has no ADL_PATH value")

    resolved = _resolve_relative(adl_path, repo_root)
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve meeting note and ADL paths for summarize-meeting-decisions."
    )
    parser.add_argument(
        "--meeting-file",
        default=None,
        help="Path to a specific meeting note. Default: list .env's MEETING_NOTES_FOLDER contents.",
    )
    parser.add_argument(
        "--adl-path",
        default=None,
        help="Path to the ADL file. Default: .env's ADL_PATH.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    meeting_result = resolve_meeting_input(args.meeting_file)
    if isinstance(meeting_result, list):
        print("Candidate meeting notes (no meetingFilePath given):")
        for candidate in meeting_result:
            print(f"  {candidate}")
    else:
        print(f"Meeting note: {meeting_result}")

    adl_path = resolve_adl_path(args.adl_path)
    print(f"ADL path: {adl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
