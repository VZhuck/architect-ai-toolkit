import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import resolve_run as rr
from resolve_run import classify, match_runs, resolve_files, sha256_of, suggest_run_id


def _write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    """A project root with sources, state, taxonomy, and noise."""
    _write(tmp_path / "docs/payments/SAD.docx", "docx bytes")
    _write(tmp_path / "docs/payments/nfr.md", "# NFR\n")
    _write(tmp_path / "docs/payments/sub/notes.pdf", "pdf bytes")
    _write(tmp_path / "docs/payments/image.png", "png")
    _write(tmp_path / "docs/payments/.hidden/secret.md", "hidden")
    _write(tmp_path / "ai-workflow/nfr-state/run-1/sources/docs/payments/SAD.docx.md", "converted")
    _write(tmp_path / "ai-workflow/nfr-taxonomy/quality-attributes.md", "vocab")
    return tmp_path


def _resolve(root: Path, *paths: str) -> dict:
    return resolve_files(
        list(paths), root, root / "ai-workflow/nfr-state", root / "ai-workflow/nfr-taxonomy"
    )


def _paths(result: dict) -> list[str]:
    return [f["path"] for f in result["files"]]


# --- path resolution -----------------------------------------------------------


def test_directory_is_recursive_and_filtered(project):
    result = _resolve(project, "docs/payments/")

    assert _paths(result) == [
        "docs/payments/SAD.docx",
        "docs/payments/nfr.md",
        "docs/payments/sub/notes.pdf",
    ]
    assert result["unsupported"] == ["docs/payments/image.png"]
    assert "docs/payments/.hidden/secret.md" in result["excluded"]


def test_equivalent_forms_resolve_to_same_set(project):
    (project / "docs/payments/image.png").unlink()
    (project / "docs/payments/sub/notes.pdf").unlink()

    as_dir = _paths(_resolve(project, "docs/payments/"))
    as_mask = _paths(_resolve(project, "./docs/payments/*"))
    as_list = _paths(_resolve(project, "docs/payments/nfr.md", "docs/payments/SAD.docx"))

    assert as_dir == as_mask == as_list == ["docs/payments/SAD.docx", "docs/payments/nfr.md"]


def test_list_is_deduplicated(project):
    result = _resolve(project, "docs/payments/nfr.md", "docs/payments/*.md", "docs/payments/nfr.md")
    assert _paths(result) == ["docs/payments/nfr.md"]


def test_recursive_glob(project):
    assert _paths(_resolve(project, "docs/**/*.pdf")) == ["docs/payments/sub/notes.pdf"]


def test_own_state_and_taxonomy_never_mined(project):
    result = _resolve(project, ".")

    paths = _paths(result)
    assert not any(p.startswith("ai-workflow/") for p in paths)
    assert "ai-workflow/nfr-state/run-1/sources/docs/payments/SAD.docx.md" in result["excluded"]
    assert "ai-workflow/nfr-taxonomy/quality-attributes.md" in result["excluded"]


def test_unmatched_path_is_reported(project):
    result = _resolve(project, "docs/missing.md", "nope/*.md")
    assert result["files"] == []
    assert result["unmatched"] == ["docs/missing.md", "nope/*.md"]


def test_files_carry_sha256(project):
    result = _resolve(project, "docs/payments/nfr.md")
    assert result["files"][0]["sha256"] == sha256_of(project / "docs/payments/nfr.md")
    assert result["files"][0]["ext"] == ".md"


# --- run id --------------------------------------------------------------------


def test_suggested_run_id_uses_common_parent():
    now = datetime(2026, 9, 24, 14, 2)
    assert (
        suggest_run_id(["docs/payments/SAD.docx", "docs/payments/sub/notes.pdf"], now)
        == "docs-payments-20260924-1402"
    )
    assert suggest_run_id(["README.md", "docs/a.md"], now) == "repo-20260924-1402"


# --- run matching --------------------------------------------------------------


@pytest.mark.parametrize(
    ("new", "old", "expected"),
    [
        ({"a", "b"}, {"a", "b"}, "identical"),
        ({"a", "b", "c"}, {"a", "b"}, "superset"),
        ({"a"}, {"a", "b"}, "subset"),
        ({"a", "c"}, {"a", "b"}, "partial"),
        ({"c"}, {"a", "b"}, "none"),
        ({"a"}, set(), "none"),
    ],
)
def test_classify(new, old, expected):
    assert classify(new, old) == expected


