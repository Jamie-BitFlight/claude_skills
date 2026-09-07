"""Closure tests over ``dh_core.ledger_spec``.

Each test names one way the specification could be open: a column no event sets, an event no
command emits, a reason nothing prints, a status a command does not handle. A red test is a hole
in the design, found before ``dh_core/ledger.py`` exists.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest
from dh_core import ledger_spec as spec
from marko import Markdown
from marko.block import Heading, Quote
from marko.inline import RawText
from sam_schema.core.models import TaskStatus

TASK_COMMANDS = [c for c in spec.COMMANDS if c.scope == spec.Scope.TASK]
PLAN_COMMANDS = [c for c in spec.COMMANDS if c.scope == spec.Scope.PLAN]
COMMAND_NAMES = {c.name for c in spec.COMMANDS}
EVENT_KINDS = {e.kind for e in spec.EVENTS}
REASONS_BY_CODE = {r.code: r for r in spec.REASONS}
COLUMN_NAMES = {c.name for c in spec.COLUMNS}
TABLE_NAMES = {c.table for c in spec.COLUMNS}

PLUGIN_ROOT: Path = Path(__file__).resolve().parents[1]
CONTRACT: Path = PLUGIN_ROOT / "docs" / "graph-ir" / "ASSESSOR-CONTRACT.md"
AUTHORITY_HEADING = "Authority of a task's instructions, at runtime"


def test_statuses_equal_task_status_enum() -> None:
    assert {s.value for s in spec.Status} == {s.value for s in TaskStatus}


def test_every_event_column_names_declared_events() -> None:
    for col in spec.COLUMNS:
        if col.provenance is spec.Provenance.DERIVED:
            assert col.rule, f"{col.table}.{col.name} is derived with no rule"
            assert not col.set_by, f"{col.table}.{col.name} is derived and lists events"
        else:
            assert col.set_by, f"{col.table}.{col.name} has no event that sets it"
            unknown = set(col.set_by) - EVENT_KINDS
            assert not unknown, f"{col.table}.{col.name} set by undeclared events {unknown}"


def test_every_event_sets_a_column_and_is_emitted_by_a_transition() -> None:
    set_by = {k for c in spec.COLUMNS for k in c.set_by}
    emitted = {k for t in spec.TRANSITIONS for k in t.events}
    for e in spec.EVENTS:
        assert e.kind in set_by, f"{e.kind} sets no column"
        assert e.kind in emitted, f"{e.kind} is emitted by no transition"
    assert emitted <= EVENT_KINDS, f"transitions emit undeclared events {emitted - EVENT_KINDS}"


def test_event_written_by_matches_transitions() -> None:
    for e in spec.EVENTS:
        unknown = set(e.written_by) - COMMAND_NAMES
        assert not unknown, f"{e.kind} written by unknown commands {unknown}"
        emitters = {t.command for t in spec.TRANSITIONS if e.kind in t.events}
        assert emitters == set(e.written_by), (
            f"{e.kind}: written_by {sorted(e.written_by)} but transitions emit from {sorted(emitters)}"
        )


def test_every_check_reason_is_declared_and_every_reason_is_used() -> None:
    used: Counter[str] = Counter()
    for t in spec.TRANSITIONS:
        for check in t.checks:
            reason = REASONS_BY_CODE.get(check.reason)
            assert reason is not None, f"{t.command}/{t.from_status} checks undeclared reason {check.reason}"
            assert reason.kind is not spec.ReasonKind.OUTCOME, f"{t.command} checks an outcome reason {check.reason}"
            used[check.reason] += 1
        if t.noop:
            assert REASONS_BY_CODE[t.noop].kind is spec.ReasonKind.NOOP
            used[t.noop] += 1
    outcome_text = (
        " ".join(e.value for t in spec.TRANSITIONS for e in t.effects)
        + " "
        + " ".join(t.note for t in spec.TRANSITIONS)
    )
    for r in spec.REASONS:
        if r.kind is spec.ReasonKind.OUTCOME:
            token = r.code.split(":")[0]
            assert token in outcome_text, f"outcome reason {r.code} appears in no effect or note"
        elif r.code == "network-filesystem":
            continue  # printed at open, before any transition
        else:
            assert used[r.code], f"reason {r.code} is printed by no transition"


def test_reason_codes_unique() -> None:
    codes = [r.code for r in spec.REASONS]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("command", [c.name for c in TASK_COMMANDS])
@pytest.mark.parametrize("status", list(spec.Status))
def test_every_task_command_handles_every_status_exactly_once(command: str, status: spec.Status) -> None:
    matches = [t for t in spec.TRANSITIONS if t.command == command and t.from_status in (status, spec.ANY)]
    assert len(matches) == 1, f"{command} in {status}: {len(matches)} transitions"


def test_plan_commands_have_one_transition_or_are_reads() -> None:
    reads = {"validate", "list", "status", "ready"}
    for c in PLAN_COMMANDS:
        matches = [t for t in spec.TRANSITIONS if t.command == c.name]
        if c.name in reads:
            continue
        assert len(matches) == 1, f"{c.name}: {len(matches)} transitions"
        assert matches[0].from_status == spec.ANY


def test_transition_commands_exist() -> None:
    for t in spec.TRANSITIONS:
        assert t.command in COMMAND_NAMES, f"transition names unknown command {t.command}"


def test_effects_name_columns_or_tables() -> None:
    compound = {"sections", "task model fields", "plans, tasks, sections", "export_cursors", "plans", "tasks"}
    for t in spec.TRANSITIONS:
        for e in t.effects:
            assert e.column in COLUMN_NAMES or e.column in TABLE_NAMES or e.column in compound, (
                f"{t.command}/{t.from_status} sets unknown column {e.column}"
            )


def test_to_status_is_a_status_or_a_conditional() -> None:
    for t in spec.TRANSITIONS:
        if not t.to_status or t.to_status == "--new-status":
            continue
        assert t.to_status in set(spec.Status) or " when " in t.to_status, f"{t.command}: to_status {t.to_status!r}"


def test_renewing_commands_renew_in_progress() -> None:
    for c in spec.COMMANDS:
        if c.renews:
            t = next(x for x in spec.TRANSITIONS if x.command == c.name and x.from_status == spec.Status.IN_PROGRESS)
            assert "lease.renewed" in t.events, f"{c.name} renews but its in-progress transition emits no lease.renewed"
            assert {e.column for e in t.effects} >= {"expires", "last_activity", "first_renewed"}


def test_flags_unique_per_command_and_commands_unique() -> None:
    names = [c.name for c in spec.COMMANDS]
    assert len(names) == len(set(names))
    for c in spec.COMMANDS:
        flags = [f.name for f in c.flags]
        assert len(flags) == len(set(flags)), f"{c.name} repeats a flag"
    assert not set(spec.RETIRED_COMMANDS) & COMMAND_NAMES


def test_key_forms_have_their_flags() -> None:
    for c in spec.COMMANDS:
        flags = {f.name for f in c.flags}
        if "attempt" in c.key:
            assert "--attempt" in flags, f"{c.name} keyed by attempt without --attempt"
        if "path" in c.key:
            assert "--path" in flags, f"{c.name} keyed by path without --path"
        if c.key == "attempt|path":
            addr = next(f for f in c.flags if f.name == "--address")
            assert not addr.required, f"{c.name}: --address must be optional when --path is an alternative"


def test_config_keys_referenced_exist() -> None:
    keys = {c.key for c in spec.CONFIG}
    text = " ".join(e.value for t in spec.TRANSITIONS for e in t.effects)
    referenced = set(re.findall(r"\b(lease\.[a-z_]+|loop\.[a-z_]+)\b", text))
    assert referenced == keys, f"referenced {referenced} vs declared {keys}"


def test_report_check_columns_exist() -> None:
    assert "attempts" in COLUMN_NAMES
    assert {"name", "attempt", "content"} <= {c.name for c in spec.COLUMNS if c.table == "sections"}


def test_no_session_or_agent_id_anywhere() -> None:
    import inspect

    source = inspect.getsource(spec)
    forbidden = re.findall(r"session_id|agent_id|CLAUDE_CODE_SESSION_ID|\bbinding\b", source)
    assert forbidden == ["session id", "agent id"] or not [f for f in forbidden if "_" in f], (
        f"identity keys present: {forbidden}"
    )


def test_model_fields_match_models() -> None:
    from sam_schema.core.models import Plan, Task

    plan_fields = set(Plan.model_fields) - {"tasks", "source_path", "source_format"}
    assert set(spec.PLAN_MODEL_FIELDS) == plan_fields, plan_fields ^ set(spec.PLAN_MODEL_FIELDS)
    assert set(spec.TASK_MODEL_FIELDS) == set(Task.model_fields), set(Task.model_fields) ^ set(spec.TASK_MODEL_FIELDS)


# ---------------------------------------------------------------------------
# Anti-drift: AUTHORITY_PREAMBLE against ASSESSOR-CONTRACT.md's own block quote
# ---------------------------------------------------------------------------
#
# Mirrors the CONTRACT-path pattern in test_decomposition_gate.py -- reading the governing document
# as data rather than trusting a hand-copied string -- and, per this repo's rule (AGENTS.md), parses
# markdown structure with marko rather than a hand-rolled regex. marko locates the block quote
# structurally (so a structural change -- the quote dropped, replaced, or moved out of its heading --
# fails this test rather than silently reading something else); the verbatim text is then read from
# the raw lines that quote spans and stripped of its leading ``> `` markers, the same transform
# ``ledger_spec.AUTHORITY_PREAMBLE`` was built with.


def heading_text(heading: Heading) -> str:
    return "".join(child.children for child in heading.children if isinstance(child, RawText)).strip()


def contract_authority_quote() -> str:
    """Return ASSESSOR-CONTRACT.md's authority block quote, verbatim with ``> `` markers stripped.

    Returns:
        The block quote's text, joined by newlines, with no leading ``> ``/``>`` marker on any line.
    """
    text = CONTRACT.read_text(encoding="utf-8")
    children = list(Markdown(extensions=["gfm"]).parse(text).children)
    heading_index = next(
        (
            index
            for index, child in enumerate(children)
            if isinstance(child, Heading) and child.level == 3 and heading_text(child) == AUTHORITY_HEADING
        ),
        None,
    )
    assert heading_index is not None, "could not find the authority heading -- fix the parser, not the test"

    quote_node = None
    for child in children[heading_index + 1 :]:
        if isinstance(child, Heading) and child.level <= 3:
            break
        if isinstance(child, Quote):
            quote_node = child
            break
    assert quote_node is not None, "no block quote found under the authority heading -- fix the parser, not the test"

    lines = text.splitlines()
    heading_line = next(i for i, line in enumerate(lines) if line.strip() == f"### {AUTHORITY_HEADING}")
    start = next(i for i in range(heading_line + 1, len(lines)) if lines[i].startswith(">"))
    quoted: list[str] = []
    for line in lines[start:]:
        if line == ">":
            quoted.append("")
            continue
        if line.startswith("> "):
            quoted.append(line[2:])
            continue
        break
    return "\n".join(quoted)


def test_authority_preamble_matches_the_contracts_block_quote() -> None:
    """``ledger_spec.AUTHORITY_PREAMBLE`` must equal the contract's own block quote, verbatim.

    Two encodings of the same text drift silently otherwise; this is the check that would catch it.
    """
    assert contract_authority_quote() == spec.AUTHORITY_PREAMBLE


def test_authority_preamble_anti_drift_check_is_not_vacuous() -> None:
    """A deliberately wrong body must NOT match the contract's quote -- the comparison is live."""
    assert contract_authority_quote() != "this is not the real authority preamble text"
