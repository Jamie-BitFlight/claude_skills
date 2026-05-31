"""Progressive Markdown navigation layer for the development-harness plugin.

Provides token-budget-aware section navigation, code block viewing, and
search over Markdown documents.

Typical usage::

    from progressive_markdown import MarkdownNavigator

    nav = MarkdownNavigator.from_markdown(content, source="README.md")
    toc = nav.map()  # paginated table of contents
    section = nav.view_section("h2.1")  # view a specific section
    code = nav.view_code("code_0001")  # view a code block
    hits = nav.search("authentication")  # search by keyword
"""

from __future__ import annotations

from .models import CodeBlockRef, MarkdownIndex, SectionRef
from .navigator import MarkdownNavigator

__all__ = ["CodeBlockRef", "MarkdownIndex", "MarkdownNavigator", "SectionRef"]
