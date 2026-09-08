"""Which store a ``sam plan`` command reads is decided by which flags were passed, not by their values.

``sam_schema.sam_plan.store_for`` picks between the work ledger and the pre-ledger content store
from the flags one invocation carried, and ``named`` reads "was this passed" off the value the
parser produced. That reading is only an answer while every optional flag of a routing command
defaults to a value no caller can supply. ``--offset`` was declared ``= 0``, so its own value chose
the store: ``plan list --offset 0`` read the ledger and ``plan list --offset 1`` read the content
store. These hold the mechanism to the invariant it depends on rather than to that one flag.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import pytest
import typer
from sam_schema import sam_plan


@pytest.mark.parametrize("offset", [0, 1, 7])
def test_the_offset_value_does_not_choose_the_store(offset: int) -> None:
    """Every passed ``--offset`` routes alike; the number is pagination, not a store selector."""
    assert sam_plan.named({"--offset": offset}) == ["--offset"]
    assert sam_plan.store_for("list", legacy={"--offset": offset}, spec={}) is sam_plan.Store.CONTENT


def test_an_omitted_offset_leaves_the_command_on_its_default_store() -> None:
    """``plan list`` with no flag at all still reads the ledger."""
    legacy = {"--plan-dir": None, "--search": None, "--offset": None, "--limit": None, "--filter": None}
    assert sam_plan.named(legacy) == []
    assert sam_plan.store_for("list", legacy=legacy, spec={}) is sam_plan.Store.LEDGER


@pytest.mark.parametrize("value", [None, False, [], ()])
def test_the_values_a_parser_leaves_for_an_omitted_flag_read_as_absent(value: object) -> None:
    """A value option, a switch and a repeatable option each have one absent value."""
    assert sam_plan.absent(value)


@pytest.mark.parametrize("value", [0, "", 0.0, True, "0", ["x"]])
def test_a_value_a_caller_could_pass_reads_as_passed(value: object) -> None:
    """``0`` equals both ``False`` and the old ``--offset`` default, so absence is read by identity."""
    assert not sam_plan.absent(value)


def test_the_shipped_plan_group_declares_no_routed_flag_a_caller_can_default() -> None:
    """Every optional flag of every routing command has an absent value nobody can pass."""
    sam_plan.check_routing_defaults()


def one_command_group(command: Callable[..., None]) -> typer.Typer:
    """Build a plan group offering *command* as ``list``.

    Typer collapses a group holding a single command into that command, leaving no ``commands``
    mapping for :func:`sam_schema.sam_plan.check_routing_defaults` to walk, so a second command
    keeps the group a group.

    Args:
        command: The callback to offer as ``list``.

    Returns:
        The group.
    """
    group = typer.Typer()
    group.command("list")(command)

    @group.command("status")
    def status() -> None:
        """A second command, so the group stays one."""

    return group


def test_the_guard_rejects_a_routed_flag_whose_default_is_a_real_value() -> None:
    """Re-declaring ``--offset = 0`` fails at import rather than routing by its value."""

    def listing(offset: Annotated[int, typer.Option("--offset", min=0)] = 0) -> None:
        """A routing command with a default a caller can also pass."""

    group = one_command_group(listing)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sam_plan, "app", group)
        with pytest.raises(ValueError, match=r"list declares --offset with default 0"):
            sam_plan.check_routing_defaults()


def test_the_guard_accepts_a_required_flag_with_no_absent_value() -> None:
    """A required option is always passed, so it never has to answer the question."""

    def listing(slug: Annotated[str, typer.Option("--slug")]) -> None:
        """A routing command whose flag the parser never fills in."""

    group = one_command_group(listing)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sam_plan, "app", group)
        sam_plan.check_routing_defaults()
