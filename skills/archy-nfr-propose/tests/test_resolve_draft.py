import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import resolve_draft as rd

REGISTRY = """# NFR Registry Log

## NFR Registry

| NFR ID | NFR Type | NFR Category | Verbatim evidence | Metrics | Source | Interpretation | Confidence | Priority | Status | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NFR-001 | QAR | Performance & Scalability | "fast" | p95 < 300 ms | a.md:L1 | x | 95 | | Confirmed | |
| NFR-002 | QAR | Resilience | "up" | | a.md:L2 | x | 70 | | TO REVIEW | |

## Open Questions

| # | Question | NFR ID | Proposed default | Default by | Comments | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | target? | NFR-002 | | | | TO REVIEW |
| Q2 | window? | NFR-001 | monthly | SKILL | ok | Closed |

## Conflicts

| # | NFR Type | NFR Category | NFR IDs | Value A | Source A | Value B | Source B |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Dropped

| NFR ID | Text | Source | Why dropped | Dropped by |
| --- | --- | --- | --- | --- |
| NFR-003 | "export CSV" | a.md:L5 | functional behaviour | SKILL |
"""


def make_run(root: Path, run_id: str, stage="finished", step="", update_on="2026-09-25T10:00:00+00:00", state=True):
    run_dir = root / "ai-workflow/nfr-state" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "nfr-registry-log.md").write_text(REGISTRY, encoding="utf-8")
    if state:
        (run_dir / "state.yaml").write_text(
            yaml.safe_dump({"run_id": run_id, "active_stage": stage, "active_step": step, "update_on": update_on}),
            encoding="utf-8",
        )
    return run_dir


def make_draft(root: Path, draft_id: str, target: str, target_sha: str, inputs: list[tuple[str, str]], retired=()):
    draft_dir = root / "ai-workflow/nfr-draft" / draft_id
    draft_dir.mkdir(parents=True)
    state = {
        "run_id": draft_id,
        "active_skill": "archy-nfr-propose",
        "active_stage": "stage-2",
        "active_step": "review-parked",
        "files_4_review": [{"path": p, "sha256": s, "status": "merged"} for p, s in inputs],
        "target_sad_docs": [{"path": target, "sha256": target_sha, "exists": True, "draft": "draft.md"}],
    }
    (draft_dir / "state.yaml").write_text(yaml.safe_dump(state), encoding="utf-8")
    rows = "".join(f"| {r} | | test | 2026-09-29 |\n" for r in retired)
    (draft_dir / "nfr-draft-log.md").write_text(
        f"# Log\n\n## Retired\n\n| ID | Replaced by | Reason | Date |\n| -- | -- | -- | -- |\n{rows}", encoding="utf-8"
    )
    return draft_dir


def call(root: Path, *args, env=None):
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = rd.main(["--root", str(root), *args], env=env or {})
    return code, json.loads(buf.getvalue())


@pytest.fixture
def project(tmp_path):
    (tmp_path / "sad").mkdir()
    (tmp_path / "sad/08.Non-Functional-Requirements.md").write_text("# NFR\n", encoding="utf-8")
    return tmp_path


# --- target ------------------------------------------------------------------------


def test_target_from_param(project):
    make_run(project, "a")
    code, out = call(project, "--nfr-doc", "sad/08.Non-Functional-Requirements.md")
    assert code == 0
    assert out["target"]["source"] == "param" and out["target"]["exists"]
    assert len(out["target"]["sha256"]) == 64 and out["target"]["format_source"] == "gc"


def test_target_from_env(project):
    make_run(project, "a")
    _, out = call(project, env={"NFR_PATH": "./sad/08.Non-Functional-Requirements.md"})
    assert out["target"]["path"] == "sad/08.Non-Functional-Requirements.md"
    assert out["target"]["source"] == "env"


