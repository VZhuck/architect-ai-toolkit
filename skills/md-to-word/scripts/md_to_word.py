#!/usr/bin/env python3
"""Convert a folder of rule-compliant markdown SAD section files back into a
single Word (.docx) document.

Reverses skills/word-to-md: reads 00.Index.md plus <n>.<Title>.md section
files from a source folder (as word-to-md produces them), splits 00.Index.md
into its cover-page preamble (kept) and materialized TOC list (dropped, since
pandoc's --toc generates a native Word TOC field instead), renders any
```mermaid fenced code blocks to PNG images via mermaid-cli (pandoc has no
native mermaid support and would otherwise emit the diagram source as a
literal text block), and runs pandoc once over the cover content plus the
ordered section files to produce a single .docx, optionally styled with a
--reference-doc template.

Usage:
  uv run python skills/md-to-word/scripts/md_to_word.py --source sad
  uv run python skills/md-to-word/scripts/md_to_word.py --source sad --template path/to/template.docx
  uv run python skills/md-to-word/scripts/md_to_word.py --source sad --output dist/sad.docx
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from index_split import split_cover_and_toc_list

_SECTION_FILE_RE = re.compile(r"^(\d+)\..+\.md$")
_ENV_SAD_TEMPLATE_RE = re.compile(r"^\s*SAD_TEMPLATE\s*=\s*(.+?)\s*$", re.MULTILINE)
_MERMAID_FENCE_RE = re.compile(r"^```\s*mermaid\b", re.MULTILINE | re.IGNORECASE)


def _read_env_sad_template(repo_root: Path) -> str | None:
    """Read the SAD_TEMPLATE key from a .env file at the repo root, if present."""
    env_path = repo_root / ".env"
    if not env_path.exists():
        return None

    match = _ENV_SAD_TEMPLATE_RE.search(env_path.read_text(encoding="utf-8"))
    if not match:
        return None

    value = match.group(1).strip().strip('"').strip("'")
    return value or None


def resolve_template(template: str | None, repo_root: Path | None = None) -> Path | None:
    """Resolve the reference-doc template: explicit arg > .env SAD_TEMPLATE > None.

    Raises FileNotFoundError if a template resolves (from either source) but
    the path does not exist on disk.
    """
    if repo_root is None:
        repo_root = Path.cwd()

    source = "explicit --template argument"
    if template is None:
        template = _read_env_sad_template(repo_root)
        source = ".env SAD_TEMPLATE"

    if template is None:
        print(
            "Warning: no template resolved (no --template argument and no .env "
            "SAD_TEMPLATE key) - using pandoc's default docx styling.",
            file=sys.stderr,
        )
        return None

    template_path = Path(template).expanduser()
    if not template_path.is_absolute():
        template_path = repo_root / template_path

    if not template_path.exists():
        raise FileNotFoundError(f"template resolved from {source} does not exist: {template_path}")

    return template_path


def _ordered_section_files(source_folder: Path) -> list[Path]:
    """All <n>.<Title>.md files in source_folder, sorted by numeric prefix."""
    candidates = []
    for path in source_folder.glob("*.md"):
        match = _SECTION_FILE_RE.match(path.name)
        if match and path.name != "00.Index.md":
            candidates.append((int(match.group(1)), path))

    candidates.sort(key=lambda pair: pair[0])
    return [path for _, path in candidates]


def _render_mermaid_diagrams(md_path: Path, artifacts_dir: Path) -> None:
    """Replace ```mermaid fenced code blocks in md_path with rendered PNG
    image references, in place, via mermaid-cli. No-op if the file has no
    mermaid fences - callers should check _MERMAID_FENCE_RE before calling.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["mmdc", "-i", str(md_path), "-o", str(md_path), "-e", "png", "-a", str(artifacts_dir)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "mermaid-cli (mmdc) is not installed or not on PATH - install "
            "@mermaid-js/mermaid-cli to render mermaid diagrams in "
            f"{md_path.name}, or remove the mermaid fence"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"mermaid-cli failed rendering {md_path.name}: {exc.stderr}") from exc


def convert(
    source_folder: Path,
    template: str | Path | None = None,
    output: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    source_folder = Path(source_folder).expanduser().resolve()
    if not source_folder.is_dir():
        raise FileNotFoundError(f"source folder not found: {source_folder}")

    if repo_root is None:
        repo_root = Path.cwd()

    resolved_template = resolve_template(str(template) if template else None, repo_root)

    index_path = source_folder / "00.Index.md"
    cover_text = ""
    if index_path.exists():
        cover_text, _dropped = split_cover_and_toc_list(index_path.read_text(encoding="utf-8"))

    section_files = _ordered_section_files(source_folder)
    if not section_files:
        raise FileNotFoundError(f"no <n>.<Title>.md section files found under {source_folder}")

    if output is None:
        output = Path("ai-workflow") / "md-to-word" / f"{source_folder.name}.docx"
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="md-to-word-") as staging_dir_str:
        staging_dir = Path(staging_dir_str)

        media_src = source_folder / "media"
        if media_src.exists():
            shutil.copytree(media_src, staging_dir / "media")

        cover_path = staging_dir / "00.Cover.md"
        cover_path.write_text(cover_text, encoding="utf-8")

        staged_section_paths = []
        for section_path in section_files:
            staged_path = staging_dir / section_path.name
            shutil.copy2(section_path, staged_path)
            staged_section_paths.append(staged_path)

        mermaid_artifacts_dir = staging_dir / "media" / "mermaid"
        for md_path in [cover_path, *staged_section_paths]:
            if _MERMAID_FENCE_RE.search(md_path.read_text(encoding="utf-8")):
                _render_mermaid_diagrams(md_path, mermaid_artifacts_dir)

        tmp_docx = staging_dir / f"{output.stem}.tmp.docx"

        cmd = ["pandoc", "-s", "--toc", "--toc-depth=3"]
        if resolved_template is not None:
            cmd += ["--reference-doc", str(resolved_template)]
        cmd += [cover_path.name] + [p.name for p in staged_section_paths]
        cmd += ["-o", tmp_docx.name]

        try:
            subprocess.run(cmd, cwd=staging_dir, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "pandoc is not installed or not on PATH - install pandoc to use this skill"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"pandoc conversion failed: {exc.stderr}") from exc

        shutil.move(str(tmp_docx), str(output))

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a folder of rule-compliant markdown SAD section files into a single Word document."
    )
    parser.add_argument(
        "--source",
        default="sad",
        help="Source folder containing 00.Index.md and <n>.<Title>.md section files. Default: sad",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Optional reference .docx template. Default: .env's SAD_TEMPLATE, else pandoc's default styling.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output .docx path. Default: ai-workflow/md-to-word/<source-folder-name>.docx",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = convert(
        Path(args.source),
        args.template,
        Path(args.output) if args.output else None,
    )
    print(f"Wrote Word document to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
