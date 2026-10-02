import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_draft import check, load_catalogs
from gc_tables import apply_changes
from test_gc_tables import GC, lines_of

REPO = Path(__file__).resolve().parents[3]
CATALOGS = load_catalogs(REPO / "skills/archy-init-nfr-taxonomy/taxonomy")

ADD = {"op": "add", "id": "QAR-004", "after_id": "QAR-001",
       "fields": {"category": "Performance & Scalability", "statement": "Refund latency", "metrics": "p95 < 1 s"}}
UPDATE = {"op": "update", "id": "QAR-002", "fields": {"priority": "High"}}


def run(changes, draft=None, forbid=None, claim=None):
    base = lines_of(GC)
    draft = draft if draft is not None else apply_changes(base, changes)
    return check(base, draft, claim if claim is not None else changes, CATALOGS, forbid)


def checks(result):
    return {e["check"] for e in result["errors"]}


def test_legitimate_add_and_update_pass():
    result = run([ADD, UPDATE])
    assert result["ok"], result["errors"]


def test_changed_intro_word_fails_with_line():
    draft = [l.replace("Custom intro kept verbatim.", "Custom intro kept verbally.") for l in apply_changes(lines_of(GC), [ADD])]
    result = run([ADD], draft=draft)
    assert "preservation" in checks(result)
    err = next(e for e in result["errors"] if e["check"] == "preservation")
    assert err["line"] and "verbally" in err["draft"]


def test_unclaimed_row_change_fails():
    draft = apply_changes(lines_of(GC), [UPDATE])
    result = run([UPDATE], draft=draft, claim=[])
    assert any(e.get("id") == "QAR-002" for e in result["errors"])


def test_unclaimed_add_and_remove_fail():
    draft = apply_changes(lines_of(GC), [ADD, {"op": "remove", "id": "ASM-001"}])
    result = run([], draft=draft, claim=[])
    ids = {e.get("id") for e in result["errors"] if e["check"] == "preservation"}
    assert {"QAR-004", "ASM-001"} <= ids


def test_reordered_untouched_rows_fail():
    base = lines_of(GC)
    i1 = next(i for i, l in enumerate(base) if l.startswith("| QAR-001"))
    i3 = next(i for i, l in enumerate(base) if l.startswith("| QAR-003"))
    draft = list(base)
    draft[i1], draft[i3] = draft[i3], draft[i1]
    assert "preservation" in checks(run([], draft=draft))


def test_broken_table_fails():
    draft = [l.replace("| ASM-001 | Peak load stays under 2,000 TPS | Capacity plan fails | High |",
                       "| ASM-001 | Peak load | High |") for l in lines_of(GC)]
    assert "tables" in checks(run([], draft=draft, claim=[{"op": "update", "id": "ASM-001"}]))


def test_new_id_format_and_section():
    bad_format = {**ADD, "id": "PERF-9"}
    result = run([bad_format], draft=apply_changes(lines_of(GC), [{**ADD, "id": "PERF-9", "section": "Quality Attributes"}]))
    assert "ids" in checks(result)
    wrong_section = {"op": "add", "id": "CSTR-005", "section": "Quality Attributes",
                     "fields": {"category": "Resilience", "statement": "x"}}
    assert "ids" in checks(run([wrong_section]))


def test_duplicate_id_fails():
    draft = apply_changes(lines_of(GC), [ADD])
    draft = [l.replace("| QAR-004 |", "| QAR-003 |") for l in draft]
    assert "ids" in checks(run([ADD], draft=draft))


def test_category_must_be_catalog_name():
    bad = {**ADD, "fields": {**ADD["fields"], "category": "Performance"}}
    assert "categories" in checks(run([bad]))


def test_unclaimed_noncatalog_category_is_warning():
    base_text = GC.replace("| QAR-003 | Performance & Scalability |", "| QAR-003 | Speed |")
    base = lines_of(base_text)
    result = check(base, base, [], CATALOGS)
    assert result["ok"] and result["warnings"]


def test_forbidden_id_rendered():
    assert "forbidden" in checks(run([ADD], forbid=["qar-4"]))
