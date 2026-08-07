"""End-to-end pytest coverage for the md-to-word skill, run against a small
synthetic section folder shaped like word-to-md's own output."""

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import md_to_word
from md_to_word import convert, resolve_template

INDEX_MD = """# Index

![A cover diagram](media/cover.png){width="1in"}

**Sample SAD**

Classification: Internal Use Only

1. [Section One](01.Section-One.md)

    - [1.1 Subsection](01.Section-One.md#subsection)

2. [Section Two](02.Section-Two.md)
"""

SECTION_ONE_MD = """# Section One

## 1.1 Subsection

Some content for section one.
"""

SECTION_TWO_MD = """# Section Two

More content for section two.
"""

SECTION_WITH_MERMAID_MD = """# Section Three

```mermaid
sequenceDiagram
    Alice->>Bob: Hello Bob
    Bob-->>Alice: Hello Alice
```
"""


@pytest.fixture()
def section_folder(tmp_path):
    folder = tmp_path / "sad"
    folder.mkdir()
    (folder / "00.Index.md").write_text(INDEX_MD, encoding="utf-8")
    (folder / "01.Section-One.md").write_text(SECTION_ONE_MD, encoding="utf-8")
    (folder / "02.Section-Two.md").write_text(SECTION_TWO_MD, encoding="utf-8")

    media_dir = folder / "media"
    media_dir.mkdir()
    # 1x1 transparent PNG.
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "89000000017352474200aece1ce90000000467414d410000b18f0bfc6105000000"
        "097048597300000ec300000ec301c76fa8640000000d49444154085b6360000000"
        "020001e221bc330000000049454e44ae426082"
    )
    (media_dir / "cover.png").write_bytes(png_bytes)

    return folder


def document_xml(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path) as z:
        return z.read("word/document.xml").decode("utf-8")


def test_default_output_path(section_folder, monkeypatch):
    monkeypatch.chdir(section_folder.parent)
    output = convert(section_folder)

    assert output == (section_folder.parent / "ai-workflow" / "md-to-word" / "sad.docx").resolve()
    assert output.exists()


def test_explicit_output_path(section_folder, tmp_path):
    output_path = tmp_path / "dist" / "custom.docx"
    output = convert(section_folder, output=output_path)

    assert output == output_path.resolve()
    assert output.exists()


def test_native_toc_field_present_and_materialized_list_absent(section_folder, tmp_path):
    output = convert(section_folder, output=tmp_path / "out.docx")
    xml = document_xml(output)

    assert "TOC \\o" in xml
    # The materialized numbered list text should not appear as rendered body content.
    assert "Section One](01.Section-One.md)" not in xml


def test_cover_content_present(section_folder, tmp_path):
    output = convert(section_folder, output=tmp_path / "out.docx")
    xml = document_xml(output)

    assert "Sample SAD" in xml
    assert "Classification: Internal Use Only" in xml


def test_source_folder_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        convert(tmp_path / "does-not-exist")


def test_no_section_files_found(tmp_path):
    empty_folder = tmp_path / "empty-sad"
    empty_folder.mkdir()
    with pytest.raises(FileNotFoundError):
        convert(empty_folder)


@pytest.fixture()
def section_folder_with_mermaid(section_folder):
    (section_folder / "03.Section-Three.md").write_text(SECTION_WITH_MERMAID_MD, encoding="utf-8")
    return section_folder


