"""Machine-consumed wiring contract for agents that can reach the DH CLI."""

from __future__ import annotations

import re
from pathlib import Path

from agent_profile.parser import _load_frontmatter_from_path, _normalize_skills

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_ROOT = _PLUGIN_ROOT / "agents"
_SKILLS_ROOT = _PLUGIN_ROOT / "skills"
_CLI_USAGE_SKILL = "dh:dh-cli-usage"
_CLI_TOKEN_RE = re.compile(r"<sam_cli\s*/>|<dh_scripts\s*/>")
_CLI_PATH_RE = re.compile(r"sam_schema[/\\.]cli\b|run_sam_cli\.py")


def _skill_body(skill_uri: str) -> str:
    name = skill_uri.removeprefix("dh:")
    if name == skill_uri:
        return ""
    path = _SKILLS_ROOT / name / "SKILL.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def test_agents_reaching_cli_preload_its_resolver_and_can_execute_it() -> None:
    """Agents that can encounter a DH CLI command load its resolver and expose Bash."""
    running: list[Path] = []
    invalid: list[str] = []

    for path in sorted(_AGENTS_ROOT.glob("*.md")):
        meta, body = _load_frontmatter_from_path(path)
        raw = path.read_text(encoding="utf-8")
        assert meta or not raw.lstrip().startswith("---"), f"{path.name}: frontmatter did not parse"

        skills = _normalize_skills(meta.get("skills"))
        unresolved = [
            uri
            for uri in skills
            if uri.startswith("dh:") and not (_SKILLS_ROOT / uri.removeprefix("dh:") / "SKILL.md").is_file()
        ]
        reachable_text = body + "".join(_skill_body(uri) for uri in skills)
        if not (_CLI_TOKEN_RE.search(reachable_text) or _CLI_PATH_RE.search(reachable_text)) and not unresolved:
            continue

        running.append(path)
        reasons: list[str] = []
        if _CLI_USAGE_SKILL not in skills:
            reasons.append(f"skills has no {_CLI_USAGE_SKILL}")

        tools = meta.get("tools")
        tool_names = tools if isinstance(tools, list) else str(tools).split(",")
        normalized_tools = {str(name).strip().split("(", 1)[0] for name in tool_names}
        if tools is not None and "Bash" not in normalized_tools:
            reasons.append("tools has no Bash")
        if unresolved:
            reasons.append(f"unresolved local skills: {unresolved}")

        if reasons:
            invalid.append(f"{path.relative_to(_PLUGIN_ROOT)}: {'; '.join(reasons)}")

    assert running, "No agent reaches the DH CLI; contract check would be vacuous."
    assert not invalid, "Invalid DH CLI agent wiring:\n" + "\n".join(invalid)
