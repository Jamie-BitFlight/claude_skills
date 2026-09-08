"""Guards the RT-ICA verdict vocabulary against producer/consumer drift.

Two skills in this plugin run the same RT-ICA framework at different stages, and they pin
different verdict token sets on purpose:

- ``skills/rt-ica/SKILL.md`` — the implementation gate. Two values, ``APPROVED`` and ``BLOCKED``.
  Binary because at that gate there is no "proceed with gaps" outcome: proceeding on an unresolved
  condition is the failure the gate exists to prevent.
- ``skills/planner-rt-ica/SKILL.md`` — the planning and grooming pass. Three values,
  ``APPROVED-FOR-PLANNING``, ``APPROVED-WITH-GAPS`` and ``BLOCKED-FOR-PLANNING``. The middle value
  is load-bearing: it separates "cannot plan at all" from "can plan, with known gaps", and the
  second is the ordinary outcome for a brownfield or refactor item.

The two sets are disjoint so a reader of a persisted ``RT-ICA`` section can tell which stage wrote
it, and so a consumer that recognises only one set fails loudly on the other rather than guessing.

What went wrong before this module existed: ``agents/rtica-assessor.md`` computed a binary
``Verdict: READY | BLOCKED`` from ``if MISSING count == 0``, and the grooming swarm halted on that
``BLOCKED``. Every item with a single MISSING prerequisite — the expected brownfield case — stopped
the groom before the groomer agent ran. The producer emitted one vocabulary and the consumer read
another, and because the collapsed value was ``BLOCKED``, the split looked exactly like a gate
working correctly.

Three spellings are therefore retired on the grooming path and this module fails if any returns:

- a ``READY`` verdict in any form — the binary assessor verdict that could not express the middle
  value;
- a ``Verdict:`` or ``Status:`` label carrying a verdict token — the field name is ``Decision:``,
  which is what the ``groom/finalize.md`` validation gate and the work stage's staleness policy
  match literally;
- a bare ``Decision: APPROVED`` or ``Decision: BLOCKED`` on the grooming path — those belong to the
  implementation gate, and emitting them from a grooming producer destroys the discriminator that
  lets ``work/rt-ica-gate.md`` tell the two stages apart.

Every test here is a plain test. The precedent module ``test_status_token_vocabulary_drift.py``
records the lesson: its whole-vocabulary check is a ``strict=True`` xfail, which is structurally
incapable of catching a regression in the thing it names, so the reintroduction guard had to be
split out as a plain test beside it. Nothing here is marked xfail.
"""

from __future__ import annotations

import re
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# The two owning skills, each pinning its own set.
_GATE_SKILL = _PLUGIN_ROOT / "skills" / "rt-ica" / "SKILL.md"
_GATE_TOKENS = frozenset({"APPROVED", "BLOCKED"})

_PLANNER_SKILL = _PLUGIN_ROOT / "skills" / "planner-rt-ica" / "SKILL.md"
_PLANNER_TOKENS = frozenset({"APPROVED-FOR-PLANNING", "APPROVED-WITH-GAPS", "BLOCKED-FOR-PLANNING"})

# Every token that can ever appear as an RT-ICA verdict, plus the retired binary grooming verdict.
_VERDICT_UNIVERSE = _GATE_TOKENS | _PLANNER_TOKENS | {"READY"}

# Producers and consumers of the grooming-stage verdict. Each of these either writes a
# ``Decision:`` line into the item's RT-ICA section or branches on one, so all of them must speak
# the planner vocabulary and nothing else.
_GROOMING_PATH = (
    "agents/rtica-assessor.md",
    "agents/backlog-item-groomer.md",
    "skills/work-backlog-item/references/workflows/groom/analyze.md",
    "skills/work-backlog-item/references/workflows/groom/swarm.md",
    "skills/work-backlog-item/references/workflows/groom/finalize.md",
    "skills/work-backlog-item/references/workflows/groom/start.md",
    "docs/backlog-lifecycle.md",
)

# The one consumer that must recognise both sets: it reads a persisted RT-ICA section that either
# stage may have written, so narrowing it to one set reintroduces the silent-misread failure.
_DUAL_CONSUMER = "skills/work-backlog-item/references/workflows/work/rt-ica-gate.md"

# A verdict label and whatever follows it on the same line. The label may be wrapped in markdown
# emphasis or backticks; the capture is deliberately case-sensitive so the sub-agent contract's
# all-caps ``STATUS:`` line is a different vocabulary and never matched here.
_LABEL_RE = re.compile(r"(?:\*\*|`)?(Decision|Verdict|Status)(?:\*\*|`)?:[ \t]*(.*)")

