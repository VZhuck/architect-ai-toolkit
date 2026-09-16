"""Unit tests for the NFR document validator.

The validator is the aait-nfr pipeline's enforcement mechanism: publish promotes
a draft only when this script passes. Each failure mode below is a way an
under-refined or mis-classified document could otherwise reach the deliverable.

The regression that matters most is test_regulation_name_in_driver_passes - a
legitimate business driver naming a regulation must not trip the technical
vocabulary scan.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from validate_nfr import validate  # noqa: E402

CATALOG_DIR = SKILL_DIR / "templates"

CLEAN = """# Non-Functional Requirements

Intro paragraph.

## Business Drivers & Goals

| ID | Business Driver | Goal / Business Impact | Priority |
| --- | --- | --- | :-: |
| BD-01 | Risk & Compliance | ContosoX incurs a EUR 2m penalty if PCI-DSS 4.0 certification is not achieved by 30/06/2027 | P0 |
| BD-02 | Increase Revenue | Cart abandonment above 12% costs ~£400k per quarter | P0 |

## Quality Attribute Requirements

Explanatory paragraph.

| ID | Quality Attribute | Requirement | Priority | Driver |
| --- | --- | --- | :-: | --- |
| QAR-01 | Performance & Scalability | p95 checkout latency < 2s at 500 concurrent users | P0 | BD-02 |
| QAR-02 | Performance & Scalability | Sustains 1,000 TPS peak; scale-out lag < 60s | P1 | BD-02 |
| QAR-07 | Security & Privacy | PII erased within 30 days of a verified subject request | P0 | BD-01 |
| QAR-08 | Usability & Accessibility | WCAG 2.2 AA conformance across all public journeys | P1 | — |

## Constraints

- Deployment restricted to EU Azure regions (data residency, legal review 2026-03-11)

## Assumptions

