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
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))

from index_split import split_cover_and_toc_list

_SECTION_FILE_RE = re.compile(r"^(\d+)\..+\.md$")
_ENV_SAD_TEMPLATE_RE = re.compile(r"^\s*SAD_TEMPLATE\s*=\s*(.+?)\s*$", re.MULTILINE)
_MERMAID_FENCE_RE = re.compile(r"^```\s*mermaid\b(.*?)^```", re.MULTILINE | re.IGNORECASE | re.DOTALL)
_ICON_REF_RE = re.compile(
    r'icon:\s*["\']?([a-zA-Z][\w-]*):([a-zA-Z][\w-]*)["\']?'
    r"|\(([a-zA-Z][\w-]*):([a-zA-Z][\w-]*)\)"
)
_HTML_TABLE_RE = re.compile(
    r"(?:<!--\s*HTML format:.*?-->\s*\n)?(<table\b.*?</table>)",
    re.IGNORECASE | re.DOTALL,
)

_PAGE_BREAK_OPENXML = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_DOCX_NS = {"w": _W_NS, "r": _R_NS}

_CONTENT_TYPE_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
    ".emf": "image/x-emf",
}


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


def _detect_icon_packs(text: str) -> list[str]:
    """Find iconify-style `prefix:name` icon references inside ```mermaid
    fences (e.g. `icon: "logos:aws-lambda"` or `service db(logos:aws-rds)`)
    and return the unique iconify package names (`@iconify-json/<prefix>`)
    mermaid-cli needs to resolve them. Without these, referenced icons render
    as a "?" placeholder instead of the actual glyph.
    """
    prefixes: set[str] = set()
    for fence_match in _MERMAID_FENCE_RE.finditer(text):
        body = fence_match.group(1)
        for match in _ICON_REF_RE.finditer(body):
            prefix = match.group(1) or match.group(3)
            if prefix:
                prefixes.add(prefix)

    return [f"@iconify-json/{prefix}" for prefix in sorted(prefixes)]


