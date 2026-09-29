"""Machine-consumed wiring contract for agents that can reach resolver-dependent DH CLI tokens."""

from __future__ import annotations

import re
from pathlib import Path

from agent_profile.parser import _load_frontmatter_from_path, _normalize_skills

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_ROOT = _PLUGIN_ROOT / "agents"
_SKILLS_ROOT = _PLUGIN_ROOT / "skills"
_CLI_USAGE_SKILL = "dh:dh-cli-usage"
_CLI_TOKEN_RE = re.compile(r"<sam_cli\s*/>|<dh_scripts\s*/>")


def _skill_body(skill_uri: str) -> str:
    name = skill_uri.removeprefix("dh:")
    if name == skill_uri:
        return ""
    path = _SKILLS_ROOT / name / "SKILL.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def test_agents_reaching_cli_tokens_preload_resolver_and_can_execute() -> None:
    """Resolver-dependent CLI tokens are reachable only with the resolver and Bash."""
    invalid: list[str] = []

    for path in sorted(_AGENTS_ROOT.glob("*.md")):
        meta, body = _load_frontmatter_from_path(path)
        skills = _normalize_skills(meta.get("skills"))
        reachable_text = body + "".join(_skill_body(uri) for uri in skills)
        if not _CLI_TOKEN_RE.search(reachable_text):
            continue

        reasons: list[str] = []
        if _CLI_USAGE_SKILL not in skills:
            reasons.append(f"skills has no {_CLI_USAGE_SKILL}")

        tools = meta.get("tools")
        tool_names = tools if isinstance(tools, list) else str(tools).split(",")
        normalized_tools = {str(name).strip().split("(", 1)[0] for name in tool_names}
        if tools is not None and "Bash" not in normalized_tools:
            reasons.append("tools has no Bash")

        if reasons:
            invalid.append(f"{path.relative_to(_PLUGIN_ROOT)}: {'; '.join(reasons)}")

    assert not invalid, "Invalid DH CLI token wiring:\n" + "\n".join(invalid)
