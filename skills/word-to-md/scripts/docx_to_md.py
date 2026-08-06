#!/usr/bin/env python3
"""Convert a Word document into rule-compliant markdown section files.

Stage A extracts the docx to raw markdown + media via pandoc into an
intermediate ai-workflow/word-to-md/<doc-stem>/ folder. Stage B normalizes
that raw markdown deterministically (drop pandoc's auto-TOC, convert
non-merged HTML tables to markdown, split by H1, generate an index) per
rules/sad-sections.instructions.md, and writes the result to --target-folder.

Usage:
  uv run python skills/word-to-md/scripts/docx_to_md.py --source path/to/file.docx
  uv run python skills/word-to-md/scripts/docx_to_md.py --source path/to/file.docx --target-folder sad
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sad_structure import build_index, build_section_files, split_cover_and_body
from table_normalizer import normalize_tables


def extract_docx(source: Path, workdir: Path) -> Path:
    """Run pandoc to extract raw markdown + media, returning the raw.md path."""
    workdir.mkdir(parents=True, exist_ok=True)
    rel_source = os.path.relpath(source, workdir)

    cmd = [
        "pandoc",
        "-t",
        "markdown",
        "--extract-media=media",
        "--columns=1000",
        "--to=markdown-simple_tables-multiline_tables-grid_tables",
        rel_source,
        "-o",
        "raw.md",
    ]
    try:
        subprocess.run(cmd, cwd=workdir, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pandoc is not installed or not on PATH - install pandoc to use this skill"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pandoc conversion failed: {exc.stderr}") from exc

    return workdir / "raw.md"


def convert(source: Path, target_folder: Path, workdir: Path | None = None) -> Path:
    source = Path(source).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"source document not found: {source}")

    if workdir is None:
        workdir = Path("ai-workflow") / "word-to-md" / source.stem
    workdir = Path(workdir)

    raw_md_path = extract_docx(source, workdir)
    raw_text = raw_md_path.read_text(encoding="utf-8")

    cover_text, body_text = split_cover_and_body(raw_text)
    body_text = normalize_tables(body_text)

    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)

    section_files = build_section_files(body_text)
    for filename, _heading_text, content in section_files:
        (target_folder / filename).write_text(content, encoding="utf-8")

    index_content = build_index(cover_text, section_files)
    (target_folder / "00.Index.md").write_text(index_content, encoding="utf-8")

    media_src = workdir / "media"
    if media_src.exists():
        media_dst = target_folder / "media"
        if media_dst.exists():
            shutil.rmtree(media_dst)
        shutil.copytree(media_src, media_dst)

    return target_folder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Word document into rule-compliant markdown section files."
    )
    parser.add_argument("--source", required=True, help="Path to the source .docx file.")
    parser.add_argument(
        "--target-folder",
        default="sad",
        help="Output folder for generated section files. Default: sad",
    )
    parser.add_argument(
        "--workdir",
        default=None,
        help=(
            "Intermediate folder for pandoc's raw extraction. "
            "Default: ai-workflow/word-to-md/<source-doc-name>"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = convert(
        Path(args.source),
        Path(args.target_folder),
        Path(args.workdir) if args.workdir else None,
    )
    print(f"Wrote rule-compliant section files to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
