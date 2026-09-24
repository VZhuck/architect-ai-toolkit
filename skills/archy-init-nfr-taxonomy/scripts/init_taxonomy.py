#!/usr/bin/env python3
"""Materialize the archy-init-nfr-taxonomy skill's taxonomy/ into a project.

Copies every non-hidden file under the skill's taxonomy/ folder into the
target (default ai-workflow/nfr-taxonomy, resolved against the cwd), preserving
relative subpaths. Version-aware, driven by SKILL.md's `metadata.version` and
a `<target>/.taxonomy-version` marker:

- marker equals skill version (no --force): nothing is written ("up-to-date")
- no marker: every file is written ("initialized")
- different version or --force: every file is overwritten ("updated")

Source paths are resolved from this script's location, not the cwd, so it
works both in this repo and from an installed skill directory. Prints a JSON
result to stdout.

Usage:
  uv run python skills/archy-init-nfr-taxonomy/scripts/init_taxonomy.py
  uv run python skills/archy-init-nfr-taxonomy/scripts/init_taxonomy.py --target docs/taxonomy --force
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = SKILL_DIR / "taxonomy"
DEFAULT_SKILL_MD = SKILL_DIR / "SKILL.md"
DEFAULT_TARGET = "ai-workflow/nfr-taxonomy"
MARKER_NAME = ".taxonomy-version"
IGNORED_DIRS = {"__pycache__"}

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_METADATA_VERSION_RE = re.compile(
    r"^metadata:[ \t]*\n(?:[ \t]+.*\n)*?[ \t]+version:[ \t]*(.+?)[ \t]*$", re.MULTILINE
)


class TaxonomyError(Exception):
    """Raised when the skill's taxonomy or version cannot be resolved."""


def read_skill_version(skill_md: Path) -> str:
    """Read `metadata.version` from a SKILL.md frontmatter block."""
    if not skill_md.is_file():
        raise TaxonomyError(f"SKILL.md not found: {skill_md}")

    frontmatter = _FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
    if not frontmatter:
        raise TaxonomyError(f"SKILL.md has no frontmatter: {skill_md}")

    match = _METADATA_VERSION_RE.search(frontmatter.group(1) + "\n")
    version = match.group(1).strip().strip('"').strip("'") if match else ""
    if not version:
        raise TaxonomyError(f"SKILL.md frontmatter has no metadata.version: {skill_md}")
    return version


def list_taxonomy_files(source: Path) -> list[Path]:
    """Return sorted relative paths of non-hidden taxonomy files under source."""
    if not source.is_dir():
        raise TaxonomyError(f"taxonomy folder not found: {source}")

    files = sorted(
        path.relative_to(source)
        for path in source.rglob("*")
        if path.is_file()
        and not any(
            part.startswith(".") or part in IGNORED_DIRS
            for part in path.relative_to(source).parts
        )
    )
    if not files:
        raise TaxonomyError(f"taxonomy folder has no files: {source}")
    return files


def _read_marker(target: Path) -> str | None:
    marker = target / MARKER_NAME
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8").strip() or None


def init_taxonomy(
    target: Path,
    force: bool = False,
    source: Path | None = None,
    skill_md: Path | None = None,
) -> dict:
    """Copy taxonomy files into target according to the version policy.

    Validates the source and version before writing anything.
    """
    source = (source or DEFAULT_SOURCE).resolve()
    skill_md = skill_md or DEFAULT_SKILL_MD

    version = read_skill_version(skill_md)
    files = list_taxonomy_files(source)
    previous_version = _read_marker(target)

    result = {
        "version": version,
        "previous_version": previous_version,
        "status": "",
        "source": str(source),
        "target": str(target),
        "copied": [],
        "skipped": [],
        "overwritten": [],
    }

    if previous_version == version and not force:
        result["status"] = "up-to-date"
        result["skipped"] = [rel.as_posix() for rel in files]
        return result

    result["status"] = "initialized" if previous_version is None else "updated"
    for rel in files:
        destination = target / rel
        bucket = "overwritten" if destination.exists() else "copied"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, destination)
        result[bucket].append(rel.as_posix())

    (target / MARKER_NAME).write_text(version + "\n", encoding="utf-8")
    return result


def _resolve_relative(path_str: str, repo_root: Path) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy the archy-init-nfr-taxonomy skill's taxonomy files into the project."
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help=f"Destination folder. Default: {DEFAULT_TARGET} (relative to cwd).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recopy every taxonomy file even when the installed version matches.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = _resolve_relative(args.target, Path.cwd())

    try:
        result = init_taxonomy(target, force=args.force)
    except TaxonomyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