class TestMermaidDiagrams:
    def test_mermaid_fence_rendered_as_image_not_text(self, section_folder_with_mermaid, tmp_path):
        output = convert(section_folder_with_mermaid, output=tmp_path / "out.docx")

        with zipfile.ZipFile(output) as z:
            doc_xml = z.read("word/document.xml").decode("utf-8")
            media_files = [n for n in z.namelist() if n.startswith("word/media/")]

        assert "sequenceDiagram" not in doc_xml
        assert "```" not in doc_xml
        # The cover's PNG plus the rendered mermaid diagram PNG.
        assert len(media_files) >= 2

    def test_source_section_file_left_untouched(self, section_folder_with_mermaid, tmp_path):
        source_path = section_folder_with_mermaid / "03.Section-Three.md"
        original_content = source_path.read_text(encoding="utf-8")

        convert(section_folder_with_mermaid, output=tmp_path / "out.docx")

        assert source_path.read_text(encoding="utf-8") == original_content

    def test_missing_mmdc_raises_clear_error(self, section_folder_with_mermaid, tmp_path, monkeypatch):
        real_run = subprocess.run

        def fake_run(cmd, *args, **kwargs):
            if cmd[0] == "mmdc":
                raise FileNotFoundError("mmdc not found")
            return real_run(cmd, *args, **kwargs)

        monkeypatch.setattr(md_to_word.subprocess, "run", fake_run)

        with pytest.raises(RuntimeError, match="mermaid-cli"):
            convert(section_folder_with_mermaid, output=tmp_path / "out.docx")

    def test_no_mermaid_fence_skips_mmdc_invocation(self, section_folder, tmp_path, monkeypatch):
        real_run = subprocess.run
        calls = []

        def fake_run(cmd, *args, **kwargs):
            calls.append(cmd[0])
            return real_run(cmd, *args, **kwargs)

        monkeypatch.setattr(md_to_word.subprocess, "run", fake_run)

        convert(section_folder, output=tmp_path / "out.docx")

        assert "mmdc" not in calls


class TestIconPackDetection:
    def test_detects_icon_shape_syntax(self):
        text = '```mermaid\nflowchart TD\n  A@{ icon: "logos:aws-lambda" }\n```\n'
        assert md_to_word._detect_icon_packs(text) == ["@iconify-json/logos"]

    def test_detects_architecture_service_syntax(self):
        text = (
            "```mermaid\narchitecture-beta\n"
            "    service lambda(logos:aws-lambda)[Lambda]\n"
            "    service db(logos:aws-rds)[Database]\n"
            "```\n"
        )
        assert md_to_word._detect_icon_packs(text) == ["@iconify-json/logos"]

    def test_ignores_non_icon_colons_like_sequence_messages(self):
        text = "```mermaid\nsequenceDiagram\n    Alice->>Bob: Hello Bob\n```\n"
        assert md_to_word._detect_icon_packs(text) == []

    def test_no_mermaid_fence_returns_empty(self):
        assert md_to_word._detect_icon_packs("plain text, no fences here") == []

    def test_mmdc_invoked_with_detected_icon_packs(self, section_folder, tmp_path, monkeypatch):
        (section_folder / "03.Section-Three.md").write_text(
            '```mermaid\narchitecture-beta\n    service db(logos:aws-rds)[Database]\n```\n',
            encoding="utf-8",
        )
        real_run = subprocess.run
        recorded_cmds = []

        def fake_run(cmd, *args, **kwargs):
            if cmd[0] == "mmdc":
                recorded_cmds.append(cmd)
                Path(cmd[cmd.index("-o") + 1]).write_text("rendered", encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0)
            return real_run(cmd, *args, **kwargs)

        monkeypatch.setattr(md_to_word.subprocess, "run", fake_run)

        convert(section_folder, output=tmp_path / "out.docx")

        assert len(recorded_cmds) == 1
        cmd = recorded_cmds[0]
        assert "--iconPacks" in cmd
        assert "@iconify-json/logos" in cmd


ROWSPAN_TABLE_SECTION_MD = """# Section Three

<!-- HTML format: contains rowspan -->
<table>
<tr><td rowspan="2">Row label</td><td><img src="media/cover.png" width="50"/></td></tr>
<tr><td>Second row</td></tr>
</table>
"""


