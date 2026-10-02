#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Parse and patch the managed tables of an NFR document (golden copy, GC).

An NFR document has four H2 sections, each with free text and one markdown
table whose first-class key column is `ID`:

  Business Drivers & Goals  (BD)    Quality Attributes  (QAR)
  Assumptions               (ASM)   Constraints         (CSTR)

Only the data rows of those four tables are "managed". Everything else
(headings, intro text, other sections, custom columns, untouched rows) is
never rewritten, so a patched draft stays byte-identical outside the rows
the change set claims.

Subcommands (each prints one JSON object to stdout):
  parse --doc <md>                           records by ID, table line ranges
  base  --template <md> --out <md>           template with sample rows removed
  patch --doc <md> --changes <json> --out <md>
        apply [{op: add|update|remove, id, section?, fields, after_id?}, ...]

Exit codes: 0 ok, 1 parse/patch error (JSON has "errors"), 2 bad arguments.

Usage:
  uv run skills/archy-nfr-propose/scripts/gc_tables.py parse --doc <nfr_doc>
  uv run skills/archy-nfr-propose/scripts/gc_tables.py base --template <taxonomy_dir>/nfr-req-tmpl.md --out draft.md
  uv run skills/archy-nfr-propose/scripts/gc_tables.py patch --doc draft.md --changes changes.json --out draft.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECTIONS = {
    "Business Drivers & Goals": "BD",
    "Quality Attributes": "QAR",
    "Assumptions": "ASM",
    "Constraints": "CSTR",
}
TYPE_SECTION = {t: s for s, t in SECTIONS.items()}

# logical field -> column header, per type (see design.md "GC parsing and patching")
COLUMNS = {
    "BD": {"id": "ID", "category": "Business Driver", "statement": "Business Goal",
           "metrics": "Metric / Criteria", "priority": "Priority"},
    "QAR": {"id": "ID", "category": "Quality Attribute", "statement": "Requirement",
            "metrics": "Metric / Criteria", "priority": "Priority"},
    "ASM": {"id": "ID", "statement": "Assumption", "risk": "Risk", "priority": "Impact"},
    "CSTR": {"id": "ID", "statement": "Constraint", "priority": "Impact"},
}

ID_RE = re.compile(r"^(BD|QAR|ASM|CSTR)-(\d+)$", re.IGNORECASE)
SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")


class DocError(Exception):
    """Raised with a list of structured errors."""

    def __init__(self, errors: list[dict]):
        super().__init__("; ".join(e["message"] for e in errors))
        self.errors = errors


# --- low-level markdown helpers ----------------------------------------------


