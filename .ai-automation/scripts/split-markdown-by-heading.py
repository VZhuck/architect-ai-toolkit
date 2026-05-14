#!/usr/bin/env python3
"""Split a markdown file into multiple files by heading using LangChain.

Usage:
  python .ai-automation/scripts/split-markdown-by-heading.py --source-md ./sad/source.md
  python .ai-automation/scripts/split-markdown-by-heading.py --source-md ./sad/source.md --target-folder ./sad/sections
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Sequence, Tuple

from langchain_text_splitters.markdown import ExperimentalMarkdownSyntaxTextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split source markdown by headings and write files to a target folder."
    )
    parser.add_argument(
        "--source-md",
        required=True,
        help="Path to a single source markdown file.",
    )
    parser.add_argument(
        "--target-folder",
        required=False,
        default=None,
        help=(
            "Output folder for generated files. "
            "Default: ./<source-file-name-without-extension>"
        ),
    )
    parser.add_argument(
        "--headers",
        nargs="*",
        default=["#"],
        help="Heading levels to split on. Default: #",
    )
    return parser.parse_args()


def sanitize_filename(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "", cleaned)
    cleaned = cleaned.strip("-._")
    return cleaned or "section"


def build_headers_to_split_on(headers: Sequence[str]) -> List[Tuple[str, str]]:
    # Metadata keys become h1/h2/h3, etc., matching the heading depth.
    return [(marker, f"h{len(marker)}") for marker in headers]


def build_output_name(index: int, doc_metadata: dict) -> str:
    h1 = doc_metadata.get("h1")
    h2 = doc_metadata.get("h2")
    h3 = doc_metadata.get("h3")

    if h3:
        label = f"{h1 or ''}-{h2 or ''}-{h3}"
    elif h2:
        label = f"{h1 or ''}-{h2}"
    elif h1:
        label = str(h1)
    elif index == 0:
        label = label = f"Index"
    else:   
        label = f"section-{index:02d}"

    return f"{index:02d}.{sanitize_filename(label)}.md"


def main() -> int:
    args = parse_args()

    source_md = Path(args.source_md).expanduser()
    if not source_md.exists() or source_md.suffix.lower() != ".md":
        raise FileNotFoundError(
            f"source markdown not found or not a .md file: {source_md}"
        )

    target_folder = (
        Path(args.target_folder).expanduser()
        if args.target_folder
        else Path(".") / source_md.stem
    )
    target_folder.mkdir(parents=True, exist_ok=True)

    markdown_text = source_md.read_text(encoding="utf-8")

    headers_to_split_on = build_headers_to_split_on(args.headers)
    splitter = ExperimentalMarkdownSyntaxTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    docs = splitter.split_text(markdown_text)

    if not docs:
        out_file = target_folder / "00-full-document.md"
        out_file.write_text(markdown_text, encoding="utf-8")
        print(f"No split sections found. Wrote full document: {out_file}")
        return 0

    for idx, doc in enumerate(docs, start=0):
        output_name = build_output_name(idx, doc.metadata)
        output_path = target_folder / output_name

        # ExperimentalMarkdownSyntaxTextSplitter preserves original formatting
        # and includes headers when strip_headers=False
        content = doc.page_content
        if content and not content.endswith("\n"):
            content += "\n"

        output_path.write_text(content, encoding="utf-8")
        print(f"Wrote: {output_path}")

    print(f"Created {len(docs)} file(s) in {target_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
