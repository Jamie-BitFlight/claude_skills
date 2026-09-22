#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marko>=2.2.2",
#   "pydantic>=2.0",
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Standards regressions for the portable rebase skill boundary."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

import marko
import pytest
from marko import block, inline
from pydantic import BaseModel, ConfigDict, Field

from rebase_activation import ActionKind, ActivationResults, EvalPackage
from rebase_cli import emit_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
RESULTS_PATH = SKILL_ROOT / "evals" / "activation-results.json"
EVIDENCE_PATH = SKILL_ROOT / "references" / "runtime-evidence.json"
ROUTINE_DOCUMENTS = (
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "references" / "start-rebase.md",
    SKILL_ROOT / "references" / "active-rebase.md",
    SKILL_ROOT / "references" / "active-rebase-operation.md",
    SKILL_ROOT / "references" / "rebase-edge-cases.md",
)


class RuntimeClaim(BaseModel):
    """One machine-checkable repository-runtime citation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    source_symbol: str = Field(min_length=1)
    source_lines: tuple[int, int]
    observed_by: str = Field(min_length=1)


class RuntimeEvidence(BaseModel):
    """Citation manifest consumed by routine skill documents."""

    schema_version: int
    claims: list[RuntimeClaim] = Field(min_length=1)


def markdown_links(path: Path) -> list[str]:
    """Return every inline-link destination in one Markdown document.

    Returns:
        Link destinations in document order.
    """
    document = marko.parse(path.read_text(encoding="utf-8"))
    destinations: list[str] = []
    stack = [document]
    while stack:
        node = stack.pop()
        if isinstance(node, inline.Link):
            destinations.append(node.dest)
        children = getattr(node, "children", None)
        if isinstance(children, list):
            stack.extend(reversed(children))
        elif isinstance(node, block.Document) and children is not None:
            stack.append(children)
    return destinations


def function_lines(path: Path) -> dict[str, tuple[int, int]]:
    """Return unambiguous function line spans keyed by name.

    Returns:
        Function start and end lines.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: (node.lineno, node.end_lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno is not None
    }


def test_installed_skill_directory_evidence_is_absolute_and_missing_metadata_fails_closed() -> None:
    """Reject unresolved routine command paths and command work after a missing-directory terminal."""
    package = EvalPackage.model_validate_json(EVALS_PATH.read_text(encoding="utf-8"))
    results = ActivationResults.model_validate_json(RESULTS_PATH.read_text(encoding="utf-8"))
    missing_case = next(
        (case for case in results.cases if case.final_terminal == "BLOCKED_SKILL_DIR_UNAVAILABLE"), None
    )
    assert missing_case is not None
    assert all(action.kind not in {ActionKind.COMMAND, ActionKind.MUTATION} for action in missing_case.actions)
    assert any(evaluation.required_terminal == "BLOCKED_SKILL_DIR_UNAVAILABLE" for evaluation in package.evals)

    for case in results.cases:
        if not case.observed_activation or case.final_terminal == "BLOCKED_SKILL_DIR_UNAVAILABLE":
            continue
        skill_directory = Path(getattr(case, "skill_directory", ""))
        assert skill_directory.is_absolute()
        for action in case.actions:
            if action.kind is ActionKind.COMMAND and action.script_path is not None:
                assert Path(action.script_path).is_absolute()
                assert Path(action.script_path).is_relative_to(skill_directory)


def test_runtime_claim_citations_resolve_to_current_symbols_and_observed_tests() -> None:
    """Keep each routine claim bound to current source and executable evidence."""
    assert EVIDENCE_PATH.is_file()
    evidence = RuntimeEvidence.model_validate_json(EVIDENCE_PATH.read_text(encoding="utf-8"))
    claims = {claim.id: claim for claim in evidence.claims}
    assert len(claims) == len(evidence.claims)
    cited_ids: set[str] = set()
    for document in ROUTINE_DOCUMENTS:
        links = markdown_links(document)
        document_claims = {
            target.partition("#")[2] for target in links if target.partition("#")[0].endswith("runtime-evidence.json")
        }
        assert document_claims, document
        cited_ids.update(document_claims)
    assert cited_ids == set(claims)

    for claim in claims.values():
        source = SKILL_ROOT / claim.source_path
        test_path_text, _, test_name = claim.observed_by.partition("::")
        assert source.is_file()
        assert function_lines(source)[claim.source_symbol] == claim.source_lines
        assert test_name in function_lines(SKILL_ROOT / test_path_text)


def test_every_executable_pep723_script_stays_below_the_split_boundary() -> None:
    """Include executable tests in the repository's readable-file boundary."""
    executable_scripts = [
        path for path in SCRIPTS.glob("*.py") if path.read_text(encoding="utf-8").startswith("#!/usr/bin/env -S uv run")
    ]
    assert executable_scripts
    assert {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in executable_scripts
        if len(path.read_text(encoding="utf-8").splitlines()) >= 500
    } == {}


def test_functions_stay_within_the_python_architecture_boundary() -> None:
    """Keep production and test functions below the documented 50-line boundary."""
    oversized: dict[str, int] = {}
    for path in SCRIPTS.glob("*.py"):
        for name, (start, end) in function_lines(path).items():
            if end - start + 1 > 50:
                oversized[f"{path.name}:{name}"] = end - start + 1
    assert oversized == {}


def test_instruction_route_validation_has_no_producer_imposed_byte_ceiling() -> None:
    """Reject source tests that limit complete safety instructions by byte count."""
    tree = ast.parse((SCRIPTS / "test_rebase_skill.py").read_text(encoding="utf-8"))
    capped_lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(operator, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for operator in node.ops):
            continue
        calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
        names = [child.id for child in ast.walk(node) if isinstance(child, ast.Name)]
        reads_bytes = any(isinstance(call.func, ast.Attribute) and call.func.attr == "read_bytes" for call in calls)
        if reads_bytes or any(name.endswith("_bytes") for name in names):
            capped_lines.append(node.lineno)
    assert capped_lines == []


def test_cli_json_boundary_rejects_untyped_mappings(capsys: pytest.CaptureFixture[str]) -> None:
    """Require every structured CLI response to cross the boundary as a Pydantic model."""
    with pytest.raises(TypeError):
        emit_json(cast("Any", {"state": "PLAN_INVALID"}))
    assert capsys.readouterr().out == ""


def test_managed_response_functions_do_not_advertise_mapping_contracts() -> None:
    """Keep public managed response annotations model-based rather than dict-based."""
    violations: list[str] = []
    for path in (SCRIPTS / "rebase_capture.py", SCRIPTS / "rebase_cli.py", SCRIPTS / "rebase_finalize.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        violations.extend(
            f"{path.name}:{node.name}"
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.returns is not None and "dict[" in ast.unparse(node.returns)
        )
    assert violations == []


def test_runtime_evidence_manifest_is_json() -> None:
    """Keep the citation manifest parseable by agents and validators."""
    assert json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))["schema_version"] == 1
