"""Split word-to-md's 00.Index.md into cover preamble vs. materialized TOC list.

00.Index.md (per skills/word-to-md/scripts/sad_structure.py's build_index) contains
cover-page content (title block, doc version, classification, cover image) followed
by a materialized nested list of numbered section/subsection links. When converting
back to .docx, the materialized list is redundant with pandoc's native --toc field,
so it is dropped while the cover content is kept.
"""

from __future__ import annotations

import re

_TOC_LIST_ITEM_RE = re.compile(r"^\d+\.\s+\[", re.MULTILINE)


def split_cover_and_toc_list(text: str) -> tuple[str, str]:
    """Split index text at the first numbered TOC list link.

    Returns (cover, dropped) where cover is everything before the first line
    matching a numbered list link (e.g. "1. [Title](...)"), and dropped is
    everything from that point onward. If no such line exists, cover is the
    entire text and dropped is empty.
    """
    match = _TOC_LIST_ITEM_RE.search(text)
    if match is None:
        return text.strip(), ""

    return text[: match.start()].strip(), text[match.start() :].strip()
