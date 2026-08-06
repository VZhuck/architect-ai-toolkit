"""End-to-end pytest coverage for the word-to-md skill, run against the
checked-in test-data/Northwind-Cloud-Landing-Zone-SAD.docx fixture."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from docx_to_md import convert
from sad_structure import github_anchor

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DOCX = REPO_ROOT / "test-data" / "Northwind-Cloud-Landing-Zone-SAD.docx"


@pytest.fixture(scope="module")
def converted_output(tmp_path_factory):
    target_folder = tmp_path_factory.mktemp("word-to-md-output")
    workdir = tmp_path_factory.mktemp("word-to-md-workdir")
    convert(SOURCE_DOCX, target_folder, workdir=workdir)
    return target_folder


def test_expected_files_are_created(converted_output):
    names = {p.name for p in converted_output.glob("*.md")}
    assert names == {"00.Index.md", "01.Architecture-Overview.md", "02.Cost-Benefit-Analysis.md"}


def test_estimated_monthly_cost_table_is_markdown_pipe_table(converted_output):
    content = (converted_output / "02.Cost-Benefit-Analysis.md").read_text(encoding="utf-8")
    section = content.split("## 2.1 Estimated Monthly Platform Cost", 1)[1]
    section = section.split("## 2.2", 1)[0]

    assert "<table" not in section
    assert "**Service**" in section
    assert re.search(r"^\|.*\|.*\|$", section, re.MULTILINE)
    assert "Azure Firewall (hub)" in section


def test_benefit_comparison_table_converted_not_html(converted_output):
    content = (converted_output / "02.Cost-Benefit-Analysis.md").read_text(encoding="utf-8")
    section = content.split("## 2.2 Benefit Comparison by Landing Zone Area", 1)[1]

    assert "<table" not in section
    assert "&amp;" not in section
    assert "Security & Governance" in section
    assert "- Centralized policy enforcement<br>" in section


def test_no_stray_html_entities_anywhere(converted_output):
    for md_file in converted_output.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        assert not re.search(r"&(amp|lt|gt|quot|#39);", content), f"entity found in {md_file.name}"


def test_no_pandoc_auto_toc_or_cover_text_in_section_files(converted_output):
    section_1 = (converted_output / "01.Architecture-Overview.md").read_text(encoding="utf-8")
    assert "Table of Contents" not in section_1
    assert "Classification: Internal Use Only" not in section_1


def test_cover_text_folded_into_index_preamble(converted_output):
    index_content = (converted_output / "00.Index.md").read_text(encoding="utf-8")
    assert "Classification: Internal Use Only" in index_content


def test_index_links_resolve_to_real_headings_in_target_files(converted_output):
    index_content = (converted_output / "00.Index.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)#]+\.md)(?:#([\w-]+))?\)", index_content)

    assert links, "expected at least one link in the index"

    for filename, anchor in links:
        target_path = converted_output / filename
        assert target_path.exists(), f"index links to missing file: {filename}"
        if not anchor:
            continue
        target_content = target_path.read_text(encoding="utf-8")
        headings = re.findall(r"^#{1,6}[ \t]+(.*)$", target_content, re.MULTILINE)
        anchors_in_target = {github_anchor(h) for h in headings}
        assert anchor in anchors_in_target, f"anchor #{anchor} not found in {filename}"


def test_images_preserved_with_paths_and_attributes(converted_output):
    section_1 = (converted_output / "01.Architecture-Overview.md").read_text(encoding="utf-8")
    assert re.search(r"!\[.*?\]\(media/media/image2\.png\)\{width=", section_1)
    assert (converted_output / "media" / "media" / "image2.png").exists()
    assert (converted_output / "media" / "media" / "image1.jpg").exists()
