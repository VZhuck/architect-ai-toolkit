#!/usr/bin/env python3
"""Validate a Non-Functional Requirements document.

This script is the aait-nfr pipeline's enforcement mechanism. /aait:nfr-publish
renders a draft, runs this validator, and promotes to the target document only
on exit code 0. That is what makes premature publishing safe: an under-refined
draft fails here instead of corrupting the deliverable.

It is also runnable standalone on any NFR document - no sources, draft, or
trace file required - so a document produced elsewhere can be audited.

The script never modifies the document it validates.

Exit codes:
  0  all checks passed (warnings may still be reported)
  1  one or more checks failed
  2  the document or a catalog could not be read

Usage:
  uv run python skills/aait-nfr/scripts/validate_nfr.py --doc sad/08.Non-Functional-Requirements.md
  uv run python skills/aait-nfr/scripts/validate_nfr.py --doc <path> --catalog-dir skills/aait-nfr/templates
  uv run python skills/aait-nfr/scripts/validate_nfr.py --doc <path> --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Document vocabulary
# --------------------------------------------------------------------------

DRIVERS_SECTION = "Business Drivers & Goals"
QAR_SECTION = "Quality Attribute Requirements"
CONSTRAINTS_SECTION = "Constraints"
ASSUMPTIONS_SECTION = "Assumptions"

REQUIRED_SECTIONS = [
    DRIVERS_SECTION,
    QAR_SECTION,
    CONSTRAINTS_SECTION,
    ASSUMPTIONS_SECTION,
]

# Retired headings, mapped to their replacement. Reported, never rewritten.
LEGACY_HEADINGS = {
    "Business Quality Attribures": DRIVERS_SECTION,
    "Business Quality Attributes": DRIVERS_SECTION,
    "Quality Attributes": QAR_SECTION,
    "Constrains": CONSTRAINTS_SECTION,
}

MAX_P0 = 7
LOCK_MARKER = "\N{LOCK}"

# --------------------------------------------------------------------------
# Business / technical separation
#
# Mechanism and measurement vocabulary only. Regulation and standard names are
# deliberately absent: "PCI-DSS 4.0 certification by 30/06/2027" is a
# legitimate business driver and must pass.
# --------------------------------------------------------------------------

TECHNICAL_TOKENS = [
    r"\blatenc(?:y|ies)\b",
    r"\bthroughput\b",
    r"\buptime\b",
    r"\bdowntime\b",
    r"\bRTO\b",
    r"\bRPO\b",
    r"\bMTTR\b",
    r"\bMTBF\b",
    r"\bMTTD\b",
    r"\bSLO\b",
    r"\b[TQR]PS\b",
    r"\bp\d{2}\b",
    r"\bpercentile\b",
    r"\bencrypt(?:ed|ion)\b",
    r"\bTLS\b",
    r"\bmTLS\b",
    r"\bPII\b",
    r"\bauth[nz]\b",
    r"\bauthentication\b",
    r"\bauthorization\b",
    r"\bauthorisation\b",
    r"\bAPI\b",
    r"\bendpoint\b",
    r"\bdatabase\b",
    r"\bcache\b",
    r"\bfailover\b",
    r"\breplica(?:tion)?\b",
    r"\bbackup\b",
    r"\bmilliseconds?\b",
    r"\bconcurrent users\b",
    r"\d+\s*ms\b",
    r"\bnines\b",
]

MONEY_PATTERNS = [
    r"[€£$¥₹]\s?\d",
    r"\d+(?:[.,]\d+)?\s?(?:[kmb]n?|bn)?\s?(?:EUR|USD|GBP|JPY|INR)\b",
    r"\b(?:EUR|USD|GBP|JPY|INR)\s?\d",
]

DATE_PATTERNS = [
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\bQ[1-4]\s?(?:FY)?\d{2,4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    r"\b(?:19|20)\d{2}\b",
    r"\bwithin\s+\d+\s+(?:day|week|month|year)s?\b",
    r"\bby\s+(?:end\s+of\s+)?(?:FY)?\d{2,4}\b",
    r"\bFY\s?\d{2,4}\b",
]

# business-drivers.md: a driver "carries money, a date, or market position".
# Market position is the third of those - a driver may state what market the
# business wins, keeps, or is shut out of, without naming a figure or a date.
MARKET_POSITION_PATTERNS = [
    r"\bmarket\s+(?:access|position|share|entry)\b",
    r"\bexclusiv(?:e|ity)\b",
    r"\bnew\s+(?:revenue\s+)?(?:stream|market)s?\b",
    r"\bsole\s+(?:route|provider|supplier|operator)\b",
    r"\blicen[cs]e\b",
    r"\bcontractual\s+obligations?\b",
]

# --------------------------------------------------------------------------
# Measurability
# --------------------------------------------------------------------------

PENDING_MARKERS = [r"\(proposed\)", r"\bTBD\b"]

UNIT_TOKENS = [
    r"\bms\b",
    r"\bseconds?\b",
    r"\bsecs?\b",
    r"\bminutes?\b",
    r"\bmins?\b",
    r"\bhours?\b",
    r"\bhrs?\b",
    r"\bdays?\b",
    r"\bweeks?\b",
    r"\bmonths?\b",
    r"%",
    r"\b[TQR]PS\b",
    r"\b[KMGT]B\b",
    r"\busers?\b",
    r"\brequests?\b",
    r"\btransactions?\b",
    r"\bnines\b",
]

OPERATOR_TOKENS = [r"[<>≤≥]", r"<=", r">=", r"\bp\d{2}\b", r"\bat least\b", r"\bno more than\b"]

# Standards conformance counts as a threshold even without a numeric unit.
STANDARD_TOKENS = [
    r"\bWCAG\b",
    r"\bconformance\b",
    r"\bcompliant\b",
    r"\bcertifi(?:ed|cation)\b",
    r"\blevel\s+A{1,3}\b",
    r"\bISO\s?\d",
    r"\bSOC\s?2\b",
]


@dataclass
class Finding:
    level: str  # "fail" | "warn"
    check: str
    location: str
    message: str


@dataclass
class Table:
    heading: str
    headers: list[str]
    rows: list[dict[str, str]]
    line_numbers: list[int] = field(default_factory=list)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def strip_comments(text: str) -> str:
    """Blank out HTML comments so template guidance never trips a content check.

    Line breaks inside a comment are preserved, so every line number reported
    against the stripped text still matches the file on disk.
    """
    return re.sub(
        r"<!--.*?-->",
        lambda m: "\n" * m.group(0).count("\n"),
        text,
        flags=re.DOTALL,
    )


def parse_tables(text: str) -> dict[str, Table]:
    """Parse markdown tables, keyed by the nearest preceding heading."""
    tables: dict[str, Table] = {}
    heading = ""
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        heading_match = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if heading_match:
            heading = heading_match.group(1)
            i += 1
            continue

        if line.strip().startswith("|") and i + 1 < len(lines):
            separator = lines[i + 1].strip()
            if re.match(r"^\|[\s:|-]+\|$", separator):
                headers = [c.strip() for c in line.strip().strip("|").split("|")]
                rows: list[dict[str, str]] = []
                numbers: list[int] = []
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                    cells += [""] * (len(headers) - len(cells))
                    rows.append(dict(zip(headers, cells)))
                    numbers.append(j + 1)
                    j += 1
                if heading not in tables:
                    tables[heading] = Table(heading, headers, rows, numbers)
                i = j
                continue
        i += 1

    return tables


def parse_headings(text: str) -> list[tuple[int, int, str]]:
    """Return (line number, level, title) for every ATX heading."""
    out = []
    for n, line in enumerate(text.split("\n"), start=1):
        match = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if match:
            out.append((n, len(match.group(1)), match.group(2)))
    return out


def parse_catalog_names(path: Path) -> list[str]:
    """Extract the first-column attribute names from a catalog markdown table."""
    names: list[str] = []
    for table in parse_tables(strip_comments(path.read_text(encoding="utf-8"))).values():
        if not table.headers:
            continue
        key = table.headers[0]
        for row in table.rows:
            raw = row.get(key, "").strip()
            cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", raw).strip()
            if cleaned and not cleaned.startswith("-"):
                names.append(cleaned)
        if names:
            break
    return names


def matches_any(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        found = re.search(pattern, text, re.IGNORECASE)
        if found:
            return found.group(0)
    return None


def is_placeholder(row: dict[str, str]) -> bool:
    """Template placeholder rows carry an ID but no content."""
    values = [v for k, v in row.items() if k.lower() != "id"]
    return all(not v.strip() for v in values)


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_structure(text: str, raw: str, findings: list[Finding]) -> None:
    headings = parse_headings(text)
    titles = {t for _, _, t in headings}

    for section in REQUIRED_SECTIONS:
        if section not in titles:
            findings.append(
                Finding("fail", "structure", section, f"required section is missing: {section}")
            )

    for line_no, _, title in headings:
        if title in LEGACY_HEADINGS and title not in REQUIRED_SECTIONS:
            findings.append(
                Finding(
                    "fail",
                    "legacy-heading",
                    f"line {line_no}",
                    f"retired heading {title!r}; use {LEGACY_HEADINGS[title]!r}",
                )
            )

    h1s = [(n, t) for n, level, t in headings if level == 1]
    if len(h1s) == 0:
        findings.append(Finding("fail", "sad-rules", "document", "no H1 heading"))
    elif len(h1s) > 1:
        extra = ", ".join(f"line {n} ({t!r})" for n, t in h1s[1:])
        findings.append(
            Finding("fail", "sad-rules", "document", f"more than one H1: {extra}")
        )
    elif h1s[0][0] != 1:
        findings.append(
            Finding("fail", "sad-rules", f"line {h1s[0][0]}", "H1 is not at the file start")
        )

    lines = text.split("\n")
    for line_no, _, title in headings:
        if line_no > 1 and lines[line_no - 2].strip():
            findings.append(
                Finding(
                    "fail",
                    "sad-rules",
                    f"line {line_no}",
                    f"no empty line before heading {title!r}",
                )
            )

    raw_lines = raw.split("\n")
    for n, line in enumerate(raw_lines, start=1):
        if "<table" in line.lower():
            window = "\n".join(raw_lines[max(0, n - 4) : n - 1])
            if "<!--" not in window:
                findings.append(
                    Finding(
                        "fail",
                        "sad-rules",
                        f"line {n}",
                        "HTML table without the explanatory comment the SAD rules require",
                    )
                )


def check_catalog_fidelity(
    tables: dict[str, Table],
    drivers: list[str],
    attributes: list[str],
    findings: list[Finding],
) -> None:
    specs = [
        (DRIVERS_SECTION, "Business Driver", drivers, "business-drivers.md"),
        (QAR_SECTION, "Quality Attribute", attributes, "quality-attributes.md"),
    ]

    for section, column, catalog, filename in specs:
        table = tables.get(section)
        if table is None:
            continue
        if column not in table.headers:
            findings.append(
                Finding("fail", "structure", section, f"table has no {column!r} column")
            )
            continue
        for row, line_no in zip(table.rows, table.line_numbers):
            if is_placeholder(row):
                continue
            raw = row.get(column, "").strip()
            name = re.sub(r"\*\*(.*?)\*\*", r"\1", raw).strip()
            if not name:
                findings.append(
                    Finding("fail", "catalog-fidelity", f"line {line_no}", f"empty {column}")
                )
            elif name not in catalog:
                near = [c for c in catalog if c.lower().startswith(name.lower()[:6])]
                hint = f"; did you mean {near[0]!r}?" if near else ""
                findings.append(
                    Finding(
                        "fail",
                        "catalog-fidelity",
                        f"line {line_no}",
                        f"{name!r} is not in {filename}{hint}",
                    )
                )

    drivers_table = tables.get(DRIVERS_SECTION)
    if drivers_table is not None:
        real = [r for r in drivers_table.rows if not is_placeholder(r)]
        if len(real) > len(drivers):
            findings.append(
                Finding(
                    "fail",
                    "catalog-fidelity",
                    DRIVERS_SECTION,
                    f"{len(real)} rows but the catalog defines only {len(drivers)} drivers",
                )
            )


def check_business_separation(tables: dict[str, Table], findings: list[Finding]) -> None:
    table = tables.get(DRIVERS_SECTION)
    if table is None:
        return

    goal_columns = [h for h in table.headers if h not in ("ID", "Business Driver", "Priority")]

    for row, line_no in zip(table.rows, table.line_numbers):
        if is_placeholder(row):
            continue
        cell = " ".join(row.get(c, "") for c in goal_columns).strip()
        if not cell:
            findings.append(
                Finding("fail", "business-separation", f"line {line_no}", "empty goal cell")
            )
            continue

        hit = matches_any(TECHNICAL_TOKENS, cell)
        if hit:
            findings.append(
                Finding(
                    "fail",
                    "business-separation",
                    f"line {line_no}",
                    f"driver cell contains technical vocabulary ({hit!r}); this belongs in "
                    f"{QAR_SECTION}",
                )
            )

        if not (
            matches_any(MONEY_PATTERNS, cell)
            or matches_any(DATE_PATTERNS, cell)
            or matches_any(MARKET_POSITION_PATTERNS, cell)
        ):
            findings.append(
                Finding(
                    "fail",
                    "business-separation",
                    f"line {line_no}",
                    "driver cell states no monetary amount, date, or market position",
                )
            )


def check_measurability(tables: dict[str, Table], findings: list[Finding]) -> None:
    table = tables.get(QAR_SECTION)
    if table is None:
        return

    column = next((h for h in table.headers if h.lower().startswith("requirement")), None)
    if column is None:
        column = next((h for h in table.headers if h.lower().startswith("metric")), None)
    if column is None:
        findings.append(
            Finding("fail", "structure", QAR_SECTION, "table has no Requirement column")
        )
        return

    for row, line_no in zip(table.rows, table.line_numbers):
        if is_placeholder(row):
            continue
        cell = row.get(column, "").strip()
        if not cell:
            findings.append(
                Finding("fail", "measurability", f"line {line_no}", "empty requirement cell")
            )
            continue
        if matches_any(PENDING_MARKERS, cell):
            findings.append(
                Finding(
                    "warn",
                    "measurability",
                    f"line {line_no}",
                    "pending stakeholder confirmation",
                )
            )
            continue

        has_number = bool(re.search(r"\d", cell))
        qualified = matches_any(UNIT_TOKENS, cell) or matches_any(OPERATOR_TOKENS, cell)
        if (has_number and qualified) or matches_any(STANDARD_TOKENS, cell):
            continue

        findings.append(
            Finding(
                "fail",
                "measurability",
                f"line {line_no}",
                "requirement states no threshold with a unit, and is not marked "
                "(proposed) or TBD",
            )
        )


def collect_priorities(tables: dict[str, Table]) -> list[tuple[str, str, str, int]]:
    """Return (section, row id, priority cell, line number) for every content row."""
    out = []
    for section in (DRIVERS_SECTION, QAR_SECTION):
        table = tables.get(section)
        if table is None or "Priority" not in table.headers:
            continue
        for row, line_no in zip(table.rows, table.line_numbers):
            if is_placeholder(row):
                continue
            out.append((section, row.get("ID", "").strip(), row["Priority"].strip(), line_no))
    return out


def check_p0_budget(tables: dict[str, Table], findings: list[Finding]) -> None:
    p0 = [
        (row_id, line_no)
        for _, row_id, priority, line_no in collect_priorities(tables)
        if re.search(r"\bP0\b", priority)
    ]
    if len(p0) > MAX_P0:
        listed = ", ".join(f"{i or '?'} (line {n})" for i, n in p0)
        findings.append(
            Finding(
                "fail",
                "p0-budget",
                "document",
                f"{len(p0)} rows carry P0; the budget is {MAX_P0}. Rows: {listed}",
            )
        )


def head_version(doc: Path) -> str | None:
    """Return the git HEAD content of the document, or None if unavailable."""
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=doc.parent if doc.parent.exists() else Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        rel = doc.resolve().relative_to(Path(root).resolve())
        result = subprocess.run(
            ["git", "show", f"HEAD:{rel.as_posix()}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError, OSError):
        return None


def check_priority_locks(
    doc: Path, tables: dict[str, Table], findings: list[Finding]
) -> None:
    locked = [
        (section, row_id, priority, line_no)
        for section, row_id, priority, line_no in collect_priorities(tables)
        if LOCK_MARKER in priority
    ]
    if not locked:
        return

    baseline = head_version(doc)
    if baseline is None:
        findings.append(
            Finding(
                "warn",
                "priority-lock",
                "document",
                f"{len(locked)} locked priorities could not be verified: no git HEAD "
                "version of this document",
            )
        )
        return

    previous = {
        row_id: priority
        for _, row_id, priority, _ in collect_priorities(parse_tables(strip_comments(baseline)))
        if row_id
    }

    for _, row_id, priority, line_no in locked:
        if not row_id or row_id not in previous:
            continue
        if previous[row_id].strip() != priority.strip():
            findings.append(
                Finding(
                    "fail",
                    "priority-lock",
                    f"line {line_no}",
                    f"{row_id} is locked at {previous[row_id]!r} in HEAD but reads "
                    f"{priority!r} here",
                )
            )


def check_assumptions(text: str, findings: list[Finding]) -> None:
    lines = text.split("\n")
    start = None
    for n, line in enumerate(lines):
        match = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if match:
            if match.group(1) == ASSUMPTIONS_SECTION:
                start = n + 1
            elif start is not None:
                break
    if start is None:
        return

    for n in range(start, len(lines)):
        if re.match(r"^#{1,6}\s+", lines[n]):
            break
        stripped = lines[n].strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        if body.lower().startswith("assumption (impact)"):
            continue  # template placeholder
        if not re.search(r"\(.+\)", body):
            findings.append(
                Finding(
                    "fail",
                    "assumptions",
                    f"line {n + 1}",
                    "assumption states no impact in brackets; expected "
                    "'- Assumption (Impact)' then the explanation on the next line",
                )
            )
            continue
        following = lines[n + 1].strip() if n + 1 < len(lines) else ""
        if not following or following.startswith("- "):
            findings.append(
                Finding(
                    "fail",
                    "assumptions",
                    f"line {n + 1}",
                    "assumption has no explanation line following it",
                )
            )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def validate(doc: Path, catalog_dir: Path) -> list[Finding]:
    findings: list[Finding] = []

    raw = doc.read_text(encoding="utf-8")
    text = strip_comments(raw)
    tables = parse_tables(text)

    drivers = parse_catalog_names(catalog_dir / "business-drivers.md")
    attributes = parse_catalog_names(catalog_dir / "quality-attributes.md")

    check_structure(text, raw, findings)
    check_catalog_fidelity(tables, drivers, attributes, findings)
    check_business_separation(tables, findings)
    check_measurability(tables, findings)
    check_p0_budget(tables, findings)
    check_priority_locks(doc, tables, findings)
    check_assumptions(text, findings)

    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Non-Functional Requirements document. Never modifies it."
    )
    parser.add_argument("--doc", required=True, help="Path to the NFR document to validate.")
    parser.add_argument(
        "--catalog-dir",
        default=str(Path(__file__).resolve().parent.parent / "templates"),
        help="Folder holding business-drivers.md and quality-attributes.md.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    doc = Path(args.doc).expanduser()
    catalog_dir = Path(args.catalog_dir).expanduser()

    if not doc.is_file():
        print(f"error: document not found: {doc}", file=sys.stderr)
        return 2
    for name in ("business-drivers.md", "quality-attributes.md"):
        if not (catalog_dir / name).is_file():
            print(f"error: catalog not found: {catalog_dir / name}", file=sys.stderr)
            return 2

    findings = validate(doc, catalog_dir)
    failures = [f for f in findings if f.level == "fail"]
    warnings = [f for f in findings if f.level == "warn"]

    if args.json:
        print(
            json.dumps(
                {
                    "document": str(doc),
                    "valid": not failures,
                    "failures": [vars(f) for f in failures],
                    "warnings": [vars(f) for f in warnings],
                },
                indent=2,
            )
        )
        return 1 if failures else 0

    if failures:
        print(f"FAIL  {doc}  ({len(failures)} failing check"
              f"{'s' if len(failures) != 1 else ''})\n")
        for finding in failures:
            print(f"  [{finding.check}] {finding.location}: {finding.message}")
    else:
        print(f"PASS  {doc}")

    if warnings:
        print(f"\n  {len(warnings)} warning{'s' if len(warnings) != 1 else ''}:")
        for finding in warnings:
            print(f"  [{finding.check}] {finding.location}: {finding.message}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