def split_cells(line: str) -> list[str]:
    """Split a markdown table row into stripped cells, honouring `\\|` escapes."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells, current, i = [], [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            current.append("\\|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    cells.append("".join(current).strip())
    return cells


def plain(value: str) -> str:
    """Cell text without bold/italic/code markers and with `\\|` unescaped."""
    value = value.replace("\\|", "|").strip()
    value = re.sub(r"^(\*\*|__)(.*)\1$", r"\2", value)
    value = re.sub(r"^(\*|_|`)(.*)\1$", r"\2", value)
    return value.strip()


def escape_cell(value: str) -> str:
    value = str(value).replace("\r", " ").replace("\n", "<br>")
    return re.sub(r"(?<!\\)\|", r"\\|", value)


def render_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(SEPARATOR_CELL_RE.match(c.replace(" ", "")) for c in cells)


def normalize_id(value: str) -> str | None:
    """`qar-13` -> `QAR-013`; None when not <TYPE>-<n>."""
    match = ID_RE.match(plain(value))
    if not match:
        return None
    return f"{match.group(1).upper()}-{int(match.group(2)):03d}"


def read_lines(path: Path) -> list[str]:
    """Lines with their original endings, so untouched bytes survive a rewrite."""
    return path.read_bytes().decode("utf-8").splitlines(keepends=True)


def _strip_eol(line: str) -> str:
    return line.rstrip("\r\n")


def _eol(line: str) -> str:
    return line[len(_strip_eol(line)):] or "\n"


# --- parsing -------------------------------------------------------------------


def _heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", _strip_eol(line))
    return (len(match.group(1)), match.group(2).strip()) if match else None


def parse_lines(lines: list[str], require_all: bool = True) -> dict:
    """Parse managed sections. Line numbers in the result are 1-based."""
    errors: list[dict] = []
    headings: list[tuple[int, int, str]] = []  # (index, level, text)
    in_fence = False
    for idx, line in enumerate(lines):
        if _strip_eol(line).lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        if in_fence:
            continue
        head = _heading(line)
        if head:
            headings.append((idx, head[0], head[1]))

    sections: dict[str, dict] = {}
    for pos, (idx, level, text) in enumerate(headings):
        if level != 2 or text not in SECTIONS:
            continue
        if text in sections:
            errors.append({"check": "section", "line": idx + 1,
                           "message": f"section '{text}' appears twice (lines {sections[text]['heading_line']} and {idx + 1})"})
            continue
        end = next((h[0] for h in headings[pos + 1:] if h[1] <= 2), len(lines))
        sections[text] = _parse_section(lines, text, idx, end, errors)

    if require_all:
        for name in SECTIONS:
            if name not in sections:
                hint = ""
                near = [h[2] for h in headings if h[1] == 2 and h[2].lower()[:6] == name.lower()[:6]]
                if near:
                    hint = f" (found '{near[0]}')"
                errors.append({"check": "section", "line": None,
                               "message": f"missing H2 section '## {name}'{hint}"})

    records: dict[str, dict] = {}
    for name, section in sections.items():
        for row in section.get("rows", []):
            rid = row["id"]
            if not rid:
                continue
            key = normalize_id(rid) or rid
            if key in records:
                errors.append({"check": "duplicate-id", "line": row["line"], "id": rid,
                               "message": f"duplicate ID {rid} (lines {records[key]['line']} and {row['line']})"})
                continue
            records[key] = {**row, "section": name, "type": SECTIONS[name]}

    return {"sections": sections, "records": records, "errors": errors}


def _parse_section(lines: list[str], name: str, start: int, end: int, errors: list[dict]) -> dict:
    section: dict = {"heading_line": start + 1, "end_line": end, "table": None, "rows": []}
    idx = start + 1
    while idx < end and not is_table_line(lines[idx]):
        idx += 1
    if idx >= end:
        errors.append({"check": "table", "line": start + 1, "message": f"section '{name}' has no table"})
        return section

    header = split_cells(lines[idx])
    table = {"header_line": idx + 1, "headers": header, "separator_line": None,
             "first_row_line": None, "last_line": idx + 1}
    section["table"] = table
    if idx + 1 >= end or not is_table_line(lines[idx + 1]) or not is_separator(split_cells(lines[idx + 1])):
        errors.append({"check": "table", "line": idx + 2,
                       "message": f"section '{name}': table has no separator row after the header"})
        return section
    table["separator_line"] = idx + 2
    table["last_line"] = idx + 2

    lower = [h.lower() for h in header]
    if "id" not in lower:
        errors.append({"check": "id-column", "line": idx + 1,
                       "message": f"section '{name}': table has no 'ID' column"})
        return section
    id_col = lower.index("id")
    type_ = SECTIONS[name]
    col_of = {field: lower.index(col.lower()) for field, col in COLUMNS[type_].items() if col.lower() in lower}
    section["columns"] = {field: header[i] for field, i in col_of.items()}
    section["custom_columns"] = [h for i, h in enumerate(header) if i not in col_of.values()]

    row_idx = idx + 2
    while row_idx < end and is_table_line(lines[row_idx]):
        cells = split_cells(lines[row_idx])
        if len(cells) != len(header):
            errors.append({"check": "columns", "line": row_idx + 1,
                           "message": f"section '{name}': row has {len(cells)} cells, header has {len(header)}"})
        cells = (cells + [""] * len(header))[: len(header)]
        rid = plain(cells[id_col])
        if not rid:
            errors.append({"check": "id-column", "line": row_idx + 1,
                           "message": f"section '{name}': row without an ID"})
        fields = {field: plain(cells[i]) for field, i in col_of.items()}
        section["rows"].append({
            "line": row_idx + 1,
            "id": rid,
            "fields": fields,
            "cells": dict(zip(header, cells)),
            "raw": _strip_eol(lines[row_idx]),
        })
        if table["first_row_line"] is None:
            table["first_row_line"] = row_idx + 1
        table["last_line"] = row_idx + 1
        row_idx += 1
    return section


def parse_doc(path: Path, require_all: bool = True) -> dict:
    return parse_lines(read_lines(path), require_all)


def h2_tables(text: str) -> dict[str, list[dict[str, str]]]:
    """Generic reader: H2 heading -> data rows (header -> plain cell) of its first table.

    Used for registry-style logs (`nfr-registry-log.md`, `nfr-draft-log.md`).
    """
    tables: dict[str, list[dict[str, str]]] = {}
    section, header, state = None, None, "text"
    for line in text.splitlines():
        head = _heading(line)
        if head and head[0] <= 2:
            section = head[1] if head[0] == 2 else None
            header, state = None, "text"
            if section is not None:
                tables.setdefault(section, [])
            continue
        if section is None or state == "done":
            continue
        if is_table_line(line):
            cells = split_cells(line)
            if state == "text":
                header, state = cells, "header"
            elif state == "header":
                state = "rows" if is_separator(cells) else "done"
            else:
                tables[section].append({h: plain(c) for h, c in zip(header, cells)})
        elif state != "text":
            state = "done"
    return tables


def id_numbers(ids) -> dict[str, int]:
    """Highest number per type among IDs of the form <TYPE>-<n>."""
    highest = {t: 0 for t in COLUMNS}
    for rid in ids:
        norm = normalize_id(rid)
        if norm:
            type_, num = norm.split("-")
            highest[type_] = max(highest[type_], int(num))
    return highest


# --- patching ------------------------------------------------------------------


def _section_for(change: dict, parsed: dict) -> str:
    if change.get("section"):
        if change["section"] not in SECTIONS:
            raise DocError([{"check": "change", "message": f"unknown section '{change['section']}'"}])
        return change["section"]
    norm = normalize_id(change.get("id", ""))
    if norm:
        return TYPE_SECTION[norm.split("-")[0]]
    rec = parsed["records"].get(change.get("id"))
    if rec:
        return rec["section"]
    raise DocError([{"check": "change", "id": change.get("id"),
                     "message": f"cannot tell the section for {change.get('id')}; pass 'section'"}])


def _cells_for(section: dict, type_: str, fields: dict, current: dict[str, str] | None) -> list[str]:
    headers = section["table"]["headers"]
    by_header = {h.lower(): h for h in headers}
    cells = dict(current) if current else {h: "" for h in headers}
    for key, value in fields.items():
        header = COLUMNS[type_].get(key)
        target = by_header.get((header or key).lower())
        if target is None:
            if header is None:
                raise DocError([{"check": "change", "message": f"unknown field or column '{key}'"}])
            continue  # the document has no such column: nothing to write
        cells[target] = escape_cell(value)
    return [cells[h] for h in headers]


def apply_changes(lines: list[str], changes: list[dict]) -> list[str]:
    """Return new lines with the changes applied, re-parsing after each one."""
    lines = list(lines)
    for change in changes:
        parsed = parse_lines(lines, require_all=False)
        fatal = [e for e in parsed["errors"] if e["check"] in ("table", "id-column", "duplicate-id")]
        if fatal:
            raise DocError(fatal)
        op = change.get("op")
        name = _section_for(change, parsed)
        section = parsed["sections"].get(name)
        if not section or not section.get("table") or "columns" not in section:
            raise DocError([{"check": "change", "message": f"document has no usable '{name}' table"}])
        type_ = SECTIONS[name]
        rows = {normalize_id(r["id"]) or r["id"]: r for r in section["rows"]}
        rid = normalize_id(change.get("id", "")) or change.get("id")
        eol = _eol(lines[section["table"]["separator_line"] - 1])

        if op == "add":
            if not rid:
                raise DocError([{"check": "change", "message": "add needs an 'id'"}])
            if rid in parsed["records"]:
                raise DocError([{"check": "change", "id": rid, "message": f"{rid} already exists"}])
            fields = {**change.get("fields", {}), "id": rid}
            new_line = render_row(_cells_for(section, type_, fields, None)) + eol
            after = normalize_id(change.get("after_id") or "") or change.get("after_id")
            if after and after in rows:
                at = rows[after]["line"]  # insert after this 1-based line
            else:
                at = section["table"]["last_line"]
            lines.insert(at, new_line)
        elif op in ("update", "remove"):
            if rid not in rows:
                raise DocError([{"check": "change", "id": rid,
                                 "message": f"{rid} not found in section '{name}'"}])
            row = rows[rid]
            if op == "remove":
                del lines[row["line"] - 1]
            else:
                fields = {k: v for k, v in change.get("fields", {}).items() if k != "id"}
                new_line = render_row(_cells_for(section, type_, fields, row["cells"])) + eol
                lines[row["line"] - 1] = new_line
        else:
            raise DocError([{"check": "change", "message": f"unknown op '{op}'"}])
    return lines


def template_base(lines: list[str]) -> list[str]:
    """The template with every managed data row removed."""
    parsed = parse_lines(lines)
    if parsed["errors"]:
        raise DocError(parsed["errors"])
    drop = {row["line"] for s in parsed["sections"].values() for row in s["rows"]}
    return [line for i, line in enumerate(lines, start=1) if i not in drop]


# --- CLI -------------------------------------------------------------------------


def _summary(parsed: dict) -> dict:
    sections = {}
    for name, s in parsed["sections"].items():
        t = s.get("table") or {}
        sections[name] = {
            "type": SECTIONS[name],
            "heading_line": s["heading_line"],
            "header_line": t.get("header_line"),
            "separator_line": t.get("separator_line"),
            "last_line": t.get("last_line"),
            "headers": t.get("headers"),
            "columns": s.get("columns", {}),
            "custom_columns": s.get("custom_columns", []),
            "rows": [{"line": r["line"], "id": r["id"], "fields": r["fields"], "cells": r["cells"]} for r in s["rows"]],
        }
    ids = [r["id"] for s in parsed["sections"].values() for r in s["rows"] if r["id"]]
    return {
        "sections": sections,
        "ids": ids,
        "nonstandard_ids": [i for i in ids if not normalize_id(i)],
        "highest": id_numbers(ids),
        "errors": parsed["errors"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse and patch NFR document tables.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_parse = sub.add_parser("parse")
    p_parse.add_argument("--doc", required=True)
    p_base = sub.add_parser("base")
    p_base.add_argument("--template", required=True)
    p_base.add_argument("--out", required=True)
    p_patch = sub.add_parser("patch")
    p_patch.add_argument("--doc", required=True)
    p_patch.add_argument("--changes", required=True, help="JSON file: a list of changes, or {\"changes\": [...]}")
    p_patch.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    try:
        if args.cmd == "parse":
            result = _summary(parse_doc(Path(args.doc)))
            result["doc"] = args.doc
            print(json.dumps(result, indent=2))
            return 1 if result["errors"] else 0

        if args.cmd == "base":
            out = template_base(read_lines(Path(args.template)))
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_bytes("".join(out).encode("utf-8"))
            print(json.dumps({"out": args.out, "status": "written"}))
            return 0

        data = json.loads(Path(args.changes).read_text(encoding="utf-8"))
        changes = data["changes"] if isinstance(data, dict) else data
        out = apply_changes(read_lines(Path(args.doc)), changes)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_bytes("".join(out).encode("utf-8"))
        print(json.dumps({"out": args.out, "status": "patched", "applied": len(changes)}))
        return 0
    except DocError as exc:
        print(json.dumps({"errors": exc.errors}, indent=2))
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"errors": [{"check": "io", "message": str(exc)}]}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
