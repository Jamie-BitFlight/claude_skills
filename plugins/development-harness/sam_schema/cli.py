"""Typer CLI for SAM task/plan operations.

Provides the ``sam`` command with subcommands for creating, reading, updating,
claiming, and validating plans and tasks.

Usage::

    sam create auth-system --goal "Implement auth" --stdin
    sam read P1/T3
    sam update P1 --context "New context"
    sam update P1/T3 --append-section "Notes" --section-content "text"
    sam claim P1/T3
    sam validate P1
    sam state P1/T3 complete
    sam ready P1
    sam status P1
    sam status --all
    sam migrate P1
    sam migrate --all
    sam migrate --all --dry-run
    sam migrate --all --skip-sync
    sam append-task P1 --task-json '{"task":"T3","title":"New","status":"not-started","agent":"worker","dependencies":[],"priority":3,"complexity":"medium"}'
    sam append-task P1 --stdin
    sam finalize P1
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, NoReturn

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import dh_paths
import typer
from dh_core import operations
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML, YAMLError

from sam_schema import cli_active_task, cli_output
from sam_schema.core.addressing import AddressingError, parse_address, resolve_plan_address
from sam_schema.core.backends.local_yaml import plan_id_from_path
from sam_schema.core.exceptions import PlanNotFoundError, TaskNotFoundError
from sam_schema.core.models import CreatePlanError, TaskStatus
from sam_schema.core.task_config import get_backend
from sam_schema.readers.detect import FormatDetectionError
from sam_schema.writers.yaml_writer import write_plan

_PLAN_LOAD_ERRORS: tuple[type[Exception], ...] = (FileNotFoundError, FormatDetectionError, ValueError, TypeError)

_SYNC_ERRORS: tuple[type[Exception], ...]
try:
    from backlog_core.models import BacklogError, Output
    from backlog_core.operations import sync_items as _sync_backlog

    _BACKLOG_CORE_AVAILABLE = True
    _SYNC_ERRORS = (BacklogError, OSError, ValueError)
except ImportError:
    _BACKLOG_CORE_AVAILABLE = False
    _SYNC_ERRORS = (OSError, ValueError)

app = typer.Typer(name="sam", help="SAM task/plan file interface.", no_args_is_help=True)

_OUTPUT_FORMATS = ("json", "yaml", "rich")
_YAML_FRONTMATTER_PARTS = 3


def _parse_filter_pairs(filters: list[str] | None) -> dict[str, str] | None:
    """Parse repeated ``--filter key=value`` options into a dict.

    Each entry must be ``key=value``; the first ``=`` splits the pair. An empty
    or all-None list returns ``None`` so callers can pass it straight through to
    operations that treat ``None`` as "no filter".

    Args:
        filters: List of ``key=value`` strings from a repeatable Typer option.

    Returns:
        Dict of key→value pairs, or ``None`` when no filters were supplied.

    Raises:
        typer.BadParameter: When an entry lacks ``=`` or has an empty key.
    """
    if not filters:
        return None
    result: dict[str, str] = {}
    for entry in filters:
        if "=" not in entry:
            raise typer.BadParameter(f"--filter expects 'key=value', got: {entry!r}")
        key, _, value = entry.partition("=")
        if not key:
            raise typer.BadParameter(f"--filter key must be non-empty: {entry!r}")
        result[key] = value
    return result or None


def _coerce_plan_dir(plan_dir: Path | None) -> Path:
    """Return the resolved plan directory.

    When ``plan_dir`` is ``None`` (the Typer default for all commands), returns
    the DH-paths canonical location via :func:`dh_paths.plan_dir`.  When an
    explicit path is supplied on the command line, that path is returned as-is.

    Args:
        plan_dir: Path supplied by the caller, or ``None`` when the option was
                  omitted.

    Returns:
        Resolved :class:`~pathlib.Path` to the plan directory.
    """
    if plan_dir is None:
        return dh_paths.plan_dir()
    return plan_dir


def _coerce_backlog_dir(backlog_dir: Path | None) -> Path:
    """Return the resolved backlog directory.

    When ``backlog_dir`` is ``None`` (the Typer default for the migrate command),
    returns the DH-paths canonical location via :func:`dh_paths.backlog_dir`.
    When an explicit path is supplied on the command line, that path is returned
    as-is.

    Args:
        backlog_dir: Path supplied by the caller, or ``None`` when the option was
                     omitted.

    Returns:
        Resolved :class:`~pathlib.Path` to the backlog directory.
    """
    if backlog_dir is None:
        return dh_paths.backlog_dir()
    return backlog_dir


def _err(msg: str, exit_code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit.

    Thin alias for :func:`sam_schema.cli_output.err`, kept so the many
    existing call sites in this module stay unchanged.

    Args:
        msg: Human-readable error message.
        exit_code: Process exit code (1 for user errors, 2 for internal errors).

    Raises:
        typer.Exit: Always — terminates the command with *exit_code*.
    """
    cli_output.err(msg, exit_code)


def _resolve_plan(address_part: str, plan_dir: Path) -> Path:
    """Resolve the plan portion of an address to a filesystem path.

    Args:
        address_part: Plan address component (e.g., ``"1"``, ``"auth-system"``).
        plan_dir: Directory to search for plan files.

    Returns:
        Resolved path to the plan file or directory.

    Raises:
        SystemExit(1): If the address cannot be resolved or the directory is missing.
    """
    try:
        return resolve_plan_address(address_part, plan_dir)
    except FileNotFoundError as exc:
        _err(str(exc))
    except AddressingError as exc:
        _err(str(exc))


def _get_plan_status_for_address(plan_address: str, plan_dir: Path) -> dict[str, object]:
    """Resolve ``plan_address`` to a plan and return its status via the operations layer.

    Accepts either a direct filesystem path (e.g. ``plan/tasks-696-slug.md``)
    or a structured plan address (e.g. ``P696``, ``auth-system``).  Direct paths
    are detected by checking whether the argument exists on disk before falling
    back to address parsing.

    Delegates to ``dh_core.operations.get_plan_status`` via a
    ``LocalYamlTaskProvider`` backend so the CLI shares the same code path
    as the MCP server, including the drafting-state check.

    Args:
        plan_address: Plan address string or filesystem path.
        plan_dir: Directory to search when resolving structured addresses.

    Returns:
        Status dict from the operations layer. When the plan is in drafting
        state, returns ``{"drafting": True, "state": "drafting"}``.

    Raises:
        SystemExit(1): If the path or address cannot be resolved.
        SystemExit(2): If the format cannot be detected.
    """
    # If the argument is an existing file path, load the plan directly.
    if Path(plan_address).exists():
        file_path = Path(plan_address)
        file_plan_dir = file_path.parent
        plan_ref = plan_id_from_path(file_path)
        backend = get_backend(str(file_plan_dir))
        try:
            status = operations.get_plan_status(backend, plan_ref)
            return status.model_dump(mode="json")
        except ValueError:
            return {"drafting": True, "state": "drafting"}
        except PlanNotFoundError as exc:
            _err(str(exc))
        except FileNotFoundError as exc:
            _err(str(exc))
        except FormatDetectionError as exc:
            _err(str(exc), exit_code=2)

    # Accept structured addresses only (P{N}, slug). The backend resolves
    # the address to whatever storage it uses — never pass filesystem paths.
    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    backend = get_backend(str(plan_dir))
    try:
        status = operations.get_plan_status(backend, plan_ref)
        return status.model_dump(mode="json")
    except ValueError:
        return {"drafting": True, "state": "drafting"}
    except PlanNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)


def _output_json(data: object) -> None:
    """Print ``data`` as compact JSON to stdout.

    Thin alias for :func:`sam_schema.cli_output.output_json`, kept so the many
    existing call sites in this module stay unchanged.

    Args:
        data: A Pydantic model, list of models, or JSON-serializable object.
    """
    cli_output.output_json(data)


def _output_yaml(data: object) -> None:
    """Print ``data`` as YAML to stdout.

    Pydantic models are converted to plain dicts before serialization so the
    YAML dumper can handle them.

    Args:
        data: Any YAML-serializable object, Pydantic model, or list of models.
    """
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    elif isinstance(data, list) and data and all(isinstance(item, BaseModel) for item in data):
        data = [item.model_dump(mode="json") for item in data if isinstance(item, BaseModel)]
    y = YAML()
    y.default_flow_style = False
    buf = io.StringIO()
    y.dump(data, buf)
    typer.echo(buf.getvalue(), nl=False)


def _output_rich_task(task_data: dict[str, object]) -> None:
    """Print task fields as a Rich table.

    Args:
        task_data: Task dict from ``model_dump(mode="json")``.
    """
    console = Console()
    table = Table(title=str(task_data.get("title", "")), show_header=True, header_style="bold cyan")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    for key, value in task_data.items():
        if value is not None and value not in ("", []):
            table.add_row(str(key), str(value))

    console.print(table)


