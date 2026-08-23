"""Guards the artifact-type owner map declared in the plugin's AGENTS.md.

``artifact_read`` called without an ``artifact_id`` resolves a manifest entry by
``(item_id, artifact_type)`` alone — it sorts all matching entries by ``created_at`` descending and
returns the newest one. A type whose read decides a workflow branch can therefore address exactly
one document that way, and must have exactly one registering agent. Types that are intentionally
multi-entry, or whose producers all re-register a single shared ``artifact_id``, are safe with
several registering agents and are marked as not gate-read.

One registering agent is not one entry, and this guard does not claim otherwise. A single producer
that registers one entry per unit reviewed leaves several under its own type; its consumers pass an
``artifact_id`` instead of reading by type. The owner map's ``Gate-read`` column bounds who may
write a type, not how many entries one writer leaves.

AGENTS.md's "Artifact types and registering agents" table is the declared map. These tests hold the
shipped markdown and that map in agreement:

* every ``artifact_register`` call in shipped markdown — MCP tool form and ``artifact register``
  CLI form — names a ``(type, agent)`` pair the map declares;
* every gate-read type in the map has exactly one registering agent.

The map, not the scan, is the source of truth for ownership. Some producers are directed in prose
that contains no call to parse — an agent told to "use ``artifact_type=...``" registers the same
entry as one shown a literal call — so a type may legitimately declare an owner that appears in no
scanned call. The scan catches undeclared writers; the map covers the producers it cannot see.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_MD = _PLUGIN_ROOT / "AGENTS.md"

_OWNER_TABLE_HEADING = "| Type | Registering agents | Gate-read | Notes |"

# MCP tool form: artifact_register(item_id=..., artifact_type="x", ..., agent="y"). No observed call
# nests parentheses in its body, so a non-greedy match to the first ")" bounds a single call.
_TOOL_CALL_RE = re.compile(r"artifact_register\((?P<body>.*?)\)", re.DOTALL)
# CLI form: `... artifact register \` followed by one --flag per continuation line.
_CLI_CALL_RE = re.compile(r"artifact\s+register\b[^\n]*\n(?:[ \t]*--[^\n]*\n?)*")

# `artifact_type = "x"` is the same call as `artifact_type="x"`; PEP 8 forbids the spaces for a
# keyword argument but shipped markdown is prose, not linted source, so both forms occur.
_TOOL_TYPE_RE = re.compile(r"""artifact_type\s*=\s*["']([^"']+)["']""")
_TOOL_AGENT_RE = re.compile(r"""\bagent\s*=\s*["']([^"']+)["']""")
# A CLI flag value may be single-quoted, double-quoted, or bare — `--artifact-type feature-context`
# is as much a registration as `--artifact-type "feature-context"`. Requiring quotes made every bare
# value invisible to the scan.
_CLI_TYPE_RE = re.compile(r"""--artifact-type[=\s]+["']?([^\s"'\\]+)["']?""")
_CLI_AGENT_RE = re.compile(r"""--agent[=\s]+["']?([^\s"'\\]+)["']?""")

# Whether the call supplies the argument at all, independent of whether its value is a literal.
_TOOL_AGENT_PRESENT_RE = re.compile(r"\bagent\s*=")
_CLI_AGENT_PRESENT_RE = re.compile(r"--agent\b")

_PLACEHOLDER_CHARS = frozenset("{}<>$")
"""Characters that mark a value as a substitution slot rather than a literal registration."""

_DEFAULT_AGENT = ""
"""``artifact_register``'s default ``agent`` — what a call that omits the argument registers under.

