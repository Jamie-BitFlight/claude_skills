"""Provider-neutral dispatch command group."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Literal

import typer
from dh_core import operations
from dispatch_schema import (
    ConflictGroup,
    DispatchPlan,
    ItemPriority,
    ItemStatus,
    MilestoneHeader,
    QualityGates,
    Wave,
    WaveItem,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sam_schema.cli_output import emit_result, err

app = typer.Typer(help="Dispatch workflow operations.", no_args_is_help=True, rich_markup_mode=None)


class _PlanWaveItemInput(BaseModel):
    """Strict, non-JSON command-line representation of a plan wave item."""

    model_config = ConfigDict(extra="forbid")

    wave: int | None = Field(default=None, ge=1)
    issue: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    priority: ItemPriority = ItemPriority.P1
    conflict_group: int | None = Field(default=None, ge=1)
    depends_on: list[Annotated[int, Field(ge=1)]] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.PENDING
    parallel: bool | None = None


class _ConflictGroupInput(BaseModel):
    """Strict command-line representation of a conflict group."""

    model_config = ConfigDict(extra="forbid")

    group_id: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1)
    items: list[str] = Field(..., min_length=2)


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
        elif key in {"title", "priority", "status"}:
            fields[key] = raw
        elif key == "parallel":
            if raw.lower() not in {"true", "false"}:
                raise ValueError("parallel must be true or false")
            fields[key] = raw.lower() == "true"
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


def _parse_conflict_group(value: str) -> _ConflictGroupInput:
    """Parse and strictly validate one conflict group.

    Returns:
        A validated conflict-group input model.
    """
    fields: dict[str, object] = {}
    for part in value.split(";"):
        key, separator, raw = part.partition("=")
        if not separator or not key or not raw:
            if key == "items" and separator:
                raise ValueError("conflict groups field items must not be empty")
            raise ValueError("conflict groups use key=value fields separated by ';'")
        if key in fields:
            raise ValueError(f"duplicate conflict-group field: {key}")
        if key == "group_id":
            fields[key] = int(raw)
        elif key == "items":
            fields[key] = raw.split(",")
        elif key == "reason":
            fields[key] = raw
        else:
            raise ValueError(f"unknown conflict-group field: {key}")
    return _ConflictGroupInput.model_validate(fields)


def _group_plan_items(values: list[str]) -> tuple[dict[int, list[WaveItem]], dict[int, bool]]:
    """Parse and group plan items by their wave number.

    Returns:
        Wave items grouped by validated wave number.
    """
    grouped: dict[int, list[WaveItem]] = defaultdict(list)
    parallel: dict[int, bool] = {}
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
                status=item.status,
            )
        )
        if item.parallel is not None:
            previous = parallel.setdefault(wave_number, item.parallel)
            if previous != item.parallel:
                raise ValueError(f"wave {wave_number} has inconsistent parallel values")
    return grouped, parallel


@app.command("read")
def read(milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)]) -> None:
    """Read a dispatch plan."""
    emit_result(operations.dispatch_read_plan(milestone_number=milestone_number))


@app.command("validate")
def validate(milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)]) -> None:
    """Validate a dispatch plan's structure."""
    emit_result(operations.dispatch_validate_plan(milestone_number=milestone_number))


@app.command("create-plan")
def create_plan(
    milestone_number: Annotated[int, typer.Option("--milestone-number", min=1)],
    milestone_title: Annotated[str, typer.Option("--milestone-title")],
    integration_branch: Annotated[str, typer.Option("--integration-branch")],
    wave_item: Annotated[list[str], typer.Option("--wave-item", help="wave=1;issue=2;title=...;priority=P1")],
    conflict_group: Annotated[
        list[str] | None, typer.Option("--conflict-group", help="group_id=1;reason=...;items=101,102")
    ] = None,
    pre_merge: Annotated[list[str] | None, typer.Option("--pre-merge")] = None,
    post_merge: Annotated[list[str] | None, typer.Option("--post-merge")] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    validate_after_write: Annotated[bool, typer.Option("--validate/--no-validate")] = True,
) -> None:
    """Create a dispatch plan from strictly validated named fields."""
    if not integration_branch:
        err("Invalid dispatch plan input: integration branch must not be empty")
    groups_input = conflict_group or []
    pre_merge_input = pre_merge or []
    post_merge_input = post_merge or []
    try:
        grouped, parallel = _group_plan_items(wave_item)
        groups = [_parse_conflict_group(value) for value in groups_input]
        plan = DispatchPlan(
            milestone=MilestoneHeader(
                number=milestone_number, title=milestone_title, integration_branch=integration_branch
            ),
            conflict_groups=[ConflictGroup.model_validate(group.model_dump()) for group in groups],
            waves=[
                Wave(wave=number, parallel=parallel.get(number, True), items=items)
                for number, items in sorted(grouped.items())
            ],
            quality_gates=QualityGates(pre_merge=pre_merge_input, post_merge=post_merge_input),
        )
    except (ValidationError, ValueError) as exc:
        err(f"Invalid dispatch plan input: {exc}")
    emit_result(
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
    emit_result(operations.dispatch_wave_start(milestone=milestone_number, wave_num=wave_number, items=items))


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
    emit_result(
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
    emit_result(operations.dispatch_wave_status(milestone=milestone_number, wave_num=wave_number))


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
    emit_result(
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