def _output_rich_status(status_data: dict[str, object]) -> None:
    """Print plan status as Rich tables.

    Args:
        status_data: Status dict from the operations layer.
    """
    console = Console()

    feature = str(status_data.get("feature", ""))
    total = status_data.get("total_tasks", 0)
    raw_completion = status_data.get("completion_pct", 0.0)
    completion = float(raw_completion) if isinstance(raw_completion, (int, float)) else 0.0
    has_cycles = status_data.get("has_cycles", False)

    meta = Table(title=f"Plan: {feature}", show_header=False)
    meta.add_column("Field", style="cyan")
    meta.add_column("Value", style="green")
    meta.add_row("Total tasks", str(total))
    meta.add_row("Completion", f"{completion:.1f}%")
    meta.add_row("Has cycles", str(has_cycles))
    console.print(meta)

    raw_by_status = status_data.get("by_status")
    by_status: dict[str, int] = (
        {str(k): int(v) for k, v in raw_by_status.items() if isinstance(v, int)}
        if isinstance(raw_by_status, dict)
        else {}
    )
    if by_status:
        st_table = Table(title="By Status", show_header=True, header_style="bold")
        st_table.add_column("Status", style="cyan")
        st_table.add_column("Count", style="green", justify="right")
        for s, count in by_status.items():
            st_table.add_row(str(s), str(count))
        console.print(st_table)

    raw_ready = status_data.get("ready_tasks")
    ready_list: list[str] = [str(t) for t in raw_ready] if isinstance(raw_ready, list) else []
    if ready_list:
        console.print(f"Ready tasks: {', '.join(ready_list)}")


def _read_plan_only(plan_ref: str, plan_dir: Path, output_format: str) -> None:
    """Read a plan-only address and emit its fields.

    Delegates to dh_core.operations.read_plan via a LocalYamlTaskProvider
    backend so the CLI shares the same code path as the MCP server.

    Args:
        plan_ref: Plan address component (e.g. ``"1"``, ``"auth-system"``).
        plan_dir: Directory to search for plan files.
        output_format: One of ``json``, ``yaml``, ``rich``.
    """
    backend = get_backend(str(plan_dir))
    try:
        data = operations.read_plan(backend, plan_ref)
    except PlanNotFoundError as exc:
        _err(str(exc))
        return

    match output_format:
        case "json":
            _output_json(data)
        case "yaml":
            _output_yaml(data)
        case _:
            _output_json(data.plan.model_dump(mode="json", by_alias=True, exclude_none=True))


def _read_task_assignment(plan_ref: str, plan_dir: Path, task_id: str, output_format: str) -> None:
    """Read a task address and emit a ``TaskAssignment`` response.

    Delegates to ``dh_core.operations.read_task`` via a
    ``LocalYamlTaskProvider`` backend so the CLI shares the same code path
    as the MCP server.

    Args:
        plan_ref: Plan address component (e.g. ``"1"``, ``"auth-system"``).
        plan_dir: Directory to search for plan files.
        task_id: Normalised task ID (e.g. ``"T3"``).
        output_format: One of ``json``, ``yaml``, ``rich``.
    """
    backend = get_backend(str(plan_dir))
    try:
        data = operations.read_task(backend, plan_ref, task_id)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except TaskNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    match output_format:
        case "json":
            _output_json(data)
        case "yaml":
            _output_yaml(data)
        case _:
            task_dict = data.model_dump(mode="json", by_alias=True, exclude_none=True)
            console = Console()
            if task_dict.get("plan_goal"):
                console.print(f"[bold cyan]Plan goal:[/bold cyan] {task_dict['plan_goal']}")
            if task_dict.get("plan_context"):
                console.print(f"[bold cyan]Plan context:[/bold cyan] {task_dict['plan_context']}")
            _output_rich_task(task_dict.get("task", task_dict))


@app.command(name="list")
def list_plans(
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Case-insensitive substring filter")] = None,
    offset: Annotated[int, typer.Option("--offset", help="Zero-based index of first item to return")] = 0,
    limit: Annotated[int | None, typer.Option("--limit", help="Maximum number of items to return")] = None,
    filters: Annotated[
        list[str] | None,
        typer.Option("--filter", help="Filter by key=value pairs (repeatable). Example: --filter feature=auth"),
    ] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json|yaml")] = "json",
) -> None:
    """List all plans in plan_dir with optional search filtering.

    Delegates to ``dh_core.operations.list_plans`` via a
    ``LocalYamlTaskProvider`` backend so the CLI shares the same code
    path as the MCP server.

    Output (JSON)::

        {
            "items": [{"feature": "auth-system", "goal": "...", "task_count": 3, "plan_ref": "..."}],
            "count": 1,
            "total": 1,
        }

    Args:
        plan_dir: Directory to scan for plan files.
        search: Optional substring to filter results by. Matched case-insensitively
                against ``feature``, ``description``, and ``goal`` fields.
        offset: Zero-based start index into the filtered result list.
        limit: Maximum number of items to return. Defaults to all results.
        filters: Optional ``key=value`` pairs (repeatable) for generic key filtering.
                Compose with AND logic; a key absent from a plan excludes it.
        output_format: Output serialization format (json or yaml).
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    if output_format not in _OUTPUT_FORMATS:
        _err(f"Invalid format '{output_format}'. Must be one of: {', '.join(_OUTPUT_FORMATS)}")

    if not plan_dir.exists():
        _err(f"Plan directory does not exist: {plan_dir}")

    backend = get_backend(str(plan_dir))
    result = operations.list_plans(
        backend, search=search, offset=offset, limit=limit, filter_by_key=_parse_filter_pairs(filters)
    )

    # Wrap the list in the documented envelope so CLI consumers receive a
    # stable shape: {"items": [...], "count": N, "total": N}.
    envelope = {"items": [dict(s) for s in result], "count": len(result), "total": len(result)}

    if output_format == "yaml":
        _output_yaml(envelope)
    else:
        _output_json(envelope)


@app.command()
def read(
    address: Annotated[str, typer.Argument(help="Plan address (P{N}) or task address (P{N}/T{M})")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json|yaml|rich")] = "json",
) -> None:
    """Read a plan or task and print its fields.

    When a task address is given (``P{N}/T{M}``), returns a ``TaskAssignment``
    response that includes both the plan-level context (goal, shared context,
    acceptance criteria) and the task details.  This gives agents everything
    they need in one call.

    When a plan-only address is given (``P{N}``), returns the ``Plan`` JSON.

    Args:
        address: Plan address (``P{N}`` or slug) or task address (``P{N}/T{M}``).
        plan_dir: Directory to search for plan files.
        output_format: Output serialization format.
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    if output_format not in _OUTPUT_FORMATS:
        _err(f"Invalid format '{output_format}'. Must be one of: {', '.join(_OUTPUT_FORMATS)}")

    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    if task_ref is None:
        _read_plan_only(plan_ref, plan_dir, output_format)
        return

    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref
    _read_task_assignment(plan_ref, plan_dir, task_id, output_format)


@app.command()
def state(
    address: Annotated[str, typer.Argument(help="Task address: P{plan}/T{task}")],
    new_status: Annotated[str, typer.Argument(help="New status value")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
) -> None:
    """Update a task's status.

    Args:
        address: Task address in ``P{N}/T{M}`` format.
        new_status: New status string (e.g., ``complete``, ``in-progress``).
        plan_dir: Directory to search for plan files.
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    if task_ref is None:
        _err(f"Address '{address}' does not include a task component (expected P{{N}}/T{{M}})")

    try:
        parsed_status = TaskStatus(new_status)
    except ValueError:
        valid = ", ".join(str(s) for s in TaskStatus)
        _err(f"Invalid status '{new_status}'. Must be one of: {valid}")

    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref

    backend = get_backend(str(plan_dir))

    # Read current task to capture old status for the confirmation message.
    try:
        assignment = operations.read_task(backend, plan_ref, task_id)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except TaskNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    task_data = assignment.task
    old_status = task_data.status

    try:
        result = operations.update_task_status(backend, plan_ref, task_id, parsed_status)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except TaskNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    typer.echo(f"Task {task_id}: {old_status} -> {result['status']}")


@app.command()
def ready(
    plan_address: Annotated[str, typer.Argument(help="Plan address: P{plan}")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json|yaml")] = "json",
) -> None:
    """List tasks ready for dispatch.

    Args:
        plan_address: Plan address in ``P{N}`` format.
        plan_dir: Directory to search for plan files.
        output_format: Output serialization format (json or yaml).
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    if output_format not in _OUTPUT_FORMATS:
        _err(f"Invalid format '{output_format}'. Must be one of: {', '.join(_OUTPUT_FORMATS)}")

    # Accept structured addresses only (P{N}, slug). The backend resolves
    # the address to whatever storage it uses — never pass filesystem paths.
    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    backend = get_backend(str(plan_dir))
    try:
        result = operations.get_ready_tasks(backend, plan_ref)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)
    except ValueError:
        # Drafting marker — plan is in DRAFTING state.
        drafting_marker = {"drafting": True, "ready_tasks": []}
        if output_format == "yaml":
            _output_yaml(drafting_marker)
        else:
            _output_json(drafting_marker)
        return

    # CLI output: serialize the ReadyTasksResult model.
    if output_format == "yaml":
        _output_yaml(result)
    else:
        _output_json(result)


