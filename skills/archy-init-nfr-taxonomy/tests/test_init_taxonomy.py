import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import init_taxonomy as it
from init_taxonomy import TaxonomyError, init_taxonomy, read_skill_version

SKILL_DIR = Path(__file__).resolve().parents[1]
REAL_TAXONOMY = SKILL_DIR / "taxonomy"
REAL_SKILL_MD = SKILL_DIR / "SKILL.md"

RESULT_FIELDS = {
    "version",
    "previous_version",
    "status",
    "source",
    "target",
    "copied",
    "skipped",
    "overwritten",
}


def _real_taxonomy_files():
    """Every non-hidden file in the skill's taxonomy/ - never a hard-coded list."""
    return sorted(
        p.relative_to(REAL_TAXONOMY)
        for p in REAL_TAXONOMY.rglob("*")
        if p.is_file()
        and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(REAL_TAXONOMY).parts)
    )


def _write_skill_md(path: Path, version: str | None) -> Path:
    metadata = f"metadata:\n  version: {version}\n" if version else ""
    path.write_text(f"---\nname: archy-init-nfr-taxonomy\ndescription: test\n{metadata}---\n\n# Test\n", encoding="utf-8")
    return path


@pytest.fixture
def fake_skill(tmp_path):
    """A skill copy whose version the test controls: (source, skill_md)."""
    source = tmp_path / "skill" / "taxonomy"
    (source / "nested").mkdir(parents=True)
    (source / "drivers.md").write_text("drivers v1\n", encoding="utf-8")
    (source / "nested" / "attributes.md").write_text("attributes v1\n", encoding="utf-8")
    (source / ".gitkeep").write_text("", encoding="utf-8")
    skill_md = _write_skill_md(tmp_path / "skill" / "SKILL.md", "1.0.0")
    return source, skill_md


# --- real skill taxonomy -----------------------------------------------------


def test_real_skill_declares_version():
    assert read_skill_version(REAL_SKILL_MD)


def test_real_taxonomy_all_files_copied(tmp_path):
    files = _real_taxonomy_files()
    assert files, "skill taxonomy/ must contain at least one file"

    target = tmp_path / "ai-workflow" / "taxonomy"
    result = init_taxonomy(target)

    assert result["status"] == "initialized"
    assert result["copied"] == [f.as_posix() for f in files]
    for rel in files:
        assert (target / rel).read_bytes() == (REAL_TAXONOMY / rel).read_bytes()
    assert (target / ".taxonomy-version").read_text().strip() == read_skill_version(REAL_SKILL_MD)


# --- version policy (fixture skill) ------------------------------------------


def test_first_run_copies_and_ignores_hidden(fake_skill, tmp_path):
    source, skill_md = fake_skill
    target = tmp_path / "project" / "deep" / "taxonomy"

    result = init_taxonomy(target, source=source, skill_md=skill_md)

    assert result["status"] == "initialized"
    assert result["previous_version"] is None
    assert result["copied"] == ["drivers.md", "nested/attributes.md"]
    assert (target / "nested" / "attributes.md").read_text() == "attributes v1\n"
    assert not (target / ".gitkeep").exists()
    assert (target / ".taxonomy-version").read_text().strip() == "1.0.0"


def test_same_version_skips_and_preserves_local_edits(fake_skill, tmp_path):
    source, skill_md = fake_skill
    target = tmp_path / "taxonomy"
    init_taxonomy(target, source=source, skill_md=skill_md)
    (target / "drivers.md").write_text("tailored\n", encoding="utf-8")

    result = init_taxonomy(target, source=source, skill_md=skill_md)

    assert result["status"] == "up-to-date"
    assert result["skipped"] == ["drivers.md", "nested/attributes.md"]
    assert result["copied"] == [] and result["overwritten"] == []
    assert (target / "drivers.md").read_text() == "tailored\n"


