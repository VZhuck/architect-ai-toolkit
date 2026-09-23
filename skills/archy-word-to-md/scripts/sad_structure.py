"""Deterministic structural normalization for SAD markdown, per
rules/sad-sections.instructions.md: drop pandoc's auto-TOC, fold cover content
into an index preamble, split by H1 into title-case-hyphenated files, and
generate a mechanical 00.Index.md with cross-file links.
"""

from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$", re.MULTILINE)
_H1_RE = re.compile(r"^#[ \t]+(.*)$", re.MULTILINE)
_LEADING_NUMBERING_RE = re.compile(r"^\s*\d+(?:\.\d+)*[.)]?\s*")
_WINDOWS_INVALID_RE = re.compile(r'[\\/:*?"<>|]')


def split_cover_and_body(text: str) -> tuple[str, str]:
    """Split off any pre-heading cover content and pandoc's auto-TOC section.

    Returns (cover_text, body_text) where body_text starts at the first real
    H1 section.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return "", text

    first = matches[0]
    cover = text[: first.start()].strip()
    body_start = first.start()

    if first.group(1) == "#" and first.group(2).strip().lower() == "table of contents":
        body_start = matches[1].start() if len(matches) > 1 else len(text)

    return cover, text[body_start:]


def split_by_h1(text: str) -> list[tuple[str, str]]:
    """Split body text into (heading_text, section_content) per H1 section."""
    matches = list(_H1_RE.finditer(text))
    sections = []
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        heading_text = m.group(1).strip()
        content = text[start:end].rstrip() + "\n"
        sections.append((heading_text, content))
    return sections


def strip_leading_numbering(heading_text: str) -> str:
    return _LEADING_NUMBERING_RE.sub("", heading_text).strip()


def sanitize_title(heading_text: str) -> str:
    """Title-case-hyphenated filename title: preserve source word casing,
    strip leading section numbering and Windows-invalid characters, hyphenate
    spaces. Per rules/sad-sections.instructions.md - NOT lowercased kebab-case.
    """
    title = strip_leading_numbering(heading_text)
    title = _WINDOWS_INVALID_RE.sub("", title)
    title = re.sub(r"\s+", "-", title.strip())
    title = re.sub(r"-{2,}", "-", title).strip("-")
    return title or "Section"


def github_anchor(heading_text: str) -> str:
    """GitHub-style heading anchor, matching pandoc's own auto-identifier
    behavior: leading non-letter characters (section numbering) are stripped
    entirely, not just hyphenated, before slugifying.
    """
    text = heading_text.strip().lower()
    text = re.sub(r"^[^a-z]+", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text


def build_section_files(body_text: str) -> list[tuple[str, str, str]]:
    """Return [(filename, raw_h1_heading_text, content)] for every H1 section."""
    sections = split_by_h1(body_text)
    result = []
    for i, (heading_text, content) in enumerate(sections, start=1):
        filename = f"{i:02d}.{sanitize_title(heading_text)}.md"
        result.append((filename, heading_text, content))
    return result


def build_index(cover_text: str, section_files: list[tuple[str, str, str]]) -> str:
    lines = ["# Index", ""]
    if cover_text:
        lines.append(cover_text)
        lines.append("")

    for i, (filename, heading_text, content) in enumerate(section_files, start=1):
        title = strip_leading_numbering(heading_text)
        lines.append(f"{i}. [{title}]({filename})")
        lines.append("")
        for level_hashes, sub_heading in re.findall(r"^(#{2,3})[ \t]+(.*)$", content, re.MULTILINE):
            anchor = github_anchor(sub_heading)
            indent = "    " if len(level_hashes) == 2 else "        "
            lines.append(f"{indent}- [{sub_heading.strip()}]({filename}#{anchor})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
