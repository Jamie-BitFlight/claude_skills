"""Guards that a plugin's own markdown never links or paths outside its directory.

A plugin distributed standalone into another repo (installed via the marketplace, not this
checkout) has no sibling `rules/`, `docs/`, or other plugin directories to resolve against. A
relative markdown link that walks upward past the plugin root — e.g.
`[x](../../../../rules/foo.md)` — silently 404s for that installer even though it resolves fine
inside this monorepo. `plugins/agent-orchestration` had exactly this defect (fixed alongside this
test); this guard keeps it from recurring there.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def find_self_containment_violations(plugin_dir: Path) -> list[tuple[Path, int, str, Path]]:
    """Find markdown links under `plugin_dir` that resolve outside it.

    Args:
        plugin_dir: Root directory of the plugin to scan.

    Returns:
        One `(file, line_number, link_target, resolved_path)` tuple per offending link.
    """
    violations: list[tuple[Path, int, str, Path]] = []
    for md_file in plugin_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        for match in _LINK_PATTERN.finditer(content):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#", "${")):
                continue
            resolved = (md_file.parent / target.split("#", 1)[0]).resolve()
            try:
                resolved.relative_to(plugin_dir.resolve())
            except ValueError:
                line_number = content.count("\n", 0, match.start()) + 1
                violations.append((md_file, line_number, target, resolved))
    return violations


def test_agent_orchestration_has_no_links_outside_plugin() -> None:
    """Every markdown link under `plugins/agent-orchestration/` resolves inside the plugin."""
    plugin_dir = _REPO_ROOT / "plugins" / "agent-orchestration"
    violations = find_self_containment_violations(plugin_dir)

    assert not violations, "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{line}: [{target}] resolves outside the plugin, to {resolved}"
        for path, line, target, resolved in violations
    )
