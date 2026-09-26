"""Static contract regressions for the holistic-linting redesign.

These tests cover deterministic source contracts from the E01-E17 review matrix.
Live model/host behavior remains a separate certification surface.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills" / "holistic-linting" / "SKILL.md"
ARCH = ROOT / "ARCHITECTURE.md"
RESOLVER = ROOT / "skills" / "holistic-linting-resolver" / "SKILL.md"
AGENT = ROOT / "agents" / "linting-root-cause-resolver.md"
REVIEWER = ROOT / "agents" / "post-linting-architecture-reviewer.md"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_requested_unchanged_scope_and_discovery_terminals_are_explicit() -> None:
    skill = text(SKILL)
    assert "explicitly requested files/directories" in skill
    for outcome in ("COMPLETE", "NO_APPLICABLE_GATES", "INCOMPLETE"):
        assert outcome in skill
    assert "empty/unknown result" in skill


def test_runtime_discovery_does_not_route_through_setup_writer() -> None:
    skill = text(SKILL)
    assert "Do not use `discover_linters.py` for runtime discovery" in skill
    assert "[detect_hook_tool.py](./scripts/detect_hook_tool.py)" in skill


def test_gate_success_is_separate_from_diagnostic_disposition() -> None:
    skill = text(SKILL)
    assert "zero exit can still emit warnings/advisories" in skill
    assert "do not bypass out-of-scope/advisory accounting" in skill


def test_missing_capability_and_read_only_writer_handoff_are_explicit() -> None:
    skill = text(SKILL)
    assert "actually available in the host" in skill
    assert "conditional assessment lanes, not automatic writers" in skill
    assert "caller or another authorized writer" in skill


def test_integrity_verification_rejects_manufactured_green() -> None:
    skill = text(SKILL)
    for phrase in (
        "newly added/broadened suppression",
        "severity/applicability weakening",
        "gate bypass/removal",
        "deletion of required behavior",
    ):
        assert phrase in skill
    assert "successful linter rerun alone is insufficient" in skill


def test_out_of_scope_payload_has_delivery_fallback() -> None:
    skill = text(SKILL)
    for phrase in ("tool/gate", "exact diagnostic", "reproduction command/context", "destination/receipt"):
        assert phrase in skill
    assert "return the complete payload to the caller" in skill


def test_compatibility_inputs_and_outputs_are_explicit() -> None:
    resolver = text(RESOLVER)
    agent = text(AGENT)
    assert "file/scope input" in resolver
    assert "supplied diagnostic evidence" in resolver
    assert "STATUS: DONE | BLOCKED" in agent
    assert "explicit none when clean" in agent


def test_rule_lookup_retains_version_and_offline_paths() -> None:
    skill = text(SKILL)
    assert "ruff rule <CODE>" in skill
    assert "vendored MyPy docs" in skill
    assert "Bandit rule index" in skill
    assert "version uncertainty" in skill


def test_bounded_reviewer_has_status_and_false_suppression_guard() -> None:
    reviewer = text(REVIEWER)
    assert "strings/fixtures" in reviewer
    assert "unchanged pre-existing comments" in reviewer
    assert "STATUS: DONE | BLOCKED" in reviewer
    assert "UNVERIFIED" in reviewer


def test_architecture_preserves_evidence_invalidation_and_parallelism_semantics() -> None:
    arch = text(ARCH)
    assert "Evidence invalidated by a later edit" in arch
    assert "A filename neither proves independence nor dependence" in arch
    assert "successful command" in arch
    assert "advisory diagnostics" in arch


def test_declared_runtime_and_fallback_resources_are_reachable() -> None:
    skill_root = SKILL.parent
    expected = [
        skill_root / "scripts" / "detect_hook_tool.py",
        skill_root / "references" / "rules" / "mypy" / "index.md",
        skill_root / "references" / "mypy-docs",
        skill_root / "references" / "rules" / "bandit" / "index.md",
    ]
    for target in expected:
        assert target.exists(), f"declared holistic-linting resource is missing: {target}"
    assert expected[0].is_file()
    assert expected[1].is_file()
    assert expected[2].is_dir()
    assert expected[3].is_file()


def _assert_required_resources(root: Path) -> None:
    required = [
        root / "scripts" / "detect_hook_tool.py",
        root / "references" / "rules" / "mypy" / "index.md",
        root / "references" / "mypy-docs",
        root / "references" / "rules" / "bandit" / "index.md",
    ]
    missing = [path for path in required if not path.exists()]
    assert not missing, f"missing declared resources: {missing}"


def test_missing_declared_resource_negative_control(tmp_path: Path) -> None:
    import shutil

    copied = tmp_path / "holistic-linting"
    shutil.copytree(SKILL.parent, copied)
    (copied / "scripts" / "detect_hook_tool.py").unlink()
    try:
        _assert_required_resources(copied)
    except AssertionError:
        pass
    else:
        raise AssertionError("negative control did not detect a missing runtime helper")
