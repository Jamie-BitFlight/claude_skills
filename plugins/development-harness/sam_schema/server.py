"""FastMCP server for SAM task/plan operations.

Exposes the same operations as the Typer CLI as MCP tools for use by
Claude Code agents and other MCP clients.

Tools:
    sam_plan        — Consolidated plan-level operations (read, create, list, status, ready, update)
    sam_task        — Consolidated task-level operations (read, claim, state, update)
    sam_active_task — Session-scoped active task context management (get, set, update, clear)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

import backlog_core.models as _backlog_models
import tiktoken
from backlog_core.artifact_provider import create_artifact_provider
from backlog_core.artifact_registry import ArtifactRegistry as _ArtifactRegistry
from backlog_core.models import ArtifactEntry, ArtifactStatus, ArtifactType, BacklogError
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from sam_schema.core.action_models import (
    ActiveTaskActionConfig,
    AppendTaskConfig,
    CreatePlanConfig,
    ListPlansConfig,
    PlanActionConfig,
    ReadyPlanConfig,
    SetActiveTaskConfig,
    StateTaskConfig,
    TaskActionConfig,
    UpdateActiveTaskConfig,
    UpdatePlanConfig,
    UpdateTaskConfig,
)
from sam_schema.core.context_config import ContextConfig, create_context_backend, get_context_config, set_context_config
from sam_schema.core.exceptions import PlanNotFoundError, SamError, TaskNotFoundError
from sam_schema.core.models import Plan, PlanState, Task, TaskAssignment
from sam_schema.core.task_config import TaskConfig, create_task_backend, get_task_config, set_task_config

if TYPE_CHECKING:
    from sam_schema.core.task_backend import TaskBackend

_log = logging.getLogger(__name__)
_artifact_registry = _ArtifactRegistry()

_PLAN_DIR_SENTINEL = "plan"

# Sentinel session key used when session_id is omitted from sam_active_task calls.
# Single-agent scenarios do not require explicit session isolation.
_DEFAULT_SESSION_ID = "_default"

# Returned by _sam_plan_status and _sam_plan_ready when the plan is in drafting state.
# Defined once here to ensure both handlers return an identical shape.
_DRAFTING_MARKER_RESPONSE: dict[str, object] = {"drafting": True, "state": PlanState.DRAFTING}

# Stem parsing thresholds used in _build_task_assignment.
_STEM_MIN_PARTS_FOR_NUMBER: int = 2
_STEM_MIN_PARTS_FOR_SLUG: int = 3

# Initialize the default backend at module import time.
# Tests may call set_task_config() before importing this module to inject a custom backend.
try:
    get_task_config()
except RuntimeError:
    set_task_config(TaskConfig(backend=create_task_backend()))

# Initialize the context backend at module import time.
# Tests may call set_context_config() before importing this module to inject a custom backend.
try:
    get_context_config()
except RuntimeError:
    set_context_config(ContextConfig(backend=create_context_backend()))


def _get_backend(plan_dir_str: str) -> TaskBackend:
    """Return the configured backend, or a LocalYamlTaskProvider for an explicit plan_dir.

    When *plan_dir_str* is the default sentinel (``"plan"``), returns the
    module-level configured backend from :func:`get_task_config`.  When
    *plan_dir_str* is a concrete filesystem path, creates a
    :class:`~sam_schema.core.backends.local_yaml.LocalYamlTaskProvider` for
    that path to preserve backward compatibility with callers that supply an
    explicit directory.

    Args:
        plan_dir_str: The ``plan_dir`` parameter from the MCP tool call.

    Returns:
        :class:`~sam_schema.core.task_backend.TaskBackend` instance to use for
        this tool call.
    """
    if plan_dir_str == _PLAN_DIR_SENTINEL:
        return get_task_config().backend
    # Non-default plan_dir: callers passing a concrete path expect local filesystem
    # behavior, so create a LocalYamlTaskProvider for that explicit path.
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider  # noqa: PLC0415

    return LocalYamlTaskProvider(Path(plan_dir_str))


# Token budget for auto-pagination: 4400 tokens (cl100k_base encoding).
_TOKEN_BUDGET: int = 4_400
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")

mcp: FastMCP = FastMCP(
    "sam",
    instructions=(
        "SAM (Structured Agent-Managed) task plan server. "
        "Use sam_task to read, claim, update state, or update fields of a specific task — "
        "set config.action to: read | claim | state | update. "
        "Use sam_plan to read a plan, create a plan, list all plans, get progress status, "
        "or list ready-to-dispatch tasks — "
        "set config.action to: read | create | list | status | ready | update | append_task | finalize. "
        "Use sam_active_task to park and retrieve the task currently being worked on "
        "within an agent session — "
        "set config.action to: get | set | update | clear."
    ),
)


def run_server() -> None:
    """Entry point for ``sam-mcp`` console script."""
    mcp.run()


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
        provider = create_artifact_provider(
            repo=repo,
            root_worktree=_backlog_models._REPO_ROOT,  # noqa: SLF001
        )
        entry = ArtifactEntry(
            artifact_type=ArtifactType.TASK_PLAN,
            artifact_id=str(plan_path),
            status=ArtifactStatus.CURRENT,
            agent="sam_create",
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


def _validated_task_patch(backend: TaskBackend, plan_id: str, task_id: str, raw_fields: dict[str, Any]) -> Task:
    """Validate raw JSON patch fields through the Pydantic Task model.

    Reads the current task, merges *raw_fields* into its data, then passes the
    merged dict through ``Task.model_validate`` so field validators run (e.g.
    ``validate_task_id_list`` normalises ``dependencies``).  Returns the
    fully-validated Task model for the caller to write via ``backend.update_task``.

    Args:
        backend: Active TaskBackend instance.
        plan_id: Backend-assigned plan identifier.
        task_id: Task identifier within the plan.
        raw_fields: JSON-decoded patch dict from ``set_fields_json``.

    Returns:
        Fully-validated Task model with the patched fields applied.

    Raises:
        PlanNotFoundError: When plan_id cannot be resolved by the backend.
        TaskNotFoundError: When task_id does not exist within the plan.
        pydantic.ValidationError: When a field value fails Task model validation.
    """
    task_data = backend.read_task(plan_id, task_id)
    current = Task.model_validate(task_data)
    return Task.model_validate({**current.model_dump(), **raw_fields})


# Actions that require the ``plan`` parameter to be supplied.
_SAM_PLAN_REQUIRED_ACTIONS: frozenset[str] = frozenset({"read", "status", "ready", "update", "append_task", "finalize"})


def _sam_plan_read(plan: str, plan_dir: str) -> dict:
    """Return Plan fields for the given plan address."""
    backend = _get_backend(plan_dir)
    plan_data = backend.read_plan(plan)
    plan_dict = {k: v for k, v in plan_data.items() if k != "plan_id"}
    plan_model = Plan.model_validate(plan_dict)
    return plan_model.model_dump(mode="json", by_alias=True, exclude_none=True)


def _sam_plan_create(config: CreatePlanConfig, plan_dir: str) -> dict:
    """Create a new plan from a typed list of task definitions.

    Returns:
        Dict with ``plan_id``, ``plan_ref``, and ``task_count`` keys.
        ``plan_ref`` is computed in the server response as ``#{issue},{plan_id}``
        when an issue number is present, or just ``plan_id`` otherwise.
        It is not stored in the Plan model.
    """
    backend = _get_backend(plan_dir)
    plan_data = backend.create_plan(
        slug=config.slug, goal=config.goal, tasks=config.tasks, context=config.context, issue=config.issue
    )
    plan_id_str = plan_data["plan_id"]
    plan_ref: str | None = (
        (f"#{config.issue},{plan_id_str}" if config.issue is not None else plan_id_str) if plan_id_str else None
    )
    result: dict[str, Any] = {"plan_id": plan_id_str, "task_count": len(plan_data["tasks"]), "plan_ref": plan_ref}
    if config.issue is not None and plan_data["source_path"]:
        _try_register_task_plan_artifact(config.issue, Path(plan_data["source_path"]))
    return result


def _sam_plan_list(config: ListPlansConfig, plan_dir: str) -> dict:
    """List all plans with optional search and auto-pagination.

    Returns:
        Paginated dict with ``items``, ``count``, ``pagination``, ``messages``,
        ``warnings``, and ``errors`` keys. Each item contains ``feature``,
        ``goal``, ``description``, ``task_count``, ``issue``, and ``plan_ref``.
    """
    backend = _get_backend(plan_dir)
    summaries = backend.list_plans(search=config.search)
    all_items: list[dict[str, Any]] = [
        {
            "feature": s["feature"],
            "goal": s["goal"],
            "description": s["description"],
            "task_count": s["task_count"],
            "issue": s.get("issue"),
            "plan_ref": (f"#{s['issue']},{s['plan_id']}" if s.get("issue") else s.get("plan_id")),
        }
        for s in summaries
    ]
    return _paginate_results(
        all_items, offset=config.offset, limit=config.limit, messages=[], warnings=[], errors=[], tool_name="sam_plan"
    )


def _sam_plan_status(plan: str, plan_dir: str) -> dict:
    """Return plan-level progress summary including autonomy mode.

    Calls ``get_plan_status`` for computed metrics and ``read_plan`` to
    surface the ``autonomy`` field, which lives on the Plan model and is
    not part of ``PlanStatus``.  Follows the same pattern as
    ``_sam_plan_ready``.
    """
    backend = _get_backend(plan_dir)
    status = backend.get_plan_status(plan)
    if status.get("state") == PlanState.DRAFTING:
        return dict(_DRAFTING_MARKER_RESPONSE)
    plan_data = backend.read_plan(plan)
    result = dict(status)
    result["autonomy"] = plan_data.get("autonomy", "full_auto")
    return result


def _sam_plan_ready(plan: str, config: ReadyPlanConfig, plan_dir: str) -> dict:
    """List tasks ready for dispatch.

    Calls ``get_plan_status`` first for the drafting check (single backend call),
    then ``get_ready_tasks`` only when the plan is not in drafting state.

    Returns:
        Dict with ``ready_tasks``, ``count``, ``feature``, and ``issue`` keys.
    """
    backend = _get_backend(plan_dir)
    status = backend.get_plan_status(plan)
    if status.get("state") == PlanState.DRAFTING:
        return dict(_DRAFTING_MARKER_RESPONSE)
    tasks_data = backend.get_ready_tasks(plan)
    plan_data = backend.read_plan(plan)  # needed for plan_data["issue"]
    if config.full:
        ready_tasks: list[dict[str, Any]] = [Task.model_validate(t).model_dump(mode="json") for t in tasks_data]
    else:
        ready_tasks = [
            {
                "id": t["id"],
                "task": t["title"],
                "agent": t["agent"],
                "skills": t["skills"] or [],
                "dependencies": t["dependencies"] or [],
                "status": t["status"],
                "priority": int(t["priority"]),
            }
            for t in tasks_data
        ]
    return {
        "ready_tasks": ready_tasks,
        "count": len(tasks_data),
        "feature": cast("str", status["feature"]),
        "issue": plan_data["issue"],
    }


def _sam_plan_update(plan: str, config: UpdatePlanConfig, plan_dir: str) -> dict:
    """Update plan-level context and/or fields.

    Returns:
        Dict with ``updated`` (bool) and ``address`` (plan identifier) keys.
    """
    backend = _get_backend(plan_dir)
    plan_fields: dict[str, str | int | list[str]] | None = None
    if config.set_fields_json is not None:
        raw_fields: Any = json.loads(config.set_fields_json)
        if not isinstance(raw_fields, dict):
            raise ValueError("set_fields_json must be a JSON object")
        plan_fields = cast("dict[str, str | int | list[str]]", raw_fields)
    backend.update_plan_fields(plan, context=config.context, set_fields=plan_fields)
    return {"updated": True, "address": plan}


def _sam_plan_append_task(plan: str, config: AppendTaskConfig, plan_dir: str) -> dict:
    """Append a single task to an existing plan.

    Converts ``config.task`` (a validated :class:`TaskDefinition` model) to a
    snake_case dict via ``model_dump`` and delegates to ``backend.append_task``.
    Pydantic handles alias normalisation (kebab-case → snake_case) at the MCP
    boundary; no YAML parsing or re-normalisation is required downstream.

    See AppendTaskConfig for the single-writer contract and #1770 for the ADR.

    Args:
        plan: Plan address (e.g., ``P1`` or slug).
        config: AppendTaskConfig carrying the validated TaskDefinition.
        plan_dir: Plan directory path passed through to ``_get_backend``.

    Returns:
        Result dict from ``backend.append_task`` — shape: ``{"appended": True, "task_id": ...}``.

    Raises:
        PlanNotFoundError: When the plan address cannot be resolved.
        TaskValidationError: When the task definition fails model validation.
    """
    backend = _get_backend(plan_dir)
    return backend.append_task(plan, config.task)


def _sam_plan_finalize(plan: str, plan_dir: str) -> dict:
    """Transition a plan from drafting state to ready state.

    See FinalizePlanConfig and #1770 for the ADR.

    Returns:
        Result dict from ``backend.finalize_plan`` — shape: ``{"finalized": True, "state": "ready"}``.
    """
    backend = _get_backend(plan_dir)
    return backend.finalize_plan(plan)


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Plan Operations", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
)
def sam_plan(
    config: Annotated[
        PlanActionConfig,
        Field(
            description="Action config. Set 'action' to: read | create | list | status | ready | update | append_task | finalize"
        ),
    ],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
    plan: Annotated[
        str | None,
        Field(
            description=(
                "Plan address (e.g., 'P1' or slug). "
                "Required for: read, status, ready, update, append_task, finalize. "
                "Not used for: list, create."
            )
        ),
    ] = None,
) -> dict:
    """Consolidated plan-level operations for SAM.

    Delegates to the appropriate plan operation based on ``config.action``.

    Actions requiring the ``plan`` parameter:

    - ``read``: Return Plan fields for the given plan address.
    - ``status``: Return plan-level progress summary (task counts, completion %).
    - ``ready``: List tasks ready for dispatch (not-started, all deps resolved).
    - ``update``: Set plan-level context and/or patch plan fields.
    - ``append_task``: Append a single task to an existing plan (incremental build; see #1770).
    - ``finalize``: Transition a plan from drafting state to ready state (see #1770).

    Actions that do not use ``plan``:

    - ``create``: Create a new plan from a typed list of task definitions.
    - ``list``: List all plans with optional search and auto-pagination.

    Args:
        config: Discriminated union config. The ``action`` field selects the operation.
        plan_dir: Path to the directory containing plan files.
        plan: Plan address component. Required for read, status, ready, update, append_task, finalize actions.

    Returns:
        Response dict whose shape depends on the action (see individual action docs).

    Raises:
        ToolError: When ``plan`` is None for an action that requires it.
    """
    if config.action in _SAM_PLAN_REQUIRED_ACTIONS and plan is None:
        raise ToolError(
            f"sam_plan: action='{config.action}' requires the 'plan' parameter "
            f"(e.g., plan='P1'). Actions that do not need 'plan': list, create."
        )

    match config.action:
        case "read":
            return _sam_plan_read(cast("str", plan), plan_dir)
        case "create":
            return _sam_plan_create(cast("CreatePlanConfig", config), plan_dir)
        case "list":
            return _sam_plan_list(cast("ListPlansConfig", config), plan_dir)
        case "status":
            return _sam_plan_status(cast("str", plan), plan_dir)
        case "ready":
            return _sam_plan_ready(cast("str", plan), cast("ReadyPlanConfig", config), plan_dir)
        case "update":
            return _sam_plan_update(cast("str", plan), cast("UpdatePlanConfig", config), plan_dir)
        case "append_task":
            return _sam_plan_append_task(cast("str", plan), cast("AppendTaskConfig", config), plan_dir)
        case "finalize":
            return _sam_plan_finalize(cast("str", plan), plan_dir)
        case _:  # pragma: no cover
            raise ValueError(f"sam_plan: unhandled action '{config.action}'")


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Task Operations", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
)
def sam_task(
    plan: Annotated[str, Field(description="Plan address (e.g., 'P1' or slug)")],
    task: Annotated[str, Field(description="Task ID within the plan (e.g., 'T3')")],
    config: Annotated[
        TaskActionConfig, Field(description="Action config. Set 'action' to: read | claim | state | update")
    ],
    plan_dir: Annotated[str, Field(description="Plan directory path")] = "plan",
) -> dict:
    """Read, claim, update state, or update fields for a specific task.

    # TRADE-OFF: readonly annotation loss
    # sam_read (replaced by action="read") was annotated readonly=True in FastMCP,
    # meaning it did not require a confirmation prompt from Claude Code.
    # sam_task cannot be readonly because it includes write actions (claim, state,
    # update). Consequence: Claude Code will show a confirmation prompt for read
    # operations that previously did not require one. This is a known, accepted
    # trade-off — a clean 3-tool interface outweighs the read UX regression.
    # If read-without-prompt becomes required, extract a separate readonly
    # sam_task_read tool in a future iteration.

    Args:
        plan: Plan address component (numeric index or slug).
        task: Task ID component (e.g., ``T3``).
        config: Discriminated union selecting the action and its parameters.
        plan_dir: Path to the directory containing plan files.

    Returns:
        Action-specific dict. See individual action descriptions.
    """
    backend = _get_backend(plan_dir)
    plan_id = plan

    match config.action:
        case "read":
            plan_data = backend.read_plan(plan_id)
            task_data = backend.read_task(plan_id, task)
            task_model = Task.model_validate(task_data)
            assignment = TaskAssignment(
                plan_number=plan_data.get("plan_id", plan_id),
                plan_slug=plan_data.get("feature") or None,
                plan_goal=plan_data.get("goal") or None,
                plan_context=plan_data.get("context") or None,
                plan_acceptance_criteria=plan_data.get("acceptance_criteria")
                or plan_data.get("acceptance-criteria")
                or None,
                task=task_model,
            )
            return assignment.model_dump(mode="json", by_alias=True, exclude_none=True)

        case "claim":
            claimed = backend.claim_task(plan_id, task)
            if not claimed:
                try:
                    task_data = backend.read_task(plan_id, task)
                    current_status = task_data["status"]
                except (PlanNotFoundError, TaskNotFoundError, SamError):
                    return {
                        "claimed": False,
                        "error": f"Cannot claim task '{task}': task is not available for claiming.",
                    }
                else:
                    return {
                        "claimed": False,
                        "error": f"Cannot claim task '{task}': expected status 'not-started' but found '{current_status}'.",
                    }
            return {"claimed": True, "task_id": task, "started": datetime.now(UTC).isoformat()}

        case "state":
            state_config = cast("StateTaskConfig", config)
            backend.update_task_status(plan_id, task, state_config.status)
            return {"id": task, "status": state_config.status}

        case "update":
            update_config = cast("UpdateTaskConfig", config)
            if update_config.set_fields_json is not None:
                raw_fields: Any = json.loads(update_config.set_fields_json)
                if not isinstance(raw_fields, dict):
                    raise ToolError("set_fields_json must be a JSON object")
                validated_task = _validated_task_patch(backend, plan_id, task, raw_fields)
                backend.update_task(plan_id, validated_task)
            if update_config.append_section is not None:
                backend.append_task_section(
                    plan_id, task, update_config.append_section, update_config.section_content or ""
                )
            return {"updated": True, "address": f"{plan}/{task}"}

        case _:  # pragma: no cover
            raise ValueError(f"sam_task: unhandled action '{config.action}'")


@mcp.tool(
    annotations=ToolAnnotations(
        title="SAM Active Task Context",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def sam_active_task(
    config: Annotated[
        ActiveTaskActionConfig, Field(description="Action config. Set 'action' to: get | set | update | clear")
    ],
    session_id: Annotated[
        str | None,
        Field(
            description=(
                "Session identifier for scoping the active task context. "
                "When None, uses the '_default' sentinel for single-agent scenarios."
            )
        ),
    ] = None,
) -> dict:
    """Session-scoped active task context management.

    Parks a task address in session-scoped storage so subsequent operations
    can omit the plan/task parameters. Useful in single-agent workflows where
    repeatedly passing the same address is noise.

    Actions:

    - ``get``: Return the active task context, or ``{"active_task": null}`` if not set.
    - ``set``: Store a plan/task address as the active task for this session.
    - ``update``: Update fields on the active task without repeating its address.
    - ``clear``: Remove the active task context for this session.

    Args:
        config: Discriminated union selecting the action and its parameters.
        session_id: Claude Code session identifier. When ``None``, uses the
            ``"_default"`` sentinel (suitable for single-agent scenarios that
            do not need explicit session isolation).

    Returns:
        Action-specific dict. See individual action descriptions.

    Raises:
        ToolError: When ``action="update"`` and no active task has been set.
    """
    resolved_session = session_id if session_id is not None else _DEFAULT_SESSION_ID
    ctx_backend = get_context_config().backend

    match config.action:
        case "get":
            active = ctx_backend.get_active_task(resolved_session)
            if active is None:
                return {"active_task": None}
            return {"active_task": active.model_dump(mode="json")}

        case "set":
            set_config = cast("SetActiveTaskConfig", config)
            active = ctx_backend.set_active_task(
                resolved_session, set_config.plan, set_config.task, set_config.plan_dir
            )
            return {"active_task": active.model_dump(mode="json")}

        case "update":
            active = ctx_backend.get_active_task(resolved_session)
            if active is None:
                raise ToolError(
                    "sam_active_task: no active task set for this session. "
                    "Call sam_active_task(action='set', plan=..., task=...) first."
                )
            update_config = cast("UpdateActiveTaskConfig", config)
            # ActiveTaskContext stores task_file_path and task_id.
            # Derive plan_id and plan_dir from the path rather than storing them separately.
            active_plan_dir = str(Path(active.task_file_path).parent)
            active_plan_id = Path(active.task_file_path).stem.split("-")[0]
            active_task_id = active.task_id
            task_backend = _get_backend(active_plan_dir)
            if update_config.set_fields_json is not None:
                raw_fields: Any = json.loads(update_config.set_fields_json)
                if not isinstance(raw_fields, dict):
                    raise ToolError("set_fields_json must be a JSON object")
                validated_task = _validated_task_patch(task_backend, active_plan_id, active_task_id, raw_fields)
                task_backend.update_task(active_plan_id, validated_task)
            if update_config.append_section is not None:
                task_backend.append_task_section(
                    active_plan_id, active_task_id, update_config.append_section, update_config.section_content or ""
                )
            return {"updated": True, "address": f"{active_plan_id}/{active_task_id}"}

        case "clear":
            removed = ctx_backend.clear_active_task(resolved_session)
            return {"cleared": removed}

        case _:  # pragma: no cover
            raise ValueError(f"sam_active_task: unhandled action '{config.action}'")