@app.command()
def status(
    plan_address: Annotated[
        str | None, typer.Argument(help="Plan address: P{plan}. Omit with --all to list every plan.")
    ] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json|rich")] = "json",
    all_plans: Annotated[bool, typer.Option("--all", help="List status for every plan in plan_dir")] = False,
) -> None:
    """Show plan-level progress summary.

    With ``--all`` and no address, iterates over all plan files in ``plan_dir``
    and returns a JSON list of status objects.

    Args:
        plan_address: Plan address in ``P{N}`` format. Optional when ``--all`` is set.
        plan_dir: Directory to search for plan files.
        output_format: Output serialization format (json or rich).
        all_plans: If ``True``, return status for every plan found in ``plan_dir``.
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    if all_plans:
        if not plan_dir.exists():
            _err(f"Plan directory does not exist: {plan_dir}")
        results: list[dict[str, object]] = []
        backend = get_backend(str(plan_dir))
        for candidate in sorted(plan_dir.iterdir()):
            if not (candidate.suffix in {".yaml", ".md"} or candidate.is_dir()):
                continue
            try:
                plan_ref = plan_id_from_path(candidate)
                ps = operations.get_plan_status(backend, plan_ref)
                entry = ps.model_dump(mode="json")
                entry["path"] = str(candidate)
                results.append(entry)
            except ValueError:
                # Drafting plans raise ValueError — include a drafting marker
                # entry instead of silently skipping them.
                results.append({"drafting": True, "state": "drafting", "path": str(candidate)})
                continue
            except _PLAN_LOAD_ERRORS as exc:
                # Skip unreadable plan files when listing all; emit to stderr
                typer.echo(f"Warning: skipping {candidate}: {exc}", err=True)
                continue
        _output_json(results)
        return

    if plan_address is None:
        _err("Provide a plan address or use --all to list every plan")

    data = _get_plan_status_for_address(plan_address, plan_dir)

    if data.get("drafting"):
        if output_format == "rich":
            console = Console()
            console.print("Plan is in drafting state.")
        else:
            _output_json(data)
        return

    if output_format == "rich":
        _output_rich_status(data)
    else:
        _output_json(data)


@app.command()
def create(
    slug: Annotated[str, typer.Argument(help="Short identifier for the plan (e.g., auth-system)")],
    goal: Annotated[str, typer.Option("--goal", help="Human-readable goal statement")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Directory to create the plan in")] = None,
    context: Annotated[str | None, typer.Option("--context", help="Plan-level context (markdown)")] = None,
    issue: Annotated[int | None, typer.Option("--issue", help="GitHub issue number")] = None,
    from_stdin: Annotated[bool, typer.Option("--stdin", help="Read task YAML from stdin")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Create a new plan file with the given slug and goal.

    With ``--stdin``, reads a YAML document from stdin containing a ``tasks:``
    list.  Each task dict must satisfy the ``Task`` schema (required fields:
    ``task``/``id``, ``title``, ``status``, ``agent``, ``dependencies``,
    ``priority``, ``complexity``).

    Output (JSON)::

        {"path": "plan/Pa1b2c3d4-auth-system.yaml", "plan_id": "Pa1b2c3d4", "task_count": 3}

    Args:
        slug: Short slug identifier for the plan.
        goal: Goal statement written to the plan file.
        plan_dir: Directory where the plan file will be created.
        context: Optional plan-level context string.
        issue: Optional GitHub issue number.
        from_stdin: If ``True``, read task YAML from stdin.
        output_format: Output format (only ``json`` is supported).
    """
    if output_format != "json":
        _err(f"Unsupported output format: {output_format!r}. Only 'json' is supported.")
    plan_dir = _coerce_plan_dir(plan_dir)
    tasks: list[dict[str, object]] = []

    if from_stdin:
        raw = sys.stdin.read()
        if raw.strip():
            y = YAML()
            parsed = y.load(raw)
            if isinstance(parsed, dict) and "tasks" in parsed:
                tasks = list(parsed["tasks"])
            elif isinstance(parsed, list):
                tasks = [item for item in parsed if isinstance(item, dict)]
            else:
                _err("stdin must be YAML with a top-level 'tasks:' list or a bare list")

    # Delegate to dh_core.operations via a LocalYamlTaskProvider backend.

    backend = get_backend(str(plan_dir))
    try:
        result = operations.create_plan(backend, slug=slug, goal=goal, tasks=tasks, context=context, issue=issue)
    except ValueError as exc:
        _err(str(exc))
    except OSError as exc:
        _err(str(exc), exit_code=2)

    if isinstance(result, CreatePlanError):
        _err(result.error, exit_code=2)

    # Build the CLI output dict; operations layer returns a model, path is CLI-specific.
    plan_id = result.plan_id
    path_str = str(plan_dir / f"{plan_id}-{slug}.yaml") if plan_id else str(plan_dir)
    output = {**result.model_dump(by_alias=True, exclude_none=True), "path": path_str}
    _output_json(output)


