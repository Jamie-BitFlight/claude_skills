"""A refused command tells the caller what the refusal means (R3/R4).

``sam plan`` refuses with a reason code. The code is routable, so it leads the line and a caller
matching on it is unaffected. On its own it is not actionable: the caller ran a CLI command in
some other repository and cannot read this one to find out that ``attempts-exhausted`` is lifted
with ``--more-attempts``. ``skills/start-task/SKILL.md`` hand-maintained that mapping for three
of the sixteen refusals, which is the drift this closes.

Every message is asserted against what it must not contain rather than against its wording, so a
later rewrite may change the words and may not put a ledger column back.
"""

from __future__ import annotations

import re

import pytest
from dh_core import ledger_spec
from dh_core.ledger_spec import ReasonKind

_ACTED_ON_BY_A_FLAG = {
    "leased": "--force",
    "stale-attempt": "--attempt",
    "attempt-closed": "--attempt",
    "attempt-required": "--attempt",
    "reason-required": "--reason",
    "unmatched-path": "--path",
    "task-accepted": "--force",
    "dependents-started": "--force",
    "attempts-exhausted": "--more-attempts",
    "status-invalid": "--new-status",
    "exists": "--replace",
}

# A ledger column, table or spec constant. The caller sees none of them.
_BEHIND_THE_SURFACE = re.compile(
    r"\b(?:plans|tasks|events|export_cursors)\.\w+|\battempt_open\b|\bNETWORK_FILESYSTEMS\b"
    r"|\bREPORT_SECTIONS\b|\bledger_spec\b|\b\w+\.py\b|#\d{3,}"
)


def test_every_reason_carries_a_message() -> None:
    assert ledger_spec.REASON_BY_CODE.keys() == {r.code for r in ledger_spec.REASONS}
    for reason in ledger_spec.REASONS:
        assert reason.message.strip(), f"{reason.code} has no message"
        opens_a_sentence = reason.message[0].isupper() or reason.message.startswith("--")
        assert opens_a_sentence, f"{reason.code}'s message is not a sentence"
        assert reason.message.rstrip().endswith("."), f"{reason.code}'s message is not a sentence"


@pytest.mark.parametrize("reason", ledger_spec.REASONS, ids=lambda r: r.code)
def test_message_stays_on_the_surface_the_caller_touches(reason: ledger_spec.Reason) -> None:
    leak = _BEHIND_THE_SURFACE.search(reason.message)
    assert leak is None, (
        f"{reason.code}'s message names {leak.group(0)!r}, which the caller cannot see. "
        f"Its condition may name it -- that field is for a maintainer reading the spec."
    )


@pytest.mark.parametrize(("code", "flag"), sorted(_ACTED_ON_BY_A_FLAG.items()))
def test_a_refusal_the_caller_can_lift_names_the_flag_that_lifts_it(code: str, flag: str) -> None:
    assert flag in ledger_spec.REASON_BY_CODE[code].message


def test_a_noop_says_nothing_changed() -> None:
    for reason in ledger_spec.REASONS:
        if reason.kind is ReasonKind.NOOP:
            assert "Nothing changed." in reason.message, f"{reason.code} does not say the call was a no-op"


def test_the_emitted_line_leads_with_the_code() -> None:
    """A caller matching on the bare code keeps working; the meaning follows it."""
    from sam_schema.sam_plan import _reason_line

    line = _reason_line("attempts-exhausted")
    assert line.startswith("attempts-exhausted")
    assert "--more-attempts" in line
    assert _reason_line("cascade:T4") == "cascade:T4", "a templated code has no table entry and prints alone"
