"""Guards that a plugin's own markdown never links or paths outside its directory.

A plugin distributed standalone into another repo (installed via the marketplace, not this
checkout) has no sibling `rules/`, `docs/`, or other plugin directories to resolve against. A
relative markdown link that walks upward past the plugin root — e.g.
`[x](../../../../rules/foo.md)` — silently 404s for that installer even though it resolves fine
inside this monorepo. The link guard runs over every plugin's git-tracked `.md` and `.markdown`
files, including `href`/`src` in raw HTML, and fails on any `.mdx` file. It is a stopgap until
skilllint's own rule (bitflight-devops/skilllint#291) replaces it (#3971).

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

import html
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

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
_MARKDOWN_SUFFIXES = (".md", ".markdown")
# marko parses JSX-wrapped Markdown in `.mdx` as an opaque HTML block, so its links are invisible.
_UNSUPPORTED_SUFFIXES = (".mdx",)
_EXCLUDED_LINK_PREFIXES = ("http://", "https://", "mailto:", "#", "${", "//")
# A link leaves the plugin only through `..`, a root-absolute `/`, or a `file:` URL. A file with
# none of these in plain text, no link destination holding a `\`, `%` or `&` that could encode
# them, and no HTML `href=`/`src=`, cannot hold an escaping link, so the link guard skips it.
_MAY_ESCAPE_PATTERN = re.compile(
    r"(?:^|[\s(<:/])\.\.(?:[/)#>\s]|$)|(?:\]\(|\]:)\s*<?(?:/|file:|[^\s)>]*[\\%&])|\b(?:href|src)\s*=",
    re.IGNORECASE | re.MULTILINE,
)
# `href`/`src` attribute values in raw HTML, double-quoted, single-quoted or unquoted.
_HTML_URL_ATTR_PATTERN = re.compile(r"""\b(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", re.IGNORECASE)
# CommonMark backslash escapes: a backslash before ASCII punctuation.
_BACKSLASH_ESCAPE_PATTERN = re.compile(r"\\([!-/:-@\[-`{-~])")


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


def _unsupported_files(files: list[Path]) -> list[Path]:
    """Select the files the link guard cannot parse, so it fails closed on them.

    Args:
        files: Candidate file paths, normally `_TRACKED_PLUGIN_FILES`.

    Returns:
        The `.mdx` files in `files`.
    """
    return [path for path in files if path.suffix in _UNSUPPORTED_SUFFIXES]


def _markdown_files(plugin_dir: Path, files: list[Path]) -> list[Path]:
    """Select the Markdown files under `plugin_dir` from `files`.

    Args:
        plugin_dir: Root directory of the plugin.
        files: Candidate file paths, normally `_TRACKED_PLUGIN_FILES`.

    Returns:
        The `.md` and `.markdown` files inside `plugin_dir`.
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


def _decode_destination(dest: str) -> str:
    """Decode a Markdown link destination the way a renderer and browser will before resolving it.

    marko 2.x unescapes backslashes in inline links only, and decodes neither HTML entities
    nor percent-encoding, but a renderer decodes the first two and a browser resolves
    `%2E%2E/` as `../`. A backslash left after unescaping is not a separator: a CommonMark
    renderer percent-encodes it to `%5C` in the href, which a browser keeps as a filename
    character.

    Args:
        dest: Link destination as marko returns it.

    Returns:
        `dest` with backslash escapes, HTML entities and percent-encoding decoded.
    """
    return unquote(html.unescape(_BACKSLASH_ESCAPE_PATTERN.sub(r"\1", dest)))


def _decode_html_url(value: str) -> str:
    """Decode a raw-HTML `href`/`src` value the way a browser will before resolving it.

    CommonMark passes raw HTML through untouched, so no backslash unescaping applies. A browser
    decodes entities and then, following WHATWG URL parsing, reads each literal `\\` in a path
    as `/`. A `%5C` stays a filename character, so separators are normalized before
    percent-decoding.

    Args:
        value: Attribute value as written in the HTML.

    Returns:
        `value` with entities decoded, `\\` read as `/`, and percent-encoding decoded.
    """
    return unquote(html.unescape(value).replace("\\", "/"))


def _link_targets(nodes: list[tuple[Element, int]]) -> list[tuple[str, str, int]]:
    """Collect every link destination in a walked document, with its enclosing block's offset.

    Args:
        nodes: `_walk_nodes` output for one document.

    Returns:
        `(destination, decoded, offset)` for each Markdown link, image, reference definition,
        and HTML `href`/`src` attribute value, `decoded` as a browser will resolve it.
    """
    # A `[text][label]` usage carries its definition's destination (backslash-unescaped by
    # marko, unlike the definition's), so it is checked through its `LinkRefDef` alone.
    defined = {_decode_destination(node.dest.strip()) for node, _start in nodes if isinstance(node, block.LinkRefDef)}
    targets: list[tuple[str, str, int]] = []
    for node, start in nodes:
        if isinstance(node, (inline.Link, inline.Image)):
            decoded = _decode_destination(node.dest.strip())
            if decoded not in defined:
                targets.append((node.dest.strip(), decoded, start))
        elif isinstance(node, block.LinkRefDef):
            # Covers reference-style definitions (`[label]: url`), used or not.
            targets.append((node.dest.strip(), _decode_destination(node.dest.strip()), start))
        elif isinstance(node, (block.HTMLBlock, inline.InlineHTML)):
            raw = str(node.body if isinstance(node, block.HTMLBlock) else node.children)
            for match in _HTML_URL_ATTR_PATTERN.finditer(raw):
                value = (match.group(1) or match.group(2) or match.group(3) or "").strip()
                targets.append((value, _decode_html_url(value), start))
    return targets


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
        targets = _link_targets(list(_walk_nodes(doc, starts)))
        for target, decoded, start in targets:
            if decoded.startswith(_EXCLUDED_LINK_PREFIXES):
                continue
            if decoded.lower().startswith("file:"):
                resolved = Path(decoded)
            else:
                resolved = (md_file.parent / decoded.split("#", 1)[0]).resolve()
                if resolved.is_relative_to(resolved_root):
                    continue
            violations.append((md_file, _line_at(content, target, start), target, resolved))
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


_ENCODED_ESCAPES = [
    r"\.\./outside.md",
    "%2E%2E/outside.md",
    "%2e%2e/outside.md",
    "&#46;&#46;/outside.md",
    "&period;&period;/outside.md",
    r"\/etc/outside.md",
    "&#47;etc/outside.md",
    "file&#58;///Users/me/outside.md",
]


@pytest.mark.parametrize("dest", _ENCODED_ESCAPES)
@pytest.mark.parametrize("form", ["[x]({dest})", "[x][r]\n\n[r]: {dest}"], ids=["inline", "reference"])
def test_link_guard_flags_escaped_and_encoded_destinations(tmp_path: Path, form: str, dest: str) -> None:
    """Backslash-escaped, entity- and percent-encoded destinations that decode to an escape are flagged."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n{form.format(dest=dest)}\n")

    assert len(find_self_containment_violations(tmp_path, [md_file])) == 1


