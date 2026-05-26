"""FastMCP 3.x server exposing all backlog operations as MCP tools."""

from __future__ import annotations

import argparse
import asyncio
import collections
import contextlib
import dataclasses
import json as _json
import logging as _logging
import os as _os
import re as _re
import sqlite3
import sys
import time as _time
from datetime import UTC, datetime as _datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, TypeAlias

import dh_paths as _dh_paths
import dispatch_schema as _ds
import tiktoken
from fastmcp import Context, FastMCP
from github import GithubException as _GithubException
from mcp.types import ToolAnnotations
from pydantic import Field
from ruamel.yaml import YAML as _YAML, YAMLError as _YAMLError

from . import models as _models, operations
from .artifact_provider import ArtifactBackend, ItemId, create_artifact_provider
from .artifact_provider_local import LocalFilesystemArtifactProvider
from .artifact_registry import ArtifactRegistry
from .backend_protocol import IssueNode as _IssueNode, get_config as _get_config
from .dispatch_state import DispatchStateManager as _DispatchStateManager
from .models import (
    ArtifactContent,
    ArtifactEntry,
    ArtifactStatus,
    ArtifactType,
    BackendAvailability as _BackendAvailability,
    BackendStatus as _BackendStatus,
    BacklogError,
    DispatchItemRecord as _DispatchItemRecord,
    DispatchSpawnSummary as _DispatchSpawnSummary,
    DispatchWaveRecord as _DispatchWaveRecord,
    DispatchWaveSummary as _DispatchWaveSummary,
    GitHubUnavailableError,
    Output,
    RegisterResult,
    init as _init_models,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .operations import ImpactRadiusItem as _ImpactRadiusItem

EffortLevel: TypeAlias = Literal["low", "medium", "high", "max"]

# Token budget for auto-pagination in backlog_list: 4400 tokens (cl100k_base encoding).
_LIST_TOKEN_BUDGET = 4_400
# Token budget for auto-compacting backlog_view: 4000 tokens (cl100k_base encoding).
# When the full response exceeds this budget and the caller has not requested a
# specific section, backlog_view returns a compact section-directory form so the
# caller can request only the sections it needs.
_VIEW_TOKEN_BUDGET = 4_000
_GROOMED_SECTION_TYPE = "groomed"
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")

# Heuristic threshold for the body-length pre-check in backlog_view.
# If result.body alone exceeds this many characters the full JSON response is
# almost certainly over _VIEW_TOKEN_BUDGET (cl100k_base averages ~4 chars/token,
# so _VIEW_TOKEN_BUDGET tokens ≈ 16 000 chars; body is only part of the payload).
# The precise token count is still computed for borderline cases.
_VIEW_BODY_CHARS_THRESHOLD = _VIEW_TOKEN_BUDGET * 4


def _token_count(serialised: str) -> int:
    """Count cl100k_base tokens in an already-serialized JSON string.

    Args:
        serialised: A JSON string produced by json.dumps.

    Returns:
        Token count as an integer.
    """
    return len(_enc.encode(serialised))


# Fields searched by default when no field-specific prefix is given.
# ``body`` contains the full item content (description + all section entries)
# built by operations._build_item_body so that plain-text and regex searches
# cover the complete backlog item, not just the 4 metadata fields.
_SEARCH_FIELDS: tuple[str, ...] = ("title", "section", "topic", "type", "body")

# Minimum length for a valid /pattern/ regex term (e.g. "/x/" has length 3).
_REGEX_SLASH_MIN_LEN = 2

# All fields that callers can request via the fields= parameter on backlog_list.
# Fields in _DEFAULT_ITEM_FIELDS are returned when no fields= parameter is given.
# ``body`` is omitted from the default set because it makes responses large.
_AVAILABLE_FIELDS: tuple[str, ...] = ("issue", "title", "section", "topic", "type", "status", "body")
_DEFAULT_ITEM_FIELDS: frozenset[str] = frozenset(_AVAILABLE_FIELDS) - {"body"}

# item_depth value that includes the full body in each returned item.
_ITEM_DEPTH_FULL = 3

# Beads integration removed — was auto-installing @beads/bd via npm during the
# FastMCP lifespan hook, blocking MCP initialization for 20+ seconds when the
# download hung.  Beads local storage for task tracking is a future feature;
# re-add as an opt-in integration (e.g. DH_ENABLE_BEADS=1) when actual tool
# calls depend on it.


def _apply_fields_projection(
    items: list[dict[str, object]] | list[dict[str, str | bool]], fields: list[str] | None, item_depth: int, out: Output
) -> list[dict[str, object]]:
    """Project item dicts to the requested fields.

    When ``fields`` is provided, each item is reduced to only those keys.
    Unknown field names are emitted as warnings on ``out``.
    When ``fields`` is None, ``body`` is excluded from the default response
    unless ``item_depth`` is at the full-content level (``_ITEM_DEPTH_FULL``),
    which already adds body intentionally.

    Args:
        items: Enriched item dicts to project.
        fields: Caller-requested field names, or None for the default shape.
        item_depth: The item_depth parameter value from the tool call.
        out: Output collector for warnings.

    Returns:
        Projected item dicts.
    """
    if fields is not None:
        unknown = [f for f in fields if f not in _AVAILABLE_FIELDS]
        for u in unknown:
            out.warn(f"Unknown field '{u}' — available fields: {', '.join(_AVAILABLE_FIELDS)}")
        known = [f for f in fields if f in _AVAILABLE_FIELDS]
        return [{f: item[f] for f in known if f in item} for item in items]
    if item_depth < _ITEM_DEPTH_FULL:
        # Exclude body by default — callers must opt-in via fields=['body'].
        # At depth=3, _apply_item_depth already adds body intentionally.
        return [{k: v for k, v in item.items() if k != "body"} for item in items]
    # Widen to the declared return type — items may be the narrower str|bool variant.
    return [dict(item) for item in items]


def _item_field_text(item: dict[str, str | bool], field: str) -> str:
    """Return the casefolded text for a single field of an item dict."""
    return str(item.get(field, "") or "").casefold()


def _build_haystack(item: dict[str, str | bool]) -> str:
    """Return a single casefolded string combining all default search fields.

    Building the haystack is O(fields) per item.  Pre-computing it once before
    evaluating multiple terms avoids rebuilding it for every (item, term) pair.
    """
    return " ".join(_item_field_text(item, f) for f in _SEARCH_FIELDS)


def _item_matches_term(item: dict[str, str | bool], term: str, haystack: str | None = None) -> bool:
    """Return True if a single search term matches the item.

    Supported term forms (evaluated in order):
    - ``/pattern/`` or ``regex:pattern`` — compiled regex matched against all
      default search fields joined with a space (title, section, topic, type,
      and full body content).
    - ``field:value`` — substring match restricted to a named field
      (``title``, ``section``, ``topic``, ``type``, ``body``).  Unknown field
      names fall back to full-text substring match.
    - plain text — case-insensitive substring match across all default fields
      (existing behaviour, fully preserved).

    Args:
        item: Backlog item dict.
        term: A single search term (no AND/OR operators).
        haystack: Pre-computed full-text string from ``_build_haystack``.
            When provided, avoids rebuilding the haystack inside this call.
            Pass ``None`` (default) to let this function build it on demand.
    """
    term = term.strip()
    if not term:
        return True

    # Regex form: /pattern/ or regex:pattern
    if (term.startswith("/") and term.endswith("/") and len(term) > _REGEX_SLASH_MIN_LEN) or term.startswith("regex:"):
        pattern_str = term[1:-1] if term.startswith("/") else term[len("regex:") :]
        try:
            pattern = _re.compile(pattern_str, _re.IGNORECASE)
        except _re.error:
            # Invalid regex — fall through to plain substring match on the raw term.
            pass
        else:
            hs = haystack if haystack is not None else _build_haystack(item)
            return bool(pattern.search(hs))

    # Field-specific form: field:value
    if ":" in term:
        field, _, value = term.partition(":")
        field = field.strip().lower()
        value = value.strip().casefold()
        if field in _SEARCH_FIELDS:
            return value in _item_field_text(item, field)
        # Unknown field prefix — treat as plain text (fall through).

    # Plain text — existing case-insensitive substring match across all fields.
    needle = term.casefold()
    hs = haystack if haystack is not None else _build_haystack(item)
    return needle in hs


# ---------------------------------------------------------------------------
# Search expression AST — predicates defined first so the parser can annotate
# return types without forward references.
# ---------------------------------------------------------------------------


class _Predicate:
    """Base class for search predicates.

    Subclasses implement ``__call__(item, haystack) -> bool``.
    """

    def __call__(self, item: dict[str, str | bool], haystack: str) -> bool:
        """Evaluate the predicate against a single backlog item.

        Args:
            item: Backlog item dict.
            haystack: Pre-computed full-text string from ``_build_haystack``.

        Returns:
            True if the item matches the predicate.
        """
        raise NotImplementedError


@dataclasses.dataclass
class _TermPred(_Predicate):
    """Match a single leaf term against an item."""

    term: str

    def __call__(self, item: dict[str, str | bool], haystack: str) -> bool:
        return _item_matches_term(item, self.term, haystack)


@dataclasses.dataclass
class _AndPred(_Predicate):
    """Conjunction: both sub-predicates must match."""

    left: _Predicate
    right: _Predicate

    def __call__(self, item: dict[str, str | bool], haystack: str) -> bool:
        return self.left(item, haystack) and self.right(item, haystack)


@dataclasses.dataclass
class _OrPred(_Predicate):
    """Disjunction: at least one sub-predicate must match."""

    left: _Predicate
    right: _Predicate

    def __call__(self, item: dict[str, str | bool], haystack: str) -> bool:
        return self.left(item, haystack) or self.right(item, haystack)


@dataclasses.dataclass
class _NotPred(_Predicate):
    """Negation: the sub-predicate must not match."""

    operand: _Predicate

    def __call__(self, item: dict[str, str | bool], haystack: str) -> bool:
        return not self.operand(item, haystack)


class _TruePred(_Predicate):
    """Always-true predicate used as a safe no-op fallback."""

    def __call__(self, item: dict[str, str | bool], haystack: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# Tokenizer and recursive-descent parser
# ---------------------------------------------------------------------------


def _tokenize_search(search: str) -> list[str]:
    """Tokenize a search query into a flat list of tokens.

    Tokens are one of: ``(``, ``)``, ``AND``, ``OR``, ``NOT``, or a bare term
    string.  Keywords are matched case-insensitively and emitted in uppercase.
    Whitespace between tokens is consumed.  Terms that contain colons (field
    prefixes), slashes (regex), or other non-keyword text are preserved as-is.

    Args:
        search: Raw search query string.

    Returns:
        List of string tokens.
    """
    tokens: list[str] = []
    i = 0
    n = len(search)
    while i < n:
        if search[i].isspace():
            i += 1
            continue
        if search[i] in "()":
            tokens.append(search[i])
            i += 1
            continue
        j = i
        while j < n and not search[j].isspace() and search[j] not in "()":
            j += 1
        word = search[i:j]
        upper = word.upper()
        tokens.append(upper if upper in {"AND", "OR", "NOT"} else word)
        i = j
    return tokens


class _SearchParser:
    """Recursive descent parser for search queries.

    Grammar (precedence: NOT > AND > OR)::

        expr     := or_expr
        or_expr  := and_expr ( OR and_expr )*
        and_expr := not_expr ( AND not_expr )*
        not_expr := NOT not_expr | atom
        atom     := LPAREN expr RPAREN | TERM

    The parse result is a ``_Predicate`` callable ``(item, haystack) -> bool``.
    """

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> str | None:
        """Return the next token without consuming it, or None at end-of-input."""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self) -> str:
        """Consume and return the next token.

        Returns:
            The token at the current position.
        """
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> _Predicate:
        """Parse all tokens and return a root predicate.

        Remaining unparsed tokens after the top-level ``or_expr`` are joined
        with implicit AND so that malformed partial queries still match
        sensibly rather than silently ignoring trailing terms.

        Returns:
            Callable predicate representing the full expression.
        """
        pred = self._parse_or()
        while self._peek() is not None and self._peek() not in {")", "OR"}:
            if self._peek() == "AND":
                self._consume()
            right = self._parse_not()
            pred = _AndPred(pred, right)
        return pred

    def _parse_or(self) -> _Predicate:
        left = self._parse_and()
        while self._peek() == "OR":
            self._consume()
            right = self._parse_and()
            left = _OrPred(left, right)
        return left

    def _parse_and(self) -> _Predicate:
        left = self._parse_not()
        while self._peek() == "AND":
            self._consume()
            right = self._parse_not()
            left = _AndPred(left, right)
        return left

    def _parse_not(self) -> _Predicate:
        if self._peek() == "NOT":
            self._consume()
            operand = self._parse_not()
            return _NotPred(operand)
        return self._parse_atom()

    def _parse_atom(self) -> _Predicate:
        tok = self._peek()
        if tok == "(":
            self._consume()
            pred = self._parse_or()
            if self._peek() == ")":
                self._consume()
            return pred
        if tok is not None and tok not in {"AND", "OR", "NOT", ")"}:
            self._consume()
            return _TermPred(tok)
        # Empty or unexpected token — safe no-op fallback.
        return _TruePred()


def _apply_search_filter(items: list[dict[str, str | bool]], search: str) -> list[dict[str, str | bool]]:
    """Filter items using the full-text search query syntax.

    Query syntax (operator precedence: NOT > AND > OR):

    - ``term1 OR term2``  — item matches if either term matches.
    - ``term1 AND term2`` — item matches only if both terms match.
    - ``NOT term`` — item matches only if the term does *not* match.
    - ``(term1 OR term2) AND term3`` — parenthetical grouping controls precedence.
    - Bare text without operators — original substring behaviour (single term).

    Operators are whitespace-delimited and case-insensitive.

    Each individual term supports:

    - ``/regex/`` or ``regex:pattern`` — regex match
    - ``field:value`` — field-specific substring match
    - plain text — substring match across all default fields

    Args:
        items: Backlog item dicts to filter.
        search: Query string.

    Returns:
        Filtered list of items that match the search query.
    """
    search = search.strip()
    if not search:
        return items

    tokens = _tokenize_search(search)
    parser = _SearchParser(tokens)
    predicate = parser.parse()

    result = []
    for item in items:
        hs = _build_haystack(item)
        if predicate(item, hs):
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Primitive 1: match_context helpers
# ---------------------------------------------------------------------------

# Snippet window: characters before and after the match position.
# Used as the default when snippet_context is not supplied to _make_snippet.
_SNIPPET_WINDOW = 60

# Default snippet_context value (pre + post budget combined).
_DEFAULT_SNIPPET_CONTEXT = 2 * _SNIPPET_WINDOW


def _parse_body_sections(body: str) -> list[tuple[str, str]]:
    """Parse a markdown body string into (section_slug, text) tuples.

    Splits on ``## Heading`` lines. Text before the first heading is attributed
    to ``"body:preamble"``.

    Args:
        body: Raw markdown body string.

    Returns:
        List of (section_slug, text) pairs in document order.
    """
    sections: list[tuple[str, str]] = []
    current_slug = "body:preamble"
    current_parts: list[str] = []
    for line in body.splitlines(keepends=True):
        if line.startswith("## "):
            if current_parts:
                sections.append((current_slug, "".join(current_parts)))
            heading = line[3:].strip()
            current_slug = "body:" + heading.lower().replace(" ", "-")
            current_parts = []
        else:
            current_parts.append(line)
    if current_parts:
        sections.append((current_slug, "".join(current_parts)))
    return sections


def _make_snippet(text: str, start: int, end: int, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT) -> str:
    """Extract a snippet around a match position with sliding-window budget.

    The total character budget is *snippet_context*, split equally between the
    text before and after the match.  Unused budget on either side is
    redistributed to the other side so the window is as wide as possible.

    Args:
        text: The full text in which the match was found.
        start: Match start index.
        end: Match end (exclusive) index.
        snippet_context: Total characters to show before and after the match
            (combined).  Defaults to ``2 * _SNIPPET_WINDOW`` (120) to preserve
            prior behaviour when callers do not supply the argument.

    Returns:
        Up to *snippet_context* + (end-start) characters centred on the match,
        with leading/trailing ``...`` markers when content was truncated.
    """
    raw, matched, _snip_start, _snip_end = _make_snippet_parts(text, start, end, snippet_context)
    del matched
    return raw


def _make_snippet_parts(
    text: str, start: int, end: int, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT
) -> tuple[str, str, int, int]:
    """Compute snippet parts for a match, enabling both plain and formatted output.

    Implements the sliding-window budget: pre and post budgets each receive half
    of *snippet_context*; any unused budget on one side is redistributed to the
    other so the window stays as wide as possible.

    Args:
        text: The full text in which the match was found.
        start: Match start index (inclusive).
        end: Match end index (exclusive).
        snippet_context: Total character budget split across pre and post sides.

    Returns:
        Tuple of (raw_snippet, matched_text, snip_start, snip_end) where
        raw_snippet is the text[snip_start:snip_end] with leading/trailing
        ``...`` markers, matched_text is text[start:end], and snip_start/
        snip_end are the absolute window boundaries in *text*.
    """
    pre_budget = snippet_context // 2
    post_budget = snippet_context // 2

    # Sliding window: redistribute surplus from whichever side is near a boundary.
    actual_pre = min(pre_budget, start)
    surplus_pre = pre_budget - actual_pre
    adjusted_post = post_budget + surplus_pre

    actual_post = min(adjusted_post, len(text) - end)
    surplus_post = post_budget - min(post_budget, len(text) - end)  # surplus from original split
    if surplus_post > 0:
        pre_budget += surplus_post
        actual_pre = min(pre_budget, start)

    snip_start = start - actual_pre
    snip_end = end + actual_post
    snippet = text[snip_start:snip_end]
    if snip_start > 0:
        snippet = "..." + snippet
    if snip_end < len(text):
        snippet += "..."
    return snippet, text[start:end], snip_start, snip_end


def _format_match_text(
    field: str, match_index: int, text: str, start: int, end: int, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT
) -> str:
    """Format a single match entry as a human-readable snippet line.

    The section label ``[segment: field]`` is always shown and is NOT counted
    against the character budget.  The sliding window applies only to the
    haystack text excluding the label.

    Format::

        N::[segment: field]:: ...pre-text...MATCHED TERM...post-text...

    where ``...`` prefix/suffix are present only when content was truncated.

    Args:
        field: Field or section slug (e.g. ``"title"``, ``"body:acceptance-criteria"``).
        match_index: 1-based index of this match within the item.
        text: The full haystack text (section content, not including the label).
        start: Match start index within *text*.
        end: Match end index (exclusive) within *text*.
        snippet_context: Total character budget for pre + post context.

    Returns:
        Formatted match line string.
    """
    raw_snippet, matched, ss, se = _make_snippet_parts(text, start, end, snippet_context)
    del matched, ss, se
    return f"{match_index}::[segment: {field}]:: {raw_snippet}"


_META_FIELDS: tuple[str, ...] = ("title", "section", "topic", "type")


def _match_body_sections(
    item: dict[str, str | bool],
    term: str,
    needle_fn: Callable[[str], tuple[int, int] | None],
    snippet_context: int = _DEFAULT_SNIPPET_CONTEXT,
) -> list[dict[str, str]]:
    """Return match entries for all body sections where needle_fn returns a span.

    Args:
        item: Backlog item dict.
        term: The original search term (stored in each match entry).
        needle_fn: Callable that takes a text string and returns a (start, end)
            span tuple on match, or ``None`` when there is no match.
        snippet_context: Total character budget passed to ``_make_snippet``.

    Returns:
        List of match-context dicts for body sections that matched.
    """
    body_str = str(item.get("body", "") or "")
    matches: list[dict[str, str]] = []
    for section_slug, section_text in _parse_body_sections(body_str):
        span = needle_fn(section_text)
        if span is not None:
            matches.append({
                "field": section_slug,
                "term": term,
                "snippet": _make_snippet(section_text, *span, snippet_context=snippet_context),
            })
    return matches


def _collect_regex_matches(
    item: dict[str, str | bool], term: str, pattern_str: str, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT
) -> list[dict[str, str]] | None:
    """Collect matches for a regex term.

    Args:
        item: Backlog item dict.
        term: The original search term.
        pattern_str: Raw regex pattern extracted from the term.
        snippet_context: Total character budget passed to ``_make_snippet``.

    Returns:
        List of match-context dicts, or ``None`` if the regex is invalid
        (caller should fall through to plain-text matching).
    """
    try:
        pattern = _re.compile(pattern_str, _re.IGNORECASE)
    except _re.error:
        return None
    matches: list[dict[str, str]] = []
    for field in _META_FIELDS:
        field_text = str(item.get(field, "") or "")
        m = pattern.search(field_text)
        if m:
            matches.append({
                "field": field,
                "term": term,
                "snippet": _make_snippet(field_text, m.start(), m.end(), snippet_context=snippet_context),
            })
    matches.extend(
        _match_body_sections(
            item,
            term,
            lambda t: (m.start(), m.end()) if (m := pattern.search(t)) else None,
            snippet_context=snippet_context,
        )
    )
    return matches


def _collect_field_matches(
    item: dict[str, str | bool],
    term: str,
    field_name: str,
    value_needle: str,
    snippet_context: int = _DEFAULT_SNIPPET_CONTEXT,
) -> list[dict[str, str]]:
    """Collect matches for a field:value term.

    Args:
        item: Backlog item dict.
        term: The original search term.
        field_name: The field to search (e.g. ``"title"``, ``"body"``).
        value_needle: Casefolded substring to find.
        snippet_context: Total character budget passed to ``_make_snippet``.

    Returns:
        List of match-context dicts.
    """
    if field_name == "body":
        return _match_body_sections(
            item,
            term,
            lambda t: (pos, pos + len(value_needle)) if (pos := t.casefold().find(value_needle)) != -1 else None,
            snippet_context=snippet_context,
        )
    field_text = str(item.get(field_name, "") or "")
    pos = field_text.casefold().find(value_needle)
    if pos != -1:
        return [
            {
                "field": field_name,
                "term": term,
                "snippet": _make_snippet(field_text, pos, pos + len(value_needle), snippet_context=snippet_context),
            }
        ]
    return []


def _collect_plain_matches(
    item: dict[str, str | bool], term: str, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT
) -> list[dict[str, str]]:
    """Collect matches for a plain-text term across all fields.

    Args:
        item: Backlog item dict.
        term: The original search term (used as the needle after casefolding).
        snippet_context: Total character budget passed to ``_make_snippet``.

    Returns:
        List of match-context dicts.
    """
    needle = term.casefold()
    matches: list[dict[str, str]] = []
    for field in _META_FIELDS:
        field_text = str(item.get(field, "") or "")
        pos = field_text.casefold().find(needle)
        if pos != -1:
            matches.append({
                "field": field,
                "term": term,
                "snippet": _make_snippet(field_text, pos, pos + len(needle), snippet_context=snippet_context),
            })
    matches.extend(
        _match_body_sections(
            item,
            term,
            lambda t: (pos, pos + len(needle)) if (pos := t.casefold().find(needle)) != -1 else None,
            snippet_context=snippet_context,
        )
    )
    return matches


def _collect_match_context(
    item: dict[str, str | bool], term: str, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT
) -> list[dict[str, str]]:
    """Return match context entries for *term* against *item*.

    Each returned dict has ``field``, ``term``, and ``snippet`` keys.
    Body matches are attributed to the named markdown section (e.g.
    ``"body:acceptance-criteria"``), not the bare string ``"body"``.

    Args:
        item: Backlog item dict.
        term: A single search term (no AND/OR/NOT operators).
        snippet_context: Total character budget passed to the snippet helpers.

    Returns:
        List of match-context dicts (empty when the term does not match).
    """
    term = term.strip()
    if not term:
        return []

    # Regex form: /pattern/ or regex:pattern
    if (term.startswith("/") and term.endswith("/") and len(term) > _REGEX_SLASH_MIN_LEN) or term.startswith("regex:"):
        pattern_str = term[1:-1] if term.startswith("/") else term[len("regex:") :]
        result = _collect_regex_matches(item, term, pattern_str, snippet_context=snippet_context)
        if result is not None:
            return result
        # Invalid regex — fall through to plain text.

    # Field-specific form: field:value
    if ":" in term:
        field, _, value = term.partition(":")
        field_name = field.strip().lower()
        value_needle = value.strip().casefold()
        if field_name in _SEARCH_FIELDS:
            return _collect_field_matches(item, term, field_name, value_needle, snippet_context=snippet_context)
        # Unknown field prefix — fall through to plain text.

    return _collect_plain_matches(item, term, snippet_context=snippet_context)


def _extract_leaf_terms(search: str) -> list[str]:
    """Extract all leaf (non-operator) terms from a search query string.

    Args:
        search: Raw search query string.

    Returns:
        List of term strings in left-to-right order.
    """
    OPERATORS = frozenset({"AND", "OR", "NOT"})
    tokens = _tokenize_search(search)
    return [t for t in tokens if t not in OPERATORS and t not in {"(", ")"}]


def _enrich_with_match_context(
    items: list[dict[str, str | bool]], search: str | None, snippet_context: int = _DEFAULT_SNIPPET_CONTEXT
) -> list[dict[str, object]]:
    """Add ``matches`` and ``match_header`` keys to each item based on the search query terms.

    Only items that already passed the search filter are enriched.

    Each match entry contains ``field``, ``term``, ``snippet``, and ``text`` keys.
    The ``text`` key holds a formatted line::

        N::[segment: field]:: ...pre-text...MATCHED TERM...post-text...

    where N is the 1-based match index within the item.

    The ``match_header`` key on each item holds ``#number - title`` for
    grouped display: the header appears once, then each ``text`` line follows.

    Args:
        items: Items filtered by ``_apply_search_filter``.
        search: The original search query string, or ``None``.
        snippet_context: Total character budget for pre + post context per match.

    Returns:
        New list of dicts (widened to ``dict[str, object]``) with ``matches``
        and ``match_header`` added to each item.
    """
    enriched: list[dict[str, object]] = []
    terms = _extract_leaf_terms(search) if search else []
    for item in items:
        wide: dict[str, object] = dict(item)
        raw_matches: list[dict[str, str]] = []
        for term in terms:
            raw_matches.extend(_collect_match_context(item, term, snippet_context=snippet_context))

        number = str(item.get("issue", item.get("number", ""))).lstrip("#")
        title = str(item.get("title", ""))
        wide["match_header"] = f"#{number} - {title}" if number else title

        # Annotate each match with a 1-based index and formatted text line.
        annotated: list[dict[str, str]] = []
        for idx, match in enumerate(raw_matches, start=1):
            entry = dict(match)
            entry["text"] = f"     {idx}::[segment: {match['field']}]:: {match['snippet']}"
            annotated.append(entry)

        wide["matches"] = annotated
        enriched.append(wide)
    return enriched


# ---------------------------------------------------------------------------
# Deduplication helper
# ---------------------------------------------------------------------------

# NOTE: FastMCP v3 provides list_page_size for paginating MCP component lists
# (tools/resources/prompts) and per-request Depends() caching. Neither applies
# here — tool result content pagination and token counting are application-level
# concerns with no FastMCP built-in equivalent.


def _dedup_by_issue_number(items: list[dict[str, str | bool]]) -> list[dict[str, str | bool]]:
    """Deduplicate items by issue number, preserving first-seen order.

    When an item appears more than once in the list (e.g. because the upstream
    cache contained a duplicate entry), only the first occurrence is kept.
    Items without a numeric ``issue`` or ``number`` field are preserved as-is
    and cannot be de-duplicated — they each appear once.

    Args:
        items: Raw item dicts from operations.list_items.

    Returns:
        Deduplicated list with the same dict objects (no copy).
    """
    seen: set[str] = set()
    result: list[dict[str, str | bool]] = []
    for item in items:
        raw = str(item.get("issue", item.get("number", "")))
        key = raw.lstrip("#").strip()
        if key and key.isdigit():
            if key in seen:
                continue
            seen.add(key)
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Token-based match pagination helper
# ---------------------------------------------------------------------------


def _compute_match_tokens(item: dict[str, object]) -> int:
    """Count tokens for the match_context output of a single enriched item.

    Counts tokens across the match_header and all match text lines for the item,
    using the shared cl100k_base encoder.  This represents the token cost of
    displaying this item's match output.

    Args:
        item: An enriched item dict (output of _enrich_with_match_context).

    Returns:
        Token count for this item's match output.
    """
    # Serialize the match output (header + all match text lines) and count tokens.
    # We use json.dumps on the relevant keys rather than subscript access to stay
    # type-safe: item is dict[str, object] so individual values are object.
    return _token_count(_json.dumps({"h": item.get("match_header"), "m": item.get("matches")}))


def _paginate_match_items(
    enriched: list[dict[str, object]], page: int, tokens_per_page: int, page_token_limit: int
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Split enriched match-context items into token-sized pages.

    Partitions ``enriched`` into pages where each page holds items up to
    ``tokens_per_page`` tokens.  Only activates pagination when total tokens
    across all items exceeds ``page_token_limit``.

    Args:
        enriched: All enriched items (already filtered and deduped).
        page: 1-based page number requested by the caller.
        tokens_per_page: Maximum tokens per page.
        page_token_limit: Minimum total tokens before pagination activates.

    Returns:
        Tuple of (page_items, match_pages_meta) where match_pages_meta is a
        dict suitable for inclusion in the tool response.
    """
    token_counts = [_compute_match_tokens(item) for item in enriched]
    total_tokens = sum(token_counts)

    if total_tokens <= page_token_limit:
        return enriched, {
            "current_page": 1,
            "total_pages": 1,
            "tokens_per_page": tokens_per_page,
            "total_match_tokens": total_tokens,
            "paginated": False,
        }

    # Build page boundaries by accumulating token counts.
    pages: list[list[dict[str, object]]] = []
    current_page_items: list[dict[str, object]] = []
    current_page_tokens = 0
    for item, cost in zip(enriched, token_counts, strict=True):
        if current_page_items and current_page_tokens + cost > tokens_per_page:
            pages.append(current_page_items)
            current_page_items = [item]
            current_page_tokens = cost
        else:
            current_page_items.append(item)
            current_page_tokens += cost
    if current_page_items:
        pages.append(current_page_items)

    total_pages = max(1, len(pages))
    safe_page = max(1, min(page, total_pages))
    page_items = pages[safe_page - 1]

    return page_items, {
        "current_page": safe_page,
        "total_pages": total_pages,
        "tokens_per_page": tokens_per_page,
        "total_match_tokens": total_tokens,
        "paginated": True,
    }


def _maybe_add_pagination_notice(match_pages: dict[str, object], out: Output, response: dict[str, object]) -> None:
    """Add a human-readable truncation message to ``out`` when on page 1 of a paginated result.

    Mutates ``out`` by appending a message, then re-merges ``out.to_dict()`` into
    ``response`` so the response messages list reflects the addition.

    Args:
        match_pages: The match_pages metadata dict from _paginate_match_items.
        out: The Output collector for this request.
        response: The in-progress response dict to update in-place.
    """
    if not (match_pages.get("paginated") and match_pages.get("current_page") == 1):
        return
    total_pages = match_pages["total_pages"]
    tpp = match_pages["tokens_per_page"]
    out.info(
        f"Match output truncated: showing page 1 of {total_pages} ({tpp} tokens/page). "
        f"Use page=2..{total_pages} to see remaining results."
    )
    response.update(out.to_dict())


# ---------------------------------------------------------------------------
# Primitive 2: item_depth helpers
# ---------------------------------------------------------------------------


def _parse_body_section_names(body: str) -> list[str]:
    """Return the list of section names present in a markdown body string.

    Args:
        body: Raw markdown body string.

    Returns:
        List of section heading strings in document order.
    """
    return [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]


def _parse_body_section_first_lines(body: str) -> dict[str, str]:
    """Return a mapping of section name to the first non-empty content line.

    Args:
        body: Raw markdown body string.

    Returns:
        Dict mapping section heading to first non-empty content line.
    """
    result: dict[str, str] = {}
    current_heading: str | None = None
    found_first: bool = False
    for line in body.splitlines():
        if line.startswith("## "):
            current_heading = line[3:].strip()
            found_first = False
            result[current_heading] = ""
        elif current_heading is not None and not found_first and line.strip():
            result[current_heading] = line.strip()
            found_first = True
    return result


# Minimum depth level that adds full description and section previews.
_ITEM_DEPTH_FULL: int = 2

# Depth level that retains the raw body field (full item content).
_ITEM_DEPTH_BODY: int = 3

# Maximum description snippet length for item_depth=1.
_DESCRIPTION_SNIPPET_LEN: int = 300


def _apply_item_depth(item: dict[str, object], depth: int) -> dict[str, object]:
    """Augment a list-entry item dict according to the requested depth level.

    - ``0`` -- no changes (returns item cast to dict[str, object]).
    - ``1`` -- adds ``description_snippet`` (<=300 chars) and ``section_names``.
    - ``2`` -- adds ``full_description`` and ``section_first_lines``.
    - ``3`` -- body already in the dict; no additional mutation.

    Args:
        item: A single backlog list entry dict.
        depth: Requested depth level (0-3).

    Returns:
        New dict widened to ``dict[str, object]`` with depth-specific keys added.
    """
    wide: dict[str, object] = dict(item)
    if depth <= 0:
        return wide
    body = str(item.get("body", "") or "")
    description = str(item.get("description", "") or "")
    if depth >= 1:
        wide["description_snippet"] = description[:_DESCRIPTION_SNIPPET_LEN]
        wide["section_names"] = _parse_body_section_names(body)
    if depth >= _ITEM_DEPTH_FULL:
        wide["full_description"] = description
        wide["section_first_lines"] = _parse_body_section_first_lines(body)
    # depth 1 and 2: remove body (replaced by structured depth fields above).
    # depth 3: body is the full content — retain it for callers that need it.
    if depth < _ITEM_DEPTH_BODY:
        wide.pop("body", None)
    return wide


# ---------------------------------------------------------------------------
# Primitive 3: backlog_view section filter
# ---------------------------------------------------------------------------

_VIEW_ALWAYS_INCLUDE: frozenset[str] = frozenset({"number", "title", "status", "type", "priority"})


def _filter_view_sections(response: dict[str, object], sections: list[str]) -> dict[str, object]:
    """Filter the backlog_view response to only the requested sections.

    Identity fields (number, title, status, type, priority) are always included.
    The ``sections`` dict in the response is filtered to the named keys only.
    All other top-level keys are preserved.

    Args:
        response: Full serialised ViewItemResult dict.
        sections: List of section name strings to include.

    Returns:
        Filtered response dict (same object, mutated in place).
    """
    requested: frozenset[str] = frozenset(sections)
    raw_sections = response.get("sections")
    if isinstance(raw_sections, dict):
        response["sections"] = {k: v for k, v in raw_sections.items() if k in requested}
    return response


def _parse_args() -> argparse.Namespace:
    """Parse server startup arguments.

    Returns:
        Parsed namespace; ``project_dir`` is ``None`` when not supplied.
    """
    parser = argparse.ArgumentParser(description="Backlog MCP server")
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help=(
            "Absolute path to the user's project root. "
            "Required when installed as a plugin so BACKLOG_DIR resolves "
            "to the user's project rather than the plugin cache directory."
        ),
    )
    # parse_known_args prevents FastMCP/uvicorn arguments from causing errors
    namespace, _ = parser.parse_known_args(sys.argv[1:])
    return namespace


_args = _parse_args()
# Only eagerly initialise when the caller supplied an explicit project directory.
# Without --project-dir the server may start from a non-git cwd (e.g. installed
# as a plugin); in that case get_config() lazily auto-initialises on first use
# via environment variables or git discovery, which is less likely to crash at
# import time.
if _args.project_dir is not None:
    _init_models(_args.project_dir)


def _read_gate_token(gate_token: str) -> str | None:
    """Read the session gate token file and return its contents for comparison.

    The token is generated and written by
    ``skills/work-backlog-item/scripts/get-gate-token.mjs`` when the skill loads.
    The token format is ``{session_id}:{hex_token}`` — the session ID is extracted
    from the caller-provided value so the MCP server never needs its own
    CLAUDE_CODE_SESSION_ID to locate the file.

    Args:
        gate_token: The value passed by the caller. Must contain a ``:`` separating
            the session ID from the random hex portion.

    Returns:
        The file contents (the full ``{session_id}:{hex_token}`` string), or None
        when the format is invalid or the file cannot be read.
    """
    colon = gate_token.find(":")
    if colon < 1:
        return None
    session_id = gate_token[:colon]
    dh_state_home = _os.environ.get("DH_STATE_HOME", "")
    dh_root = Path(dh_state_home).expanduser() if dh_state_home else Path.home() / ".dh"
    token_path = dh_root / "sessions" / session_id / ".gate-token"
    try:
        return token_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


mcp = FastMCP(
    "backlog",
    instructions=(
        "Backlog management server. Manages per-item markdown files in ~/.dh/projects/{slug}/backlog/, "
        "syncs with GitHub Issues (source of truth), and provides CRUD operations for "
        "backlog items including add, list, view, update, groom, close, resolve, and sync."
    ),
    version="0.1.0",
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Add Backlog Item", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
async def backlog_add(
    ctx: Context,
    title: Annotated[str, Field(description="Item title")],
    priority: Annotated[str, Field(description="Priority level: P0, P1, P2, or Ideas")],
    description: Annotated[str, Field(description="Item description")],
    source: Annotated[str, Field(description="Where this item came from")] = "Not specified",
    type_: Annotated[
        str, Field(description="Item type: Feature, Bug, Refactor, Docs, or Chore", alias="type")
    ] = "Feature",
    force: Annotated[bool, Field(description="Skip fuzzy duplicate check")] = False,
    gate_token: Annotated[
        str | None,
        Field(
            description="Required gate token. Load /dh:work-backlog-item (or /dh:create-backlog-item) — the skill injects the token at load time via the <gate_token> tag."
        ),
    ] = None,
) -> dict:
    """Add a new item to the backlog. Creates a per-item file and a GitHub issue.

    Use priority P0 for must-have, P1 for should-have, P2 for could-have,
    or Ideas for exploratory items.

    Returns:
        Dict with file_path, title, priority, issue number (if created),
        and output messages/warnings. On error, dict contains an error key.
    """
    if not gate_token:
        return {
            "error": "Gate token required. Load /dh:work-backlog-item create — the skill provides the gate_token at load time."
        }
    expected_token = _read_gate_token(gate_token)
    if expected_token is None:
        await ctx.warning("Gate token file unreadable — format invalid or session file missing")
        return {
            "error": 'Direct backlog_add calls are not permitted. Load and follow /dh:work-backlog-item create -- "<description>" — it will provide the required gate_token.'
        }
    if gate_token != expected_token:
        return {
            "error": 'Direct backlog_add calls are not permitted. Load and follow /dh:work-backlog-item create -- "<description>" — it will provide the required gate_token.'
        }
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.add_item,
            title=title,
            priority=priority,
            description=description,
            source=source,
            type_=type_,
            force=force,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


def _assert_config() -> None:
    """Raise :exc:`BacklogError` when BacklogConfig has not been initialised.

    Converts the :exc:`RuntimeError` from :func:`models.get_config` into a
    :exc:`BacklogError` so tool handlers that already catch ``BacklogError``
    return structured JSON instead of crashing.

    Raises:
        BacklogError: When no project root is discoverable and no env vars are set.
    """
    try:
        _models.get_config()
    except RuntimeError as exc:
        raise BacklogError(str(exc)) from exc


def _probe_backend_status() -> _BackendStatus:
    """Delegate to the configured backend's probe_backend_status().

    Extracted as a module-level function so tests can patch
    ``backlog_core.server._probe_backend_status`` without reaching into the
    backend object directly.

    Returns a default ``NOT_CHECKED`` status when BacklogConfig has not been
    initialised (e.g. the server was started outside a git repository without
    environment variables set).

    Returns:
        BackendStatus populated by the active backend implementation, or a
        default NOT_CHECKED status when config is unavailable.
    """
    try:
        return _get_config().backend.probe_backend_status()
    except (RuntimeError, ValueError):
        return _BackendStatus(availability=_BackendAvailability.NOT_CHECKED)


def _format_backend_status_message(status: _BackendStatus) -> str:
    """Format a single-line human-readable backend status string for the messages list.

    When reachable, the format is:
        ``Backend: GitHub, Backend availability: reachable, Backend items (N open / M total)``

    When unavailable (any non-reachable state), the format is:
        ``Backend: GitHub, Backend availability: <state>, Backend items (--- open / --- total)[cache: N open / M total]``

    Args:
        status: Populated BackendStatus from probe_backend_status().

    Returns:
        Formatted status string.
    """
    availability_label = (
        status.availability.value if isinstance(status.availability, _BackendAvailability) else str(status.availability)
    )
    if (
        status.availability == _BackendAvailability.REACHABLE
        and status.open_count is not None
        and status.total_count is not None
    ):
        return (
            f"Backend: {status.name}, Backend availability: {availability_label}, "
            f"Backend items ({status.open_count} open / {status.total_count} total)"
        )
    cache_open = status.cache_open_count
    cache_total = status.cache_total_count
    return (
        f"Backend: {status.name}, Backend availability: {availability_label}, "
        f"Backend items (--- open / --- total)"
        f"[cache: {cache_open} open / {cache_total} total]"
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Backlog Items", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list(
    from_github: Annotated[bool, Field(description="Refresh local cache from GitHub Issues before listing")] = False,
    label: Annotated[str | None, Field(description="Filter by GitHub label (e.g. 'priority:p1', 'type:bug')")] = None,
    section: Annotated[
        str | None, Field(description="Filter by priority section: P0, P1, P2, or Ideas (case-insensitive)")
    ] = None,
    status: Annotated[
        str | None, Field(description="Filter by status value e.g. 'needs-grooming', 'status:in-progress'")
    ] = None,
    title_filter: Annotated[
        str | None,
        Field(description="Filter items whose title contains this substring (case-insensitive)", alias="title"),
    ] = None,
    type_: Annotated[
        str | None,
        Field(
            description=(
                "Filter by metadata.type — case-insensitive exact match (e.g. 'Bug', 'Feature'). "
                "Items without metadata.type are excluded when this filter is active."
            ),
            alias="type",
        ),
    ] = None,
    topic: Annotated[
        str | None,
        Field(
            description=(
                "Filter by metadata.topic — case-insensitive substring match. "
                "Items without metadata.topic are excluded when this filter is active."
            )
        ),
    ] = None,
    include_closed: Annotated[
        bool, Field(description="Include items with closed/done/resolved status (excluded by default)")
    ] = False,
    search: Annotated[
        str | None,
        Field(
            description=(
                "Full-text search across the complete item content — title, section, topic, "
                "type, description, acceptance criteria, and all section body text. "
                "Supports OR/AND/NOT operators (e.g. 'auth OR deploy', 'backlog NOT quality'), "
                "parenthetical grouping ('(auth OR deploy) AND quality'), "
                "regex patterns (/pattern/ or regex:pattern), "
                "field-specific search (title:auth, type:bug, topic:devops, section:P1, body:sdlc-layers), "
                "and plain case-insensitive substring matching. "
                "Operator precedence: NOT > AND > OR. "
                "Combine with other filters (section=, type=, topic=) to narrow results further."
            )
        ),
    ] = None,
    offset: Annotated[
        int, Field(ge=0, description="Skip the first N items from the filtered result set (for pagination).")
    ] = 0,
    limit: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Maximum number of items to return. 0 = auto-paginate to stay within 4400 token budget "
                "(cl100k_base encoding). Caller can override with an explicit positive value."
            ),
        ),
    ] = 0,
    count_only: Annotated[
        bool,
        Field(
            description=(
                'When True, return only {"count": N} without fetching item content. '
                "Use to check result-set size before committing to a full fetch."
            )
        ),
    ] = False,
    match_context: Annotated[
        bool,
        Field(
            description=(
                "When True, each returned item includes a 'matches' list showing where search "
                "terms were found (field, term, snippet, text). Body matches are attributed to the named "
                "section (e.g. 'body:acceptance-criteria'). Only meaningful when search is also set. "
                "Default False preserves the existing response shape."
            )
        ),
    ] = False,
    snippet_context: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Total character budget for the pre + post context window around each match. "
                "Split equally: up to snippet_context//2 chars before and after the matched text. "
                "Unused budget on one side is redistributed to the other (sliding window). "
                "Only applies when match_context=True. Default 1024."
            ),
        ),
    ] = 1024,
    item_depth: Annotated[
        int,
        Field(
            ge=0,
            le=3,
            description=(
                "Controls how much content is returned per item. "
                "0 (default): compact format — number, title, status, type, priority only. "
                "1: adds description_snippet (first 300 chars) and section_names list. "
                "2: adds full_description and section_first_lines dict. "
                "3: full item content including complete body. "
                "Use depth=3 only with small limit values (≤5) to avoid large responses."
            ),
        ),
    ] = 0,
    page: Annotated[
        int,
        Field(
            ge=1,
            description=(
                "When match_context=True and total match tokens exceed page_token_limit, "
                "selects which page of results to return (1-based). "
                "Ignored when match_context=False — use offset/limit for non-match pagination."
            ),
        ),
    ] = 1,
    tokens_per_page: Annotated[
        int,
        Field(
            ge=1,
            description=(
                "Maximum tokens of match_context output per page. "
                "Only active when match_context=True and total tokens exceed page_token_limit."
            ),
        ),
    ] = 1000,
    page_token_limit: Annotated[
        int,
        Field(
            ge=1,
            description=(
                "If total match_context output tokens across all matching items exceeds this "
                "value, pagination is activated and only the items for the requested page are "
                "returned. When match_context=False this parameter has no effect."
            ),
        ),
    ] = 4000,
    fields: Annotated[
        list[str] | None,
        Field(
            description=(
                "When provided, each returned item contains only the listed fields. "
                "Available fields: issue, title, section, topic, type, status, body. "
                "body is excluded from the default response but can be requested here. "
                "Unknown field names produce a warning in the warnings list."
            )
        ),
    ] = None,
) -> dict:
    """List all open backlog items.

    Use from_github=true to refresh the local cache from GitHub before listing.
    Use label to filter items by a specific GitHub label.
    Use section to filter by priority section (P0, P1, P2, Ideas).
    Use status to filter by status value (e.g. needs-grooming, status:in-progress).
    Use title to filter by title substring (case-insensitive).
    Use type_ to filter by metadata.type exact match (e.g. Bug, Feature).
    Use topic to filter by metadata.topic substring match.
    Use include_closed=true to include items with terminal status (done, resolved, closed).
    Use search for full-text search across the complete item content (title, section, topic,
    type, description, and all section body text including acceptance criteria and impact radius).
    Search supports OR/AND/NOT operators (e.g. 'auth OR deploy', 'backlog NOT quality'),
    parenthetical grouping ((auth OR deploy) AND quality), regex (/pattern/ or regex:pattern),
    field-specific syntax (title:auth, type:bug, topic:devops, body:sdlc-layers), and plain substring matching.
    Use count_only=true to return only {"count": N} without fetching item content.
    Use offset and limit to paginate results. When limit=0, auto-pagination keeps the
    response under 4400 tokens (cl100k_base encoding). When has_more=true, call again
    with the offset shown in next_call.
    When match_context=True, use page/tokens_per_page/page_token_limit to control
    token-based pagination of match output. When match_pages.paginated=true, use
    page=2..N to retrieve subsequent pages.

    Returns:
        Dict with items list, count, pagination object, and output messages/warnings.
        Each item includes state (open/closed) and status (workflow status from status:* labels).
        pagination contains offset, limit, total, and has_more. When has_more=true,
        next_call provides the suggested follow-up call string.
        When match_context=True, match_pages contains current_page, total_pages,
        tokens_per_page, total_match_tokens, and paginated flag.
        When count_only=True, returns only {"count": N}.
        On error, dict contains an error key.
        Items are deduplicated by issue number — if the cache contained duplicate
        entries, only the first occurrence of each issue number is returned.
    """
    out = Output()
    try:
        _assert_config()
        result, backend_status = await asyncio.gather(
            asyncio.to_thread(
                operations.list_items,
                from_github=from_github,
                label=label,
                section=section,
                status=status,
                title=title_filter,
                type_=type_,
                topic=topic,
                include_closed=include_closed,
                output=out,
            ),
            asyncio.to_thread(_probe_backend_status),
        )
    except BacklogError as e:
        backend_status = await asyncio.to_thread(_probe_backend_status)
        return {"error": str(e), "backend": backend_status.model_dump(), **out.to_dict()}

    # "items" holds list[dict[str, str | bool]] per operations.list_items return type.
    # Filter to dict elements only to narrow the heterogeneous value union.
    raw_items = result.get("items", [])
    all_items: list[dict[str, str | bool]] = (
        [x for x in raw_items if isinstance(x, dict)] if isinstance(raw_items, list) else []
    )

    # Apply cross-field search filter when requested.
    if search is not None:
        all_items = _apply_search_filter(all_items, search)

    # Deduplicate by issue number — the cache may contain duplicate entries for
    # the same issue (observed: #260 appeared twice when multiple match paths
    # selected the same item).  Keyed on numeric issue number; first occurrence wins.
    all_items = _dedup_by_issue_number(all_items)

    total = len(all_items)

    # count_only short-circuit: return only the item count without page content.
    if count_only:
        return {"count": total}

    # ADR-5: cache_open_count reflects the same filter as the items list.
    backend_status.cache_open_count = total

    # Append the human-readable backend status line to the messages list.
    out.info(_format_backend_status_message(backend_status))

    # Determine effective page limit.
    if limit > 0:
        # Caller requested an explicit limit — honour it exactly.
        effective_limit = limit
    else:
        # Auto-paginate: binary-search for the largest slice that fits the budget.
        # Start with all items and halve until the token count fits.
        candidate = all_items[offset:]
        effective_limit = len(candidate)
        while effective_limit > 1:
            token_count = _token_count(_json.dumps(candidate[:effective_limit]))
            if token_count <= _LIST_TOKEN_BUDGET:
                break
            effective_limit = max(1, effective_limit // 2)

    page_items = all_items[offset : offset + effective_limit]
    has_more = (offset + effective_limit) < total

    # Primitive 2 and 1: enrich page items when depth or match context is requested.
    # Order matters: match context must read body BEFORE item_depth removes it.
    # Step 1 — add match snippets (reads body from original page_items)
    # Step 2 — apply token-based pagination (match_context=True only)
    # Step 3 — apply depth (may remove body from the already-enriched items)
    # Use a widened list type to accommodate the richer value types added by enrichment.
    enriched_items: list[dict[str, object]] | list[dict[str, str | bool]]
    match_pages: dict[str, object] | None = None

    enriched_items: list[dict[str, object]] | list[dict[str, str | bool]]
    if match_context:
        enriched_items, match_pages = _paginate_match_items(
            _enrich_with_match_context(page_items, search, snippet_context=snippet_context),
            page=page,
            tokens_per_page=tokens_per_page,
            page_token_limit=page_token_limit,
        )
    else:
        enriched_items = page_items
        match_pages = None

    if item_depth > 0:
        enriched_items = [_apply_item_depth(dict(it), item_depth) for it in enriched_items]

    # Apply fields projection or default body exclusion.
    enriched_items = _apply_fields_projection(enriched_items, fields=fields, item_depth=item_depth, out=out)

    pagination: dict = {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more}
    response: dict = {
        **result,
        "items": enriched_items,
        "count": len(enriched_items),
        "available_fields": list(_AVAILABLE_FIELDS),
        "pagination": pagination,
        "backend": backend_status.model_dump(),
        **out.to_dict(),
    }
    if has_more:
        response["next_call"] = f"backlog_list(offset={offset + effective_limit}, limit={effective_limit})"
    if match_pages is not None:
        response["match_pages"] = match_pages
        _maybe_add_pagination_notice(match_pages, out, response)
    return response


def _build_compact_manifest(
    result: _models.ViewItemResult, full_response: dict[str, object], selector: str
) -> dict[str, object]:
    """Build the compact routing manifest returned by ``backlog_view(summary=True)``.

    Args:
        result: Typed ViewItemResult from view_item.
        full_response: Full serialised response dict (used only for size hint).
        selector: Original selector string for _hint message.

    Returns:
        Compact dict with issue_number, title, labels, status, plan_path,
        and size hint for the full response.
    """
    full_chars = len(_json.dumps(full_response))
    plan_match = _re.search(r"^[Pp]lan:\s*(\S+)", result.body, _re.MULTILINE)
    plan_path: str | None = plan_match.group(1) if plan_match else None
    issue_number: int | None = result.number
    if issue_number is None:
        num_match = _re.search(r"(\d+)", result.issue)
        if num_match:
            issue_number = int(num_match.group(1))
    status: str = "closed" if result.state == "closed" else "open"
    compact: dict[str, object] = {
        "issue_number": issue_number,
        "title": result.title,
        "labels": result.labels,
        "status": status,
        "plan_path": plan_path,
        "_summary": True,
        "_full_chars": full_chars,
        "_hint": (
            f"Load full content: backlog_view(selector='{selector}', summary=False)\n"
            f"Load specific sections: backlog_view(selector='{selector}', summary=False, section='<index, title, or /regex/>')"
        ),
    }
    sections_index = _sections_index_from_result(result)
    if sections_index:
        compact["sections_index"] = sections_index
    return compact


def _sections_index_from_result(result: _models.ViewItemResult) -> str:
    r"""Build a ``## Sections`` index string from a populated ViewItemResult.

    Prefers ``result.sections_index`` when already set (YAML items with
    ``include_content=False``).  Falls back to deriving the index from
    ``result.sections`` (the dict populated by the full-content path for both
    YAML and GitHub items) so that over-budget responses always include a usable
    section directory regardless of item type or ``include_content`` flag.

    Args:
        result: ViewItemResult after view_item has been called.

    Returns:
        ``"## Sections\\n[0] Name (N entries)\\n..."`` string, or ``""`` when no
        section information is available.
    """
    if result.sections_index:
        return result.sections_index
    if not result.sections:
        return ""
    lines: list[str] = ["## Sections"]
    for idx, (name, sec) in enumerate(result.sections.items()):
        # Both SectionEntryMetadata and GroomedSectionMetadata are TypedDicts
        # (plain dicts at runtime) — no isinstance guard needed.
        sec_type = sec.get("type")
        if sec_type == _GROOMED_SECTION_TYPE:
            subs = sec.get("subsections")
            count = len(subs) if isinstance(subs, dict) else 0
            lines.append(f"[{idx}] {name} ({count} subsections)")
        else:
            count = int(sec.get("num_entries", 0))
            lines.append(f"[{idx}] {name} ({count} entries)")
    return "\n".join(lines) + "\n"


def _build_over_budget_view(result: _models.ViewItemResult, full_chars: int, selector: str) -> dict[str, object]:
    """Build a compact section-directory response for an over-budget backlog_view call.

    When the full response would exceed ``_VIEW_TOKEN_BUDGET`` tokens and the caller
    has not requested a specific section, this response is returned instead.  It
    always includes item metadata and the ``description`` field (the short summary),
    a section directory listing each section name with its approximate size, and
    usage instructions for requesting individual sections.

    Args:
        result: Typed ViewItemResult from view_item.
        full_chars: Character length of the serialised full response (size hint).
        selector: Original selector string used to build the usage hint.

    Returns:
        Compact dict with number, title, priority, status, description,
        sections_index, _over_budget, _full_chars, and _usage.
    """
    compact: dict[str, object] = {
        "number": result.number,
        "title": result.title,
        "priority": result.priority,
        "status": result.status,
        "description": result.description,
        "_over_budget": True,
        "_full_chars": full_chars,
        "_usage": (
            f"This response exceeded the {_VIEW_TOKEN_BUDGET}-token budget "
            f"({full_chars} chars in full form). "
            "Use the sections_index below to identify which sections you need, "
            "then request them individually:\n"
            f"  backlog_view(selector='{selector}', summary=False, sections=['Section Name'])\n"
            f"  backlog_view(selector='{selector}', summary=False, section='0,1,3')\n"
            f"  backlog_view(selector='{selector}', summary=False, section='/regex/')"
        ),
    }
    sections_index = _sections_index_from_result(result)
    if sections_index:
        compact["sections_index"] = sections_index
    return compact


@mcp.tool(
    annotations=ToolAnnotations(
        title="View Backlog Item", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_view(
    selector: Annotated[str, Field(description="Item selector: GitHub issue URL, #N, bare number, or title substring")],
    summary: Annotated[
        bool,
        Field(
            description=(
                "When True (default), returns a compact routing manifest with issue_number, title, labels, "
                "status, plan_path, sections_index (all available sections as [N] Title (count) lines), "
                "_full_chars, and _hint showing how to load full content or specific sections. "
                "When False, returns the full response unchanged."
            )
        ),
    ] = True,
    include_content: Annotated[
        bool,
        Field(
            description="When True (default), returns full body and section entries. When False, returns metadata and section inventory only (section names with entry counts, no body or entry content)."
        ),
    ] = True,
    offset: Annotated[int, Field(ge=0, description="Skip N entry blocks from body start (for pagination)")] = 0,
    limit: Annotated[int, Field(ge=0, description="Show at most N entry blocks (0 = all, no truncation)")] = 0,
    show: Annotated[
        str | None,
        Field(description="Entry filter: 'all', 'last', 'first', 'struck', or integer N (first N active entries)"),
    ] = None,
    since: Annotated[
        str | None, Field(description="ISO date/datetime. Only entries at or after this timestamp are included.")
    ] = None,
    section: Annotated[
        str | None,
        Field(
            description=(
                "Section filter for YAML items (no effect on GitHub-only items with a raw body). "
                "Accepts: numeric index '2', comma-separated indices '0,2,4', "
                "regex '/impact.*/', or substring match 'RT-ICA'. "
                "When provided, body and sections in the response reflect only the matched section(s)."
            )
        ),
    ] = None,
    sections: Annotated[
        list[str] | None,
        Field(
            description=(
                "When provided, filter the returned sections dict to only the named sections. "
                "Identity fields (number, title, status, type, priority) are always included. "
                "Invalid or missing section names are silently omitted — no error is raised. "
                "Default None returns the full response unchanged."
            )
        ),
    ] = None,
) -> dict:
    """View a single backlog item or GitHub issue in detail.

    Accepts a GitHub issue URL, #N, bare number, or title substring as selector.
    Use offset and limit to paginate long issue bodies.
    Use show and since to filter entry blocks within sections.
    Use include_content=False to get a compact response with section names and
    entry counts only, omitting the full body and entry content.
    Use summary=False to receive the full response; summary=True (default) returns
    a compact routing manifest that always includes sections_index so callers know
    exactly which sections exist before deciding what to load.
    Use section to filter the response to specific sections by index, title, or regex.
    Use sections=[...] to return only the named sections plus identity fields
    (number, title, status, type, priority).

    Progressive disclosure pattern:
        Step 1 — call with summary=True (default) to get sections_index and metadata.
        Step 2 — load only the sections needed:
            backlog_view(selector="...", summary=False, section="Fact-Check")
            backlog_view(selector="...", summary=False, section="0,1,3")
            backlog_view(selector="...", summary=False, section="/acceptance|plan/")

    Returns:
        When summary=True (default): compact dict with issue_number, title, labels,
        status, plan_path, sections_index (all sections as [N] Title (count) lines),
        _summary, _full_chars, and _hint with section-loading syntax.
        When summary=False: dict with title, priority, issue, plan, file_path, body,
        sections metadata, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        # MCP tool parameters are always strings; convert numeric show values to int.
        parsed_show: str | int | None = show
        if show is not None:
            try:
                parsed_show = int(show)
            except ValueError:
                parsed_show = show
        result = await asyncio.to_thread(
            operations.view_item,
            selector=selector,
            include_content=include_content,
            offset=offset,
            limit=limit,
            show=parsed_show,
            since=since,
            section=section,
            output=out,
        )
        full_response = result.model_dump()
        if not summary:
            # Primitive 3: filter to named sections when requested.
            if sections is not None:
                full_response = _filter_view_sections(full_response, sections)
            # Auto-compact: when the response exceeds the token budget return a compact
            # section-directory form so the caller can request only what it needs.
            # This check runs unconditionally for all summary=False calls — the caller's
            # sections= or section= filter does NOT bypass enforcement.  The contract is:
            # agents must never receive a response that overflows their context; the tool
            # is the correct enforcement point.
            # Heuristic pre-check: if body alone exceeds the chars threshold the full
            # response is almost certainly over budget — skip serialisation.  The precise
            # token count is still computed for borderline cases where the body is small
            # but other fields push the total over the limit.
            body_chars = len(result.body)
            if body_chars > _VIEW_BODY_CHARS_THRESHOLD:
                serialised = _json.dumps(full_response)
                return _build_over_budget_view(result, len(serialised), selector)
            serialised = _json.dumps(full_response)
            if _token_count(serialised) > _VIEW_TOKEN_BUDGET:
                return _build_over_budget_view(result, len(serialised), selector)
            return full_response
        return _build_compact_manifest(result, full_response, selector)
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Sync Backlog", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
async def backlog_sync(
    ctx: Context,
    dry_run: Annotated[bool, Field(description="Preview what would be synced without making changes")] = False,
) -> dict:
    """Sync backlog items with GitHub: create missing issues and push groomed content.

    Use dry_run=true to preview changes without modifying anything.

    Returns:
        Dict with created and pushed counts and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        await ctx.info("Starting backlog sync" + (" (dry-run)" if dry_run else ""))
        result = await asyncio.to_thread(operations.sync_items, dry_run=dry_run, output=out)
        for w in out.warnings:
            await ctx.warning(w)
        created = result.get("created", 0)
        pushed = result.get("pushed", 0)
        await ctx.info(f"Sync complete: {created} issue(s) created, {pushed} item(s) pushed")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Close Backlog Item", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_close(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    reason: Annotated[
        str,
        Field(
            description="Why the item is being dismissed. One of: duplicate, out_of_scope, superseded, wontfix, blocked"
        ),
    ],
    reference: Annotated[
        str, Field(description="Related item reference: #N, URL, or title of the item this duplicates/is superseded by")
    ] = "",
    comment: Annotated[str, Field(description="Additional context about why this item is being closed")] = "",
    cleanup: Annotated[
        bool, Field(description="Remove local file after close; index link becomes GitHub issue URL")
    ] = False,
    force: Annotated[bool, Field(description="Close even if open PRs reference the issue")] = False,
) -> dict:
    """Dismiss a backlog item without completing it and close its GitHub issue.

    Use for items that are duplicates, out of scope, superseded, wontfix,
    or permanently blocked. For completed work, use backlog_resolve instead.

    Returns:
        Dict with closed item title, reason, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.close_item,
            selector=selector,
            reason=reason,
            reference=reference,
            comment=comment,
            cleanup=cleanup,
            force=force,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Resolve Backlog Item", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_resolve(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    summary: Annotated[str, Field(description="What was done — 1-2 sentence completion summary (required)")],
    plan: Annotated[str | None, Field(description="Plan path or completion reference")] = None,
    method: Annotated[str | None, Field(description="How the work was done — approach taken")] = None,
    notes: Annotated[str | None, Field(description="Problems found, surprises, or other comments")] = None,
    follow_ups: Annotated[str | None, Field(description="Created follow-up tickets (comma-separated refs)")] = None,
    findings: Annotated[str | None, Field(description="Retrospective learnings from this work")] = None,
    cleanup: Annotated[
        bool, Field(description="Remove local file after resolve; index link becomes GitHub issue URL")
    ] = False,
    force: Annotated[bool, Field(description="Resolve even if open PRs reference the issue")] = False,
) -> dict:
    """Mark a backlog item as DONE (completed) and close its GitHub issue.

    Creates a structured completion record as an audit/retrospective trail.
    Only summary is required — for trivial items a one-liner suffices.
    For dismissals (duplicate, out of scope, etc.), use backlog_close instead.

    Returns:
        Dict with resolved item title, summary, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.resolve_item,
            selector=selector,
            summary=summary,
            plan=plan or "",
            method=method or "",
            notes=notes or "",
            follow_ups=follow_ups or "",
            findings=findings or "",
            cleanup=cleanup,
            force=force,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update Backlog Item", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_update(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    plan: Annotated[str | None, Field(description="Path to a plan file to attach to the item")] = None,
    status: Annotated[
        str | None,
        Field(description="Set item status (e.g. 'in-progress'). Updates GitHub issue labels when applicable."),
    ] = None,
    section: Annotated[
        str | None, Field(description="Section name for groomed content update (use with content parameter)")
    ] = None,
    content: Annotated[
        str | None, Field(description="Content for the named section (use with section parameter)")
    ] = None,
    title: Annotated[
        str | None,
        Field(
            description="New title for the item. Updates the local file name field and GitHub issue title if the item already has a linked issue."
        ),
    ] = None,
    description: Annotated[
        str | None,
        Field(description="New description text for the item. Updates the local file only — no GitHub sync."),
    ] = None,
    entry_id: Annotated[
        str | None, Field(description="Timestamp ID of an existing entry to replace within the section")
    ] = None,
    replace_section: Annotated[
        bool, Field(description="Strike all existing entries in the section and append new content")
    ] = False,
    reason: Annotated[
        str | None, Field(description="Reason for striking entries (required when replace_section=True)")
    ] = None,
    verified: Annotated[
        bool,
        Field(
            description="Apply status:verified label to the GitHub issue. "
            "Signals that /complete-implementation quality gates have passed. "
            "Auto-creates the label if absent. No-op when item has no issue number."
        ),
    ] = False,
) -> dict:
    """Update a backlog item: attach a plan, set status, or write groomed content.

    For groomed content, provide section + content for section updates.
    Use entry_id to replace a specific entry, or replace_section=True to
    strike all entries and append new content. Groomed content is synced
    to the GitHub issue when the item has one.

    Use verified=True after /complete-implementation quality gates pass to
    apply the status:verified label to the linked GitHub issue.

    Returns:
        Dict with updated item title, applied changes, and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.update_item,
            selector=selector,
            plan=plan,
            status=status,
            section=section,
            content=content,
            title=title,
            description=description,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
            verified=verified,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Groom Backlog Item", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_groom(
    ctx: Context,
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    section: Annotated[
        str | None, Field(description="Section name for incremental update (use with content parameter)")
    ] = None,
    content: Annotated[
        str | None, Field(description="Content for the named section (use with section parameter)")
    ] = None,
    entry_id: Annotated[
        str | None, Field(description="Timestamp ID of an existing entry to replace within the section")
    ] = None,
    replace_section: Annotated[
        bool, Field(description="Strike all existing entries in the section and append new content")
    ] = False,
    reason: Annotated[
        str | None, Field(description="Reason for striking entries (required when replace_section=True)")
    ] = None,
    append: Annotated[
        bool,
        Field(
            description=(
                "When True and section is provided, append new content after existing section content "
                "(newline-separated) instead of replacing it. No entry-block wrapping is applied. "
                "Use this to incrementally add lines to a section such as ## Concerns."
            )
        ),
    ] = False,
    sections: Annotated[
        dict[str, str] | None,
        Field(
            description=(
                "Batch section writes: mapping of section name to raw content. "
                "Mutually exclusive with section, content, entry_id, replace_section, reason, and append. "
                "Each section is written with entry-block wrapping applied automatically. "
                "GitHub sync is performed after all local writes complete."
            )
        ),
    ] = None,
    mark_groomed: Annotated[
        bool,
        Field(
            description=(
                "When True, advance item status to groomed after content is written: set local frontmatter "
                "status to 'groomed', remove status:needs-grooming label (idempotent), and add status:groomed "
                "label (created if absent). Default False preserves existing behavior."
            )
        ),
    ] = False,
) -> dict:
    """Write groomed content into a backlog item's per-item file and sync to its GitHub issue.

    Provide section + content for section updates. Use entry_id to replace
    a specific entry, or replace_section=True to strike all entries and
    append new content. Set append=True to add content after existing section
    text without entry-block wrapping. Use sections for atomic multi-section
    writes in a single call — mutually exclusive with section/content/etc.
    When the item has a GitHub issue, the groomed content is synced there
    automatically.

    Returns:
        Dict with groomed item title, synced status, and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    if sections is not None and any((section, content, entry_id, replace_section, reason, append)):
        return {
            "error": "sections is mutually exclusive with section, content, entry_id, replace_section, reason, and append"
        }
    try:
        await ctx.info(f"Grooming item: {selector}")
        result = await asyncio.to_thread(
            operations.groom_item,
            selector=selector,
            section=section,
            content=content,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
            append=append,
            sections=sections,
            mark_groomed=mark_groomed,
        )
        for w in out.warnings:
            await ctx.warning(w)
        title = result.get("title", selector)
        await ctx.info(f"Groomed: {title}")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Normalize Backlog Items",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def backlog_normalize(
    ctx: Context,
    dry_run: Annotated[bool, Field(description="Preview normalization changes without modifying files")] = False,
) -> dict:
    """Normalize all per-item files to research-style metadata format and remove body duplication.

    This is a one-off maintenance operation. Use dry_run=true to preview
    what would change.

    Returns:
        Dict with count of normalized files and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        await ctx.info("Starting normalize" + (" (dry-run)" if dry_run else ""))
        result = await asyncio.to_thread(operations.normalize_items, dry_run=dry_run, output=out)
        for w in out.warnings:
            await ctx.warning(w)
        updated = result.get("updated", 0)
        suffix = " (dry-run)" if dry_run else ""
        await ctx.info(f"Normalized {updated} file(s){suffix}")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Pull Backlog Items", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_pull(
    ctx: Context,
    selector: Annotated[
        str | None,
        Field(
            description="Optional selector to pull a single issue: #N, bare number, GitHub URL, or title substring. When omitted, pulls all issues."
        ),
    ] = None,
    dry_run: Annotated[bool, Field(description="Preview what would be pulled without modifying local files")] = False,
    force: Annotated[
        bool, Field(description="Overwrite local content even if local version is newer or longer")
    ] = False,
    diff: Annotated[bool, Field(description="Include entry-level diff output showing local vs remote changes")] = False,
) -> dict:
    """Pull issue body content from GitHub into local per-item files.

    When selector is provided, pulls a single issue by #N, bare number,
    GitHub URL, or title substring. When omitted, pulls all issues.

    Auto-migrates P0/P1 items lacking GitHub Issues by creating them.
    Merges by section using entry-aware merge (keeps longer entries,
    preserves strikes). Use dry_run=true to preview changes.
    Use diff=true to include entry-level diff output.

    Returns:
        Dict with count of pulled items (bulk) or file_path (single) and
        output messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        if selector is not None:
            await ctx.info(f"Pulling issue: {selector}")
            result = await asyncio.to_thread(operations.pull_by_selector, selector, diff=diff, output=out)
            for w in out.warnings:
                await ctx.warning(w)
            file_path = result.get("file_path")
            await ctx.info(f"Pulled: {file_path}" if file_path else "Nothing pulled")
            return {**result, **out.to_dict()}
        await ctx.info("Starting bulk pull from GitHub" + (" (dry-run)" if dry_run else ""))
        result = await asyncio.to_thread(operations.pull_items, dry_run=dry_run, force=force, diff=diff, output=out)
        for w in out.warnings:
            await ctx.warning(w)
        pulled = result.get("pulled", 0)
        await ctx.info(f"Pull complete: {pulled} item(s) pulled")
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create SAM Task", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
async def backlog_create_sam_task(
    parent_issue_number: Annotated[
        str | int,
        Field(
            description="Parent story issue number (integer for GitHub; beads IDs not supported for SAM task operations)"
        ),
    ],
    task_id: Annotated[str, Field(description="Feature-scoped task ID, e.g. 'T1'")],
    feature: Annotated[str, Field(description="Feature slug, e.g. 'my-feature'")],
    task_type: Annotated[str, Field(description="Task category: research | implement | review | fix | docs")],
    agent: Annotated[str, Field(description="Agent name to execute this task")],
    priority: Annotated[int, Field(description="Priority 1-5 (1=highest)")] = 2,
    skills: Annotated[list[str], Field(description="Skill names for the executing agent")] = [],  # noqa: B006
    dependencies: Annotated[list[str], Field(description="Task IDs this task depends on")] = [],  # noqa: B006
    description: Annotated[str, Field(description="Human-readable description of the task")] = "",
    acceptance_criteria: Annotated[list[str] | None, Field(description="Acceptance criteria strings")] = None,
    labels: Annotated[list[str] | None, Field(description="GitHub label names to apply")] = None,
) -> dict:
    """Create a GitHub sub-issue for a SAM task under a parent story issue.

    Use to bootstrap GitHub visibility for a task when starting a new feature plan.

    Returns:
        Dict with issue_number, title, url, and output messages. On error, returns error key.
    """
    out = Output()
    if isinstance(parent_issue_number, str):
        return {
            "error": f"backlog_create_sam_task requires an integer issue number, got {parent_issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(
            operations.create_sam_task,
            parent_issue_number=parent_issue_number,
            task_id=task_id,
            feature=feature,
            task_type=task_type,
            agent=agent,
            priority=priority,
            skills=skills,
            dependencies=dependencies,
            description=description,
            acceptance_criteria=acceptance_criteria,
            labels=labels,
            output=out,
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get SAM Tasks", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_get_sam_tasks(
    parent_issue_number: Annotated[
        str | int,
        Field(
            description="Parent story issue number (integer for GitHub; beads IDs not supported for SAM task operations)"
        ),
    ],
    refresh_cache: Annotated[bool, Field(description="Write updated cache after fetching")] = True,
) -> dict:
    """Return all SAM task sub-issues for a parent story issue.

    Returns tasks list with SamTask fields plus issue_number and issue_url.
    Falls back to local cache if GitHub is unavailable.
    Use to inspect per-task status from the GitHub source of truth.
    """
    out = Output()
    if isinstance(parent_issue_number, str):
        return {
            "error": f"backlog_get_sam_tasks requires an integer issue number, got {parent_issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(
            operations.get_sam_tasks, parent_issue_number=parent_issue_number, refresh_cache=refresh_cache, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update SAM Task Status",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def backlog_update_sam_task_status(
    issue_number: Annotated[
        str | int,
        Field(
            description="Task sub-issue number (integer for GitHub; beads IDs not supported for SAM task operations)"
        ),
    ],
    new_status: Annotated[str, Field(description="Target status: not-started | in-progress | complete | blocked")],
) -> dict:
    """Update the status field in a SAM task sub-issue.

    Patches the sam:task YAML block in the issue body. No-op if status already matches.

    Returns:
        Dict with updated (bool), issue_number, new_status, and output messages.
        On error, returns error key.
    """
    out = Output()
    if isinstance(issue_number, str):
        return {
            "error": f"backlog_update_sam_task_status requires an integer issue number, got {issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(
            operations.update_sam_task_status, issue_number=issue_number, new_status=new_status, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


# ---------------------------------------------------------------------------
# Artifact manifest tools
# ---------------------------------------------------------------------------

_artifact_registry = ArtifactRegistry()
# TODO(H05): Move to FastMCP lifespan context — eliminate module-level singleton.
_artifact_provider: ArtifactBackend | None = None
_artifact_provider_warning: str | None = None


def _require_artifact_entries(entries: list, label: str) -> None:
    """Raise BacklogError when no artifact entries are found.

    Args:
        entries: List of artifact entries (may be empty).
        label: Error message to include in the exception.

    Raises:
        BacklogError: When ``entries`` is empty.
    """
    if not entries:
        raise BacklogError(label)


def _get_artifact_provider() -> ArtifactBackend:
    """Return (or lazily create) the ArtifactBackend singleton.

    Deferred so the provider is created after ``_init_models()`` has resolved
    the repo slug and project root from the ``--project-dir`` argument.

    When the configured remote backend is unavailable or unconfigured, falls
    back to :class:`~backlog_core.artifact_provider_local.LocalFilesystemArtifactProvider`
    and sets ``_artifact_provider_warning`` so every artifact MCP tool surfaces
    the degraded-mode notice to callers.

    Returns:
        Initialised ``ArtifactBackend`` instance.  Never raises — falls back
        to the local filesystem provider when the remote backend fails to
        initialise.
    """
    global _artifact_provider, _artifact_provider_warning  # noqa: PLW0603
    if _artifact_provider is not None:
        return _artifact_provider
    provider: ArtifactBackend
    repo = _models.get_default_repo()
    if not repo:
        provider = LocalFilesystemArtifactProvider(root_worktree=_dh_paths.git_project_root())
    else:
        try:
            provider = create_artifact_provider(repo=repo, root_worktree=_models.get_repo_root())
        except (GitHubUnavailableError, BacklogError):
            provider = LocalFilesystemArtifactProvider(root_worktree=_dh_paths.git_project_root())
    _artifact_provider = provider
    if isinstance(provider, LocalFilesystemArtifactProvider):
        _artifact_provider_warning = "Artifacts stored in local filesystem provider. Remote sync unavailable."
    return _artifact_provider


@mcp.tool(
    annotations=ToolAnnotations(
        title="Register Artifact", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def artifact_register(
    item_id: Annotated[
        str | int,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[
        str,
        Field(
            description=(
                "Artifact type: feature-context, architect, task-plan, T0-baseline, TN-verification, "
                "codebase-analysis, research"
            )
        ),
    ],
    artifact_id: Annotated[
        str,
        Field(
            description=(
                "Logical identifier for the artifact. Use a repo-relative path for file artifacts "
                "(e.g. plan/architect-foo.md) or a logical id for content-only artifacts "
                "(e.g. T0-baseline-{slug})."
            )
        ),
    ],
    status: Annotated[str, Field(description="Lifecycle status: draft, current, superseded, archived")] = "current",
    agent: Annotated[str, Field(description="Name of the producing agent")] = "",
    content: Annotated[
        str | None,
        Field(
            description=(
                "Optional artifact content to store as a GitHub issue comment. "
                "When provided the content is stored in a collapsible comment identified by type+path. "
                "When omitted only the manifest entry is registered (backward-compatible)."
            )
        ),
    ] = None,
) -> dict:
    """Upsert an artifact entry in the manifest for a GitHub issue.

    Idempotent by (artifact_type, artifact_id). If an entry with the same type and
    artifact_id already exists it is updated in-place (status, agent, timestamp).
    If only the type matches but the artifact_id differs, a new row is added.

    Content upload follows three-tier resolution:

    1. **Explicit content** — when *content* is provided, it is uploaded
       directly to a structured GitHub issue comment so it can be retrieved
       via ``artifact_read`` even from worktree-isolated agents.
    2. **Auto-read from local file** — when *content* is ``None`` but a local
       file exists at *artifact_id* (resolved against the root worktree), the
       file is read automatically and uploaded as in tier 1.
    3. **Manifest-only** — when *content* is ``None`` and no local file exists,
       the manifest entry is registered without content storage.  A warning is
       emitted so callers can detect the gap.

    Returns:
        Dict with registered (bool), artifact_count (int), action (str),
        content_stored (bool), and output messages/warnings. On error, dict
        contains an error key.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        if _artifact_provider_warning is not None:
            out.warnings.append(_artifact_provider_warning)
        artifact_type_enum = ArtifactType(artifact_type)
        status_enum = ArtifactStatus(status)
        entry = ArtifactEntry(
            artifact_type=artifact_type_enum,
            artifact_id=artifact_id,
            status=status_enum,
            created_at=_datetime.now(UTC).isoformat(),
            agent=agent,
        )

        def _run() -> RegisterResult:
            manifest = provider.get_manifest(item_id)
            updated_manifest = _artifact_registry.register(manifest, entry)
            provider.set_manifest(item_id, updated_manifest)
            # Determine action: "updated" if entry pre-existed, "added" otherwise.
            existed = any(
                e.artifact_type == artifact_type_enum and e.artifact_id == artifact_id for e in manifest.artifacts
            )
            action = "updated" if existed else "added"

            # Content upload — three-way resolution:
            # 1. Explicit content provided → use it directly.
            # 2. No explicit content but local file exists → read and upload.
            # 3. Neither → register manifest entry only; emit a warning.
            upload_content: str | None = content
            if upload_content is None:
                upload_content = provider.read_local_artifact_content(artifact_id)
                if upload_content is None:
                    out.warn(
                        f"No content provided and no local file found at {artifact_id!r}. "
                        "Manifest entry registered without content storage."
                    )

            content_stored = False
            if upload_content is not None:
                provider.store_artifact_content(item_id, artifact_type, artifact_id, upload_content)
                content_stored = True

            return RegisterResult(
                registered=True,
                artifact_count=len(updated_manifest.artifacts),
                action=action,
                content_stored=content_stored,
            )

        result = await asyncio.to_thread(_run)
        return {**result.model_dump(), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Artifacts", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def artifact_list(
    item_id: Annotated[
        str | int,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[str | None, Field(description="Filter by artifact type (optional)")] = None,
) -> dict:
    """Return all artifacts registered for a backlog item.

    Optionally filter by artifact type. Returns an empty list when no
    manifest section exists yet — this is not an error.

    Returns:
        Dict with artifacts (list of dicts), count (int), and output
        messages/warnings. On error, dict contains an error key.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        if _artifact_provider_warning is not None:
            out.warnings.append(_artifact_provider_warning)
        type_filter: ArtifactType | None = ArtifactType(artifact_type) if artifact_type else None

        def _run() -> list[dict]:
            manifest = provider.get_manifest(item_id)
            if type_filter is not None:
                entries = _artifact_registry.get_by_type(manifest, type_filter)
            else:
                entries = manifest.artifacts
            return [e.model_dump(mode="json") for e in entries]

        artifacts = await asyncio.to_thread(_run)
        return {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Artifact", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def artifact_get(
    item_id: Annotated[
        str | int,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[str, Field(description="Artifact type to retrieve")],
) -> dict:
    """Return metadata for a specific artifact type registered on a backlog item.

    If multiple artifacts of the same type exist (e.g. multiple
    codebase-analysis files), all are returned.

    Returns:
        Dict with artifacts (list of dicts), count (int), and output
        messages/warnings. Returns error key when type is not found.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        if _artifact_provider_warning is not None:
            out.warnings.append(_artifact_provider_warning)
        type_enum = ArtifactType(artifact_type)

        def _run() -> list[dict]:
            manifest = provider.get_manifest(item_id)
            entries = _artifact_registry.get_by_type(manifest, type_enum)
            return [e.model_dump(mode="json") for e in entries]

        artifacts = await asyncio.to_thread(_run)
        if not artifacts:
            return {"error": f"No artifacts of type '{artifact_type}' found for item #{item_id}", **out.to_dict()}
        return {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Artifact", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def artifact_read(
    item_id: Annotated[
        str | int,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[str, Field(description="Artifact type whose content to read")],
) -> dict:
    """Read the file content for an artifact registered on a backlog item.

    Content retrieval order:

    1. GitHub issue comments — searches for a stored artifact content comment
       matching the artifact type and path.  This succeeds even when the local
       filesystem file does not exist (e.g. from a worktree-isolated agent).
    2. Local filesystem fallback — when no GitHub comment is found, resolves
       the artifact path against the root worktree.

    Path safety (filesystem path): the provider validates that the resolved
    path is under the repository root (path traversal prevention).

    Returns:
        Dict with type (str), path (str), content (str), status (str), and
        output messages/warnings. Returns error key on type-not-found, path
        safety violation, or when content is not found via either source.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        if _artifact_provider_warning is not None:
            out.warnings.append(_artifact_provider_warning)
        type_enum = ArtifactType(artifact_type)

        def _run() -> ArtifactContent:
            manifest = provider.get_manifest(item_id)
            entries = _artifact_registry.get_by_type(manifest, type_enum)
            _require_artifact_entries(entries, f"No artifacts of type '{artifact_type}' found for item #{item_id}")
            # Sort by created_at desc so the most recently registered entry comes first.
            # Entries without a timestamp sort last (empty string is smallest; stable sort
            # preserves insertion order among multiple undated entries).
            entries_sorted = sorted(entries, key=lambda e: e.created_at or "", reverse=True)
            entry = entries_sorted[0]
            if len(entries_sorted) > 1:
                skipped = [e.artifact_id for e in entries_sorted[1:]]
                out.warnings.append(
                    f"Multiple {artifact_type!r} artifacts found ({len(entries_sorted)}); "
                    f"returning most recent ({entry.artifact_id!r}). Skipped: {skipped}"
                )

            # 1. Try GitHub comment storage first.
            github_content = provider.read_artifact_content_from_remote(item_id, artifact_type, entry.artifact_id)
            if github_content is not None:
                return ArtifactContent(
                    artifact_type=entry.artifact_type,
                    path=entry.artifact_id,
                    content=github_content,
                    status=entry.status,
                )

            # 2. Fall back to local filesystem.
            content = provider.read_artifact_content(entry.artifact_id)
            return ArtifactContent(
                artifact_type=entry.artifact_type, path=entry.artifact_id, content=content, status=entry.status
            )

        result = await asyncio.to_thread(_run)
        return {**result.model_dump(mode="json"), **out.to_dict()}
    except (ValueError, KeyError) as e:
        return {"error": f"Invalid parameter: {e}", **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Ready SAM Tasks", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_get_ready_sam_tasks(
    parent_issue_number: Annotated[
        str | int,
        Field(
            description="Parent story issue number (integer for GitHub; beads IDs not supported for SAM task operations)"
        ),
    ],
) -> dict:
    """Return SAM tasks ready for execution from GitHub sub-issues.

    Fetches sub-issues, resolves dependency graph locally, returns tasks whose
    status is not-started and all dependencies are terminal.
    Output shape matches implementation_manager.py ready-tasks JSON:
    feature, ready_tasks, count. Each ready_task includes id, name, agent, skills, issue_number.
    Falls back to local cache if GitHub is unavailable.
    """
    out = Output()
    if isinstance(parent_issue_number, str):
        return {
            "error": f"backlog_get_ready_sam_tasks requires an integer issue number, got {parent_issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(
            operations.get_ready_sam_tasks, parent_issue_number=parent_issue_number, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Strike Entry", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_strike_entry(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    entry_id: Annotated[str, Field(description="Timestamp ID of the entry to strike")],
    reason: Annotated[str, Field(description="Human-readable reason for striking the entry")],
    section: Annotated[str | None, Field(description="Optional section name to scope the search within")] = None,
) -> dict:
    """Strike (retract) an entry block within a backlog item.

    Wraps the entry in a collapsed details block with the reason,
    preserving the original content for audit. Syncs to GitHub issue
    if the item has one.

    Returns:
        Dict with strike results and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.strike_entry, selector=selector, entry_id=entry_id, reason=reason, section=section, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Labels", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list_labels(limit: Annotated[int, Field(description="Maximum labels to return")] = 100) -> dict:
    """List repository labels (read-only).

    Returns all labels defined on the repository, up to ``limit``.
    Label mutations are not supported by this tool; they are owned by
    the state transition handler.

    Returns:
        Dict with ``labels`` (list of dicts with ``name``, ``color``, ``description``),
        ``count``, and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_labels, limit=limit, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Merged PRs", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list_merged_prs(
    search: Annotated[
        str | None,
        Field(
            description=(
                "Optional substring to filter by (checked against PR title and body, "
                "case-insensitive). Use to find PRs related to a specific issue number "
                "(e.g. '#42') or keyword."
            )
        ),
    ] = None,
    limit: Annotated[int, Field(description="Maximum number of PRs to return")] = 20,
) -> dict:
    """List merged pull requests, optionally filtered by a search query.

    Only PRs that were actually merged (not just closed) are returned.
    Use ``search`` to filter by issue reference (e.g. ``'#42'``) or any
    keyword present in the PR title or body.

    Returns:
        Dict with ``pull_requests`` (list of dicts with ``number``,
        ``title``, ``merged_at``, ``author``, ``url``, ``head_branch``),
        ``count``, and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_merged_prs, search=search, limit=limit, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Milestones", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list_milestones(
    state: Annotated[str, Field(description="Milestone state filter: open | closed | all")] = "open",
) -> dict:
    """List repository milestones filtered by state.

    Returns milestones with their issue counts and optional due dates.

    Returns:
        Dict with ``milestones`` (list of dicts with ``number``, ``title``,
        ``state``, ``description``, ``due_on``, ``open_issues``,
        ``closed_issues``), ``count``, and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_milestones, state=state, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Soonest Milestone", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_get_soonest_milestone() -> dict:
    """Return the open milestone with the earliest due date.

    Milestones without a due date are excluded. If all open milestones
    lack a due date, the first one by GitHub's default ordering is returned
    with a warning.

    Returns:
        Dict with ``milestone`` (dict or None) containing ``number``, ``title``,
        ``state``, ``description``, ``due_on``, ``open_issues``,
        ``closed_issues``, and output messages/warnings.
        ``milestone`` is ``None`` when no open milestones exist.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.get_soonest_milestone, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Milestone", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
async def backlog_create_milestone(
    title: Annotated[str, Field(description="Milestone title (required, must be non-empty)")],
    description: Annotated[str, Field(description="Optional milestone description")] = "",
    due_on: Annotated[
        str | None,
        Field(description="Optional due date as ISO 8601 string, e.g. '2026-06-30' or '2026-06-30T00:00:00Z'"),
    ] = None,
) -> dict:
    """Create a new milestone on the repository.

    Returns:
        Dict with ``milestone`` containing ``number``, ``title``, ``state``,
        ``description``, ``due_on``, ``open_issues``, ``closed_issues``,
        and output messages/warnings.
        On error, dict contains an ``error`` key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.create_milestone, title=title, description=description, due_on=due_on, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Issues", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list_issues(
    milestone: Annotated[str | None, Field(description="Filter by milestone title")] = None,
    labels: Annotated[str | None, Field(description="Comma-separated label names to filter by")] = None,
    state: Annotated[str, Field(description="Issue state: open, closed, or all")] = "open",
    limit: Annotated[int, Field(description="Maximum issues to return")] = 30,
) -> dict:
    """List GitHub issues with optional milestone, label, and state filters.

    Returns:
        Dict with issues list, count, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_issues, milestone=milestone, labels=labels, state=state, limit=limit, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Comment on Issue", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
async def backlog_comment_issue(
    issue_number: Annotated[
        str | int,
        Field(description="Issue number (integer for GitHub; beads IDs not supported for comment operations)"),
    ],
    body: Annotated[str, Field(description="Comment body (Markdown)")],
) -> dict:
    """Add a comment to a GitHub issue.

    Returns:
        Dict with issue_number, comment_id, comment_url, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    if isinstance(issue_number, str):
        return {
            "error": f"backlog_comment_issue requires an integer issue number, got {issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(operations.comment_issue, issue_number=issue_number, body=body, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Issue Comments", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list_comments(
    issue_number: Annotated[
        str | int,
        Field(description="Issue number (integer for GitHub; beads IDs not supported for comment operations)"),
    ],
    limit: Annotated[int, Field(description="Maximum comments to return")] = 20,
    offset: Annotated[int, Field(description="Number of comments to skip")] = 0,
) -> dict:
    """List comments on a GitHub issue.

    Returns:
        Dict with comments (list of {id, author, created_at, updated_at, preview}),
        count, has_more, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    if isinstance(issue_number, str):
        return {
            "error": f"backlog_list_comments requires an integer issue number, got {issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(
            operations.list_comments, issue_number=issue_number, limit=limit, offset=offset, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Issue Comment", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_read_comment(
    issue_number: Annotated[
        str | int,
        Field(description="Issue number (integer for GitHub; beads IDs not supported for comment operations)"),
    ],
    comment_id: Annotated[
        int,
        Field(
            description="REST comment database ID (integer). Use the GitHub REST API or issue comment list to obtain this ID."
        ),
    ],
) -> dict:
    """Read the full body of a single comment on a GitHub issue.

    Returns:
        Dict with id (GraphQL node ID), author, created_at, updated_at,
        body (full Markdown — no truncation), and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    if isinstance(issue_number, str):
        return {
            "error": f"backlog_read_comment requires an integer issue number, got {issue_number!r}",
            **out.to_dict(),
        }
    try:
        result = await asyncio.to_thread(
            operations.read_comment, issue_number=issue_number, comment_id=comment_id, output=out
        )
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Projects", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def backlog_list_projects(
    owner: Annotated[str | None, Field(description="GitHub owner (org or user). Defaults to repo owner")] = None,
    limit: Annotated[int, Field(description="Maximum projects to return")] = 20,
) -> dict:
    """List Projects V2 for the repository owner via GraphQL.

    Returns:
        Dict with projects list, count, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_projects, owner=owner, limit=limit, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Project", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
    )
)
async def backlog_create_project(
    title: Annotated[str, Field(description="Project title")],
    owner: Annotated[str | None, Field(description="GitHub owner (org or user). Defaults to repo owner")] = None,
) -> dict:
    """Create a Projects V2 project under the repository owner.

    Resolves the owner node ID then runs the createProjectV2 GraphQL mutation.

    Returns:
        Dict with project_id, title, url, number, and output messages/warnings.
        On error, dict contains an error key.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.create_project, title=title, owner=owner, output=out)
        return {**result, **out.to_dict()}
    except BacklogError as e:
        return {"error": str(e), **out.to_dict()}


def _dispatch_plan_path(milestone_number: int) -> Path:
    """Return the canonical dispatch plan path for a milestone.

    Delegates to :func:`dispatch_schema.dispatch_plan_path`, resolving the
    project root from ``_models.BACKLOG_DIR``.

    Args:
        milestone_number: GitHub milestone number.

    Returns:
        Path to ``plan/milestone-{N}-dispatch.yaml`` under the project root.
    """
    # Use the git project root for dispatch plan path resolution.
    # BACKLOG_DIR now points to ~/.dh/projects/{slug}/backlog/ and cannot be
    # used to derive the project root by walking up with .parent.parent.
    return _ds.dispatch_plan_path(milestone_number, _models.get_repo_root())


def _try_register_dispatch_plan_artifact(item_id: ItemId, plan_path: Path) -> None:
    """Register the newly written dispatch plan file as a dispatch-plan artifact.

    Best-effort: logs a warning on any failure but never raises.  Called after
    ``dispatch_create_plan`` writes the plan file when the caller provides an
    associated issue identifier.

    Args:
        item_id: Issue number or beads string identifier to register the artifact against.
        plan_path: Absolute or repo-relative path to the created plan file.
    """
    log = _logging.getLogger(__name__)
    try:
        repo = _models.get_default_repo()
        if not repo:
            log.warning("dispatch_create_plan: skipping artifact registration — DEFAULT_REPO not set")
            return
        provider = create_artifact_provider(repo=repo, root_worktree=_models.get_repo_root())
        entry = ArtifactEntry(
            artifact_type=ArtifactType.DISPATCH_PLAN,
            artifact_id=str(plan_path),
            status=ArtifactStatus.CURRENT,
            agent="dispatch_create_plan",
        )
        manifest = provider.get_manifest(item_id)
        updated_manifest = _artifact_registry.register(manifest, entry)
        provider.set_manifest(item_id, updated_manifest)
        log.info("dispatch_create_plan: registered dispatch-plan artifact %s for item %s", plan_path, item_id)
    except (BacklogError, _GithubException) as exc:
        log.warning(
            "dispatch_create_plan: artifact registration failed for item %s (path=%s): %s", item_id, plan_path, exc
        )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Dispatch Plan", readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
)
async def dispatch_read(milestone_number: Annotated[int, Field(description="GitHub milestone number")]) -> dict:
    """Read a dispatch plan for the given milestone.

    Loads and returns the full plan as a dict. Returns an error dict if
    the plan file does not exist or fails YAML/schema validation.

    Returns:
        Dict with ``milestone_number`` and ``plan`` (full plan
        as a nested dict), or ``error`` on failure.
    """
    plan_path = _dispatch_plan_path(milestone_number)
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, plan_path)
    except FileNotFoundError:
        return {"error": f"Dispatch plan not found: {plan_path}", "milestone_number": milestone_number}
    except ValueError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    return {"milestone_number": milestone_number, "plan": plan.model_dump()}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Validate Dispatch Plan",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def dispatch_validate(milestone_number: Annotated[int, Field(description="GitHub milestone number")]) -> dict:
    """Validate an existing dispatch plan's structural integrity.

    Reads the plan file then runs five structural checks: duplicate issues,
    conflict group references, depends_on existence, wave ordering, and
    conflict group wave placement.

    Returns:
        Dict with ``is_valid`` (bool), ``errors`` (list[str]), and
        ``warnings`` (list[str]), or ``error`` on file/parse failure.
    """
    plan_path = _dispatch_plan_path(milestone_number)
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, plan_path)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    result = await asyncio.to_thread(_ds.validate_plan_integrity, plan)
    return {"milestone_number": milestone_number, **dataclasses.asdict(result)}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Check Dispatch Staleness",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def dispatch_stale_check(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    repo: Annotated[str, Field(description="Repository slug owner/name. Defaults to repo from project")] = "",
) -> dict:
    """Check whether a dispatch plan is stale relative to the current milestone.

    Fetches open issues assigned to the milestone from GitHub, compares
    their issue numbers against those in the plan, and returns a stale/fresh
    indicator with added/removed issue lists.

    Returns:
        Dict with ``is_stale`` (bool), ``added_issues`` (list[int]),
        ``removed_issues`` (list[int]), and ``message`` (str).
        Returns ``error`` on file/parse or GitHub failure.
    """
    plan_path = _dispatch_plan_path(milestone_number)
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, plan_path)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc), "milestone_number": milestone_number}

    def _fetch_milestone_issue_numbers() -> list[int]:
        gh_repo = _get_config().backend.get_github(repo)
        owner, repo_name = gh_repo.full_name.split("/", 1)
        open_issues = _get_config().backend.sync_issues_graphql(
            gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number
        )
        closed_issues = _get_config().backend.sync_issues_graphql(
            gh_repo, owner, repo_name, state="CLOSED", milestone_number=milestone_number
        )
        return [issue["number"] for issue in open_issues + closed_issues]

    try:
        current_numbers = await asyncio.to_thread(_fetch_milestone_issue_numbers)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except (BacklogError, _GithubException) as exc:
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    result = await asyncio.to_thread(_ds.detect_stale_plan, plan, current_numbers)
    return {"milestone_number": milestone_number, **dataclasses.asdict(result)}


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Dispatch Plan", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def dispatch_create_plan(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    plan: Annotated[_ds.DispatchPlan, Field(description="The dispatch plan for this milestone.")],
    overwrite: Annotated[
        bool,
        Field(
            description=(
                "Allow overwriting an existing plan file. When False (default), returns an error "
                "if plan/milestone-{N}-dispatch.yaml already exists."
            )
        ),
    ] = False,
    validate: Annotated[
        bool,
        Field(
            description=(
                "Run structural integrity validation after writing. When True (default), the response "
                "includes is_valid, errors, and warnings from validate_plan_integrity()."
            )
        ),
    ] = True,
    issue: Annotated[
        int | None,
        Field(
            description=(
                "Optional GitHub issue number to associate. When provided, auto-registers the plan "
                "file as a 'dispatch-plan' artifact on the issue."
            )
        ),
    ] = None,
) -> dict:
    """Create or overwrite a dispatch plan YAML file for a milestone.

    Accepts a typed ``DispatchPlan`` model, writes it atomically to
    ``plan/milestone-{N}-dispatch.yaml``, and optionally validates structural
    integrity after writing.

    Args:
        milestone_number: GitHub milestone number.
        plan: The dispatch plan for this milestone. ``plan.milestone.number``
            must match ``milestone_number``.
        overwrite: When ``False`` (default) returns an error if the plan file
            already exists.
        validate: When ``True`` (default) runs ``validate_plan_integrity`` after
            writing and includes the result in the response.
        issue: Optional GitHub issue number.  When provided, auto-registers the
            plan file as a ``dispatch-plan`` artifact (best-effort).

    Returns:
        Success dict with ``milestone_number``, ``wave_count``,
        ``item_count``, ``is_valid``, ``errors``, ``warnings``, and ``messages``.
        Error dict contains an ``error`` key.
    """
    out = Output()
    plan_path = _dispatch_plan_path(milestone_number)

    # Verify plan.milestone.number matches the milestone_number parameter
    if plan.milestone.number != milestone_number:
        return {
            "error": (
                f"Milestone number mismatch: parameter is {milestone_number} "
                f"but plan.milestone.number is {plan.milestone.number}"
            ),
            "milestone_number": milestone_number,
            **out.to_dict(),
        }

    # Check for existing file when overwrite is False
    if not overwrite and plan_path.exists():
        return {
            "error": (f"Plan file already exists: {plan_path}. Pass overwrite=True to replace it."),
            "milestone_number": milestone_number,
            **out.to_dict(),
        }

    # 6. Write atomically
    try:
        await asyncio.to_thread(_ds.write_dispatch_plan, plan, plan_path)
    except ValueError as exc:
        return {
            "error": f"Cannot write plan (symlink target rejected): {exc}",
            "milestone_number": milestone_number,
            **out.to_dict(),
        }
    except OSError as exc:
        return {"error": f"Failed to write plan file: {exc}", "milestone_number": milestone_number, **out.to_dict()}

    out.info(f"Wrote dispatch plan to {plan_path}")

    # 7. Post-write validation
    is_valid: bool | None = None
    val_errors: list[str] = []
    val_warnings: list[str] = []
    if validate:
        val_result = await asyncio.to_thread(_ds.validate_plan_integrity, plan)
        is_valid = val_result.is_valid
        val_errors = list(val_result.errors)
        val_warnings = list(val_result.warnings)

    # 8. Artifact registration (best-effort)
    if issue is not None:
        _try_register_dispatch_plan_artifact(issue, plan_path)

    wave_count = len(plan.waves)
    item_count = sum(len(wave.items) for wave in plan.waves)

    return {
        "milestone_number": milestone_number,
        "wave_count": wave_count,
        "item_count": item_count,
        "is_valid": is_valid,
        "errors": val_errors,
        "warnings": val_warnings,
        **out.to_dict(),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Analyze Dispatch Conflicts",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def dispatch_conflicts(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    repo: Annotated[str, Field(description="Repository slug owner/name. Defaults to repo from project")] = "",
) -> dict:
    """Analyze Impact Radius conflicts for items in a milestone.

    Fetches open issues for the milestone from GitHub, extracts the
    Impact Radius section from each issue body, then runs conflict analysis
    to find items that share file paths.

    Returns:
        Dict with ``conflict_groups`` (list of group dicts with group_id,
        reason, and items), ``count`` (int), and ``milestone_number``.
        Returns ``error`` on GitHub failure.
    """

    def _fetch_items_with_impact_radius() -> list[_ImpactRadiusItem]:
        gh_repo = _get_config().backend.get_github(repo)
        owner, repo_name = gh_repo.full_name.split("/", 1)
        issue_nodes: list[_IssueNode] = _get_config().backend.sync_issues_graphql(
            gh_repo, owner, repo_name, state="OPEN", milestone_number=milestone_number
        )
        items: list[_ImpactRadiusItem] = []
        ir_re = _re.compile(r"##\s+Impact\s+Radius\b(.*?)(?=\n##|\Z)", _re.IGNORECASE | _re.DOTALL)
        for issue in issue_nodes:
            body = issue["body"] or ""
            match = ir_re.search(body)
            impact_radius = match.group(1).strip() if match else ""
            items.append({"title": issue["title"], "issue": issue["number"], "impact_radius": impact_radius})
        return items

    try:
        items = await asyncio.to_thread(_fetch_items_with_impact_radius)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), "milestone_number": milestone_number}
    except (BacklogError, _GithubException) as exc:
        return {"error": f"GitHub API error: {exc}", "milestone_number": milestone_number}

    conflict_groups = await asyncio.to_thread(operations.analyze_impact_radius_conflicts, items)
    return {
        "milestone_number": milestone_number,
        "conflict_groups": [dataclasses.asdict(cg) for cg in conflict_groups],
        "count": len(conflict_groups),
    }


# ---------------------------------------------------------------------------
# artifact_migrate helpers
# ---------------------------------------------------------------------------

#: Lazily created YAML parser for migration helpers (preserve_quotes prevents
#: round-trip mutations when loading frontmatter).
# TODO(H05): Move to FastMCP lifespan context — eliminate module-level singleton.
_migrate_yaml: _YAML | None = None


def _get_migrate_yaml() -> _YAML:
    """Return (or lazily create) the shared YAML instance for migration.

    Returns:
        Configured ``YAML`` instance with ``preserve_quotes=True``.
    """
    global _migrate_yaml  # noqa: PLW0603
    if _migrate_yaml is None:
        _migrate_yaml = _YAML()
        _migrate_yaml.preserve_quotes = True
    return _migrate_yaml


#: Filename pattern → ArtifactType mapping (ordered — first match wins).
_MIGRATE_FILENAME_PATTERNS: list[tuple[_re.Pattern[str], ArtifactType]] = [
    (_re.compile(r"^feature-context-(.+)\.md$"), ArtifactType.FEATURE_CONTEXT),
    (_re.compile(r"^architect-(.+)\.md$"), ArtifactType.ARCHITECT),
    (_re.compile(r"^P\d+-(.+)\.yaml$"), ArtifactType.TASK_PLAN),
    (_re.compile(r"^T0-baseline-(.+)\.yaml$"), ArtifactType.T0_BASELINE),
    (_re.compile(r"^TN-verification-(.+)\.yaml$"), ArtifactType.TN_VERIFICATION),
]

#: Pattern matching markdown files in plan/codebase/ → codebase-analysis.
_MIGRATE_CODEBASE_PATTERN = _re.compile(r"^.+\.md$")


def _migrate_extract_issue(file_path: Path) -> int | None:
    """Read the ``issue`` field from YAML frontmatter or a bare YAML file.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Integer issue number when found and parseable, ``None`` otherwise.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    yaml = _get_migrate_yaml()
    raw_data: object = None
    if file_path.suffix in {".yaml", ".yml"}:
        try:
            raw_data = yaml.load(text)
        except _YAMLError:
            return None
    else:
        fm_match = _re.match(r"^---\r?\n(.*?)\r?\n(?:---|\.\.\.)(?:\r?\n|$)", text, _re.DOTALL)
        if not fm_match:
            return None
        try:
            raw_data = yaml.load(fm_match.group(1))
        except _YAMLError:
            return None

    if isinstance(raw_data, dict):
        return _migrate_coerce_issue(raw_data.get("issue"))
    return None


