"""Guards against artifact-type co-tenancy drift across agent files.

``artifact_read`` resolves a manifest entry by ``(item_id, artifact_type)`` only — it sorts all
matching entries by ``created_at`` descending and returns the newest one, silently discarding the
rest. AGENTS.md's Artifact Manifest System table therefore documents each artifact type as owned
by exactly one producing agent. If a second agent starts writing under an already-owned type, its
entries race the owner's for that slot: whichever agent registers last wins the read, and any
consumer keyed on the owner's content silently receives the newest writer's data instead.

This test parses every agent file for ``artifact_register(`` calls, extracts each
``(artifact_type, agent)`` pair keyed on the call's own ``agent="..."`` argument (not the file it
appears in — a planner agent's task-template prose may show the call another agent will make on
its behalf, e.g. `swarm-task-planner.md` documenting the `t0-baseline-capture` bookend task's
call), and fails if any artifact type is written by more than one distinct registering agent.
"""

from __future__ import annotations

import re
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Captures one artifact_register(...) call body up to its closing paren. None of the observed
# call shapes nest parentheses inside the body (values are quoted strings, braces, or bare
# identifiers), so a non-greedy match to the first ")" reliably bounds a single call.
_REGISTER_CALL_RE = re.compile(r"artifact_register\((?P<body>.*?)\)", re.DOTALL)
_ARTIFACT_TYPE_RE = re.compile(r"""artifact_type=["']([^"']+)["']""")
_AGENT_RE = re.compile(r"""agent=["']([^"']+)["']""")


def _iter_agent_files() -> list[Path]:
    return sorted((_PLUGIN_ROOT / "agents").rglob("*.md"))


def test_each_artifact_type_has_exactly_one_registering_agent() -> None:
    """Every artifact_type written via artifact_register() must have exactly one writer.

    A second agent registering under an already-owned type silently wins or loses the
    ``artifact_read`` race depending on write order — see module docstring.
    """
    owners: dict[str, set[str]] = {}
    for path in _iter_agent_files():
        text = path.read_text(encoding="utf-8")
        for match in _REGISTER_CALL_RE.finditer(text):
            body = match.group("body")
            type_match = _ARTIFACT_TYPE_RE.search(body)
            if not type_match:
                continue
            agent_match = _AGENT_RE.search(body)
            registering_agent = agent_match.group(1) if agent_match else path.stem
            owners.setdefault(type_match.group(1), set()).add(registering_agent)

    co_owned = {artifact_type: sorted(agents) for artifact_type, agents in owners.items() if len(agents) > 1}

    assert not co_owned, (
        "artifact_type(s) registered by more than one agent — artifact_read returns only the "
        "most recently created entry for a given (item_id, artifact_type), so a second writer "
        "under an already-owned type silently displaces the owner's content for any consumer "
        "reading by type alone. Each entry is (artifact_type, [registering_agents]): " + repr(co_owned)
    )
