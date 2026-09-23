"""Unit tests for the table normalizer, using synthetic HTML snippets so the
merged-cell ("keep as HTML") branch is covered even though the sample docx
fixture doesn't happen to contain a merged-cell table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from table_normalizer import find_top_level_tables, normalize_table_html, normalize_tables

SIMPLE_TABLE_NO_MERGE = """<table>
<tbody>
<tr><td><strong>Area</strong></td><td><strong>Key Benefits</strong></td><td style="text-align: right;"><strong>Annual Value (USD)</strong></td></tr>
<tr><td>Security &amp; Governance</td><td><ul><li><p>Centralized policy enforcement</p></li><li><p>Faster detection</p></li></ul></td><td style="text-align: right;">$185,000</td></tr>
</tbody>
</table>"""

MERGED_CELL_TABLE = """<table>
<tbody>
<tr><td colspan="2">Header spanning 2 columns</td></tr>
<tr><td>Cell 1</td><td>Cell 2</td></tr>
</tbody>
</table>"""

ROWSPAN_TABLE = """<table>
<tbody>
<tr><td rowspan="2">Spans two rows</td><td>Cell A</td></tr>
<tr><td>Cell B</td></tr>
</tbody>
</table>"""

NESTED_TABLE = """<table>
<tbody>
<tr><td><table><tbody><tr><td>inner</td></tr></tbody></table></td></tr>
</tbody>
</table>"""


def test_table_without_merge_converts_to_markdown_pipe_table():
    result = normalize_table_html(SIMPLE_TABLE_NO_MERGE)

    assert "<table" not in result
    assert "| **Area** | **Key Benefits** | **Annual Value (USD)** |" in result
    assert "|---|---|--:|" in result


def test_list_cells_join_with_br_bullet_pseudo_format():
    result = normalize_table_html(SIMPLE_TABLE_NO_MERGE)

    assert "- Centralized policy enforcement<br>- Faster detection" in result


def test_html_entities_are_unescaped_in_converted_table():
    result = normalize_table_html(SIMPLE_TABLE_NO_MERGE)

    assert "&amp;" not in result
    assert "Security & Governance" in result


def test_colspan_table_is_kept_as_html_with_comment():
    result = normalize_table_html(MERGED_CELL_TABLE)

    assert "<table" in result
    assert result.startswith("<!-- HTML format: contains merged cells (colspan/rowspan) -->")


def test_rowspan_table_is_kept_as_html_with_comment():
    result = normalize_table_html(ROWSPAN_TABLE)

    assert "<table" in result
    assert "contains merged cells (colspan/rowspan)" in result


def test_nested_table_is_kept_as_html_with_comment():
    result = normalize_table_html(NESTED_TABLE)

    assert result.count("<table") == 2
    assert "contains nested tables" in result


def test_find_top_level_tables_skips_nested_table_span():
    text = f"before\n\n{NESTED_TABLE}\n\nafter"
    spans = find_top_level_tables(text)

    assert len(spans) == 1
    start, end = spans[0]
    assert text[start:end] == NESTED_TABLE


def test_normalize_tables_processes_multiple_tables_in_document():
    text = f"# Doc\n\n{SIMPLE_TABLE_NO_MERGE}\n\nsome text\n\n{MERGED_CELL_TABLE}\n"
    result = normalize_tables(text)

    assert "| **Area** |" in result
    assert "<!-- HTML format: contains merged cells (colspan/rowspan) -->" in result
    assert "some text" in result
