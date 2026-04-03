"""FastMCP server for SAM task/plan operations.

Exposes the same operations as the Typer CLI as MCP tools for use by
Claude Code agents and other MCP clients.

Tools:
    sam_read    — Read a task by address (returns TaskAssignment when task provided)
    sam_state   — Update a task's status
    sam_ready   — List ready tasks for a plan
    sam_status  — Get plan-level progress summary
    sam_list    — List all plans with search and pagination
    sam_create  — Create a new plan from YAML task definitions
    sam_update  — Update plan or task fields, or append a section
    sam_claim   — Claim a task (transition to in-progress)
"""

from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import Annotated, Any

import backlog_core.models as _backlog_models
import dh_paths
import tiktoken
from backlog_core.artifact_provider import GitHubArtifactProvider
from backlog_core.artifact_registry import ArtifactRegistry as _ArtifactRegistry
from backlog_core.models import ArtifactEntry, ArtifactStatus, ArtifactType, BacklogError
from fastmcp import FastMCP
from pydantic import Field
from ruamel.yaml import YAML, YAMLError

from sam_schema.core.addressing import AddressingError, resolve_plan_address
from sam_schema.core.models import TaskStatus
from sam_schema.core.query import (
    claim_task,
    create_plan,
    get_plan_status,
    get_ready_tasks,
    get_task_assignment,
    load_plan,
    update_plan_fields,
    update_status,
)
from sam_schema.readers.detect import FormatDetectionError

_log = logging.getLogger(__name__)
_artifact_registry = _ArtifactRegistry()

_PLAN_READ_ERRORS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    AddressingError,
    FormatDetectionError,
    KeyError,
    ValueError,
    TypeError,
)

_PLAN_DIR_SENTINEL = "plan"


def _resolve_plan_dir(plan_dir: str) -> Path:
    """Resolve the plan directory, using dh_paths when the caller passes the default sentinel.

    The MCP API exposes ``plan_dir`` with a default of ``"plan"`` (the legacy
    repo-relative path).  When a caller omits the parameter (or passes the
    sentinel value ``"plan"``), we route through :func:`dh_paths.plan_dir` so
    the resolved path follows the three-tier DH state layout.  Explicit
    non-sentinel values are resolved as-is, preserving backward compatibility
    for callers that supply a concrete path.

    Args:
        plan_dir: The raw ``plan_dir`` string from the MCP tool parameter.

    Returns:
        Absolute :class:`~pathlib.Path` to the plan directory.
    """
    if plan_dir == _PLAN_DIR_SENTINEL:
        return dh_paths.plan_dir()
    return Path(plan_dir)


# Token budget for auto-pagination: 4400 tokens (cl100k_base encoding).
_TOKEN_BUDGET: int = 4_400
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")

mcp: FastMCP = FastMCP(
    "sam",
    instructions=(
        "SAM (Structured Agent-Managed) task plan server. "
        "Use sam_read to inspect a plan or task. "
        "Use sam_claim to take ownership of a task before starting work. "
        "Use sam_state to update task status. "
        "Use sam_ready to list tasks ready for dispatch. "
        "Use sam_status for a plan-level progress summary. "
        "Use sam_list to enumerate all plans with optional search and pagination. "
        "Use sam_create to create a new plan from YAML task definitions. "
        "Use sam_update to set fields or append a markdown section to a task body."
    ),
)


def run_server() -> None:
    """Entry point for ``sam-mcp`` console script."""
    mcp.run()