def _migrate_coerce_issue(value: object) -> int | None:
    """Coerce a YAML value to a positive integer issue number.

    Args:
        value: Raw value from YAML (may be int, str, or None).

    Returns:
        Positive integer, or ``None``.
    """
    if value is None:
        return None
    try:
        n = int(str(value))
    except (ValueError, TypeError):
        return None
    return n if n > 0 else None


def _migrate_slug_from_path(file_path: Path) -> str:
    r"""Extract the slug from a plan filename.

    Strips known prefixes and the file extension.

    Args:
        file_path: Path object for the plan file.

    Returns:
        Slug string (e.g. ``"my-feature"``).
    """
    name = file_path.stem
    for prefix in ("feature-context-", "architect-", "T0-baseline-", "TN-verification-"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    p_match = _re.match(r"^P\d+-(.+)$", name)
    if p_match:
        return p_match.group(1)
    return name


def _migrate_find_issue_via_backlog(slug: str, backlog_items: list[dict]) -> int | None:
    """Match a slug against cached backlog items to find an issue number.

    Args:
        slug: Slug string extracted from the artifact filename.
        backlog_items: List of backlog item dicts (each has ``title``,
            ``number``, and optionally ``plan`` fields).

    Returns:
        Matched GitHub issue number, or ``None``.
    """
    slug_words = set(slug.replace("-", " ").replace("_", " ").lower().split())
    for item in backlog_items:
        title: str = item.get("title", "") or ""
        plan_path: str = item.get("plan", "") or ""
        issue_number = _migrate_coerce_issue(item.get("number"))
        if issue_number is None:
            continue
        if slug in plan_path:
            return issue_number
        title_words = set(title.replace("-", " ").replace("_", " ").lower().split())
        overlap = slug_words & title_words
        if len(overlap) >= max(1, len(slug_words) // 2):
            return issue_number
    return None


def _migrate_resolve_issue(file_path: Path, backlog_items: list[dict]) -> int | None:
    """Resolve the issue number for a file via frontmatter or slug fallback.

    Args:
        file_path: Absolute path to the artifact file.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Resolved issue number, or ``None``.
    """
    issue = _migrate_extract_issue(file_path)
    if issue is None:
        slug = _migrate_slug_from_path(file_path)
        issue = _migrate_find_issue_via_backlog(slug, backlog_items)
    return issue


def _migrate_classify_plan_file(file_path: Path) -> ArtifactType | None:
    """Classify a plan file by its filename pattern.

    Args:
        file_path: Path to the file.

    Returns:
        Matching ``ArtifactType``, or ``None``.
    """
    name = file_path.name
    for pattern, artifact_type in _MIGRATE_FILENAME_PATTERNS:
        if pattern.match(name):
            return artifact_type
    return None


_MigrateCandidate = tuple[str, ArtifactType, ItemId | None, str | None]

#: Return type for candidate discovery — (actionable candidates, filtered-out count).
_MigrateDiscoveryResult = tuple[list[_MigrateCandidate], int]


def _migrate_make_candidate(
    rel: str, atype: ArtifactType, issue: int | None, issue_filter: int | None
) -> _MigrateCandidate | None:
    """Build a candidate tuple, returning ``None`` when the file is filtered out.

    When ``issue_filter`` is set, candidates whose resolved issue does not
    match are excluded entirely (counted as filtered by the caller) rather
    than included as skipped entries.  This avoids building a 500-entry
    skipped list when a specific issue is requested.

    Args:
        rel: Repo-relative path string.
        atype: Resolved artifact type.
        issue: Resolved issue number or ``None``.
        issue_filter: When set, candidates not matching this issue are
            excluded (returns ``None``).

    Returns:
        ``(rel, atype, issue, skip_reason)`` tuple, or ``None`` when filtered.
    """
    if issue_filter is not None and (issue is None or issue != issue_filter):
        return None
    if issue is None:
        return (rel, atype, issue, "no issue number found")
    return (rel, atype, issue, None)


def _migrate_scan_codebase_dir(
    codebase_dir: Path, repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan ``plan/codebase/`` for markdown codebase-analysis files.

    Args:
        codebase_dir: Absolute path to the ``plan/codebase/`` directory.
        repo_root: Absolute path to the repository root.
        issue_filter: When set, non-matching files are counted but not
            included in the returned candidate list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)``.
    """
    results: list[_MigrateCandidate] = []
    filtered = 0
    for child in codebase_dir.iterdir():
        if not (child.is_file() and _MIGRATE_CODEBASE_PATTERN.match(child.name)):
            continue
        rel = child.relative_to(repo_root).as_posix()
        issue = _migrate_resolve_issue(child, backlog_items)
        candidate = _migrate_make_candidate(rel, ArtifactType.CODEBASE_ANALYSIS, issue, issue_filter)
        if candidate is None:
            filtered += 1
        else:
            results.append(candidate)
    return results, filtered


def _migrate_scan_plan_dir(
    plan_dir: Path, repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan ``plan/`` (excluding subdirectories other than ``codebase/``).

    Args:
        plan_dir: Absolute path to the ``plan/`` directory.
        repo_root: Absolute path to the repository root.
        issue_filter: When set, non-matching files are counted but not
            included in the returned candidate list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)``.
    """
    results: list[_MigrateCandidate] = []
    filtered = 0
    for file_path in plan_dir.iterdir():
        if file_path.is_dir():
            if file_path.name == "codebase":
                sub_results, sub_filtered = _migrate_scan_codebase_dir(
                    file_path, repo_root, issue_filter, backlog_items
                )
                results.extend(sub_results)
                filtered += sub_filtered
            continue
        if not file_path.is_file():
            continue
        atype = _migrate_classify_plan_file(file_path)
        if atype is None:
            continue
        rel = file_path.relative_to(repo_root).as_posix()
        issue = _migrate_resolve_issue(file_path, backlog_items)
        candidate = _migrate_make_candidate(rel, atype, issue, issue_filter)
        if candidate is None:
            filtered += 1
        else:
            results.append(candidate)
    return results, filtered


def _migrate_discover_candidates(
    repo_root: Path, issue_filter: int | None, backlog_items: list[dict]
) -> _MigrateDiscoveryResult:
    """Scan plan/ and research/ for artifact files.

    When ``issue_filter`` is set, only candidates linked to that issue are
    returned — non-matching files are counted in ``filtered_count`` instead
    of being included as skipped entries.  This prevents the caller from
    building a 500+ entry skipped list when a specific issue is requested.

    Args:
        repo_root: Absolute path to the repository root.
        issue_filter: When set, only candidates linked to this issue number
            are included in the returned list.
        backlog_items: Pre-fetched backlog items for slug-based fallback.

    Returns:
        Tuple of ``(candidates, filtered_count)`` where ``candidates`` is a
        list of ``(rel_path, artifact_type, issue_number, skip_reason)``
        tuples and ``filtered_count`` is the number of files excluded by the
        issue filter.
    """
    candidates: list[_MigrateCandidate] = []
    filtered = 0

    plan_dir = _dh_paths.plan_dir(repo_root)
    if plan_dir.is_dir():
        plan_candidates, plan_filtered = _migrate_scan_plan_dir(plan_dir, repo_root, issue_filter, backlog_items)
        candidates.extend(plan_candidates)
        filtered += plan_filtered

    research_dir = repo_root / "research"
    if research_dir.is_dir():
        for file_path in research_dir.rglob("*.md"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(repo_root).as_posix()
            issue = _migrate_resolve_issue(file_path, backlog_items)
            candidate = _migrate_make_candidate(rel, ArtifactType.RESEARCH, issue, issue_filter)
            if candidate is None:
                filtered += 1
            else:
                candidates.append(candidate)

    return candidates, filtered


def _migrate_register_one(
    provider: ArtifactBackend, rel_path: str, artifact_type: ArtifactType, item_id: ItemId
) -> tuple[bool, str]:
    """Register a single artifact, uploading content when available.

    Idempotent — the registry upserts on (artifact_type, path).

    Args:
        provider: Initialised ``ArtifactBackend`` instance.
        rel_path: Repo-relative path string.
        artifact_type: Resolved artifact type.
        item_id: Issue number or beads string identifier.

    Returns:
        Tuple of ``(success: bool, message: str)``.
    """
    entry = ArtifactEntry(
        artifact_type=artifact_type,
        artifact_id=rel_path,
        status=ArtifactStatus.CURRENT,
        created_at=_datetime.now(UTC).isoformat(),
        agent="artifact-migrate",
    )
    manifest = provider.get_manifest(item_id)
    existed = any(e.artifact_type == artifact_type and e.artifact_id == rel_path for e in manifest.artifacts)
    updated_manifest = _artifact_registry.register(manifest, entry)
    provider.set_manifest(item_id, updated_manifest)

    local_content = provider.read_local_artifact_content(rel_path)
    if local_content is not None:
        provider.store_artifact_content(item_id, str(artifact_type), rel_path, local_content)
        content_note = " (content uploaded)"
    else:
        content_note = " (no local file — manifest-only)"

    action = "updated" if existed else "added"
    return True, f"{action}{content_note}"


# ---------------------------------------------------------------------------
# artifact_migrate helpers (dry-run / live-run)
# ---------------------------------------------------------------------------


def _migrate_dry_run(issue_number: int | None) -> dict:
    """Discover candidates and return a preview without making any API calls.

    Args:
        issue_number: Optional issue filter passed to candidate discovery.

    Returns:
        Dict with ``dry_run``, ``would_register``, ``would_skip``,
        ``details``, and ``verify`` keys.  ``details`` contains only entries
        that would be registered or cannot be registered due to a missing
        issue number — filtered entries are counted in ``would_skip`` but not
        included individually.
    """
    repo_root = _models.get_repo_root()
    candidates, filtered_count = _migrate_discover_candidates(repo_root, issue_number, [])

    details: list[dict] = []
    would_register = 0
    would_skip = filtered_count  # filtered-out files count as skipped
    for rel_path, atype, issue, skip_reason in candidates:
        if skip_reason:
            # Include no-issue entries in details so the caller knows which
            # files could not be resolved — but do NOT include filter skips.
            details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": f"skip — {skip_reason}"})
            would_skip += 1
        else:
            details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": "would register"})
            would_register += 1

    verify = (
        f"Use artifact_list(item_id={issue_number}) to verify registered entries"
        if issue_number is not None
        else "Use artifact_list(item_id=<N>) per item to verify registered entries"
    )
    return {
        "dry_run": True,
        "would_register": would_register,
        "would_skip": would_skip,
        "details": details,
        "verify": verify,
    }


def _migrate_queue_manifest_only(
    provider: ArtifactBackend, item_id: ItemId, candidates: list[_MigrateCandidate], out: Output
) -> list[_MigrateCandidate]:
    """Append manifest-only entries (content_stored=False) to the candidate list.

    Called when ``item_id`` is provided so already-registered entries
    without uploaded content are re-processed to trigger the auto-upload path.

    Args:
        provider: Initialised provider used to read the manifest.
        item_id: Issue number or beads string identifier whose manifest to inspect.
        candidates: Existing candidate list (may be mutated by extension).
        out: Output accumulator for warnings.

    Returns:
        Extended candidate list.
    """
    try:
        manifest = provider.get_manifest(item_id)
    except (BacklogError, _GithubException):
        out.warn(f"Could not read existing manifest for item {item_id!r}. Skipping manifest check.")
        return candidates

    result = list(candidates)
    for entry in manifest.artifacts:
        # Re-queue every registered entry so the auto-upload path can attempt
        # content upload for entries where no content was stored yet.
        # _migrate_register_one is idempotent (upserts on type+path).
        already_queued = any(
            rel == entry.artifact_id and atype == entry.artifact_type
            for rel, atype, _, skip_reason in candidates
            if skip_reason is None
        )
        if not already_queued:
            result.append((entry.artifact_id, entry.artifact_type, item_id, None))
            out.warn(f"Queued manifest-only entry for re-registration: {entry.artifact_id!r}")
    return result


def _migrate_live_run(issue_number: int | None, out: Output) -> dict:
    """Execute the live migration against GitHub.

    Args:
        issue_number: Optional issue filter.
        out: Output accumulator (warnings written here).

    Returns:
        Dict with ``migrated``, ``skipped``, ``failed``, ``details``, and
        ``verify``.  ``details`` contains only migrated and failed entries —
        skipped entries are counted in ``skipped`` but not listed individually
        to keep the response compact.
    """
    repo_root = _models.get_repo_root()
    provider = _get_artifact_provider()

    backlog_items: list[dict] = []
    try:
        raw = operations.list_items()
        if isinstance(raw, list):
            backlog_items = raw
        elif isinstance(raw, dict):
            raw_backlog = raw.get("items", [])
            backlog_items = [x for x in raw_backlog if isinstance(x, dict)] if isinstance(raw_backlog, list) else []
    except (BacklogError, OSError):
        out.warn("Could not fetch backlog items for slug matching. Continuing without fallback.")

    candidates, filtered_count = _migrate_discover_candidates(repo_root, issue_number, backlog_items)

    if issue_number is not None:
        candidates = _migrate_queue_manifest_only(provider, issue_number, candidates, out)

    migrated = 0
    skipped = filtered_count  # files excluded by issue filter count as skipped
    failed = 0
    run_details: list[dict] = []

    for rel_path, atype, issue, skip_reason in candidates:
        if skip_reason:
            # Count no-issue files as skipped; do NOT add to run_details to
            # avoid a 500-entry skipped list in the response.
            skipped += 1
            continue

        assert issue is not None  # skip_reason is None only when issue resolved  # noqa: S101
        try:
            _ok, action_msg = _migrate_register_one(provider, rel_path, atype, issue)
            migrated += 1
            run_details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": action_msg})
        except (BacklogError, _GithubException, OSError) as exc:
            failed += 1
            run_details.append({"path": rel_path, "type": str(atype), "issue": issue, "outcome": f"FAILED: {exc}"})

    verify = (
        f"Use artifact_read(item_id={issue_number}, artifact_type='<type>') "
        f"or artifact_list(item_id={issue_number}) to verify"
        if issue_number is not None
        else "Use artifact_list(item_id=<N>) per item to verify registered entries"
    )
    return {"migrated": migrated, "skipped": skipped, "failed": failed, "details": run_details, "verify": verify}


# ---------------------------------------------------------------------------
# artifact_migrate MCP tool
# ---------------------------------------------------------------------------


@mcp.tool(
    annotations=ToolAnnotations(
        title="Migrate Artifacts", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
    )
)
async def artifact_migrate(
    item_id: Annotated[
        str | int | None,
        Field(
            description="Migrate artifacts for a specific item only (integer for GitHub, beads nanoid string for beads backend). Omit to scan all items."
        ),
    ] = None,
    dry_run: Annotated[
        bool, Field(description="When true, report what would be migrated without making any API calls.")
    ] = False,
) -> dict:
    """Migrate existing plan/research artifacts into the artifact manifest system.

    Scans ``plan/`` and ``research/`` directories for artifact files,
    determines the artifact type from the filename pattern, extracts the
    linked GitHub issue number from YAML frontmatter (falling back to slug
    matching against backlog items), and calls the artifact_register logic
    for each discovered file.

    When ``item_id`` is provided the tool also checks the existing
    manifest for that item: any already-registered entry that has
    ``content_stored=False`` is re-registered so the auto-upload path can
    run and upload the local file content.

    Safe to re-run — the registry upserts on ``(artifact_type, path)``
    so existing entries are updated in-place rather than duplicated.

    Returns:
        Dict with ``migrated`` (int), ``skipped`` (int), ``failed`` (int),
        and ``details`` (list of per-artifact outcome dicts).  Each detail
        dict contains ``path``, ``type``, ``issue``, and ``outcome``.
        On error, dict contains an ``error`` key.
    """
    out = Output()

    # artifact_migrate scans plan/research directories by GitHub issue number.
    # Beads string IDs are not supported by the migration scanner — reject early
    # so the caller gets a clear message rather than a type error downstream.
    if isinstance(item_id, str):
        return {
            "error": (
                f"artifact_migrate requires an integer item ID, got {item_id!r}. "
                "Beads string ID filtering is not supported by the migration scanner."
            ),
            **out.to_dict(),
        }

    if dry_run:
        try:
            result = await asyncio.to_thread(_migrate_dry_run, item_id)
        except OSError as exc:
            return {"error": f"Discovery failed: {exc}", **out.to_dict()}
        return {**result, **out.to_dict()}

    try:
        result = await asyncio.to_thread(_migrate_live_run, item_id, out)
    except GitHubUnavailableError as exc:
        return {"error": str(exc), **out.to_dict()}
    except (BacklogError, _GithubException, OSError) as exc:
        return {"error": f"Migration failed: {exc}", **out.to_dict()}

    return {**result, **out.to_dict()}


# ---------------------------------------------------------------------------
# Dispatch execution tools — state management + process spawning
# ---------------------------------------------------------------------------

#: Lazily created singleton DispatchStateManager.
# TODO(H05): Move to FastMCP lifespan context — eliminate module-level singleton.
_dispatch_state_mgr: _DispatchStateManager | None = None

#: Path to the spawn.py script resolved once at module level.
_SPAWN_SCRIPT: Path = Path(__file__).parent.parent / "skills" / "kage-bunshin" / "scripts" / "spawn.py"


def _project_stub() -> str:
    """Derive a stable project slug from the repository root path.

    Converts the absolute path of the project root (e.g.
    ``/home/user/repos/my_project``) to a hyphen-separated slug by replacing
    all ``/`` separators with ``-`` and stripping the leading ``-``.

    Returns:
        Slug string, e.g. ``home-user-repos-my_project``.
    """
    project_root = _models.get_repo_root()
    return str(project_root).lstrip("/").replace("/", "-")


def _dispatch_state_manager() -> _DispatchStateManager:
    """Return the lazily created DispatchStateManager singleton.

    Creates the state database under ``~/.dh/projects/{project-stub}/`` on
    first call. The parent directory is created if necessary.

    Returns:
        Shared ``DispatchStateManager`` instance for this server process.
    """
    global _dispatch_state_mgr  # noqa: PLW0603
    if _dispatch_state_mgr is None:
        db_path = Path.home() / ".dh" / "projects" / _project_stub() / "dispatch-state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _dispatch_state_mgr = _DispatchStateManager(db_path)
    return _dispatch_state_mgr


@mcp.tool(
    annotations=ToolAnnotations(
        title="Start Dispatch Wave",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )
)
async def dispatch_wave_start(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[int, Field(description="Wave number from dispatch plan (1-based)")],
    items: Annotated[
        list[dict[str, object]], Field(description="List of items, each with 'issue' (int) and 'title' (str) keys")
    ],
) -> dict:
    """Record the start of a dispatch wave.

    Creates wave and item entries in the state database. Items are
    initialised with status ``pending``. Call this before spawning
    processes for a wave.

    Returns:
        Dict with ``milestone``, ``wave_num``, ``items_count``, ``status``,
        and ``messages``/``warnings``. Returns ``error`` if the wave already
        exists or if an item entry is malformed.
    """
    item_records = [
        _DispatchItemRecord(
            milestone=milestone, wave_num=wave_num, issue=int(str(item["issue"])), title=str(item.get("title", ""))
        )
        for item in items
    ]
    try:
        wave: _DispatchWaveRecord = await asyncio.to_thread(
            _dispatch_state_manager().create_wave, milestone, wave_num, item_records
        )
    except sqlite3.IntegrityError:
        return {
            "error": f"Wave {wave_num} already exists for milestone {milestone}",
            "milestone": milestone,
            "wave_num": wave_num,
        }
    return {
        "milestone": wave.milestone,
        "wave_num": wave.wave_num,
        "items_count": len(wave.items),
        "status": wave.status,
        "messages": [f"Wave {wave_num} created with {len(wave.items)} items"],
        "warnings": [],
        "errors": [],
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update Dispatch Item Status",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def dispatch_item_status(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    issue: Annotated[int, Field(description="Issue number of the item")],
    status: Annotated[str, Field(description="New status: 'complete', 'failed', or 'skipped'")],
    result: Annotated[str, Field(description="Result summary or JSON from result file")] = "",
    error: Annotated[str, Field(description="Error details on failure")] = "",
    cost: Annotated[float | None, Field(description="USD cost if available from claude output")] = None,
) -> dict:
    """Record completion or failure of a dispatch item.

    Looks up the item by milestone + issue across all waves. Updates
    status, result/error data, and completion timestamp.

    Returns:
        Dict with ``milestone``, ``issue``, ``wave_num``, ``status``,
        ``messages``/``warnings``. Returns ``error`` key if item not found.
    """
    mgr = _dispatch_state_manager()

    def _find_and_update() -> dict:
        waves = mgr.get_all_waves(milestone)
        for wave in waves:
            for item in wave.items:
                if item.issue == issue:
                    match status:
                        case "complete":
                            mgr.set_item_complete(
                                milestone=milestone, wave_num=wave.wave_num, issue=issue, result=result, cost=cost
                            )
                        case "failed":
                            mgr.set_item_failed(milestone=milestone, wave_num=wave.wave_num, issue=issue, error=error)
                        case "skipped":
                            # Treat skipped the same as failed with a standard message.
                            mgr.set_item_failed(
                                milestone=milestone, wave_num=wave.wave_num, issue=issue, error=error or "skipped"
                            )
                        case _:
                            return {
                                "error": f"Invalid status '{status}': must be 'complete', 'failed', or 'skipped'",
                                "milestone": milestone,
                                "issue": issue,
                            }
                    return {
                        "milestone": milestone,
                        "issue": issue,
                        "wave_num": wave.wave_num,
                        "status": status,
                        "messages": [f"Item #{issue} marked {status} in wave {wave.wave_num}"],
                        "warnings": [],
                        "errors": [],
                    }
        return {
            "error": f"Item #{issue} not found in any wave for milestone {milestone}",
            "milestone": milestone,
            "issue": issue,
        }

    return await asyncio.to_thread(_find_and_update)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Query Dispatch Wave Status",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def dispatch_wave_status(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[int, Field(description="Wave number to query (1-based)")],
) -> dict:
    """Query the current status of a dispatch wave.

    Returns item-level detail grouped by status, with elapsed time and
    progress counts. Checks PIDs for in-progress items and marks dead
    ones as failed before returning.

    Returns:
        Dict with :class:`~backlog_core.models.DispatchWaveSummary` fields,
        or ``error`` if wave not found.
    """
    mgr = _dispatch_state_manager()
    warnings: list[str] = []

    def _check_and_query() -> _DispatchWaveRecord | None:
        stale = mgr.check_stale_pids()
        warnings.extend(
            f"PID {stale_item.pid} for issue #{stale_item.issue} is dead — marked failed"
            for stale_item in stale
            if stale_item.milestone == milestone and stale_item.wave_num == wave_num
        )
        return mgr.get_wave(milestone, wave_num)

    wave = await asyncio.to_thread(_check_and_query)

    if wave is None:
        return {
            "error": f"Wave {wave_num} not found for milestone {milestone}",
            "milestone": milestone,
            "wave_num": wave_num,
        }

    items = wave.items
    status_counts = collections.Counter(i.status for i in items)

    elapsed: float | None = None
    if wave.started_at:
        with contextlib.suppress(ValueError):
            start = _datetime.fromisoformat(wave.started_at)
            end = _datetime.fromisoformat(wave.completed_at) if wave.completed_at else _datetime.now(UTC)
            elapsed = (end - start).total_seconds()

    # Usage accumulation is deferred to item completion time (dispatch_item_status)
    # and stored in wave/item records. Reading JSONL on every wave query is a
    # hot-path bloat issue; accumulated_usage is returned from stored dispatch state.
    accumulated_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "estimated_cost_usd": 0.0,
        "events_with_usage": 0,
    }

    summary = _DispatchWaveSummary(
        milestone=milestone,
        wave_num=wave_num,
        status=wave.status,
        total_items=len(items),
        pending=status_counts.get("pending", 0),
        in_progress=status_counts.get("in-progress", 0),
        complete=status_counts.get("complete", 0),
        failed=status_counts.get("failed", 0),
        skipped=status_counts.get("skipped", 0),
        started_at=wave.started_at,
        completed_at=wave.completed_at,
        elapsed_seconds=elapsed,
        items=items,
    )
    return {
        **summary.model_dump(),
        "messages": [],
        "warnings": warnings,
        "errors": [],
        "accumulated_usage": accumulated_usage,
    }


@dataclasses.dataclass
class _WaveCounters:
    """Mutable counters shared across concurrent item coroutines in one wave.

    Using a dataclass avoids ``nonlocal`` declarations in nested async
    functions, which are not thread/coroutine-safe without extra locking and
    cause PLR0914 (too many local variables) in the outer function.
    """

    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_done: int = 0  # cumulative across all waves so far


def _build_spawn_cmd(
    milestone: int,
    issue_num: int,
    item_title: str,
    model: str,
    phase: str,
    integration_branch: str,
    effort: EffortLevel | None = None,
) -> list[str]:
    """Construct the spawn.py subprocess command for one dispatch item.

    Args:
        milestone: GitHub milestone number.
        issue_num: GitHub issue number for the item.
        item_title: Human-readable title used as the prompt suffix.
        model: Model identifier string passed to spawn.py.
        phase: ``'work'`` adds ``--worktree``; any other value omits it.
        integration_branch: If non-empty, appended as ``--branch <value>``.
        effort: Effort level passed to spawn.py as ``--effort``; ``None``
            omits the flag and lets the model default apply.

    Returns:
        List of strings suitable for ``asyncio.create_subprocess_exec``.
    """
    cmd: list[str] = ["uv", "run", str(_SPAWN_SCRIPT), "--model", model, "--name", f"dispatch-{milestone}-{issue_num}"]
    if effort is not None:
        cmd += ["--effort", effort]
    if phase == "work":
        cmd.append("--worktree")
    if integration_branch:
        cmd += ["--branch", integration_branch]
    cmd.append(f"Work on issue #{issue_num}: {item_title}")
    return cmd


async def _poll_until_done(
    mgr: _DispatchStateManager, milestone: int, wave_num: int, issue_num: int, pid: int, result_file: str
) -> tuple[bool, float | None]:
    """Poll until a spawned item completes or its PID dies.

    Args:
        mgr: State manager used to write terminal status.
        milestone: GitHub milestone number.
        wave_num: Wave number (1-based).
        issue_num: GitHub issue number for the item.
        pid: OS process ID of the spawned session (``-1`` when unknown).
        result_file: Filesystem path where spawn.py writes its result JSON.

    Returns:
        ``(succeeded, cost)`` — ``succeeded`` is ``True`` when the result
        file was found; ``cost`` is the USD amount extracted from the result
        JSON or ``None``.
    """
    rf_path = Path(result_file) if result_file else None

    while True:
        await asyncio.sleep(2)

        if rf_path is not None:
            result_ready = await asyncio.to_thread(lambda: rf_path.exists() and rf_path.stat().st_size > 0)
            if result_ready:
                try:
                    content = await asyncio.to_thread(lambda: rf_path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    content = ""
                item_cost: float | None = None
                try:
                    rj = _json.loads(content)
                    item_cost = float(rj.get("cost", 0)) or None
                except (ValueError, KeyError, TypeError):
                    pass
                await asyncio.to_thread(mgr.set_item_complete, milestone, wave_num, issue_num, content, item_cost)
                return True, item_cost

        pid_alive = True
        if pid > 0:
            try:
                _os.kill(pid, 0)
            except ProcessLookupError:
                pid_alive = False
            except PermissionError:
                pass

        if not pid_alive:
            error_msg = f"Process died unexpectedly (PID {pid})"
            await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
            return False, None


async def _run_spawn_item(
    mgr: _DispatchStateManager,
    semaphore: asyncio.Semaphore,
    counters: _WaveCounters,
    warnings: list[str],
    ctx: Context,
    milestone: int,
    wave_num: int,
    issue_num: int,
    item_title: str,
    total_items: int,
    model: str,
    phase: str,
    integration_branch: str,
    effort: EffortLevel | None = None,
) -> None:
    """Spawn one dispatch item, monitor it, and update shared counters.

    Args:
        mgr: Dispatch state manager.
        semaphore: Concurrency throttle — held for the item's full lifetime.
        counters: Shared mutable counters updated on completion.
        warnings: List to append failure messages to.
        ctx: FastMCP context for progress and log reporting.
        milestone: GitHub milestone number.
        wave_num: Wave number (1-based).
        issue_num: GitHub issue number.
        item_title: Human-readable title for the prompt.
        total_items: Total items across all waves (for progress reporting).
        model: Model identifier string.
        phase: ``'work'`` or ``'groom'``.
        integration_branch: Branch name for ``--branch`` flag; empty to omit.
        effort: Effort level forwarded to spawn.py as ``--effort``; ``None``
            uses the model default.
    """
    async with semaphore:
        cmd = _build_spawn_cmd(milestone, issue_num, item_title, model, phase, integration_branch, effort=effort)
        pid = -1
        result_file = ""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, _ = await proc.communicate()
            stdout_text = stdout_bytes.decode(errors="replace").strip()

            try:
                spawn_data = _json.loads(stdout_text)
                pid = int(spawn_data.get("pid", -1))
                result_file = str(spawn_data.get("result_file", ""))
                session_id = spawn_data.get("session_id")
            except (ValueError, KeyError):
                error_msg = f"spawn.py non-JSON output: {stdout_text}"
                await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
                counters.failed += 1
                counters.total_done += 1
                warnings.append(f"Item #{issue_num} failed: {error_msg}")
                await ctx.report_progress(counters.total_done, total_items)
                return

            if pid > 0:
                await asyncio.to_thread(mgr.set_item_in_progress, milestone, wave_num, issue_num, pid)

            if session_id:
                await asyncio.to_thread(mgr.set_item_session_id, milestone, wave_num, issue_num, session_id)

            succeeded, _ = await _poll_until_done(mgr, milestone, wave_num, issue_num, pid, result_file)
            if succeeded:
                counters.completed += 1
            else:
                counters.failed += 1
                warnings.append(f"Item #{issue_num} failed: process exited with no result")

        except (OSError, sqlite3.Error) as exc:
            error_msg = f"Spawn error: {exc}"
            await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
            counters.failed += 1
            warnings.append(f"Item #{issue_num} failed: {error_msg}")

        counters.total_done += 1
        await ctx.report_progress(counters.total_done, total_items)
        await ctx.info(
            f"Wave {wave_num}: {counters.total_done}/{total_items} items — "
            f"{counters.completed} done, {counters.failed} failed"
        )


@mcp.tool(
    task=True,
    annotations=ToolAnnotations(
        title="Spawn Dispatch Wave",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def dispatch_spawn(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[
        int, Field(description="Starting wave number (1-based). Runs this wave and all subsequent waves")
    ],
    ctx: Context,
    max_concurrent: Annotated[int, Field(description="Maximum concurrent spawned sessions")] = 3,
    model: Annotated[str, Field(description="Model identifier for spawned sessions")] = "sonnet",
    phase: Annotated[
        str, Field(description="Dispatch phase: 'groom' (no worktree) or 'work' (with worktree)")
    ] = "work",
    effort: Annotated[
        EffortLevel | None,
        Field(
            description=(
                "Effort level for spawned sessions (sets CLAUDE_CODE_EFFORT_LEVEL). "
                "Choices: low, medium, high, max. None (default) uses model default."
            )
        ),
    ] = None,
) -> dict:
    """Spawn and monitor kage-bunshin sessions for a dispatch wave.

    Runs as a background task (``task=True``). Returns a task ID immediately.
    The background task:

    1. Detects and marks stale PIDs from prior runs.
    2. Reads the dispatch plan to get wave items.
    3. Iterates waves from ``wave_num`` through the last wave in the plan.
    4. For each wave: spawns items throttled to ``max_concurrent``, monitors
       PIDs, reads result files, and reports progress via
       ``ctx.report_progress()``.
    5. On item failure: marks failed, continues with remaining items.
    6. Returns a :class:`~backlog_core.models.DispatchSpawnSummary` when all
       waves complete.

    Args:
        milestone: GitHub milestone number.
        wave_num: Starting wave number (1-based); all subsequent waves run too.
        ctx: FastMCP context (injected automatically).
        max_concurrent: Maximum number of sessions running in parallel.
        model: Model identifier forwarded to each spawned session.
        phase: ``'work'`` adds ``--worktree``; ``'groom'`` omits it.
        effort: Effort level forwarded to spawn.py as ``--effort``. Accepts
            ``low``, ``medium``, ``high``, or ``max``. ``None`` (default)
            omits the flag and lets the model default apply.

    Returns:
        Dict with :class:`~backlog_core.models.DispatchSpawnSummary` fields
        on completion, or ``error`` on failure.
    """
    try:
        plan = await asyncio.to_thread(_ds.read_dispatch_plan, _dispatch_plan_path(milestone))
    except FileNotFoundError:
        return {"error": f"Dispatch plan not found for milestone {milestone}", "milestone": milestone}
    except ValueError as exc:
        return {"error": f"Invalid dispatch plan: {exc}", "milestone": milestone}

    mgr = _dispatch_state_manager()
    await asyncio.to_thread(mgr.check_stale_pids)

    start_time = _time.monotonic()
    integration_branch: str = plan.milestone.integration_branch
    all_waves = [w for w in plan.waves if w.wave >= wave_num]
    total_items = sum(len(w.items) for w in all_waves)
    per_wave_summaries: list[_DispatchWaveSummary] = []
    warnings: list[str] = []
    semaphore = asyncio.Semaphore(max_concurrent)
    overall = _WaveCounters()

    for wave in all_waves:
        with contextlib.suppress(sqlite3.IntegrityError):
            await asyncio.to_thread(
                mgr.create_wave,
                milestone,
                wave.wave,
                [
                    _DispatchItemRecord(milestone=milestone, wave_num=wave.wave, issue=i.issue, title=i.title)
                    for i in wave.items
                ],
            )

        wave_counters = _WaveCounters(total_done=overall.total_done)
        await asyncio.gather(*[
            _run_spawn_item(
                mgr=mgr,
                semaphore=semaphore,
                counters=wave_counters,
                warnings=warnings,
                ctx=ctx,
                milestone=milestone,
                wave_num=wave.wave,
                issue_num=item.issue,
                item_title=item.title,
                total_items=total_items,
                model=model,
                phase=phase,
                integration_branch=integration_branch,
                effort=effort,
            )
            for item in wave.items
        ])

        overall.completed += wave_counters.completed
        overall.failed += wave_counters.failed
        overall.total_done = wave_counters.total_done

        fetched = await asyncio.to_thread(mgr.get_wave, milestone, wave.wave)
        per_wave_summaries.append(
            _DispatchWaveSummary(
                milestone=milestone,
                wave_num=wave.wave,
                status=fetched.status if fetched else "complete",
                total_items=len(wave.items),
                pending=0,
                in_progress=0,
                complete=wave_counters.completed,
                failed=wave_counters.failed,
                skipped=wave_counters.skipped,
            )
        )

    elapsed_seconds = _time.monotonic() - start_time

    def _sum_costs() -> float | None:
        all_w = mgr.get_all_waves(milestone)
        costs = [i.cost for w in all_w if w.wave_num >= wave_num for i in w.items if i.cost is not None]
        return sum(costs) if costs else None

    total_cost = await asyncio.to_thread(_sum_costs)
    summary = _DispatchSpawnSummary(
        milestone=milestone,
        waves_executed=len(all_waves),
        total_items=total_items,
        completed=overall.completed,
        failed=overall.failed,
        skipped=overall.skipped,
        elapsed_seconds=elapsed_seconds,
        per_wave=per_wave_summaries,
        total_cost=total_cost,
    )
    return {
        **summary.model_dump(),
        "messages": [f"Dispatch complete: {overall.completed}/{total_items} items succeeded"],
        "warnings": warnings,
        "errors": [],
    }


from agent_profile import mcp as _agent_profile_mcp

mcp.mount(_agent_profile_mcp, namespace="profile")

if __name__ == "__main__":
    mcp.run()
