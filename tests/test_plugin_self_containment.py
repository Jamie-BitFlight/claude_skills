"""Guards that a plugin's own markdown never links or paths outside its directory.

A plugin distributed standalone into another repo (installed via the marketplace, not this
checkout) has no sibling `rules/`, `docs/`, or other plugin directories to resolve against. A
relative markdown link that walks upward past the plugin root — e.g.
`[x](../../../../rules/foo.md)` — silently 404s for that installer even though it resolves fine
inside this monorepo. The link guard runs over every plugin's git-tracked `.md`, `.markdown`
and `.mdx` files. It is a stopgap until skilllint's own rule (bitflight-devops/skilllint#291)
replaces it (#3971).

plugin-creator's `skills/lint/scripts/audit_runtime_escapes.py` also reports escaping links, and
neither check can replace the other. The audit ships inside the plugin for consumers to run, so it
cannot depend on this repo's tests. It scans only runtime roots (`skills/`, `agents/`,
`commands/`) and reports wider escape classes that still have open findings, so it cannot gate CI.
This guard is the CI gate for one class across every plugin Markdown file, `README.md` and
`docs/` included.

A second guard catches leakage that isn't a markdown link at all: a runtime file (anything but
`MAINTENANCE.md`/`SKILL-GOALS.md`, which are design-time and never load at runtime) naming this
monorepo's own authoring-time locations by their repo-relative name (`rules/`, `.claude/hooks/`,
`docs/`) or by an absolute path under a user-specific filesystem root (`/Users/...`, `/home/...`).
Neither exists in an installed consumer's tree. It runs on `plugins/agent-orchestration` only:
its hits across the other plugins are tracked by #3426 and #3440 to #3443.

Both guards resolve paths via `Path.resolve()`, which fully dereferences symlinks; a plugin that
symlinks in shared content (a pattern this repo does use elsewhere) could produce misleading
results, though no plugin does so today.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import marko
import pytest
from marko import block, inline
from marko.element import Element
from marko.source import Source

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGINS_ROOT = _REPO_ROOT / "plugins"
_URL_PATTERN = re.compile(r"https?://\S+")
_ABS_PATH_PATTERN = re.compile(r"(?<![\w/{])/(?:Users|home|root)/[\w./-]*")
_AUTHORING_DIR_TOKENS = ("rules/", ".claude/hooks/", "docs/")
_DESIGN_TIME_FILENAMES = {"MAINTENANCE.md", "SKILL-GOALS.md"}
_MARKDOWN_SUFFIXES = (".md", ".markdown", ".mdx")
_EXCLUDED_LINK_PREFIXES = ("http://", "https://", "mailto:", "#", "${", "//")
# A link leaves the plugin only through `..`, a root-absolute `/`, or a `file:` URL. A file with
# none of these cannot hold an escaping link, so the link guard skips parsing it.
_MAY_ESCAPE_PATTERN = re.compile(
    r"(?:^|[\s(<:/])\.\.(?:[/)#>\s]|$)|(?:\]\(|\]:)\s*<?(?:/|file:)", re.IGNORECASE | re.MULTILINE
)


def _tracked_files(root: Path) -> list[Path]:
    """List the files git tracks under `root`, so local runs check what CI checks.

    Args:
        root: Directory inside this repository.

    Returns:
        Absolute paths of tracked files that exist in the working tree.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--", str(root)], cwd=_REPO_ROOT, capture_output=True, check=True, text=True
    ).stdout
    return [path for rel in listing.split("\0") if rel and (path := _REPO_ROOT / rel).is_file()]


_TRACKED_PLUGIN_FILES = _tracked_files(_PLUGINS_ROOT)
_PLUGIN_DIRS = sorted({
    _PLUGINS_ROOT / rel.parts[0]
    for rel in (path.relative_to(_PLUGINS_ROOT) for path in _TRACKED_PLUGIN_FILES)
    if len(rel.parts) > 1
})