@app.command()
def update(
    address: Annotated[str, typer.Argument(help="Plan address (P{N}) or task address (P{N}/T{M})")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    set_field: Annotated[list[str] | None, typer.Option("--set", help="field=value pairs to update")] = None,
    context: Annotated[str | None, typer.Option("--context", help="Set plan-level context field")] = None,
    append_section_name: Annotated[
        str | None, typer.Option("--append-section", help="Heading for the section to append")
    ] = None,
    section_content: Annotated[
        str | None, typer.Option("--section-content", help="Body text for the appended section")
    ] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Update plan or task fields.

    Supports three operations (combinable in one call):

    - ``--set field=value`` — update an arbitrary field on a plan or task.
    - ``--context TEXT`` — set the plan-level context field.
    - ``--append-section HEADING --section-content TEXT`` — append a markdown
      section to a task's body (requires a task address).

    Args:
        address: Plan address (``P{N}``) or task address (``P{N}/T{M}``).
        plan_dir: Directory to search for plan files.
        set_field: List of ``field=value`` strings.
        context: Plan-level context text.
        append_section_name: Heading for the markdown section to append.
        section_content: Body text for the appended section.
        output_format: Output format (only ``json`` is supported).
    """
    if set_field is None:
        set_field = []
    if output_format != "json":
        _err(f"Unsupported output format: {output_format!r}. Only 'json' is supported.")
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    task_id = f"T{task_ref}" if task_ref is not None and task_ref.isdigit() else task_ref

    # Parse --set field=value pairs
    parsed_fields: dict[str, str | int | list[str]] = {}
    for pair in set_field:
        if "=" not in pair:
            _err(f"--set value must be in 'field=value' format, got: {pair!r}")
        k, _, v = pair.partition("=")
        parsed_fields[k.strip()] = v

    if not context and not parsed_fields and not append_section_name:
        _err("Provide at least one of --context, --set, or --append-section")

    backend = get_backend(str(plan_dir))
    try:
        operations.update_plan_fields(
            backend,
            plan_ref,
            task_id=task_id,
            set_fields=parsed_fields or None,
            context=context,
            append_section_name=append_section_name,
            section_content=section_content,
        )
    except ValueError as exc:
        _err(str(exc))
    except (FileNotFoundError, KeyError) as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    _output_json({"updated": True, "address": address})


@app.command()
def claim(
    address: Annotated[str, typer.Argument(help="Task address: P{plan}/T{task}")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Claim a task by transitioning it to ``in-progress``.

    Exits non-zero if the task is already claimed or is not in ``not-started``
    status.  The JSON response includes the ``started`` timestamp written to
    the task file.

    Output (JSON)::

        {"claimed": true, "task_id": "T1", "started": "2026-03-15T13:01:10+00:00"}

    Args:
        address: Task address in ``P{N}/T{M}`` format.
        plan_dir: Directory to search for plan files.
        output_format: Output format (only ``json`` is supported).
    """
    if output_format != "json":
        _err(f"Unsupported output format: {output_format!r}. Only 'json' is supported.")
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    if task_ref is None:
        _err(f"Address '{address}' does not include a task component (expected P{{N}}/T{{M}})")

    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref

    backend = get_backend(str(plan_dir))
    try:
        result = operations.claim_task(backend, plan_ref, task_id)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except TaskNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)
    except ValueError as exc:
        # Task is not claimable — already claimed or in a terminal state.
        _err(str(exc))

    # claim_task returns a ClaimResult envelope with claimed/task_id/started/warnings.
    _output_json(result)


@app.command()
def validate(
    address: Annotated[str, typer.Argument(help="Plan address: P{plan}")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Validate a plan file against the canonical schema.

    Loads the plan and reports any schema gaps detected during parsing.
    Exits 0 if valid, 1 if any errors were found.

    Output (JSON)::

        {"valid": true, "errors": [], "warnings": []}

    Args:
        address: Plan address in ``P{N}`` format.
        plan_dir: Directory to search for plan files.
        output_format: Output format (only ``json`` is supported).
    """
    if output_format != "json":
        _err(f"Unsupported output format: {output_format!r}. Only 'json' is supported.")
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, _ = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    backend = get_backend(str(plan_dir))
    try:
        result = operations.read_plan(backend, plan_ref)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)
    except (ValueError, TypeError) as exc:
        _output_json({"valid": False, "errors": [str(exc)], "warnings": []})
        raise typer.Exit(1) from None

    errors: list[str] = []
    warnings: list[str] = []

    for gap in result.gaps:
        msg = f"[{gap.task_id}] {gap.field_name}: {gap.gap_type} (expected: {gap.expected})"
        if gap.gap_type in {"missing", "invalid_type", "invalid_value"}:
            errors.append(msg)
        else:
            warnings.append(msg)

    valid = len(errors) == 0
    result = {"valid": valid, "errors": errors, "warnings": warnings}
    _output_json(result)
    if not valid:
        raise typer.Exit(1)


def _resolve_task_definition(task_json: str | None, from_stdin: bool) -> dict[str, object]:
    """Resolve a task definition from ``--task-json`` or ``--stdin``.

    Args:
        task_json: Task definition as a JSON string, or ``None``.
        from_stdin: If ``True``, read task YAML from stdin.

    Returns:
        Parsed task definition dict.

    Raises:
        SystemExit(1): If neither source is provided, JSON is invalid, or
            stdin does not contain a YAML mapping.
    """
    if task_json is not None:
        try:
            parsed = json.loads(task_json)
        except json.JSONDecodeError as exc:
            _err(f"Invalid JSON in --task-json: {exc}")
        if not isinstance(parsed, dict):
            _err("--task-json must be a JSON object (task definition)")
        return parsed
    if not from_stdin:
        _err("Provide a task definition via --task-json or --stdin")

    raw = sys.stdin.read()
    if not raw.strip():
        _err("stdin is empty — provide a task definition via --stdin or --task-json")
    y = YAML()
    parsed = y.load(raw)
    if not isinstance(parsed, dict):
        _err("stdin must be a YAML task definition (single mapping)")
    return parsed


@app.command(name="append-task")
def append_task(
    plan_address: Annotated[str, typer.Argument(help="Plan address: P{plan} or slug")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    task_json: Annotated[str | None, typer.Option("--task-json", help="Task definition as JSON string")] = None,
    from_stdin: Annotated[bool, typer.Option("--stdin", help="Read task YAML from stdin")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Append a single task to an existing plan.

    Reads a task definition from ``--task-json`` (JSON string) or ``--stdin``
    (YAML). The task is appended to the plan identified by ``plan_address``.
    Plans in ``drafting`` state stay in drafting until ``sam finalize`` is called.

    Output (JSON)::

        {"appended": true, "task_id": "T3"}

    Args:
        plan_address: Plan address in ``P{N}`` or slug format.
        plan_dir: Directory to search for plan files.
        task_json: Task definition as a JSON string.
        from_stdin: If ``True``, read task YAML from stdin.
        output_format: Output format (only ``json`` is supported).
    """
    if output_format != "json":
        _err(f"Unsupported output format: {output_format!r}. Only 'json' is supported.")
    plan_dir = _coerce_plan_dir(plan_dir)

    # Accept structured addresses only (P{N}, slug).
    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    task_dict = _resolve_task_definition(task_json, from_stdin)

    backend = get_backend(str(plan_dir))
    try:
        result = operations.append_task(backend, plan_ref, task_dict)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)
    except ValueError as exc:
        _err(str(exc))

    _output_json(result)


@app.command()
def finalize(
    plan_address: Annotated[str, typer.Argument(help="Plan address: P{plan} or slug")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Transition a plan from drafting state to ready state.

    After appending tasks to a drafting plan, ``finalize`` transitions the
    plan to ``ready`` state, making it available for execution via
    ``sam ready`` and ``sam status``.

    Output (JSON)::

        {"finalized": true, "state": "ready"}

    Args:
        plan_address: Plan address in ``P{N}`` or slug format.
        plan_dir: Directory to search for plan files.
        output_format: Output format (only ``json`` is supported).
    """
    if output_format != "json":
        _err(f"Unsupported output format: {output_format!r}. Only 'json' is supported.")
    plan_dir = _coerce_plan_dir(plan_dir)

    # Accept structured addresses only (P{N}, slug).
    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    backend = get_backend(str(plan_dir))
    try:
        result = operations.finalize_plan(backend, plan_ref)
    except PlanNotFoundError as exc:
        _err(str(exc))
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    _output_json(result)


def _canonical_output_path(plan_path: Path) -> Path:
    """Derive the canonical ``P{NNN}-{slug}.yaml`` output path for a legacy plan file.

    Args:
        plan_path: Source ``.md`` or directory plan path.

    Returns:
        Canonical output path.  For directories, returns the same path unchanged.
        For files matching ``tasks-{N}-{slug}.md``, returns ``P{NNN}-{slug}.yaml``.
        For any other file, returns the path with ``.yaml`` suffix.
    """
    if plan_path.is_dir():
        return plan_path
    m = re.match(r"^tasks-(\d+)-(.+)\.md$", plan_path.name)
    if m:
        num = int(m.group(1))
        slug = m.group(2)
        return plan_path.parent / f"P{num:03d}-{slug}.yaml"
    return plan_path.with_suffix(".yaml")


def _extract_fallback_metadata(raw_content: str, plan_path: Path) -> tuple[int, str, str, int | None]:
    """Extract minimal metadata from a non-parseable plan file.

    Args:
        raw_content: Raw text of the plan file.
        plan_path: Path to the plan file (used for filename-based extraction).

    Returns:
        Tuple of ``(plan_number, slug, goal, issue)`` where ``issue`` may be ``None``.
    """
    m = re.match(r"^tasks-(\d+)-(.+)\.md$", plan_path.name)
    plan_number = int(m.group(1)) if m else 0
    slug = m.group(2) if m else plan_path.stem

    goal = slug.replace("-", " ").title()
    heading_match = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
    if heading_match:
        goal = heading_match.group(1).strip()
    else:
        fm_desc = re.search(r"^description:\s*(.+)$", raw_content, re.MULTILINE)
        if fm_desc:
            goal = fm_desc.group(1).strip().strip("\"'")

    issue: int | None = None
    issue_bold = re.search(r"\*\*Issue\*\*[:\s]+#?(\d+)", raw_content)
    if issue_bold:
        issue = int(issue_bold.group(1))
    else:
        issue_fm = re.search(r"^issue:\s*#?(\d+)", raw_content, re.MULTILINE)
        if issue_fm:
            issue = int(issue_fm.group(1))

    return plan_number, slug, goal, issue


def _migrate_one_fallback(plan_path: Path, dry_run: bool) -> tuple[Path | None, str]:
    """Best-effort preservation migration for files that ``load_plan`` cannot parse.

    When the canonical loader rejects a file (non-standard task lists, checklist
    tasks, or prose-only markdown), this fallback reads the raw content, extracts
    whatever structured metadata is available from the filename and file body, and
    writes a minimal valid Plan YAML.  The full original content is preserved in the
    ``context`` field — no data is lost.

    The output YAML has:

    - ``plan_number`` and ``slug`` derived from the filename.
    - ``goal`` from the first ``#`` heading or ``description:`` frontmatter field.
    - ``status: complete`` (all non-parseable plans are assumed to be old/done).
    - ``tasks: []`` — the original task content lives in ``context.body``.
    - ``context.body`` — the complete raw file content verbatim.
    - ``context.source_file`` — original filename for traceability.

    Args:
        plan_path: Path to the legacy ``.md`` file.
        dry_run: If ``True``, print what would change without writing to disk.

    Returns:
        Tuple of ``(output_path, source_format)`` where ``source_format`` is
        ``"fallback-preservation"``.  ``output_path`` is ``None`` on dry-run.

    Raises:
        FileExistsError: If the canonical target already exists and ``dry_run`` is ``False``.
        OSError: If the output file cannot be written.
    """
    source_format = "fallback-preservation"
    output_path = _canonical_output_path(plan_path)

    # Collision check — same guard as _migrate_one
    if output_path != plan_path and output_path.exists():
        msg = f"Skipping {plan_path.name}: target {output_path.name} already exists"
        typer.echo(msg, err=True)
        if not dry_run:
            raise FileExistsError(msg)
        return None, source_format

    raw_content = plan_path.read_text(encoding="utf-8", errors="replace")
    plan_number, slug, goal, issue = _extract_fallback_metadata(raw_content, plan_path)

    if dry_run:
        typer.echo(f"Would migrate (fallback): {plan_path}")
        typer.echo(f"  Source format: {source_format}")
        typer.echo(f"  Output path:   {output_path}")
        typer.echo(f"  Goal:          {goal}")
        typer.echo("  Tasks:         0 (content preserved in context)")
        return None, source_format

    y = YAML()
    y.default_flow_style = False
    y.width = 2147483647

    plan_data: dict[str, object] = {
        "plan_number": plan_number,
        "slug": slug,
        "goal": goal,
        "status": "complete",
        "tasks": [],
        "context": {"source_file": plan_path.name, "body": raw_content},
    }
    if issue is not None:
        plan_data["issue"] = issue

    buf = io.StringIO()
    y.dump(plan_data, buf)
    output_path.write_text(buf.getvalue(), encoding="utf-8")

    typer.echo(f"Migrated (fallback) {plan_path} -> {output_path}")
    typer.echo(f"  Source format: {source_format}")
    typer.echo(f"  Goal:          {goal}")
    typer.echo("  Tasks written: 0 (original content preserved in context.body)")
    return output_path, source_format


def _migrate_one(plan_path: Path, dry_run: bool) -> tuple[Path | None, str]:
    """Migrate a single plan file to canonical pure-YAML format.

    Attempts canonical load via ``operations.read_plan``.  If the loader raises any
    exception (non-standard task lists, checklist tasks, or prose-only markdown),
    falls back to ``_migrate_one_fallback`` which performs best-effort
    preservation: the original content is stored verbatim in ``context.body``.

    Args:
        plan_path: Resolved path to the plan file or directory.
        dry_run: If ``True``, print what would change without writing to disk.

    Returns:
        Tuple of ``(output_path, source_format)``.  ``output_path`` is ``None``
        when ``dry_run`` is ``True`` (nothing was written).

    Raises:
        FileNotFoundError: If ``plan_path`` does not exist.
        FileExistsError: If the canonical target already exists (collision guard).
        OSError: If the output file cannot be written.
    """
    plan_ref = plan_id_from_path(plan_path)
    # Root the backend at the parent directory for both files and directories.
    # For files (e.g. P1-auth.yaml), plan_path.parent is the plan dir. For
    # directory-based plans (e.g. P1-auth/), the backend must also look at the
    # parent — rooting at the directory itself breaks plan resolution.
    backend = get_backend(str(plan_path.parent))
    try:
        result = operations.read_plan(backend, plan_ref)
    except _PLAN_LOAD_ERRORS:
        return _migrate_one_fallback(plan_path, dry_run)

    source_format = result.source_format
    plan = result.plan

    output_path = _canonical_output_path(plan_path)

    # Collision check: skip if target P{NNN} file already exists
    if output_path != plan_path and output_path.exists():
        msg = f"Skipping {plan_path.name}: target {output_path.name} already exists"
        typer.echo(msg, err=True)
        if not dry_run:
            raise FileExistsError(msg)
        return None, source_format

    if dry_run:
        typer.echo(f"Would migrate: {plan_path}")
        typer.echo(f"  Source format: {source_format}")
        typer.echo(f"  Output path:   {output_path}")
        typer.echo(f"  Tasks:         {len(plan.tasks)}")
        typer.echo(f"  Schema gaps:   {len(result.gaps)}")
        if result.gaps:
            for gap in result.gaps:
                typer.echo(f"    [{gap.task_id}] {gap.field_name}: {gap.gap_type}")
        return None, source_format

    written = write_plan(plan, output_path)
    typer.echo(f"Migrated {plan_path} -> {written}")
    typer.echo(f"  Source format: {source_format}")
    typer.echo(f"  Tasks written: {len(plan.tasks)}")
    return written, source_format


def _update_backlog_refs(old_path: Path, new_path: Path, backlog_dir: Path) -> int:
    """Update ``plan:`` frontmatter fields in backlog files that reference ``old_path``.

    Scans ``backlog_dir`` for ``*.md`` files whose YAML frontmatter ``plan``
    field matches ``old_path`` (as a string) and rewrites it to ``new_path``.
    Uses ``ruamel.yaml`` directly for comment-preserving round-trip edits of
    the frontmatter block, without requiring ``backlog_core``.

    Args:
        old_path: The legacy plan path being replaced.
        new_path: The canonical ``.yaml`` path to substitute.
        backlog_dir: Directory containing backlog ``*.md`` files.

    Returns:
        Number of backlog files updated.
    """
    if not backlog_dir.exists():
        return 0

    old_str = str(old_path)
    new_str = str(new_path)
    updated = 0
    y = YAML()
    y.preserve_quotes = True
    y.width = 2147483647

    for md_file in sorted(backlog_dir.glob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if not raw.startswith("---"):
            continue
        parts = raw.split("---", 2)
        if len(parts) < _YAML_FRONTMATTER_PARTS:
            continue
        _, fm_text, body = parts
        try:
            fm_data = y.load(fm_text)
        except YAMLError:
            continue
        if not isinstance(fm_data, dict):
            continue
        plan_val = fm_data.get("plan")
        if plan_val is None or str(plan_val) != old_str:
            continue
        fm_data["plan"] = new_str
        try:
            buf = io.StringIO()
            y.dump(fm_data, buf)
            new_raw = f"---\n{buf.getvalue()}---{body}"
            md_file.write_text(new_raw, encoding="utf-8")
            updated += 1
        except (YAMLError, OSError):
            continue

    return updated


@app.command()
def migrate(
    plan_address: Annotated[str | None, typer.Argument(help="Plan address: P{plan}. Omit when using --all.")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
    all_plans: Annotated[bool, typer.Option("--all", help="Migrate every legacy plan file in plan_dir")] = False,
    skip_sync: Annotated[
        bool, typer.Option("--skip-sync", help="Skip backlog sync to GitHub before migrating")
    ] = False,
    backlog_dir: Annotated[
        Path | None, typer.Option("--backlog-dir", help="Backlog directory for plan reference updates")
    ] = None,
) -> None:
    """Migrate a legacy or YAML-frontmatter plan to canonical pure-YAML format.

    With ``--all``, scans ``plan_dir`` for every legacy ``tasks-{N}-{slug}.md``
    file, migrates each one to a ``.yaml`` counterpart, and updates any backlog
    ``plan:`` references that pointed at the old path.

    Without ``--all``, migrates the single plan identified by ``plan_address``.

    Args:
        plan_address: Plan address in ``P{N}`` format. Required unless ``--all`` is set.
        plan_dir: Directory to search for plan files.
        dry_run: If ``True``, print what would change without writing to disk.
        all_plans: If ``True``, migrate every eligible legacy file in ``plan_dir``.
        skip_sync: If ``True``, skip the pre-migration backlog sync step.
        backlog_dir: Directory containing backlog ``*.md`` files for reference updates.
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    backlog_dir = _coerce_backlog_dir(backlog_dir)
    if all_plans:
        _migrate_all(plan_dir=plan_dir, dry_run=dry_run, skip_sync=skip_sync, backlog_dir=backlog_dir)
        return

    if plan_address is None:
        _err("Provide a plan address or use --all to migrate every plan")

    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    plan_path = _resolve_plan(plan_ref, plan_dir)

    try:
        _migrate_one(plan_path, dry_run)
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)
    except (ValueError, OSError) as exc:
        _err(str(exc), exit_code=2)


def _migrate_all(plan_dir: Path, dry_run: bool, skip_sync: bool, backlog_dir: Path | None = None) -> None:
    """Bulk-migrate all legacy plan files in ``plan_dir``.

    Steps:
      1. Inventory ``.md`` files matching ``tasks-{N}-{slug}`` pattern.
      2. Sync backlog to GitHub (unless ``skip_sync`` is set).
      3. Migrate each file; collect old→new path mappings.
      4. Update backlog references for each migrated file.
      5. Print summary.

    Args:
        plan_dir: Directory to scan for legacy plan files.
        dry_run: If ``True``, print what would change without writing to disk.
        skip_sync: If ``True``, skip the backlog sync step.
        backlog_dir: Directory containing backlog ``*.md`` files for reference updates.
    """
    resolved_backlog_dir = _coerce_backlog_dir(backlog_dir)
    if not plan_dir.exists():
        _err(f"Plan directory does not exist: {plan_dir}")

    # Step 1: Inventory — find .md files matching tasks-{N}-{slug} pattern
    legacy_pattern = re.compile(r"^tasks-\d+-")
    candidates: list[Path] = sorted(p for p in plan_dir.iterdir() if p.suffix == ".md" and legacy_pattern.match(p.name))

    if not candidates:
        typer.echo("No legacy plan files found to migrate.")
        return

    typer.echo(f"Found {len(candidates)} legacy plan file(s) to migrate.")

    # Step 2: Backlog sync
    if not skip_sync and not dry_run:
        _attempt_backlog_sync()

    # Step 3: Migrate each file
    migrated: list[tuple[Path, Path]] = []  # (old_path, new_path)
    errors: list[str] = []

    for plan_path in candidates:
        # Check for collision: target .yaml already exists
        target = plan_path.with_suffix(".yaml")
        if not dry_run and target.exists():
            typer.echo(f"  Skipping {plan_path.name}: {target.name} already exists", err=True)
            continue

        try:
            written, _ = _migrate_one(plan_path, dry_run)
        except (*_PLAN_LOAD_ERRORS, OSError) as exc:
            msg = f"  Error migrating {plan_path.name}: {exc}"
            typer.echo(msg, err=True)
            errors.append(msg)
            continue

        if written is not None:
            migrated.append((plan_path, written))

    # Step 4: Update backlog references
    ref_updates = 0
    if not dry_run:
        for old_path, new_path in migrated:
            ref_updates += _update_backlog_refs(old_path, new_path, resolved_backlog_dir)

    # Step 5: Report
    typer.echo("")
    if dry_run:
        typer.echo(f"Dry run complete. Would migrate {len(candidates)} file(s).")
    else:
        typer.echo("Migration complete.")
        typer.echo(f"  Migrated:          {len(migrated)}/{len(candidates)} file(s)")
        typer.echo(f"  Backlog refs updated: {ref_updates}")
        if errors:
            typer.echo(f"  Errors:            {len(errors)}", err=True)


def _attempt_backlog_sync() -> None:
    """Attempt to sync the local backlog to GitHub.

    Tries ``backlog_core`` first, then falls back to shelling out to
    ``uv run backlog sync``.  Prints a warning on failure but does not abort.
    """
    if _BACKLOG_CORE_AVAILABLE:
        try:
            _sync_backlog()
        except _SYNC_ERRORS as sync_exc:
            typer.echo(f"Warning: backlog_core sync failed; falling back to CLI. ({sync_exc})", err=True)
        else:
            typer.echo("Backlog synced to GitHub.")
            return

    if not (uv_exe := shutil.which("uv")):
        typer.echo("Warning: backlog sync unavailable (uv not found).", err=True)
        return

    try:
        proc = subprocess.run(
            [uv_exe, "run", "backlog", "sync"], capture_output=True, text=True, timeout=30, check=False
        )
        if proc.returncode == 0:
            typer.echo("Backlog synced to GitHub.")
        else:
            typer.echo(f"Warning: backlog sync failed (exit {proc.returncode}): {proc.stderr.strip()}", err=True)
    except (subprocess.SubprocessError, OSError) as exc:
        typer.echo(f"Warning: backlog sync unavailable: {exc}", err=True)


def _print_output_messages(out: Output, *, stderr: bool = True) -> None:
    """Print any messages, warnings, and errors collected in an ``Output``.

    By default informational messages are sent to stderr (via ``err=True``)
    so that stdout remains parseable for JSON consumers. When ``stderr`` is
    ``False``, messages go to stdout.
    """
    for msg in out.messages:
        typer.echo(msg, err=stderr)
    for msg in out.warnings:
        typer.echo(f"Warning: {msg}", err=True)
    for msg in out.errors:
        typer.echo(f"Error: {msg}", err=True)


@app.command(name="backlog-add")
def backlog_add(
    title: Annotated[str, typer.Argument(help="Backlog item title")],
    description: Annotated[str, typer.Option("--description", help="Item description")] = "",
    priority: Annotated[str, typer.Option("--priority", help="Priority level (P1/P2/P3)")] = "P1",
    source: Annotated[str, typer.Option("--source", help="Source of the item")] = "Not specified",
    type_: Annotated[str, typer.Option("--type", help="Item type (Feature/Bug/etc.)")] = "Feature",
    force: Annotated[bool, typer.Option("--force", help="Force creation even if duplicate suspected")] = False,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Add a new item to the backlog."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.add_item(
        title=title,
        description=description,
        priority=priority,
        source=source,
        type_=type_,
        force=force,
        repo=repo,
        output=out,
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-list")
def backlog_list(
    from_github: Annotated[bool, typer.Option("--from-github", help="Refresh from GitHub before listing")] = False,
    label: Annotated[str | None, typer.Option("--label", help="Filter by label")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Filter by section")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Filter by status")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Filter by title substring")] = None,
    type_: Annotated[str | None, typer.Option("--type", help="Filter by item type")] = None,
    topic: Annotated[str | None, typer.Option("--topic", help="Filter by topic")] = None,
    include_closed: Annotated[bool, typer.Option("--include-closed", help="Include closed items")] = False,
    filters: Annotated[
        list[str] | None,
        typer.Option(
            "--filter", help="Filter by key=value pairs on result items (repeatable). Example: --filter type=Bug"
        ),
    ] = None,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List backlog items, optionally filtered."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_items(
        from_github=from_github,
        label=label,
        section=section,
        status=status,
        title=title,
        type_=type_,
        topic=topic,
        include_closed=include_closed,
        filter_by_key=_parse_filter_pairs(filters),
        repo=repo,
        output=out,
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-link-followup")
def backlog_link_followup(
    selector: Annotated[
        str, typer.Argument(help="Item selector: title substring, #N, bare number, URL, or beads nanoid")
    ],
    followup_to: Annotated[
        str,
        typer.Option(
            "--to", help="Logical ID of the originating plan/task (e.g. P1, P1/T3). Empty string clears the link."
        ),
    ],
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Link a follow-up backlog item to its originating plan or task."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.link_followup(selector=selector, followup_to=followup_to, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-list-followups")
def backlog_list_followups(
    followup_to: Annotated[str, typer.Argument(help="Logical ID of the originating plan/task (e.g. P1, P1/T3)")],
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List backlog items linked as follow-ups to the given origin."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_followups(followup_to=followup_to, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-view")
def backlog_view(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    limit: Annotated[int, typer.Option("--limit", help="Maximum items to return (0 = all)")] = 0,
    show: Annotated[str | None, typer.Option("--show", help="Show specific section or field")] = None,
    since: Annotated[str | None, typer.Option("--since", help="Filter entries since date/commit")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Show only a named section")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """View a single backlog item by selector."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.view_item(
        selector=selector, repo=repo, offset=offset, limit=limit, show=show, since=since, output=out, section=section
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-update")
def backlog_update(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    plan: Annotated[str | None, typer.Option("--plan", help="Set plan reference")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Set status (e.g. in-progress)")] = None,
    section: Annotated[str | None, typer.Option("--section", help="Section name for content update")] = None,
    content: Annotated[str | None, typer.Option("--content", help="Content to write into section")] = None,
    title: Annotated[str | None, typer.Option("--title", help="New title")] = None,
    description: Annotated[str | None, typer.Option("--description", help="New description")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Update a backlog item's fields."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.update_item(
        selector=selector,
        plan=plan,
        status=status,
        section=section,
        content=content,
        title=title,
        description=description,
        repo=repo,
        output=out,
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-close")
def backlog_close(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    reason: Annotated[str, typer.Option("--reason", help="Categorized reason for closing (required)")],
    reference: Annotated[str, typer.Option("--reference", help="Reference URL or issue number")] = "",
    comment: Annotated[str, typer.Option("--comment", help="Closing comment")] = "",
    cleanup: Annotated[bool, typer.Option("--cleanup", help="Clean up local files after closing")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force close even if checks fail")] = False,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Dismiss a backlog item without completion (duplicate, out-of-scope, etc.)."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.close_item(
        selector=selector,
        reason=reason,
        reference=reference,
        comment=comment,
        cleanup=cleanup,
        force=force,
        repo=repo,
        output=out,
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-resolve")
def backlog_resolve(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    summary: Annotated[str, typer.Option("--summary", help="Completion summary (required)")],
    plan: Annotated[str, typer.Option("--plan", help="Plan reference applied")] = "",
    method: Annotated[str, typer.Option("--method", help="Method used to resolve")] = "",
    notes: Annotated[str, typer.Option("--notes", help="Additional notes")] = "",
    follow_ups: Annotated[str, typer.Option("--follow-ups", help="Follow-up items")] = "",
    findings: Annotated[str, typer.Option("--findings", help="Findings or evidence")] = "",
    cleanup: Annotated[bool, typer.Option("--cleanup", help="Clean up local files after resolving")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force resolve even if checks fail")] = False,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Mark a backlog item as done (completed) and close the issue with evidence."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.resolve_item(
        selector=selector,
        summary=summary,
        plan=plan,
        method=method,
        notes=notes,
        follow_ups=follow_ups,
        findings=findings,
        cleanup=cleanup,
        force=force,
        repo=repo,
        output=out,
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-groom")
def backlog_groom(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    section: Annotated[str | None, typer.Option("--section", help="Section name for content")] = None,
    content: Annotated[str | None, typer.Option("--content", help="Content to write into section")] = None,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Write groomed content into a backlog item file."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.groom_item(selector=selector, section=section, content=content, repo=repo, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-sync")
def backlog_sync(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Sync local backlog items to GitHub (create missing issues, push groomed content)."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.sync_items(repo=repo, dry_run=dry_run, output=out)
    _output_json(result)
    _print_output_messages(out)


def _parse_json_list(raw: str, param_name: str) -> list[str]:
    """Parse a JSON string into a list[str], or exit with error.

    Returns:
        Parsed list of strings.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        _err(f"Invalid JSON for {param_name}: {exc}")
    if not isinstance(parsed, list):
        _err(f"Invalid JSON for {param_name}: expected a list")
    return [str(item) for item in parsed]


@app.command(name="sam-task-create")
def sam_task_create(
    parent_issue: Annotated[int, typer.Argument(help="Parent issue number")],
    task_id: Annotated[str, typer.Option("--task-id", help="Task identifier")] = "",
    feature: Annotated[str, typer.Option("--feature", help="Feature name")] = "",
    task_type: Annotated[str, typer.Option("--task-type", help="Task type")] = "",
    agent: Annotated[str, typer.Option("--agent", help="Agent name")] = "",
    priority: Annotated[int, typer.Option("--priority", help="Task priority")] = 0,
    skills_json: Annotated[str, typer.Option("--skills-json", help="JSON list of skills")] = "[]",
    dependencies_json: Annotated[str, typer.Option("--dependencies-json", help="JSON list of dependencies")] = "[]",
    description: Annotated[str, typer.Option("--description", help="Task description")] = "",
    acceptance_criteria_json: Annotated[
        str, typer.Option("--acceptance-criteria-json", help="JSON list of acceptance criteria")
    ] = "[]",
    labels_json: Annotated[str, typer.Option("--labels-json", help="JSON list of labels")] = "[]",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Create a SAM task issue under a parent issue."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    skills = _parse_json_list(skills_json, "skills")
    dependencies = _parse_json_list(dependencies_json, "dependencies")
    acceptance_criteria = _parse_json_list(acceptance_criteria_json, "acceptance_criteria")
    labels = _parse_json_list(labels_json, "labels")
    out = Output()
    result = operations.create_sam_task(
        parent_issue_number=parent_issue,
        task_id=task_id,
        feature=feature,
        task_type=task_type,
        agent=agent,
        priority=priority,
        skills=skills,
        dependencies=dependencies,
        description=description,
        acceptance_criteria=acceptance_criteria,
        labels=labels,
        output=out,
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="sam-tasks")
def sam_tasks(
    parent_issue: Annotated[int, typer.Argument(help="Parent issue number")],
    refresh_cache: Annotated[bool, typer.Option("--refresh-cache", help="Refresh cache from GitHub")] = True,
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List SAM tasks under a parent issue."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.get_sam_tasks(
        parent_issue_number=parent_issue, refresh_cache=refresh_cache, repo=repo, output=out
    )
    _output_json(result)
    _print_output_messages(out)


@app.command(name="sam-task-status")
def sam_task_status(
    issue_number: Annotated[int, typer.Argument(help="SAM task issue number")],
    status: Annotated[str, typer.Option("--status", help="New status")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Update a SAM task's status."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    if not status:
        _err("--status is required")
    out = Output()
    result = operations.update_sam_task_status(issue_number=issue_number, new_status=status, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="sam-ready-tasks")
def sam_ready_tasks(
    parent_issue: Annotated[int, typer.Argument(help="Parent issue number")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List SAM tasks that are ready to start (dependencies met)."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.get_ready_sam_tasks(parent_issue_number=parent_issue, repo=repo, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="labels")
def labels(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    limit: Annotated[int, typer.Option("--limit", help="Maximum labels to return")] = 100,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List GitHub labels for a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_labels(repo=repo, limit=limit, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="merged-prs")
def merged_prs(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    search: Annotated[str | None, typer.Option("--search", help="Search query")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum PRs to return")] = 20,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List merged pull requests for a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_merged_prs(repo=repo, search=search, limit=limit, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="milestones")
def milestones(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    state: Annotated[str, typer.Option("--state", help="Milestone state (open/closed/all)")] = "open",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List milestones for a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_milestones(repo=repo, state=state, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="soonest-milestone")
def soonest_milestone(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Get the soonest open milestone for a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.get_soonest_milestone(repo=repo, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="create-milestone")
def create_milestone(
    title: Annotated[str, typer.Option("--title", help="Milestone title (required)")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    description: Annotated[str, typer.Option("--description", help="Milestone description")] = "",
    due_on: Annotated[str | None, typer.Option("--due-on", help="Due date (ISO 8601)")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Create a new milestone in a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.create_milestone(repo=repo, title=title, description=description, due_on=due_on, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="issues")
def issues(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    milestone: Annotated[str | None, typer.Option("--milestone", help="Filter by milestone")] = None,
    labels: Annotated[str | None, typer.Option("--labels", help="Comma-separated labels")] = None,
    state: Annotated[str, typer.Option("--state", help="Issue state (open/closed/all)")] = "open",
    limit: Annotated[int, typer.Option("--limit", help="Maximum issues to return")] = 30,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List issues in a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_issues(repo=repo, milestone=milestone, labels=labels, state=state, limit=limit, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="comment-issue")
def comment_issue(
    issue_number: Annotated[int, typer.Option("--issue-number", help="Issue number (required)")],
    body: Annotated[str, typer.Option("--body", help="Comment body (required)")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Add a comment to a GitHub issue."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.comment_issue(repo=repo, issue_number=issue_number, body=body, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="comments")
def comments(
    issue_number: Annotated[int, typer.Option("--issue-number", help="Issue number (required)")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    limit: Annotated[int, typer.Option("--limit", help="Maximum comments to return")] = 20,
    offset: Annotated[int, typer.Option("--offset", help="Pagination offset")] = 0,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List comments on a GitHub issue."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_comments(repo=repo, issue_number=issue_number, limit=limit, offset=offset, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="read-comment")
def read_comment(
    issue_number: Annotated[int, typer.Option("--issue-number", help="Issue number (required)")],
    comment_id: Annotated[int, typer.Option("--comment-id", help="Comment ID (required)")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Read a single comment on a GitHub issue."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.read_comment(repo=repo, issue_number=issue_number, comment_id=comment_id, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="projects")
def projects(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    owner: Annotated[str | None, typer.Option("--owner", help="Repository owner")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum projects to return")] = 20,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List GitHub Projects for a repository or owner."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.list_projects(repo=repo, owner=owner, limit=limit, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="create-project")
def create_project(
    title: Annotated[str, typer.Option("--title", help="Project title (required)")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    owner: Annotated[str | None, typer.Option("--owner", help="Repository owner")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Create a new GitHub Project."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.create_project(repo=repo, title=title, owner=owner, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-pull")
def backlog_pull(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    diff: Annotated[bool, typer.Option("--diff", help="Return a diff instead of writing the item")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Pull a single backlog item from GitHub by selector."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.pull_by_selector(selector=selector, repo=repo, diff=diff, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-pull-all")
def backlog_pull_all(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force pull even if local items are newer")] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Return a diff instead of writing items")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Pull all backlog items from GitHub for a repository."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.pull_items(repo=repo, dry_run=dry_run, force=force, diff=diff, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-normalize")
def backlog_normalize(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Normalize backlog item files (canonical frontmatter and structure)."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.normalize_items(dry_run=dry_run, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-strike")
def backlog_strike(
    selector: Annotated[str, typer.Argument(help="Item selector: #N, bare number, title, or URL")],
    entry_id: Annotated[str, typer.Option("--entry-id", help="Log entry ID to strike (required)")],
    reason: Annotated[str, typer.Option("--reason", help="Reason for striking the entry (required)")],
    section: Annotated[str | None, typer.Option("--section", help="Section containing the entry")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Strike a log entry from a backlog item."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.strike_entry(selector=selector, entry_id=entry_id, reason=reason, section=section, output=out)
    _output_json(result)
    _print_output_messages(out)


@app.command(name="backlog-refresh")
def backlog_refresh(
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    label: Annotated[str | None, typer.Option("--label", help="Filter issues by label")] = None,
    full_refresh: Annotated[bool, typer.Option("--full-refresh", help="Re-fetch all items, not just deltas")] = False,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Refresh the local backlog cache from GitHub Issues."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    out = Output()
    result = operations.refresh_local_cache_from_github(repo=repo, label=label, full_refresh=full_refresh, output=out)
    _output_json(result)
    _print_output_messages(out)


# ---------------------------------------------------------------------------
# Dispatch CLI commands
# ---------------------------------------------------------------------------


@app.command(name="dispatch-read")
def dispatch_read(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Read a dispatch plan for a milestone."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_read_plan(milestone_number=milestone)
    _output_json(result)


@app.command(name="dispatch-validate")
def dispatch_validate(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Validate a dispatch plan's structural integrity."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_validate_plan(milestone_number=milestone)
    _output_json(result)


@app.command(name="dispatch-stale-check")
def dispatch_stale(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Check whether a dispatch plan is stale relative to the current milestone."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_stale_check(milestone_number=milestone, repo=repo)
    _output_json(result)


@app.command(name="dispatch-create-plan")
def dispatch_create(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    plan_json: Annotated[str, typer.Option("--plan-json", help="Dispatch plan as JSON string")],
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing plan file")] = False,
    validate: Annotated[bool, typer.Option("--validate", help="Run validation after writing")] = True,
    issue: Annotated[int | None, typer.Option("--issue", help="Optional issue to register artifact for")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Create or overwrite a dispatch plan YAML file."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    try:
        plan_dict = json.loads(plan_json)
    except json.JSONDecodeError as exc:
        _err(f"Invalid JSON for plan: {exc}")
    result = operations.dispatch_create_plan(
        milestone_number=milestone, plan=plan_dict, overwrite=overwrite, validate=validate, issue=issue
    )
    _output_json(result)


@app.command(name="dispatch-conflicts")
def dispatch_conflicts_cmd(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    repo: Annotated[str, typer.Option("--repo", help="Repository (owner/name)")] = "",
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Analyze Impact Radius conflicts for items in a milestone."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_conflicts(milestone_number=milestone, repo=repo)
    _output_json(result)


@app.command(name="dispatch-wave-start")
def dispatch_wave_start_cmd(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    wave: Annotated[int, typer.Option("--wave", help="Wave number (1-based)")],
    items_json: Annotated[str, typer.Option("--items-json", help="JSON list of items with 'issue' and 'title' keys")],
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Record the start of a dispatch wave."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    try:
        items = json.loads(items_json)
    except json.JSONDecodeError as exc:
        _err(f"Invalid JSON for items: {exc}")
    if not isinstance(items, list):
        _err("Invalid JSON for items: expected a list")
    result = operations.dispatch_wave_start(milestone=milestone, wave_num=wave, items=items)
    _output_json(result)


@app.command(name="dispatch-item-status")
def dispatch_item_status_cmd(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    issue: Annotated[int, typer.Argument(help="Issue number of the item")],
    status: Annotated[str, typer.Option("--status", help="New status: complete, failed, or skipped")],
    result_summary: Annotated[str, typer.Option("--result", help="Result summary or JSON")] = "",
    error: Annotated[str, typer.Option("--error", help="Error details on failure")] = "",
    cost: Annotated[float | None, typer.Option("--cost", help="USD cost if available")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Record completion or failure of a dispatch item."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_item_status(
        milestone=milestone, issue=issue, status=status, result=result_summary, error=error, cost=cost
    )
    _output_json(result)


@app.command(name="dispatch-wave-status")
def dispatch_wave_status_cmd(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    wave: Annotated[int, typer.Argument(help="Wave number to query (1-based)")],
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Query the current status of a dispatch wave."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_wave_status(milestone=milestone, wave_num=wave)
    _output_json(result)


@app.command(name="dispatch-spawn")
def dispatch_spawn_cmd(
    milestone: Annotated[int, typer.Argument(help="GitHub milestone number")],
    wave: Annotated[int, typer.Option("--wave", help="Starting wave number (1-based)")],
    max_concurrent: Annotated[int, typer.Option("--max-concurrent", help="Maximum concurrent spawned sessions")] = 3,
    model: Annotated[str, typer.Option("--model", help="Model identifier for spawned sessions")] = "sonnet",
    phase: Annotated[str, typer.Option("--phase", help="Dispatch phase: 'groom' or 'work'")] = "work",
    effort: Annotated[
        str | None, typer.Option("--effort", help="Effort level: low, medium, high, max (omit for model default)")
    ] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Spawn and monitor kage-bunshin sessions for a dispatch wave."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.dispatch_spawn(
        milestone=milestone, wave_num=wave, max_concurrent=max_concurrent, model=model, phase=phase, effort=effort
    )
    _output_json(result)


# ---------------------------------------------------------------------------
# Artifact CLI commands
# ---------------------------------------------------------------------------


@app.command(name="artifact-register")
def artifact_register_cmd(
    item_id: Annotated[int, typer.Argument(help="Backlog item identifier (GitHub issue number)")],
    artifact_type: Annotated[str, typer.Option("--type", help="Artifact type")],
    artifact_id: Annotated[str, typer.Option("--artifact-id", help="Artifact logical identifier or path")],
    status: Annotated[str, typer.Option("--status", help="Lifecycle status")] = "current",
    agent: Annotated[str, typer.Option("--agent", help="Producing agent name")] = "",
    content: Annotated[str | None, typer.Option("--content", help="Optional artifact content")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Register or update an artifact for a backlog item."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.artifact_register(
        item_id=item_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        status=status,
        agent=agent,
        content=content,
    )
    _output_json(result)


@app.command(name="artifact-list")
def artifact_list_cmd(
    item_id: Annotated[int, typer.Argument(help="Backlog item identifier (GitHub issue number)")],
    artifact_type: Annotated[str | None, typer.Option("--type", help="Filter by artifact type")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """List artifacts registered for a backlog item."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.artifact_list(item_id=item_id, artifact_type=artifact_type)
    _output_json(result)


@app.command(name="artifact-get")
def artifact_get_cmd(
    item_id: Annotated[int, typer.Argument(help="Backlog item identifier (GitHub issue number)")],
    artifact_type: Annotated[str, typer.Option("--type", help="Artifact type to retrieve")],
    artifact_id: Annotated[str | None, typer.Option("--artifact-id", help="Specific artifact ID")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Get metadata for artifacts of a specific type on a backlog item."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.artifact_get(item_id=item_id, artifact_type=artifact_type, artifact_id=artifact_id)
    _output_json(result)


@app.command(name="artifact-read")
def artifact_read_cmd(
    item_id: Annotated[int, typer.Argument(help="Backlog item identifier (GitHub issue number)")],
    artifact_type: Annotated[str, typer.Option("--type", help="Artifact type to read")],
    artifact_id: Annotated[str | None, typer.Option("--artifact-id", help="Specific artifact ID")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Read the file content for an artifact on a backlog item."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.artifact_read(item_id=item_id, artifact_type=artifact_type, artifact_id=artifact_id)
    _output_json(result)


@app.command(name="artifact-migrate")
def artifact_migrate_cmd(
    item_id: Annotated[int | None, typer.Option("--item-id", help="Migrate for a specific item only")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without making API calls")] = False,
    old_artifact_id: Annotated[
        str | None, typer.Option("--old-id", help="Old artifact ID for single-item rename")
    ] = None,
    new_artifact_id: Annotated[
        str | None, typer.Option("--new-id", help="New artifact ID for single-item rename")
    ] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json")] = "json",
) -> None:
    """Migrate plan/research artifacts into the artifact manifest system."""
    if output_format != "json":
        _err(f"Invalid format '{output_format}'. Must be one of: json")
    result = operations.artifact_migrate(
        item_id=item_id, dry_run=dry_run, old_artifact_id=old_artifact_id, new_artifact_id=new_artifact_id
    )
    _output_json(result)


# Active-task commands live in cli_active_task.py (file-size budget).
app.add_typer(cli_active_task.app, name="active-task")


if __name__ == "__main__":  # pragma: no cover
    app()
