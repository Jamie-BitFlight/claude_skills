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
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path
from typing import Annotated, NoReturn, cast

import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML

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

app = typer.Typer(name="sam", help="SAM task/plan file interface.", no_args_is_help=True)

_OUTPUT_FORMATS = ("json", "yaml", "rich")


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
    completion = status_data.get("completion_pct", 0.0)
    has_cycles = status_data.get("has_cycles", False)

    meta = Table(title=f"Plan: {feature}", show_header=False)
    meta.add_column("Field", style="cyan")
    meta.add_column("Value", style="green")
    meta.add_row("Total tasks", str(total))
    meta.add_row("Completion", f"{float(completion):.1f}%")  # type: ignore[arg-type]
    meta.add_row("Has cycles", str(has_cycles))
    console.print(meta)

    raw_by_status = status_data.get("by_status")
    by_status: dict[str, int] = raw_by_status if isinstance(raw_by_status, dict) else {}  # type: ignore[assignment]
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


@app.command()
def read(
    address: Annotated[str, typer.Argument(help="Plan address (P{N}) or task address (P{N}/T{M})")],
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
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
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
) -> None:
    """Update a task's status.

    Args:
        address: Task address in ``P{N}/T{M}`` format.
        new_status: New status string (e.g., ``complete``, ``in-progress``).
        plan_dir: Directory to search for plan files.
    """
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
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
) -> None:
    """List tasks ready for dispatch.

    Args:
        plan_address: Plan address in ``P{N}`` format.
        plan_dir: Directory to search for plan files.
    """
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
    _output_json(data)


@app.command()
def status(
    plan_address: Annotated[
        str | None, typer.Argument(help="Plan address: P{plan}. Omit with --all to list every plan.")
    ] = None,
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
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
            except Exception as exc:  # noqa: BLE001
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
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Directory to create the plan in")] = Path("plan"),
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
    tasks: list[dict[str, object]] = []

    if from_stdin:
        raw = sys.stdin.read()
        if raw.strip():
            y = YAML()
            parsed = y.load(raw)
            if isinstance(parsed, dict) and "tasks" in parsed:
                tasks = list(parsed["tasks"])
            elif isinstance(parsed, list):
                tasks = cast("list[dict[str, object]]", list(parsed))
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
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
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
    try:
        plan_ref, task_ref = parse_address(address)
    except ValueError as exc:
        _err(str(exc))

    plan_path = _resolve_plan(plan_ref, plan_dir)
    task_id = f"T{task_ref}" if task_ref is not None and task_ref.isdigit() else task_ref

    # Parse --set field=value pairs
    parsed_fields: dict[str, str] = {}
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
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
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
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
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
    except Exception as exc:  # noqa: BLE001
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


@app.command()
def migrate(
    plan_address: Annotated[str, typer.Argument(help="Plan address: P{plan}")],
    plan_dir: Annotated[Path, typer.Option("--plan-dir", help="Plan directory")] = Path("plan"),
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing")] = False,
) -> None:
    """Migrate a legacy or YAML-frontmatter plan to canonical pure-YAML format.

    Args:
        plan_address: Plan address in ``P{N}`` format.
        plan_dir: Directory to search for plan files.
        dry_run: If ``True``, print what would change without writing to disk.
    """
    try:
        plan_ref, _ = parse_address(plan_address)
    except ValueError as exc:
        _err(str(exc))

    plan_path = _resolve_plan(plan_ref, plan_dir)

    try:
        result = load_plan(plan_path)
    except FileNotFoundError as exc:
        _err(str(exc))
    except FormatDetectionError as exc:
        _err(str(exc), exit_code=2)

    source_format = result.source_format
    plan = result.plan

    # Determine output path: always write to .yaml extension alongside source
    output_path = plan_path if plan_path.is_dir() else plan_path.with_suffix(".yaml")

    if dry_run:
        typer.echo(f"Would migrate: {plan_path}")
        typer.echo(f"  Source format: {source_format}")
        typer.echo(f"  Output path:   {output_path}")
        typer.echo(f"  Tasks:         {len(plan.tasks)}")
        typer.echo(f"  Schema gaps:   {len(result.gaps)}")
        if result.gaps:
            for gap in result.gaps:
                typer.echo(f"    [{gap.task_id}] {gap.field_name}: {gap.gap_type}")
        return

    try:
        written = write_plan(plan, output_path)
    except (ValueError, OSError) as exc:
        _err(str(exc), exit_code=2)

    typer.echo(f"Migrated {plan_path} -> {written}")
    typer.echo(f"  Source format: {source_format}")
    typer.echo(f"  Tasks written: {len(plan.tasks)}")


if __name__ == "__main__":  # pragma: no cover
    app()
