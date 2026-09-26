"""Every relative Markdown link in the plugin resolves to a file or directory.

skilllint validates component frontmatter, not links inside references/, so a
broken link into the rule corpus or to an agent otherwise goes unnoticed.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from markdown_it import MarkdownIt

ROOT = Path(__file__).parents[1]


def relative_links() -> list[tuple[str, str]]:
    """(source file relative to the plugin root, link target) for each relative link."""
    links = []
    parser = MarkdownIt()
    for path in sorted(ROOT.rglob("*.md")):
        for token in parser.parse(path.read_text(encoding="utf-8")):
            for child in token.children or []:
                href = child.attrGet("href") if child.type == "link_open" else None
                if not isinstance(href, str):
                    continue
                parts = urlsplit(href)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                links.append((path.relative_to(ROOT).as_posix(), unquote(parts.path)))
    return links


def test_links_are_found() -> None:
    assert relative_links(), "no relative links parsed from the plugin's Markdown"


@pytest.mark.parametrize(("source", "target"), relative_links())
def test_relative_link_resolves(source: str, target: str) -> None:
    assert ((ROOT / source).parent / target).exists(), f"{source} links to missing {target}"
