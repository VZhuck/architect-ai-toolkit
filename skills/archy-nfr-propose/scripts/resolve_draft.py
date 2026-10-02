#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Resolve archy-nfr-propose inputs: target document, miner runs, and drafts.

- target: --nfr-doc, else the NFR_PATH env var, else NFR_PATH from the
  repo-root .env, else "needs_path": the skill must ask. There is no built-in
  default. Relative paths resolve against the repo root (--root, default: git
  top level, else cwd), never the skill folder. Reports the source
  (param | env | .env), whether it exists, and its sha256.
- runs: every <state-base>/<run>/ holding nfr-registry-log.md, with stage,
  step, registry counts, warnings (no state.yaml, not finished), and the most
  recently updated one marked "latest". --run selects runs (run id, run
  folder, or registry path; repeatable).
- drafts: every <draft-base>/<draft>/state.yaml for the same target, matched
  on the selected registry set: identical | superset | subset | partial,
  with stale inputs (registry sha256 changed) and target drift (target
  sha256 changed since the draft started). A draft's identity is
  (target path, set of input registry paths), not its folder name.

Prints one JSON object to stdout. Exits 2, still printing the JSON, when no
miner run with a registry exists.

Usage:
  uv run skills/archy-nfr-propose/scripts/resolve_draft.py --list
  uv run skills/archy-nfr-propose/scripts/resolve_draft.py --nfr-doc <nfr_doc> \\
      --run payments-20260924-1402 --run security-20260926-0930
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gc_tables import h2_tables  # noqa: E402

