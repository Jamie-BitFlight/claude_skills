"""Focused contracts for DH CLI token wiring and resolver targets."""

from __future__ import annotations

import re
from pathlib import Path

from agent_profile.parser import _load_frontmatter_from_path, _normalize_skills

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_ROOT = _PLUGIN_ROOT / "agents"
_SKILLS_ROOT = _PLUGIN_ROOT / "skills"
_CLI_USAGE_SKILL = "dh:dh-cli-usage"
_CLI_USAGE_PATH = _SKILLS_ROOT / "dh-cli-usage" / "SKILL.md"
_CLI_TOKEN_RE = re.compile(r"<sam_cli\s*/>|<dh_scripts\s*/>")
_TAG_BLOCK_RE = r"<{tag}>\s*(?P<body>.*?)\s*</{tag}>"
_SKILL_DIR_PATH_RE = re.compile(r"\$\{[A-Z_]+_SKILL_DIR\}(?P<suffix>/[^\s\"]+)")


def _skill_body(skill_uri: str) -> str:
    name = skill_uri.removeprefix("dh:")
    if name == skill_uri:
        return ""
    path = _SKILLS_ROOT / name / "SKILL.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _tag_lines(body: str, tag: str) -> list[str]:
    match = re.search(_TAG_BLOCK_RE.format(tag=re.escape(tag)), body, flags=re.DOTALL)
    assert match is not None, f"{_CLI_USAGE_PATH.relative_to(_PLUGIN_ROOT)} has no <{tag}> block"
    return [line.strip() for line in match.group("body").splitlines() if line.strip()]


def _resolved_target(line: str) -> Path:
    match = _SKILL_DIR_PATH_RE.search(line)
    assert match is not None, f"resolver line has no skill-directory-relative target: {line!r}"
    return (_CLI_USAGE_PATH.parent / match.group("suffix").lstrip("/")).resolve()


def test_agents_reaching_cli_tokens_preload_resolver() -> None:
    """Agents reaching resolver-dependent CLI tokens preload the resolver and Bash."""
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


def test_dh_cli_usage_resolves_to_existing_plugin_targets() -> None:
    """Resolver paths point at the shipped CLI and scripts directory."""
    meta, body = _load_frontmatter_from_path(_CLI_USAGE_PATH)
    assert meta.get("name") == "dh-cli-usage"

    cli_targets = {_resolved_target(line) for line in _tag_lines(body, "sam_cli")}
    script_targets = {_resolved_target(line) for line in _tag_lines(body, "dh_scripts")}

    expected_cli = (_PLUGIN_ROOT / "sam_schema" / "cli.py").resolve()
    expected_scripts = (_PLUGIN_ROOT / "scripts").resolve()

    assert cli_targets == {expected_cli}
    assert expected_cli.is_file()
    assert script_targets == {expected_scripts}
    assert expected_scripts.is_dir()
