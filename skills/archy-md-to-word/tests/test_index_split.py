import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from index_split import split_cover_and_toc_list

REAL_INDEX_SAMPLE = """# Index

![Close-up of a server network panel with lights and cables](media/media/image1.jpg){width="5.519607392825897in" height="3.6761996937882766in"}

**Cloud Landing Zone**

Solution Architecture Document

*Northwind Systems --- Enterprise Technology*

Document Version: 1.0 (Draft)

August 2026

Classification: Internal Use Only

1. [Architecture Overview](01.Architecture-Overview.md)

    - [1.1 Purpose and Scope](01.Architecture-Overview.md#purpose-and-scope)
        - [1.1.1 In Scope](01.Architecture-Overview.md#in-scope)
        - [1.1.2 Out of Scope](01.Architecture-Overview.md#out-of-scope)
    - [1.2 Conceptual Diagram](01.Architecture-Overview.md#conceptual-diagram)

2. [Cost-Benefit Analysis](02.Cost-Benefit-Analysis.md)

    - [2.1 Estimated Monthly Platform Cost](02.Cost-Benefit-Analysis.md#estimated-monthly-platform-cost)
    - [2.2 Benefit Comparison by Landing Zone Area](02.Cost-Benefit-Analysis.md#benefit-comparison-by-landing-zone-area)
"""


def test_real_sample_shape_cover_and_list_split():
    cover, dropped = split_cover_and_toc_list(REAL_INDEX_SAMPLE)

    assert "Classification: Internal Use Only" in cover
    assert "media/media/image1.jpg" in cover
    assert "1. [Architecture Overview]" not in cover
    assert "2. [Cost-Benefit Analysis]" not in cover

    assert "1. [Architecture Overview](01.Architecture-Overview.md)" in dropped
    assert "1.1 Purpose and Scope" in dropped
    assert "Classification" not in dropped


def test_cover_and_list_present():
    text = "# Index\n\nSome cover text.\n\n1. [Section One](01.Section-One.md)\n"
    cover, dropped = split_cover_and_toc_list(text)

    assert cover == "# Index\n\nSome cover text."
    assert dropped.startswith("1. [Section One]")


def test_no_list_present_cover_only():
    text = "# Index\n\nJust a preamble with no sections yet.\n"
    cover, dropped = split_cover_and_toc_list(text)

    assert cover == text.strip()
    assert dropped == ""


def test_no_cover_present_list_starts_at_line_one():
    text = "1. [Section One](01.Section-One.md)\n2. [Section Two](02.Section-Two.md)\n"
    cover, dropped = split_cover_and_toc_list(text)

    assert cover == ""
    assert dropped == text.strip()
