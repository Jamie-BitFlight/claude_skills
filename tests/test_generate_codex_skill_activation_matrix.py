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

    parsed_rows = [json.loads(line) for line in checked_in.splitlines()]
    expected_targets = {row["target"] for row in rows}
    actual_targets = {row["target"] for row in parsed_rows}
    regenerate = "uv run --script scripts/generate_codex_skill_activation_matrix.py"

    assert actual_targets == expected_targets, (
        f"Missing targets: {sorted(expected_targets - actual_targets, key=str)}; "
        f"extra targets: {sorted(actual_targets - expected_targets, key=str)}. Run: {regenerate}"
    )
    assert parsed_rows == rows, f"Matrix inventory/evidence differs from its declared inputs. Run: {regenerate}"
    # Retain exact freshness: semantic equality alone would miss canonical-byte drift.
    assert checked_in == generator.render_rows(rows), (
        f"Matrix JSONL differs from the generator's canonical serialization. Run: {regenerate}"
    )
    assert all(row["status"] in {"NO_ORACLE", "MAPPED", "BLOCKED", "PASSED", "FAILED"} for row in parsed_rows)
    for row in parsed_rows:
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


def test_build_rows_includes_repo_scoped_codex_skills(tmp_path: Path) -> None:
    """Expose repository `.agents/skills` through the real-consumer activation matrix."""
    skill_path = tmp_path / ".agents" / "skills" / "rebase" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("---\nname: rebase\ndescription: Rebase safely.\n---\nBody\n", encoding="utf-8")

    rows = generator.build_rows(tmp_path)

    assert rows == [
        {
            "target": "repo-skills:rebase",
            "plugin_id": "repo-skills",
            "skill": "rebase",
            "source_path": ".agents/skills/rebase/SKILL.md",
            "task_source": None,
            "task_text": None,
            "expected_outcome": None,
            "safety_class": "UNCLASSIFIED",
            "chain": [],
            "status": "NO_ORACLE",
            "evidence": {
                "distribution": None,
                "cache_provenance": None,
                "injection": None,
                "behavior": None,
                "safety": None,
            },
        }
    ]


@pytest.mark.parametrize(
    "rows",
    [
        [{"z": [2, 1], "a": {"y": True, "x": None}}, {"target": "second"}],
        [{"a": {"x": None, "y": True}, "z": [2, 1]}, {"target": "second"}],
    ],
    ids=["reverse-key-insertion", "sorted-key-insertion"],
)
def test_render_rows_uses_canonical_jsonl(rows: list[dict[str, object]]) -> None:
    """Pin reviewed bytes independently of the writer/checker round trip."""
    assert generator.render_rows(rows) == '{"a": {"x": null, "y": true}, "z": [2, 1]}\n{"target": "second"}\n'


@pytest.fixture
def matrix_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use real manifests, frontmatter, and files; redirect only CLI configuration."""
    skills_root = _write_plugin_manifest(tmp_path / "plugins", "sample-plugin")
    _write_skill(skills_root, "example", "example")
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "MATRIX_PATH", tmp_path / "tests" / "fixtures" / "matrix.jsonl")
    monkeypatch.setattr(generator, "OVERRIDES_PATH", tmp_path / "tests" / "fixtures" / "overrides.json")
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py"])
    return tmp_path


def test_cli_check_flag_fails_on_missing_matrix(matrix_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Checking an absent artifact reports failure without creating it."""
    matrix_path = matrix_workspace / "tests" / "fixtures" / "matrix.jsonl"
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 1
    assert not matrix_path.exists()


def test_cli_check_flag_passes_on_fresh_matrix(matrix_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A writer/checker round trip succeeds without the check rewriting its input."""
    assert generator.main() == 0
    matrix_path = matrix_workspace / "tests" / "fixtures" / "matrix.jsonl"
    written = matrix_path.read_bytes()
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 0
    assert matrix_path.read_bytes() == written


@pytest.mark.parametrize("drift", ["serialization", "evidence", "missing-row"])
def test_cli_check_flag_rejects_existing_matrix_drift(
    matrix_workspace: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], drift: str
) -> None:
    """Reject corrupted existing artifacts, including PR #3910's compact JSON."""
    assert generator.main() == 0
    matrix_path = matrix_workspace / "tests" / "fixtures" / "matrix.jsonl"
    rows = [json.loads(line) for line in matrix_path.read_text(encoding="utf-8").splitlines()]
    if drift == "serialization":
        changed = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
    elif drift == "evidence":
        rows[0]["status"] = "PASSED"
        changed = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    else:
        changed = ""
    matrix_path.write_text(changed, encoding="utf-8")
    before_check = matrix_path.read_bytes()
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 1
    assert str(matrix_path) in capsys.readouterr().out
    assert matrix_path.read_bytes() == before_check


def test_cli_check_flag_detects_added_skill(matrix_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A newly declared skill makes the preserved artifact stale before regeneration."""
    assert generator.main() == 0
    matrix_path = matrix_workspace / "tests" / "fixtures" / "matrix.jsonl"
    written = matrix_path.read_bytes()
    _write_skill(matrix_workspace / "plugins" / "sample-plugin" / "skills", "added", "added")
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 1
    assert matrix_path.read_bytes() == written


def test_cli_check_flag_accepts_skill_body_changes(matrix_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Inventory ignores skill prose when declared identity and evidence are unchanged."""
    assert generator.main() == 0
    matrix_path = matrix_workspace / "tests" / "fixtures" / "matrix.jsonl"
    written = matrix_path.read_bytes()
    skill_path = matrix_workspace / "plugins" / "sample-plugin" / "skills" / "example" / "SKILL.md"
    skill_path.write_text("---\nname: example\n---\nRevised instructions.\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["generate_codex_skill_activation_matrix.py", "--check"])

    exit_code = generator.main()

    assert exit_code == 0
    assert matrix_path.read_bytes() == written
