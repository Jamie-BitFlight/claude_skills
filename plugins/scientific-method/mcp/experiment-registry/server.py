#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastmcp>=3.0.0",
#   "pydantic>=2.0",
# ]
# ///
"""Experiment Registry MCP Server.

Manages controlled experiment lifecycle: creation, stepping, validation, and completion.
Experiment types are composable JSON definitions — a universal core merged with domain extensions.
State persists to .claude/experiments/{id}/state.json.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from models import StepExtension
from pydantic import Field
from registry_loader import RegistryLoader
from state_manager import StateManager

mcp = FastMCP("experiment-registry")

# Module-level loader — registry files are static; one load per server process.
_loader = RegistryLoader()


def _make_state_manager(project_root: str | None) -> StateManager:
    """Return a StateManager rooted at *project_root* (defaults to cwd).

    Args:
        project_root: Optional project root path. Falls back to the current
            working directory when ``None`` or empty.

    Returns:
        A configured ``StateManager`` instance.
    """
    root = Path(project_root) if project_root else Path(Path.cwd())
    return StateManager(project_root=root, loader=_loader)


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True})
def list_experiment_types() -> dict[str, Any]:
    """List all registered experiment types with their names and descriptions.

    Returns a mapping of type names to concise descriptions so callers can
    choose the right base type before starting an experiment.

    Returns:
        dict: Keys ``types`` (list of dicts with ``name`` and ``description``)
            and ``count`` (int).
    """
    types = _loader.list_types()
    return {"types": [{"name": t.name, "description": t.description} for t in types], "count": len(types)}


@mcp.tool(annotations={"readOnlyHint": True})
def inspect_experiment_type(
    name: Annotated[str, Field(description="Registry name of the experiment type, e.g. 'ai_agent_testing'.")],
) -> dict[str, Any]:
    """Return the full definition for a single registered experiment type.

    Includes steps, artefact requirements, checklists, rubric templates, and
    anti-patterns for the requested type.

    Args:
        name: Registry name of the experiment type.

    Returns:
        dict: Full experiment type definition including ``name``, ``description``,
            ``extends``, ``steps``, ``rubric_templates``, and ``anti_patterns``.

    Raises:
        ToolError: If *name* is not a known experiment type.
    """
    try:
        exp_type = _loader.get_type(name)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    steps = [
        {
            "id": s.id,
            "name": s.name,
            "required_artefacts": s.required_artefacts,
            "validation": s.validation,
            "checklist": s.checklist,
            "human_input_required": s.human_input_required,
            "human_input_description": s.human_input_description,
        }
        for s in exp_type.steps
    ]

    step_extensions = {
        step_id: {
            "additional_artefacts": ext.additional_artefacts,
            "checklist": ext.checklist,
            "human_input_required": ext.human_input_required,
            "human_input_description": ext.human_input_description,
        }
        for step_id, ext in exp_type.step_extensions.items()
    }

    rubric_templates = [
        {"name": r.name, "observable": r.observable, "pass": r.pass_, "fail": r.fail} for r in exp_type.rubric_templates
    ]

    return {
        "name": exp_type.name,
        "description": exp_type.description,
        "extends": exp_type.extends,
        "steps": steps,
        "step_extensions": step_extensions,
        "rubric_templates": rubric_templates,
        "anti_patterns": exp_type.anti_patterns,
    }


# ---------------------------------------------------------------------------
# State-mutating tools
# ---------------------------------------------------------------------------


@mcp.tool()
def start_experiment(
    base: Annotated[
        str, Field(description="Name of the registered experiment type to use as the base, e.g. 'ai_agent_testing'.")
    ],
    context: Annotated[str, Field(description="Human-readable description of what this experiment is investigating.")],
    extensions: Annotated[
        dict[str, dict[str, Any]] | None,
        Field(
            default=None,
            description=(
                "Optional inline step extensions keyed by step id. Each value is a dict with optional keys: "
                "'additional_artefacts' (list[str]), 'checklist' (list[str]), "
                "'human_input_required' (bool), 'human_input_description' (str)."
            ),
        ),
    ] = None,
    project_root: Annotated[
        str | None,
        Field(default=None, description="Project root directory. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """Create a new experiment from a registered type and return its initial state.

    Merges core + base + inline extensions into a fully resolved step list,
    creates persisted state, and returns the experiment ID plus the first step.

    Args:
        base: Registered experiment type name.
        context: Human-readable experiment purpose.
        extensions: Optional inline step extensions applied on top of the
            domain type extensions. Keys are step ids.
        project_root: Project root directory. Defaults to cwd.

    Returns:
        dict: Contains ``experiment_id``, ``base``, ``context``, ``status``,
            ``first_step`` (step id string), ``total_steps`` (int), and
            ``state_path`` (str).

    Raises:
        ToolError: If *base* is not a known experiment type.
    """
    parsed_extensions: dict[str, StepExtension] | None = None
    if extensions:
        try:
            parsed_extensions = {step_id: StepExtension(**ext) for step_id, ext in extensions.items()}
        except Exception as exc:
            raise ToolError(f"Invalid extensions format: {exc}") from exc

    manager = _make_state_manager(project_root)
    try:
        state = manager.create_experiment(base=base, context=context, extensions=parsed_extensions)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    first_step_def = state.merged_steps[0] if state.merged_steps else None

    return {
        "experiment_id": state.id,
        "base": state.base,
        "context": state.context,
        "status": state.status,
        "first_step": {
            "id": first_step_def.id,
            "name": first_step_def.name,
            "required_artefacts": first_step_def.required_artefacts,
            "checklist": first_step_def.checklist,
            "human_input_required": first_step_def.human_input_required,
            "human_input_description": first_step_def.human_input_description,
        }
        if first_step_def
        else None,
        "total_steps": len(state.merged_steps),
        "state_path": str(manager._state_path(state.id)),  # noqa: SLF001
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_current_step(
    experiment_id: Annotated[str, Field(description="Unique experiment identifier returned by start_experiment.")],
    project_root: Annotated[
        str | None,
        Field(default=None, description="Project root directory. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """Return details for the current step of an in-progress experiment.

    Includes which artefacts are required, which are already present, what
    is missing, and whether human input is needed before the step can complete.

    Args:
        experiment_id: Unique experiment identifier.
        project_root: Project root directory. Defaults to cwd.

    Returns:
        dict: Contains ``experiment_id``, ``status``, ``current_step`` (dict
            with full step details), ``provided_artefacts`` (dict),
            ``missing_artefacts`` (list), and ``completed_steps`` (list).

    Raises:
        ToolError: If the experiment is not found.
    """
    manager = _make_state_manager(project_root)
    try:
        state = manager.load_experiment(experiment_id)
        step = manager.get_current_step(experiment_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    missing = [a for a in step.required_artefacts if a not in state.artefacts]

    return {
        "experiment_id": experiment_id,
        "status": state.status,
        "current_step": {
            "id": step.id,
            "name": step.name,
            "required_artefacts": step.required_artefacts,
            "validation": step.validation,
            "checklist": step.checklist,
            "human_input_required": step.human_input_required,
            "human_input_description": step.human_input_description,
        },
        "provided_artefacts": state.artefacts,
        "missing_artefacts": missing,
        "completed_steps": state.completed_steps,
        "iteration_count": state.iteration_count,
    }


@mcp.tool()
def complete_step(
    experiment_id: Annotated[str, Field(description="Unique experiment identifier.")],
    step_id: Annotated[str, Field(description="Id of the step being completed — must match the current step.")],
    artefacts: Annotated[
        dict[str, str],
        Field(description="Key-value artefacts produced during this step. Keys must satisfy all required_artefacts."),
    ],
    rubric_scores: Annotated[
        dict[str, bool] | None,
        Field(
            default=None,
            description=(
                "Per-criterion pass/fail scores required when completing the 'iterate' step. "
                "Keys are criterion names from the experiment's rubric; values are booleans. "
                "The MCP derives criteria_passed from these scores — do not pass criteria_passed "
                "in artefacts. Required for 'iterate'; ignored for all other steps."
            ),
        ),
    ] = None,
    project_root: Annotated[
        str | None,
        Field(default=None, description="Project root directory. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """Attempt to complete a step and advance the experiment to the next step.

    Validates that all required artefacts are present, runs the full validation
    layer (content checks, file existence, freeze integrity, iteration output,
    rubric scoring), handles the 'iterate' step loop, and advances or terminates
    the experiment accordingly.

    Args:
        experiment_id: Unique experiment identifier.
        step_id: Id of the step being completed.
        artefacts: Key-value pairs produced during this step.
        rubric_scores: Per-criterion boolean scores required for the 'iterate'
            step. Keys must match criterion names from the experiment's rubric.
            The MCP computes criteria_passed from these — not from artefacts.
        project_root: Project root directory. Defaults to cwd.

    Returns:
        dict: Contains ``success`` (bool). On success: ``next_step`` (str or
            None), ``status`` (str). On failure: ``missing_artefacts`` (list),
            ``blocked_on_human_input`` (bool) with ``description`` (str), or
            ``validation_errors`` (list of error dicts with ``code`` and
            ``message`` keys).

    Raises:
        ToolError: If *step_id* does not match the current step or the
            experiment is not found.
    """
    manager = _make_state_manager(project_root)
    try:
        result = manager.complete_step(
            experiment_id=experiment_id, step_id=step_id, artefacts=artefacts, rubric_scores=rubric_scores
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    return dict(result)


@mcp.tool(annotations={"readOnlyHint": True})
def list_experiments(
    project_root: Annotated[
        str | None,
        Field(default=None, description="Project root directory. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """List all persisted experiments in the project, with their current status.

    Returns summary information useful for selecting an experiment to resume.

    Args:
        project_root: Project root directory. Defaults to cwd.

    Returns:
        dict: Keys ``experiments`` (list of summary dicts) and ``count`` (int).
    """
    manager = _make_state_manager(project_root)
    experiments = manager.list_experiments()

    summaries = [
        {
            "id": e.id,
            "base": e.base,
            "status": e.status,
            "context": e.context,
            "current_step": e.current_step,
            "created": e.created,
            "last_updated": e.last_updated,
        }
        for e in experiments
    ]

    return {"experiments": summaries, "count": len(summaries)}


@mcp.tool(annotations={"readOnlyHint": True})
def resume_experiment(
    experiment_id: Annotated[str, Field(description="Unique experiment identifier to resume.")],
    project_root: Annotated[
        str | None,
        Field(default=None, description="Project root directory. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """Load a persisted experiment and return its current position.

    Use this to restore context after a session break before calling
    get_current_step or complete_step.

    Args:
        experiment_id: Unique experiment identifier.
        project_root: Project root directory. Defaults to cwd.

    Returns:
        dict: Contains ``experiment_id``, ``base``, ``context``, ``status``,
            ``current_step`` (step id), ``completed_steps`` (list),
            ``total_steps`` (int), ``iteration_count`` (int), and
            ``artefacts`` (dict of already-provided artefacts).

    Raises:
        ToolError: If the experiment is not found.
    """
    manager = _make_state_manager(project_root)
    try:
        state = manager.load_experiment(experiment_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    return {
        "experiment_id": state.id,
        "base": state.base,
        "context": state.context,
        "status": state.status,
        "current_step": state.current_step,
        "completed_steps": state.completed_steps,
        "total_steps": len(state.merged_steps),
        "iteration_count": state.iteration_count,
        "artefacts": state.artefacts,
        "created": state.created,
        "last_updated": state.last_updated,
    }


@mcp.tool(annotations={"readOnlyHint": True})
def get_experiment_summary(
    experiment_id: Annotated[str, Field(description="Unique experiment identifier.")],
    project_root: Annotated[
        str | None,
        Field(default=None, description="Project root directory. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """Return a final summary of an experiment for retrospective handoff.

    Includes file paths, artefact inventory, and final status — intended to be
    passed to the retrospective-analyst agent after an experiment completes.

    Args:
        experiment_id: Unique experiment identifier.
        project_root: Project root directory. Defaults to cwd.

    Returns:
        dict: Contains ``id``, ``base``, ``status``, ``context``, ``created``,
            ``last_updated``, ``completed_steps``, ``artefacts``,
            ``iteration_count``, and ``state_file_path`` (str).

    Raises:
        ToolError: If the experiment is not found.
    """
    manager = _make_state_manager(project_root)
    try:
        summary = manager.get_experiment_summary(experiment_id)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    state_path = manager._state_path(experiment_id)  # noqa: SLF001
    return {**summary, "state_file_path": str(state_path)}


if __name__ == "__main__":
    mcp.run()
