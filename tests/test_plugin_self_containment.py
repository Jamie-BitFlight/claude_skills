"""Guards that a plugin's own markdown never links or paths outside its directory.

A plugin distributed standalone into another repo (installed via the marketplace, not this
checkout) has no sibling `rules/`, `docs/`, or other plugin directories to resolve against. A
relative markdown link that walks upward past the plugin root — e.g.
`[x](../../../../rules/foo.md)` — silently 404s for that installer even though it resolves fine
inside this monorepo. The link guard runs over the git-tracked `.md` and `.markdown` files under
each plugin's `agents/`, `skills/` and `commands/` directories, the Markdown an agent reads from an
installed copy, including `href`/`src` in raw HTML, and fails on any `.mdx` file. READMEs,
`CLAUDE.md`, `AGENTS.md`, `docs/` and ADRs are repository documents, read only in this checkout,
so their repo-relative links resolve correctly and the guard skips them. It is a stopgap until
skilllint's own rule (bitflight-devops/skilllint#291) replaces it (#3971).

plugin-creator's `skills/lint/scripts/audit_runtime_escapes.py` also reports escaping links, and
neither check can replace the other. The audit ships inside the plugin for consumers to run, so it
cannot depend on this repo's tests. It scans only runtime roots (`skills/`, `agents/`,
`commands/`) and reports wider escape classes that still have open findings, so it cannot gate CI.
This guard is the CI gate for one class across those same runtime roots in every plugin.

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
import string
import subprocess
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

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
# Plugin subdirectories whose Markdown agents read from an installed copy at runtime.
_RUNTIME_DIRS = ("agents", "skills", "commands")
# marko parses JSX-wrapped Markdown in `.mdx` as an opaque HTML block, so its links are invisible.
_UNSUPPORTED_SUFFIXES = (".mdx",)
# A link leaves the plugin only through `..`, a root-absolute `/`, or a `file:` URL. A file with
# none of these in plain text, no link destination holding a `\`, `%` or `&` that could encode
# them, and no HTML `href=`/`src=`, cannot hold an escaping link, so the link guard skips it.
_MAY_ESCAPE_PATTERN = re.compile(
    r"(?:^|[\s(<:/])\.\.(?:[/)#>\s]|$)|(?:\]\(|\]:)\s*<?(?:/|file:|[^\s)>]*[\\%&])|\b(?:href|src)\s*=",
    re.IGNORECASE | re.MULTILINE,
)
# RFC 3986 unreserved characters: the only ones a percent escape may decode to without changing
# the URL's structure.
_UNRESERVED = frozenset(string.ascii_letters + string.digits + "-._~")
_PERCENT_ESCAPE_PATTERN = re.compile(r"%([0-9A-Fa-f]{2})")
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


def _runtime_markdown_files(plugin_dir: Path, files: list[Path]) -> list[Path]:
    """Select the Markdown files under `plugin_dir`'s `agents/`, `skills/` and `commands/`.

    Args:
        plugin_dir: Root directory of the plugin.
        files: Candidate file paths, normally `_TRACKED_PLUGIN_FILES`.

    Returns:
        The `.md` and `.markdown` files inside one of the plugin's runtime directories.
    """
    return [
        path for path in _markdown_files(plugin_dir, files) if path.relative_to(plugin_dir).parts[0] in _RUNTIME_DIRS
    ]


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


def _decode_markdown_destination(dest: str) -> str:
    """Decode a Markdown link destination to the URL a renderer writes into the href.

    marko 2.x unescapes backslashes in inline links only, and decodes no HTML entities, but a
    CommonMark renderer does both. A backslash left after unescaping is not a separator: the
    renderer percent-encodes it to `%5C`, which a browser keeps as a filename character.

    Args:
        dest: Link destination as marko returns it.

    Returns:
        `dest` with backslash escapes and HTML entities decoded.
    """
    return html.unescape(_BACKSLASH_ESCAPE_PATTERN.sub(r"\1", dest.strip()))


class _HtmlUrlAttributes(HTMLParser):
    """Collects `href`/`src` values from real start tags, with the line each tag starts on.

    Comments, `data-href`-style names and text inside other attributes are not attributes, so
    they are never collected. `HTMLParser` has already decoded entities in each value.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, _offset = self.getpos()
        self.found.extend((value or "", line) for name, value in attrs if name in {"href", "src"})


