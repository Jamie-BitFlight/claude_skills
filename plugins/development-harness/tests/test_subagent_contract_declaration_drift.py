"""Guards the destination rule the subagent contract states for dispatched agents.

`skills/subagent-contract/SKILL.md` is where a dispatched agent is told what its output
goes into: repository files for source, tests, and documentation; `artifact_register`
with content for every other document; the SAM plan and task operations for plans and
task state. A dispatched agent starts with an empty conversation and inherits nothing its
dispatcher loaded, so that rule reaches it only through its own `skills:` frontmatter.

An agent holding those operations and not that rule can still write its result somewhere
the next step cannot read it, and the miss is silent — the next step reads empty rather
than failing. Item grooming operations (`backlog_view`, `backlog_groom`) address no
artifact, so an agent declaring only those is out of scope and is derived as such from
its tool list rather than exempted by name.
"""

from __future__ import annotations

from pathlib import Path

from agent_profile.parser import _load_frontmatter_from_path, _normalize_skills

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_ROOT = _PLUGIN_ROOT / "agents"

_CONTRACT_SKILL = "dh:subagent-contract"

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
    """Return the names of in-scope agents that omit the subagent contract skill.

    An agent is in scope when its `tools:` key is absent (it inherits every tool, so it
    reaches the governed operations) or when the declared list reaches one of them.

    Args:
        agents_root: Directory whose `*.md` files are agent definitions.

    Returns:
        Sorted paths, relative to *agents_root*, of in-scope agents whose `skills:`
        frontmatter does not declare `dh:subagent-contract`.
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
    """Every agent that can address an artifact, plan, or task carries the rule for it."""
    missing = _agents_missing_contract(_AGENTS_ROOT)

    assert not missing, (
        "An agent reaching the SAM or artifact operations decides where its output lands, and "
        f"{_CONTRACT_SKILL} is where that decision is stated. A dispatched agent loads it through "
        "its own skills: frontmatter or not at all. These agents reach those operations without "
        f"declaring it, so each can persist a result the next step reads back empty: {missing!r}. "
        f"Add '{_CONTRACT_SKILL}' to each agent's skills: frontmatter, or remove the governed "
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
