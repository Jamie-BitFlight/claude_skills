"""Quality gate plan generator for the complete-implementation workflow.

Produces YAML strings for quality-gate plans passed to ``sam_create`` by
the ``complete-implementation`` skill:

- ``build_quality_gate_plan``: 6-task plan (QG prefix) for SAM-planned features.
- ``build_proportional_quality_gate_plan``: 3-task plan (PQG prefix) for
  issue-only fixes that bypass the SAM planning pipeline.

Both functions are pure — no file I/O, no MCP calls, no side effects.
"""

from __future__ import annotations

import io
import pathlib
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

# Ordered quality-gate phase definitions.
# Each entry maps directly to a SAM Task field set.
_PHASE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "T0",
        "title": "Multi-Perspective Review",
        "agent": "task-worker",
        "dependencies": [],
        "complexity": "high",
        "phase": 0,
    },
    {
        "id": "T1",
        "title": "Code Review",
        "agent": "code-reviewer",
        "dependencies": [],
        "complexity": "medium",
        "phase": 1,
    },
    {
        "id": "T2",
        "title": "Feature Verification",
        "agent": "feature-verifier",
        "dependencies": ["T1"],
        "complexity": "medium",
        "phase": 2,
    },
    {
        "id": "T3",
        "title": "Integration Check",
        "agent": "integration-checker",
        "dependencies": ["T2"],
        "complexity": "medium",
        "phase": 3,
    },
    {
        "id": "T4",
        "title": "Documentation Drift Audit",
        "agent": "doc-drift-auditor",
        "dependencies": ["T3"],
        "complexity": "low",
        "phase": 4,
    },
    {
        "id": "T5",
        "title": "Documentation Update",
        "agent": "service-docs-maintainer",
        "dependencies": ["T4"],
        "complexity": "low",
        "phase": 5,
    },
    {
        "id": "T6",
        "title": "Context Refinement",
        "agent": "context-refinement",
        "dependencies": ["T5"],
        "complexity": "medium",
        "phase": 6,
    },
]


