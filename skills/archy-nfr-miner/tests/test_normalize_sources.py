import json
import sys
import zipfile
from pathlib import Path

import pypandoc
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import normalize_sources as ns
from normalize_sources import normalize, sha256_of, table_to_markdown

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DOCX = "test-data/Northwind-Cloud-Landing-Zone-SAD.docx"


# --- fixture builders --------------------------------------------------------------


def make_docx(path: Path) -> Path:
    """A docx with a heading, a table, a tracked insertion and a tracked deletion."""
    md = (
        "# Security\n\n"
        "Before **INSERTED** and *REMOVED* after.\n\n"
        "| Attribute | Target |\n|---|---|\n| Availability | 99.9% monthly |\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    plain = path.with_suffix(".plain.docx")
    pypandoc.convert_text(md, "docx", format="md", outputfile=str(plain))

    with zipfile.ZipFile(plain) as src:
        parts = {name: src.read(name) for name in src.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    ins = '<w:r><w:rPr><w:b /><w:bCs /></w:rPr><w:t xml:space="preserve">INSERTED</w:t></w:r>'
    dele = '<w:r><w:rPr><w:i /><w:iCs /></w:rPr><w:t xml:space="preserve">REMOVED</w:t></w:r>'
    assert ins in xml and dele in xml, "pandoc docx run layout changed; update the fixture"
    xml = xml.replace(
        ins,
        '<w:ins w:id="1" w:author="t" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:t xml:space="preserve">INSERTED</w:t></w:r></w:ins>',
    ).replace(
        dele,
        '<w:del w:id="2" w:author="t" w:date="2026-01-01T00:00:00Z">'
        '<w:r><w:delText xml:space="preserve">REMOVED</w:delText></w:r></w:del>',
    )
    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        for name, data in parts.items():
            out.writestr(name, data)
    plain.unlink()
    return path


def _pdf_text(x: float, y: float, text: str) -> str:
    return f"BT /F1 11 Tf {x} {y} Td ({text}) Tj ET"


def _pdf_grid(x0: float, y_top: float, col_w: float, row_h: float, rows: list[list[str]]) -> list[str]:
    ops = []
    n_rows, n_cols = len(rows), len(rows[0])
    for r in range(n_rows + 1):
        y = y_top - r * row_h
        ops.append(f"{x0} {y} m {x0 + n_cols * col_w} {y} l S")
    for c in range(n_cols + 1):
        x = x0 + c * col_w
        ops.append(f"{x} {y_top} m {x} {y_top - n_rows * row_h} l S")
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            ops.append(_pdf_text(x0 + c * col_w + 5, y_top - (r + 1) * row_h + 7, cell))
    return ops


def make_pdf(path: Path, pages: list[list[str]]) -> Path:
    """Minimal PDF writer: each page is a list of content-stream operators."""
    objects: list[bytes] = []
    n = len(pages)
    font_id = 3 + 2 * n
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    for i, ops in enumerate(pages):
        stream = "\n".join(ops).encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {4 + 2 * i} 0 R >>".encode()
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path


def make_text_pdf(path: Path) -> Path:
    return make_pdf(
        path,
        [
            [_pdf_text(72, 720, "Page one says RTO is 4 hours.")],
            [
                _pdf_text(72, 720, "Above the table."),
                *_pdf_grid(72, 680, 150, 20, [["Metric", "Target"], ["Latency", "p95 300ms"]]),
                _pdf_text(72, 560, "Below the table."),
            ],
            [_pdf_text(72, 720, "Page three closes.")],
        ],
    )


def make_image_only_pdf(path: Path) -> Path:
    """One page holding a 1x1 inline image and no text, like a scan."""
    return make_pdf(path, [["q 100 0 0 100 72 600 cm BI /W 1 /H 1 /CS /G /BPC 8 ID A EI Q"]])


def add_docx_media(path: Path, count: int) -> Path:
    with zipfile.ZipFile(path, "a") as archive:
        for i in range(count):
            archive.writestr(f"word/media/image{i + 1}.png", b"png")
    return path


@pytest.fixture
def project(tmp_path):
    make_docx(tmp_path / "docs/SAD.docx")
    make_text_pdf(tmp_path / "docs/notes.pdf")
    make_image_only_pdf(tmp_path / "docs/scan.pdf")
    (tmp_path / "docs/nfr.md").write_text("# NFR\n", encoding="utf-8")
    (tmp_path / "docs/broken.docx").write_bytes(b"not a zip")
    (tmp_path / "docs/broken.pdf").write_bytes(b"%PDF-1.4 garbage")
    return tmp_path


def _run(project: Path, *files: str, **kwargs) -> dict:
    run_dir = project / "ai-workflow/nfr-state/run-1"
    result = normalize(list(files), project, run_dir, **kwargs)
    return {f["path"]: f for f in result["files"]}


def _record_state(project: Path, entries: dict[str, str]) -> None:
    run_dir = project / "ai-workflow/nfr-state/run-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {"files_4_review": [{"path": p, "sha256": s} for p, s in entries.items()]}
    (run_dir / "state.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")


# --- docx ------------------------------------------------------------------------


def test_docx_single_file_with_table_and_accepted_changes(project):
    result = _run(project, "docs/SAD.docx")["docs/SAD.docx"]

    assert result["status"] == "converted"
    assert result["normalized"] == "sources/docs/SAD.docx.md"
    text = (project / "ai-workflow/nfr-state/run-1" / result["normalized"]).read_text()
    assert "# Security" in text
    assert "Before INSERTED and after." in text  # insertion kept, deletion dropped
    assert "REMOVED" not in text
    assert "| Availability | 99.9% monthly |" in text


def test_docx_paragraph_stays_on_one_line(project):
    long_para = " ".join(["word"] * 200)
    pypandoc.convert_text(long_para, "docx", format="md", outputfile=str(project / "docs/long.docx"))

    result = _run(project, "docs/long.docx")["docs/long.docx"]
    text = (project / "ai-workflow/nfr-state/run-1" / result["normalized"]).read_text()
    assert long_para in text.splitlines()


# --- pdf -------------------------------------------------------------------------


def test_pdf_page_markers_and_table_once(project):
    result = _run(project, "docs/notes.pdf")["docs/notes.pdf"]

    assert result["status"] == "converted"
    text = (project / "ai-workflow/nfr-state/run-1/sources/docs/notes.pdf.md").read_text()
    markers = [text.index(f"<!-- page {n} -->") for n in (1, 2, 3)]
    assert markers == sorted(markers)
    assert "RTO is 4 hours" in text
    assert "| Latency | p95 300ms |" in text
    assert text.count("p95 300ms") == 1  # table cut out of the page text
    assert text.index("Above the table.") < text.index("| Metric") < text.index("Below the table.")


def test_scanned_pdf_fails_without_blocking_others(project):
    results = _run(project, "docs/scan.pdf", "docs/notes.pdf")

    assert results["docs/scan.pdf"]["status"] == "failed"
    assert "no extractable text" in results["docs/scan.pdf"]["reason"]
    assert results["docs/scan.pdf"]["normalized"] == ""
    assert results["docs/scan.pdf"]["images"] == 1  # the scan's images are still counted
    assert results["docs/notes.pdf"]["status"] == "converted"


# --- common ------------------------------------------------------------------------


def test_corrupt_files_fail_and_others_convert(project):
    results = _run(project, "docs/broken.docx", "docs/broken.pdf", "docs/SAD.docx")

    assert results["docs/broken.docx"]["status"] == "failed"
    assert results["docs/broken.pdf"]["status"] == "failed"
    assert results["docs/broken.docx"]["reason"]
    assert results["docs/SAD.docx"]["status"] == "converted"


def test_markdown_is_mined_in_place(project):
    result = _run(project, "docs/nfr.md")["docs/nfr.md"]
    assert result["status"] == "in-place"
    assert result["normalized"] == ""
    assert result["sha256"] == sha256_of(project / "docs/nfr.md")


def test_unchanged_source_is_not_converted_again(project):
    first = _run(project, "docs/SAD.docx")["docs/SAD.docx"]
    _record_state(project, {"docs/SAD.docx": first["sha256"]})

    assert _run(project, "docs/SAD.docx")["docs/SAD.docx"]["status"] == "unchanged"
    assert _run(project, "docs/SAD.docx", force=True)["docs/SAD.docx"]["status"] == "converted"


def test_image_count_survives_unchanged(project):
    add_docx_media(project / "docs/SAD.docx", 2)
    first = _run(project, "docs/SAD.docx")["docs/SAD.docx"]
    _record_state(project, {"docs/SAD.docx": first["sha256"]})
    second = _run(project, "docs/SAD.docx")["docs/SAD.docx"]

    assert first["images"] == 2
    assert second["status"] == "unchanged"
    assert second["images"] == 2


def test_changed_source_is_converted_again(project):
    _run(project, "docs/SAD.docx")
    _record_state(project, {"docs/SAD.docx": "old-hash"})

    assert _run(project, "docs/SAD.docx")["docs/SAD.docx"]["status"] == "converted"


def test_missing_source_fails(project):
    result = _run(project, "docs/gone.pdf")["docs/gone.pdf"]
    assert result["status"] == "failed"
    assert result["reason"] == "source file not found"


def test_table_to_markdown_escapes_cells():
    assert table_to_markdown([["A", "B"], ["x|y", "line1\nline2"], [None, ""]]) == (
        "| A | B |\n| --- | --- |\n| x\\|y | line1<br>line2 |"
    )


# --- CLI -------------------------------------------------------------------------


def test_main_on_sample_docx(tmp_path, capsys):
    run_dir = tmp_path / "run"
    assert ns.main(["--root", str(REPO_ROOT), "--run-dir", str(run_dir), "--file", SAMPLE_DOCX]) == 0

    result = json.loads(capsys.readouterr().out)
    entry = result["files"][0]
    assert entry["status"] == "converted"
    assert entry["images"] > 0
    assert (run_dir / "sources" / f"{SAMPLE_DOCX}.md").read_text().strip()
