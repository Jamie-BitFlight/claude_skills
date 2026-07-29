"""Grouped Typer commands for provider-neutral SAM plan operations."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, NoReturn

import dh_paths
import typer
from backlog_core.models import Output
from dh_core import operations
from pydantic import ValidationError
from ruamel.yaml import YAML, YAMLError

from sam_schema import cli_output
from sam_schema.cli_inputs import (
    AppendTaskInput,
    CreatePlanInput,
    PlanUpdateFields,
    PlanUpdateInput,
    TaskUpdateFields,
    TaskUpdateInput,
)
from sam_schema.core.action_models import TaskDefinition
from sam_schema.core.addressing import AddressingError, parse_address, resolve_plan_address
from sam_schema.core.backends.local_yaml import plan_id_from_path
from sam_schema.core.exceptions import PlanNotFoundError, TaskNotFoundError
from sam_schema.core.models import Complexity, CreatePlanError, PlanState, Priority, TaskStatus
from sam_schema.core.task_config import get_backend
from sam_schema.readers.detect import FormatDetectionError
from sam_schema.writers.yaml_writer import write_plan

_PLAN_LOAD_ERRORS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    FormatDetectionError,
    ValueError,
    TypeError,
    PlanNotFoundError,
)
_YAML_FRONTMATTER_PARTS = 3

_SYNC_ERRORS: tuple[type[Exception], ...]
try:
    from backlog_core.models import BacklogError
    from backlog_core.operations import sync_items as _sync_backlog

    _BACKLOG_CORE_AVAILABLE = True
    _SYNC_ERRORS = (BacklogError, OSError, ValueError)
except ImportError:
    _BACKLOG_CORE_AVAILABLE = False
    _SYNC_ERRORS = (OSError, ValueError)

if TYPE_CHECKING:
    from dh_core.protocols import TaskBackend

app = typer.Typer(name="plan", help="SAM plan and task operations.", no_args_is_help=True)


def _plan_dir(value: Path | None) -> Path:
    return dh_paths.plan_dir() if value is None else value


def _error(message: str, code: int = 1) -> NoReturn:
    cli_output.err(message, code)


def _emit(value: object) -> None:
    cli_output.output_json(value)


def _address(value: str) -> tuple[str, str | None]:
    try:
        return parse_address(value)
    except ValueError as exc:
        _error(str(exc))
        raise AssertionError from exc


def _backend(plan_dir: Path) -> TaskBackend:
    return get_backend(str(plan_dir))


def _task_options(
    task_id: str | None,
    title: str | None,
    status: TaskStatus | None,
    agent: str | None,
    dependencies: list[str] | None,
    priority: int | None,
    complexity: str | None,
) -> TaskDefinition | None:
    if task_id is None and title is None:
        return None
    if task_id is None or title is None:
        _error("--task-id and --task-title must be provided together")
    values: dict[str, object] = {"id": task_id, "title": title}
    if status is not None:
        values["status"] = status
    if agent is not None:
        values["agent"] = agent
    if dependencies is not None:
        values["dependencies"] = dependencies
    if priority is not None:
        values["priority"] = priority
    if complexity is not None:
        values["complexity"] = complexity
    try:
        return TaskDefinition.model_validate(values)
    except ValidationError as exc:
        _error(str(exc))
        raise AssertionError from exc


@app.command("list")
def list_plans(
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
    search: Annotated[str | None, typer.Option("--search")] = None,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = None,
    filters: Annotated[list[str] | None, typer.Option("--filter")] = None,
) -> None:
    """List plans as a compact JSON envelope."""
    directory = _plan_dir(plan_dir)
    if not directory.exists():
        _error(f"Plan directory does not exist: {directory}")
    filter_by_key: dict[str, str] | None = None
    if filters:
        filter_by_key = {}
        for item in filters:
            key, separator, value = item.partition("=")
            if not separator or not key:
                _error(f"--filter expects 'key=value', got: {item!r}")
            filter_by_key[key] = value
    result = operations.list_plans(
        _backend(directory), search=search, offset=offset, limit=limit, filter_by_key=filter_by_key
    )
    _emit({
        "items": [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in result],
        "count": len(result),
        "total": len(result),
    })


@app.command("read")
def read(
    address: Annotated[str, typer.Option("--address")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Read a plan or task by address."""
    plan_ref, task_ref = _address(address)
    backend = _backend(_plan_dir(plan_dir))
    try:
        if task_ref is None:
            _emit(operations.read_plan(backend, plan_ref))
        else:
            task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref
            _emit(operations.read_task(backend, plan_ref, task_id))
    except (PlanNotFoundError, TaskNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("state")
def state(
    address: Annotated[str, typer.Option("--address")],
    new_status: Annotated[TaskStatus, typer.Option("--new-status")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Update a task status and return the typed operation result."""
    plan_ref, task_ref = _address(address)
    if task_ref is None:
        _error(f"Address '{address}' does not include a task component")
    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref
    backend = _backend(_plan_dir(plan_dir))
    try:
        result = operations.update_task_status(backend, plan_ref, task_id, new_status)
    except (PlanNotFoundError, TaskNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit(result)


@app.command("ready")
def ready(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    full: Annotated[bool, typer.Option("--full")] = False,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """List tasks ready for dispatch."""
    plan_ref, task_ref = _address(plan_address)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        _emit(operations.get_ready_tasks(_backend(_plan_dir(plan_dir)), plan_ref, full=full))
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("status")
def status(
    plan_address: Annotated[str | None, typer.Option("--plan-address")] = None,
    all_plans: Annotated[bool, typer.Option("--all")] = False,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Show plan progress status."""
    directory = _plan_dir(plan_dir)
    backend = _backend(directory)
    if all_plans:
        if not directory.exists():
            _error(f"Plan directory does not exist: {directory}")
        results: list[dict[str, object]] = []
        for candidate in sorted(directory.iterdir()):
            if candidate.suffix not in {".yaml", ".md"} and not candidate.is_dir():
                continue
            try:
                entry = operations.get_plan_status(backend, plan_id_from_path(candidate)).model_dump(mode="json")
                entry["path"] = str(candidate)
                results.append(entry)
            except (PlanNotFoundError, FileNotFoundError, FormatDetectionError, ValueError) as exc:
                typer.echo(f"Warning: skipping {candidate}: {exc}", err=True)
        _emit(results)
        return
    if plan_address is None:
        _error("Provide --plan-address or --all")
    plan_ref, task_ref = _address(plan_address)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        _emit(operations.get_plan_status(backend, plan_ref))
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("create")
def create(
    slug: Annotated[str, typer.Option("--slug")],
    goal: Annotated[str, typer.Option("--goal")],
    context: Annotated[str | None, typer.Option("--context")] = None,
    issue: Annotated[int | None, typer.Option("--issue", min=1)] = None,
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
    task_title: Annotated[str | None, typer.Option("--task-title")] = None,
    task_status: Annotated[TaskStatus | None, typer.Option("--task-status")] = None,
    task_agent: Annotated[str | None, typer.Option("--task-agent")] = None,
    task_dependencies: Annotated[list[str] | None, typer.Option("--task-dependency")] = None,
    task_priority: Annotated[int | None, typer.Option("--task-priority", min=1, max=5)] = None,
    task_complexity: Annotated[Complexity | None, typer.Option("--task-complexity")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Create a plan using named typed options only."""
    task = _task_options(
        task_id, task_title, task_status, task_agent, task_dependencies, task_priority, task_complexity
    )
    try:
        config = CreatePlanInput(
            slug=slug, goal=goal, tasks=[] if task is None else [task], context=context, issue=issue
        )
        result = operations.create_plan(
            _backend(_plan_dir(plan_dir)), **config.to_config().model_dump(exclude={"action"})
        )
    except (ValidationError, ValueError, OSError) as exc:
        _error(str(exc))
    if isinstance(result, CreatePlanError):
        _error(result.error, 2)
    _emit(result)


@app.command("update")
def update(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
    context: Annotated[str | None, typer.Option("--context")] = None,
    feature: Annotated[str | None, typer.Option("--feature")] = None,
    version: Annotated[str | None, typer.Option("--version")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    state_value: Annotated[PlanState | None, typer.Option("--state")] = None,
    goal: Annotated[str | None, typer.Option("--goal")] = None,
    issue: Annotated[str | None, typer.Option("--issue")] = None,
    autonomy: Annotated[Literal["full_auto", "checkpoint", "per_task"] | None, typer.Option("--autonomy")] = None,
    title: Annotated[str | None, typer.Option("--title")] = None,
    task_status: Annotated[TaskStatus | None, typer.Option("--task-status")] = None,
    agent: Annotated[str | None, typer.Option("--agent")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
    complexity: Annotated[Complexity | None, typer.Option("--complexity")] = None,
    dependency: Annotated[list[str] | None, typer.Option("--dependency")] = None,
    skill: Annotated[list[str] | None, typer.Option("--skill")] = None,
    append_section: Annotated[str | None, typer.Option("--append-section")] = None,
    section_content: Annotated[str | None, typer.Option("--section-content")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Update declared plan/task fields or append a task section."""
    plan_ref, task_ref = _address(plan_address)
    target_task = task_id or (f"T{task_ref}" if task_ref and task_ref.isdigit() else task_ref)
    if target_task:
        try:
            fields = TaskUpdateFields(
                title=title,
                status=task_status,
                agent=agent,
                priority=priority,
                complexity=complexity,
                dependencies=dependency,
                skills=skill,
            )
            request = TaskUpdateInput(
                plan_address=plan_ref,
                task_id=target_task,
                fields=fields,
                append_section=append_section,
                section_content=section_content,
            )
            values = request.fields.as_operation_fields()
        except ValidationError as exc:
            _error(str(exc))
    else:
        try:
            fields = PlanUpdateFields(
                feature=feature,
                version=version,
                description=description,
                state=state_value,
                goal=goal,
                context=context,
                issue=issue,
                autonomy=autonomy,
            )
            request = PlanUpdateInput(
                plan_address=plan_ref,
                fields=fields,
                append_section_name=append_section,
                section_content=section_content,
            )
            values = request.fields.as_operation_fields() if request.fields else None
        except ValidationError as exc:
            _error(str(exc))
    try:
        result = operations.update_plan_fields(
            _backend(_plan_dir(plan_dir)),
            plan_ref,
            context=None if target_task else context,
            set_fields=values,
            task_id=target_task,
            append_section_name=append_section,
            section_content=section_content,
        )
    except (ValidationError, ValueError, KeyError, FileNotFoundError, PlanNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit(result)


@app.command("claim")
def claim(
    address: Annotated[str, typer.Option("--address")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Claim a task by transitioning it to in-progress."""
    plan_ref, task_ref = _address(address)
    if task_ref is None:
        _error(f"Address '{address}' does not include a task component")
    task_id = f"T{task_ref}" if task_ref.isdigit() else task_ref
    try:
        _emit(operations.claim_task(_backend(_plan_dir(plan_dir)), plan_ref, task_id))
    except (PlanNotFoundError, TaskNotFoundError, FileNotFoundError, FormatDetectionError, ValueError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


@app.command("validate")
def validate(
    address: Annotated[str, typer.Option("--address")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Validate a plan against the canonical schema."""
    plan_ref, _ = _address(address)
    try:
        result = operations.read_plan(_backend(_plan_dir(plan_dir)), plan_ref)
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    errors: list[str] = []
    warnings: list[str] = []
    for gap in result.gaps:
        message = f"[{gap.task_id}] {gap.field_name}: {gap.gap_type} (expected: {gap.expected})"
        (errors if gap.gap_type in {"missing", "invalid_type", "invalid_value"} else warnings).append(message)
    _emit({"valid": not errors, "errors": errors, "warnings": warnings})
    if errors:
        raise typer.Exit(1)


@app.command("append-task")
def append_task(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    task_id: Annotated[str, typer.Option("--task-id")],
    task_title: Annotated[str, typer.Option("--task-title")],
    task_status: Annotated[TaskStatus | None, typer.Option("--task-status")] = None,
    task_agent: Annotated[str | None, typer.Option("--task-agent")] = None,
    task_dependencies: Annotated[list[str] | None, typer.Option("--task-dependency")] = None,
    task_priority: Annotated[int | None, typer.Option("--task-priority", min=1, max=5)] = None,
    task_complexity: Annotated[Complexity | None, typer.Option("--task-complexity")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Append one typed task to a drafting plan."""
    plan_ref, task_ref = _address(plan_address)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        task = _task_options(
            task_id, task_title, task_status, task_agent, task_dependencies, task_priority, task_complexity
        )
        if task is None:
            _error("--task-id and --task-title are required")
        config = AppendTaskInput(plan_address=plan_ref, task=task)
        result = operations.append_task(_backend(_plan_dir(plan_dir)), plan_ref, config.task)
    except (ValidationError, ValueError, PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit(result)


@app.command("finalize")
def finalize(
    plan_address: Annotated[str, typer.Option("--plan-address")],
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
) -> None:
    """Transition a drafting plan to ready state."""
    plan_ref, task_ref = _address(plan_address)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        _emit(operations.finalize_plan(_backend(_plan_dir(plan_dir)), plan_ref))
    except (PlanNotFoundError, FileNotFoundError, FormatDetectionError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)


def _canonical_output_path(plan_path: Path) -> Path:
    """Return the canonical YAML destination for a legacy plan path."""
    if plan_path.is_dir():
        return plan_path
    match = re.match(r"^tasks-(\d+)-(.+)\.md$", plan_path.name)
    if match:
        return plan_path.parent / f"P{int(match.group(1)):03d}-{match.group(2)}.yaml"
    return plan_path.with_suffix(".yaml")


def _extract_fallback_metadata(raw_content: str, plan_path: Path) -> tuple[int, str, str, int | None]:
    """Extract minimal metadata when a legacy plan cannot be parsed.

    Returns:
        Plan number, slug, goal, and optional issue number.
    """
    match = re.match(r"^tasks-(\d+)-(.+)\.md$", plan_path.name)
    number = int(match.group(1)) if match else 0
    slug = match.group(2) if match else plan_path.stem
    goal = slug.replace("-", " ").title()
    heading = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
    if heading:
        goal = heading.group(1).strip()
    issue_match = re.search(r"(?:\*\*Issue\*\*|^issue):\s*#?(\d+)", raw_content, re.MULTILINE)
    return number, slug, goal, int(issue_match.group(1)) if issue_match else None


def _migrate_one_fallback(plan_path: Path, dry_run: bool) -> tuple[Path | None, str]:
    """Preserve an unparseable legacy plan as canonical YAML.

    Returns:
        Written path (or ``None`` for dry runs) and source format.
    """
    output_path = _canonical_output_path(plan_path)
    if output_path != plan_path and output_path.exists():
        message = f"Skipping {plan_path.name}: target {output_path.name} already exists"
        typer.echo(message, err=True)
        if not dry_run:
            raise FileExistsError(message)
        return None, "fallback-preservation"
    raw_content = plan_path.read_text(encoding="utf-8", errors="replace")
    number, slug, goal, issue = _extract_fallback_metadata(raw_content, plan_path)
    if dry_run:
        typer.echo(f"Would migrate (fallback): {plan_path}", err=True)
        return None, "fallback-preservation"
    data: dict[str, object] = {
        "plan_number": number,
        "slug": slug,
        "goal": goal,
        "status": "complete",
        "tasks": [],
        "context": {"source_file": plan_path.name, "body": raw_content},
    }
    if issue is not None:
        data["issue"] = issue
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 2**31 - 1
    stream = io.StringIO()
    yaml.dump(data, stream)
    output_path.write_text(stream.getvalue(), encoding="utf-8")
    typer.echo(f"Migrated (fallback) {plan_path} -> {output_path}", err=True)
    return output_path, "fallback-preservation"


def _migrate_one(plan_path: Path, dry_run: bool) -> tuple[Path | None, str]:
    """Migrate one plan, falling back to content-preserving conversion.

    Returns:
        Written path (or ``None`` for dry runs) and source format.
    """
    plan_ref = plan_id_from_path(plan_path)
    try:
        result = operations.read_plan(_backend(plan_path.parent), plan_ref)
    except _PLAN_LOAD_ERRORS:
        return _migrate_one_fallback(plan_path, dry_run)
    output_path = _canonical_output_path(plan_path)
    if output_path != plan_path and output_path.exists():
        message = f"Skipping {plan_path.name}: target {output_path.name} already exists"
        typer.echo(message, err=True)
        if not dry_run:
            raise FileExistsError(message)
        return None, result.source_format
    if dry_run:
        typer.echo(f"Would migrate: {plan_path}", err=True)
        return None, result.source_format
    written = write_plan(result.plan, output_path)
    typer.echo(f"Migrated {plan_path} -> {written}", err=True)
    return written, result.source_format


def _update_backlog_refs(old_path: Path, new_path: Path, backlog_dir: Path) -> int:
    """Update matching plan references in backlog frontmatter.

    Returns:
        Number of references updated.
    """
    if not backlog_dir.exists():
        return 0
    updated = 0
    yaml = YAML()
    yaml.preserve_quotes = True
    for md_file in sorted(backlog_dir.glob("*.md")):
        try:
            raw = md_file.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            if not raw.startswith("---") or len(parts) < _YAML_FRONTMATTER_PARTS:
                continue
            frontmatter = yaml.load(parts[1])
            if not isinstance(frontmatter, dict) or str(frontmatter.get("plan", "")) != str(old_path):
                continue
            frontmatter["plan"] = str(new_path)
            stream = io.StringIO()
            yaml.dump(frontmatter, stream)
            md_file.write_text(f"---\n{stream.getvalue()}---{parts[2]}", encoding="utf-8")
            updated += 1
        except (OSError, YAMLError):
            continue
    return updated


def _attempt_backlog_sync() -> None:
    """Best-effort backlog sync before bulk migration."""
    if _BACKLOG_CORE_AVAILABLE:
        try:
            _sync_backlog()
        except _SYNC_ERRORS as exc:
            typer.echo(f"Warning: backlog sync failed; continuing. ({exc})", err=True)
        else:
            typer.echo("Backlog synced to GitHub.", err=True)
            return
    uv_exe = shutil.which("uv")
    if not uv_exe:
        typer.echo("Warning: backlog sync unavailable (uv not found).", err=True)
        return
    try:
        process = subprocess.run(
            [uv_exe, "run", "backlog", "sync"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        typer.echo(f"Warning: backlog sync unavailable: {exc}", err=True)
    else:
        if process.returncode:
            typer.echo(f"Warning: backlog sync failed (exit {process.returncode}): {process.stderr.strip()}", err=True)
        else:
            typer.echo("Backlog synced to GitHub.", err=True)


def _migrate_all(plan_dir: Path, dry_run: bool, skip_sync: bool, backlog_dir: Path) -> dict[str, object]:
    """Migrate every legacy plan in a directory and return a JSON summary.

    Returns:
        Compact-JSON-compatible migration summary.
    """
    if not plan_dir.exists():
        _error(f"Plan directory does not exist: {plan_dir}")
    candidates = sorted(p for p in plan_dir.iterdir() if p.suffix == ".md" and re.match(r"^tasks-\d+-", p.name))
    if not candidates:
        return {"migrated": 0, "candidates": 0, "backlog_refs_updated": 0, "dry_run": dry_run}
    if not skip_sync and not dry_run:
        _attempt_backlog_sync()
    migrated: list[tuple[Path, Path]] = []
    errors: list[str] = []
    for path in candidates:
        try:
            written, _ = _migrate_one(path, dry_run)
        except (*_PLAN_LOAD_ERRORS, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
            typer.echo(f"Error migrating {path.name}: {exc}", err=True)
        else:
            if written is not None:
                migrated.append((path, written))
    references = 0 if dry_run else sum(_update_backlog_refs(old, new, backlog_dir) for old, new in migrated)
    return {
        "migrated": len(migrated),
        "candidates": len(candidates),
        "backlog_refs_updated": references,
        "errors": errors,
        "dry_run": dry_run,
    }


@app.command("migrate")
def migrate(
    plan_address: Annotated[str | None, typer.Option("--plan-address")] = None,
    plan_dir: Annotated[Path | None, typer.Option("--plan-dir")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    all_plans: Annotated[bool, typer.Option("--all")] = False,
    skip_sync: Annotated[bool, typer.Option("--skip-sync")] = False,
    backlog_dir: Annotated[Path | None, typer.Option("--backlog-dir")] = None,
) -> None:
    """Migrate one legacy plan or all legacy plans to canonical YAML."""
    directory = _plan_dir(plan_dir)
    if all_plans:
        _emit(
            _migrate_all(directory, dry_run, skip_sync, dh_paths.backlog_dir() if backlog_dir is None else backlog_dir)
        )
        return
    if plan_address is None:
        _error("Provide --plan-address or use --all to migrate every plan")
    plan_ref, task_ref = _address(plan_address)
    if task_ref is not None:
        _error("--plan-address must identify a plan, not a task")
    try:
        path = resolve_plan_address(plan_ref, directory)
        written, source_format = _migrate_one(path, dry_run)
    except (AddressingError, FileNotFoundError, FormatDetectionError, ValueError, OSError) as exc:
        _error(str(exc), 2 if isinstance(exc, FormatDetectionError) else 1)
    _emit({
        "migrated": written is not None,
        "path": str(written or path),
        "source_format": source_format,
        "dry_run": dry_run,
    })


def _repeatable(values: list[str] | None, option_name: str, *, required: bool = False) -> list[str]:
    """Validate repeatable string options at the CLI boundary.

    Returns:
        The validated values, or an empty list when the option was omitted.
    """
    if values is None:
        if required:
            cli_output.err(f"{option_name} must be provided at least once")
        return []
    if any(not value.strip() for value in values):
        cli_output.err(f"{option_name} values must not be empty")
    return values


def _emit_sam_result(result: object, output: Output) -> None:
    """Emit operation data on stdout and collected diagnostics on stderr."""
    cli_output.output_json(result)
    for message in output.messages:
        typer.echo(message, err=True)
    for warning in output.warnings:
        typer.echo(warning, err=True)
    for error in output.errors:
        typer.echo(error, err=True)


@app.command("sam-task-create")
def sam_task_create(
    parent_issue_number: Annotated[int, typer.Option("--parent-issue-number", min=1)],
    task_id: Annotated[str, typer.Option("--task-id")],
    feature: Annotated[str, typer.Option("--feature")],
    task_type: Annotated[str, typer.Option("--task-type")],
    agent: Annotated[str, typer.Option("--agent")],
    priority: Annotated[int, typer.Option("--priority", min=1, max=5)],
    description: Annotated[str, typer.Option("--description")],
    skills: Annotated[list[str] | None, typer.Option("--skill")] = None,
    dependencies: Annotated[list[str] | None, typer.Option("--dependency")] = None,
    acceptance_criteria: Annotated[list[str] | None, typer.Option("--acceptance-criterion")] = None,
    labels: Annotated[list[str] | None, typer.Option("--label")] = None,
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """Create one SAM task under a parent issue."""
    output = Output()
    result = operations.create_sam_task(
        parent_issue_number=parent_issue_number,
        repo=repo,
        task_id=task_id,
        feature=feature,
        task_type=task_type,
        agent=agent,
        priority=priority,
        skills=_repeatable(skills, "--skill", required=True),
        dependencies=_repeatable(dependencies, "--dependency"),
        description=description,
        acceptance_criteria=_repeatable(acceptance_criteria, "--acceptance-criterion"),
        labels=_repeatable(labels, "--label"),
        output=output,
    )
    _emit_sam_result(result, output)


@app.command("sam-tasks")
def sam_tasks(
    parent_issue_number: Annotated[int, typer.Option("--parent-issue-number", min=1)],
    refresh_cache: Annotated[bool, typer.Option("--refresh-cache/--no-refresh-cache")] = True,
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """List SAM tasks under a parent issue."""
    output = Output()
    result = operations.get_sam_tasks(
        parent_issue_number=parent_issue_number, refresh_cache=refresh_cache, repo=repo, output=output
    )
    _emit_sam_result(result, output)


@app.command("sam-task-status")
def sam_task_status(
    issue_number: Annotated[int, typer.Option("--issue-number", min=1)],
    new_status: Annotated[str, typer.Option("--new-status")],
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """Update a SAM task status."""
    if not new_status.strip():
        cli_output.err("--new-status must not be empty")
    output = Output()
    result = operations.update_sam_task_status(
        issue_number=issue_number, new_status=new_status, repo=repo, output=output
    )
    _emit_sam_result(result, output)


@app.command("sam-ready-tasks")
def sam_ready_tasks(
    parent_issue_number: Annotated[int, typer.Option("--parent-issue-number", min=1)],
    repo: Annotated[str, typer.Option("--repo")] = "",
) -> None:
    """List SAM tasks ready to start."""
    output = Output()
    result = operations.get_ready_sam_tasks(parent_issue_number=parent_issue_number, repo=repo, output=output)
    _emit_sam_result(result, output)


__all__ = ["app"]

if __name__ == "__main__":
    app()

# ponytail: create exposes one explicit task; use append-task for additional tasks.