def _make_run(base: Path, run_id: str, files: dict[str, str], stage="stage-1", step="1-map", statuses=None):
    statuses = statuses or {}
    state = {
        "run_id": run_id,
        "path_args": ["docs/payments/"],
        "active_skill": "archy-nfr-miner",
        "active_stage": stage,
        "active_step": step,
        "files_4_review": [
            {"path": p, "sha256": sha, "normalized": "", "status": statuses.get(p, "pending")}
            for p, sha in files.items()
        ],
    }
    _write(base / run_id / "state.yaml", yaml.safe_dump(state))


def test_match_classes_and_stale(project):
    base = project / "ai-workflow/nfr-state"
    files = _resolve(project, "docs/payments/nfr.md", "docs/payments/SAD.docx")["files"]
    shas = {f["path"]: f["sha256"] for f in files}

    _make_run(base, "same", shas, statuses={"docs/payments/nfr.md": "mined"})
    _make_run(base, "smaller", {"docs/payments/nfr.md": shas["docs/payments/nfr.md"]})
    _make_run(base, "bigger", {**shas, "docs/other.md": "abc"})
    _make_run(base, "overlap", {"docs/payments/nfr.md": "old-hash", "docs/x.md": "abc"})
    _make_run(base, "unrelated", {"docs/y.md": "abc"})

    matches = match_runs(files, base)
    by_id = {m["run_id"]: m for m in matches}

    assert [m["run_id"] for m in matches] == ["same", "smaller", "bigger", "overlap"]
    assert by_id["same"]["match"] == "identical"
    assert by_id["same"]["file_status"]["docs/payments/nfr.md"] == "mined"
    assert by_id["same"]["active_step"] == "1-map"
    assert by_id["smaller"]["match"] == "superset"
    assert by_id["smaller"]["added"] == ["docs/payments/SAD.docx"]
    assert by_id["bigger"]["match"] == "subset"
    assert by_id["bigger"]["missing"] == ["docs/other.md"]
    assert by_id["overlap"]["match"] == "partial"
    assert by_id["overlap"]["stale"] == ["docs/payments/nfr.md"]
    assert "unrelated" not in by_id


def test_changed_source_is_stale(project):
    base = project / "ai-workflow/nfr-state"
    files = _resolve(project, "docs/payments/nfr.md")["files"]
    _make_run(base, "r", {"docs/payments/nfr.md": files[0]["sha256"]})

    (project / "docs/payments/nfr.md").write_text("# NFR edited\n", encoding="utf-8")
    matches = match_runs(_resolve(project, "docs/payments/nfr.md")["files"], base)

    assert matches[0]["match"] == "identical"
    assert matches[0]["stale"] == ["docs/payments/nfr.md"]


def test_unreadable_state_is_ignored(project):
    base = project / "ai-workflow/nfr-state"
    _write(base / "broken/state.yaml", "::: not yaml [")
    assert match_runs(_resolve(project, "docs/payments/nfr.md")["files"], base) == []


# --- CLI -----------------------------------------------------------------------


def test_main_prints_json(project, capsys):
    assert rr.main(["--root", str(project), "--path", "docs/payments/nfr.md", "--run", "case-01"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert _paths(result) == ["docs/payments/nfr.md"]
    assert result["suggested_run_id"] == "case-01"
    assert result["run_exists"] is False
    assert result["runs"] == []


def test_main_unsupported_only_exits_nonzero(project, capsys):
    assert rr.main(["--root", str(project), "--path", "docs/payments/image.png"]) == 2

    result = json.loads(capsys.readouterr().out)
    assert result["files"] == []
    assert result["unsupported"] == ["docs/payments/image.png"]
    assert "no supported files" in result["error"]


def test_main_without_path_lists_unfinished_runs(project, capsys):
    base = project / "ai-workflow/nfr-state"
    _make_run(base, "open", {"docs/a.md": "1"})
    _make_run(base, "done", {"docs/b.md": "2"}, stage="finished", step="")

    assert rr.main(["--root", str(project)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert [r["run_id"] for r in result["unfinished_runs"]] == ["open"]
