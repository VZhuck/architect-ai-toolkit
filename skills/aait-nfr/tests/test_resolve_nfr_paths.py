"""Unit tests for aait-nfr path resolution.

Covers the three-step nfrPath ladder (explicit argument, .env NFR_PATH, then
choosing from sad/), the SAD-compliant name proposed for a new document, and
the rule that draft and trace files never land in sad/ - where md-to-word
would sweep them into the Word deliverable.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from resolve_nfr_paths import (  # noqa: E402
    MANY_SOURCES_THRESHOLD,
    collect_sources,
    derive_working_paths,
    propose_new_doc_name,
    resolve_nfr_path,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "sad").mkdir()
    (tmp_path / "docs").mkdir()
    return tmp_path


# --------------------------------------------------------------------------
# nfrPath resolution ladder
# --------------------------------------------------------------------------


def test_explicit_nfr_path_wins_over_env(repo: Path):
    (repo / ".env").write_text("NFR_PATH=./sad/99.From-Env.md\n")
    resolved, info = resolve_nfr_path("sad/08.Explicit.md", repo)
    assert resolved == repo / "sad" / "08.Explicit.md"
    assert info["source"] == "explicit --nfr-path"


def test_falls_back_to_env_nfr_path(repo: Path):
    (repo / ".env").write_text("OTHER=x\nNFR_PATH=./sad/08.From-Env.md\nMORE=y\n")
    resolved, info = resolve_nfr_path(None, repo)
    assert resolved == repo / "sad" / "08.From-Env.md"
    assert info["source"] == ".env NFR_PATH"


def test_env_value_may_be_quoted(repo: Path):
    (repo / ".env").write_text('NFR_PATH="./sad/08.Quoted.md"\n')
    resolved, _ = resolve_nfr_path(None, repo)
    assert resolved == repo / "sad" / "08.Quoted.md"


def test_unresolvable_asks_the_user_and_lists_sad(repo: Path):
    for name in ("00.Index.md", "01.Architecture-Overview.md", "07.Decisions.md"):
        (repo / "sad" / name).write_text("# x\n")

    resolved, info = resolve_nfr_path(None, repo)

    assert resolved is None, "must not guess a target document"
    assert info["source"] == "needs user choice"
    assert [p.name for p in info["existing"]] == [
        "00.Index.md",
        "01.Architecture-Overview.md",
        "07.Decisions.md",
    ]
    assert info["sad_dir_usable"] is True


def test_empty_sad_directory_still_asks(repo: Path):
    resolved, info = resolve_nfr_path(None, repo)
    assert resolved is None
    assert info["existing"] == []
    assert info["sad_dir_usable"] is False


def test_missing_sad_directory_still_asks(tmp_path: Path):
    resolved, info = resolve_nfr_path(None, tmp_path)
    assert resolved is None
    assert info["existing"] == []
    assert info["sad_dir_usable"] is False


def test_no_env_file_at_all(repo: Path):
    assert not (repo / ".env").exists()
    resolved, info = resolve_nfr_path(None, repo)
    assert resolved is None
    assert info["source"] == "needs user choice"


# --------------------------------------------------------------------------
# Proposed name for a new document
# --------------------------------------------------------------------------


def test_proposed_name_continues_the_sad_sequence(repo: Path):
    for n in range(8):
        (repo / "sad" / f"{n:02d}.Section-{n}.md").write_text("# x\n")
    assert propose_new_doc_name(repo / "sad") == "08.Non-Functional-Requirements.md"


def test_proposed_name_handles_decimal_sections(repo: Path):
    (repo / "sad" / "00.Index.md").write_text("# x\n")
    (repo / "sad" / "03.0.High-Level-Design.md").write_text("# x\n")
    (repo / "sad" / "03.1.Data-View.md").write_text("# x\n")
    assert propose_new_doc_name(repo / "sad") == "04.Non-Functional-Requirements.md"


def test_proposed_name_for_empty_sad(repo: Path):
    assert propose_new_doc_name(repo / "sad") == "01.Non-Functional-Requirements.md"


def test_proposed_name_surfaces_in_resolution_info(repo: Path):
    for n in range(8):
        (repo / "sad" / f"{n:02d}.Section-{n}.md").write_text("# x\n")
    _, info = resolve_nfr_path(None, repo)
    assert info["proposed_new"].name == "08.Non-Functional-Requirements.md"
    assert info["proposed_new"].parent == repo / "sad"


# --------------------------------------------------------------------------
# Derived working paths
# --------------------------------------------------------------------------


def test_draft_and_trace_derive_from_target(repo: Path):
    working = derive_working_paths(repo / "sad" / "08.Non-Functional-Requirements.md", repo)
    assert working["draft"] == repo / "ai-workflow" / "nfr" / "08.Non-Functional-Requirements.draft.md"
    assert working["trace"] == repo / "ai-workflow" / "nfr" / "08.Non-Functional-Requirements.trace.md"


def test_working_files_never_land_in_sad(repo: Path):
    """md-to-word converts everything in sad/ - working files must stay out."""
    working = derive_working_paths(repo / "sad" / "08.Non-Functional-Requirements.md", repo)
    for path in working.values():
        assert (repo / "sad") not in path.parents


def test_working_paths_ignore_where_the_target_lives(repo: Path):
    elsewhere = derive_working_paths(repo / "docs" / "nfr.md", repo)
    assert elsewhere["draft"].parent == repo / "ai-workflow" / "nfr"


# --------------------------------------------------------------------------
# Source collection
# --------------------------------------------------------------------------


def test_collects_text_bearing_files_only(repo: Path):
    (repo / "docs" / "notes.md").write_text("x")
    (repo / "docs" / "rfp.txt").write_text("x")
    (repo / "docs" / "diagram.png").write_bytes(b"\x89PNG")
    (repo / "docs" / "uv.lock").write_text("x")

    names = {p.name for p in collect_sources("docs", repo)}
    assert names == {"notes.md", "rfp.txt"}


def test_skips_noise_directories(repo: Path):
    (repo / "docs" / "notes.md").write_text("x")
    noise = repo / "docs" / "node_modules" / "pkg"
    noise.mkdir(parents=True)
    (noise / "readme.md").write_text("x")

    assert [p.name for p in collect_sources("docs", repo)] == ["notes.md"]


def test_single_file_path(repo: Path):
    target = repo / "docs" / "rfp.md"
    target.write_text("x")
    assert collect_sources("docs/rfp.md", repo) == [target]


def test_single_file_of_wrong_type_is_rejected(repo: Path):
    (repo / "docs" / "logo.png").write_bytes(b"\x89PNG")
    with pytest.raises(ValueError, match="not a text-bearing source file"):
        collect_sources("docs/logo.png", repo)


def test_missing_path_raises(repo: Path):
    with pytest.raises(FileNotFoundError, match="path not found"):
        collect_sources("docs/nope", repo)


def test_directory_with_no_candidates_raises(repo: Path):
    (repo / "docs" / "img.png").write_bytes(b"\x89PNG")
    with pytest.raises(FileNotFoundError, match="no text-bearing source files"):
        collect_sources("docs", repo)


def test_many_sources_threshold_is_detectable(repo: Path):
    for n in range(MANY_SOURCES_THRESHOLD + 5):
        (repo / "docs" / f"note-{n:03d}.md").write_text("x")
    assert len(collect_sources("docs", repo)) > MANY_SOURCES_THRESHOLD
