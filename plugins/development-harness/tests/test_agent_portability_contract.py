"""Stable portability contracts for installed development-harness agents."""

from __future__ import annotations

import re
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_AGENTS_ROOT = _PLUGIN_ROOT / "agents"

_REPO_FLAG_RE = re.compile(
    r"(?:^|\s)(?:-R|--repo)(?:=|\s+)(?P<slug>[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*)"
)
_PLUGIN_ROOT_VAR_RE = re.compile(r"\$\{(?:[A-Z]+_)?PLUGIN_ROOT\}")
_PLUGIN_SKILL_PATH_RE = re.compile(r"plugins/[\w.-]+/skills/[\w.-]+/SKILL\.md")


def _agent_texts() -> list[tuple[Path, str]]:
    return [(path, path.read_text(encoding="utf-8")) for path in sorted(_AGENTS_ROOT.glob("*.md"))]


def test_agents_do_not_hardcode_repository_targets() -> None:
    """Installed agents must operate on the caller's repository, not the author's."""
    offenders = [
        f"{path.relative_to(_PLUGIN_ROOT)}: {match.group('slug')}"
        for path, text in _agent_texts()
        for match in _REPO_FLAG_RE.finditer(text)
    ]

    assert not offenders, "Agent commands hard-code repository targets:\n" + "\n".join(offenders)


def test_agents_do_not_bind_runtime_paths_to_the_authoring_checkout() -> None:
    """Agent runtime instructions avoid checkout-specific plugin and skill paths."""
    offenders: list[str] = []
    for path, text in _agent_texts():
        if _PLUGIN_ROOT_VAR_RE.search(text):
            offenders.append(f"{path.relative_to(_PLUGIN_ROOT)}: plugin-root variable")
        if _PLUGIN_SKILL_PATH_RE.search(text):
            offenders.append(f"{path.relative_to(_PLUGIN_ROOT)}: plugin-rooted skill path")

    assert not offenders, "Non-portable agent runtime paths:\n" + "\n".join(offenders)
