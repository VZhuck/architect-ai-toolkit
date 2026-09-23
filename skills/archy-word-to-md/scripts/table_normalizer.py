"""Normalize HTML tables in markdown to comply with rules/sad-sections.instructions.md.

Decision rule: an HTML <table> is converted to a markdown pipe table unless it
contains a colspan/rowspan attribute or a nested <table> (merged cells / nested
tables cannot be represented in markdown) - in which case it is kept as HTML,
entities are unescaped, and an explanatory comment is added above it.
"""

from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

_TABLE_OPEN_RE = re.compile(r"<table\b", re.IGNORECASE)
_TABLE_CLOSE_RE = re.compile(r"</table\s*>", re.IGNORECASE)


def find_top_level_tables(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of every top-level <table>...</table> block.

    Nested tables are matched as part of their parent's span, not separately,
    since a nested table forces the whole outer table to stay as HTML anyway.
    """
    spans: list[tuple[int, int]] = []
    pos = 0
    while True:
        open_match = _TABLE_OPEN_RE.search(text, pos)
        if not open_match:
            break
        depth = 1
        search_pos = open_match.end()
        end = len(text)
        while depth > 0:
            next_open = _TABLE_OPEN_RE.search(text, search_pos)
            next_close = _TABLE_CLOSE_RE.search(text, search_pos)
            if not next_close:
                end = len(text)
                break
            if next_open and next_open.start() < next_close.start():
                depth += 1
                search_pos = next_open.end()
            else:
                depth -= 1
                search_pos = next_close.end()
                if depth == 0:
                    end = next_close.end()
        spans.append((open_match.start(), end))
        pos = end
    return spans


def _has_merge_or_nested_table(table_html: str) -> tuple[bool, str]:
    if re.search(r"\bcolspan\s*=", table_html, re.IGNORECASE) or re.search(
        r"\browspan\s*=", table_html, re.IGNORECASE
    ):
        return True, "contains merged cells (colspan/rowspan)"
    if len(_TABLE_OPEN_RE.findall(table_html)) > 1:
        return True, "contains nested tables"
    return False, ""


def _inline_to_md(node) -> str:
    if isinstance(node, NavigableString):
        return html.unescape(str(node))
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()
    if name in ("strong", "b"):
        return "**" + "".join(_inline_to_md(c) for c in node.children) + "**"
    if name in ("em", "i"):
        return "*" + "".join(_inline_to_md(c) for c in node.children) + "*"
    if name == "br":
        return " "
    return "".join(_inline_to_md(c) for c in node.children)


def _block_lines(node) -> list[str]:
    lines: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = _inline_to_md(child).strip()
            if text:
                lines.append(text)
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        if name == "p":
            text = _inline_to_md(child).strip()
            if text:
                lines.append(text)
        elif name in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                text = _inline_to_md(li).strip()
                if text:
                    lines.append(f"- {text}")
        else:
            text = _inline_to_md(child).strip()
            if text:
                lines.append(text)
    return lines


def _cell_to_md(cell) -> str:
    lines = _block_lines(cell)
    return "<br>".join(lines)


def _column_alignment(rows: list[list], col_index: int) -> str | None:
    for row in rows:
        if col_index >= len(row):
            continue
        style = row[col_index].get("style", "") if isinstance(row[col_index], Tag) else ""
        style = style.lower()
        if "text-align: right" in style or "text-align:right" in style:
            return "right"
        if "text-align: left" in style or "text-align:left" in style:
            return "left"
    return None


def _html_table_to_markdown(table_tag) -> str:
    rows = [tr.find_all(["td", "th"], recursive=False) for tr in table_tag.find_all("tr", recursive=True)]
    rows = [r for r in rows if r]
    if not rows:
        return ""

    header_cells, *body_rows = rows
    ncols = len(header_cells)

    header_md = [_cell_to_md(c) for c in header_cells]
    alignments = [_column_alignment(rows, i) for i in range(ncols)]
    separators = []
    for align in alignments:
        if align == "right":
            separators.append("--:")
        elif align == "left":
            separators.append(":--")
        else:
            separators.append("---")

    lines = ["| " + " | ".join(header_md) + " |", "|" + "|".join(separators) + "|"]
    for row in body_rows:
        cells_md = [_cell_to_md(row[i]) if i < len(row) else "" for i in range(ncols)]
        lines.append("| " + " | ".join(cells_md) + " |")
    return "\n".join(lines)


def normalize_table_html(table_html: str) -> str:
    """Normalize a single <table>...</table> HTML string per the SAD table rules."""
    keep_html, reason = _has_merge_or_nested_table(table_html)
    if keep_html:
        unescaped = html.unescape(table_html)
        return f"<!-- HTML format: {reason} -->\n\n{unescaped}"

    soup = BeautifulSoup(table_html, "html.parser")
    table_tag = soup.find("table")
    if table_tag is None:
        return html.unescape(table_html)
    return _html_table_to_markdown(table_tag)


def normalize_tables(markdown_text: str) -> str:
    """Normalize every top-level HTML table in a markdown document in place."""
    spans = find_top_level_tables(markdown_text)
    text = markdown_text
    for start, end in reversed(spans):
        block = text[start:end]
        replacement = f"\n\n{normalize_table_html(block)}\n\n"
        text = text[:start] + replacement + text[end:]
    return re.sub(r"\n{3,}", "\n\n", text)
