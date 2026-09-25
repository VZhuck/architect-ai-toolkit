#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Resolve archy-nfr-miner source paths and match them against existing runs.

A run's identity is its resolved file set, not a session id or folder name.
This script:

- resolves every --path (dir: recursive, file, glob mask) to a sorted,
  de-duplicated list of root-relative files with a supported extension
- always excludes the working dir base, the taxonomy dir, and hidden folders
- hashes each file (sha256)
- compares the set with every <working-dir-base>/*/state.yaml and classifies
  the match: identical | superset | subset | partial (runs with no overlap
  are left out), reporting stale (changed) files and the run's position

With --list-runs (and no --path) it lists unfinished runs instead.

Prints one JSON object to stdout. Exits 2, still printing the JSON report,
when --path resolves to no supported file.

Usage:
  uv run skills/archy-nfr-miner/scripts/resolve_run.py --path docs/payments/
  uv run skills/archy-nfr-miner/scripts/resolve_run.py --path "docs/*.md" --path specs/sec.pdf
  uv run skills/archy-nfr-miner/scripts/resolve_run.py --list-runs
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

SUPPORTED_EXTENSIONS = {".md", ".mdx", ".docx", ".pdf"}
IGNORED_DIRS = {"__pycache__", "node_modules"}
DEFAULT_WORKING_DIR_BASE = "ai-workflow/nfr-state"
DEFAULT_TAXONOMY_DIR = "ai-workflow/nfr-taxonomy"
STATE_FILE = "state.yaml"
FINISHED_STAGE = "finished"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _has_hidden_or_ignored_dir(path: Path, root: Path) -> bool:
    rel = Path(_rel(path, root))
    return any(part.startswith(".") or part in IGNORED_DIRS for part in rel.parts[:-1])


def _expand(arg: str, root: Path) -> list[Path]:
    """Expand one --path value to candidate files (unfiltered)."""
    candidate = Path(arg).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_dir():
        return [p for p in candidate.rglob("*") if p.is_file()]
    if candidate.is_file():
        return [candidate]
    if glob.has_magic(arg):
        pattern = arg if Path(arg).is_absolute() else str(root / arg)
        return [Path(p) for p in glob.glob(pattern, recursive=True) if Path(p).is_file()]
    return []


def resolve_files(
    path_args: list[str], root: Path, working_dir_base: Path, taxonomy_dir: Path
) -> dict:
    """Resolve path arguments to the supported, non-excluded file set."""
    root = root.resolve()
    working_dir_base = working_dir_base.resolve()
    taxonomy_dir = taxonomy_dir.resolve()

    files: dict[str, Path] = {}
    excluded: set[str] = set()
    unsupported: set[str] = set()
    unmatched: list[str] = []

    for arg in path_args:
        found = _expand(arg, root)
        if not found:
            unmatched.append(arg)
        for path in found:
            path = path.resolve()
            rel = _rel(path, root)
            if (
                _is_within(path, working_dir_base)
                or _is_within(path, taxonomy_dir)
                or _has_hidden_or_ignored_dir(path, root)
            ):
                excluded.add(rel)
            elif path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                unsupported.add(rel)
            else:
                files[rel] = path

    return {
        "files": [
            {"path": rel, "sha256": sha256_of(files[rel]), "ext": files[rel].suffix.lower()}
            for rel in sorted(files)
        ],
        "excluded": sorted(excluded),
        "unsupported": sorted(unsupported),
        "unmatched": unmatched,
    }


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def suggest_run_id(file_paths: list[str], now: datetime | None = None) -> str:
    """<common-parent-slug>-<yyyymmdd-hhmm>; 'repo' when files share only the root."""
    now = now or datetime.now()
    parents = [Path(p).parent.as_posix() for p in file_paths] or ["."]
    common = os.path.commonpath(parents) if len(parents) > 1 else parents[0]
    slug = _slug(common) or "repo"
    return f"{slug}-{now.strftime('%Y%m%d-%H%M')}"


def _load_state(state_file: Path) -> dict | None:
    try:
        data = yaml.safe_load(state_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _run_files(state: dict) -> dict[str, dict]:
    entries = state.get("files_4_review") or []
    result = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("path"):
            result[str(entry["path"])] = entry
        elif isinstance(entry, str):
            result[entry] = {"path": entry}
    return result


def load_runs(working_dir_base: Path) -> list[tuple[str, dict]]:
    if not working_dir_base.is_dir():
        return []
    runs = []
    for run_dir in sorted(p for p in working_dir_base.iterdir() if p.is_dir()):
        state = _load_state(run_dir / STATE_FILE)
        if state is not None:
            runs.append((run_dir.name, state))
    return runs


def _run_summary(run_id: str, state: dict, run_files: dict[str, dict]) -> dict:
    statuses = {path: entry.get("status", "pending") for path, entry in run_files.items()}
    return {
        "run_id": run_id,
        "path_args": state.get("path_args") or [],
        "active_skill": state.get("active_skill"),
        "active_stage": state.get("active_stage"),
        "active_step": state.get("active_step"),
        "finished": state.get("active_stage") == FINISHED_STAGE,
        "update_on": state.get("update_on"),
        "file_status": statuses,
    }


def classify(new_paths: set[str], run_paths: set[str]) -> str:
    if not new_paths or not run_paths:
        return "none"
    if new_paths == run_paths:
        return "identical"
    if run_paths < new_paths:
        return "superset"
    if new_paths < run_paths:
        return "subset"
    if new_paths & run_paths:
        return "partial"
    return "none"


MATCH_ORDER = {"identical": 0, "superset": 1, "subset": 2, "partial": 3}


def match_runs(files: list[dict], working_dir_base: Path) -> list[dict]:
    """Existing runs that overlap the resolved file set, best match first."""
    new_hashes = {f["path"]: f["sha256"] for f in files}
    new_paths = set(new_hashes)
    matches = []
    for run_id, state in load_runs(working_dir_base):
        run_files = _run_files(state)
        run_paths = set(run_files)
        match = classify(new_paths, run_paths)
        if match == "none":
            continue
        stale = sorted(
            path
            for path in new_paths & run_paths
            if run_files[path].get("sha256") and run_files[path]["sha256"] != new_hashes[path]
        )
        summary = _run_summary(run_id, state, run_files)
        summary.update(
            {
                "match": match,
                "added": sorted(new_paths - run_paths),
                "missing": sorted(run_paths - new_paths),
                "stale": stale,
            }
        )
        matches.append(summary)
    matches.sort(key=lambda m: (MATCH_ORDER[m["match"]], m["finished"], m["run_id"]))
    return matches


def list_unfinished_runs(working_dir_base: Path) -> list[dict]:
    runs = []
    for run_id, state in load_runs(working_dir_base):
        summary = _run_summary(run_id, state, _run_files(state))
        if not summary["finished"]:
            runs.append(summary)
    return runs


def _resolve_relative(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve archy-nfr-miner sources and match them against existing runs."
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Dir, file, or glob mask. Repeat for a list.",
    )
    parser.add_argument(
        "--working-dir-base",
        default=DEFAULT_WORKING_DIR_BASE,
        help=f"Run folders live here. Default: {DEFAULT_WORKING_DIR_BASE}",
    )
    parser.add_argument(
        "--taxonomy-dir",
        default=DEFAULT_TAXONOMY_DIR,
        help=f"Excluded from mining. Default: {DEFAULT_TAXONOMY_DIR}",
    )
    parser.add_argument("--run", default=None, help="Explicit run folder name.")
    parser.add_argument("--root", default=".", help="Project root. Default: cwd.")
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List unfinished runs instead of resolving paths.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    working_dir_base = _resolve_relative(args.working_dir_base, root)
    taxonomy_dir = _resolve_relative(args.taxonomy_dir, root)

    if args.list_runs or not args.path:
        result = {
            "working_dir_base": _rel(working_dir_base.resolve(), root),
            "unfinished_runs": list_unfinished_runs(working_dir_base),
        }
        print(json.dumps(result, indent=2, default=str))
        return 0

    result = resolve_files(args.path, root, working_dir_base, taxonomy_dir)
    run_id = args.run or suggest_run_id([f["path"] for f in result["files"]])
    result.update(
        {
            "root": root.as_posix(),
            "working_dir_base": _rel(working_dir_base.resolve(), root),
            "path_args": args.path,
            "suggested_run_id": run_id,
            "run_exists": (working_dir_base / run_id).exists(),
            "runs": match_runs(result["files"], working_dir_base),
        }
    )
    if not result["files"]:
        result["error"] = "no supported files resolved (.md, .mdx, .docx, .pdf)"
        print(json.dumps(result, indent=2, default=str))
        return 2

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