# An upper-case token, the shape every verdict in either set takes.
_TOKEN_RE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*")

# A markdown ATX heading, captured so its level can be compared.
_HEADING_RE = re.compile(r"^(#{1,6}) ")

# Opening delimiters that introduce a template alternation, e.g. ``{A|B}``, ``<A or B>``, ``[A|B]``.
_GROUP_CLOSERS = {"{": "}", "<": ">", "[": "]"}

# Upper-case words that appear in a template's placeholder position and name no verdict.
_PLACEHOLDERS = frozenset({"TOKEN", "N", "X", "YYYY", "MM", "DD"})


def _tokens_after_label(rest: str) -> list[str]:
    """Extract the verdict tokens a label introduces.

    Handles a single token (``Decision: APPROVED-WITH-GAPS``) and a template alternation
    (``Decision: {A|B|C}``, ``**Verdict**: <READY or BLOCKED>``) alike.

    Args:
        rest: The text following the label's colon, to end of line.

    Returns:
        Upper-case tokens found, placeholders removed.
    """
    rest = rest.strip()
    if not rest:
        return []
    if rest[0] in _GROUP_CLOSERS:
        end = rest.find(_GROUP_CLOSERS[rest[0]])
        if end == -1:
            return []
        found = _TOKEN_RE.findall(rest[1:end])
    else:
        match = _TOKEN_RE.match(rest.lstrip("`"))
        found = [match.group(0)] if match else []
    return [token for token in found if token not in _PLACEHOLDERS]


def _labelled_verdicts(path: Path) -> list[tuple[int, str, str]]:
    """Collect every verdict-labelled token in a file.

    A label is only reported when the token following it is a member of the verdict universe,
    so the ``Status:`` field that carries a condition state (``AVAILABLE``/``DERIVABLE``/
    ``MISSING``) is not mistaken for a verdict.

    Args:
        path: File to scan.

    Returns:
        Tuples of (1-based line number, label used, token found).
    """
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for match in _LABEL_RE.finditer(line):
            label, rest = match.group(1), match.group(2)
            hits.extend((lineno, label, token) for token in _tokens_after_label(rest) if token in _VERDICT_UNIVERSE)
    return hits


