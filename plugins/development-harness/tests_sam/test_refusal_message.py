"""A refused command tells the caller what the refusal means, in words the caller can use (R3/R4).

``sam plan`` refuses with a reason code. The code is routable, so it leads the line and a caller
matching on it is unaffected. On its own it is not actionable: the caller ran a CLI command in
some other repository and cannot read this one to find out that ``attempts-exhausted`` is lifted
with ``--more-attempts``. ``skills/start-task/SKILL.md`` hand-maintained that mapping for three of
the sixteen refusals, which is the drift this closes.

Both checks here derive their vocabulary from ``ledger_spec`` itself, so they fail when the spec
moves and the prose does not -- which is the only way this prose goes wrong. Asserting that a
message contains a string someone typed proves only that they typed it.
"""

from __future__ import annotations

import re

import pytest
from dh_core import ledger_spec

#: Every flag any command accepts. A message offering a flag that is not here sends the caller to
#: an error instead of a way out.
_REAL_FLAGS: frozenset[str] = frozenset(flag.name for command in ledger_spec.COMMANDS for flag in command.flags)

#: Spellings the ledger uses that ordinary prose does not: the table names, a qualified
#: ``table.column``, and any column whose name is snake_case. A bare column name is excluded on
#: purpose -- ``accepted``, ``archived`` and ``ready`` are English words before they are columns,
#: and "This task is already accepted" is the sentence a caller needs, not a leak.
_TABLES: frozenset[str] = frozenset(column.table for column in ledger_spec.COLUMNS)
_QUALIFIED: frozenset[str] = frozenset(f"{column.table}.{column.name}" for column in ledger_spec.COLUMNS)
_COMPOUND_COLUMNS: frozenset[str] = frozenset(column.name for column in ledger_spec.COLUMNS if "_" in column.name)
_LEDGER_SPELLINGS: frozenset[str] = _TABLES | _QUALIFIED | _COMPOUND_COLUMNS

_FLAG = re.compile(r"--[a-z][a-z-]*")
_TOKEN = re.compile(r"[a-z_]+(?:\.[a-z_]+)?")


@pytest.mark.parametrize("reason", ledger_spec.REASONS, ids=lambda r: r.code)
def test_a_flag_a_message_offers_is_a_flag_a_command_accepts(reason: ledger_spec.Reason) -> None:
    """Fails when a flag is renamed in COMMANDS and the prose still offers the old spelling."""
    offered = set(_FLAG.findall(reason.message))
    unknown = offered - _REAL_FLAGS
    assert not unknown, (
        f"{reason.code}'s message offers {sorted(unknown)}, which no command in ledger_spec.COMMANDS "
        f"accepts. A caller that follows it gets an unknown-flag error instead of a way out."
    )


@pytest.mark.parametrize("reason", ledger_spec.REASONS, ids=lambda r: r.code)
def test_a_message_names_nothing_the_caller_cannot_see(reason: ledger_spec.Reason) -> None:
    """Fails when a message reaches for the ledger's own vocabulary to explain itself.

    ``condition`` is where that vocabulary belongs -- it is read by a maintainer with this file
    open. ``message`` is read by an agent that ran a command in another repository.
    """
    named = {token for token in _TOKEN.findall(reason.message) if token in _LEDGER_SPELLINGS}
    assert not named, (
        f"{reason.code}'s message names {sorted(named)}, which is a ledger table or column. The "
        f"caller cannot see the ledger. Say what happened to their call instead; the condition "
        f"field is where the column name belongs."
    )