@pytest.mark.parametrize(
    "html",
    [
        '<a href="../../outside.md">x</a>',
        '<p align="center"><img src="../../outside.png"></p>',
        "Text <img src='/etc/outside.png'/> more.",
        "<a href=&quot;x&quot; HREF=../../outside.md>x</a>",
        '<a href="&#46;&#46;/outside.md">x</a>',
    ],
    ids=["inline-href", "block-src", "inline-src-root-absolute", "unquoted-uppercase", "entity-encoded"],
)
def test_link_guard_flags_escaping_html_href_and_src(tmp_path: Path, html: str) -> None:
    """`href` and `src` attributes in HTML blocks and inline HTML that leave the plugin are flagged."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n{html}\n")

    assert len(find_self_containment_violations(tmp_path, [md_file])) == 1


@pytest.mark.parametrize(
    "html",
    ['<a href="..\\..\\outside.md">x</a>', '<img src="..&#92;..&#92;outside.png">'],
    ids=["literal-backslash", "entity-backslash"],
)
def test_link_guard_treats_html_backslash_as_path_separator(tmp_path: Path, html: str) -> None:
    """A browser reads `\\` in an `href`/`src` path as `/`, so `..\\..\\` leaves the plugin."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n{html}\n")

    assert len(find_self_containment_violations(tmp_path, [md_file])) == 1


@pytest.mark.parametrize(
    "text",
    ["[x](..\\..\\outside.md)", "[x](..\\\\..\\\\outside.md)", '<a href="..%5C..%5Coutside.md">x</a>'],
    ids=["markdown-escaped-dots", "markdown-literal-backslash", "html-percent-encoded-backslash"],
)
def test_link_guard_does_not_treat_encoded_backslash_as_separator(tmp_path: Path, text: str) -> None:
    """A backslash that reaches the href as `%5C` is a filename character, not a separator.

    A CommonMark renderer percent-encodes a backslash left in a destination after unescaping,
    and a browser splits paths on a literal `\\` only.
    """
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n{text}\n")

    assert find_self_containment_violations(tmp_path, [md_file]) == []


def test_link_guard_passes_html_links_inside_the_plugin(tmp_path: Path) -> None:
    """HTML `href`/`src` values that stay in the plugin, or are URLs, are not flagged."""
    md_file = tmp_path / "doc.md"
    md_file.write_text('<a href="./a.md">a</a> <img src="https://example.com/x.png">\n')

    assert find_self_containment_violations(tmp_path, [md_file]) == []


def test_mdx_files_are_rejected_not_scanned(tmp_path: Path) -> None:
    """marko parses JSX-wrapped Markdown as an HTML block, so an `.mdx` file fails closed."""
    files = [tmp_path / "a.md", tmp_path / "b.mdx"]

    assert _unsupported_files(files) == [tmp_path / "b.mdx"]


def test_no_tracked_plugin_file_is_mdx() -> None:
    """MDX is not supported by this guard; see #3971."""
    unsupported = _unsupported_files(_TRACKED_PLUGIN_FILES)

    assert not unsupported, "MDX is not supported by this guard; see #3971:\n" + "\n".join(
        str(path.relative_to(_REPO_ROOT)) for path in unsupported
    )


def test_markdown_file_selection_covers_markdown(tmp_path: Path) -> None:
    """`.markdown` files are scanned alongside `.md`; `.mdx`, other files and other dirs are not."""
    files = [tmp_path / "a.md", tmp_path / "b.markdown", tmp_path / "c.mdx", tmp_path / "d.txt", Path("/other/e.md")]

    assert _markdown_files(tmp_path, files) == files[:2]


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
