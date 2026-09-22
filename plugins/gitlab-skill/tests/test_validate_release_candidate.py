from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPT = PLUGIN_ROOT / "skills" / "gitlab-skill" / "scripts" / "validate_release_candidate.py"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "candidate-ci" / ".gitlab-ci.yml"
INVALID_RESPONSE = Path(__file__).parent / "fixtures" / "candidate-ci" / "lint-invalid.json"


def load_module() -> ModuleType:
    """Load the standalone candidate validator."""
    spec = importlib.util.spec_from_file_location("validate_release_candidate", SCRIPT)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_include_order_and_root_precedence() -> None:
    """Nested includes resolve first, later includes win, and root wins last."""
    module = load_module()
    candidate = module.resolve_candidate(FIXTURE_ROOT)

    assert "include" not in candidate
    assert candidate["variables"] == {"NESTED": "included", "FIRST": "included", "SHARED": "root", "SECOND": "included"}
    assert candidate["ordered_job"]["stage"] == "second"
    assert candidate["root_job"]["stage"] == "verify"


def test_candidate_lint_submits_include_free_static_content() -> None:
    """The helper makes one static content request and defers event contexts."""
    module = load_module()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(arguments: list[str], payload: str, _timeout: float) -> str:
        decoded = json.loads(payload)
        calls.append((arguments, decoded))
        return json.dumps({"valid": True, "errors": [], "jobs": [{"name": "root_job"}]})

    result = module.validate_candidate(
        root_file=FIXTURE_ROOT, host="gitlab.example", project_id=529, timeout=5, runner=runner
    )

    assert result == {
        "ok": True,
        "valid": True,
        "errors": [],
        "jobs": ["root_job"],
        "pre_merge_contexts": ["static"],
        "deferred_contexts": ["default_branch", "matching_tag", "nonmatching_tag"],
    }
    arguments, payload = calls[0]
    assert arguments[-1] == "projects/529/ci/lint"
    assert "ref" not in payload
    assert "dry_run" not in payload
    assert "include:" not in str(payload["content"])


def test_candidate_lint_preserves_full_compact_errors() -> None:
    """Invalid lint returns every server error in compact JSON output."""
    module = load_module()

    def runner(_arguments: list[str], _payload: str, _timeout: float) -> str:
        return INVALID_RESPONSE.read_text(encoding="utf-8")

    result = module.validate_candidate(
        root_file=FIXTURE_ROOT, host="gitlab.example", project_id=529, timeout=5, runner=runner
    )
    encoded = json.dumps(result, separators=(",", ":"))
    assert encoded == (
        '{"ok":false,"valid":false,"errors":["first error","second error"],"jobs":[],'
        '"pre_merge_contexts":["static"],'
        '"deferred_contexts":["default_branch","matching_tag","nonmatching_tag"]}'
    )


def test_remote_include_is_rejected_before_lint(tmp_path: Path) -> None:
    """Candidate resolution never emits the known-invalid remote include strategy."""
    module = load_module()
    root = tmp_path / ".gitlab-ci.yml"
    root.write_text("include:\n  - project: group/project\n    file: ci.yml\n", encoding="utf-8")
    with pytest.raises(module.CandidateValidationError, match="candidate includes must be project-local paths"):
        module.resolve_candidate(root)


def test_tag_contract_rejects_independent_literal_drift() -> None:
    """Prefix, regex, and wildcard are one resolved policy input."""
    module = load_module()
    valid = {
        "variables": {
            "RELEASE_TAG_PREFIX": "product-v",
            "RELEASE_TAG_REGEX": r"/^product-v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$/",
            "RELEASE_TAG_WILDCARD": "product-v*",
        }
    }
    module.validate_tag_contract(valid)
    valid["variables"]["RELEASE_TAG_WILDCARD"] = "other-*"
    with pytest.raises(module.CandidateValidationError, match="inconsistent"):
        module.validate_tag_contract(valid)
