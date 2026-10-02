#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Validate an archy-nfr-propose draft against its base document.

Deterministic checks (see the nfr-propose spec, "Draft validation"):

- preservation: every line outside the managed table rows is byte-identical
  to the base, in order; a managed row that differs from the base, appears,
  or disappears must be claimed by the change set (add / update / remove);
  unclaimed base rows keep their relative order
- tables: the draft parses (four sections, a separator row, an ID column,
  the header's column count on every row)
- ids: unique across the document; a new ID is <TYPE>-### and sits in its
  type's section (existing base IDs are kept as they are)
- categories: a claimed QAR/BD row names a category verbatim from
  quality-attributes.md / business-drivers.md (unclaimed rows: warning only)
- forbidden: no forbidden ID (TO REVIEW, conflict, dropped) is rendered

Prints one JSON object {ok, errors, warnings}. Exits 1 when any error.

Usage:
  uv run skills/archy-nfr-propose/scripts/check_draft.py --base <draft_dir>/base.md \\
      --draft <draft_dir>/draft.md --changes <draft_dir>/changes.json \\
      --taxonomy-dir <taxonomy_dir> [--forbid QAR-014 ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gc_tables import (  # noqa: E402
    SECTIONS,
    normalize_id,
    parse_lines,
    plain,
    read_lines,
)


def _key(rid: str) -> str:
    return normalize_id(rid) or rid


def _managed_rows(parsed: dict) -> dict[int, str]:
    """1-based line -> normalized ID for every managed data row."""
    return {row["line"]: _key(row["id"]) for s in parsed["sections"].values() for row in s["rows"]}


def load_catalogs(taxonomy_dir: Path) -> dict[str, set[str]]:
    def names(file: str, header: str) -> set[str]:
        path = taxonomy_dir / file
        if not path.is_file():
            return set()
        found: set[str] = set()
        text = path.read_text(encoding="utf-8")
        in_table = False
        for line in text.splitlines():
            if line.lstrip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if not in_table:
                    in_table = cells[0] == header
                    continue
                if cells and cells[0] and not set(cells[0]) <= set("-: "):
                    found.add(plain(cells[0]))
            else:
                in_table = False
        return found

    return {
        "QAR": names("quality-attributes.md", "Quality Attribute"),
        "BD": names("business-drivers.md", "Business Driver"),
    }


def claimed_ids(changes: list[dict]) -> dict[str, set[str]]:
    claimed = {"add": set(), "update": set(), "remove": set()}
    for change in changes:
        op = change.get("op")
        if op in claimed and change.get("id"):
            claimed[op].add(_key(change["id"]))
    return claimed


def check(base_lines: list[str], draft_lines: list[str], changes: list[dict],
          catalogs: dict[str, set[str]] | None = None, forbid: list[str] | None = None) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    claimed = claimed_ids(changes)
    touched = claimed["add"] | claimed["update"] | claimed["remove"]

    base = parse_lines(base_lines)
    draft = parse_lines(draft_lines)
    for err in base["errors"]:
        errors.append({**err, "check": f"base-{err['check']}"})
    for err in draft["errors"]:
        errors.append({**err, "check": "tables" if err["check"] != "duplicate-id" else "ids"})
    if base["errors"] or any(e["check"] in ("section", "table", "id-column") for e in draft["errors"]):
        return {"ok": False, "errors": errors, "warnings": warnings}

    # --- preservation: text outside managed rows
    base_rows, draft_rows = _managed_rows(base), _managed_rows(draft)
    base_text = [(i, l) for i, l in enumerate(base_lines, 1) if i not in base_rows]
    draft_text = [(i, l) for i, l in enumerate(draft_lines, 1) if i not in draft_rows]
    for (bi, bl), (di, dl) in zip(base_text, draft_text):
        if bl != dl:
            errors.append({"check": "preservation", "line": di,
                           "message": f"draft line {di} differs from base line {bi} outside the managed rows",
                           "base": bl.rstrip("\r\n"), "draft": dl.rstrip("\r\n")})
            break
    if len(base_text) != len(draft_text) and not any(e["check"] == "preservation" for e in errors):
        errors.append({"check": "preservation", "line": None,
                       "message": f"text outside the managed rows has {len(draft_text)} lines, base has {len(base_text)}"})

    # --- preservation: managed rows
    base_by_id = {_key(r["id"]): r for s in base["sections"].values() for r in s["rows"]}
    draft_by_id = {_key(r["id"]): r for s in draft["sections"].values() for r in s["rows"]}
    for rid, row in draft_by_id.items():
        if rid not in base_by_id and rid not in claimed["add"]:
            errors.append({"check": "preservation", "line": row["line"], "id": rid,
                           "message": f"{rid} is new in the draft but not claimed by an add"})
    for rid, row in base_by_id.items():
        if rid not in draft_by_id:
            if rid not in claimed["remove"]:
                errors.append({"check": "preservation", "line": row["line"], "id": rid,
                               "message": f"{rid} is missing from the draft but not claimed by a remove"})
        elif draft_by_id[rid]["raw"] != row["raw"] and rid not in claimed["update"]:
            errors.append({"check": "preservation", "line": draft_by_id[rid]["line"], "id": rid,
                           "message": f"{rid} changed but is not claimed by an update",
                           "base": row["raw"], "draft": draft_by_id[rid]["raw"]})
    for name in SECTIONS:
        base_order = [_key(r["id"]) for r in base["sections"][name]["rows"] if _key(r["id"]) not in touched]
        draft_order = [_key(r["id"]) for r in draft["sections"][name]["rows"] if _key(r["id"]) in base_order]
        if base_order != draft_order:
            errors.append({"check": "preservation", "line": None,
                           "message": f"section '{name}': untouched rows changed order"})

    # --- ids
    for name, section in draft["sections"].items():
        type_ = SECTIONS[name]
        for row in section["rows"]:
            rid = _key(row["id"])
            if rid in base_by_id:
                continue  # GC IDs are kept as they are
            norm = normalize_id(row["id"])
            if not norm:
                errors.append({"check": "ids", "line": row["line"], "id": row["id"],
                               "message": f"new ID {row['id']} is not <TYPE>-###"})
            elif not norm.startswith(type_ + "-"):
                errors.append({"check": "ids", "line": row["line"], "id": row["id"],
                               "message": f"{row['id']} sits in '{name}', which holds {type_} IDs"})

    # --- categories
    if catalogs:
        for name, section in draft["sections"].items():
            type_ = SECTIONS[name]
            if type_ not in catalogs or not catalogs[type_]:
                continue
            for row in section["rows"]:
                category = row["fields"].get("category", "")
                if category in catalogs[type_]:
                    continue
                item = {"check": "categories", "line": row["line"], "id": row["id"],
                        "message": f"{row['id']}: '{category}' is not a {type_} catalog name"}
                (errors if _key(row["id"]) in touched else warnings).append(item)

    # --- forbidden
    for rid in forbid or []:
        if _key(rid) in draft_by_id:
            errors.append({"check": "forbidden", "line": draft_by_id[_key(rid)]["line"], "id": rid,
                           "message": f"{rid} must not be rendered (open, conflicting, or dropped)"})

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an NFR draft against its base.")
    parser.add_argument("--base", required=True, help="GC document, or the template base when there is no GC.")
    parser.add_argument("--draft", required=True)
    parser.add_argument("--changes", default=None, help="Change-set JSON used for the draft (list or {changes}).")
    parser.add_argument("--taxonomy-dir", default=None)
    parser.add_argument("--forbid", action="append", default=[], help="Target ID that must not be rendered.")
    args = parser.parse_args(argv)

    changes: list[dict] = []
    if args.changes:
        data = json.loads(Path(args.changes).read_text(encoding="utf-8"))
        changes = data["changes"] if isinstance(data, dict) else data
    catalogs = load_catalogs(Path(args.taxonomy_dir)) if args.taxonomy_dir else None
    result = check(read_lines(Path(args.base)), read_lines(Path(args.draft)), changes, catalogs, args.forbid)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
