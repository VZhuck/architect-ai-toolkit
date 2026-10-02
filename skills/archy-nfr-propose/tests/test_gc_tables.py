import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import gc_tables as gt
from gc_tables import DocError, apply_changes, h2_tables, normalize_id, parse_lines, split_cells, template_base

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "skills/archy-init-nfr-taxonomy/taxonomy/nfr-req-tmpl.md"

GC = """# Non-Functional Requirements

Owner: platform team.

## Business Drivers & Goals

Our drivers.

| ID | Business Driver | Business Goal | Metric / Criteria | Priority |
| --- | --- | --- | --- | --- |
| BD-001 | Time to Market | EU launch | live by 2027-03-31 | Critical |

## Quality Attributes

Custom intro kept verbatim.

| ID | Quality Attribute | Requirement | Metric / Criteria | Priority | Owner |
|---|---|---|---|---|---|
| QAR-001 | Performance & Scalability | Checkout latency | p95 < 300 ms | High | Team A |
| QAR-002 | Resilience | Payment API availability | 99.9% monthly |  | Team B |
| QAR-003 | Performance & Scalability | Search latency | p95 < 800 ms | Medium | Team C |

## Assumptions

| ID | Assumption | Risk | Impact |
| --- | --- | --- | --- |
| ASM-001 | Peak load stays under 2,000 TPS | Capacity plan fails | High |

## Constraints

| ID | Constraint | Impact |
| --- | --- | --- |
| CSTR-001 | Azure EU regions only | High |

## Glossary

| Term | Meaning |
| --- | --- |
| TPS | transactions per second |
"""


def lines_of(text: str) -> list[str]:
    return text.splitlines(keepends=True)


# --- parse -----------------------------------------------------------------------


def test_parse_template():
    parsed = parse_lines(lines_of(TEMPLATE.read_text(encoding="utf-8")))
    assert parsed["errors"] == []
    assert list(parsed["records"]) == ["BD-001", "QAR-001", "ASM-001", "CSTR-001"]
    qar = parsed["records"]["QAR-001"]["fields"]
    assert qar["category"] == "Performance & Scalability"
    assert qar["metrics"] == "p95 < 500 ms @ 500 TPS"


def test_parse_gc_custom_column_and_text():
    parsed = parse_lines(lines_of(GC))
    assert parsed["errors"] == []
    section = parsed["sections"]["Quality Attributes"]
    assert section["custom_columns"] == ["Owner"]
    assert parsed["records"]["QAR-002"]["cells"]["Owner"] == "Team B"
    assert parsed["records"]["QAR-002"]["fields"]["priority"] == ""
    assert "TPS" not in parsed["records"]  # the Glossary table is not managed


def test_parse_shuffled_columns():
    text = GC.replace(
        "| ID | Constraint | Impact |\n| --- | --- | --- |\n| CSTR-001 | Azure EU regions only | High |",
        "| Impact | Constraint | ID |\n| --- | --- | --- |\n| High | Azure EU regions only | CSTR-001 |",
    )
    rec = parse_lines(lines_of(text))["records"]["CSTR-001"]
    assert rec["fields"] == {"id": "CSTR-001", "statement": "Azure EU regions only", "priority": "High"}


@pytest.mark.parametrize(
    "mutate, check",
    [
        (lambda t: t.replace("## Assumptions", "## Assumption list"), "section"),
        (lambda t: t.replace("| ID | Constraint | Impact |\n| --- | --- | --- |\n| CSTR-001 | Azure EU regions only | High |\n", "No table.\n"), "table"),
        (lambda t: t.replace("| ID | Assumption | Risk | Impact |", "| Key | Assumption | Risk | Impact |"), "id-column"),
        (lambda t: t.replace("QAR-003", "QAR-002"), "duplicate-id"),
        (lambda t: t.replace("| ASM-001 | Peak load stays under 2,000 TPS | Capacity plan fails | High |", "| ASM-001 | Peak load | High |"), "columns"),
        (lambda t: t.replace("| ID | Assumption | Risk | Impact |\n| --- | --- | --- | --- |", "| ID | Assumption | Risk | Impact |"), "table"),
    ],
)
def test_parse_errors(mutate, check):
    errors = parse_lines(lines_of(mutate(GC)))["errors"]
    assert any(e["check"] == check for e in errors), errors


