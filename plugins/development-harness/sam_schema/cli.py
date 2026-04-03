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
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML, YAMLError

from sam_schema.core.addressing import AddressingError, parse_address, resolve_plan_address
from sam_schema.core.models import PlanStatus, TaskStatus
from sam_schema.core.query import (
    claim_task,
    create_plan,
    get_plan_status,
    get_ready_tasks,
    get_task,
    get_task_assignment,
    load_plan,
    update_plan_fields,
    update_status,
)
from sam_schema.readers.detect import FormatDetectionError
from sam_schema.writers.yaml_writer import write_plan

_PLAN_LOAD_ERRORS: tuple[type[Exception], ...] = (FileNotFoundError, FormatDetectionError, ValueError, TypeError)

_SYNC_ERRORS: tuple[type[Exception], ...]
try:
    from backlog_core.models import BacklogError
    from backlog_core.operations import sync_items as _sync_backlog

    _BACKLOG_CORE_AVAILABLE = True
    _SYNC_ERRORS = (BacklogError, OSError, ValueError)
except ImportError:
    _BACKLOG_CORE_AVAILABLE = False
    _SYNC_ERRORS = (OSError, ValueError)

app = typer.Typer(name="sam", help="SAM task/plan file interface.", no_args_is_help=True)

_OUTPUT_FORMATS = ("json", "yaml", "rich")


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

    Args:
        msg: Human-readable error message.
        exit_code: Process exit code (1 for user errors, 2 for internal errors).
    """
    typer.echo(f"Error: {msg}", err=True)
    raise typer.Exit(exit_code)


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


def _get_plan_status_for_address(plan_address: str, plan_dir: Path) -> PlanStatus:
    """Resolve ``plan_address`` to a path and return its plan status.

    Accepts either a direct filesystem path (e.g. ``plan/tasks-696-slug.md``)
    or a structured plan address (e.g. ``P696``, ``auth-system``).  Direct paths
    are detected by checking whether the argument exists on disk before falling
    back to address parsing.

    Args:
        plan_address: Plan address string or filesystem path.
        plan_dir: Directory to search when resolving structured addresses.

    Returns:
        ``PlanStatus`` for the resolved plan.

    Raises:
        SystemExit(1): If the path or address cannot be resolved.
        SystemExit(2): If the format cannot be detected.
    """
    direct = Path(plan_address)
    if direct.exists() and (direct.is_file() or direct.is_dir()):
        plan_path: Path = direct
    else:
        try:
            plan_ref, _ = parse_address(plan_address)
        except ValueError as exc:
            _err(str(exc))
        plan_path = _resolve_plan(plan_ref, plan_dir)

    try:
        return get_plan_status(plan_path)
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)


def _output_json(data: object) -> None:
    """Print ``data`` as formatted JSON to stdout.

    Args:
        data: Any JSON-serializable object.
    """
    typer.echo(json.dumps(data, indent=2, default=str))


def _output_yaml(data: object) -> None:
    """Print ``data`` as YAML to stdout.

    Args:
        data: Any YAML-serializable object.
    """
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
        status_data: PlanStatus dict from ``model_dump(mode="json")``.
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


def _read_plan_only(plan_path: Path, output_format: str) -> None:
    """Read a plan-only address and emit its fields.

    Args:
        plan_path: Resolved path to the plan file or directory.
        output_format: One of ``json``, ``yaml``, ``rich``.
    """
    try:
        result = load_plan(plan_path)
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    data = result.plan.model_dump(mode="json", by_alias=True, exclude_none=True)
    if output_format == "json":
        _output_json(data)
    elif output_format == "yaml":
        _output_yaml(data)
    else:
        _output_rich_task(data)


def _read_task_assignment(plan_path: Path, task_id: str, output_format: str) -> None:
    """Read a task address and emit a ``TaskAssignment`` response.

    Args:
        plan_path: Resolved path to the plan file or directory.
        task_id: Normalised task ID (e.g. ``"T3"``).
        output_format: One of ``json``, ``yaml``, ``rich``.
    """
    try:
        assignment = get_task_assignment(plan_path, task_id)
    except FileNotFoundError as exc:
        _err(str(exc))
    except KeyError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    data = assignment.model_dump(mode="json", by_alias=True, exclude_none=True)
    if output_format == "json":
        _output_json(data)
    elif output_format == "yaml":
        _output_yaml(data)
    else:
        console = Console()
        if assignment.plan_goal:
            console.print(f"[bold cyan]Plan goal:[/bold cyan] {assignment.plan_goal}")
        if assignment.plan_context:
            console.print(f"[bold cyan]Plan context:[/bold cyan] {assignment.plan_context}")
        _output_rich_task(data.get("task", data))


@app.command(name="list")
def list_plans(
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    search: Annotated[str | None, typer.Option("--search", help="Case-insensitive substring filter")] = None,
    offset: Annotated[int, typer.Option("--offset", help="Zero-based index of first item to return")] = 0,
    limit: Annotated[int | None, typer.Option("--limit", help="Maximum number of items to return")] = None,
    output_format: Annotated[str, typer.Option("--format", help="Output format: json|yaml")] = "json",
) -> None:
    """List all plans in plan_dir with optional search filtering.

    Reads every plan file found in ``plan_dir``, applies optional search
    filtering across ``feature``, ``description``, and ``goal`` fields
    (case-insensitive), then returns a page of results.

    Output (JSON)::

        {"items": [{"feature": "auth-system", "goal": "...", "task_count": 3, "path": "..."}], "count": 1, "total": 1}

    Args:
        plan_dir: Directory to scan for plan files.
        search: Optional substring to filter results by. Matched case-insensitively
                against ``feature``, ``description``, and ``goal`` fields.
        offset: Zero-based start index into the filtered result list.
        limit: Maximum number of items to return. Defaults to all results.
        output_format: Output serialization format (json or yaml).
    """
    plan_dir = _coerce_plan_dir(plan_dir)
    if output_format not in _OUTPUT_FORMATS:
        _err(f"Invalid format '{output_format}'. Must be one of: {', '.join(_OUTPUT_FORMATS)}")

    if not plan_dir.exists():
        _err(f"Plan directory does not exist: {plan_dir}")

    candidates: list[Path] = sorted(c for c in plan_dir.iterdir() if c.suffix in {".yaml", ".md"} or c.is_dir())

    all_items: list[dict[str, object]] = []
    for candidate in candidates:
        try:
            read_result = load_plan(candidate)
            plan = read_result.plan
            summary: dict[str, object] = {
                "feature": plan.feature,
                "goal": plan.goal,
                "description": plan.description,
                "task_count": len(plan.tasks),
                "path": str(plan.source_path or candidate),
            }
            if search is None or _plan_summary_matches(summary, search):
                all_items.append(summary)
        except _PLAN_LOAD_ERRORS as exc:
            typer.echo(f"Warning: skipping {candidate.name}: {exc}", err=True)

    total = len(all_items)
    page = all_items[offset:] if limit is None else all_items[offset : offset + limit]
    result: dict[str, object] = {"items": page, "count": len(page), "total": total}

    if output_format == "yaml":
        _output_yaml(result)
    else:
        _output_json(result)


def _plan_summary_matches(summary: dict[str, object], search: str) -> bool:
    """Return ``True`` if any searchable field in ``summary`` contains ``search``.

    Matches case-insensitively against ``feature``, ``description``, and ``goal``.

    Args:
        summary: Plan summary dict with ``feature``, ``description``, ``goal`` keys.
        search: Substring to search for.

    Returns:
        ``True`` if any field matches.
    """
    needle = search.lower()
    for field in ("feature", "description", "goal"):
        val = summary.get(field)
        if val is not None and needle in str(val).lower():
            return True
    return False


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

    plan_path = _resolve_plan(plan_ref, plan_dir)

    if task_ref is None:
        _read_plan_only(plan_path, output_format)
        return

    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref
    _read_task_assignment(plan_path, task_id, output_format)


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

    plan_path = _resolve_plan(plan_ref, plan_dir)
    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref

    try:
        old_task = get_task(plan_path, task_id)
    except FileNotFoundError as exc:
        _err(str(exc))
    except KeyError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    old_status = old_task.status

    try:
        updated_task = update_status(plan_path, task_id, parsed_status)
    except FileNotFoundError as exc:
        _err(str(exc))
    except (KeyError, ValueError) as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    typer.echo(f"Task {task_id}: {old_status} -> {updated_task.status}")


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

    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    plan_path = _resolve_plan(plan_ref, plan_dir)

    try:
        tasks = get_ready_tasks(plan_path)
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    data = [t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in tasks]
    if output_format == "yaml":
        _output_yaml(data)
    else:
        _output_json(data)


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
        for candidate in sorted(plan_dir.iterdir()):
            if not (candidate.suffix in {".yaml", ".md"} or candidate.is_dir()):
                continue
            try:
                ps = get_plan_status(candidate)
                entry = ps.model_dump(mode="json")
                entry["path"] = str(candidate)
                results.append(entry)
            except _PLAN_LOAD_ERRORS as exc:
                # Skip unreadable plan files when listing all; emit to stderr
                typer.echo(f"Warning: skipping {candidate}: {exc}", err=True)
                continue
        _output_json(results)
        return

    if plan_address is None:
        _err("Provide a plan address or use --all to list every plan")

    plan_status = _get_plan_status_for_address(plan_address, plan_dir)

    data = plan_status.model_dump(mode="json")

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

        {"path": "plan/P001-auth-system.yaml", "plan_number": 1, "task_count": 3}

    Args:
        slug: Short slug identifier for the plan.
        goal: Goal statement written to the plan file.
        plan_dir: Directory where the plan file will be created.
        context: Optional plan-level context string.
        issue: Optional GitHub issue number.
        from_stdin: If ``True``, read task YAML from stdin.
        output_format: Output format (only ``json`` is supported).
    """
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

    try:
        plan = create_plan(slug=slug, goal=goal, tasks=tasks, plan_dir=plan_dir, context=context, issue=issue)
    except ValueError as exc:
        _err(str(exc))
    except OSError as exc:
        _err(str(exc), exit_code=2)

    source_path = plan.source_path
    path_str = str(source_path) if source_path is not None else str(plan_dir)
    # Extract numeric plan number from written path stem
    plan_number: int | None = None
    if source_path is not None:
        m = re.match(r"^P(\d+)-", source_path.name)
        if m:
            plan_number = int(m.group(1))

    result: dict[str, object] = {"path": path_str, "plan_number": plan_number, "task_count": len(plan.tasks)}
    _output_json(result)