def _verdict_vocabulary_section(path: Path) -> str:
    """Return the text of a skill's verdict-vocabulary section.

    Args:
        path: Skill file to read.

    Returns:
        The section body, from its heading to the next heading at the same or shallower level.

    Raises:
        AssertionError: If the skill has no such section — the definition this module cites would
            then be nowhere, which is itself the drift.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    heading = next(
        (
            (i, match)
            for i, line in enumerate(lines)
            if (match := _HEADING_RE.match(line)) and "verdict vocabulary" in line.lower()
        ),
        None,
    )
    assert heading is not None, (
        f"{path.relative_to(_PLUGIN_ROOT)} has no 'Verdict Vocabulary' heading. "
        "This module cites that section as where the skill's token set is defined."
    )
    start, level = heading[0], len(heading[1].group(1))
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if (match := _HEADING_RE.match(lines[i])) and len(match.group(1)) <= level
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_gate_skill_defines_the_two_values_this_module_guards() -> None:
    """``skills/rt-ica/SKILL.md``'s verdict-vocabulary section still defines both binary values.

    Without this, ``_GATE_TOKENS`` is a claim about a file nothing rereads.
    """
    defined = set(_TOKEN_RE.findall(_verdict_vocabulary_section(_GATE_SKILL))) & _VERDICT_UNIVERSE

    assert defined >= set(_GATE_TOKENS), (
        f"{_GATE_SKILL.relative_to(_PLUGIN_ROOT)} no longer defines "
        f"{sorted(set(_GATE_TOKENS) - defined)}, which this module guards as its set."
    )


def test_planner_skill_defines_the_three_values_this_module_guards() -> None:
    """``skills/planner-rt-ica/SKILL.md``'s section still defines all three planning verdicts.

    The middle value is the reason this set is not binary. Losing it from the owning skill is the
    change that would silently re-collapse every producer downstream, so its absence has to be a
    test failure and not a quiet edit.
    """
    defined = set(_TOKEN_RE.findall(_verdict_vocabulary_section(_PLANNER_SKILL))) & _VERDICT_UNIVERSE

    assert defined >= set(_PLANNER_TOKENS), (
        f"{_PLANNER_SKILL.relative_to(_PLUGIN_ROOT)} no longer defines "
        f"{sorted(set(_PLANNER_TOKENS) - defined)}. If APPROVED-WITH-GAPS is gone, so is the "
        "distinction between 'cannot plan at all' and 'can plan, with known gaps'."
    )


def test_each_owning_skill_emits_only_its_own_set() -> None:
    """Neither skill writes a ``Decision:`` line carrying the other's tokens.

    Each may name the other's set in prose — the cross-reference is deliberate — but a producer
    example emitting the wrong set is how a copy-paste puts the wrong vocabulary on the wire.
    """
    offenders = [
        f"  {skill.relative_to(_PLUGIN_ROOT)}:{lineno} — {label}: {token}"
        for skill, owned in ((_GATE_SKILL, _GATE_TOKENS), (_PLANNER_SKILL, _PLANNER_TOKENS))
        for lineno, label, token in _labelled_verdicts(skill)
        if token not in owned
    ]

    assert not offenders, "An owning skill emits a verdict from the other skill's set:\n" + "\n".join(offenders)


def test_the_two_vocabularies_stay_disjoint() -> None:
    """No token belongs to both sets.

    Overlap is what makes a persisted ``RT-ICA`` section ambiguous about which stage wrote it, and
    what stops a consumer from failing loudly on the vocabulary it does not handle.
    """
    overlap = _GATE_TOKENS & _PLANNER_TOKENS

    assert not overlap, (
        f"The implementation-gate and planning verdict sets now share {sorted(overlap)}. "
        "A reader of a persisted RT-ICA section can no longer tell which stage wrote it."
    )


def test_grooming_path_speaks_only_the_planner_vocabulary() -> None:
    """Every verdict written or gated on along the grooming path is a planner token.

    This is the reintroduction guard. A ``READY`` verdict, or a bare ``APPROVED``/``BLOCKED``,
    appearing in any of these files is the exact split that halted the groom on its own normal
    outcome: the assessor collapsed three states into two, and the swarm gate read the collapsed
    value as a stop.
    """
    offenders: list[str] = []
    for relative in _GROOMING_PATH:
        path = _PLUGIN_ROOT / relative
        assert path.exists(), f"{relative} is listed on the grooming path but is not in this checkout"
        for lineno, label, token in _labelled_verdicts(path):
            if token not in _PLANNER_TOKENS:
                offenders.append(f"  {relative}:{lineno} — {label}: {token}")

    assert not offenders, (
        "Retired RT-ICA verdict spellings are back on the grooming path:\n"
        + "\n".join(offenders)
        + f"\nThe grooming path emits only {sorted(_PLANNER_TOKENS)}; "
        f"{sorted(_GATE_TOKENS)} belong to {_GATE_SKILL.relative_to(_PLUGIN_ROOT)} and READY to nothing."
    )


def test_grooming_path_labels_every_verdict_decision() -> None:
    """The grooming path spells the verdict field ``Decision:`` and nothing else.

    ``groom/finalize.md``'s validation gate and the work stage's staleness policy both match this
    line literally. A ``Verdict:`` or ``Status:`` label carrying a verdict token is invisible to
    both, which is how a verdict goes unread rather than being read wrongly.
    """
    offenders = [
        f"  {relative}:{lineno} — {label}: {token}"
        for relative in _GROOMING_PATH
        for lineno, label, token in _labelled_verdicts(_PLUGIN_ROOT / relative)
        if label != "Decision"
    ]

    assert not offenders, (
        "RT-ICA verdicts on the grooming path are labelled with a field the gates do not read:\n"
        + "\n".join(offenders)
        + "\nWrite the verdict as a plain `Decision: <TOKEN>` line."
    )


def test_dual_stage_consumer_still_handles_both_vocabularies() -> None:
    """The work-stage RT-ICA gate names every token either stage can write.

    It reads a section the groom stage or the implementation gate may have produced. Narrowing it
    to one set restores the failure this module exists for: an unrecognised verdict read as a
    block, indistinguishable from a gate working.
    """
    path = _PLUGIN_ROOT / _DUAL_CONSUMER
    text = path.read_text(encoding="utf-8")
    unhandled = sorted(token for token in _GATE_TOKENS | _PLANNER_TOKENS if token not in text)

    assert not unhandled, (
        f"{_DUAL_CONSUMER} no longer names {unhandled}. It consumes RT-ICA sections written by "
        "either stage, so every token of both vocabularies needs a stated action there."
    )