def test_parse_error_names_line(tmp_path):
    doc = tmp_path / "gc.md"
    doc.write_text(GC.replace("QAR-003", "QAR-002"), encoding="utf-8")
    assert gt.main(["parse", "--doc", str(doc)]) == 1


def test_split_cells_escaped_pipe():
    assert split_cells("| a \\| b | c |") == ["a \\| b", "c"]


def test_normalize_id():
    assert normalize_id("qar-13") == "QAR-013"
    assert normalize_id("NFR-001") is None


# --- patch -----------------------------------------------------------------------


def test_patch_preserves_untouched_bytes():
    text = GC.replace("Custom intro kept verbatim.", "Custom intro kept verbatim.  \t")
    base = lines_of(text)
    changes = [
        {"op": "add", "id": "QAR-4", "fields": {"category": "Performance & Scalability", "statement": "Refund latency",
                                               "metrics": "p95 < 1 s", "priority": "Low"}, "after_id": "QAR-001"},
        {"op": "update", "id": "QAR-002", "fields": {"priority": "Critical"}},
        {"op": "add", "id": "CSTR-002", "fields": {"statement": "PCI | DSS scope", "priority": "High"}},
    ]
    out = apply_changes(base, changes)
    added = {"| QAR-004 | Performance & Scalability | Refund latency | p95 < 1 s | Low |  |\n",
             "| CSTR-002 | PCI \\| DSS scope | High |\n"}
    updated = "| QAR-002 | Resilience | Payment API availability | 99.9% monthly | Critical | Team B |\n"
    assert updated in out
    assert added <= set(out)
    rest = [l for l in out if l not in added and l != updated]
    assert rest == [l for l in base if not l.startswith("| QAR-002 ")]
    # QAR-004 placed right after QAR-001, before QAR-002
    ids = [l.split("|")[1].strip() for l in out if l.startswith("| QAR-")]
    assert ids == ["QAR-001", "QAR-004", "QAR-002", "QAR-003"]


def test_patch_remove_and_errors():
    out = apply_changes(lines_of(GC), [{"op": "remove", "id": "ASM-001"}])
    assert not any(l.startswith("| ASM-001") for l in out)
    with pytest.raises(DocError):
        apply_changes(lines_of(GC), [{"op": "add", "id": "QAR-001", "fields": {}}])
    with pytest.raises(DocError):
        apply_changes(lines_of(GC), [{"op": "update", "id": "QAR-099", "fields": {}}])


def test_patch_keeps_crlf():
    base = lines_of(GC.replace("\n", "\r\n"))
    out = apply_changes(base, [{"op": "add", "id": "ASM-002", "fields": {"statement": "x", "risk": "y", "priority": "Low"}}])
    assert all(l.endswith("\r\n") for l in out)


def test_patch_cli(tmp_path):
    doc = tmp_path / "gc.md"
    doc.write_text(GC, encoding="utf-8")
    changes = tmp_path / "c.json"
    changes.write_text(json.dumps({"changes": [{"op": "update", "id": "QAR-002", "fields": {"metrics": "99.95%"}}]}))
    out = tmp_path / "draft.md"
    assert gt.main(["patch", "--doc", str(doc), "--changes", str(changes), "--out", str(out)]) == 0
    assert "| QAR-002 | Resilience | Payment API availability | 99.95% |  | Team B |" in out.read_text()


# --- template base -----------------------------------------------------------------


def test_template_base_removes_samples_only(tmp_path):
    base = template_base(lines_of(TEMPLATE.read_text(encoding="utf-8")))
    parsed = parse_lines(base)
    assert parsed["errors"] == []
    assert all(not s["rows"] for s in parsed["sections"].values())
    original = TEMPLATE.read_text(encoding="utf-8").splitlines(keepends=True)
    assert [l for l in original if not l.startswith(("| BD-", "| QAR-", "| ASM-", "| CSTR-"))] == base


# --- generic registry reader --------------------------------------------------------


def test_h2_tables_reads_registry_sections():
    text = (REPO / "skills/archy-init-nfr-taxonomy/taxonomy/nfr-registry-log.md").read_text(encoding="utf-8")
    tables = h2_tables(text)
    assert tables["NFR Registry"][0]["NFR ID"] == "NFR-001"
    assert tables["Open Questions"][0]["Status"] == "TO REVIEW"
    assert tables["Conflicts"] == []
