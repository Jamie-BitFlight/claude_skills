"""Tests for the deterministic Codex skill activation-matrix scaffold."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import generate_codex_skill_activation_matrix as generator


def test_checked_in_matrix_matches_declared_plugin_skills() -> None:
    """Keep every declared Codex skill visible until it gains real test evidence."""
    rows = generator.apply_overrides(generator.build_rows(), generator.load_overrides())
    checked_in = generator.MATRIX_PATH.read_text(encoding="utf-8")

    assert checked_in == generator.render_rows(rows)
    assert all(row["status"] in {"NO_ORACLE", "MAPPED", "BLOCKED", "PASSED", "FAILED"} for row in rows)
    for row in rows:
        if row["status"] == "NO_ORACLE":
            assert row["task_source"] is None
            assert row["task_text"] is None
            assert row["expected_outcome"] is None
            assert row["safety_class"] == "UNCLASSIFIED"
        if row["status"] == "MAPPED":
            assert isinstance(row["task_source"], str)
            assert isinstance(row["task_text"], str)
            assert isinstance(row["expected_outcome"], str)
            assert row["safety_class"] != "UNCLASSIFIED"

    parsed_rows = [json.loads(line) for line in checked_in.splitlines()]
    targets = [row["target"] for row in parsed_rows]
    assert targets == sorted(targets)
    assert len({row["target"] for row in parsed_rows}) == len(parsed_rows), "duplicate target in checked-in matrix"


def _write_plugin_manifest(plugins_root: Path, plugin_id: str, skills_dir: str = "skills") -> Path:
    """Write a minimal Codex plugin manifest fixture and return its skills root."""
    manifest_dir = plugins_root / plugin_id / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(
        json.dumps({"name": plugin_id, "skills": f"./{skills_dir}"}), encoding="utf-8"
    )
    skills_root = plugins_root / plugin_id / skills_dir
    skills_root.mkdir(parents=True)
    return skills_root


def _write_skill(skills_root: Path, dir_name: str, skill_name: str) -> Path:
    """Write a minimal SKILL.md fixture declaring skill_name and return its path."""
    skill_dir = skills_root / dir_name
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(f"---\nname: {skill_name}\n---\nBody\n", encoding="utf-8")
    return skill_path


def test_load_skill_name_raises_when_frontmatter_has_no_name(tmp_path: Path) -> None:
    """A SKILL.md whose frontmatter never declares a name cannot resolve a target."""
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("---\ndescription: something\n---\nBody\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no name"):
        generator.load_skill_name(skill_path)


def test_load_skill_name_raises_when_frontmatter_is_incomplete(tmp_path: Path) -> None:
    """A SKILL.md with no YAML frontmatter delimiters cannot resolve a target."""
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("Just a body, no frontmatter at all.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing or incomplete"):
        generator.load_skill_name(skill_path)


def test_apply_overrides_rejects_unknown_target() -> None:
    """An override referencing a target absent from the manifest-derived inventory is rejected."""
    rows: list[dict[str, object]] = [{"target": "plugin:known-skill"}]

    with pytest.raises(ValueError, match="unknown targets"):
        generator.apply_overrides(rows, {"plugin:unknown-skill": {"status": "MAPPED"}})


def test_build_rows_rejects_duplicate_targets(tmp_path: Path) -> None:
    """Two skill directories declaring the same frontmatter name collide on one target."""
    plugins_root = tmp_path / "plugins"
    skills_root = _write_plugin_manifest(plugins_root, "sample-plugin")
    _write_skill(skills_root, "first", "duplicate-skill")
    _write_skill(skills_root, "second", "duplicate-skill")

    with pytest.raises(ValueError, match="Duplicate plugin-surface skill targets"):
        generator.build_rows(tmp_path)


def test_cli_check_flag_fails_on_stale_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--check exits non-zero when no matrix has ever been written for the fixture tree."""
    plugins_root = tmp_path / "plugins"
    skills_root = _write_plugin_manifest(plugins_root, "sample-plugin")
    _write_skill(skills_root, "example", "example")
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "MATRIX_PATH", tmp_path / "tests" / "fixtures" / "matrix.jsonl")
    monkeypatch.setattr(generator, "OVERRIDES_PATH", tmp_path / "tests" / "fixtures" / "overrides.json")
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 1


def test_cli_check_flag_passes_on_fresh_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--check exits zero immediately after the fixture tree's matrix has been written."""
    plugins_root = tmp_path / "plugins"
    skills_root = _write_plugin_manifest(plugins_root, "sample-plugin")
    _write_skill(skills_root, "example", "example")
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "MATRIX_PATH", tmp_path / "tests" / "fixtures" / "matrix.jsonl")
    monkeypatch.setattr(generator, "OVERRIDES_PATH", tmp_path / "tests" / "fixtures" / "overrides.json")
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py"])
    write_exit_code = generator.main()
    assert write_exit_code == 0
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 0
