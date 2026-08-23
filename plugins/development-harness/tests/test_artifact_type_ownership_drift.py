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

from pydantic import BaseModel, Field

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_MD = _PLUGIN_ROOT / "AGENTS.md"

_OWNER_TABLE_HEADING = "| Type | Registering agents | Gate-read | Notes |"

# MCP tool form: artifact_register(item_id=..., artifact_type="x", ..., agent="y"). No observed call
# nests parentheses in its body, so a non-greedy match to the first ")" bounds a single call.
_TOOL_CALL_RE = re.compile(r"artifact_register\((?P<body>.*?)\)", re.DOTALL)
# CLI form: `... artifact register \` followed by one --flag per continuation line.
_CLI_CALL_RE = re.compile(r"artifact\s+register\b[^\n]*\n(?:[ \t]*--[^\n]*\n?)*")

_TOOL_TYPE_RE = re.compile(r"""artifact_type=["']([^"']+)["']""")
_TOOL_AGENT_RE = re.compile(r"""agent=["']([^"']+)["']""")
# A CLI flag value may be single-quoted, double-quoted, or bare — `--artifact-type feature-context`
# is as much a registration as `--artifact-type "feature-context"`. Requiring quotes made every bare
# value invisible to the scan.
_CLI_TYPE_RE = re.compile(r"""--artifact-type[=\s]+["']?([^\s"'\\]+)["']?""")
_CLI_AGENT_RE = re.compile(r"""--agent[=\s]+["']?([^\s"'\\]+)["']?""")

_PLACEHOLDER_CHARS = frozenset("{}<>$")
"""Characters that mark a value as a substitution slot rather than a literal registration."""


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


def scan_registrations() -> list[Registration]:
    """Collect every attributable ``artifact_register`` call in the plugin's markdown.

    A call is attributable when it names both its artifact type and its registering agent as
    literals. CLI flag values count whether quoted or bare. Calls using a substitution slot for
    either (``artifact_type=<type>``, ``--agent {resolved_agent}``) show the call shape rather than
    a concrete registration and carry no ownership claim.

    Returns:
        One entry per attributable call, keyed on the agent the call itself names.
    """
    found: list[Registration] = []
    for path in sorted(_PLUGIN_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(_PLUGIN_ROOT))
        chunks = [(m.group("body"), _TOOL_TYPE_RE, _TOOL_AGENT_RE) for m in _TOOL_CALL_RE.finditer(text)]
        chunks += [(m.group(0), _CLI_TYPE_RE, _CLI_AGENT_RE) for m in _CLI_CALL_RE.finditer(text)]
        for chunk, type_re, agent_re in chunks:
            type_match = type_re.search(chunk)
            agent_match = agent_re.search(chunk)
            if not type_match or not agent_match:
                continue
            artifact_type, agent = type_match.group(1), agent_match.group(1)
            if _is_placeholder(artifact_type) or _is_placeholder(agent):
                continue
            found.append(Registration(artifact_type=artifact_type, agent=agent, source=rel))
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
