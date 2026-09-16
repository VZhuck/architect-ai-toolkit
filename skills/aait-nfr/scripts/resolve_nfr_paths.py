#!/usr/bin/env python3
"""Resolve inputs for the aait-nfr skill.

Two independent resolutions, both falling back to a repo-root .env file using
plain key=value parsing (no python-dotenv), matching
skills/summarize-meeting-decisions/scripts/resolve_paths.py:

- sources: explicit --path (file or directory), expanded to the text-bearing
  files underneath it.
- target document: explicit --nfr-path, else .env's NFR_PATH, else the list of
  markdown documents in sad/ for the caller to choose from, plus a proposed
  SAD-compliant name for a new document.

The draft and trace paths are always derived from the resolved target document
and always live under ai-workflow/nfr/ - they are never passed in, and never
land in sad/, where md-to-word would sweep them into the Word deliverable.

Usage:
  uv run python skills/aait-nfr/scripts/resolve_nfr_paths.py --path docs/rfp
  uv run python skills/aait-nfr/scripts/resolve_nfr_paths.py --path docs/rfp --nfr-path sad/08.Non-Functional-Requirements.md
  uv run python skills/aait-nfr/scripts/resolve_nfr_paths.py --nfr-path sad/08.Non-Functional-Requirements.md --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ENV_KEY_RE_TEMPLATE = r"^\s*{key}\s*=\s*(.+?)\s*$"

# Text-bearing source extensions worth mining. Anything else is skipped.
SOURCE_EXTENSIONS = {".md", ".txt", ".docx", ".pdf", ".adoc", ".csv"}

# Directory names never worth recursing into.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

# Above this many candidate files, the skill asks which subset matters rather
# than dispatching a mining agent per file.
MANY_SOURCES_THRESHOLD = 30

# Where working files live. Gitignored, machine-local, never inside sad/.
WORKING_DIR = Path("ai-workflow") / "nfr"

# Default folder searched for an existing target document when NFR_PATH is unset.
SAD_DIR = Path("sad")

DEFAULT_NEW_DOC_TITLE = "Non-Functional-Requirements"


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


def collect_sources(path_str: str, repo_root: Path | None = None) -> list[Path]:
    """Expand a file or directory into the text-bearing files worth mining.

    Raises FileNotFoundError if the path does not exist, or if a directory
    holds no candidate files.
    """
    if repo_root is None:
        repo_root = Path.cwd()

    source = _resolve_relative(path_str, repo_root)

    if source.is_file():
        if source.suffix.lower() not in SOURCE_EXTENSIONS:
            raise ValueError(
                f"path is not a text-bearing source file ({source.suffix}): {source}"
            )
        return [source]

    if not source.is_dir():
        raise FileNotFoundError(f"path not found: {source}")

    candidates: list[Path] = []
    for entry in sorted(source.rglob("*")):
        if not entry.is_file():
            continue
        if any(part in SKIP_DIRS for part in entry.parts):
            continue
        if entry.suffix.lower() in SOURCE_EXTENSIONS:
            candidates.append(entry)

    if not candidates:
        raise FileNotFoundError(f"no text-bearing source files under: {source}")

    return candidates


def propose_new_doc_name(sad_dir: Path, title: str = DEFAULT_NEW_DOC_TITLE) -> str:
    """Propose a SAD-compliant filename for a new document in sad/.

    Follows rules/sad-sections.instructions.md: a zero-padded section-number
    prefix continuing the existing sequence, then a Title-Case-Hyphenated title.
    """
    highest = 0
    width = 2
    if sad_dir.is_dir():
        for entry in sad_dir.iterdir():
            match = re.match(r"^(\d+)(?:\.\d+)?\.", entry.name)
            if match:
                highest = max(highest, int(match.group(1)))
                width = max(width, len(match.group(1)))

    return f"{highest + 1:0{width}d}.{title}.md"


def resolve_nfr_path(
    nfr_path: str | None, repo_root: Path | None = None
) -> tuple[Path | None, dict]:
    """Resolve the target NFR document: explicit arg, else .env NFR_PATH, else ask.

    Returns (resolved_path, info). resolved_path is None when the caller must
    ask the user to choose - info then carries the candidate documents found in
    sad/ and a proposed name for a new document. The resolved path is not
    required to exist on disk; publish creates it on first write.
    """
    if repo_root is None:
        repo_root = Path.cwd()

    if nfr_path:
        return _resolve_relative(nfr_path, repo_root), {"source": "explicit --nfr-path"}

    from_env = _read_env_key(repo_root, "NFR_PATH")
    if from_env:
        return _resolve_relative(from_env, repo_root), {"source": ".env NFR_PATH"}

    sad_dir = repo_root / SAD_DIR
    existing = (
        sorted(p for p in sad_dir.glob("*.md") if p.is_file()) if sad_dir.is_dir() else []
    )

    return None, {
        "source": "needs user choice",
        "sad_dir": sad_dir,
        "existing": existing,
        "proposed_new": sad_dir / propose_new_doc_name(sad_dir),
        "sad_dir_usable": bool(existing),
    }


def derive_working_paths(nfr_path: Path, repo_root: Path | None = None) -> dict[str, Path]:
    """Derive the draft and trace paths from the resolved target document.

    Both always live under ai-workflow/nfr/ regardless of where the target
    document lives, so md-to-word never sweeps them into the SAD deliverable.
    """
    if repo_root is None:
        repo_root = Path.cwd()

    stem = nfr_path.stem
    working = repo_root / WORKING_DIR
    return {
        "draft": working / f"{stem}.draft.md",
        "trace": working / f"{stem}.trace.md",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve source and NFR document paths for the aait-nfr skill."
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Directory or file to analyze. Omit to resolve only the target document.",
    )
    parser.add_argument(
        "--nfr-path",
        default=None,
        help="Target NFR document. Default: .env's NFR_PATH, else choose from sad/.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON instead of text."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()

    sources: list[Path] = []
    if args.path:
        sources = collect_sources(args.path, repo_root)

    nfr_path, info = resolve_nfr_path(args.nfr_path, repo_root)
    working = derive_working_paths(nfr_path, repo_root) if nfr_path else {}

    if args.json:
        payload = {
            "sources": [str(p) for p in sources],
            "source_count": len(sources),
            "many_sources": len(sources) > MANY_SOURCES_THRESHOLD,
            "nfr_path": str(nfr_path) if nfr_path else None,
            "nfr_path_source": info["source"],
            "nfr_path_exists": nfr_path.is_file() if nfr_path else False,
            "draft": str(working["draft"]) if working else None,
            "trace": str(working["trace"]) if working else None,
        }
        if nfr_path is None:
            payload["existing_documents"] = [str(p) for p in info["existing"]]
            payload["proposed_new"] = str(info["proposed_new"])
            payload["sad_dir_usable"] = info["sad_dir_usable"]
        print(json.dumps(payload, indent=2))
        return 0

    if args.path:
        print(f"Sources ({len(sources)}):")
        for candidate in sources:
            print(f"  {candidate}")
        if len(sources) > MANY_SOURCES_THRESHOLD:
            print(
                f"\n  More than {MANY_SOURCES_THRESHOLD} candidate files - ask the user "
                "which subset matters before dispatching mining agents."
            )

    if nfr_path is not None:
        print(f"\nNFR document: {nfr_path}  ({info['source']})")
        print(f"  exists: {nfr_path.is_file()}")
        print(f"Draft: {working['draft']}")
        print(f"Trace: {working['trace']}")
        return 0

    print("\nNFR document: needs user choice (no --nfr-path, no .env NFR_PATH)")
    if info["existing"]:
        print(f"  Existing documents in {info['sad_dir']}:")
        for candidate in info["existing"]:
            print(f"    {candidate}")
    else:
        print(
            f"  {info['sad_dir']} does not exist or holds no markdown documents - "
            "ask the user for the target document path directly."
        )
    print(f"  Proposed name for a new document: {info['proposed_new']}")
    print(
        "\n  Ask the user to select an existing document or confirm/adjust the "
        "proposed new name. Do not guess."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
