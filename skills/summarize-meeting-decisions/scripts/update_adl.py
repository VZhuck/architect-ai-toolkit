#!/usr/bin/env python3
"""Append confirmed decision rows to an Architecture Decision Log (ADL) file.

Pure file mechanics only - no duplicate comparison of any kind. Duplicate
judgment happens earlier, in the skill's Claude-driven semantic comparison
and user-confirmation steps; this script appends exactly the rows it is
given.

Usage:
  uv run python skills/summarize-meeting-decisions/scripts/update_adl.py \
      --adl-path sad/07.Decision-Acceptance-Board.md \
      --row "Security|Token storage|Use short-lived JWTs|2026-08-06|Jane Doe"
"""

from __future__ import annotations

import argparse
from pathlib import Path

_TABLE_HEADER = (
    "| **Area** | **Problem** | **Decision** | **Date** | **Approvers** |\n"
    "| -------- | ----------- | ------------ | -------- | ------------- |\n"
)
_DECISIONS_SECTION_TITLE = "## Decisions"

DecisionRow = tuple[str, str, str, str, str]


def _format_row(row: DecisionRow) -> str:
    area, problem, decision, date, approvers = row
    return f"| {area} | {problem} | {decision} | {date} | {approvers} |\n"


def append_decisions(adl_path: Path, rows: list[DecisionRow]) -> Path:
    """Append rows to adl_path's decisions table, creating the file/section as needed.

    - If adl_path doesn't exist: create it with a markdown title plus the
      standard table header before appending rows.
    - If adl_path exists but has no "## Decisions" section: append that
      section (with the standard table header) to the end of the file.
    - If adl_path exists and already has a "## Decisions" section: append
      rows to the end of the file (the section's table is always the last
      content in the file once this function has run at least once).

    Raises OSError if the file cannot be written.
    """
    adl_path = Path(adl_path)

    if not rows:
        return adl_path

    if not adl_path.exists():
        adl_path.parent.mkdir(parents=True, exist_ok=True)
        title = adl_path.stem.replace("-", " ").replace("_", " ").strip() or "Architecture Decision Log"
        content = f"# {title}\n\n{_DECISIONS_SECTION_TITLE}\n\n{_TABLE_HEADER}"
        for row in rows:
            content += _format_row(row)
        adl_path.write_text(content, encoding="utf-8")
        return adl_path

    existing = adl_path.read_text(encoding="utf-8")

    if _DECISIONS_SECTION_TITLE not in existing:
        if not existing.endswith("\n"):
            existing += "\n"
        existing += f"\n{_DECISIONS_SECTION_TITLE}\n\n{_TABLE_HEADER}"
    elif not existing.endswith("\n"):
        existing += "\n"

    for row in rows:
        existing += _format_row(row)

    adl_path.write_text(existing, encoding="utf-8")
    return adl_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append confirmed decision rows to an ADL file."
    )
    parser.add_argument("--adl-path", required=True, help="Path to the ADL markdown file.")
    parser.add_argument(
        "--row",
        action="append",
        default=[],
        dest="rows",
        metavar="AREA|PROBLEM|DECISION|DATE|APPROVERS",
        help="A decision row, pipe-separated (repeat for multiple rows).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[DecisionRow] = []
    for raw in args.rows:
        parts = raw.split("|")
        if len(parts) != 5:
            raise ValueError(f"expected 5 pipe-separated fields, got {len(parts)}: {raw!r}")
        rows.append(tuple(part.strip() for part in parts))  # type: ignore[arg-type]

    output_path = append_decisions(Path(args.adl_path), rows)
    print(f"Updated ADL: {output_path} (+{len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
