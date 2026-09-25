#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pypandoc-binary>=1.13", "pdfplumber>=0.11", "pyyaml>=6.0"]
# ///
"""Convert archy-nfr-miner binary sources into one markdown file each.

For every --file (root-relative):

- .md / .mdx  -> mined in place, nothing written ("in-place")
- .docx       -> pandoc gfm, --wrap=none (one paragraph per line, stable line
                 refs), --track-changes=accept, no media extraction
- .pdf        -> pdfplumber, page by page: "<!-- page N -->" marker, then text
                 and tables in top-to-bottom order; table regions are cut out
                 of the text so nothing is mined twice

Output goes to <run-dir>/sources/<rel-path>.md (e.g. sources/docs/SAD.docx.md).
A file whose sha256 matches the one recorded in <run-dir>/state.yaml, and whose
output still exists, is not converted again ("unchanged"). A file that cannot
be converted, or that has no extractable text, is reported "failed" with a
reason; the other files are still converted.

Prints one JSON object to stdout.

Usage:
  uv run skills/archy-nfr-miner/scripts/normalize_sources.py \
      --run-dir ai-workflow/nfr-state/docs-20260924-1402 \
      --file docs/SAD.docx --file docs/notes.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import yaml

SOURCES_DIR = "sources"
STATE_FILE = "state.yaml"
IN_PLACE_EXTENSIONS = {".md", ".mdx"}
PANDOC_ARGS = ["--wrap=none", "--track-changes=accept"]


class ConversionError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_path(run_dir: Path, rel: str) -> Path:
    return run_dir / SOURCES_DIR / f"{rel}.md"


# --- docx ------------------------------------------------------------------------


def count_docx_images(source: Path) -> int:
    try:
        with zipfile.ZipFile(source) as archive:
            return sum(1 for name in archive.namelist() if name.startswith("word/media/"))
    except zipfile.BadZipFile as exc:
        raise ConversionError(f"not a valid .docx archive: {exc}") from exc


def convert_docx(source: Path) -> tuple[str, int]:
    import pypandoc

    images = count_docx_images(source)
    try:
        text = pypandoc.convert_file(str(source), "gfm", format="docx", extra_args=PANDOC_ARGS)
    except (RuntimeError, OSError) as exc:
        raise ConversionError(f"pandoc conversion failed: {exc}") from exc
    if not text.strip():
        raise ConversionError("no extractable text")
    return text.replace("\r\n", "\n"), images


# --- pdf -------------------------------------------------------------------------


def _cell(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>").strip()


def table_to_markdown(rows: list[list]) -> str:
    rows = [row for row in rows if row and any(cell not in (None, "") for cell in row)]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [[_cell(c) for c in row] + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(padded[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(row) + " |" for row in padded[1:]]
    return "\n".join(lines)


def _region_text(page, top: float, bottom: float) -> str:
    if bottom - top <= 0:
        return ""
    region = page.within_bbox((0, top, page.width, bottom))
    return (region.extract_text() or "").strip()


def convert_pdf(source: Path) -> tuple[str, int]:
    import pdfplumber

    blocks: list[str] = []
    images = 0
    has_text = False
    try:
        with pdfplumber.open(source) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                blocks.append(f"<!-- page {number} -->")
                images += len(page.images)
                tables = sorted(page.find_tables(), key=lambda t: t.bbox[1])
                cursor = 0.0
                for table in tables:
                    x0, top, x1, bottom = table.bbox
                    text = _region_text(page, cursor, top)
                    if text:
                        blocks.append(text)
                        has_text = True
                    markdown = table_to_markdown(table.extract())
                    if markdown:
                        blocks.append(markdown)
                        has_text = True
                    cursor = max(cursor, bottom)
                text = _region_text(page, cursor, page.height)
                if text:
                    blocks.append(text)
                    has_text = True
    except ConversionError:
        raise
    except Exception as exc:  # pdfminer raises many unrelated types on bad input
        raise ConversionError(f"pdf conversion failed: {exc}") from exc
    if not has_text:
        raise ConversionError("no extractable text (scanned? OCR is out of scope)")
    return "\n\n".join(blocks) + "\n", images


CONVERTERS = {".docx": convert_docx, ".pdf": convert_pdf}


def count_images(source: Path, ext: str) -> int:
    """Image count without converting; 0 when the file cannot be read."""
    try:
        if ext == ".docx":
            return count_docx_images(source)
        if ext == ".pdf":
            import pdfplumber

            with pdfplumber.open(source) as pdf:
                return sum(len(page.images) for page in pdf.pages)
    except Exception:  # a corrupt file already fails conversion with a reason
        return 0
    return 0


# --- orchestration -----------------------------------------------------------------


def recorded_hashes(run_dir: Path) -> dict[str, str]:
    state_file = run_dir / STATE_FILE
    if not state_file.is_file():
        return {}
    try:
        state = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    hashes = {}
    for entry in state.get("files_4_review") or []:
        if isinstance(entry, dict) and entry.get("path") and entry.get("sha256"):
            hashes[str(entry["path"])] = str(entry["sha256"])
    return hashes


def normalize_file(rel: str, root: Path, run_dir: Path, recorded: dict[str, str], force: bool = False) -> dict:
    source = root / rel
    ext = source.suffix.lower()
    result = {"path": rel, "status": "", "normalized": "", "sha256": "", "reason": "", "images": 0}

    if not source.is_file():
        result.update(status="failed", reason="source file not found")
        return result
    result["sha256"] = sha256_of(source)

    if ext in IN_PLACE_EXTENSIONS:
        result["status"] = "in-place"
        return result
    converter = CONVERTERS.get(ext)
    if converter is None:
        result.update(status="failed", reason=f"unsupported extension {ext}")
        return result

    target = normalized_path(run_dir, rel)
    result["normalized"] = target.relative_to(run_dir).as_posix()
    if not force and target.is_file() and recorded.get(rel) == result["sha256"]:
        result.update(status="unchanged", images=count_images(source, ext))
        return result

    try:
        text, images = converter(source)
    except ConversionError as exc:
        result.update(status="failed", reason=str(exc), normalized="", images=count_images(source, ext))
        return result

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    result.update(status="converted", images=images)
    return result


def normalize(files: list[str], root: Path, run_dir: Path, force: bool = False) -> dict:
    recorded = recorded_hashes(run_dir)
    return {
        "run_dir": run_dir.as_posix(),
        "files": [normalize_file(rel, root, run_dir, recorded, force) for rel in files],
    }


def _resolve_relative(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert .docx/.pdf sources to one markdown file each for NFR mining."
    )
    parser.add_argument("--run-dir", required=True, help="Run folder, e.g. ai-workflow/nfr-state/<run-id>.")
    parser.add_argument(
        "--file",
        action="append",
        required=True,
        help="Root-relative source file. Repeat for several files.",
    )
    parser.add_argument("--root", default=".", help="Project root. Default: cwd.")
    parser.add_argument("--force", action="store_true", help="Convert even when the source is unchanged.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    run_dir = _resolve_relative(args.run_dir, root)
    result = normalize(args.file, root, run_dir, force=args.force)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