def _make_yaml() -> YAML:
    """Return a ruamel.yaml instance configured for plain YAML output.

    Returns:
        Configured ``YAML`` instance.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # prevent line-wrapping in long body strings
    return yaml


def _phase_body(phase: int, impl_plan_address: str, issue: str | None = None) -> str:
    """Build the task body markdown for a quality-gate phase.

    Args:
        phase: Phase number (0-6).
        impl_plan_address: Address of the implementation plan, e.g. ``P003``.
        issue: GitHub issue number, e.g. ``"42"``, or ``None`` to omit.

    Returns:
        Markdown string cross-referencing the implementation plan.
    """
    phase_def = next((p for p in _PHASE_DEFINITIONS if p["phase"] == phase), None)
    title = phase_def["title"] if phase_def is not None else f"Phase {phase}"
    if phase == 0:
        issue_arg = f" --issue {issue}" if issue is not None else ""
        return (
            f"## Quality Gate Phase 0: Multi-Perspective Review\n\n"
            f"Implementation plan: `{impl_plan_address}`\n\n"
            f"Invoke the multi-perspective review skill:\n"
            f'Skill(skill="dh:multi-perspective-review", args="--diff HEAD~1..HEAD{issue_arg}")\n\n'
            f"This phase dispatches four parallel reviewer agents (Security, Performance, Quality,\n"
            f"Accessibility). The skill exits non-zero if any perspective returns REJECT.\n"
            f"Mark this task complete only after all four perspectives have returned APPROVE or SKIP.\n"
        )
    return (
        f"## Quality Gate Phase {phase}: {title}\n\n"
        f"Implementation plan: `{impl_plan_address}`\n\n"
        f"Run this phase as instructed by the `{title.lower()}` agent.\n"
        f"Mark this task complete after the phase agent finishes.\n"
    )


def build_quality_gate_plan(
    slug: str, issue: str | None, impl_plan_address: str, phase_4_drift_found: bool | None = None
) -> str:
    """Generate YAML for a 7-task quality-gate plan.

    The returned string is intended to be passed directly to ``sam_create``
    as the ``tasks_yaml`` argument. No file I/O is performed.

    Args:
        slug: Feature slug used as the plan ``feature`` identifier,
            e.g. ``"my-feature"``.
        issue: GitHub issue number (as a string) to embed in the plan, or
            ``None`` to omit the field.
        impl_plan_address: Address of the implementation plan this QG plan
            is gating, e.g. ``"P003"``. Embedded in each task body.
        phase_4_drift_found: Reserved for future use. When ``False``, callers
            may later mark T5 as SKIPPED via ``sam_state``. This parameter
            does not affect the generated YAML — T5 is always emitted with
            status ``not-started``.

    Returns:
        YAML string containing plan-level metadata and 7 task definitions.
        The string is valid YAML parseable by ``ruamel.yaml`` and validates
        against the ``Plan`` model.
    """
    plan_data: dict[str, Any] = {
        "feature": slug,
        "version": "1.0",
        "goal": f"Quality gate verification for implementation plan {impl_plan_address}",
        "tasks": [],
    }

    if issue is not None:
        plan_data["issue"] = issue

    tasks: list[dict[str, Any]] = []
    for defn in _PHASE_DEFINITIONS:
        body_text = _phase_body(defn["phase"], impl_plan_address, issue=issue)
        task: dict[str, Any] = {
            "id": defn["id"],
            "title": defn["title"],
            "status": "not-started",
            "agent": defn["agent"],
            "dependencies": list(defn["dependencies"]),
            "priority": 1,
            "complexity": defn["complexity"],
            "body": LiteralScalarString(body_text),
        }
        tasks.append(task)

    plan_data["tasks"] = tasks

    yaml = _make_yaml()
    stream = io.StringIO()
    yaml.dump(plan_data, stream)
    return stream.getvalue()


# ---------------------------------------------------------------------------
# Proportional quality-gate definitions (3-task plan for issue-only fixes)
# ---------------------------------------------------------------------------

# Phase index constant — avoids PLR2004 magic-number lint errors
_PROPORTIONAL_PHASE_TEST_VERIFY = 2

_PROPORTIONAL_PHASE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "T1",
        "title": "Code Review",
        "agent": "code-reviewer",
        "dependencies": [],
        "complexity": "medium",
        "phase": 1,
    },
    {
        "id": "T2",
        "title": "Test Verification",
        "agent": "task-worker",
        "dependencies": ["T1"],
        "complexity": "low",
        "phase": 2,
    },
    {
        "id": "T3",
        "title": "Acceptance Criteria Check",
        "agent": "task-worker",
        "dependencies": ["T2"],
        "complexity": "low",
        "phase": 3,
    },
]


def _proportional_phase_body(
    phase: int, issue_number: str, modified_files: list[str], acceptance_criteria: str | None
) -> str:
    """Build the task body markdown for a proportional quality-gate phase.

    Args:
        phase: Phase number (1-3).
        issue_number: GitHub issue number, e.g. ``"42"``.
        modified_files: List of file paths changed by the fix, e.g.
            ``["src/foo.py", "src/bar.py"]``.
        acceptance_criteria: Raw acceptance criteria text extracted from the
            issue body, or ``None`` if none were found.

    Returns:
        Markdown string describing what this phase agent should do.
    """
    if phase == 1:
        lines = [
            "## Proportional Gate Phase 1: Code Review",
            "",
            f"Review the changes made for issue #{issue_number}.",
            "",
        ]
        if modified_files:
            lines += ["**Modified files:**", ""]
            lines += [f"- `{f}`" for f in modified_files]
        else:
            lines += ["No specific modified files identified. Review all uncommitted changes."]
        lines += [
            "",
            "Check for correctness, style, and potential regressions.",
            "Mark this task complete when code review is finished.",
        ]
        return "\n".join(lines) + "\n"

    if phase == _PROPORTIONAL_PHASE_TEST_VERIFY:
        lines = [
            "## Proportional Gate Phase 2: Test Verification",
            "",
            f"Run tests to verify the fix for issue #{issue_number} does not introduce regressions.",
            "",
        ]
        test_files = _derive_test_files(modified_files)
        if test_files:
            lines += ["**Test commands:**", ""]
            lines += [f"- `uv run pytest {f}`" for f in test_files]
        else:
            lines += ["**Test command:**", "", "- `uv run pytest`"]
        lines += ["", "Mark this task complete when all tests pass."]
        return "\n".join(lines) + "\n"

    # phase == 3
    lines = [
        "## Proportional Gate Phase 3: Acceptance Criteria Check",
        "",
        f"Verify that issue #{issue_number} acceptance criteria are satisfied.",
        "",
    ]
    if acceptance_criteria:
        lines += ["**Acceptance criteria:**", "", acceptance_criteria, ""]
        lines += ["Confirm each criterion above is met before marking this task complete."]
    else:
        lines += ["No acceptance criteria found in issue body. This phase passes trivially."]
    lines += ["", "Mark this task complete when verification is done."]
    return "\n".join(lines) + "\n"


def _derive_test_files(modified_files: list[str]) -> list[str]:
    """Derive test file paths from a list of source file paths.

    Maps ``src/foo/bar.py`` → ``tests/test_bar.py`` and
    ``packages/foo/bar.py`` → ``tests/test_bar.py``.  Only returns paths
    that follow the ``*.py`` extension convention; non-Python files are
    ignored.

    Args:
        modified_files: List of modified source file paths.

    Returns:
        Deduplicated list of inferred test file paths (may be empty).
    """
    test_files: list[str] = []
    seen: set[str] = set()
    for path in modified_files:
        p = pathlib.Path(path)
        if p.suffix != ".py":
            continue
        # Skip files that are already test files
        candidate = path if p.name.startswith("test_") else f"tests/test_{p.stem}.py"
        if candidate not in seen:
            seen.add(candidate)
            test_files.append(candidate)
    return test_files


def build_proportional_quality_gate_plan(
    slug: str, issue: str, modified_files: list[str], acceptance_criteria: str | None
) -> str:
    """Generate YAML for a 3-task proportional quality-gate plan.

    Used by ``complete-implementation`` when the input is a GitHub issue
    number without a linked SAM plan.  The returned string is intended to
    be passed directly to ``sam_create`` as the ``tasks_yaml`` argument.
    No file I/O is performed.

    Args:
        slug: Feature slug used as the plan ``feature`` identifier,
            e.g. ``"issue-42"``.
        issue: GitHub issue number as a string, e.g. ``"42"``.
        modified_files: List of file paths modified by the fix, used to
            scope code review and derive test commands.
        acceptance_criteria: Raw acceptance criteria text extracted from
            the issue body, or ``None`` if none were found.

    Returns:
        YAML string containing plan-level metadata and 3 task definitions.
        The string is valid YAML parseable by ``ruamel.yaml`` and validates
        against the ``Plan`` model.
    """
    plan_data: dict[str, Any] = {
        "feature": slug,
        "version": "1.0",
        "goal": f"Proportional quality gate verification for issue #{issue}",
        "issue": issue,
        "tasks": [],
    }

    tasks: list[dict[str, Any]] = []
    for defn in _PROPORTIONAL_PHASE_DEFINITIONS:
        body_text = _proportional_phase_body(defn["phase"], issue, modified_files, acceptance_criteria)
        task: dict[str, Any] = {
            "id": defn["id"],
            "title": defn["title"],
            "status": "not-started",
            "agent": defn["agent"],
            "dependencies": list(defn["dependencies"]),
            "priority": 1,
            "complexity": defn["complexity"],
            "body": LiteralScalarString(body_text),
        }
        tasks.append(task)

    plan_data["tasks"] = tasks

    yaml = _make_yaml()
    stream = io.StringIO()
    yaml.dump(plan_data, stream)
    return stream.getvalue()