class TestHtmlTableSplicing:
    def test_rowspan_table_and_image_survive_conversion(self, section_folder, tmp_path):
        (section_folder / "03.Section-Three.md").write_text(ROWSPAN_TABLE_SECTION_MD, encoding="utf-8")

        output = convert(section_folder, output=tmp_path / "out.docx")

        with zipfile.ZipFile(output) as z:
            doc_xml = z.read("word/document.xml").decode("utf-8")
            media_files = [n for n in z.namelist() if n.startswith("word/media/")]

        assert "<w:tbl" in doc_xml
        assert "vMerge" in doc_xml
        assert "<!-- HTML format" not in doc_xml
        # The cover PNG plus the table-cell image spliced in from the HTML fragment.
        assert len(media_files) >= 2

    def test_source_section_file_left_untouched(self, section_folder, tmp_path):
        (section_folder / "03.Section-Three.md").write_text(ROWSPAN_TABLE_SECTION_MD, encoding="utf-8")
        source_path = section_folder / "03.Section-Three.md"
        original_content = source_path.read_text(encoding="utf-8")

        convert(section_folder, output=tmp_path / "out.docx")

        assert source_path.read_text(encoding="utf-8") == original_content


class TestPageBreaks:
    def test_page_break_before_every_section(self, section_folder, tmp_path):
        output = convert(section_folder, output=tmp_path / "out.docx")

        with zipfile.ZipFile(output) as z:
            doc_xml = z.read("word/document.xml").decode("utf-8")

        # section_folder has two <n>.<Title>.md files, so two page breaks expected.
        assert doc_xml.count('w:type="page"') == 2


class TestNonMediaAssetFolders:
    def test_image_under_non_media_folder_is_embedded(self, section_folder, tmp_path):
        # rules/sad-sections.instructions.md explicitly allows images under
        # other relative folders, e.g. ./diagrams/diagram-name.svg - not just
        # media/. convert() must copy those folders into staging too, or
        # pandoc silently can't find the file and drops the image.
        diagrams_dir = section_folder / "diagrams"
        diagrams_dir.mkdir()
        svg_bytes = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
            b'<rect width="40" height="40" fill="blue"/></svg>'
        )
        (diagrams_dir / "diagram.svg").write_bytes(svg_bytes)

        (section_folder / "01.Section-One.md").write_text(
            SECTION_ONE_MD + "\n![A diagram](diagrams/diagram.svg)\n", encoding="utf-8"
        )

        output = convert(section_folder, output=tmp_path / "out.docx")

        with zipfile.ZipFile(output) as z:
            media_files = [n for n in z.namelist() if n.startswith("word/media/")]

        assert any(name.endswith(".svg") for name in media_files)


class TestTemplateResolution:
    def test_explicit_argument_overrides_env(self, tmp_path):
        explicit_template = tmp_path / "explicit.docx"
        explicit_template.write_bytes(b"fake")
        env_template = tmp_path / "env.docx"
        env_template.write_bytes(b"fake")
        (tmp_path / ".env").write_text(f"SAD_TEMPLATE={env_template}\n", encoding="utf-8")

        resolved = resolve_template(str(explicit_template), repo_root=tmp_path)
        assert resolved == explicit_template

    def test_falls_back_to_env(self, tmp_path):
        env_template = tmp_path / "env.docx"
        env_template.write_bytes(b"fake")
        (tmp_path / ".env").write_text(f"SAD_TEMPLATE={env_template}\n", encoding="utf-8")

        resolved = resolve_template(None, repo_root=tmp_path)
        assert resolved == env_template

    def test_no_template_resolved_warns_and_returns_none(self, tmp_path, capsys):
        resolved = resolve_template(None, repo_root=tmp_path)
        assert resolved is None
        assert "Warning" in capsys.readouterr().err

    def test_resolved_path_does_not_exist_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            resolve_template(str(tmp_path / "missing.docx"), repo_root=tmp_path)

    def test_env_resolved_path_does_not_exist_raises(self, tmp_path):
        (tmp_path / ".env").write_text("SAD_TEMPLATE=./missing.docx\n", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            resolve_template(None, repo_root=tmp_path)
