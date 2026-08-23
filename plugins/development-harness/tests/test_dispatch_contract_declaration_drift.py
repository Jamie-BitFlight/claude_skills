"""Guards the roster invariant the dispatch contract skill states as fact.

`skills/dispatch-contract/SKILL.md` tells a dispatcher that a `dh:` agent passing the
tool-reach check is already executing under the dispatch contract, so no per-candidate
check of the candidate's `skills:` frontmatter is needed. A dispatcher cannot verify
that claim: the listing it picks a target from carries name, description, and tool list
only. The claim is therefore load-bearing prose backed by nothing unless every dh agent
that declares a governed operation also declares `dh:dispatch-contract`.

The governed operations are the ones the skill's own decision list enumerates — the SAM
plan/task/active-task operations, the artifact operations, and `profile_load`. Item
grooming operations (`backlog_view`, `backlog_groom`) are not governed by this contract,
so an agent declaring only those is out of scope and is derived as such from its tool
list rather than exempted by name.
"""

from __future__ import annotations

from pathlib import Path

from agent_profile.parser import _load_frontmatter_from_path, _normalize_skills

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_ROOT = _PLUGIN_ROOT / "agents"

_CONTRACT_SKILL = "dh:dispatch-contract"

# Bare operation names as exposed by the SAM server (sam_schema/server.py) and the
# backlog server (backlog_core/server.py, which mounts agent_profile under `profile_`).
_GOVERNED_OPERATIONS = frozenset({
    "sam_plan",
    "sam_task",
    "sam_active_task",
    "artifact_register",
    "artifact_read",
    "artifact_list",
    "artifact_get",
    "profile_load",
    "profile_list",
})

# A whole-server grant reaches every operation that server exposes.
_GOVERNED_SERVERS = frozenset({"mcp__plugin_dh_sam", "mcp__plugin_dh_backlog"})


def _reaches_governed_operation(tools: list[str]) -> bool:
    """Report whether a declared tool list reaches any contract-governed operation.

    Args:
        tools: Tool entries exactly as declared in the agent's `tools:` frontmatter.

    Returns:
        True when the list grants a governed server wholesale, grants every tool via a
        wildcard, or names an individual governed operation.
    """
    for tool in tools:
        if tool == "*" or tool in _GOVERNED_SERVERS:
            return True
        if tool.rsplit("__", 1)[-1] in _GOVERNED_OPERATIONS:
            return True
    return False


def _agents_missing_contract(agents_root: Path) -> list[str]:
    """Return the names of in-scope agents that omit the dispatch contract skill.

    An agent is in scope when its `tools:` key is absent (it inherits every tool, so it
    reaches the governed operations) or when the declared list reaches one of them.

    Args:
        agents_root: Directory whose `*.md` files are agent definitions.

    Returns:
        Sorted paths, relative to *agents_root*, of in-scope agents whose `skills:`
        frontmatter does not declare `dh:dispatch-contract`.
    """
    missing: list[str] = []
    for path in sorted(agents_root.rglob("*.md")):
        meta, _ = _load_frontmatter_from_path(path)
        if not meta:
            continue
        in_scope = "tools" not in meta or _reaches_governed_operation(_normalize_skills(meta.get("tools")))
        if in_scope and _CONTRACT_SKILL not in _normalize_skills(meta.get("skills")):
            missing.append(str(path.relative_to(agents_root)))
    return missing


def test_every_dh_agent_reaching_governed_operations_declares_the_contract() -> None:
    """The invariant the skill asserts to dispatchers holds across the whole roster."""
    missing = _agents_missing_contract(_AGENTS_ROOT)

    assert not missing, (
        "The dispatch-contract skill tells a dispatcher that a dh: agent passing the tool-reach "
        f"check is already executing under {_CONTRACT_SKILL}, and a dispatcher cannot verify that "
        "per candidate — the agent listing exposes name, description, and tools only. These agents "
        "declare a governed operation without declaring the contract, so a dispatcher following "
        f"the skill would dispatch them expecting behaviour they do not load: {missing!r}. Add "
        f"'{_CONTRACT_SKILL}' to each agent's skills: frontmatter, or remove the governed "
        "operations from its tools: frontmatter."
    )


def test_guard_detects_a_dropped_contract_declaration(tmp_path: Path) -> None:
    """Removing the declaration from an in-scope agent is caught.

    The roster currently satisfies the invariant, so the assertion above passes on every
    run and on its own proves only that the loop found nothing. Copying one in-scope
    agent and stripping its declaration shows the loop can produce a finding.
    """
    source = _AGENTS_ROOT / "code-reviewer.md"
    text = source.read_text(encoding="utf-8")
    assert _CONTRACT_SKILL in text, f"fixture source must declare {_CONTRACT_SKILL}"

    (tmp_path / source.name).write_text(text.replace(f"  - {_CONTRACT_SKILL}\n", ""), encoding="utf-8")

    assert _agents_missing_contract(tmp_path) == [source.name]