@app.command()
def update(
    address: Annotated[str, typer.Argument(help="Plan address (P{N}) or task address (P{N}/T{M})")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir", help="Plan directory")] = None,
    set_field: Annotated[list[str], typer.Option("--set", help="field=value pairs to update")] = [],  # noqa: B006
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
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    plan_path = _resolve_plan(plan_ref, plan_dir)
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

    try:
        update_plan_fields(
            plan_path,
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
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    if task_ref is None:
        _err(f"Address '{address}' does not include a task component (expected P{{N}}/T{{M}})")

    plan_path = _resolve_plan(plan_ref, plan_dir)
    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref

    try:
        updated_task = claim_task(plan_path, task_id)
    except FileNotFoundError as exc:
        _err(str(exc))
    except KeyError as exc:
        _err(str(exc))
    except ValueError as exc:
        # Already claimed or in non-claimable state — exit non-zero
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    started_val = updated_task.started
    started_str = started_val.isoformat() if started_val is not None else None
    _output_json({"claimed": True, "task_id": task_id, "started": started_str})


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
    plan_dir = _coerce_plan_dir(plan_dir)
    try:
        plan_ref, _ = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    plan_path = _resolve_plan(plan_ref, plan_dir)

    try:
        result = load_plan(plan_path)
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
    _output_json({"valid": valid, "errors": errors, "warnings": warnings})

    if not valid:
        raise typer.Exit(1)


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

    Attempts canonical load via ``load_plan``.  If the loader raises any
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
    try:
        result = load_plan(plan_path)
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
        if len(parts) < 3:  # noqa: PLR2004
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

    uv_exe = shutil.which("uv")
    if uv_exe is None:
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


if __name__ == "__main__":  # pragma: no cover
    app()