def test_target_missing_file_uses_template(project):
    make_run(project, "a")
    _, out = call(project, "--nfr-doc", "sad/09.New.md")
    assert out["target"]["exists"] is False and out["target"]["format_source"] == "template"


def test_target_needs_path(project):
    make_run(project, "a")
    _, out = call(project)
    assert out["target"]["needs_path"] is True


def test_target_param_beats_env(project):
    make_run(project, "a")
    _, out = call(project, "--nfr-doc", "sad/09.New.md", env={"NFR_PATH": "sad/08.Non-Functional-Requirements.md"})
    assert out["target"]["path"] == "sad/09.New.md" and out["target"]["source"] == "param"


def test_target_env_beats_env_file(project):
    make_run(project, "a")
    (project / ".env").write_text("NFR_PATH=sad/09.New.md\n", encoding="utf-8")
    _, out = call(project, env={"NFR_PATH": "sad/08.Non-Functional-Requirements.md"})
    assert out["target"]["path"] == "sad/08.Non-Functional-Requirements.md" and out["target"]["source"] == "env"


def test_target_from_env_file(project):
    make_run(project, "a")
    (project / ".env").write_text('# comment\nOTHER=x\nNFR_PATH="./sad/08.Non-Functional-Requirements.md"\n', encoding="utf-8")
    _, out = call(project)
    assert out["target"]["path"] == "sad/08.Non-Functional-Requirements.md"
    assert out["target"]["source"] == ".env" and out["target"]["exists"]


def test_target_env_file_without_key_needs_path(project):
    make_run(project, "a")
    (project / ".env").write_text("ADL_PATH=./sad/07.md\n", encoding="utf-8")
    _, out = call(project)
    assert out["target"]["needs_path"] is True