@mcp.tool
def sam_read(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str | None, Field(description="Task ID (e.g., 'T3'). Omit to read plan-level fields only.")] = None,
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Read a plan or task and return its fields as a dict.

    When ``task`` is provided, returns a ``TaskAssignment`` dict that includes
    both plan-level context (``plan_goal``, ``plan_context``,
    ``plan_acceptance_criteria``) and the nested ``task`` object.  This gives
    agents everything they need in one call.

    When ``task`` is omitted, returns the ``Plan`` fields only.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID component (e.g., ``T3``). Optional.
        plan_dir: Path to the directory containing plan files.

    Returns:
        ``TaskAssignment`` fields as a JSON-serializable dict when ``task`` is
        provided, or ``Plan`` fields when ``task`` is omitted.  Returns a dict
        with an ``error`` key on failure.
    """
    try:
        plan_path = resolve_plan_address(plan, _resolve_plan_dir(plan_dir))
        if task is not None:
            result = get_task_assignment(plan_path, task)
            return result.model_dump(mode="json", by_alias=True, exclude_none=True)
        # Plan-only read: return Plan metadata without TaskAssignment wrapper.
        read_result = load_plan(plan_path)
        return read_result.plan.model_dump(mode="json", by_alias=True, exclude_none=True)
    except _PLAN_READ_ERRORS as exc:
        return {"error": str(exc)}


@mcp.tool
def sam_state(
    plan: Annotated[str, Field(description="Plan address")],
    task: Annotated[str, Field(description="Task ID")],
    status: Annotated[str, Field(description="New status value")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Update a task's status.

    Args:
        plan: Plan address component.
        task: Task ID component.
        status: New status string (e.g., ``complete``, ``in-progress``).
        plan_dir: Path to the directory containing plan files.

    Returns:
        Updated task fields as a JSON-serializable dict, or a dict with an
        ``error`` key on failure.
    """
    try:
        new_status = TaskStatus(status)
        plan_path = resolve_plan_address(plan, _resolve_plan_dir(plan_dir))
        result = update_status(plan_path, task, new_status)
        return result.model_dump(mode="json")
    except (FileNotFoundError, AddressingError, FormatDetectionError, KeyError, ValueError) as exc:
        return {"error": str(exc)}