def _html_url_attributes(raw: str) -> list[tuple[str, int]]:
    """Return `(value, line)` for each `href`/`src` in `raw`, `line` counted from 1 within `raw`."""
    parser = _HtmlUrlAttributes()
    parser.feed(raw)
    parser.close()
    return parser.found


def _link_targets(nodes: list[tuple[Element, int]], content: str) -> list[tuple[str, str, int]]:
    """Collect every link destination in a walked document, as the URL a browser will follow.

    Args:
        nodes: `_walk_nodes` output for one document.
        content: The document's text, to turn block offsets into line numbers.

    Returns:
        `(destination, url, line)` for each Markdown link, image, reference definition, and HTML
        `href`/`src` attribute. `url` is what reaches the href. For HTML, a literal `\\` is read as
        `/`, as WHATWG URL parsing does, because CommonMark passes raw HTML through untouched.
    """
    # A `[text][label]` usage carries its definition's destination (backslash-unescaped by
    # marko, unlike the definition's), so it is checked through its `LinkRefDef` alone.
    defined = {_decode_markdown_destination(node.dest) for node, _start in nodes if isinstance(node, block.LinkRefDef)}
    targets: list[tuple[str, str, int]] = []
    for node, start in nodes:
        if isinstance(node, (inline.Link, inline.Image, block.LinkRefDef)):
            url = _decode_markdown_destination(node.dest)
            # `LinkRefDef` covers reference-style definitions (`[label]: url`), used or not.
            if isinstance(node, block.LinkRefDef) or url not in defined:
                targets.append((node.dest.strip(), url, _line_at(content, node.dest.strip(), start)))
        elif isinstance(node, (block.HTMLBlock, inline.InlineHTML)):
            if isinstance(node, block.HTMLBlock):
                raw = str(node.body)
                first_line = content.count("\n", 0, start) + 1
            else:
                raw = str(node.children)
                first_line = _line_at(content, raw, start)
            targets.extend(
                (value.strip(), value.strip().replace("\\", "/"), first_line + line - 1)
                for value, line in _html_url_attributes(raw)
            )
    return targets


def _decode_unreserved(path: str) -> str:
    """Percent-decode only unreserved characters, so `%2E` becomes `.` but `%2F` stays literal."""

    def decode(match: re.Match[str]) -> str:
        char = chr(int(match.group(1), 16))
        return char if char in _UNRESERVED else match.group(0)

    return _PERCENT_ESCAPE_PATTERN.sub(decode, path)


def _escaping_path(url: str, md_file: Path, root: Path) -> Path | None:
    """Resolve `url` from `md_file` as a browser would, and report it if it leaves `root`.

    Scheme, host and fragment are read from the raw URL, so an encoded `%3A`, `%2F` or `%23`
    never creates one. In the path, only unreserved characters are decoded. `%2E%2E` is then a
    dot segment, as WHATWG URL parsing treats it, while `%2F` and `%5C` stay characters inside a
    segment.

    Args:
        url: The URL as it reaches the href.
        md_file: File holding the link.
        root: Resolved plugin root.

    Returns:
        The resolved path of a `file:` URL, a root-absolute path, or a relative path that
        climbs above `root`. `None` for a path inside `root`, an external URL (another scheme,
        or a host), or a `${...}` substitution.
    """
    if url.startswith("${"):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        # Raised only for a malformed host (`//[x`), so the URL is external either way.
        return None
    if parts.scheme == "file":
        return Path(unquote(parts.path))
    if parts.scheme or parts.netloc:
        return None
    resolved = (md_file.parent / _decode_unreserved(parts.path)).resolve()
    return None if resolved.is_relative_to(root) else resolved