@pytest.mark.parametrize("subdir", ["sad", ".claude/skills/archy-nfr-propose"])
def test_target_relative_to_repo_root(project, monkeypatch, subdir):
    import subprocess

    subprocess.run(["git", "init", "-q", str(project)], check=True)
    make_run(project, "a")
    (project / ".env").write_text("NFR_PATH=./sad/08.Non-Functional-Requirements.md\n", encoding="utf-8")
    (project / subdir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(project / subdir)
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rd.main([], env={})
    out = json.loads(buf.getvalue())
    assert Path(out["root"]) == project.resolve()
    assert out["target"]["path"] == "sad/08.Non-Functional-Requirements.md" and out["target"]["exists"]
    assert out["selected"] == [] and [r["run_id"] for r in out["runs"]] == ["a"]


def test_repo_root_outside_git_is_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert rd.repo_root() == tmp_path.resolve()


# --- runs ----------------------------------------------------------------------------


def test_runs_listed_with_warnings_and_latest(project):
    make_run(project, "old", update_on="2026-09-20T10:00:00+00:00")
    make_run(project, "new", update_on="2026-09-28T10:00:00+00:00")
    make_run(project, "parked", stage="stage-2", step="review-parked", update_on="2026-09-21T10:00:00+00:00")
    make_run(project, "nostate", state=False)
    code, out = call(project, "--list")
    assert code == 0
    runs = {r["run_id"]: r for r in out["runs"]}
    assert set(runs) == {"old", "new", "parked", "nostate"}
    latest = [r["run_id"] for r in out["runs"] if r["latest"]]
    assert len(latest) == 1
    assert runs["parked"]["warnings"] == ["not finished (stage-2/review-parked)"]
    assert runs["nostate"]["warnings"] == ["no state.yaml"]
    assert runs["old"]["warnings"] == []
    counts = runs["old"]["counts"]
    assert counts["entries"] == 2 and counts["by_status"] == {"Confirmed": 1, "TO REVIEW": 1}
    assert counts["open_questions"] == 1 and counts["dropped"] == 1 and counts["conflicts"] == 0


def test_latest_among_state_runs(project):
    make_run(project, "old", update_on="2026-09-20T10:00:00+00:00")
    make_run(project, "new", update_on="2026-09-28T10:00:00+00:00")
    _, out = call(project, "--list")
    assert [r["run_id"] for r in out["runs"] if r["latest"]] == ["new"]
    assert out["runs"][0]["run_id"] == "new"


def test_no_runs_exits_2(project):
    code, out = call(project, "--list")
    assert code == 2 and "error" in out


def test_select_by_id_folder_and_registry(project):
    make_run(project, "a")
    make_run(project, "b")
    _, out = call(project, "--nfr-doc", "sad/08.Non-Functional-Requirements.md",
                  "--run", "a", "--run", "ai-workflow/nfr-state/b/nfr-registry-log.md", "--run", "zzz")
    assert out["selected"] == ["a", "b"] and out["unmatched"] == ["zzz"]


# --- drafts ----------------------------------------------------------------------------


TARGET = "sad/08.Non-Functional-Requirements.md"


def _reg(run_id):
    return f"ai-workflow/nfr-state/{run_id}/nfr-registry-log.md"


@pytest.mark.parametrize(
    "draft_inputs, selected, match",
    [
        (["a", "b"], ["a", "b"], "identical"),
        (["a"], ["a", "b"], "superset"),
        (["a", "b"], ["a"], "subset"),
        (["a", "c"], ["a", "b"], "partial"),
    ],
)
def test_draft_match_classes(project, draft_inputs, selected, match):
    runs = {r: make_run(project, r) for r in ("a", "b", "c")}
    sha = rd.sha256_of(runs["a"] / "nfr-registry-log.md")
    target_sha = rd.sha256_of(project / TARGET)
    make_draft(project, "d1", TARGET, target_sha, [(_reg(r), sha) for r in draft_inputs])
    args = ["--nfr-doc", TARGET]
    for r in selected:
        args += ["--run", r]
    _, out = call(project, *args)
    assert [d["match"] for d in out["drafts"]] == [match]
    assert out["drafts"][0]["stale_inputs"] == [] and out["drafts"][0]["target_drift"] is False


def test_draft_other_target_ignored(project):
    make_run(project, "a")
    make_draft(project, "d1", "sad/other.md", "", [(_reg("a"), "")])
    _, out = call(project, "--nfr-doc", TARGET, "--run", "a")
    assert out["drafts"] == []


def test_stale_input_and_target_drift(project):
    run = make_run(project, "a")
    make_draft(project, "d1", TARGET, "old-sha", [(_reg("a"), rd.sha256_of(run / "nfr-registry-log.md"))])
    (run / "nfr-registry-log.md").write_text(REGISTRY + "\n", encoding="utf-8")
    _, out = call(project, "--nfr-doc", TARGET, "--run", "a")
    draft = out["drafts"][0]
    assert draft["stale_inputs"] == [_reg("a")]
    assert draft["target_drift"] is True


def test_drafts_for_target_without_runs(project):
    make_run(project, "a")
    make_draft(project, "d1", TARGET, "", [(_reg("a"), "")])
    _, out = call(project, "--nfr-doc", TARGET)
    assert [d["match"] for d in out["drafts"]] == ["target-only"]


def test_retired_ids_collected_incl_archived(project):
    make_run(project, "a")
    make_draft(project, "d1", TARGET, "", [(_reg("a"), "")], retired=["QAR-007"])
    make_draft(project, "d0-archived-20260901-1000", TARGET, "", [(_reg("a"), "")], retired=["CSTR-002"])
    _, out = call(project, "--nfr-doc", TARGET, "--run", "a")
    assert out["retired_ids"] == ["CSTR-002", "QAR-007"]
    assert [d["draft_id"] for d in out["drafts"]] == ["d1"]


def test_suggested_draft_id():
    assert rd.suggest_draft_id(TARGET, datetime(2026, 9, 30, 10, 15)) == "08-non-functional-requirements-20260930-1015"
