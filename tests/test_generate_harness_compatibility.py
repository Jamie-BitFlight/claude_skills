"""Tests for the on-demand cross-harness compatibility view generator."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_harness_compatibility.py"


def create_minimal_repo(tmp_path: Path) -> Path:
    """Create the tracked inputs needed to exercise the generator CLI."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / SCRIPT_PATH.name).write_text(SCRIPT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "harness_compatibility_verification.json").write_text('{"plugins": {}}\n', encoding="utf-8")
    plugin_dir = tmp_path / "plugins" / "example"
    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text("{}\n", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text("{}\n", encoding="utf-8")
    skill_dir = plugin_dir / "skills" / "example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("${CLAUDE_PLUGIN_ROOT} ${CLAUDE_SKILL_DIR}\n", encoding="utf-8")
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "example.md").write_text("example\n", encoding="utf-8")
    (plugin_dir / "mcp.json").write_text('{"mcpServers": {"example": {}}}\n', encoding="utf-8")
    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "hooks.json").write_text("{}\n", encoding="utf-8")
    return tmp_path / "harness_compatibility.json"


def run_generator(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the documented self-contained generator command in the clean fixture."""
    return subprocess.run(
        ["uv", "run", "--script", "scripts/generate_harness_compatibility.py", *args],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )


def test_clean_clone_generates_complete_view_when_output_is_absent(tmp_path: Path) -> None:
    """Normal generation needs only tracked inputs, not a previous generated view."""
    output = create_minimal_repo(tmp_path)

    result = run_generator(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "wrote harness_compatibility.json (1 plugins)\n"
    generated = json.loads(output.read_text(encoding="utf-8"))
    example = generated["plugins"]["example"]
    assert example["manifests"] == {"claude": True, "codex": False, "portable": True, "hermes_native": False}
    assert example["components"] == {"skills": 1, "agents": 1, "mcp_servers": 1, "hooks": True}
    assert example["blockers"] == {"claude_plugin_root_uses": 1, "claude_skill_dir_uses": 1}
    assert example["verification"] == {
        harness: {"status": "unverified", "date": None, "notes": None} for harness in generated["harnesses"]
    }


def test_verification_evidence_is_merged_and_missing_entries_default(tmp_path: Path) -> None:
    """Sparse tracked evidence overrides only its named plugin and harness."""
    output = create_minimal_repo(tmp_path)
    (tmp_path / "plugins" / "defaulted" / "skills").mkdir(parents=True)
    (tmp_path / "harness_compatibility_verification.json").write_text(
        json.dumps({
            "plugins": {"example": {"codex": {"status": "verified", "date": "2026-09-21", "notes": "issue #3778"}}}
        }),
        encoding="utf-8",
    )

    result = run_generator(tmp_path)

    assert result.returncode == 0, result.stderr
    table = json.loads(output.read_text(encoding="utf-8"))
    assert table["plugins"]["example"]["verification"]["codex"] == {
        "status": "verified",
        "date": "2026-09-21",
        "notes": "issue #3778",
    }
    default = {"status": "unverified", "date": None, "notes": None}
    assert table["plugins"]["example"]["verification"]["hermes"] == default
    assert table["plugins"]["defaulted"]["verification"]["codex"] == default


@pytest.mark.parametrize("status", ["verifed", "unverified", "passed"])
def test_invalid_verification_status_is_rejected(tmp_path: Path, status: str) -> None:
    """Only the supported durable non-default status is accepted."""
    output = create_minimal_repo(tmp_path)
    (tmp_path / "harness_compatibility_verification.json").write_text(
        json.dumps({"plugins": {"example": {"codex": {"status": status, "date": "2026-09-21", "notes": "invalid"}}}}),
        encoding="utf-8",
    )

    result = run_generator(tmp_path)

    assert result.returncode != 0
    assert "Input should be 'verified'" in result.stderr
    assert not output.exists()


def test_check_validates_inputs_without_requiring_or_writing_ignored_output(tmp_path: Path) -> None:
    """Check mode succeeds in a clean clone and leaves the ignored view absent."""
    output = create_minimal_repo(tmp_path)

    result = run_generator(tmp_path, "--check")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "validated harness compatibility inputs (1 plugins)\n"
    assert not output.exists()