Mirrors ``backlog_core.server.artifact_register``'s signature. Resolving an omitted agent to this
value rather than skipping the call is what stops an unattributed write passing the owner map.
"""


def _is_placeholder(value: str) -> bool:
    """Report whether a scanned flag or keyword value is a substitution slot.

    A call written with ``artifact_type=<type>``, ``--agent {resolved_agent}``, or
    ``--item-id "$task_a"`` documents the call shape rather than a concrete registration, so it
    carries no ownership claim and must not be matched against the owner map.

    Args:
        value: The literal captured from the call.

    Returns:
        True when the value contains a substitution marker.
    """
    return bool(_PLACEHOLDER_CHARS & set(value))


class ArtifactTypeOwners(BaseModel):
    """One declared row of the AGENTS.md artifact-type owner map."""

    artifact_type: str
    agents: frozenset[str] = Field(default_factory=frozenset)
    gate_read: bool = False


class Registration(BaseModel):
    """One ``artifact_register`` call found in shipped markdown."""

    artifact_type: str
    agent: str
    source: str


_UNDECLARED = ArtifactTypeOwners(artifact_type="")
"""Stand-in for a type absent from the map: it owns no agent, so every writer of it is undeclared."""


def _resolve_agent(chunk: str, agent_re: re.Pattern[str], present_re: re.Pattern[str]) -> str | None:
    """Resolve the agent a scanned ``artifact_register`` call registers under.

    Three cases, and they are not the same. A literal value is the writer. An argument supplied with
    a non-literal value (``agent=agent``, ``--agent {resolved_agent}``) documents the call's shape,
    so the call makes no ownership claim. An argument omitted altogether is a concrete registration
    under ``artifact_register``'s ``agent`` default.

    Args:
        chunk: The text of one ``artifact_register`` call.
        agent_re: Pattern capturing the agent value when it is a literal.
        present_re: Pattern matching the agent argument whatever its value.

    Returns:
        The agent name, or None when the call carries no ownership claim.
    """
    match = agent_re.search(chunk)
    if match is not None:
        return None if _is_placeholder(match.group(1)) else match.group(1)
    return None if present_re.search(chunk) else _DEFAULT_AGENT


def _strip_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def parse_owner_map(text: str) -> dict[str, ArtifactTypeOwners]:
    """Parse the artifact-type owner map out of AGENTS.md.

    Args:
        text: Full AGENTS.md contents.

    Returns:
        Mapping of artifact type to its declared owners and gate-read flag.

    Raises:
        AssertionError: If the owner table heading is absent or the table is empty.
    """
    lines = text.splitlines()
    assert _OWNER_TABLE_HEADING in lines, (
        f"AGENTS.md is missing the artifact-type owner map. Expected a table headed "
        f"{_OWNER_TABLE_HEADING!r} under 'Artifact types and registering agents'."
    )
    start = lines.index(_OWNER_TABLE_HEADING) + 2  # skip the header and its separator row
    owners: dict[str, ArtifactTypeOwners] = {}
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        cells = list(line.split("|")[1:-1])
        if len(cells) < 3:
            continue
        artifact_type = _strip_cell(cells[0])
        agents = frozenset(_strip_cell(a) for a in cells[1].split(",") if _strip_cell(a))
        owners[artifact_type] = ArtifactTypeOwners(
            artifact_type=artifact_type, agents=agents, gate_read=_strip_cell(cells[2]).lower() == "yes"
        )
    assert owners, "The artifact-type owner map in AGENTS.md declares no rows."
    return owners


def parse_registrations(text: str, source: str) -> list[Registration]:
    """Collect every attributable ``artifact_register`` call in one markdown document.

    A call is attributable when it names its artifact type as a literal. CLI flag values count
    whether quoted or bare. Calls using a substitution slot for the type or the agent
    (``artifact_type=<type>``, ``--agent {resolved_agent}``) show the call shape rather than a
    concrete registration and carry no ownership claim.

    Omitting the agent argument is not the same as supplying it with a placeholder.
    ``artifact_register``'s ``agent`` parameter defaults to ``""``, so a call that names a type and
    omits the argument registers a concrete entry under the empty producer. Those resolve to
    ``_DEFAULT_AGENT`` and are held against the owner map like any other writer, because an entry no
    declared agent owns is exactly the unattributable write this guard exists to catch. See
    ``_resolve_agent``.

    Args:
        text: The markdown to scan.
        source: Identifier recorded on each result, normally a plugin-relative path.

    Returns:
        One entry per attributable call, keyed on the agent the call names or defaults to.
    """
    chunks = [
        (m.group("body"), _TOOL_TYPE_RE, _TOOL_AGENT_RE, _TOOL_AGENT_PRESENT_RE) for m in _TOOL_CALL_RE.finditer(text)
    ]
    chunks += [(m.group(0), _CLI_TYPE_RE, _CLI_AGENT_RE, _CLI_AGENT_PRESENT_RE) for m in _CLI_CALL_RE.finditer(text)]
    found: list[Registration] = []
    for chunk, type_re, agent_re, agent_present_re in chunks:
        type_match = type_re.search(chunk)
        if not type_match or _is_placeholder(type_match.group(1)):
            continue
        agent = _resolve_agent(chunk, agent_re, agent_present_re)
        if agent is None:
            continue
        found.append(Registration(artifact_type=type_match.group(1), agent=agent, source=source))
    return found


def scan_registrations() -> list[Registration]:
    """Collect every attributable ``artifact_register`` call across the plugin's markdown.

    Returns:
        The concatenated result of ``parse_registrations`` over every shipped ``*.md``.
    """
    found: list[Registration] = []
    for path in sorted(_PLUGIN_ROOT.rglob("*.md")):
        found += parse_registrations(path.read_text(encoding="utf-8"), str(path.relative_to(_PLUGIN_ROOT)))
    return found


def test_every_registration_is_declared_in_the_owner_map() -> None:
    """Every scanned ``(artifact_type, agent)`` pair appears in the AGENTS.md owner map."""
    owners = parse_owner_map(_AGENTS_MD.read_text(encoding="utf-8"))
    undeclared = sorted({
        (r.artifact_type, r.agent, r.source)
        for r in scan_registrations()
        if r.agent not in owners.get(r.artifact_type, _UNDECLARED).agents
    })

    assert not undeclared, (
        "artifact_register call(s) name a (type, agent) pair the AGENTS.md owner map does not "
        "declare. Either the writer is registering under the wrong type, or the map is stale — "
        "resolve it in AGENTS.md before the call ships, because a read by type alone returns only "
        "the newest entry and cannot tell two writers apart. Each entry is "
        "(artifact_type, agent, source): " + repr(undeclared)
    )


def test_gate_read_types_have_exactly_one_registering_agent() -> None:
    """A type whose read drives a workflow branch is declared with a single registering agent."""
    owners = parse_owner_map(_AGENTS_MD.read_text(encoding="utf-8"))
    shared = {
        row.artifact_type: sorted(row.agents) for row in owners.values() if row.gate_read and len(row.agents) != 1
    }

    assert not shared, (
        "gate-read artifact type(s) declare other than exactly one registering agent. artifact_read "
        "returns only the most recently created entry for a given (item_id, artifact_type), so a "
        "second writer under a gate-read type silently displaces the document the gate branches on. "
        "Split the second writer onto its own type. Each entry is "
        "(artifact_type, [registering_agents]): " + repr(shared)
    )


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        (
            'artifact_register(item_id=1, artifact_type="research", agent="swarm-task-planner")',
            ("research", "swarm-task-planner"),
        ),
        (
            'artifact_register(item_id=1, artifact_type = "research", agent = "swarm-task-planner")',
            ("research", "swarm-task-planner"),
        ),
        (
            "artifact_register(item_id=1, artifact_type='research', agent='swarm-task-planner')",
            ("research", "swarm-task-planner"),
        ),
        (
            "artifact register \\\n  --artifact-type research \\\n  --agent swarm-task-planner\n",
            ("research", "swarm-task-planner"),
        ),
        (
            'artifact register \\\n  --artifact-type "research" \\\n  --agent "swarm-task-planner"\n',
            ("research", "swarm-task-planner"),
        ),
        (
            "artifact register \\\n  --artifact-type=research \\\n  --agent=swarm-task-planner\n",
            ("research", "swarm-task-planner"),
        ),
    ],
    ids=["tool-tight", "tool-spaced", "tool-single-quoted", "cli-bare", "cli-quoted", "cli-equals"],
)
def test_parse_registrations_reads_every_literal_call_form(call: str, expected: tuple[str, str]) -> None:
    """Every literal spelling of a registration yields the same (type, agent) pair.

    Tests: parse_registrations across the MCP tool and CLI call forms
    How: Parse one call per spelling — tight and spaced keyword assignment, single and double quotes,
         bare and quoted and =-separated CLI flags — and compare the extracted pair.
    Why: The guard's whole claim is that every shipped registration is held against the owner map. A
         spelling the regexes miss is a silent hole: an undeclared type or writer written that way
         passes while the suite stays green.
    """
    assert [(r.artifact_type, r.agent) for r in parse_registrations(call, "doc.md")] == [expected]


@pytest.mark.parametrize(
    "call",
    [
        'artifact_register(item_id=item_id, artifact_type="architect", agent=agent)',
        'artifact_register(item_id=item_id, artifact_type="architect", agent="{resolved_agent}")',
        'artifact_register(item_id=item_id, artifact_type="<type>", agent="planning")',
        "artifact register \\\n  --artifact-type architect \\\n  --agent {resolved_agent}\n",
    ],
    ids=["bare-identifier", "braced-agent", "angled-type", "cli-braced-agent"],
)
def test_parse_registrations_ignores_calls_that_claim_no_owner(call: str) -> None:
    """A call whose type or agent is a substitution slot makes no ownership claim.

    Tests: parse_registrations placeholder handling
    How: Parse calls whose type or agent is a bare identifier or a braced/angled slot.
    Why: These document a call's shape rather than a concrete registration. Attributing them would
         blame a document for a write it never performs, and would put values like
         '{resolved_agent}' in the owner map to keep the guard green.
    """
    assert parse_registrations(call, "doc.md") == []


def test_parse_registrations_attributes_an_omitted_agent_to_the_default() -> None:
    """A call that omits the agent argument registers under artifact_register's default.

    Tests: _resolve_agent's absent-argument branch
    How: Parse a call naming a type and no agent at all; assert the agent is _DEFAULT_AGENT.
    Why: backlog_core.server.artifact_register defaults agent to "". Skipping such a call would let
         an entry no declared agent owns pass the map — the exact unattributed write this guard
         exists to catch. It is distinct from the placeholder case above, where the argument is
         present but carries no claim.
    """
    call = 'artifact_register(item_id=1, artifact_type="architect", artifact_id="plan/a.md")'

    assert [(r.artifact_type, r.agent) for r in parse_registrations(call, "doc.md")] == [("architect", _DEFAULT_AGENT)]
