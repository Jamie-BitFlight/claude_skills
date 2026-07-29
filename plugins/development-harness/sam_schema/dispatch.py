"""Provider-neutral dispatch command group."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Literal, TypeGuard

import typer
from dh_core import operations
from dispatch_schema import DispatchPlan, ItemPriority, MilestoneHeader, QualityGates, Wave, WaveItem
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sam_schema.cli_output import err, output_json

app = typer.Typer(help="Dispatch workflow operations.", no_args_is_help=True)


class _PlanWaveItemInput(BaseModel):
    """Strict, non-JSON command-line representation of a plan wave item."""

    model_config = ConfigDict(extra="forbid")

    wave: int | None = Field(default=None, ge=1)
    issue: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    priority: ItemPriority = ItemPriority.P1
    conflict_group: int | None = Field(default=None, ge=1)
    depends_on: list[int] = Field(default_factory=list)


class _WaveStartItemInput(BaseModel):
    """Strict command-line representation of a wave-start item."""

    model_config = ConfigDict(extra="forbid")

    issue: int = Field(..., ge=1)
    title: str | None = Field(default=None, min_length=1)


def _parse_plan_item(value: str) -> _PlanWaveItemInput:
    """Parse ``key=value`` item fields and validate every field strictly.

    Returns:
        A validated plan wave-item input model.
    """
    fields: dict[str, object] = {}
    for part in value.split(";"):
        key, separator, raw = part.partition("=")
        if not separator or not key or not raw:
            raise ValueError("items use key=value fields separated by ';'")
        if key in fields:
            raise ValueError(f"duplicate item field: {key}")
        if key in {"wave", "issue", "conflict_group"}:
            fields[key] = int(raw)
        elif key == "depends_on":
            fields[key] = [int(item) for item in raw.split(",") if item]
        elif key in {"title", "priority"}:
            fields[key] = raw
        else:
            raise ValueError(f"unknown item field: {key}")
    item = _PlanWaveItemInput.model_validate(fields)
    if item.wave is None:
        raise ValueError("wave item requires a wave field")
    return item


def _parse_wave_start_item(value: str) -> _WaveStartItemInput:
    """Parse and strictly validate an issue/title wave-start item.

    Returns:
        A validated wave-start item input model.
    """
    fields: dict[str, object] = {}
    for part in value.split(";"):
        key, separator, raw = part.partition("=")
        if not separator or not key or not raw:
            raise ValueError("items use key=value fields separated by ';'")
        if key in fields:
            raise ValueError(f"duplicate item field: {key}")
        if key == "issue":
            fields[key] = int(raw)
        elif key == "title":
            fields[key] = raw
        else:
            raise ValueError(f"unknown item field: {key}")
    return _WaveStartItemInput.model_validate(fields)


def _group_plan_items(values: list[str]) -> dict[int, list[WaveItem]]:
    """Parse and group plan items by their wave number.

    Returns:
        Wave items grouped by validated wave number.
    """
    grouped: dict[int, list[WaveItem]] = defaultdict(list)
    for item in (_parse_plan_item(value) for value in values):
        wave_number = item.wave
        if wave_number is None:
            raise ValueError("wave item requires a wave field")
        grouped[wave_number].append(
            WaveItem(
                title=item.title,
                issue=item.issue,
                priority=item.priority,
                conflict_group=item.conflict_group,
                depends_on=item.depends_on,
            )
        )
    return grouped


def _is_result_mapping(value: object) -> TypeGuard[dict[str, object]]:
    """Narrow an operation result to its JSON mapping shape.

    Returns:
        Whether ``value`` is a string-keyed result mapping.
    """
    return isinstance(value, dict)


def _emit(result: object) -> None:
    """Emit operation results, keeping diagnostics off stdout."""
    if _is_result_mapping(result) and "error" in result:
        err(str(result["error"]))
    if _is_result_mapping(result):
        for key in ("messages", "warnings", "errors"):
            values = result.get(key, [])
            if isinstance(values, list):
                for value in values:
                    typer.echo(str(value), err=True)
    output_json(result)


@app.command("read")
def read(milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)]) -> None:
    """Read a dispatch plan."""
    _emit(operations.dispatch_read_plan(milestone_number=milestone_number))


@app.command("validate")
def validate(milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)]) -> None:
    """Validate a dispatch plan's structure."""
    _emit(operations.dispatch_validate_plan(milestone_number=milestone_number))