def _render_mermaid_diagrams(md_path: Path, artifacts_dir: Path, icon_packs: list[str]) -> None:
    """Replace ```mermaid fenced code blocks in md_path with rendered PNG
    image references, in place, via mermaid-cli. No-op if the file has no
    mermaid fences - callers should check _MERMAID_FENCE_RE before calling.
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["mmdc", "-i", str(md_path), "-o", str(md_path), "-e", "png", "-a", str(artifacts_dir)]
    if icon_packs:
        cmd += ["--iconPacks", *icon_packs]
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


def _render_html_table_fragment(
    table_html: str, resource_path: Path
) -> tuple[str | None, list[tuple[str, bytes, str]]]:
    """Render an isolated `<table>...</table>` HTML snippet to a native docx
    table via pandoc's HTML reader (which - unlike the markdown reader used
    for the rest of the document - actually parses rowspan/colspan and
    embedded <img> tags instead of passing them through as inert raw HTML).

    Returns (tbl_xml, media_items) where tbl_xml is the extracted <w:tbl>
    OOXML string (or None if pandoc produced no table) and media_items is a
    list of (relationship_id, media_bytes, content_type) for every image the
    table referenced.
    """
    with tempfile.TemporaryDirectory(prefix="html-table-") as fragment_dir_str:
        fragment_dir = Path(fragment_dir_str)
        html_path = fragment_dir / "table.html"
        html_path.write_text(f"<html><body>{table_html}</body></html>", encoding="utf-8")
        fragment_docx = fragment_dir / "table.docx"

        cmd = [
            "pandoc",
            "-f",
            "html",
            "-t",
            "docx",
            "--resource-path",
            str(resource_path),
            str(html_path),
            "-o",
            str(fragment_docx),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "pandoc is not installed or not on PATH - install pandoc to use this skill"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"pandoc failed rendering an HTML table fragment: {exc.stderr}") from exc

        with zipfile.ZipFile(fragment_docx) as archive:
            doc_xml = archive.read("word/document.xml")
            media_names = [name for name in archive.namelist() if name.startswith("word/media/")]
            media_bytes = {name: archive.read(name) for name in media_names}
            rels_name = "word/_rels/document.xml.rels"
            rels_xml = archive.read(rels_name) if rels_name in archive.namelist() else None

        root = etree.fromstring(doc_xml)
        tbl = root.find("w:body/w:tbl", _DOCX_NS)
        if tbl is None:
            return None, []
        tbl_xml = etree.tostring(tbl, encoding="unicode")

        media_items: list[tuple[str, bytes, str]] = []
        if rels_xml is not None:
            rels_root = etree.fromstring(rels_xml)
            for rel in rels_root:
                target = rel.get("Target")
                rid = rel.get("Id")
                if not target or not target.startswith("media/"):
                    continue
                key = f"word/{target}"
                if key not in media_bytes:
                    continue
                content_type = _CONTENT_TYPE_BY_EXT.get(Path(target).suffix.lower(), "application/octet-stream")
                media_items.append((rid, media_bytes[key], content_type))
                tbl_xml = tbl_xml.replace(f'r:embed="{rid}"', f'r:embed="__PENDING__{len(media_items) - 1}__"')

        return tbl_xml, media_items


def _splice_html_tables(
    md_path: Path, resource_path: Path, pending_media: list[tuple[str, bytes, str]]
) -> None:
    """Replace every raw `<table>` HTML block in md_path with a native docx
    table rendered via pandoc's HTML reader, in place. Raw HTML tables (kept
    as HTML by word-to-md for colspan/rowspan or nested tables) are otherwise
    passed through by pandoc's markdown reader as inert raw HTML, which the
    docx writer silently drops - along with any images inside them.

    Appends discovered images to pending_media (shared across all files) and
    rewrites each table's image references to a placeholder relationship id
    that _merge_pending_media resolves once the final document exists.
    """
    text = md_path.read_text(encoding="utf-8")

    def _replace(match: re.Match[str]) -> str:
        table_html = match.group(1)
        tbl_xml, media_items = _render_html_table_fragment(table_html, resource_path)
        if tbl_xml is None:
            return match.group(0)

        offset = len(pending_media)
        for local_index, (_old_rid, data, content_type) in enumerate(media_items):
            global_index = offset + local_index
            pending_media.append((data, content_type))
            tbl_xml = tbl_xml.replace(
                f'r:embed="__PENDING__{local_index}__"', f'r:embed="__PENDING__{global_index}__"'
            )

        return f"\n```{{=openxml}}\n{tbl_xml}\n```\n"

    new_text = _HTML_TABLE_RE.sub(_replace, text)
    if new_text != text:
        md_path.write_text(new_text, encoding="utf-8")


def _merge_pending_media(docx_path: Path, pending_media: list[tuple[bytes, str]]) -> None:
    """Register images spliced in by _splice_html_tables into a finished docx:
    add each image to word/media/, add its relationship, add its content
    type, and resolve the "__PENDING__<n>__" placeholder r:embed ids left in
    document.xml to the newly assigned relationship ids.
    """
    if not pending_media:
        return

    with tempfile.TemporaryDirectory(prefix="merge-media-") as extract_dir_str:
        extract_dir = Path(extract_dir_str)
        with zipfile.ZipFile(docx_path) as archive:
            archive.extractall(extract_dir)

        doc_xml_path = extract_dir / "word" / "document.xml"
        doc_text = doc_xml_path.read_text(encoding="utf-8")

        rels_path = extract_dir / "word" / "_rels" / "document.xml.rels"
        rels_root = etree.parse(str(rels_path)).getroot()
        existing_ids = {rel.get("Id") for rel in rels_root}

        content_types_path = extract_dir / "[Content_Types].xml"
        content_types_root = etree.parse(str(content_types_path)).getroot()
        existing_extensions = {
            default.get("Extension") for default in content_types_root.findall(f"{{{_CT_NS}}}Default")
        }

        media_dir = extract_dir / "word" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        for index, (data, content_type) in enumerate(pending_media):
            ext = next((e for e, ct in _CONTENT_TYPE_BY_EXT.items() if ct == content_type), ".bin")
            filename = f"htmlTableImage{index}{ext}"
            (media_dir / filename).write_bytes(data)

            new_rid = f"rIdHtmlTable{index}"
            while new_rid in existing_ids:
                new_rid += "x"
            existing_ids.add(new_rid)
            placeholder = f"__PENDING__{index}__"

            relationship = etree.SubElement(rels_root, f"{{{_REL_NS}}}Relationship")
            relationship.set("Id", new_rid)
            relationship.set(
                "Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
            )
            relationship.set("Target", f"media/{filename}")

            extension = ext.lstrip(".")
            if extension not in existing_extensions:
                existing_extensions.add(extension)
                default = etree.SubElement(content_types_root, f"{{{_CT_NS}}}Default")
                default.set("Extension", extension)
                default.set("ContentType", content_type)

            doc_text = doc_text.replace(f'r:embed="{placeholder}"', f'r:embed="{new_rid}"')

        doc_xml_path.write_text(doc_text, encoding="utf-8")
        etree.ElementTree(rels_root).write(str(rels_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        etree.ElementTree(content_types_root).write(
            str(content_types_path), xml_declaration=True, encoding="UTF-8", standalone=True
        )

        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in extract_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(extract_dir))


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

        # Copy every asset subfolder (media/, diagrams/, etc. - per
        # rules/sad-sections.instructions.md, images may live under either
        # convention) so relative image paths resolve regardless of which
        # directory a section file points into.
        for entry in source_folder.iterdir():
            if entry.is_dir():
                shutil.copytree(entry, staging_dir / entry.name)

        cover_path = staging_dir / "00.Cover.md"
        cover_path.write_text(cover_text, encoding="utf-8")

        staged_section_paths = []
        for section_path in section_files:
            staged_path = staging_dir / section_path.name
            shutil.copy2(section_path, staged_path)
            staged_section_paths.append(staged_path)

        pending_media: list[tuple[bytes, str]] = []
        for md_path in [cover_path, *staged_section_paths]:
            _splice_html_tables(md_path, staging_dir, pending_media)

        mermaid_artifacts_dir = staging_dir / "media" / "mermaid"
        for md_path in [cover_path, *staged_section_paths]:
            text = md_path.read_text(encoding="utf-8")
            if _MERMAID_FENCE_RE.search(text):
                _render_mermaid_diagrams(md_path, mermaid_artifacts_dir, _detect_icon_packs(text))

        page_break_path = staging_dir / "PAGEBREAK.md"
        page_break_path.write_text(_PAGE_BREAK_OPENXML, encoding="utf-8")

        tmp_docx = staging_dir / f"{output.stem}.tmp.docx"

        cmd = ["pandoc", "-s", "--toc", "--toc-depth=3"]
        if resolved_template is not None:
            cmd += ["--reference-doc", str(resolved_template)]
        cmd += [cover_path.name]
        for staged_path in staged_section_paths:
            cmd += [page_break_path.name, staged_path.name]
        cmd += ["-o", tmp_docx.name]

        try:
            subprocess.run(cmd, cwd=staging_dir, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "pandoc is not installed or not on PATH - install pandoc to use this skill"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"pandoc conversion failed: {exc.stderr}") from exc

        _merge_pending_media(tmp_docx, pending_media)
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
