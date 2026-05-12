#!/usr/bin/env python3
"""Copy a source folder into a target base directory.

Example:
  sourceDir = /source/folder-to-be-copied
  targetBaseDir = /target

Result:
    /target/folder-to-be-copied
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy source folder into target base directory, preserving "
            "the source folder name."
        )
    )
    parser.add_argument(
        "--source-dir",
        "--sourceDir",
        "--source-folder",
        "--sourceFolder",
        required=True,
        help="Path to the source folder to copy.",
    )
    parser.add_argument(
        "--target-base-dir",
        "--targetBaseDir",
        "--target-folder",
        "--targetFolder",
        required=True,
        help="Path to the target base directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If set, remove existing destination folder before copying.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_dir = Path(args.source_dir).expanduser().resolve()
    target_base_dir = Path(args.target_base_dir).expanduser().resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Source directory does not exist or is not a directory: {source_dir}")
        return 1

    if source_dir == target_base_dir:
        print("Source directory and target base directory cannot be the same path.")
        return 1

    target_base_dir.mkdir(parents=True, exist_ok=True)
    destination_dir = target_base_dir / source_dir.name

    if destination_dir.exists():
        if not args.overwrite:
            print(
                "Destination already exists. Use --overwrite to replace it: "
                f"{destination_dir}"
            )
            return 1
        shutil.rmtree(destination_dir)

    shutil.copytree(source_dir, destination_dir)

    # Ensure the required final path exists: <target-base-dir>/<source-folder-name>
    if not destination_dir.exists() or not destination_dir.is_dir():
        print(f"Copy failed, destination does not exist: {destination_dir}")
        return 1

    print(f"Copied: {source_dir}")
    print(f"To:     {destination_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
