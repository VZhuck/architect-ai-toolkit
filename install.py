#!/usr/bin/env python3
"""
install.py — create symbolic links from a target repo into this ai-automation toolkit.

Usage:
    python install.py [--platform {claude,gh,all}] [--target <path>] [--force]
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class ContainerMapping(NamedTuple):
    target_container: str
    source_container: str
    mappings: dict[str, str]  # source_name -> link_name


# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------c

# Symbolic-link mappings applied on every install.
# "shared" is always applied regardless of --platform.
PLATFORM_MAPPINGS: dict[str, ContainerMapping] = {
    "gh": ContainerMapping(
        target_container=".github",
        source_container=".ai-automation",
        mappings={
            "agents": "agents",
            "skills": "skills",
            "instructions": "instructions",
        },
    ),
    "claude": ContainerMapping(
        target_container=".claude",
        source_container=".ai-automation",
        mappings={
            "agents": "agents",
            "skills": "skills",
            "instructions": "rules",
            "instructions.md": "CLAUDE.md",
            "scripts": "scripts",
        },
    ),
    "shared": ContainerMapping(
        target_container=".ai-automation",
        source_container=".ai-automation",
        mappings={
            "scripts": "scripts",
        },
    ),
}

# One-time file copies; never overwritten even with --force.
INIT_FILE_MAPPINGS: dict[str, ContainerMapping] = {
    "gh": ContainerMapping(
        target_container=".github",
        source_container=".ai-automation",
        mappings={
            "instructions.md": "copilot-instructions.md",
        },
    ),
    "claude": ContainerMapping(
        target_container=".",
        source_container=".ai-automation",
        mappings={
            "instructions.md": "CLAUDE.md",
        },
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_existing_link_conflict(
    link_path: Path, source_path: Path, force: bool
) -> bool:
    """
    Handle a path that already exists at *link_path*.

    Returns True  → link is already correct, skip creation.
    Returns False → conflict was removed (caller should create the link).
    Raises        → conflict exists and --force was not given.
    """
    if not link_path.exists() and not link_path.is_symlink():
        return False

    expected_target = source_path.resolve()
    is_symlink = link_path.is_symlink()
    actual_target: Path | None = None

    if is_symlink:
        try:
            actual_target = link_path.resolve()
        except OSError:
            actual_target = None  # broken symlink

    if is_symlink and actual_target == expected_target:
        print(f"Link already correct: {link_path} -> {expected_target}")
        return True

    if not force:
        raise FileExistsError(
            f"Target already exists and differs: {link_path}. "
            "Re-run with --force to replace."
        )

    if link_path.is_dir() and not link_path.is_symlink():
        shutil.rmtree(link_path)
    else:
        link_path.unlink(missing_ok=True)

    print(f"Replaced existing path: {link_path}")
    return False


def _create_symlink(link_path: Path, source_path: Path) -> None:
    """Create a symbolic link, falling back to a directory junction on Windows."""
    try:
        link_path.symlink_to(source_path)
        print(f"Created symbolic link: {link_path} -> {source_path}")
    except OSError as exc:
        # On Windows without Developer Mode or elevated privileges, symlink
        # creation raises PermissionError.  For directories we can fall back
        # to an NTFS junction via os.symlink with target_is_directory=True,
        # but the standard library does not expose junction creation directly.
        # subprocess + mklink /J is the reliable cross-version approach.
        if platform.system() == "Windows" and source_path.is_dir():
            import subprocess  # noqa: PLC0415

            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link_path), str(source_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(
                    f"Created junction (symlink fallback): {link_path} -> {source_path}"
                )
                return
        raise RuntimeError(
            f"Failed to create symbolic link {link_path} -> {source_path}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def create_automation_links(
    target_repo_root: Path,
    source_repo_root: Path,
    mapping: ContainerMapping,
    force: bool,
) -> None:
    target_base = (target_repo_root / mapping.target_container).resolve()
    source_base = (source_repo_root / mapping.source_container).resolve()

    target_base.mkdir(parents=True, exist_ok=True)

    for source_name, link_name in mapping.mappings.items():
        source_path = source_base / source_name
        link_path = target_base / link_name

        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        if _resolve_existing_link_conflict(link_path, source_path, force):
            continue

        _create_symlink(link_path, source_path)


def create_main_platform_file(
    target_repo_root: Path,
    source_repo_root: Path,
    mapping: ContainerMapping,
) -> None:
    target_base = (target_repo_root / mapping.target_container).resolve()
    source_base = (source_repo_root / mapping.source_container).resolve()

    target_base.mkdir(parents=True, exist_ok=True)

    for source_name, target_name in mapping.mappings.items():
        source_file = source_base / source_name
        target_file = target_base / target_name

        if target_file.exists():
            print(f"Main platform file already exists: {target_file}")
            print("  (Not modified, even with --force)")
            continue

        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            continue

        shutil.copy2(source_file, target_file)
        print(f"Created main platform file: {target_file}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install symbolic links from a target repo into the ai-automation toolkit.",
    )
    parser.add_argument(
        "--platform",
        choices=["claude", "gh", "all"],
        default="all",
        help="AI platform to configure (default: all).",
    )
    parser.add_argument(
        "--target",
        default=".",
        metavar="PATH",
        help="Root of the target repository (default: current directory).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing links or paths that differ from the expected target.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    target_repo_root = Path(args.target).resolve()
    source_repo_root = Path(__file__).parent.resolve()

    if not target_repo_root.is_dir():
        sys.exit(f"Error: target path is not a directory: {target_repo_root}")

    selected = args.platform.lower()

    # --- symbolic-link pass ---
    for platform_key, mapping in PLATFORM_MAPPINGS.items():
        if selected not in ("all", platform_key) and platform_key != "shared":
            continue
        create_automation_links(target_repo_root, source_repo_root, mapping, args.force)

    # --- one-time file copy pass ---
    for platform_key, mapping in INIT_FILE_MAPPINGS.items():
        if selected not in ("all", platform_key):
            continue
        create_main_platform_file(target_repo_root, source_repo_root, mapping)


if __name__ == "__main__":
    main()
