"""Guards that a plugin's own markdown never links or paths outside its directory.

A plugin distributed standalone into another repo (installed via the marketplace, not this
checkout) has no sibling `rules/`, `docs/`, or other plugin directories to resolve against. A
relative markdown link that walks upward past the plugin root — e.g.
`[x](../../../../rules/foo.md)` — silently 404s for that installer even though it resolves fine
inside this monorepo. `plugins/agent-orchestration` had exactly this defect (fixed alongside this
test); this guard keeps it from recurring there.

A second guard catches leakage that isn't a markdown link at all: a runtime file (anything but
`MAINTENANCE.md`/`SKILL-GOALS.md`, which are design-time and never load at runtime) naming this
monorepo's own authoring-time locations by their repo-relative name (`rules/`, `.claude/hooks/`,
`docs/`) or by an absolute path under a user-specific filesystem root (`/Users/...`, `/home/...`).
Neither exists in an installed consumer's tree.

Both guards resolve paths via `Path.resolve()`, which fully dereferences symlinks; a plugin that
symlinks in shared content (a pattern this repo does use elsewhere) could produce misleading
results, though no plugin does so today.
"""

from __future__ import annotations

import re
from pathlib import Path

import marko
from marko import inline
from marko.element import Element

_REPO_ROOT = Path(__file__).resolve().parent.parent
_URL_PATTERN = re.compile(r"https?://\S+")
_ABS_PATH_PATTERN = re.compile(r"(?<![\w/{])/(?:Users|home|root)/[\w./-]*")
_AUTHORING_DIR_TOKENS = ("rules/", ".claude/hooks/", "docs/")
_DESIGN_TIME_FILENAMES = {"MAINTENANCE.md", "SKILL-GOALS.md"}
_EXCLUDED_LINK_PREFIXES = ("http://", "https://", "mailto:", "#", "${", "//")

_markdown = marko.Markdown()


def _walk_nodes(node: Element) -> list[Element]:
    """Depth-first walk of a marko AST, yielding every block and inline node.

    Args:
        node: Root node to walk (typically a parsed `Document`).

    Returns:
        Every node in the tree, `node` included, in document order.
    """
    nodes = [node]
    children = getattr(node, "children", None)
    if isinstance(children, list):
        for child in children:
            nodes.extend(_walk_nodes(child))
    return nodes


def _line_for(content: str, needle: str, start: int) -> tuple[int, int]:
    """Locate `needle` in `content` and translate its offset to a line number.

    Args:
        content: Full file text.
        needle: Literal substring to locate (a link target or raw text run).
        start: Offset to search from first, to keep repeated needles in document order.

    Returns:
        `(line_number, next_start)`. Falls back to searching from the top of the file if
        `needle` isn't found at or after `start`; `line_number` is `0` if it isn't found at all.
    """
    idx = content.find(needle, start)
    if idx == -1:
        idx = content.find(needle)
    if idx == -1:
        return 0, start
    return content.count("\n", 0, idx) + 1, idx + len(needle)


def find_self_containment_violations(plugin_dir: Path) -> list[tuple[Path, int, str, Path]]:
    """Find markdown links under `plugin_dir` that resolve outside it.

    Args:
        plugin_dir: Root directory of the plugin to scan.

    Returns:
        One `(file, line_number, link_target, resolved_path)` tuple per offending link.
    """
    violations: list[tuple[Path, int, str, Path]] = []
    resolved_root = plugin_dir.resolve()
    for md_file in plugin_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        doc = _markdown.parse(content)
        targets = [node.dest for node in _walk_nodes(doc) if isinstance(node, (inline.Link, inline.Image))]
        # Reference-style definitions (`[label]: url`) that no `[text][label]` usage resolves to
        # are otherwise invisible to the AST walk above, since marko only emits a `Link`/`Image`
        # node where a definition is actually used.
        targets.extend(dest for dest, _title in doc.link_ref_defs.values())
        cursor = 0
        for raw_target in targets:
            target = raw_target.strip()
            if target.startswith(_EXCLUDED_LINK_PREFIXES):
                continue
            resolved = (md_file.parent / target.split("#", 1)[0]).resolve()
            try:
                resolved.relative_to(resolved_root)
            except ValueError:
                line_number, cursor = _line_for(content, target, cursor)
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


def find_authoring_repo_leakage(plugin_dir: Path) -> list[tuple[Path, int, str, str]]:
    """Find runtime-file mentions of this monorepo's own authoring-time locations.

    Args:
        plugin_dir: Root directory of the plugin to scan.

    Returns:
        One `(file, line_number, matched_text, kind)` tuple per offending mention. Design-time
        files (`MAINTENANCE.md`, `SKILL-GOALS.md`) are exempt. Text inside code spans and code
        blocks is exempt, since it isn't authored prose or a live link.
    """
    violations: list[tuple[Path, int, str, str]] = []
    for md_file in plugin_dir.rglob("*.md"):
        if md_file.name in _DESIGN_TIME_FILENAMES:
            continue
        content = md_file.read_text(encoding="utf-8")
        doc = _markdown.parse(content)
        texts: list[str] = []
        for node in _walk_nodes(doc):
            if isinstance(node, (inline.Link, inline.Image)):
                texts.append(node.dest)
            elif isinstance(node, inline.RawText):
                texts.append(node.children)
        # Reference-style definitions (`[label]: url`) that no `[text][label]` usage resolves to
        # are otherwise invisible to the AST walk above.
        texts.extend(dest for dest, _title in doc.link_ref_defs.values())
        cursor = 0
        for text in texts:
            stripped = _URL_PATTERN.sub("", text)
            abs_match = _ABS_PATH_PATTERN.search(stripped)
            if abs_match:
                line_number, cursor = _line_for(content, text, cursor)
                violations.append((md_file, line_number, abs_match.group(0), "absolute-path"))
                continue
            for token in _AUTHORING_DIR_TOKENS:
                if token in stripped:
                    line_number, cursor = _line_for(content, text, cursor)
                    violations.append((md_file, line_number, token, "authoring-repo-relative-path"))
                    break
    return violations


def test_agent_orchestration_has_no_authoring_repo_leakage() -> None:
    """No runtime file under `plugins/agent-orchestration/` names this repo's own tree."""
    plugin_dir = _REPO_ROOT / "plugins" / "agent-orchestration"
    violations = find_authoring_repo_leakage(plugin_dir)

    assert not violations, "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{line}: {kind} — {text!r}" for path, line, text, kind in violations
    )