- Peak load stays below 1,500 TPS through FY27 (capacity plan invalid if exceeded) </br>
Derived from the 2026 volume forecast; revisit if a new market launches.
"""


def write(tmp_path: Path, text: str) -> Path:
    doc = tmp_path / "nfr.md"
    doc.write_text(text, encoding="utf-8")
    return doc


def failures(doc: Path) -> list:
    return [f for f in validate(doc, CATALOG_DIR) if f.level == "fail"]


def checks(doc: Path) -> set:
    return {f.check for f in failures(doc)}


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------


def test_clean_document_passes(tmp_path: Path):
    assert failures(write(tmp_path, CLEAN)) == []


def test_validator_never_modifies_the_document(tmp_path: Path):
    doc = write(tmp_path, CLEAN)
    before = doc.read_text(encoding="utf-8")
    validate(doc, CATALOG_DIR)
    assert doc.read_text(encoding="utf-8") == before


def test_template_placeholder_rows_are_ignored(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("| BD-02 | Increase Revenue", "| BD-02 |  |  |  |\n| BD-03 | Increase Revenue"))
    assert "catalog-fidelity" not in checks(doc)


# --------------------------------------------------------------------------
# Catalog fidelity
# --------------------------------------------------------------------------


def test_paraphrased_attribute_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("| Security & Privacy |", "| Security |"))
    found = [f for f in failures(doc) if f.check == "catalog-fidelity"]
    assert found
    assert "Security & Privacy" in found[0].message, "should hint at the catalog spelling"


def test_recased_attribute_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("| Performance & Scalability |", "| performance & scalability |"))
    assert "catalog-fidelity" in checks(doc)


def test_invented_attribute_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("| Operability |", "| Observability |"))
    doc = write(tmp_path, CLEAN.replace("| Usability & Accessibility |", "| Observability |"))
    assert "catalog-fidelity" in checks(doc)


def test_invented_business_driver_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("| Increase Revenue |", "| Customer Delight |"))
    assert "catalog-fidelity" in checks(doc)


def test_more_driver_rows_than_the_catalog_fails(tmp_path: Path):
    extra = (
        "| BD-03 | Time to Market | Launch by Q3 2027 | P1 |\n"
        "| BD-04 | Cost Optimization | Save $1m annually by 2028 | P1 |\n"
        "| BD-05 | Time to Market | Second launch by Q4 2027 | P2 |\n"
    )
    doc = write(tmp_path, CLEAN.replace("\n## Quality Attribute Requirements", f"{extra}\n## Quality Attribute Requirements"))
    found = [f for f in failures(doc) if f.check == "catalog-fidelity"]
    assert any("catalog defines only" in f.message for f in found)


# --------------------------------------------------------------------------
# Business / technical separation
# --------------------------------------------------------------------------


def test_regulation_name_in_driver_passes(tmp_path: Path):
    """Regression: a driver may name a regulation without being "technical"."""
    doc = write(tmp_path, CLEAN)
    assert "business-separation" not in checks(doc)


@pytest.mark.parametrize(
    "technical",
    [
        "Reduce p95 latency to under 200ms by 2027",
        "Achieve 99.99% uptime by 2027",
        "Encryption at rest for all PII by 2027",
        "RTO under 15 minutes by 2027",
    ],
)
def test_technical_vocabulary_in_driver_fails(tmp_path: Path, technical: str):
    doc = write(
        tmp_path,
        CLEAN.replace("Cart abandonment above 12% costs ~£400k per quarter", technical),
    )
    found = [f for f in failures(doc) if f.check == "business-separation"]
    assert any("technical vocabulary" in f.message for f in found)


def test_driver_without_money_or_date_fails(tmp_path: Path):
    doc = write(
        tmp_path,
        CLEAN.replace(
            "Cart abandonment above 12% costs ~£400k per quarter",
            "Improve our standing with enterprise buyers",
        ),
    )
    found = [f for f in failures(doc) if f.check == "business-separation"]
    assert any("no monetary amount, date, or market position" in f.message for f in found)


@pytest.mark.parametrize(
    "driver",
    [
        "Regulatory exclusivity makes us the only route to the clearing house",
        "Implement new revenue streams for third-party operators",
        "Failure forfeits market access to partner agencies",
        "Breach of the contractual obligation costs us the operating licence",
        "We become the sole provider for private road operators",
    ],
)
def test_market_position_without_money_or_date_passes(tmp_path: Path, driver: str):
    """business-drivers.md admits "money, a date, OR market position" as a driver."""
    doc = write(
        tmp_path, CLEAN.replace("Cart abandonment above 12% costs ~£400k per quarter", driver)
    )
    assert "business-separation" not in checks(doc)


@pytest.mark.parametrize(
    "driver",
    [
        "Reach the German market before the FY27 close",
        "Penalty of €2m if uncertified",
        "Saves $400k per year",
        "Certification required by 30/06/2027",
    ],
)
def test_money_or_date_variants_pass(tmp_path: Path, driver: str):
    doc = write(
        tmp_path, CLEAN.replace("Cart abandonment above 12% costs ~£400k per quarter", driver)
    )
    assert "business-separation" not in checks(doc)


# --------------------------------------------------------------------------
# Measurability
# --------------------------------------------------------------------------


def test_unmeasurable_requirement_fails(tmp_path: Path):
    doc = write(
        tmp_path,
        CLEAN.replace("WCAG 2.2 AA conformance across all public journeys", "The system should be easy to use"),
    )
    found = [f for f in failures(doc) if f.check == "measurability"]
    assert any("no threshold" in f.message for f in found)


@pytest.mark.parametrize("marker", ["(proposed)", "TBD"])
def test_pending_requirement_warns_but_does_not_fail(tmp_path: Path, marker: str):
    doc = write(
        tmp_path,
        CLEAN.replace(
            "WCAG 2.2 AA conformance across all public journeys",
            f"Availability target still to be agreed {marker}",
        ),
    )
    assert "measurability" not in checks(doc)
    assert any(f.check == "measurability" and f.level == "warn" for f in validate(doc, CATALOG_DIR))


def test_standards_conformance_counts_as_measurable(tmp_path: Path):
    doc = write(tmp_path, CLEAN)
    assert "measurability" not in checks(doc), "WCAG 2.2 AA conformance is a threshold"


# --------------------------------------------------------------------------
# P0 budget
# --------------------------------------------------------------------------


def test_p0_budget_exceeded_fails(tmp_path: Path):
    extra = "".join(
        f"| QAR-1{n} | Operability | MTTD under {n + 1} minutes for incidents | P0 | — |\n"
        for n in range(5)
    )
    doc = write(tmp_path, CLEAN.replace("\n## Constraints", f"{extra}\n## Constraints"))
    found = [f for f in failures(doc) if f.check == "p0-budget"]
    assert found and "budget is 7" in found[0].message


def test_exactly_seven_p0_passes(tmp_path: Path):
    extra = "".join(
        f"| QAR-1{n} | Operability | MTTD under {n + 1} minutes for incidents | P0 | — |\n"
        for n in range(3)
    )
    doc = write(tmp_path, CLEAN.replace("\n## Constraints", f"{extra}\n## Constraints"))
    assert "p0-budget" not in checks(doc)


# --------------------------------------------------------------------------
# Priority locks
# --------------------------------------------------------------------------


def git_repo(tmp_path: Path, text: str) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    doc = write(tmp_path, text)
    subprocess.run(["git", "add", "nfr.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    return doc


LOCKED = CLEAN.replace("| P0 | BD-02 |", "| P0 \U0001f512 | BD-02 |")


def test_altered_lock_fails_against_head(tmp_path: Path):
    doc = git_repo(tmp_path, LOCKED)
    doc.write_text(LOCKED.replace("| P0 \U0001f512 | BD-02 |", "| P1 \U0001f512 | BD-02 |"), encoding="utf-8")
    found = [f for f in failures(doc) if f.check == "priority-lock"]
    assert found and "QAR-01" in found[0].message


def test_unchanged_lock_passes_against_head(tmp_path: Path):
    doc = git_repo(tmp_path, LOCKED)
    assert "priority-lock" not in checks(doc)


def test_no_head_version_warns_rather_than_fails(tmp_path: Path):
    """Outside a repo, or before the first commit, locks cannot be verified."""
    doc = write(tmp_path, LOCKED)
    assert "priority-lock" not in checks(doc)
    warns = [f for f in validate(doc, CATALOG_DIR) if f.check == "priority-lock"]
    assert warns and warns[0].level == "warn"
    assert "no git HEAD" in warns[0].message


# --------------------------------------------------------------------------
# Structure and SAD rules
# --------------------------------------------------------------------------


def test_missing_section_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("## Constraints", "## Something Else"))
    found = [f for f in failures(doc) if f.check == "structure"]
    assert any("Constraints" in f.message for f in found)


@pytest.mark.parametrize(
    "legacy,expected",
    [
        ("Business Quality Attribures", "Business Drivers & Goals"),
        ("Constrains", "Constraints"),
    ],
)
def test_legacy_headings_are_reported(tmp_path: Path, legacy: str, expected: str):
    section = "Business Drivers & Goals" if "Attribures" in legacy else "Constraints"
    doc = write(tmp_path, CLEAN.replace(f"## {section}", f"## {legacy}"))
    found = [f for f in failures(doc) if f.check == "legacy-heading"]
    assert found and expected in found[0].message


def test_second_h1_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN + "\n# Second Title\n")
    found = [f for f in failures(doc) if f.check == "sad-rules"]
    assert any("more than one H1" in f.message for f in found)


def test_heading_without_blank_line_before_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("\n\n## Constraints", "\n## Constraints"))
    found = [f for f in failures(doc) if f.check == "sad-rules"]
    assert any("no empty line before heading" in f.message for f in found)


def test_html_table_without_comment_fails(tmp_path: Path):
    doc = write(tmp_path, CLEAN + "\n<table><tr><td>x</td></tr></table>\n")
    found = [f for f in failures(doc) if f.check == "sad-rules"]
    assert any("HTML table" in f.message for f in found)


def test_html_table_with_explanatory_comment_passes(tmp_path: Path):
    doc = write(
        tmp_path,
        CLEAN + "\n<!-- This table uses HTML formatting to preserve merged cells -->\n\n<table><tr><td>x</td></tr></table>\n",
    )
    assert "sad-rules" not in checks(doc)


# --------------------------------------------------------------------------
# Assumptions
# --------------------------------------------------------------------------


def test_assumption_without_impact_fails(tmp_path: Path):
    doc = write(
        tmp_path,
        CLEAN.replace(
            "- Peak load stays below 1,500 TPS through FY27 (capacity plan invalid if exceeded) </br>",
            "- Peak load stays below 1,500 TPS through FY27 </br>",
        ),
    )
    found = [f for f in failures(doc) if f.check == "assumptions"]
    assert found and "no impact" in found[0].message


def test_assumption_without_explanation_fails(tmp_path: Path):
    doc = write(
        tmp_path,
        CLEAN.replace(
            "Derived from the 2026 volume forecast; revisit if a new market launches.\n",
            "",
        ),
    )
    found = [f for f in failures(doc) if f.check == "assumptions"]
    assert any("no explanation" in f.message for f in found)


# --------------------------------------------------------------------------
# CLI contract
# --------------------------------------------------------------------------


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / "validate_nfr.py"), *args],
        capture_output=True,
        text=True,
    )


def test_cli_exit_zero_on_clean(tmp_path: Path):
    doc = write(tmp_path, CLEAN)
    result = run_cli("--doc", str(doc), "--catalog-dir", str(CATALOG_DIR))
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_cli_exit_one_on_failure(tmp_path: Path):
    doc = write(tmp_path, CLEAN.replace("| Security & Privacy |", "| Security |"))
    result = run_cli("--doc", str(doc), "--catalog-dir", str(CATALOG_DIR))
    assert result.returncode == 1
    assert "FAIL" in result.stdout


def test_cli_exit_two_on_missing_document(tmp_path: Path):
    result = run_cli("--doc", str(tmp_path / "nope.md"), "--catalog-dir", str(CATALOG_DIR))
    assert result.returncode == 2


def test_cli_exit_two_on_missing_catalog(tmp_path: Path):
    doc = write(tmp_path, CLEAN)
    result = run_cli("--doc", str(doc), "--catalog-dir", str(tmp_path / "nope"))
    assert result.returncode == 2
