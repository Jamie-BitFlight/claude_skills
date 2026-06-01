"""Markdown parsing using markdown-it-py.

Provides a Protocol-based parser interface and the default MarkdownItParser
implementation. The ParserResult is an internal intermediate; all public
types live in models.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from collections.abc import Mapping

    from markdown_it.token import Token

__all__ = ["MarkdownItParser", "MarkdownParser", "ParserResult"]


@dataclass(slots=True)
class ParserResult:
    """Intermediate result from parsing a markdown document.

    This type is internal to the progressive_markdown package — callers
    use MarkdownDocument (via indexer.py) for all external access.

    Args:
        source: Human-readable source label.
        raw_markdown: Original markdown text.
        lines: Source lines split from raw_markdown.
        tokens: Block-level token list from markdown-it-py.
        env: Environment dict populated by the parser (e.g. references).
    """

    source: str
    raw_markdown: str
    lines: list[str]
    tokens: list[Token]
    env: dict[str, Any] = field(default_factory=dict)


class MarkdownParser(Protocol):
    """Protocol for markdown parsers consumed by the indexer."""

    def parse(self, source: str, markdown: str) -> ParserResult:
        """Parse markdown text and return a ParserResult.

        Args:
            source: Human-readable source label (e.g. filename).
            markdown: Raw markdown text to parse.

        Returns:
            ParserResult containing tokens and environment data.
        """
        ...  # pragma: no cover


class MarkdownItParser:
    r"""Default markdown parser using markdown-it-py.

    Args:
        preset: markdown-it-py preset name (e.g. ``"commonmark"``).
        options_update: Additional options to merge into the preset.

    Example::

        parser = MarkdownItParser(preset="commonmark")
        result = parser.parse("README.md", "# Hello\\n\\nWorld.")
    """

    def __init__(
        self,
        preset: str = "commonmark",
        options_update: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialise with a preset and optional option overrides.

        Args:
            preset: markdown-it-py preset string.
            options_update: Dict of options to merge into the preset configuration.
        """
        self._md = MarkdownIt(preset, options_update or {})

    def parse(self, source: str, markdown: str) -> ParserResult:
        """Parse markdown text and return a ParserResult.

        Args:
            source: Human-readable source label (e.g. filename).
            markdown: Raw markdown text to parse.

        Returns:
            ParserResult with block-level tokens and resolved references.
        """
        env: dict[str, Any] = {}
        tokens = self._md.parse(markdown, env)
        lines = markdown.splitlines()
        return ParserResult(
            source=source,
            raw_markdown=markdown,
            lines=lines,
            tokens=tokens,
            env=env,
        )
