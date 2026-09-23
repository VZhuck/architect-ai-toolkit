"""Enforce the toolkit's `archy` naming convention for skills and commands.

See openspec capability `toolkit-naming-conventions`:
- skill folders under skills/ are `archy-<name>`
- each SKILL.md `name:` equals its folder name
- commands live under commands/archy/ (invoked as /archy:<name>)
- commands reference skills by their full, existing `archy-<name>` id
- no stale `skills/<name>/` paths or un-namespaced `/<name>` invocations
  outside openspec/

Run: uv run pytest tests/test_naming_conventions.py
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
COMMANDS_DIR = REPO_ROOT / "commands"
PREFIX = "archy-"
NAMESPACE = "archy"

SKILL_FOLDER_RE = re.compile(r"^archy-[a-z0-9]+(-[a-z0-9]+)*$")
# A hyphenated id followed by "skill", optionally backticked: "`archy-md-to-word` skill".
SKILL_REF_RE = re.compile(r"\b([a-z0-9]+(?:-[a-z0-9]+)+)`?\s+skill\b")

EXCLUDED_DIRS = {".git", ".claude", ".venv", "openspec", "ai-workflow", "__pycache__", "node_modules", ".pytest_cache"}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".sh", ".ps1", ".txt", ".yaml", ".yml", ".example"}
THIS_FILE = Path(__file__).resolve()


def skill_dirs():
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def command_files():
    return sorted(COMMANDS_DIR.rglob("*.md"))


def base_skill_names():
    """Unprefixed names of existing archy- skills, e.g. 'md-to-word'."""
    return [p.name[len(PREFIX):] for p in skill_dirs() if p.name.startswith(PREFIX)]


def base_command_names():
    return [p.stem for p in (COMMANDS_DIR / NAMESPACE).glob("*.md")]


def scanned_files():
    for path in REPO_ROOT.rglob("*"):
        rel = path.relative_to(REPO_ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if not path.is_file() or path.resolve() == THIS_FILE:
            continue
        if path.suffix in TEXT_SUFFIXES:
            yield path


def read_frontmatter_name(skill_md: Path):
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^name:\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip("\"'")
    return None


def find_stale_skill_paths(text, names):
    hits = []
    for name in names:
        hits += re.findall(rf"(?<![\w-])skills/{re.escape(name)}/", text)
    return hits


def find_stale_command_invocations(text, names):
    hits = []
    for name in names:
        hits += re.findall(rf"(?<![\w/:.-])/{re.escape(name)}(?![\w-])", text)
    return hits


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


@pytest.mark.parametrize("skill_dir", skill_dirs(), ids=lambda p: p.name)
def test_skill_folder_has_archy_prefix(skill_dir):
    assert SKILL_FOLDER_RE.match(skill_dir.name), (
        f"{_rel(skill_dir)} must be named 'archy-<kebab-name>'"
    )


@pytest.mark.parametrize("skill_dir", skill_dirs(), ids=lambda p: p.name)
def test_skill_md_name_matches_folder(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file(), f"{_rel(skill_dir)} is missing SKILL.md"
    name = read_frontmatter_name(skill_md)
    assert name == skill_dir.name, (
        f"{_rel(skill_md)} declares name '{name}', expected '{skill_dir.name}'"
    )


@pytest.mark.parametrize("command_file", command_files(), ids=lambda p: _rel(p))
def test_command_lives_in_archy_namespace(command_file):
    assert command_file.parent == COMMANDS_DIR / NAMESPACE, (
        f"{_rel(command_file)} must live under commands/{NAMESPACE}/"
    )


@pytest.mark.parametrize("command_file", command_files(), ids=lambda p: _rel(p))
def test_command_skill_references_resolve(command_file):
    existing = {p.name for p in skill_dirs()}
    refs = set(SKILL_REF_RE.findall(command_file.read_text(encoding="utf-8")))
    unresolved = sorted(r for r in refs if r not in existing)
    assert not unresolved, (
        f"{_rel(command_file)} references unknown skill(s) {unresolved}; "
        f"use the full archy- name of an existing skills/ folder"
    )


@pytest.mark.parametrize("path", sorted(scanned_files()), ids=lambda p: _rel(p))
def test_no_stale_unprefixed_skill_paths(path):
    hits = find_stale_skill_paths(path.read_text(encoding="utf-8", errors="ignore"), base_skill_names())
    assert not hits, (
        f"{_rel(path)} has stale skill path(s) {sorted(set(hits))}; use skills/{PREFIX}<name>/"
    )


@pytest.mark.parametrize("path", sorted(scanned_files()), ids=lambda p: _rel(p))
def test_no_unnamespaced_command_invocations(path):
    hits = find_stale_command_invocations(path.read_text(encoding="utf-8", errors="ignore"), base_command_names())
    assert not hits, (
        f"{_rel(path)} has un-namespaced command(s) {sorted(set(hits))}; "
        f"use /{NAMESPACE}:<name>"
    )


class TestMatcherGuards:
    """False-positive / true-positive guards for the stale-reference matchers."""

    def test_output_folder_path_is_not_a_command(self):
        assert find_stale_command_invocations("default: ai-workflow/md-to-word/sad.docx", ["md-to-word"]) == []

    def test_namespaced_invocation_is_not_flagged(self):
        assert find_stale_command_invocations("run `/archy:md-to-word sad`", ["md-to-word"]) == []

    def test_command_file_path_is_not_flagged(self):
        assert find_stale_command_invocations("see commands/archy/md-to-word.md", ["md-to-word"]) == []

    def test_bare_invocation_is_flagged(self):
        assert find_stale_command_invocations("Default template for /md-to-word when", ["md-to-word"]) == ["/md-to-word"]

    def test_prefixed_skill_path_is_not_flagged(self):
        assert find_stale_skill_paths("uv run python skills/archy-md-to-word/scripts/x.py", ["md-to-word"]) == []

    def test_unprefixed_skill_path_is_flagged(self):
        assert find_stale_skill_paths("uv run python skills/md-to-word/scripts/x.py", ["md-to-word"]) == ["skills/md-to-word/"]