def find_self_containment_violations(
    plugin_dir: Path, md_files: list[Path] | None = None
) -> list[tuple[Path, int, str, Path]]:
    """Find markdown links under `plugin_dir` that resolve outside it.

    Args:
        plugin_dir: Root directory of the plugin to scan.
        md_files: Files to scan. Defaults to the plugin's git-tracked Markdown files under
            `agents/`, `skills/` and `commands/`.

    Returns:
        One `(file, line_number, link_target, resolved_path)` tuple per offending link. A
        `file:` URL always counts as leaving the plugin.
    """
    if md_files is None:
        md_files = _runtime_markdown_files(plugin_dir, _TRACKED_PLUGIN_FILES)
    violations: list[tuple[Path, int, str, Path]] = []
    resolved_root = plugin_dir.resolve()
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8").replace("\r\n", "\n")
        if not _MAY_ESCAPE_PATTERN.search(content):
            continue
        doc, starts = _parse(content)
        for target, url, line in _link_targets(list(_walk_nodes(doc, starts)), content):
            resolved = _escaping_path(url, md_file, resolved_root)
            if resolved is not None:
                violations.append((md_file, line, target, resolved))
    return violations


@pytest.mark.parametrize("plugin_dir", _PLUGIN_DIRS, ids=lambda p: p.name)
def test_plugin_has_no_links_outside_plugin(plugin_dir: Path) -> None:
    """Every markdown link in each plugin's `agents/`, `skills/` and `commands/` stays inside it."""
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


@pytest.mark.parametrize(
    ("dest", "escapes"),
    [
        ("https%3A%2F%2Fexample.com/../../outside.md", True),
        ("x%23/../../outside.md", True),
        ("%2E%2E/outside.md", True),
        ("%2Fetc/outside.md", False),
        ("https://example.com/../../outside.md", False),
        ("#section", False),
        ("//[malformed-host/../../outside.md", False),
    ],
    ids=[
        "encoded-scheme",
        "encoded-fragment",
        "encoded-dot-segment",
        "encoded-slash",
        "external",
        "fragment",
        "malformed-host",
    ],
)
def test_link_guard_reads_url_structure_before_percent_decoding(tmp_path: Path, dest: str, escapes: bool) -> None:
    """Scheme, host and fragment come from the raw URL; only unreserved path escapes are decoded."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n[x]({dest})\n")

    assert len(find_self_containment_violations(tmp_path, [md_file])) == int(escapes)


@pytest.mark.parametrize(
    "html",
    [
        '<!-- <a href="../../outside.md">x</a> -->',
        '<div data-href="../../outside.md" data-src="../../outside.png">x</div>',
        """<a title='href="../../outside.md"' href="./inside.md">x</a>""",
    ],
    ids=["comment", "data-attributes", "attribute-text"],
)
def test_link_guard_reads_only_real_html_href_and_src(tmp_path: Path, html: str) -> None:
    """Commented tags, `data-*` attributes and text inside other attributes are not links."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(f"Intro.\n\n{html}\n")

    assert find_self_containment_violations(tmp_path, [md_file]) == []


def test_link_guard_reports_the_start_line_of_a_multi_line_html_tag(tmp_path: Path) -> None:
    """An HTML link's line is its tag's start line, counted from the enclosing HTML block."""
    md_file = tmp_path / "doc.md"
    md_file.write_text(
        'Intro.\n\n<p>\n<a\n  href="../../outside.md">x</a>\n</p>\n\nText <a\nhref="../../other.md">y</a>\n'
    )

    found = find_self_containment_violations(tmp_path, [md_file])

    assert [(line, target) for _path, line, target, _resolved in found] == [
        (4, "../../outside.md"),
        (8, "../../other.md"),
    ]


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


def test_link_guard_selects_only_runtime_directories(tmp_path: Path) -> None:
    """Runtime Markdown is scanned; READMEs, `CLAUDE.md`, `docs/` and ADRs are repository documents."""
    runtime = [tmp_path / "agents/a.md", tmp_path / "skills/s/SKILL.md", tmp_path / "commands/c.markdown"]
    repo_docs = [tmp_path / "README.md", tmp_path / "CLAUDE.md", tmp_path / "docs/adrs/ADR-1.md"]

    assert _runtime_markdown_files(tmp_path, runtime + repo_docs) == runtime


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