def _markdown_files(plugin_dir: Path, files: list[Path]) -> list[Path]:
    """Select the Markdown files under `plugin_dir` from `files`.

    Args:
        plugin_dir: Root directory of the plugin.
        files: Candidate file paths, normally `_TRACKED_PLUGIN_FILES`.

    Returns:
        The `.md`, `.markdown` and `.mdx` files inside `plugin_dir`.
    """
    return [path for path in files if path.suffix in _MARKDOWN_SUFFIXES and path.is_relative_to(plugin_dir)]


class _PositionedParser(marko.Parser):
    """marko parser that records where each block element starts in the source.

    marko keeps no source positions. This is `marko.Parser.parse_source` (marko 2.x) with one
    addition: each block's start offset is stored in `starts`, keyed by `id(element)`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.starts: dict[int, int] = {}

    def parse_source(self, source: Source) -> list[block.BlockElement]:
        element_list = self._build_block_element_list()
        ast: list[block.BlockElement] = []
        while not source.exhausted:
            start = source.pos
            for ele_type in element_list:
                if ele_type.match(source):
                    result = ele_type.parse(source)
                    if not hasattr(result, "priority"):
                        result = ele_type(result)  # ty: ignore[too-many-positional-arguments]  # copied from marko, which ignores it too
                    self.starts[id(result)] = start
                    ast.append(result)
                    break
            else:
                break
        return ast


def _parse(content: str) -> tuple[block.Document, dict[int, int]]:
    """Parse Markdown and return the document with each block's start offset.

    Args:
        content: Markdown text with `\\n` line endings, as marko itself normalizes them.

    Returns:
        `(document, starts)`, where `starts` maps `id(block)` to its offset in `content`.
    """
    parser = _PositionedParser()
    return parser.parse(content), parser.starts


def _walk_nodes(node: Element, starts: dict[int, int], start: int = 0) -> Iterator[tuple[Element, int]]:
    """Depth-first walk of a marko AST, yielding every node with its enclosing block's offset.

    Args:
        node: Root node to walk (typically a parsed `Document`).
        starts: Block start offsets from `_parse`.
        start: Offset of the nearest enclosing block seen so far.

    Yields:
        `(node, offset)` for every node in document order, `node` included.
    """
    start = starts.get(id(node), start)
    yield node, start
    children = getattr(node, "children", None)
    if isinstance(children, list):
        for child in children:
            yield from _walk_nodes(child, starts, start)


def _line_at(content: str, needle: str, start: int) -> int:
    """Return the line of the first `needle` at or after `start`, else the line of `start`."""
    idx = content.find(needle, start)
    return content.count("\n", 0, start if idx == -1 else idx) + 1


def find_self_containment_violations(
    plugin_dir: Path, md_files: list[Path] | None = None
) -> list[tuple[Path, int, str, Path]]:
    """Find markdown links under `plugin_dir` that resolve outside it.

    Args:
        plugin_dir: Root directory of the plugin to scan.
        md_files: Files to scan. Defaults to the plugin's git-tracked Markdown files.

    Returns:
        One `(file, line_number, link_target, resolved_path)` tuple per offending link. A
        `file:` URL always counts as leaving the plugin.
    """
    if md_files is None:
        md_files = _markdown_files(plugin_dir, _TRACKED_PLUGIN_FILES)
    violations: list[tuple[Path, int, str, Path]] = []
    resolved_root = plugin_dir.resolve()
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8").replace("\r\n", "\n")
        if not _MAY_ESCAPE_PATTERN.search(content):
            continue
        doc, starts = _parse(content)
        for node, start in _walk_nodes(doc, starts):
            # `LinkRefDef` covers reference-style definitions (`[label]: url`), used or not.
            if not isinstance(node, (inline.Link, inline.Image, block.LinkRefDef)):
                continue
            target = node.dest.strip()
            if target.startswith(_EXCLUDED_LINK_PREFIXES):
                continue
            if target.lower().startswith("file:"):
                resolved = Path(target)
            else:
                resolved = (md_file.parent / target.split("#", 1)[0]).resolve()
                if resolved.is_relative_to(resolved_root):
                    continue
            found = (md_file, _line_at(content, target, start), target, resolved)
            # A `[text][label]` usage carries its definition's dest, and both locate to the
            # definition's line; report that link once.
            if found not in violations:
                violations.append(found)
    return violations


@pytest.mark.parametrize("plugin_dir", _PLUGIN_DIRS, ids=lambda p: p.name)
def test_plugin_has_no_links_outside_plugin(plugin_dir: Path) -> None:
    """Every markdown link under each `plugins/<name>/` resolves inside that plugin."""
    violations = find_self_containment_violations(plugin_dir)

    assert not violations, "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{line}: [{target}] resolves outside the plugin, to {resolved}"
        for path, line, target, resolved in violations
    )


def test_link_guard_reports_the_links_own_line_past_earlier_duplicates(tmp_path: Path) -> None:
    """The reported line is the link's, not an earlier fenced or prose copy of its target text."""
    md_file = tmp_path / "doc.md"
    md_file.write_text("```text\n[x](../out.md)\n```\n\nPlain ../out.md mention.\n\n- item\n  - see [x](../out.md)\n")

    violations = find_self_containment_violations(tmp_path, [md_file])

    assert [(line, target) for _path, line, target, _resolved in violations] == [(8, "../out.md")]