@app.command("create-plan")
def create_plan(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    milestone_title: Annotated[str, typer.Option("--milestone-title")],
    integration_branch: Annotated[str, typer.Option("--integration-branch")],
    wave_item: Annotated[list[str], typer.Option("--wave-item", help="wave=1;issue=2;title=...;priority=P1")],
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    validate_after_write: Annotated[bool, typer.Option("--validate/--no-validate")] = True,
) -> None:
    """Create a dispatch plan from strictly validated named fields."""
    try:
        grouped = _group_plan_items(wave_item)
        plan = DispatchPlan(
            milestone=MilestoneHeader(
                number=milestone_number, title=milestone_title, integration_branch=integration_branch
            ),
            waves=[Wave(wave=number, items=items) for number, items in sorted(grouped.items())],
            quality_gates=QualityGates(),
        )
    except (ValidationError, ValueError) as exc:
        err(f"Invalid dispatch plan input: {exc}")
    _emit(
        operations.dispatch_create_plan(
            milestone_number=milestone_number,
            plan=plan.model_dump(mode="json", by_alias=True),
            overwrite=overwrite,
            validate=validate_after_write,
        )
    )


@app.command("wave-start")
def wave_start(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    wave_number: Annotated[int, typer.Option("--wave-number", min=1)],
    item: Annotated[list[str], typer.Option("--item", help="issue=2;title=...")],
) -> None:
    """Record the start of a dispatch wave."""
    try:
        items = [
            _parse_wave_start_item(value).model_dump(include={"issue", "title"}, exclude_none=True) for value in item
        ]
    except (ValidationError, ValueError) as exc:
        err(f"Invalid wave item: {exc}")
    _emit(operations.dispatch_wave_start(milestone=milestone_number, wave_num=wave_number, items=items))


@app.command("item-status")
def item_status(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    issue_number: Annotated[int, typer.Option("--issue-number", min=1)],
    status: Annotated[Literal["complete", "failed", "skipped"], typer.Option("--status")],
    result: Annotated[str, typer.Option("--result")] = "",
    error: Annotated[str, typer.Option("--error")] = "",
    cost: Annotated[float | None, typer.Option("--cost")] = None,
) -> None:
    """Record completion or failure of a dispatch item."""
    _emit(
        operations.dispatch_item_status(
            milestone=milestone_number, issue=issue_number, status=status, result=result, error=error, cost=cost
        )
    )


@app.command("wave-status")
def wave_status(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    wave_number: Annotated[int, typer.Option("--wave-number", min=1)],
) -> None:
    """Query dispatch wave status."""
    _emit(operations.dispatch_wave_status(milestone=milestone_number, wave_num=wave_number))


@app.command("spawn")
def spawn(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    wave_number: Annotated[int, typer.Option("--wave-number", min=1)],
    max_concurrent: Annotated[int, typer.Option("--max-concurrent", min=1)] = 3,
    model: Annotated[str, typer.Option("--model")] = "sonnet",
    phase: Annotated[Literal["groom", "work"], typer.Option("--phase")] = "work",
    effort: Annotated[Literal["low", "medium", "high", "max"] | None, typer.Option("--effort")] = None,
) -> None:
    """Spawn and monitor sessions for a dispatch wave."""
    _emit(
        operations.dispatch_spawn(
            milestone=milestone_number,
            wave_num=wave_number,
            max_concurrent=max_concurrent,
            model=model,
            phase=phase,
            effort=effort,
        )
    )


__all__ = ["app"]
