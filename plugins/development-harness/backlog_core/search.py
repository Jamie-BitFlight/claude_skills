"""Full-text search engine for backlog item dicts.

Operates on the ``list[dict[str, str | bool]]`` shape produced by
``operations.py::_build_list_entry``. This module must never import
``fastmcp`` or ``mcp`` types — that is what makes it importable from
``operations.py``, which cannot depend on the FastMCP server module.
"""

from __future__ import annotations

import dataclasses
import itertools
import operator
import re as _re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# Fields searched by default when no field-specific prefix is given.
# ``body`` contains the full item content (description + all section entries)
# built by operations._build_item_body so that plain-text and regex searches
# cover the complete backlog item, not just the 4 metadata fields.
_SEARCH_FIELDS: tuple[str, ...] = ("title", "section", "topic", "type", "body")

# Minimum length for a valid /pattern/ regex term (e.g. "/x/" has length 3).
_REGEX_SLASH_MIN_LEN = 2


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


def tokenize_search(search: str) -> list[str]:
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


def apply_search_filter(items: list[dict[str, str | bool]], search: str) -> list[dict[str, str | bool]]:
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

    tokens = tokenize_search(search)
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


# ---------------------------------------------------------------------------
# Primitive 2: content-based duplicate detection
# ---------------------------------------------------------------------------

# Statuses that mark a candidate as no longer a live duplicate risk.
_DUPLICATE_EXCLUDED_STATUSES: frozenset[str] = frozenset({"done", "resolved", "closed", "skip"})

# Common words dropped from concept extraction — not indicative of topic.
# Includes "backlog"/"item" since every item in this tracker is a backlog item,
# so those words carry no discriminating power for duplicate detection here.
_CONCEPT_STOPWORDS: frozenset[str] = frozenset({
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "backlog",
    "be",
    "been",
    "both",
    "but",
    "by",
    "can",
    "during",
    "for",
    "from",
    "had",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "item",
    "its",
    "near",
    "no",
    "nor",
    "not",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "those",
    "to",
    "was",
    "were",
    "when",
    "where",
    "which",
    "while",
    "who",
    "will",
    "with",
    "without",
    "would",
    "you",
    "your",
})

# Concept tokens shorter than this are treated as noise, not a topic word.
_MIN_CONCEPT_TOKEN_LEN = 3

_WORD_RE = _re.compile(r"[a-zA-Z0-9]+")


class DuplicateCheckStatus(StrEnum):
    """Outcome of a duplicate check — distinguishes a verified negative from an unverifiable one."""

    DUPLICATE_FOUND = "duplicate_found"
    NO_DUPLICATE = "no_duplicate"
    COULD_NOT_VERIFY = "could_not_verify"


class ContentDuplicateMatch(BaseModel):
    """A single candidate duplicate surfaced by ``find_content_duplicates``."""

    model_config = ConfigDict(frozen=True)

    title: str
    item_ref: str
    matched_field: str
    snippet: str
    match_count: int


def _extract_concept_words(text: str) -> list[str]:
    """Return casefolded, deduplicated, stopword-filtered words from ``text``, in order."""
    words: list[str] = []
    seen: set[str] = set()
    for word in _WORD_RE.findall(text.casefold()):
        if len(word) < _MIN_CONCEPT_TOKEN_LEN or word in _CONCEPT_STOPWORDS or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def build_concept_query(title: str, description: str, *, max_concepts: int = 4) -> str:
    """Build an OR search query from the significant words in title and description.

    Mirrors the manual concept-extraction step already prescribed by
    ``skills/work-backlog-item/references/workflows/create/start.md`` Step 3:
    "extract 2 to 4 key concepts ... build {c1} OR {c2} OR {c3}".

    A share of the budget is reserved for description words that add
    information the title doesn't already contain, so a verbose title can
    never fill ``max_concepts`` before any *new* description content is
    considered. Words the title and description both use (generic,
    frequently-reused terms in a single-subsystem backlog) are not treated
    as that new information, since they carry no extra discriminating
    power over title-only matching. The remaining budget is filled from
    the title first (preserving prior behavior when description is short,
    empty, or repeats the title), then from any leftover description words.

    Args:
        title: New item title.
        description: New item description.
        max_concepts: Maximum number of concept terms to include.

    Returns:
        A ``term1 OR term2 ...`` query string, or ``""`` when no usable
        concept word remains after filtering.
    """
    title_words = _extract_concept_words(title)
    desc_words = _extract_concept_words(description)
    title_word_set = set(title_words)
    desc_only_words = [word for word in desc_words if word not in title_word_set]

    concepts: list[str] = []
    seen: set[str] = set()
    reserved = min(len(desc_only_words), max(1, max_concepts // 2)) if desc_only_words else 0
    candidates = itertools.chain(desc_only_words[:reserved], title_words, desc_only_words[reserved:], desc_words)
    for word in candidates:
        if word in seen:
            continue
        seen.add(word)
        concepts.append(word)
        if len(concepts) >= max_concepts:
            break
    return " OR ".join(concepts)


def _candidate_item_ref(candidate: dict[str, str | bool]) -> str:
    """Return the actionable reference for a candidate: issue number, else logical reference.

    ``file_path`` is the key ``_build_list_entry`` uses for ``item.reference``
    (a logical id like ``"p1-slug"`` or a beads nanoid, not a filesystem path).
    """
    issue_ref = str(candidate.get("issue", "") or "")
    return issue_ref or str(candidate.get("file_path", "") or "")


def _candidate_matched_field_and_snippet(candidate: dict[str, str | bool], concept_terms: list[str]) -> tuple[str, str]:
    """Return the first field a concept term matched in, plus a snippet around it."""
    for term in concept_terms:
        for field in _SEARCH_FIELDS:
            text = _item_field_text(candidate, field)
            idx = text.find(term)
            if idx >= 0:
                return field, _make_snippet(text, idx, idx + len(term))
    return "body", str(candidate.get("title", ""))


def find_content_duplicates(
    title: str, description: str, candidates: list[dict[str, str | bool]], *, max_results: int = 5
) -> list[ContentDuplicateMatch]:
    """Find existing backlog items whose content overlaps the given title/description.

    Replaces character-sequence title matching (``difflib.SequenceMatcher``)
    with token-overlap matching over the full item content (title, description,
    and all section bodies), per ADR-004.

    Args:
        title: New item title.
        description: New item description.
        candidates: Backlog item dicts in the ``_build_list_entry`` shape.
        max_results: Maximum number of matches to return.

    Returns:
        Up to ``max_results`` matches ordered by ``match_count`` descending.
        Empty when the concept query is empty or nothing matches.
    """
    query = build_concept_query(title, description)
    if not query:
        return []

    concept_terms = [term.casefold() for term in query.split(" OR ")]
    live_candidates = [
        c
        for c in candidates
        if str(c.get("title", "")) and str(c.get("status", "")).casefold() not in _DUPLICATE_EXCLUDED_STATUSES
    ]
    matched = apply_search_filter(live_candidates, query)
    if not matched:
        return []

    scored = [(sum(1 for term in concept_terms if term in _build_haystack(c)), c) for c in matched]
    scored.sort(key=operator.itemgetter(0), reverse=True)

    results: list[ContentDuplicateMatch] = []
    for match_count, candidate in scored[:max_results]:
        matched_field, snippet = _candidate_matched_field_and_snippet(candidate, concept_terms)
        results.append(
            ContentDuplicateMatch(
                title=str(candidate.get("title", "")),
                item_ref=_candidate_item_ref(candidate),
                matched_field=matched_field,
                snippet=snippet,
                match_count=match_count,
            )
        )
    return results