@mcp.tool
def sam_ready(
    plan: Annotated[str, Field(description="Plan address")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    full: Annotated[bool, Field(description="Return full Task model dump instead of routing manifest")] = False,
) -> dict:
    """List tasks ready for dispatch.

    By default returns a compact 7-field routing manifest per task so the
    orchestrator can decide which agent to dispatch next without receiving the
    full task body (25+ fields).  Pass ``full=True`` to get the complete model
    dump (preserves backward compatibility for callers that need all fields).

    Args:
        plan: Plan address component.
        plan_dir: Path to the directory containing plan files.
        full: When True, return full Task model dump instead of routing manifest.

    Returns:
        Dict with ``ready_tasks`` list, ``count``, ``feature``, ``source_path``,
        and ``issue`` envelope fields, or a dict with an ``error`` key on failure.
    """
    try:
        plan_path = resolve_plan_address(plan, _resolve_plan_dir(plan_dir))
        read_result = load_plan(plan_path)
        loaded_plan = read_result.plan
        tasks = get_ready_tasks(plan_path)
        if full:
            ready_tasks: list[dict[str, Any]] = [t.model_dump(mode="json") for t in tasks]
        else:
            ready_tasks = [
                {
                    "id": t.id,
                    "task": t.title,
                    "agent": t.agent,
                    "skills": t.skills or [],
                    "dependencies": t.dependencies or [],
                    "status": str(t.status),
                    "priority": int(t.priority),
                }
                for t in tasks
            ]
        return {
            "ready_tasks": ready_tasks,
            "count": len(tasks),
            "feature": loaded_plan.feature,
            "source_path": str(loaded_plan.source_path or plan_path),
            "issue": loaded_plan.issue,
        }
    except _PLAN_READ_ERRORS as exc:
        return {"error": str(exc)}


@mcp.tool
def sam_status(
    plan: Annotated[str, Field(description="Plan address")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Get plan-level progress summary.

    Args:
        plan: Plan address component.
        plan_dir: Path to the directory containing plan files.

    Returns:
        ``PlanStatus`` fields as a JSON-serializable dict including
        ``total_tasks``, ``by_status``, ``ready_tasks``, ``blocked_tasks``,
        ``completion_pct``, and ``has_cycles``, or a dict with an ``error``
        key on failure.
    """
    try:
        plan_path = resolve_plan_address(plan, _resolve_plan_dir(plan_dir))
        result = get_plan_status(plan_path)
        return result.model_dump(mode="json")
    except (FileNotFoundError, AddressingError, FormatDetectionError, ValueError) as exc:
        return {"error": str(exc)}


def _paginate_results(
    all_items: list[dict[str, Any]],
    *,
    offset: int,
    limit: int | None,
    messages: list[str],
    warnings: list[str],
    errors: list[str],
    tool_name: str,
) -> dict[str, Any]:
    """Paginate ``all_items`` within the token budget and return the response dict.

    Returns:
        Dict with ``items``, ``count``, ``pagination``, ``messages``, ``warnings``, ``errors``,
        and optionally ``next_call``.
    """
    total = len(all_items)
    page_items = all_items[offset:]

    if limit is not None:
        effective_limit = limit
    else:
        effective_limit = len(page_items)
        for candidate_limit in range(1, len(page_items) + 1):
            if len(_enc.encode(json.dumps(page_items[:candidate_limit]))) > _TOKEN_BUDGET:
                effective_limit = max(1, candidate_limit - 1)
                break

    page = page_items[:effective_limit]
    has_more = (offset + len(page)) < total
    result: dict[str, Any] = {
        "items": page,
        "count": len(page),
        "pagination": {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more},
        "messages": messages,
        "warnings": warnings,
        "errors": errors,
    }
    if has_more:
        next_offset = offset + len(page)
        result["next_call"] = f"{tool_name}(offset={next_offset}, limit={effective_limit})"
    return result


def _plan_matches_search(plan_dict: dict[str, Any], search: str) -> bool:
    """Return True if ``search`` appears (case-insensitive) in any text field of ``plan_dict``.

    Checks ``feature``, ``description``, and ``goal`` — the Plan model's text fields.

    Args:
        plan_dict: JSON-serializable plan dict from ``Plan.model_dump``.
        search: Substring to search for (case-insensitive).

    Returns:
        True if the search term is found in any of the checked fields.
    """
    needle = search.lower()
    for field in ("feature", "description", "goal"):
        value = plan_dict.get(field)
        if isinstance(value, str) and needle in value.lower():
            return True
    return False


@mcp.tool
def sam_list(
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    search: Annotated[
        str | None, Field(description="Case-insensitive substring filter across feature, description, and goal fields")
    ] = None,
    offset: Annotated[int, Field(description="Zero-based index of the first item to return", ge=0)] = 0,
    limit: Annotated[
        int | None,
        Field(
            description="Maximum number of items to return. Defaults to auto-calculated value within 4400-token budget"
        ),
    ] = None,
) -> dict:
    """List all plans in ``plan_dir`` with optional search and automatic pagination.

    Reads every plan file found in ``plan_dir``, applies optional search filtering,
    then returns a page of results within the 4400-token budget (cl100k_base encoding).

    Search filtering checks the ``feature``, ``description``, and ``goal`` fields
    simultaneously, case-insensitively.  The ``offset`` and ``limit`` parameters
    let callers page through results explicitly.  When ``limit`` is omitted, the
    tool calculates a default limit that keeps the response within budget.

    When ``has_more`` is true in the ``pagination`` object, use the ``next_call``
    hint to request the next page.

    Args:
        plan_dir: Directory to scan for plan files (``*.yaml``, ``*.md``,
                  or subdirectories that are plan directories).
        search: Optional substring to filter by. Matched case-insensitively
                against ``feature``, ``description``, and ``goal`` fields.
        offset: Zero-based start index into the (filtered) result list.
        limit: Maximum items to return. Defaults to a budget-based calculation.

    Returns:
        Dict with keys:

        - ``items``: list of plan summary dicts (``feature``, ``goal``,
          ``description``, ``task_count``, ``path``).
        - ``count``: number of items in this page.
        - ``pagination``: ``{"offset": N, "limit": N, "total": N, "has_more": bool}``.
        - ``next_call``: hint string when ``has_more`` is true.
        - ``messages``: list of informational strings.
        - ``warnings``: list of non-fatal warning strings.
        - ``errors``: list of error strings (e.g. unreadable files).
    """
    p_dir = _resolve_plan_dir(plan_dir)
    warnings: list[str] = []
    errors: list[str] = []
    messages: list[str] = []

    if not p_dir.exists():
        return {
            "items": [],
            "count": 0,
            "pagination": {"offset": offset, "limit": limit or 0, "total": 0, "has_more": False},
            "messages": messages,
            "warnings": warnings,
            "errors": [f"Plan directory does not exist: {plan_dir}"],
        }

    # Collect all plan candidates (yaml/md files and plan directories).
    candidates: list[Path] = sorted(c for c in p_dir.iterdir() if c.suffix in {".yaml", ".md"} or c.is_dir())

    # Load each candidate into a summary dict, skipping unreadable files.
    all_items: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            read_result = load_plan(candidate)
            plan = read_result.plan
            plan_dict = plan.model_dump(mode="json", by_alias=True, exclude_none=True)
            summary: dict[str, Any] = {
                "feature": plan.feature,
                "goal": plan.goal,
                "description": plan.description,
                "task_count": len(plan.tasks),
                "path": str(plan.source_path or candidate),
            }
            if search is None or _plan_matches_search(plan_dict, search):
                all_items.append(summary)
        except (FileNotFoundError, FormatDetectionError, ValueError, TypeError) as exc:
            warnings.append(f"Skipped {candidate.name}: {exc}")

    return _paginate_results(
        all_items, offset=offset, limit=limit, messages=messages, warnings=warnings, errors=errors, tool_name="sam_list"
    )


def _try_register_task_plan_artifact(issue_number: int, plan_path: Path) -> None:
    """Register the newly created plan file as a task-plan artifact.

    Best-effort: logs a warning on any failure but never raises.  Called after
    ``sam_create`` writes the plan file when the plan has an associated GitHub
    issue number.

    Args:
        issue_number: GitHub issue number to register the artifact against.
        plan_path: Absolute or repo-relative path to the created plan file.
    """
    try:
        repo = _backlog_models.DEFAULT_REPO
        if not repo:
            _log.warning("sam_create: skipping artifact registration — DEFAULT_REPO not set")
            return
        provider = GitHubArtifactProvider(
            repo=repo,
            root_worktree=_backlog_models._REPO_ROOT,  # noqa: SLF001
        )
        entry = ArtifactEntry(
            artifact_type=ArtifactType.TASK_PLAN, path=str(plan_path), status=ArtifactStatus.CURRENT, agent="sam_create"
        )
        manifest = provider.get_manifest(issue_number)
        updated_manifest = _artifact_registry.register(manifest, entry)
        provider.set_manifest(issue_number, updated_manifest)
        _log.info("sam_create: registered task-plan artifact %s for issue #%d", plan_path, issue_number)

        try:
            content = plan_path.read_text(encoding="utf-8")
            provider.store_artifact_content(
                issue_number, artifact_type=ArtifactType.TASK_PLAN.value, path=str(plan_path), content=content
            )
            _log.info("sam_create: uploaded task-plan content to GitHub issue #%d", issue_number)
        except (BacklogError, OSError) as upload_exc:
            _log.warning(
                "sam_create: artifact content upload failed for issue #%d (path=%s): %s",
                issue_number,
                plan_path,
                upload_exc,
                exc_info=True,
            )
    except (BacklogError, ValueError, OSError) as exc:
        _log.warning(
            "sam_create: artifact registration failed for issue #%d (path=%s): %s",
            issue_number,
            plan_path,
            exc,
            exc_info=True,
        )


@mcp.tool
def sam_create(
    slug: Annotated[str, Field(description="Short identifier for the plan (e.g., 'auth-system')")],
    goal: Annotated[str, Field(description="Human-readable goal statement for the plan")],
    tasks_yaml: Annotated[str, Field(description="YAML string with a 'tasks' key containing a list of task dicts")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    context: Annotated[str | None, Field(description="Optional plan-level context (markdown prose)")] = None,
    issue: Annotated[int | None, Field(description="Optional GitHub issue number to associate with the plan")] = None,
) -> dict:
    """Create a new plan from YAML task definitions.

    Parses ``tasks_yaml`` (a YAML string containing a ``tasks:`` list), validates
    each task dict against the ``Task`` Pydantic model, assigns the next available
    plan number, and writes the plan file to ``{plan_dir}/P{NNN}-{slug}.yaml``.

    Mirrors ``sam create`` CLI behaviour. All write operations are atomic.

    Args:
        slug: Short identifier for the plan.
        goal: Human-readable goal statement.
        tasks_yaml: YAML string whose top-level key is ``tasks`` — a list of task
                    dicts (required fields per ``Task`` model: ``task``, ``title``,
                    ``status``, ``agent``, ``dependencies``, ``priority``,
                    ``complexity``).
        plan_dir: Directory in which to create the plan file.
        context: Optional plan-level context string.
        issue: Optional GitHub issue number.

    Returns:
        ``{"path": str, "plan_number": int, "task_count": int}`` on success, or
        ``{"error": str}`` on failure.
    """
    try:
        yaml: Any = YAML()
        parsed: dict[str, Any] = yaml.load(tasks_yaml)
        if not isinstance(parsed, dict) or "tasks" not in parsed:
            return {"error": "tasks_yaml must be a YAML string with a top-level 'tasks' key"}
        task_list: list[dict[str, Any]] = parsed["tasks"]
        plan = create_plan(
            slug=slug, goal=goal, tasks=task_list, plan_dir=_resolve_plan_dir(plan_dir), context=context, issue=issue
        )
        # Derive plan_number from source_path stem (e.g. "P003-auth-system" -> 3).
        plan_number: int | None = None
        if plan.source_path is not None:
            stem = plan.source_path.stem
            if stem.startswith("P") and "-" in stem:
                with contextlib.suppress(ValueError):
                    plan_number = int(stem.split("-", 1)[0][1:])
        result = {"path": str(plan.source_path), "plan_number": plan_number, "task_count": len(plan.tasks)}
    except (YAMLError, ValueError, OSError) as exc:
        return {"error": str(exc)}
    else:
        # Auto-register the new plan file as a task-plan artifact when the plan
        # is linked to a GitHub issue.  Best-effort: failure does not block creation.
        if issue is not None and plan.source_path is not None:
            _try_register_task_plan_artifact(issue, plan.source_path)
        return result


@mcp.tool
def sam_update(
    address: Annotated[str, Field(description="Plan address (e.g., 'P1') or task address (e.g., 'P1/T2')")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    set_fields_json: Annotated[
        str | None, Field(description="JSON object of field=value pairs to set on the plan or task")
    ] = None,
    context: Annotated[str | None, Field(description="Set the plan-level context field")] = None,
    append_section: Annotated[
        str | None, Field(description="Name of the markdown section to append to the task body")
    ] = None,
    section_content: Annotated[str | None, Field(description="Body content for the appended section")] = None,
) -> dict:
    """Update plan or task fields, or append a markdown section to a task body.

    Supports three non-exclusive operations that can be combined in one call:

    1. ``set_fields_json`` — a JSON object of ``{field: value}`` pairs to update.
    2. ``context`` — shorthand for setting the plan-level ``context`` field.
    3. ``append_section`` + ``section_content`` — append a named markdown section
       to a task's body (task address required for this operation).

    Mirrors ``sam update`` CLI behaviour.

    Args:
        address: Plan or task address. Task address required for
                 ``append_section`` and task-level ``set_fields_json``.
        plan_dir: Directory containing plan files.
        set_fields_json: JSON string ``{"field": "value", ...}`` to set.
        context: If provided, sets the plan-level ``context`` field.
        append_section: Section heading to append to the task body.
        section_content: Body text for the appended section.

    Returns:
        ``{"updated": true, "address": str}`` on success, or ``{"error": str}``
        on failure.
    """
    try:
        # Split address into plan and optional task components.
        if "/" in address:
            plan_part, task_id = address.split("/", 1)
        else:
            plan_part = address
            task_id = None

        plan_path = resolve_plan_address(plan_part, _resolve_plan_dir(plan_dir))

        set_fields: dict[str, str | int | list[str]] | None = None
        if set_fields_json is not None:
            raw_fields: Any = json.loads(set_fields_json)
            if not isinstance(raw_fields, dict):
                return {"error": "set_fields_json must be a JSON object"}
            set_fields = {str(k): str(v) for k, v in raw_fields.items()}

        update_plan_fields(
            plan_path,
            task_id=task_id,
            set_fields=set_fields,
            context=context,
            append_section_name=append_section,
            section_content=section_content,
        )
    except (FileNotFoundError, AddressingError, KeyError, ValueError, OSError) as exc:
        return {"error": str(exc)}
    else:
        return {"updated": True, "address": address}


@mcp.tool
def sam_claim(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str, Field(description="Task ID to claim (e.g., 'T3')")],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Claim a task by transitioning it from ``not-started`` to ``in-progress``.

    Guards against double-claiming: returns an error dict (not an exception) if
    the task is already in-progress or in a terminal state. Mirrors ``sam claim``
    CLI behaviour.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID to claim (e.g., ``T3``).
        plan_dir: Path to the directory containing plan files.

    Returns:
        ``{"claimed": true, "task_id": str, "started": str}`` on success, or
        ``{"claimed": false, "error": str}`` if the task cannot be claimed.
    """
    try:
        plan_path = resolve_plan_address(plan, _resolve_plan_dir(plan_dir))
        updated_task = claim_task(plan_path, task)
    except (ValueError, KeyError) as exc:
        return {"claimed": False, "error": str(exc)}
    except (FileNotFoundError, AddressingError, FormatDetectionError, OSError) as exc:
        return {"error": str(exc)}
    else:
        return {"claimed": True, "task_id": updated_task.id, "started": updated_task.started}