def test_version_change_overwrites_and_updates_marker(fake_skill, tmp_path):
    source, skill_md = fake_skill
    target = tmp_path / "taxonomy"
    init_taxonomy(target, source=source, skill_md=skill_md)
    (target / "drivers.md").write_text("tailored\n", encoding="utf-8")
    (source / "drivers.md").write_text("drivers v2\n", encoding="utf-8")
    _write_skill_md(skill_md, "1.1.0")

    result = init_taxonomy(target, source=source, skill_md=skill_md)

    assert result["status"] == "updated"
    assert result["previous_version"] == "1.0.0"
    assert result["overwritten"] == ["drivers.md", "nested/attributes.md"]
    assert (target / "drivers.md").read_text() == "drivers v2\n"
    assert (target / ".taxonomy-version").read_text().strip() == "1.1.0"


def test_missing_marker_overwrites_existing_files(fake_skill, tmp_path):
    source, skill_md = fake_skill
    target = tmp_path / "taxonomy"
    target.mkdir()
    (target / "drivers.md").write_text("stale\n", encoding="utf-8")

    result = init_taxonomy(target, source=source, skill_md=skill_md)

    assert result["status"] == "initialized"
    assert result["overwritten"] == ["drivers.md"]
    assert result["copied"] == ["nested/attributes.md"]
    assert (target / "drivers.md").read_text() == "drivers v1\n"
    assert (target / ".taxonomy-version").read_text().strip() == "1.0.0"


def test_force_recopies_same_version(fake_skill, tmp_path):
    source, skill_md = fake_skill
    target = tmp_path / "taxonomy"
    init_taxonomy(target, source=source, skill_md=skill_md)
    (target / "drivers.md").write_text("tailored\n", encoding="utf-8")

    result = init_taxonomy(target, force=True, source=source, skill_md=skill_md)

    assert result["status"] == "updated"
    assert "drivers.md" in result["overwritten"]
    assert (target / "drivers.md").read_text() == "drivers v1\n"


def test_unrelated_target_files_untouched(fake_skill, tmp_path):
    source, skill_md = fake_skill
    target = tmp_path / "taxonomy"
    target.mkdir()
    (target / "project-notes.md").write_text("mine\n", encoding="utf-8")

    init_taxonomy(target, source=source, skill_md=skill_md)
    _write_skill_md(skill_md, "2.0.0")
    init_taxonomy(target, source=source, skill_md=skill_md)

    assert (target / "project-notes.md").read_text() == "mine\n"


# --- errors -------------------------------------------------------------------


def test_missing_version_errors_without_writing(fake_skill, tmp_path):
    source, skill_md = fake_skill
    _write_skill_md(skill_md, None)
    target = tmp_path / "taxonomy"

    with pytest.raises(TaxonomyError, match="metadata.version"):
        init_taxonomy(target, source=source, skill_md=skill_md)
    assert not target.exists()


def test_missing_source_errors_without_writing(fake_skill, tmp_path):
    _, skill_md = fake_skill
    target = tmp_path / "taxonomy"

    with pytest.raises(TaxonomyError, match="not found"):
        init_taxonomy(target, source=tmp_path / "nope", skill_md=skill_md)
    assert not target.exists()


def test_empty_source_errors_without_writing(fake_skill, tmp_path):
    _, skill_md = fake_skill
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / ".gitkeep").write_text("", encoding="utf-8")
    target = tmp_path / "taxonomy"

    with pytest.raises(TaxonomyError, match="no files"):
        init_taxonomy(target, source=empty, skill_md=skill_md)
    assert not target.exists()


# --- CLI ----------------------------------------------------------------------


def test_main_prints_json_result(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert it.main([]) == 0

    result = json.loads(capsys.readouterr().out)
    assert RESULT_FIELDS <= result.keys()
    assert result["status"] == "initialized"
    assert Path(result["target"]) == tmp_path / "ai-workflow" / "taxonomy"
    assert result["copied"] == [f.as_posix() for f in _real_taxonomy_files()]


def test_main_error_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(it, "DEFAULT_SKILL_MD", _write_skill_md(tmp_path / "SKILL.md", None))

    assert it.main(["--target", str(tmp_path / "taxonomy")]) == 1
    assert "metadata.version" in capsys.readouterr().err
    assert not (tmp_path / "taxonomy").exists()