DEFAULT_STATE_BASE = "ai-workflow/nfr-state"
DEFAULT_DRAFT_BASE = "ai-workflow/nfr-draft"
ENV_VAR = "NFR_PATH"
ENV_FILE = ".env"
_ENV_KEY_RE_TEMPLATE = r"^\s*{key}\s*=\s*(.+?)\s*$"
REGISTRY_FILE = "nfr-registry-log.md"
STATE_FILE = "state.yaml"
FINISHED_STAGES = {"finished", "hand-off"}
MATCH_ORDER = {"identical": 0, "superset": 1, "subset": 2, "partial": 3}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _resolve(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def _load_yaml(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _when(value, fallback: Path) -> datetime:
    """Parse update_on; fall back to the file's mtime. Always timezone-aware."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback.stat().st_mtime, tz=timezone.utc)


# --- target ----------------------------------------------------------------------


def repo_root(cwd: Path | None = None) -> Path:
    """The git top level containing cwd, else cwd itself."""
    cwd = (cwd or Path.cwd()).resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return cwd
    return Path(out).resolve() if out else cwd


def read_env_file(root: Path, key: str) -> str | None:
    """Read one key=value entry from the repo-root .env, if present."""
    env_path = root / ENV_FILE
    if not env_path.is_file():
        return None
    pattern = re.compile(_ENV_KEY_RE_TEMPLATE.format(key=re.escape(key)), re.MULTILINE)
    match = pattern.search(env_path.read_text(encoding="utf-8"))
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'") or None


def resolve_target(nfr_doc: str | None, root: Path, env: dict) -> dict:
    if nfr_doc:
        value, source = nfr_doc, "param"
    elif env.get(ENV_VAR):
        value, source = env[ENV_VAR], "env"
    else:
        value, source = read_env_file(root, ENV_VAR), ENV_FILE
    if not value:
        return {"needs_path": True, "path": None, "source": None, "exists": False, "sha256": ""}
    path = _resolve(value, root)
    exists = path.is_file()
    return {
        "needs_path": False,
        "path": _rel(path, root),
        "source": source,
        "exists": exists,
        "sha256": sha256_of(path) if exists else "",
        "format_source": "gc" if exists else "template",
    }


# --- runs ------------------------------------------------------------------------


def registry_counts(registry: Path) -> dict:
    tables = h2_tables(registry.read_text(encoding="utf-8"))
    entries = [r for r in tables.get("NFR Registry", []) if r.get("NFR ID")]
    by_status: dict[str, int] = {}
    for row in entries:
        status = row.get("Status", "") or "-"
        by_status[status] = by_status.get(status, 0) + 1
    questions = [r for r in tables.get("Open Questions", []) if r.get("#")]
    return {
        "entries": len(entries),
        "by_status": by_status,
        "open_questions": sum(1 for q in questions if q.get("Status", "").upper() != "CLOSED"),
        "conflicts": sum(1 for c in tables.get("Conflicts", []) if c.get("#")),
        "dropped": sum(1 for d in tables.get("Dropped", []) if d.get("NFR ID")),
    }


def discover_runs(state_base: Path, root: Path) -> list[dict]:
    runs = []
    if not state_base.is_dir():
        return runs
    for run_dir in sorted(p for p in state_base.iterdir() if p.is_dir() and not p.name.startswith(".")):
        registry = run_dir / REGISTRY_FILE
        if not registry.is_file():
            continue
        state_file = run_dir / STATE_FILE
        state = _load_yaml(state_file) if state_file.is_file() else None
        warnings = []
        if state is None:
            warnings.append("no state.yaml")
        stage = (state or {}).get("active_stage")
        step = (state or {}).get("active_step")
        finished = stage in FINISHED_STAGES
        if state is not None and not finished:
            warnings.append(f"not finished ({stage or '?'}/{step or '?'})")
        updated = _when((state or {}).get("update_on"), state_file if state else registry)
        runs.append({
            "run_id": run_dir.name,
            "registry": _rel(registry, root),
            "registry_sha256": sha256_of(registry),
            "has_state": state is not None,
            "active_stage": stage,
            "active_step": step,
            "finished": finished,
            "update_on": updated.isoformat(),
            "counts": registry_counts(registry),
            "warnings": warnings,
            "latest": False,
        })
    if runs:
        latest = max(runs, key=lambda r: r["update_on"])
        latest["latest"] = True
    runs.sort(key=lambda r: r["update_on"], reverse=True)
    return runs


def select_runs(values: list[str], runs: list[dict], root: Path) -> tuple[list[dict], list[str]]:
    by_id = {r["run_id"]: r for r in runs}
    by_registry = {r["registry"]: r for r in runs}
    selected, unmatched = [], []
    for value in values:
        if value in by_id:
            run = by_id[value]
        else:
            path = _resolve(value, root)
            if path.is_dir():
                path = path / REGISTRY_FILE
            run = by_registry.get(_rel(path, root))
        if run is None:
            unmatched.append(value)
        elif run not in selected:
            selected.append(run)
    return selected, unmatched


# --- drafts ----------------------------------------------------------------------


def classify(new_paths: set[str], draft_paths: set[str]) -> str:
    if not new_paths or not draft_paths:
        return "none"
    if new_paths == draft_paths:
        return "identical"
    if draft_paths < new_paths:
        return "superset"
    if new_paths < draft_paths:
        return "subset"
    if new_paths & draft_paths:
        return "partial"
    return "none"


def match_drafts(draft_base: Path, target: dict, selected: list[dict], root: Path) -> list[dict]:
    if not draft_base.is_dir() or not target.get("path"):
        return []
    current = {r["registry"]: r["registry_sha256"] for r in selected}
    drafts = []
    for draft_dir in sorted(p for p in draft_base.iterdir() if p.is_dir() and not p.name.startswith(".")):
        state = _load_yaml(draft_dir / STATE_FILE)
        if not state:
            continue
        targets = state.get("target_sad_docs") or []
        if not targets or not isinstance(targets[0], dict):
            continue
        if _rel(_resolve(str(targets[0].get("path", "")), root), root) != target["path"]:
            continue
        inputs = {
            str(e["path"]): e for e in (state.get("files_4_review") or []) if isinstance(e, dict) and e.get("path")
        }
        match = classify(set(current), set(inputs)) if current else "target-only"
        if match == "none":
            continue
        stale = []
        for path, entry in inputs.items():
            file = _resolve(path, root)
            now = sha256_of(file) if file.is_file() else ""
            if entry.get("sha256") and entry["sha256"] != now:
                stale.append(path)
        started = str(targets[0].get("sha256") or "")
        drafts.append({
            "draft_id": draft_dir.name,
            "draft_dir": _rel(draft_dir, root),
            "match": match,
            "added": sorted(set(current) - set(inputs)),
            "missing": sorted(set(inputs) - set(current)) if current else [],
            "stale_inputs": sorted(stale),
            "target_drift": started != (target.get("sha256") or ""),
            "archived": "-archived-" in draft_dir.name,
            "active_stage": state.get("active_stage"),
            "active_step": state.get("active_step"),
            "update_on": str(state.get("update_on") or ""),
        })
    drafts = [d for d in drafts if not d["archived"]]
    drafts.sort(key=lambda d: (MATCH_ORDER.get(d["match"], 9), d["active_stage"] == "finished", d["draft_id"]))
    return drafts


def retired_ids(draft_base: Path, target_path: str | None, root: Path) -> list[str]:
    """IDs listed in `## Retired` of every draft log (archived too) for this target."""
    found: set[str] = set()
    if not draft_base.is_dir() or not target_path:
        return []
    for draft_dir in draft_base.iterdir():
        state = _load_yaml(draft_dir / STATE_FILE) if draft_dir.is_dir() else None
        log = draft_dir / "nfr-draft-log.md"
        if not state or not log.is_file():
            continue
        targets = state.get("target_sad_docs") or []
        if not targets or _rel(_resolve(str(targets[0].get("path", "")), root), root) != target_path:
            continue
        for row in h2_tables(log.read_text(encoding="utf-8")).get("Retired", []):
            if row.get("ID"):
                found.add(row["ID"])
    return sorted(found)


def suggest_draft_id(target_path: str | None, now: datetime | None = None) -> str:
    now = now or datetime.now()
    stem = Path(target_path).stem if target_path else "nfr"
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "nfr"
    return f"{slug}-{now.strftime('%Y%m%d-%H%M')}"


# --- CLI -------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve archy-nfr-propose target, runs, and drafts.")
    parser.add_argument(
        "--nfr-doc", default=None, help=f"Target NFR document, repo-relative. Default: ${ENV_VAR}, else {ENV_FILE}."
    )
    parser.add_argument("--run", action="append", default=[], help="Run id, run folder, or registry path. Repeatable.")
    parser.add_argument("--draft", default=None, help="Explicit draft folder name.")
    parser.add_argument("--state-base", default=DEFAULT_STATE_BASE)
    parser.add_argument("--draft-base", default=DEFAULT_DRAFT_BASE)
    parser.add_argument("--root", default=None, help="Repo root. Default: git top level, else cwd.")
    parser.add_argument("--list", action="store_true", help="Only list runs (no target needed).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, env: dict | None = None) -> int:
    args = parse_args(argv)
    env = os.environ if env is None else env
    root = Path(args.root).expanduser().resolve() if args.root else repo_root()
    state_base = _resolve(args.state_base, root)
    draft_base = _resolve(args.draft_base, root)

    runs = discover_runs(state_base, root)
    result: dict = {
        "root": root.as_posix(),
        "state_base": _rel(state_base, root),
        "draft_base": _rel(draft_base, root),
        "runs": runs,
    }
    if not runs:
        result["error"] = f"no miner run with {REGISTRY_FILE} under {result['state_base']}"

    if not args.list:
        target = resolve_target(args.nfr_doc, root, env)
        selected, unmatched = select_runs(args.run, runs, root)
        draft_id = args.draft or suggest_draft_id(target.get("path"))
        result.update({
            "target": target,
            "selected": [r["run_id"] for r in selected],
            "unmatched": unmatched,
            "suggested_draft_id": draft_id,
            "draft_exists": (draft_base / draft_id).exists(),
            "drafts": match_drafts(draft_base, target, selected, root),
            "retired_ids": retired_ids(draft_base, target.get("path"), root),
        })

    print(json.dumps(result, indent=2, default=str))
    return 0 if runs else 2


if __name__ == "__main__":
    sys.exit(main())
