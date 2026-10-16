"""A refused command tells the caller what the refusal means, in words the caller can use (R3/R4).

``sam plan`` refuses with a reason code. The code is routable, so it leads the line and a caller
matching on it is unaffected. On its own it is not actionable: the caller ran a CLI command in
some other repository and cannot read this one to find out that ``attempts-exhausted`` is lifted
with ``--more-attempts``. ``skills/start-task/SKILL.md`` hand-maintained that mapping for three of
the sixteen refusals, which is the drift this closes.

The check derives each offered flag from the declarative command surface and verifies that every
command emitting the reason accepts it. This protects followable CLI advice, not incidental wording.
"""

from __future__ import annotations

import re

import pytest
from dh_core import ledger_spec

_FLAG = re.compile(r"--[a-z][a-z-]*")


def _emitting_commands(code: str) -> frozenset[str]:
    """Return every command whose transitions can refuse with ``code``."""
    return frozenset(
        transition.command
        for transition in ledger_spec.TRANSITIONS
        for check in getattr(transition, "checks", ())
        if getattr(check, "reason", None) == code
    )


def _flags_of(command: str) -> frozenset[str]:
    found = next((c for c in ledger_spec.COMMANDS if c.name == command), None)
    return frozenset(flag.name for flag in found.flags) if found else frozenset()


#: Every (reason, flag, command) the spec can actually produce: a reason whose message offers a
#: flag, paired with each command that can refuse with that reason.
_OFFERS: list[tuple[str, str, str]] = sorted(
    (reason.code, flag, command)
    for reason in ledger_spec.REASONS
    for flag in _FLAG.findall(reason.message)
    for command in _emitting_commands(reason.code)
)


@pytest.mark.parametrize(("code", "flag", "command"), _OFFERS, ids=lambda v: v)
def test_a_flag_a_message_offers_is_accepted_by_every_command_that_refuses_with_it(
    code: str, flag: str, command: str
) -> None:
    """A message is one sentence for every command that emits it, so the flag must work for all.

    Asserting the flag exists *somewhere* in COMMANDS is the weaker check, and it passed while
    ``leased`` offered ``--force`` to ``dispatch``, which has no such flag -- so the caller that
    most often meets ``leased`` got ``Error: No such option: --force`` for following the advice.
    """
    assert flag in _flags_of(command), (
        f"{code}'s message offers {flag}, but `sam plan {command}` can refuse with {code} and does "
        f"not accept {flag}. A caller that follows the message gets an unknown-flag error. Either "
        f"say what happened without naming a flag, or give the flag to every command that refuses "
        f"with this code."
    )