@pytest.mark.parametrize(
    "link",
    ["[x](file:///Users/me/repo/rules/a.md)", "[x](/etc/rules/a.md)", "[x][l]\n\n[l]: ../../rules/a.md"],
    ids=["file-url", "root-absolute", "reference-definition"],
)
def test_link_guard_flags_escaping_link_forms(tmp_path: Path, link: str) -> None:
    """`file:` URLs, root-absolute paths and reference definitions that leave the plugin are flagged."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n{link}\n")

    assert len(find_self_containment_violations(tmp_path, [md_file])) == 1


def test_markdown_file_selection_covers_markdown_and_mdx(tmp_path: Path) -> None:
    """`.markdown` and `.mdx` files are scanned alongside `.md`; other files and other dirs are not."""
    files = [tmp_path / "a.md", tmp_path / "b.markdown", tmp_path / "c.mdx", tmp_path / "d.txt", Path("/other/e.md")]

    assert _markdown_files(tmp_path, files) == files[:3]


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
    for md_file in _markdown_files(plugin_dir, _TRACKED_PLUGIN_FILES):
        if md_file.name in _DESIGN_TIME_FILENAMES:
            continue
        content = md_file.read_text(encoding="utf-8").replace("\r\n", "\n")
        doc, starts = _parse(content)
        texts: list[tuple[str, int]] = []
        for node, start in _walk_nodes(doc, starts):
            if isinstance(node, (inline.Link, inline.Image, block.LinkRefDef)):
                texts.append((node.dest, start))
            elif isinstance(node, inline.RawText):
                texts.append((node.children, start))
        for text, start in texts:
            stripped = _URL_PATTERN.sub("", text)
            abs_match = _ABS_PATH_PATTERN.search(stripped)
            if abs_match:
                violations.append((md_file, _line_at(content, text, start), abs_match.group(0), "absolute-path"))
                continue
            for token in _AUTHORING_DIR_TOKENS:
                if token in stripped:
                    violations.append((md_file, _line_at(content, text, start), token, "authoring-repo-relative-path"))
                    break
    return violations


def test_agent_orchestration_has_no_authoring_repo_leakage() -> None:
    """No runtime file under `plugins/agent-orchestration/` names this repo's own tree."""
    plugin_dir = _REPO_ROOT / "plugins" / "agent-orchestration"
    violations = find_authoring_repo_leakage(plugin_dir)

    assert not violations, "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{line}: {kind} — {text!r}" for path, line, text, kind in violations
    )
