"""FastMCP 3.x server exposing all backlog operations as MCP tools.

Exists to guarantee what raw file or API access cannot:
1. Correct, audit-preserving backlog state across whichever backend is
   configured, under concurrent writers — durable for every backend except
   the in-memory one, an intentionally non-durable test double.
2. A structured, resource-bounded interface for the calling agent — safety
   annotations, typed errors, token-budget-aware pagination — in place of
   CLI/stderr parsing or unbounded reads.
3. Crash-safe tracking of multi-agent dispatch, wave, and task execution state.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import contextlib
import dataclasses
import difflib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, TypeAlias, TypeGuard

import dh_paths
import dispatch_schema
import tiktoken
from dh_core import operations
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp_tasks import TasksExtension
from github import GithubException
from mcp.types import ToolAnnotations
from progressive_markdown.exceptions import OrdinalNotFoundError
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from ruamel.yaml import YAML

from . import models, sync_engine
from .artifact_manifest_store import artifact_content_reference, load_manifest as load_manifest_record, publish_artifact
from .artifact_registry import ArtifactRegistry
from .backend_protocol import get_config
from .backend_types import ContentProvider, SnapshotCheckpointProvider, SyncProvider
from .disclosure_handler import BacklogViewDisclosureHandler, DisclosureRequest, DisclosureRequestParser
from .disclosure_types import DisclosureMode, DisclosureParamError
from .dispatch_state import DispatchStateManager
from .models import (
    AmbiguousSelectorError,
    ArtifactContent,
    ArtifactEntry,
    ArtifactManifest,
    ArtifactStatus,
    ArtifactType,
    BackendAvailability,
    BackendStatus,
    BacklogError,
    BranchConflictError,
    CacheStateCorruptError,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentProviderError,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    DispatchItemRecord,
    DispatchWaveRecord,
    DispatchWaveSummary,
    DuplicateItemError,
    EntryNotFoundError,
    ItemNotFoundError,
    Output,
    ReferenceCollisionError,
    RegisterResult,
    StatusSource,
    UnsupportedBackendCapabilityError,
    UnsupportedCapabilityError,
    ValidationError,
    init as init_models,
)
from .parsing import parse_issue_number
from .search import (
    _DEFAULT_SNIPPET_CONTEXT,
    _META_FIELDS,
    _REGEX_SLASH_MIN_LEN,
    _SEARCH_FIELDS,
    _make_snippet,
    _parse_body_sections,
    tokenize_search,
)
from .sync_state import (
    RETRYABLE_TRANSIENT_EXCEPTIONS,
    SyncErrorKind,
    SyncState,
    SyncStatus,
    classify_github_failure,
    get_sync_state,
)
from .tool_responses import (
    AccumulatedUsage,
    ArtifactReadResponse,
    ArtifactRegisterResponse,
    ArtifactsListResponse,
    BacklogAddResponse,
    BacklogAssignItemToMilestoneResponse,
    BacklogCloseResponse,
    BacklogCommentIssueResponse,
    BacklogCreateMilestoneResponse,
    BacklogCreateProjectResponse,
    BacklogCreateSamTaskResponse,
    BacklogGetReadySamTasksResponse,
    BacklogGetSoonestMilestoneResponse,
    BacklogGroomResponse,
    BacklogLinkFollowupResponse,
    BacklogListCommentsResponse,
    BacklogListFollowupsResponse,
    BacklogListIssuesResponse,
    BacklogListLabelsResponse,
    BacklogListMergedPrsResponse,
    BacklogListMilestonesResponse,
    BacklogListProjectsResponse,
    BacklogListResponse,
    BacklogNormalizeResponse,
    BacklogPullResponse,
    BacklogReadCommentResponse,
    BacklogResolveResponse,
    BacklogStrikeEntryResponse,
    BacklogSyncResponse,
    BacklogUpdateResponse,
    BacklogUpdateSamTaskStatusResponse,
    BacklogViewResponse,
    DispatchConflictsResponse,
    DispatchCreatePlanResponse,
    DispatchItemStatusResponse,
    DispatchReadResponse,
    DispatchSpawnResponse,
    DispatchStaleCheckResponse,
    DispatchValidateResponse,
    DispatchWaveStartResponse,
    DispatchWaveStatusResponse,
    SamTaskLookupResult,
    SyncNowResponse,
    SyncStatusResponse,
)

_ALLOW_CACHED_DESCRIPTION = (
    "After a live provider read fails, permit a warned fallback to cached provider records. "
    "Live data is always attempted first."
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Mapping, Sequence

    from pydantic import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

EffortLevel: TypeAlias = Literal["low", "medium", "high", "max"]
ItemId: TypeAlias = int | str


class _WireSchema:
    """Use a response model's JSON schema without changing dict serialization."""

    def __init__(self, cls: type[BaseModel]) -> None:
        self.cls = cls

    def __get_pydantic_json_schema__(  # ruff: ignore[bad-dunder-method-name] - required Pydantic schema hook
        self, _core_schema: object, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Generate the advertised schema from the response model.

        Returns:
            The response model's JSON schema.
        """
        return handler(self.cls.__pydantic_core_schema__)


def _wire_schema(cls: type[BaseModel]) -> object:
    """Build response annotation metadata for a dumped model.

    Returns:
        Metadata that advertises ``cls`` while retaining dict serialization.
    """
    return _WireSchema(cls)


def _respond(
    cls: type[BaseModel], payload: Mapping[str, object], *, exclude_none: bool = True, exclude_unset: bool = False
) -> dict[str, object]:
    """Validate a tool payload and return its wire dict (#3369).

    Tool handlers using this helper declare dictionary return types because
    this function deliberately dumps the validated model. Claiming a response
    model return type while returning a dict makes FastMCP ask Pydantic to
    serialize a dict as that model, emitting ``PydanticSerializationUnexpectedValue``.

    ``exclude_none`` defaults to ``True`` -- the pattern nearly all ~70+
    standard call sites use -- so a tool that legitimately needs a
    load-bearing ``None`` to survive onto the wire (see ``sync_status``'s
    docstring for why that tool bypasses this helper entirely) must pass
    ``exclude_none=False`` explicitly, making the decision a visible,
    searchable keyword rather than a convention a future call site has to
    remember to deviate from.

    ``exclude_unset`` defaults to ``False``. ``backlog_view`` (#3368) is the
    one caller that needs it ``True``, paired with ``exclude_none=False``:
    each of its branches builds a small, precise payload dict against
    ``BacklogViewResponse``'s ~55 possible fields, and several legitimately
    set a key to ``None`` (e.g. ``plan_address`` when an item has no plan,
    ``issue_number`` when a selector has none) that must still appear on the
    wire -- the exact "load-bearing None" case ``exclude_none=True`` cannot
    represent. ``exclude_unset=True`` keeps exactly the keys each branch put
    in *payload* (None or not) and drops the ~45 fields that branch never
    mentioned, reproducing what the pre-#3368 code did by returning a plain
    dict with no model in between.

    Args:
        cls: The Pydantic response model class for this tool.
        payload: Raw fields to validate into ``cls``.
        exclude_none: Forwarded to ``model_dump()``. Defaults to ``True``.
        exclude_unset: Forwarded to ``model_dump()``. Defaults to ``False``.

    Returns:
        The validated model's dumped dictionary.
    """
    return cls.model_validate(payload).model_dump(exclude_none=exclude_none, exclude_unset=exclude_unset)


#: Failures that describe the call itself, not the trip to the backend: a selector that matched
#: nothing or matched several, a value that did not validate, a record that is already there, an
#: ordinal the item does not hold, a capability the backend does not implement. Repeating the
#: identical call repeats the identical outcome, so these are never retryable.
_NEVER_RETRYABLE: tuple[type[BaseException], ...] = (
    AmbiguousSelectorError,
    BranchConflictError,
    CacheStateCorruptError,
    ContentConflictError,
    DisclosureParamError,
    DuplicateItemError,
    EntryNotFoundError,
    ItemNotFoundError,
    OrdinalNotFoundError,
    ReferenceCollisionError,
    UnsupportedBackendCapabilityError,
    UnsupportedCapabilityError,
    ValidationError,
)

#: Concrete transport failures whose type alone proves a later attempt may succeed. The mixed
#: ``BackendUnavailableError`` and ``ContentUnavailableError`` bases are deliberately absent: exact
#: instances and subclasses can represent structural failures too, so their constructors or raise
#: sites must state a verdict on the exception instance when one is supported.
_TRANSPORT_FAILED: tuple[type[BaseException], ...] = RETRYABLE_TRANSIENT_EXCEPTIONS


def _retryable(exc: BaseException) -> bool | None:
    """Return whether the call that raised ``exc`` can succeed on a later attempt.

    Answers in four steps, emitting a verdict only where one is supported:

    1. A verdict the raise site or the exception class stated wins, on either error tree. The
       condition that raised it fixes the answer, and the author who knows that condition is the
       one who can say so.
    2. A class in ``_NEVER_RETRYABLE`` describes the call, so the answer is ``False``.
    3. A concrete class in ``_TRANSPORT_FAILED``, or a direct/cause-wrapped ``GithubException``,
       uses the canonical GitHub classifier. Known transient statuses report ``True``, known final
       statuses report ``False``, and an absent or unknown GitHub status reports nothing. Mixed
       availability bases with no such cause report nothing unless step 1 found an explicit
       instance verdict.
    4. Anything else reports nothing.

    ``classify_github_failure`` is the shared source for GitHub status and cause-chain semantics.
    The broader ``classify_sync_error`` is deliberately not the general answer here: it answers
    whether the sync engine should keep spending its retry budget, so its ``NON_RETRYABLE`` means
    "stop now", not "impossible", and its ``BacklogError`` default means "a fetch failed", which
    at this boundary is wrong for every call-shaped refusal raised as a bare ``BacklogError``.

    A bare ``BacklogError`` with no stated verdict therefore reports ``None`` rather than a guess.
    The caller must be able to tell "cannot succeed" from "not known", and ``exclude_none=True``
    drops the key rather than asserting a verdict this server does not have.

    Args:
        exc: The exception the tool's except arm caught.

    Returns:
        ``True`` when a later attempt may succeed, ``False`` when it cannot, ``None`` when no
        verdict is supported.
    """
    if isinstance(exc, BacklogError | ContentProviderError) and exc.retryable is not None:
        return exc.retryable
    if isinstance(exc, _NEVER_RETRYABLE):
        return False
    if isinstance(exc, _TRANSPORT_FAILED):
        return True
    github_failure = classify_github_failure(exc)
    if github_failure is SyncErrorKind.RETRYABLE:
        return True
    if github_failure is SyncErrorKind.NON_RETRYABLE:
        return False
    return None


# Module-level logger for done-callback exception reporting.
# Named _sync_task_log so tests can patch backlog_core.server._sync_task_log.
_sync_task_log = logging.getLogger(__name__)

# Token budget for auto-pagination in backlog_list: 4400 tokens (cl100k_base encoding).
_LIST_TOKEN_BUDGET = 4_400
# Token budget for auto-compacting backlog_view: 4000 tokens (cl100k_base encoding).
# When the full response exceeds this budget and the caller has not requested a
# specific section, backlog_view returns a compact section-directory form so the
# caller can request only the sections it needs.
_VIEW_TOKEN_BUDGET = 4_000
_GROOMED_SECTION_TYPE = "groomed"
_enc: tiktoken.Encoding = tiktoken.get_encoding("cl100k_base")


def _token_count(serialised: str) -> int:
    """Count cl100k_base tokens in an already-serialized JSON string.

    Args:
        serialised: A JSON string produced by json.dumps.

    Returns:
        Token count as an integer.
    """
    return len(_enc.encode(serialised))


def _view_payload_token_count(full_response: dict[str, object]) -> int:
    """Token-count the delivered ``backlog_view`` payload without double-counting.

    The full-content view can return the same text twice. Section content
    appears in ``full_response["body"]`` and again inside each
    ``full_response["sections"][name]["entries"][i]["content"]``; the item's
    description appears in ``full_response["description"]`` and again under the
    ``## Description`` heading ``operations.render_sections_as_body`` emits into
    ``body``. Counting the serialised payload verbatim would double each of
    those and could falsely trip the over-budget directory — which for a
    description of a few thousand characters (this repository's convention for a
    behavioural backlog item) means a plain ``backlog_view`` returning the
    compact section directory in place of the content the caller asked for.

    Both de-duplications are conditional on ``body`` being non-empty, so they
    subtract only a copy the caller demonstrably receives elsewhere. When
    ``body`` is empty — the structured-key drift path, where a structured
    ``sections`` match had no rendered body header to populate it — the
    per-entry ``content`` and the ``description`` are the only delivered copies
    and must be measured in full, or a genuinely over-budget response would slip
    through the gate. ``body`` itself is always measured in full, so a body that
    alone exceeds the budget still gates.

    The returned payload is never mutated — only this measurement copy.

    Args:
        full_response: The serialised ``ViewItemResult`` dict about to be returned.

    Returns:
        Token count of the de-duplicated measurement copy.
    """
    raw_body = full_response.get("body")
    body = raw_body if isinstance(raw_body, str) else ""
    if not body:
        # ``body`` is empty/cleared (e.g. the structured-key drift path): the
        # per-entry ``content`` under ``sections`` and the ``description`` are the
        # SOLE delivered copies, so both must be counted in full.  Measure verbatim.
        return _token_count(json.dumps(full_response))
    measured = dict(full_response)
    # ``body`` is non-empty and carries each duplicated field's text once.
    raw_description = full_response.get("description")
    description = raw_description.strip() if isinstance(raw_description, str) else ""
    if description and description in body:
        # Containment-checked rather than assumed: a view path that narrows ``body``
        # (a section filter, a page) can ship a ``body`` the description is NOT part
        # of, and there the ``description`` field is a sole copy to count in full.
        measured["description"] = ""
    raw_sections = full_response.get("sections")
    if isinstance(raw_sections, dict) and raw_sections:
        measured["sections"] = {name: _section_without_entry_content(sec) for name, sec in raw_sections.items()}
    return _token_count(json.dumps(measured))


def _section_without_entry_content(section: object) -> object:
    """Return a copy of *section* with each entry's ``content`` blanked.

    Used by :func:`_view_payload_token_count` so the over-budget gate does not
    count section content that the body already carries.  Non-entry-block section
    shapes (e.g. groomed ``{"type": "groomed", ...}``) are returned unchanged —
    they carry no duplicated body content to subtract.

    Args:
        section: A single ``sections`` dict value (entry-block or groomed shape).

    Returns:
        A shallow copy with blanked entry ``content`` for entry-block sections, or
        the original object for shapes without an ``entries`` list.
    """
    if not isinstance(section, dict):
        return section
    # ``isinstance`` narrows ``object`` to ``dict[Never, Never]`` under ty; rebuild a
    # concrete ``dict[str, object]`` so the ``entries`` access has a real value type.
    section_map: dict[str, object] = {str(k): v for k, v in section.items()}
    raw_entries = section_map.get("entries")
    if not isinstance(raw_entries, list):
        return section
    trimmed: dict[str, object] = dict(section_map)
    trimmed["entries"] = [{**entry, "content": ""} if isinstance(entry, dict) else entry for entry in raw_entries]
    return trimmed


# All fields that callers can request via the fields= parameter on backlog_list.
# Fields in _DEFAULT_ITEM_FIELDS are returned when no fields= parameter is given.
# ``body`` is omitted from the default set because it makes responses large.
_AVAILABLE_FIELDS: tuple[str, ...] = ("issue", "title", "section", "topic", "type", "status", "body")
_DEFAULT_ITEM_FIELDS: frozenset[str] = frozenset(_AVAILABLE_FIELDS) - {"body"}

# item_depth value that includes the full body in each returned item.
_ITEM_DEPTH_FULL = 3

# Beads-native issue and task operations use the configured backend's direct
# bd runner; DH MCP operations remain responsible for provider-neutral workflow
# state and artifacts.


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
        pattern = re.compile(pattern_str, re.IGNORECASE)
    except re.error:
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
    tokens = tokenize_search(search)
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
        items: Items already filtered by search (via ``operations.list_items``).
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
    return _token_count(json.dumps({"h": item.get("match_header"), "m": item.get("matches")}))


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


def _metadata_entry_name(entry: object) -> str:
    """Extract the ``name`` field from a serialised ``SectionMeta`` entry.

    Boundary accessor over a ``model_dump`` result: ``response["sections_metadata"]``
    is typed ``object`` after JSON-style serialisation, so each entry is validated
    here and its ``name`` returned as a ``str``.  Returns ``""`` for any entry that
    is not a dict or lacks a string ``name`` (such entries simply never match a
    requested name).

    Args:
        entry: A single ``sections_metadata`` list element of unknown shape.

    Returns:
        The entry's ``name`` as a string, or ``""`` when absent or non-string.
    """
    if not isinstance(entry, dict):
        return ""
    return next((value for key, value in entry.items() if key == "name" and isinstance(value, str)), "")


def _filter_view_sections(
    response: dict[str, object], sections: list[str], result: models.ViewItemResult
) -> dict[str, object]:
    """Filter the backlog_view response to only the requested sections.

    Identity fields (number, title, status, type, priority) are always included.
    The ``sections`` dict in the response is filtered to the named keys only,
    matched case-insensitively (case-folded, exact-name not substring) so a
    ``sections=['rt-ica']`` request keeps an ``RT-ICA`` structured key — consistent
    with the body and ``sections_metadata`` arms. All other top-level keys are
    preserved.

    In compact mode (``include_content=False``) the response carries no body and
    an empty ``sections`` dict; the inventory lives in ``sections_metadata``. The
    requested names are matched and filtered against that inventory too, so a
    valid name is not reported as a miss merely because the body and ``sections``
    dict are absent.

    The plural ``sections=[...]`` path also signals a no-match: when none of the
    requested names resolve to a structured section key, a compact
    ``sections_metadata`` entry, or a raw-body ``## ``/``### `` header,
    ``section_filter_miss`` is set to ``True`` on both the response dict and
    *result* so the caller can distinguish "the names were wrong" from "the item
    is too big" — mirroring how the singular ``section=`` path signals a miss.
    Setting it on *result* keeps the signal present when the payload is over
    budget and the response is rebuilt from *result* via
    :func:`_build_over_budget_view`. Per
    ``.claude/rules/silent-failure-prevention.md``, the branch on the requested
    names has an explicit no-match fallback rather than returning the body
    unchanged with no signal.

    When the structured ``sections`` dict matches but no body header does (case or
    format drift between YAML keys and rendered headers), the un-narrowed body is
    cleared so the matched narrowing fits the view budget instead of being
    replaced by the over-budget directory.

    Args:
        response: Full serialised ViewItemResult dict (mutated in place).
        sections: List of section name strings to include.
        result: The typed ViewItemResult backing *response*; its
            ``section_filter_miss`` flag is set on a no-match so the over-budget
            directory path also surfaces the signal.

    Returns:
        Filtered response dict (same object, mutated in place).
    """
    # Case-folded set of requested names — shared by the structured-dict, body, and
    # metadata arms so all three match section names case-insensitively (the plural
    # ``sections=[...]`` contract is exact-name, case-insensitive).
    requested_folded: frozenset[str] = frozenset(s.casefold() for s in sections)
    raw_sections = response.get("sections")
    dict_matched = False
    if isinstance(raw_sections, dict):
        # Case-insensitive membership: a ``sections=['rt-ica']`` request must keep an
        # ``RT-ICA`` structured key, consistent with ``narrow_body_to_named_sections``
        # (body arm) and the ``sections_metadata`` arm. A case-sensitive ``k in
        # requested`` test would silently drop the metadata while the body arm
        # matched, desyncing ``sections`` from ``body`` with no
        # ``section_filter_miss`` signal. Exact-name (not substring) semantics are
        # preserved.
        kept = {k: v for k, v in raw_sections.items() if isinstance(k, str) and k.casefold() in requested_folded}
        response["sections"] = kept
        dict_matched = bool(kept)
    # Compact view (include_content=False) carries no body and an empty ``sections``
    # dict; its inventory lives in ``sections_metadata`` instead.  Match and filter
    # that inventory by name so VALID section names are NOT reported as a miss in
    # compact mode (issue #2495 finding #4).  Names are compared case-insensitively
    # (case-folded) to mirror the body-header and structured-dict contract.
    raw_metadata = response.get("sections_metadata")
    metadata_matched = False
    if isinstance(raw_metadata, list):
        kept_meta = [entry for entry in raw_metadata if _metadata_entry_name(entry).casefold() in requested_folded]
        response["sections_metadata"] = kept_meta
        metadata_matched = bool(kept_meta)
    # Keep the raw body self-consistent with the section filter so a sections=[...]
    # request returns the requested slice rather than overflowing the view budget
    # on the un-narrowed body (issue #2495 defect a).
    raw_body = response.get("body")
    body_matched = False
    if isinstance(raw_body, str) and raw_body:
        narrowed, body_matched = operations.narrow_body_to_named_sections(raw_body, sections)
        if body_matched:
            response["body"] = narrowed
        elif dict_matched:
            # The structured ``sections`` dict matched the requested names but no
            # raw-body ``## ``/``### `` header did (case/format drift between the
            # YAML section keys and the rendered body headers).  Retaining the
            # un-narrowed full body would overflow the view budget and the
            # over-budget gate would replace the explicitly requested narrowing
            # with the section directory (issue #2495 finding #5).  The matched
            # content is already carried by ``response["sections"]``; clear the
            # body so the delivered payload stays consistent with the matched
            # sections and fits the budget.
            response["body"] = ""
        else:
            response["body"] = narrowed
    # No-match fallback (m1): when the caller requested names but none resolved to
    # a structured section, a compact-inventory entry, or a body header, surface
    # section_filter_miss so the caller learns the names were invalid even when an
    # over-budget directory is returned.  Set on both the response dict and
    # *result* so the over-budget rebuild via _build_over_budget_view carries the
    # signal too.
    if sections and not dict_matched and not metadata_matched and not body_matched:
        response["section_filter_miss"] = True
        result.section_filter_miss = True
        # Collect all known section names for the section-filter-miss error response.
        # ``raw_sections`` and ``raw_metadata`` still reference the original
        # (pre-filter) objects even though ``response["sections"]`` and
        # ``response["sections_metadata"]`` have been replaced above.
        valid_names: list[str] = []
        if isinstance(raw_sections, dict):
            valid_names.extend(k for k in raw_sections if isinstance(k, str))
        if isinstance(raw_metadata, list):
            for entry in raw_metadata:
                name = _metadata_entry_name(entry)
                if name and name not in valid_names:
                    valid_names.append(name)
        result.section_filter_valid_names = valid_names
    return response


def _build_section_miss_error(filter_expr: str, valid_names: list[str], out: Output) -> dict[str, object]:
    """Build an error dict for a section-filter miss.

    Returns a dict with ``error``, ``valid_sections``, and ``section_filter_miss``
    (back-compat flag) but NO ``body`` field, so callers can distinguish an error
    response from a content response by the absence of ``body``.  Adds a
    ``suggestion`` key only when difflib finds a close match in ``valid_names``
    (SequenceMatcher ratio >= 0.6, equivalent to Levenshtein-adjacent proximity).

    Adds an ``unresolved_sections`` key when *valid_names* contains a raw
    ``unknown__``-prefixed storage key — the signature left by content stored
    under a mis-keyed, unrecognized heading that
    :func:`~.section_registry.resolve_section_name` could not resolve at write
    time.  The ``unknown__`` prefix is checked literally (not via
    ``resolve_section_name`` here) because many legitimate, non-canonical
    headings exist in real item bodies (e.g. ``"Description"``) that are not
    registered in :mod:`.section_registry` yet were never mis-keyed — flagging
    every unregistered name would produce false positives on ordinary items.
    Both the singular ``section=`` path (``_apply_body_section_filter`` /
    ``_assemble_view_compact``) and the plural ``sections=[...]`` path
    (``_filter_view_sections``) populate *valid_names* from the item's actual
    section inventory, so this single check distinguishes "the requested name
    genuinely has no match, and nothing about this item is unresolved" (key
    absent) from "no match, but this item also has unresolved mis-keyed
    content the caller should investigate rather than assume absent" (key
    present, non-empty) — previously both cases produced an identical
    ``section_filter_miss: True`` with no way to tell them apart.

    Args:
        filter_expr: The section filter string the caller supplied.
        valid_names: Known section names at the time of the miss.
        out: Output accumulator carrying any messages/warnings/errors.

    Returns:
        Error dict ready to return from ``backlog_view``.
    """
    error_dict: dict[str, object] = {
        "error": f"Section not found: {filter_expr!r}",
        "valid_sections": valid_names,
        "section_filter_miss": True,
        # The item holds the sections it holds; asking for an absent one again asks the same
        # question of the same inventory.
        "retryable": False,
        **out.to_dict(),
    }
    unresolved_names = [name for name in valid_names if name.startswith("unknown__")]
    if unresolved_names:
        error_dict["unresolved_sections"] = unresolved_names
    if valid_names and filter_expr:
        matches = difflib.get_close_matches(filter_expr, valid_names, n=1, cutoff=0.6)
        if matches:
            error_dict["suggestion"] = f"Did you mean: {matches[0]!r}?"
    return error_dict


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
    init_models(_args.project_dir)


# ---------------------------------------------------------------------------
# Lifespan: launch singleton background sync once per server process.
# FastMCP 3.x already guards against concurrent lifespan re-entry via its
# internal _lifespan_lock, so we do not need an additional boolean guard here.
# The lifespan= parameter on FastMCP() must be an async context manager factory
# (decorated with @asynccontextmanager), NOT a plain async generator.
# ---------------------------------------------------------------------------


def _log_sync_task_exc(task: asyncio.Task[None]) -> None:
    """Done-callback: log any unexpected exception that escapes the sync task.

    An asyncio.CancelledError is expected during server shutdown and is
    silently ignored.  Any other exception indicates an unanticipated bug
    that escaped the broad catch in _attempt_sync; it is logged at
    ERROR level so it is visible in the server logs rather than silently
    discarded per .claude/rules/silent-failure-prevention.md.

    Args:
        task: The completed sync background task.
    """
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        _sync_task_log.error("Background sync task raised an unexpected exception: %s", exc, exc_info=exc)


# Strong references to in-flight background sync tasks.  The event loop keeps only
# weak references to tasks, so a fire-and-forget task held solely by a local
# variable can be garbage-collected mid-run.  Holding the task here until it
# completes prevents that.  See CPython asyncio.create_task docs.
_bg_sync_tasks: set[asyncio.Task[None]] = set()

# Module-level reference to the active startup sync task.  Set by _backlog_lifespan
# on first entry; prevents FastMCP re-entry (issue #1115) from launching a second task.
_active_startup_sync_task: asyncio.Task[None] | None = None


def _register_bg_task(task: asyncio.Task[None]) -> None:
    """Retain a strong reference to *task* and wire its done-callbacks.

    Args:
        task: The background sync task to track until completion.
    """
    _bg_sync_tasks.add(task)
    task.add_done_callback(_bg_sync_tasks.discard)
    task.add_done_callback(_log_sync_task_exc)


def _launch_background_sync(*, full_refresh: bool = False) -> asyncio.Task[None] | None:
    """Atomically launch the singleton maintenance worker."""
    state = get_sync_state()
    if not isinstance(get_config().backend, SyncProvider) or not state.try_start():
        return None
    sync = (
        sync_engine._startup_sync_loop(state, full_refresh=True)
        if full_refresh
        else sync_engine._startup_sync_loop(state)
    )
    task = asyncio.create_task(sync)
    _register_bg_task(task)
    return task


def _schedule_maintenance_if_checkpoint_absent() -> bool:
    """Schedule non-blocking MCP maintenance only for a cold remote cache."""
    backend = get_config().backend
    if (
        not _startup_sync_enabled()
        or not isinstance(backend, SnapshotCheckpointProvider)
        or backend.has_synced_snapshot()
    ):
        return False
    return _launch_background_sync() is not None


def _read_enabled_from_config_file(yaml_parser: object, config_path: object) -> bool | None:
    """Read ``backlog.startup_sync.enabled`` from one config file.

    Isolates the try/except so the outer loop in
    ``_read_startup_sync_enabled_from_yaml`` uses a plain
    ``if result is not None`` check, avoiding the S112 try-except-continue
    pattern.

    Args:
        yaml_parser: A ``ruamel.yaml.YAML`` instance.
        config_path: Path to the YAML config file to read.

    Returns:
        The configured bool if present, otherwise ``None``.
    """
    if not isinstance(yaml_parser, YAML) or not isinstance(config_path, Path) or not config_path.is_file():
        return None
    try:
        raw = yaml_parser.load(config_path.read_text(encoding="utf-8"))
    except Exception:  # ruff: ignore[blind-except] — ruamel.yaml raises various internal exception types
        return None
    if not isinstance(raw, dict):
        return None
    backlog_section = raw.get("backlog")
    if not isinstance(backlog_section, dict):
        return None
    startup_sync = backlog_section.get("startup_sync")
    if not isinstance(startup_sync, dict):
        return None
    enabled = startup_sync.get("enabled")
    return enabled if isinstance(enabled, bool) else None


def _read_startup_sync_enabled_from_yaml() -> bool | None:
    """Read ``backlog.startup_sync.enabled`` from .dh/config.yaml files.

    Returns the configured boolean value or ``None`` when the key is absent
    in all config files.  Implemented without private dh_config imports to
    avoid PLC2701 violations.

    Returns:
        The configured bool, or ``None`` when the key is absent.
    """
    search_paths = []
    with contextlib.suppress(FileNotFoundError, RuntimeError):
        project_root = dh_paths.git_project_root()
        search_paths.append(dh_paths.project_dh_dir(project_root) / "config.yaml")
    search_paths.append(dh_paths._dh_user_root() / "config.yaml")

    yaml = YAML(typ="safe")

    for config_path in search_paths:
        result = _read_enabled_from_config_file(yaml, config_path)
        if result is not None:
            return result
    return None


def _startup_sync_enabled() -> bool:
    """Return True when the startup sync should run (default: True).

    Reads ``backlog.startup_sync.enabled`` from ``.dh/config.yaml``.
    Returns ``True`` when the key is absent (opt-out semantics: sync runs
    unless explicitly disabled).

    Named module-level function so tests can patch via:
    ``mocker.patch("backlog_core.server._startup_sync_enabled", return_value=False)``.

    Returns:
        True if startup sync should proceed, False to skip it entirely.
    """
    configured = _read_startup_sync_enabled_from_yaml()
    return True if configured is None else configured


@contextlib.asynccontextmanager
async def _backlog_lifespan(_server: object) -> AsyncGenerator[dict[str, object], None]:
    """FastMCP lifespan: launch the background sync task before serving tools.

    The background sync task starts immediately but does not block server
    readiness — ``yield`` executes before the sync completes so tool calls
    can be answered concurrently.

    Args:
        _server: The FastMCP server instance (not used directly).

    Yields:
        Empty lifespan context dict.
    """
    # Guard 1 — kill-switch: skip entirely when disabled in config.
    # Guard 2 — re-entry (FastMCP #1115): try_start() is an atomic check-and-set;
    #   if RUNNING is already set (second lifespan entry) we skip create_task so
    #   only one background sync task runs per process lifetime.
    global _active_startup_sync_task  # ruff: ignore[global-statement]
    if _startup_sync_enabled():
        bg_task = _launch_background_sync()
        if bg_task is not None:
            # Store module-level reference so a re-entrant lifespan (FastMCP #1115)
            # cancels the same task on teardown rather than creating a dangling one.
            _active_startup_sync_task = bg_task
        else:
            bg_task = _active_startup_sync_task
    else:
        bg_task = _active_startup_sync_task
    try:
        yield {}
    finally:
        if bg_task is not None:
            bg_task.cancel()
            # Suppress the expected teardown outcomes only: CancelledError (from the
            # cancel above), TimeoutError (from wait_for), and any application-level
            # error from the task — the done-callback (_log_sync_task_exc) already
            # logged it; re-raising here would surface a clean shutdown as a crash.
            # KeyboardInterrupt / SystemExit (BaseException) still propagate.
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await asyncio.wait_for(bg_task, timeout=5.0)


mcp = FastMCP(
    "backlog",
    instructions=(
        "Backlog management server. The configured backend is the source of truth; backends that "
        "support offline queuing keep a local cache that syncs with it, others read and write it "
        "directly. Always use these tools for backlog CRUD (add, list, view, update, groom, close, "
        "resolve, sync). Reach the backlog only through these tools; on a failed call, report "
        "the failure and stop."
    ),
    version="0.1.0",
    lifespan=_backlog_lifespan,
)

# fastmcp 4 requires a server exposing task-enabled tools (dispatch_spawn) to register
# the tasks extension explicitly; fastmcp 3 registered it implicitly.
mcp.add_extension(TasksExtension())


@mcp.tool(
    annotations=ToolAnnotations(
        title="Backlog Sync Status",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def sync_status() -> SyncStatusResponse:
    """Return the current background sync state."""
    # No exclude_none here (unlike every other tool in this module): every
    # field is unconditionally present in SyncState.to_dict() -- some
    # legitimately null (e.g. started_at before any sync has run) -- and
    # there is no BacklogError arm ever needing to hide a field, so the
    # rationale for exclude_none=True (rule 5's "not unconditionally
    # present on every path" widening) doesn't apply. Dropping null keys
    # here would be a wire-format regression against the pre-existing
    # contract that every key is always present.
    #
    # Returning the model instance (not .model_dump()) keeps the declared
    # SyncStatusResponse return type accurate for in-process callers; FastMCP
    # serializes it identically at the wire boundary since no exclude_none is
    # applied here either way.
    return SyncStatusResponse.model_validate(get_sync_state().to_dict())


@mcp.tool(
    annotations=ToolAnnotations(
        title="Trigger Backlog Sync",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def sync_now(
    full_refresh: Annotated[
        bool, Field(description="Ignore the provider checkpoint and perform a full reconciliation")
    ] = False,
) -> SyncNowResponse:
    """Trigger an immediate background sync or return progress of an in-flight sync.

    If a sync is already in progress, returns the current progress without
    starting a new sync (singleton guarantee).

    If the last sync entered OFFLINE (a non-retryable failure — missing/invalid
    GITHUB_TOKEN, or a filesystem/config error) or ERROR (a retryable failure —
    network blocked, rate limited, or a GitHub server error — that exhausted
    all retries), clears the state and attempts a fresh sync.
    """
    state = get_sync_state()
    if not isinstance(get_config().backend, SyncProvider):
        return SyncNowResponse.model_validate({
            "triggered": False,
            "sync_state": state.to_dict(),
            "messages": ["Active backend does not support reconciliation."],
        })

    # Reset terminal states so the new attempt starts fresh.  Done before the
    # claim so the returned snapshot reflects the fresh RUNNING state, not the
    # stale OFFLINE/ERROR one.
    if state.status in {SyncStatus.OFFLINE, SyncStatus.ERROR}:
        state.offline_reason = ""
        state.last_error = ""
        state.retry_count = 0

    # The launcher atomically claims the sync slot before creating the worker.
    if _launch_background_sync(full_refresh=full_refresh) is None:
        return SyncNowResponse.model_validate({
            "triggered": False,
            "sync_state": state.to_dict(),
            "messages": ["A sync is already in progress. Returning current progress."],
        })

    return SyncNowResponse.model_validate({
        "triggered": True,
        "sync_state": state.to_dict(),
        "messages": ["Background sync triggered."],
    })


@mcp.tool(
    annotations=ToolAnnotations(
        title="Add Backlog Item",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def backlog_add(
    title: Annotated[
        str,
        Field(
            description=(
                "Item title, unprefixed — do not add 'fix:'/'docs:'/'chore:' yourself. "
                "The GitHub backend derives a type prefix from `type` and prepends it "
                "automatically when the GitHub issue is created, so existing GitHub-backed "
                "titles show one; the Beads, SQLite, and in-memory backends create the issue "
                "with the title exactly as given, with no prefix added."
            )
        ),
    ],
    priority: Annotated[str, Field(description="Priority level: P0, P1, P2, or Ideas")],
    description: Annotated[
        str,
        Field(
            description=(
                "Item description. A good submission covers: the goal, reproduction steps (for a "
                "defect), impact, a user story, the payoff, and any existing observations that add "
                "context. Leave out prescriptive solutions or fixes — that design work happens with "
                "rigor during the grooming phase. If a candidate fix is already known, note it under "
                "a 'User-provided context:' line instead of stating it as the requirement."
            )
        ),
    ],
    source: Annotated[str, Field(description="Where this item came from")] = "Not specified",
    type_: Annotated[
        str, Field(description="Item type: Feature, Bug, Refactor, Docs, or Chore", alias="type")
    ] = "Feature",
    force: Annotated[bool, Field(description="Skip content-based duplicate check")] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogAddResponse)]:
    """Add a new item through the configured backend and optionally create its native issue.

    For guided creation with classification and research support, use
    /dh:work-backlog-item create instead of calling this tool directly — it applies
    the same description template below plus item-type classification. Duplicate
    detection here runs unless force=True.

    ``file_path`` is for reference only. Change the item with ``backlog_update`` or
    ``backlog_groom``.

    The item can be stored while ``errors`` is non-empty and ``item_ref`` is empty: the
    item saved, but no issue was created for it.
    """
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
            allow_cached=allow_cached,
            output=out,
        )
        return _respond(BacklogAddResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogAddResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


def _assert_config() -> None:
    """Raise :exc:`BacklogError` when BacklogConfig has not been initialised.

    Converts the :exc:`RuntimeError` from :func:`models.get_config` into a
    :exc:`BacklogError` so tool handlers that already catch ``BacklogError``
    return structured JSON instead of crashing.

    Raises:
        BacklogError: When no project root is discoverable and no env vars are set.
    """
    try:
        models.get_config()
    except RuntimeError as exc:
        # No project root and no env vars: the next identical call discovers the same nothing.
        raise BacklogError(str(exc), retryable=False) from exc


def _probe_backend_status() -> BackendStatus:
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
        return get_config().backend.probe_backend_status()
    except (RuntimeError, ValueError):
        return BackendStatus(availability=BackendAvailability.NOT_CHECKED)


def _format_backend_status_message(status: BackendStatus) -> str:
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
    availability_label = status.availability.value
    if (
        status.availability == BackendAvailability.REACHABLE
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


def _is_str_bool_dict(v: object) -> TypeGuard[dict[str, str | bool]]:
    return isinstance(v, dict) and all(isinstance(k, str) and isinstance(val, (str, bool)) for k, val in v.items())


def _extract_item_list(result: Mapping[str, object]) -> list[dict[str, str | bool]]:
    """Extract the typed item list from a raw operations.list_items result dict.

    ``operations.list_items`` returns ``{"items": [...], ...}`` where each
    element may be a heterogeneous value.  This function narrows the list to
    dicts only, matching the ``list[dict[str, str | bool]]`` type expected by
    downstream filter and search helpers.

    Using ``Mapping[str, object]`` for the parameter (rather than the
    invariant ``dict[str, object]``) allows callers with more narrowly typed
    dicts to pass their values without a variance error.

    Args:
        result: The raw mapping returned by ``operations.list_items``.

    Returns:
        List of item dicts; empty when the ``items`` key is absent or its
        value is not a list.
    """
    raw = result.get("items", [])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if _is_str_bool_dict(item)]


def _build_sync_state_block(sync_state: SyncState) -> tuple[dict[str, object] | None, list[str]]:
    """Build the sync_state payload block and warning strings when the sync is not IDLE.

    Returns ``(None, [])`` when the sync status is IDLE so callers can skip
    the injection without an extra branch.  The status-aware text is preserved
    exactly as it was inline: RUNNING maps to a non-failure message; any other
    non-IDLE status is treated as a stale-cache failure.

    Args:
        sync_state: The current SyncState object from ``get_sync_state()``.

    Returns:
        A tuple of (sync_state_block, sync_warnings).  ``sync_state_block`` is
        ``None`` when ``sync_state.status`` is IDLE; otherwise it is a dict
        ready to include in a tool response.  ``sync_warnings`` is a list of
        human-readable warning strings (empty when IDLE).
    """
    if sync_state.status == SyncStatus.IDLE:
        return None, []

    last_success_str: str | None = (
        sync_state.last_success_at.isoformat() if sync_state.last_success_at is not None else None
    )
    if sync_state.status == SyncStatus.RUNNING:
        cache_warning = "backend sync in progress — cache may be incomplete"
        warning_lead = "Backend sync in progress; cache may be incomplete"
    else:
        cache_warning = "serving stale cache — backend sync failed"
        warning_lead = f"Serving stale cache: backend sync {sync_state.status}"

    failure_reason = sync_state.offline_reason or sync_state.last_error
    block: dict[str, object] = {
        "status": str(sync_state.status),
        "offline_reason": sync_state.offline_reason,
        "last_success_at": last_success_str,
        "cache_warning": cache_warning,
    }
    warning = (
        warning_lead
        + (f" ({failure_reason})" if failure_reason else "")
        + ("." if not sync_state.last_success_at else f". Last successful sync: {last_success_str}.")
    )
    return block, [warning]


def _apply_sync_state_to_response(
    response: dict[str, object], sync_state_block: dict[str, object] | None, sync_warnings: list[str]
) -> None:
    """Merge sync_state block and warnings into a tool response dict in-place.

    No-ops when ``sync_state_block`` is ``None`` (IDLE sync status).
    When warnings are present they are appended to any existing ``"warnings"``
    list in ``response``; when the existing value is not a list the sync
    warnings replace it.

    Args:
        response: The in-progress response dict to update.
        sync_state_block: Dict returned by ``_build_sync_state_block``, or
            ``None`` when the sync is IDLE.
        sync_warnings: Warning strings returned by ``_build_sync_state_block``.
    """
    if sync_state_block is None:
        return
    response["sync_state"] = sync_state_block
    existing = response.get("warnings", [])
    response["warnings"] = (list(existing) + sync_warnings) if isinstance(existing, list) else sync_warnings


def _build_count_only_response(
    total: int,
    result: Mapping[str, object],
    output: Output,
    sync_state_block: dict[str, object] | None,
    sync_warnings: list[str],
) -> dict[str, object]:
    """Build the minimal count response while preserving degradation signals.

    Returns:
        Serialized count-only response.
    """
    response: dict[str, object] = {
        "count": total,
        "from_cache": result.get("from_cache"),
        "has_pending_writes": result.get("has_pending_writes"),
    }
    if output.warnings:
        response["warnings"] = list(output.warnings)
    if output.errors:
        response["errors"] = list(output.errors)
    if result.get("status_source") == "unavailable":
        response["status_source"] = result["status_source"]
    for field in ("unavailable_capabilities", "filters_evaluated_against_unavailable_data"):
        if result.get(field):
            response[field] = result[field]
    _apply_sync_state_to_response(response, sync_state_block, sync_warnings)
    return BacklogListResponse.model_validate(response).model_dump(exclude_defaults=True)


def _page_status_source(
    source: object, items: Sequence[Mapping[str, object]], has_filters_evaluated_against_unavailable_data: bool = False
) -> StatusSource:
    """Narrow operation-level status provenance to the rows on this page.

    Returns:
        Status provenance for the returned page rows.
    """
    if source == "unavailable" and has_filters_evaluated_against_unavailable_data:
        return "unavailable"
    if source == "cache":
        return "cache"
    has_numeric = any(parse_issue_number(str(item.get("issue", ""))) is not None for item in items)
    if not has_numeric:
        return "cache"
    has_backend_owned = any(parse_issue_number(str(item.get("issue", ""))) is None for item in items)
    if source == "unavailable":
        return "unavailable"
    return "mixed" if has_backend_owned else "live"


def _resolve_effective_limit(all_items: list[dict[str, str | bool]], offset: int, limit: int) -> int:
    """Resolve the effective page limit for a ``backlog_list`` response.

    When ``limit > 0`` the caller's explicit value is returned unchanged.
    When ``limit == 0`` the function auto-paginates: it binary-halves the
    candidate slice until the serialised JSON fits within ``_LIST_TOKEN_BUDGET``.

    Args:
        all_items: The full filtered-and-deduplicated item list.
        offset: The pagination offset (items already skipped).
        limit: The caller-supplied limit (0 = auto-paginate).

    Returns:
        Effective item count for the current page.
    """
    if limit > 0:
        return limit
    candidate = all_items[offset:]
    effective = len(candidate)
    while effective > 1:
        if _token_count(json.dumps(candidate[:effective])) <= _LIST_TOKEN_BUDGET:
            break
        effective = max(1, effective // 2)
    return effective


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Backlog Items",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_list(
    refresh: Annotated[
        bool, Field(description="Reconcile the command's live provider snapshot in the foreground before returning")
    ] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
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
    filter_by_key: Annotated[
        dict[str, str] | None,
        Field(
            description=(
                "Generic key=value filter applied after type/topic/status filtering, "
                "on the result item dicts. Each key=value pair matches items where the "
                "item's value for that key equals the requested value (string comparison). "
                "All pairs compose with AND logic. A key the item does not carry returns "
                'no match (a no-op, not an error). Example: {"type": "Bug", "section": "P1"}.'
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
) -> Annotated[dict[str, object], _wire_schema(BacklogListResponse)]:
    """List all open backlog items.

    When match_context=True, use page/tokens_per_page/page_token_limit to control
    token-based pagination of match output; when match_pages.paginated=true, use
    page=2..N to retrieve subsequent pages.

    When ``has_more`` is true, ``next_call`` carries the follow-up call string to page
    with. Items are deduplicated by issue number.

    ``status_source`` reports where the status data came from,
    ``unavailable_capabilities`` names what could not be read live this call, and
    ``filters_evaluated_against_unavailable_data`` names any filter that ran against
    data that was not live. Treat a filtered listing as incomplete when the filter is
    named there.

    Live provider data is attempted first. Pass ``allow_cached=True`` only to permit
    a warned cache fallback after that live attempt fails.
    """
    out = Output()
    try:
        _assert_config()
        result, backend_status = await asyncio.gather(
            asyncio.to_thread(
                operations.list_items,
                refresh=refresh,
                allow_cached=allow_cached,
                label=label,
                section=section,
                status=status,
                title=title_filter,
                type_=type_,
                topic=topic,
                include_closed=include_closed,
                filter_by_key=filter_by_key,
                search=search,
                output=out,
            ),
            asyncio.to_thread(_probe_backend_status),
        )
    except BacklogError as e:
        backend_status = await asyncio.to_thread(_probe_backend_status)
        return _respond(
            BacklogListResponse,
            {"error": str(e), "retryable": _retryable(e), "backend": backend_status.model_dump(), **out.to_dict()},
        )

    _schedule_maintenance_if_checkpoint_absent()
    sync_state_block, sync_warnings = _build_sync_state_block(get_sync_state())

    if result.get("items") is None:
        # Fail-safe withheld listing (backlog #3546 task A4): operations.list_items
        # declined to serve items/count from a low-confidence provider-private
        # cache. Return early -- the dedup/pagination pipeline below assumes a
        # real list and would otherwise silently reconstruct items: [], the
        # exact ambiguous shape this withheld response exists to avoid.
        # cache_open_count/cache_total_count are normally derived from the
        # dedup'd item list below (ADR-5) -- which this early return skips
        # entirely because the cache result is low-confidence. Leaving them
        # at BackendStatus's default 0 would reintroduce, inside the nested
        # "backend" object, the exact authoritative-looking-zero problem
        # items/count=None exists to avoid (Codex review, PR #3576 finding
        # 1): mark them explicitly unknown rather than defaulting to a real
        # observation this response never made.
        backend_status.cache_open_count = None
        backend_status.cache_total_count = None
        withheld: dict[str, object] = {
            "items": None,
            "count": None,
            "from_cache": result.get("from_cache"),
            "has_pending_writes": result.get("has_pending_writes"),
            "status_source": result.get("status_source"),
            "unavailable_capabilities": result.get("unavailable_capabilities"),
            "filters_evaluated_against_unavailable_data": result.get("filters_evaluated_against_unavailable_data"),
            "backend": backend_status.model_dump(),
            **out.to_dict(),
        }
        _apply_sync_state_to_response(withheld, sync_state_block, sync_warnings)
        return _respond(BacklogListResponse, withheld, exclude_none=False, exclude_unset=True)

    # "items" holds list[dict[str, str | bool]] per operations.list_items return type.
    # Filter to dict elements only to narrow the heterogeneous value union.
    all_items: list[dict[str, str | bool]] = _extract_item_list(result)

    # Deduplicate by issue number — the cache may contain duplicate entries for
    # the same issue (observed: an issue appeared twice when multiple match paths
    # selected the same item).  Keyed on numeric issue number; first occurrence wins.
    all_items = _dedup_by_issue_number(all_items)

    total = len(all_items)

    # cache_open_count reflects the same filter as the items list.
    # Hoisted above count_only short-circuit so divergence computation always has
    # the correct cache count regardless of which path returns.
    backend_status.cache_open_count = total

    # Build sync_state block when the background sync is not IDLE.
    # Emitted on both the full path and the count_only path so callers can
    # distinguish "offline, cache empty" from "healthy search returned 0".
    sync_state_block, sync_warnings = _build_sync_state_block(get_sync_state())

    # count_only short-circuit: return only the item count without page content.
    # Carries sync_state + warnings when the sync is not IDLE (silent-failure prevention).
    # exclude_defaults=True (not exclude_none=True): BacklogListResponse inherits
    # Output's messages/warnings/errors, whose Field(default_factory=list) default
    # is [] rather than None, so exclude_none alone would leave them in the
    # response and contradict this branch's documented minimal shape.
    #
    # `out` (the operations-layer Output collector `list_items` wrote into) is
    # merged here on its `warnings`/`errors` channels only — never `messages`.
    # `list_items(refresh=True)` records a healthy reconciliation summary with
    # `out.info()`, while reconciliation failures and pending/rejected mutations
    # use `out.warn()`. This keeps routine prose out of the documented minimal
    # shape without discarding side-effect degradation results.
    if count_only:
        # from_cache/has_pending_writes are sourced from the same `result`
        # dict list_items already returned above -- operations.list_items
        # guarantees both keys are always present (backlog #3546 task A4).
        # Without them, a caller reading a bare count from a warm cache that
        # still holds unconfirmed local writes could mistake local-only rows
        # for provider-acknowledged data (Codex review, PR #3576 finding 2).
        return _build_count_only_response(total, result, out, sync_state_block, sync_warnings)

    # Append the human-readable backend status line to the messages list.
    out.info(_format_backend_status_message(backend_status))

    effective_limit = _resolve_effective_limit(all_items, offset, limit)
    page_items = all_items[offset : offset + effective_limit]
    has_more = (offset + effective_limit) < total

    # Primitive 2 and 1: enrich page items when depth or match context is requested.
    # Order matters: match context must read body BEFORE item_depth removes it.
    # Step 1 — add match snippets (reads body from original page_items)
    # Step 2 — apply token-based pagination (match_context=True only)
    # Step 3 — apply depth (may remove body from the already-enriched items)
    # Use a widened list type to accommodate the richer value types added by enrichment.
    match_pages: dict[str, object] | None = None
    if match_context:
        enriched_items, match_pages = _paginate_match_items(
            _enrich_with_match_context(page_items, search, snippet_context=snippet_context),
            page=page,
            tokens_per_page=tokens_per_page,
            page_token_limit=page_token_limit,
        )
    else:
        enriched_items: list[dict[str, object]] | list[dict[str, str | bool]] = page_items

    page_status_source = _page_status_source(
        result.get("status_source"), enriched_items, bool(result.get("filters_evaluated_against_unavailable_data"))
    )

    if item_depth > 0:
        enriched_items = [_apply_item_depth(dict(it), item_depth) for it in enriched_items]

    # Apply fields projection or default body exclusion.
    enriched_items = _apply_fields_projection(enriched_items, fields=fields, item_depth=item_depth, out=out)

    response: dict[str, object] = {
        **result,
        "items": enriched_items,
        "count": len(enriched_items),
        "status_source": page_status_source,
        "unavailable_capabilities": (
            result.get("unavailable_capabilities", []) if page_status_source == "unavailable" else []
        ),
        "available_fields": list(_AVAILABLE_FIELDS),
        "pagination": {"offset": offset, "limit": effective_limit, "total": total, "has_more": has_more},
        "backend": backend_status.model_dump(),
        **out.to_dict(),
    }
    _apply_sync_state_to_response(response, sync_state_block, sync_warnings)
    if has_more:
        response["next_call"] = f"backlog_list(offset={offset + effective_limit}, limit={effective_limit})"
    if match_pages is not None:
        response["match_pages"] = match_pages
        _maybe_add_pagination_notice(match_pages, out, response)
    return _respond(BacklogListResponse, response)


def _build_compact_manifest(
    result: models.ViewItemResult, full_response: dict[str, object], selector: str
) -> dict[str, object]:
    """Build the compact routing manifest returned by ``backlog_view(summary=True)``.

    Args:
        result: Typed ViewItemResult from view_item.
        full_response: Full serialised response dict (used only for size hint).
        selector: Original selector string for _hint message.

    Returns:
        Compact dict with issue_number, title, labels, status, plan_address,
        and size hint for the full response.
    """
    full_chars = len(json.dumps(full_response))
    plan_address: str | None = result.plan or None
    issue_number: int | None = result.number
    if issue_number is None:
        num_match = re.search(r"(\d+)", result.issue)
        if num_match:
            issue_number = int(num_match.group(1))
    status: str = "closed" if result.state == "closed" else "open"
    sections_index = _sections_index_from_result(result)
    if sections_index:
        # A section directory exists, so section='<name>' is a valid address —
        # name it first (R7 prohibition 1).
        hint = (
            f"Load specific sections: backlog_view(selector='{selector}', summary=False, section='<index, title, or /regex/>')\n"
            f"Load full content: backlog_view(selector='{selector}', summary=False)"
        )
    else:
        # This item has no section directory (unstructured body): a section=
        # address would produce a section_filter_miss, not content, so the only
        # mechanism present in this response is the unfiltered full-content load.
        hint = f"Load full content: backlog_view(selector='{selector}', summary=False)"
    compact: dict[str, object] = {
        "issue_number": issue_number,
        "title": result.title,
        "labels": result.labels,
        "status": status,
        "plan_address": plan_address,
        "section_filter_miss": result.section_filter_miss,
        "status_source": result.status_source,
        "unavailable_capabilities": result.unavailable_capabilities,
        "_summary": True,
        "_full_chars": full_chars,
        "_hint": hint,
    }
    if sections_index:
        compact["sections_index"] = sections_index
    return compact


def _sections_index_from_result(result: models.ViewItemResult) -> str:
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


def _build_over_budget_view(
    result: models.ViewItemResult, full_chars: int, selector: str, *, narrowed_to_single_section: bool = False
) -> dict[str, object]:
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
        narrowed_to_single_section: True when the caller already narrowed the
            request to one section (``section=`` or ``sections=[...]``) and that
            section alone is still over budget. ``_usage`` then names ``map=True``
            instead of repeating section-narrowing advice the caller has already
            exhausted, satisfying R7 prohibition 2 (never recommend an action the
            caller has already exhausted) in
            docs/agent-markdown-consumption-contract.md. It names no ``navigate=``
            ordinal because ``sections_index`` numbering is not guaranteed to
            match the ordinals ``navigate=`` resolves.

            This fixes address *validity* only. R7 prohibition 3 (never name a
            mechanism absent from the response it accompanies) stays unmet: the
            ``map=True`` call itself can exceed the budget, and there is no
            smaller retrieval to fall back to for that section, so the hint can
            still name a mechanism that cannot resolve the request. See
            architect spec 5.4 / ADR 9.1 and #3059.

    Returns:
        Compact dict with number, title, priority, status, description,
        sections_index, _over_budget, _full_chars, and _usage.
    """
    if narrowed_to_single_section:
        usage = (
            f"This response exceeded the {_VIEW_TOKEN_BUDGET}-token budget "
            f"({full_chars} chars in full form), even after narrowing to a single section — "
            "further section= narrowing is not available for this request. "
            "Get this item's ordinal map, then page through the oversized section with "
            "navigate=/head=/skip_tokens=:\n"
            f"  backlog_view(selector='{selector}', map=True)\n"
            "Note: map=True's own over_budget field reflects this item's total content "
            "estimate, not the size of the map response itself — the map text is usually "
            "small enough to return even when over_budget is true. There is no smaller "
            "retrieval for this section available yet."
        )
    else:
        usage = (
            f"This response exceeded the {_VIEW_TOKEN_BUDGET}-token budget "
            f"({full_chars} chars in full form). "
            "Use the sections_index below to identify which sections you need, "
            "then request them individually:\n"
            f"  backlog_view(selector='{selector}', summary=False, sections=['Section Name'])\n"
            f"  backlog_view(selector='{selector}', summary=False, section='0,1,3')\n"
            f"  backlog_view(selector='{selector}', summary=False, section='/regex/')"
        )
    compact: dict[str, object] = {
        "number": result.number,
        "title": result.title,
        "priority": result.priority,
        "status": result.status,
        "description": result.description,
        "section_filter_miss": result.section_filter_miss,
        "status_source": result.status_source,
        "unavailable_capabilities": result.unavailable_capabilities,
        "_over_budget": True,
        "_full_chars": full_chars,
        "_usage": usage,
    }
    sections_index = _sections_index_from_result(result)
    if sections_index:
        compact["sections_index"] = sections_index
    return compact


def _execute_disclosure_or_passthrough(
    selector: str, req: DisclosureRequest, refresh: bool = False, allow_cached: bool = False
) -> dict[str, object] | None:
    """Execute a non-PASSTHROUGH progressive disclosure request synchronously.

    Intended for ``asyncio.to_thread``.  The caller guards on
    ``req.mode != PASSTHROUGH`` before calling — this function does NOT handle
    PASSTHROUGH (returns None for it as a safety net only).

    ``OrdinalNotFoundError`` and ``BacklogError`` are caught and converted to
    error dicts so the ``to_thread`` caller receives a clean return value with
    no exception. The generic ``BacklogError`` arm includes ``error_type``
    (``type(exc).__name__``) so a caller can branch on the exception's
    identity instead of only its rendered message — flattening every
    ``BacklogError`` subtype (a missing item, a refused GraphQL/REST lookup,
    an unsupported backend capability, ...) to a bare ``{"error": str(exc)}``
    would discard which one occurred. ``OrdinalNotFoundError`` keeps its
    existing dedicated ``requested_ordinal``/``valid_ordinals`` fields unchanged — it already
    carries structured identity and that shape is pinned by
    ``test_code_fence_miss_key_set_matches_numeric_miss``.

    Args:
        selector: Issue selector forwarded to the disclosure handler.
        req: Validated disclosure request (mode + ordinal/token params).
        refresh: Forwarded to ``BacklogViewDisclosureHandler.handle()`` so
            map/navigate/extract calls get the same bypass-cache live check
            as the passthrough path.
        allow_cached: Permit warned cached fallback after a live read failure.

    Returns:
        Serialised response dict for MAP/NAVIGATE/EXTRACT, None for PASSTHROUGH
        (safety net only), or an error dict when OrdinalNotFoundError or
        BacklogError (including ItemNotFoundError) is raised.
    """
    if req.mode == DisclosureMode.PASSTHROUGH:
        return None  # safety net — caller should never reach this branch
    try:
        response = BacklogViewDisclosureHandler().handle(selector, req, refresh=refresh, allow_cached=allow_cached)
        return response.model_dump()
    except OrdinalNotFoundError as exc:
        return {
            "error": str(exc),
            "retryable": _retryable(exc),
            "requested_ordinal": exc.requested,
            "valid_ordinals": exc.valid_ordinals,
        }
    except BacklogError as exc:
        return {"error": str(exc), "retryable": _retryable(exc), "error_type": type(exc).__name__}


@mcp.tool(
    annotations=ToolAnnotations(
        title="View Backlog Item",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_view(
    selector: Annotated[
        str,
        Field(
            description="Item selector: GitHub issue URL, #N, bare number, or title substring, or beads nanoid (e.g. bd-a3f8)"
        ),
    ],
    refresh: Annotated[
        bool,
        Field(
            description=(
                "Request live enrichment for native-backend title selectors. GitHub selectors "
                "are always read live first regardless of this flag. For GitHub, prefers the authoritative "
                "head-pointer/audit-comment record; on a resolution failure it falls "
                "back to the raw issue body and records a warning that the body may be stale."
            )
        ),
    ] = False,
    summary: Annotated[
        bool,
        Field(
            description=(
                "When True (default), returns a compact routing manifest with issue_number, title, labels, "
                "status, plan_address, sections_index (all available sections as [N] Title (count) lines), "
                "_full_chars, and _hint showing how to load specific sections or full content. "
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
        Field(
            description=(
                "Entry filter: 'all', 'last', 'first', 'struck', integer N (first N active "
                "entries), or negative integer -N (last N active entries)"
            )
        ),
    ] = None,
    since: Annotated[
        str | None,
        Field(
            description=(
                "ISO date/datetime. Entries at or after this timestamp are included, plus any entry "
                "whose write time is unknown. An unknown-timestamp entry carries the literal id "
                "'0000-00-00T00:00:00Z' (legacy content stored before entries were timestamped); its "
                "age cannot be compared to the cutoff, so it is returned rather than withheld. Treat "
                "that id as 'may or may not be new', not as an old entry."
            )
        ),
    ] = None,
    section: Annotated[
        str | None,
        Field(
            description=(
                "Section filter, matched against ## / ### headings — works on raw GitHub issue "
                "bodies too, not just structured YAML items. "
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
                "A section name not present in the item returns an error dict containing "
                "``error``, ``section_filter_miss=True``, and ``valid_sections`` listing "
                "available names; an optional ``suggestion`` key is included when a close "
                "match exists. The error response has no ``body`` field. "
                "Default None returns the full response unchanged."
            )
        ),
    ] = None,
    map: Annotated[  # ruff: ignore[builtin-argument-shadowing] — shadows builtin; matches MCP parameter name exactly
        bool,
        Field(
            description=(
                "When True, returns a flat ordinal dot-path map of the item's structure. "
                "Each line shows an ordinal (e.g. '4.0'), section title, estimated token count, "
                "and a content preview. Mutually exclusive with navigate. Use this first to "
                "discover valid ordinals."
            )
        ),
    ] = False,
    navigate: Annotated[
        str | None,
        Field(
            description=(
                "Dot-path ordinal targeting a section, sub-heading, or code fence "
                "(e.g. '4.0', '3.0.1', '4.0.1', '4.0.code.0'). "
                r"Format: numeric path, optionally ending in a code-fence terminal, matching ^\d+(\.\d+)*(\.code\.\d+)?$. "
                "Without head, returns the full content at the ordinal (NAVIGATE mode). "
                "Combined with head, activates EXTRACT mode for token-bounded pagination. "
                "Use map=True first to discover valid ordinals."
            )
        ),
    ] = None,
    head: Annotated[
        int | None,
        Field(
            ge=1,
            le=25000,
            description=(
                "Maximum tokens to return from the targeted ordinal (1-25,000). "
                "Requires navigate. Returns a token-bounded window with truncated=True and "
                "a next_call hint when more content remains. "
                "Note: head activates EXTRACT mode; offset is an entry-block index (different concern)."
            ),
        ),
    ] = None,
    skip_tokens: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "Token offset for pagination continuation (requires head and navigate). "
                "skip_tokens is a within-content token offset (absolute, cl100k_base). "
                "Distinct from offset, which is an entry-block index. "
                "Set from the next_call hint to page through large content windows."
            ),
        ),
    ] = 0,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogViewResponse)]:
    r"""View a single backlog item or GitHub issue in detail.

    Ordinal format: ^\d+(\.\d+)*(\.code\.\d+)?$. Examples:
        "4.0"        — section entry (level-2)
        "4.0.1"      — sub-heading within an entry (level-3+)
        "4.0.code.0" — first code fence in an entry's direct body

    To page through large content: navigate=<ordinal>, head=4000, then repeat with
    skip_tokens set from the returned next_call hint until truncated=False.

    ``map=True`` returns the ordinal structure. ``navigate=<ordinal>`` returns that
    entry, and adding ``head=N`` windows it — page on with ``skip_tokens`` from the
    returned ``next_call``. ``summary=True`` (the default) returns the compact shape;
    ``summary=False`` returns the whole item.

    ``file_path`` is for reference only. Change the item with ``backlog_update`` or
    ``backlog_groom``.

    ``status_source`` reports where this item's live-enrichment data came from, and
    ``unavailable_capabilities`` names what could not be read live this call.

    ``struck`` and ``entry_id`` describe the addressed entry. They are ``False`` and
    empty for a level-1 section ordinal, which is not a single entry.

    Navigating to an ordinal the item does not hold returns ``valid_ordinals``, every
    ordinal it does hold.
    """
    # ---- Progressive disclosure routing (architect spec §4.6) -----------------
    # Single early-return gate: MAP/NAVIGATE/EXTRACT → return dict; PASSTHROUGH → fall through.
    disclosure_result: dict[str, object] | None = None
    try:
        disclosure_req = DisclosureRequestParser().parse(map=map, navigate=navigate, head=head, skip_tokens=skip_tokens)
        if disclosure_req.mode != DisclosureMode.PASSTHROUGH:
            disclosure_result = await asyncio.to_thread(
                _execute_disclosure_or_passthrough, selector, disclosure_req, refresh, allow_cached
            )
    except DisclosureParamError as exc:
        disclosure_result = {"error": str(exc), "retryable": _retryable(exc), "invalid_params": exc.invalid_params}

    if disclosure_result is not None:
        if "error" not in disclosure_result:
            _schedule_maintenance_if_checkpoint_absent()
        return _respond(BacklogViewResponse, disclosure_result, exclude_none=False, exclude_unset=True)
    # ---- PASSTHROUGH: falls through to legacy code below -----------------------

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
            refresh=refresh,
            allow_cached=allow_cached,
        )
        full_response = result.model_dump()
        _schedule_maintenance_if_checkpoint_absent()
        if not summary:
            # Normalise an empty ``sections=[]`` to "no section filter" (equivalent
            # to None) so the falsy-vs-None handling is consistent everywhere
            # (issue #2495 finding #6): an empty list must not empty the sections
            # dict, must not count as a narrowing request, and must not report a
            # miss.  ``sections=[]`` therefore behaves identically to
            # ``sections=None``.
            sections_filter = sections or None
            # Primitive 3: filter to named sections when requested.
            if sections_filter is not None:
                full_response = _filter_view_sections(full_response, sections_filter, result)
            # Return an explicit error dict on section-filter miss.  Covers both
            # the singular ``section=`` path (flag set by view_item via
            # _apply_body_section_filter / _assemble_view_compact) and the plural
            # ``sections=[...]`` path (flag set by _filter_view_sections above).
            # The error dict has no ``body`` field, distinguishing it from a content
            # response.  ``section_filter_miss`` is retained for backward compatibility.
            if result.section_filter_miss:
                filter_expr = section if section is not None else ", ".join(sections or [])
                return _respond(
                    BacklogViewResponse,
                    _build_section_miss_error(filter_expr, result.section_filter_valid_names, out),
                    exclude_none=False,
                    exclude_unset=True,
                )
            # Auto-compact: when the response exceeds the token budget return a compact
            # section-directory form so the caller can request only what it needs.
            #
            # The gate measures the NARROWED payload (issue #2495 defect a).  When the
            # caller requested narrowing (section / sections / offset / limit),
            # view_item and _filter_view_sections have already narrowed both
            # full_response["body"] and full_response["sections"], so full_response IS
            # the narrowed slice.  The directory fallback therefore fires only when the
            # measured payload is still over budget — i.e. an unbounded default call, or
            # a narrowed slice that itself remains too large.  An explicitly requested
            # slice/page is never silently replaced by metadata-only ("No Invented
            # Limits"); it is delivered whenever it fits the budget.
            #
            # Serialisation is unconditional: the precise token count of the whole
            # (possibly narrowed) payload is the single authoritative budget measure.
            # A prior body-chars heuristic (``len(body) > ~16 000`` forcing the
            # over-budget directory) was removed (issue #2495 finding #7).  That
            # heuristic was an over-eager approximation: char count is NOT a reliable
            # proxy for token count.  A large-but-COMPRESSIBLE body (e.g. a long run of
            # one repeated character: 16 500 chars but only ~2 100 tokens) is well under
            # _VIEW_TOKEN_BUDGET, yet the char heuristic would have wrongly suppressed it
            # into the directory.  The token count below is authoritative and may now
            # correctly deliver such a large-but-compressible body inline (No Invented
            # Limits) — while still gating bodies whose token count genuinely exceeds the
            # budget, including incompressible prose that the old heuristic also caught.
            # Measure the de-duplicated delivered payload (issue #2495 finding #4):
            # the per-entry ``content`` in the ``sections`` dict duplicates the body
            # text the caller already receives once via ``body``, so counting it
            # again wrongly inflates the measured size and can trip the directory for
            # a body that is comfortably under budget on its own.  ``body`` is still
            # measured in full, so a genuinely-too-large body (or narrowed slice)
            # still gates.  ``_full_chars`` in the directory hint reports the real
            # serialised char length of the full payload the caller would receive.
            serialised = json.dumps(full_response)
            if _view_payload_token_count(full_response) > _VIEW_TOKEN_BUDGET:
                # Read the narrowed section count from full_response, not result:
                # _filter_view_sections() narrows full_response["sections"] for the
                # plural sections=[...] path but leaves result untouched.
                narrowed_sections = full_response.get("sections")
                # Normalise a blank/whitespace-only ``section`` the same way
                # ``operations.view_item()`` does internally (``(section or
                # "").strip() or None``) — a blank string performs no narrowing
                # there, so it must not count as one here either, or an item
                # that happens to have exactly one section total would be
                # reported as an already-exhausted single-section request the
                # caller never made.
                section_requested = bool((section or "").strip())
                narrowed_to_single_section = (
                    (section_requested or sections_filter is not None)
                    and isinstance(narrowed_sections, dict)
                    and len(narrowed_sections) == 1
                )
                return _respond(
                    BacklogViewResponse,
                    _build_over_budget_view(
                        result, len(serialised), selector, narrowed_to_single_section=narrowed_to_single_section
                    ),
                    exclude_none=False,
                    exclude_unset=True,
                )
            return _respond(BacklogViewResponse, full_response, exclude_none=False, exclude_unset=True)
        return _respond(
            BacklogViewResponse,
            _build_compact_manifest(result, full_response, selector),
            exclude_none=False,
            exclude_unset=True,
        )
    except BacklogError as e:
        return _respond(
            BacklogViewResponse,
            {"error": str(e), "retryable": _retryable(e), **out.to_dict()},
            exclude_none=False,
            exclude_unset=True,
        )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Sync Backlog", read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True
    )
)
async def backlog_sync(
    ctx: Context,
    dry_run: Annotated[bool, Field(description="Preview what would be synced without making changes")] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogSyncResponse)]:
    """Sync backlog items with the configured backend: create missing work items and push groomed content.

    Use dry_run=true to preview changes without modifying anything.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.sync_items, dry_run=dry_run, output=out)
        return _respond(BacklogSyncResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogSyncResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Link Follow-up Item",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_link_followup(
    selector: Annotated[
        str, Field(description="Item selector: title substring, #N, bare number, URL, or beads nanoid")
    ],
    followup_to: Annotated[
        str,
        Field(
            description=(
                "Logical ID of the originating plan or task (e.g. 'P1', 'P1/T3'). "
                "Use P{N}/T{N} addresses or slugs — not GitHub issue numbers. "
                "Empty string clears the link."
            )
        ),
    ],
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogLinkFollowupResponse)]:
    """Link a follow-up backlog item to its originating plan or task.

    Records the origin's logical ID on the item's ``followup_to`` metadata
    field so the relationship is queryable via ``backlog_list_followups``.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.link_followup, selector=selector, followup_to=followup_to, allow_cached=allow_cached, output=out
        )
        return _respond(BacklogLinkFollowupResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogLinkFollowupResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Follow-up Items",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def backlog_list_followups(
    followup_to: Annotated[
        str,
        Field(
            description=(
                "Logical ID of the originating plan or task (e.g. 'P1', 'P1/T3'). "
                "Returns backlog items whose followup_to matches this value, excluding skipped items."
            )
        ),
    ],
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogListFollowupsResponse)]:
    """List backlog items linked as follow-ups to the given origin.

    Returns all items whose ``metadata.followup_to`` exactly matches the
    given logical ID.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_followups, followup_to=followup_to, allow_cached=allow_cached, output=out
        )
        _schedule_maintenance_if_checkpoint_absent()
        return _respond(BacklogListFollowupsResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogListFollowupsResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Close Backlog Item",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_close(
    selector: Annotated[
        str,
        Field(
            description="Item selector: GitHub issue URL, #N, bare number, title substring, or beads nanoid (e.g. bd-a3f8)"
        ),
    ],
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
    cleanup: Annotated[bool, Field(description="Reserved; currently has no effect")] = False,
    force: Annotated[bool, Field(description="Close even if open PRs reference the issue")] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogCloseResponse)]:
    """Dismiss a backlog item without completing it and close it on the configured backend.

    Use for items that are duplicates, out of scope, superseded, wontfix,
    or permanently blocked. For completed work, use backlog_resolve instead.
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
            allow_cached=allow_cached,
            output=out,
        )
        return _respond(BacklogCloseResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogCloseResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Resolve Backlog Item",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_resolve(
    selector: Annotated[
        str,
        Field(
            description="Item selector: GitHub issue URL, #N, bare number, or title substring, or beads nanoid (e.g. bd-a3f8)"
        ),
    ],
    summary: Annotated[str, Field(description="What was done — 1-2 sentence completion summary (required)")],
    plan: Annotated[
        str | None, Field(description="Plan address or completion reference. The item stores it verbatim.")
    ] = None,
    method: Annotated[str | None, Field(description="How the work was done — approach taken")] = None,
    notes: Annotated[str | None, Field(description="Problems found, surprises, or other comments")] = None,
    follow_ups: Annotated[str | None, Field(description="Created follow-up tickets (comma-separated refs)")] = None,
    findings: Annotated[str | None, Field(description="Retrospective learnings from this work")] = None,
    cleanup: Annotated[bool, Field(description="Reserved; currently has no effect")] = False,
    force: Annotated[bool, Field(description="Resolve even if open PRs reference the issue")] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogResolveResponse)]:
    """Mark a backlog item as DONE (completed) and close it on the configured backend.

    plan/method/notes/follow_ups/findings become a structured completion comment
    on the GitHub backend; other backends forward only summary (as the close
    reason) or discard these fields — they are not persisted to local item state.
    Only summary is required — for trivial items a one-liner suffices.
    For dismissals (duplicate, out of scope, etc.), use backlog_close instead.
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
            allow_cached=allow_cached,
            output=out,
        )
        return _respond(BacklogResolveResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogResolveResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update Backlog Item",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_update(
    selector: Annotated[
        str,
        Field(
            description="Item selector: GitHub issue URL, #N, bare number, or title substring, or beads nanoid (e.g. bd-a3f8)"
        ),
    ],
    plan: Annotated[
        str | None,
        Field(description="Plan address to record on the item, such as Pa1b2c3d4. The item stores it verbatim."),
    ] = None,
    status: Annotated[
        str | None,
        Field(description="Set item status (e.g. 'in-progress'). Updates the backend's status labels when applicable."),
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
        Field(
            description=(
                "New description text for the item. Reconciled immediately to the linked "
                "GitHub issue as an audit-trail comment if the item has one; never edits the "
                "issue's raw body field, which stays human-owned."
            )
        ),
    ] = None,
    entry_id: Annotated[
        str | None,
        Field(
            description=(
                "ID of an existing entry to replace within the section, as returned by "
                "backlog_view. When two entries in one section share a stored ID, backlog_view "
                "returns them with a positional '-N' suffix and that suffixed form is the one "
                "that targets them. An id matching no entry is an error naming the available "
                "ids, never a silent no-op."
            )
        ),
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
            description="Mark the linked work item as verified. "
            "Signals that /complete-implementation quality gates have passed. "
            "May be a no-op depending on the active backend — check the returned messages."
        ),
    ] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogUpdateResponse)]:
    """Update a backlog item: attach a plan, set status, or write groomed content.

    Groomed content is synced to the linked work item when the item has one.
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
            allow_cached=allow_cached,
        )
        return _respond(BacklogUpdateResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogUpdateResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Groom Backlog Item",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_groom(
    ctx: Context,
    selector: Annotated[
        str,
        Field(
            description=(
                "Item selector: GitHub issue URL, #N, bare number, or title substring, or beads "
                "nanoid (e.g. bd-a3f8) — do not prefix a beads nanoid with '#'; only a bare "
                "GitHub number takes that prefix, a '#'-prefixed nanoid resolves neither form"
            )
        ),
    ],
    section: Annotated[
        str | None, Field(description="Section name for incremental update (use with content parameter)")
    ] = None,
    content: Annotated[
        str | None, Field(description="Content for the named section (use with section parameter)")
    ] = None,
    entry_id: Annotated[
        str | None,
        Field(
            description=(
                "ID of an existing entry to replace within the section, as returned by "
                "backlog_view. When two entries in one section share a stored ID, backlog_view "
                "returns them with a positional '-N' suffix and that suffixed form is the one "
                "that targets them. An id matching no entry is an error naming the available "
                "ids, never a silent no-op."
            )
        ),
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
                "status to 'groomed' and update the backend's status labels. No effect on backends without "
                "a groomed lifecycle state — check the returned messages."
            )
        ),
    ] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogGroomResponse)]:
    """Write groomed content through the configured backend and sync its linked GitHub issue.

    When the item has a GitHub issue, the groomed content is synced there
    automatically.

    With ``mark_groomed=True``, the status advance is skipped when the item cannot be
    resolved again after the write, and ``mark_groomed_skipped`` says so. Test that
    field rather than assuming the status moved.
    """
    out = Output()
    if sections is not None and any((section, content, entry_id, replace_section, reason, append)):
        return BacklogGroomResponse(
            error="sections is mutually exclusive with section, content, entry_id, replace_section, reason, and append"
        ).model_dump(exclude_none=True)
    try:
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
            allow_cached=allow_cached,
        )
        return _respond(BacklogGroomResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogGroomResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Normalize Backlog Items",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def backlog_normalize(
    ctx: Context,
    dry_run: Annotated[bool, Field(description="Preview normalization changes without modifying files")] = False,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogNormalizeResponse)]:
    """Normalize all work items through the configured backend."""
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.normalize_items, dry_run=dry_run, allow_cached=allow_cached, output=out
        )
        return _respond(BacklogNormalizeResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogNormalizeResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Pull Backlog Items",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
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
) -> Annotated[dict[str, object], _wire_schema(BacklogPullResponse)]:
    """Reconcile linked issue content.

    Only backends that support reconciliation act on this — on other backends
    this is a no-op; check the returned messages.

    Auto-migrates P0/P1 items lacking GitHub Issues by creating them.
    Merges by section using entry-aware merge (keeps longer entries, preserves strikes).

    ``count`` is set when pulling in bulk, ``file_path`` when pulling one selector.
    """
    out = Output()
    try:
        if selector is not None:
            result = await asyncio.to_thread(operations.pull_by_selector, selector, diff=diff, output=out)
            response = BacklogPullResponse.model_validate({**result, **out.to_dict()})
            dump = response.model_dump(exclude_none=True)
            # file_path is a meaningful, documented null on this path's no-op
            # success shape (e.g. the backend lacks reconciliation support) --
            # exclude_none=True would otherwise drop the key entirely. Not
            # applied on the bulk (no-selector) path below, where file_path
            # genuinely doesn't apply and should stay absent.
            dump["file_path"] = response.file_path
            return dump
        result = await asyncio.to_thread(operations.pull_items, dry_run=dry_run, force=force, diff=diff, output=out)
        return _respond(BacklogPullResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogPullResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create SAM Task",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def backlog_create_sam_task(
    parent_issue_number: Annotated[int, Field(description="Parent story issue number (GitHub issue integer)")],
    task_id: Annotated[str, Field(description="Feature-scoped task ID, e.g. 'T1'")],
    feature: Annotated[str, Field(description="Feature slug, e.g. 'my-feature'")],
    task_type: Annotated[str, Field(description="Task category: research | implement | review | fix | docs")],
    agent: Annotated[str, Field(description="Agent name to execute this task")],
    priority: Annotated[int, Field(description="Priority 1-5 (1=highest)")] = 2,
    skills: Annotated[list[str], Field(description="Skill names for the executing agent")] = [],  # ruff: ignore[mutable-argument-default]
    dependencies: Annotated[list[str], Field(description="Task IDs this task depends on")] = [],  # ruff: ignore[mutable-argument-default]
    description: Annotated[str, Field(description="Human-readable description of the task")] = "",
    acceptance_criteria: Annotated[list[str] | None, Field(description="Acceptance criteria strings")] = None,
    labels: Annotated[list[str] | None, Field(description="GitHub label names to apply")] = None,
    repo: Annotated[str, Field(description="Repository slug (owner/name)")] = "",
) -> Annotated[dict[str, object], _wire_schema(BacklogCreateSamTaskResponse)]:
    """Create a GitHub sub-issue for a SAM task under a parent story issue.

    ``url`` is always empty.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.create_sam_task,
            parent_issue_number=parent_issue_number,
            repo=repo,
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
        return _respond(BacklogCreateSamTaskResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogCreateSamTaskResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get SAM Tasks", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def backlog_get_sam_tasks(
    parent_issue_number: Annotated[
        int | str, Field(description="Parent work-item reference (GitHub issue integer or provider-native string)")
    ],
    refresh_cache: Annotated[
        bool, Field(description="Compatibility flag; the configured provider owns refresh")
    ] = True,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(SamTaskLookupResult)]:
    """Return SAM tasks owned by a configured-backend work item.

    Returns tasks plus explicit provider freshness and availability state.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.get_sam_tasks,
            parent_issue_number=parent_issue_number,
            refresh_cache=refresh_cache,
            allow_cached=allow_cached,
            output=out,
        )
        _schedule_maintenance_if_checkpoint_absent()
        return _respond(SamTaskLookupResult, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(SamTaskLookupResult, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update SAM Task Status",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_update_sam_task_status(
    issue_number: Annotated[int, Field(description="Task sub-issue number (GitHub issue integer)")],
    new_status: Annotated[str, Field(description="Target status: not-started | in-progress | complete | blocked")],
    repo: Annotated[str, Field(description="Repository slug (owner/name)")] = "",
) -> Annotated[dict[str, object], _wire_schema(BacklogUpdateSamTaskStatusResponse)]:
    """Update the status field in a SAM task sub-issue.

    Patches the sam:task YAML block in the issue body. No-op if status already matches.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.update_sam_task_status, issue_number=issue_number, new_status=new_status, repo=repo, output=out
        )
        return _respond(BacklogUpdateSamTaskStatusResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(
            BacklogUpdateSamTaskStatusResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()}
        )


# ---------------------------------------------------------------------------
# Artifact manifest tools
# ---------------------------------------------------------------------------

_artifact_registry = ArtifactRegistry()


# TODO(H05): Move to FastMCP lifespan context — eliminate module-level singleton.
def _require_artifact_entries(entries: list, label: str) -> None:
    """Raise BacklogError when no artifact entries are found.

    Args:
        entries: List of artifact entries (may be empty).
        label: Error message to include in the exception.

    Raises:
        BacklogError: When ``entries`` is empty.
    """
    if not entries:
        # The item holds no artifact matching the selector; repeating the lookup finds none either.
        raise BacklogError(label, retryable=False)


def _get_artifact_provider() -> ContentProvider:
    provider = get_config().backend
    if not isinstance(provider, ContentProvider):
        raise ContentUnavailableError("Active backend does not support artifact content")
    return provider


def _manifest_reference(item_id: ItemId) -> ContentRef:
    """Return the manifest identity for a backlog item, refusing as a ``BacklogError``.

    This is the boundary where caller-supplied ``item_id`` becomes a model: every
    ``artifact_*`` tool builds its manifest reference here. ``ContentRef``'s validator
    refuses an empty owner namespace with ``raise ValueError``, which pydantic re-raises
    as ``pydantic.ValidationError`` -- a ``ValueError`` subclass, not a ``BacklogError``,
    so each tool's ``except BacklogError`` missed it and the refusal failed the tool call
    instead of returning the documented ``error`` response. Converting it here covers
    every validator on the model, not just the empty-string case one field constraint
    would catch.

    Returns:
        The manifest ``ContentRef`` for the item.

    Raises:
        ValidationError: When ``item_id`` is not a usable owner namespace.
    """
    try:
        return ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace=str(item_id), name="manifest")
    except PydanticValidationError as exc:
        raise ValidationError("; ".join(error["msg"] for error in exc.errors())) from exc


def _load_manifest(provider: ContentProvider, item_id: ItemId) -> ArtifactManifest:
    return load_manifest_record(provider, _manifest_reference(item_id), item_id)[0]


def _artifact_type(value: str) -> ArtifactType:
    """Return a validated artifact type or fail the MCP call with ``ToolError``."""
    try:
        return ArtifactType(value)
    except ValueError as exc:
        raise ToolError(f"Unknown artifact type: {value!r}") from exc


@mcp.tool(
    annotations=ToolAnnotations(
        title="Register Artifact",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def artifact_register(
    item_id: Annotated[
        int | str,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[ArtifactType, Field(description="Artifact type registered against the work item")],
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
    content: Annotated[
        str,
        Field(
            min_length=1,
            description="Artifact body written through the selected content provider before its manifest registration.",
        ),
    ],
    status: Annotated[ArtifactStatus, Field(description="Lifecycle status of the artifact")] = ArtifactStatus.CURRENT,
    agent: Annotated[str, Field(description="Name of the producing agent")] = "",
) -> Annotated[dict[str, object], _wire_schema(ArtifactRegisterResponse)]:
    """Upsert an artifact entry in provider-owned logical content.

    Idempotent by (artifact_type, artifact_id). If an entry with the same type and
    artifact_id already exists it is updated in-place (status, agent, timestamp).
    If only the type matches but the artifact_id differs, a new row is added.

    When the configured backend cannot store the artifact or its manifest, the call
    fails with a tool error instead of returning a response.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        entry = ArtifactEntry(
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            status=status,
            created_at=datetime.now(UTC).isoformat(),
            agent=agent,
        )

        def _run() -> RegisterResult:
            updated_manifest, existed = publish_artifact(
                provider, _manifest_reference(item_id), item_id, entry, content
            )
            action = "updated" if existed else "added"

            return RegisterResult(
                registered=True, artifact_count=len(updated_manifest.artifacts), action=action, content_stored=True
            )

        result = await asyncio.to_thread(_run)
        return _respond(
            ArtifactRegisterResponse,
            {**result.model_dump(), "messages": out.messages, "warnings": out.warnings, "errors": out.errors},
        )
    except BacklogError as e:
        return _respond(ArtifactRegisterResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Artifacts", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def artifact_list(
    item_id: Annotated[
        int | str,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[str | None, Field(description="Filter by artifact type (optional)")] = None,
) -> Annotated[dict[str, object], _wire_schema(ArtifactsListResponse)]:
    """Return all artifacts registered for a backlog item.

    Returns an empty list when no manifest section exists yet — this is not an error.

    An unrecognised ``artifact_type``, or a configured backend that cannot reach the
    manifest, fails with a tool error instead of returning a response.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        type_filter: ArtifactType | None = _artifact_type(artifact_type) if artifact_type else None

        def _run() -> list[dict]:
            manifest = _load_manifest(provider, item_id)
            if type_filter is not None:
                entries = _artifact_registry.get_by_type(manifest, type_filter)
            else:
                entries = manifest.artifacts
            return [e.model_dump(mode="json") for e in entries]

        artifacts = await asyncio.to_thread(_run)
        return _respond(ArtifactsListResponse, {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()})
    except BacklogError as e:
        return _respond(ArtifactsListResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Artifact", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def artifact_get(
    item_id: Annotated[
        int | str,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[str, Field(description="Artifact type to retrieve")],
    artifact_id: Annotated[
        str | None,
        Field(
            description=(
                "Logical identifier of the specific artifact to return. Omit to return every "
                "artifact registered under this type."
            )
        ),
    ] = None,
) -> Annotated[dict[str, object], _wire_schema(ArtifactsListResponse)]:
    """Return metadata for artifacts registered on a backlog item under one type.

    Omitting ``artifact_id`` returns every entry of the type (e.g. multiple
    codebase-analysis files). Supplying it returns the single addressed entry.

    An absent artifact is data, not a failed call: ``error`` is set when the type is
    not found, or when ``artifact_id`` matches no entry of that type.

    An unrecognised ``artifact_type``, or a configured backend that cannot reach the
    manifest, fails with a tool error instead of returning a response.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        type_enum = _artifact_type(artifact_type)

        def _run() -> list[dict]:
            manifest = _load_manifest(provider, item_id)
            entries = _artifact_registry.get_by_type(manifest, type_enum)
            _require_artifact_entries(entries, f"No artifacts of type '{artifact_type}' found for item #{item_id}")
            if artifact_id is not None:
                entries = [entry for entry in entries if entry.artifact_id == artifact_id]
                _require_artifact_entries(
                    entries, f"No artifact with id '{artifact_id}' of type '{artifact_type}' found for item #{item_id}"
                )
            return [e.model_dump(mode="json") for e in entries]

        artifacts = await asyncio.to_thread(_run)
        return _respond(ArtifactsListResponse, {"artifacts": artifacts, "count": len(artifacts), **out.to_dict()})
    except BacklogError as e:
        return _respond(ArtifactsListResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Artifact", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def artifact_read(
    item_id: Annotated[
        int | str,
        Field(
            description="Backlog item identifier — GitHub issue number (int) or beads nanoid string (e.g. 'bd-a3f8')"
        ),
    ],
    artifact_type: Annotated[str, Field(description="Artifact type whose content to read")],
    artifact_id: Annotated[
        str | None,
        Field(
            description=(
                "Logical identifier of the specific artifact to read. Omit to read the most "
                "recently registered artifact of this type."
            )
        ),
    ] = None,
) -> Annotated[dict[str, object], _wire_schema(ArtifactReadResponse)]:
    """Read provider-owned logical content for a registered artifact.

    Omitting ``artifact_id`` returns the most recently registered entry of the type.
    Supplying it addresses one specific entry.

    An absent artifact is data, not a failed call: ``error`` is set when the type is
    not found, or when the selected provider holds no matching content.

    An unrecognised ``artifact_type``, or a configured backend that cannot reach the
    manifest, fails with a tool error instead of returning a response.
    """
    out = Output()
    try:
        provider = _get_artifact_provider()
        type_enum = _artifact_type(artifact_type)

        def _run() -> ArtifactContent:
            manifest = _load_manifest(provider, item_id)
            entries = _artifact_registry.get_by_type(manifest, type_enum)
            _require_artifact_entries(entries, f"No artifacts of type '{artifact_type}' found for item #{item_id}")
            if artifact_id is not None:
                entries = [entry for entry in entries if entry.artifact_id == artifact_id]
                _require_artifact_entries(
                    entries, f"No artifact with id '{artifact_id}' of type '{artifact_type}' found for item #{item_id}"
                )
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

            content = provider.get_content(artifact_content_reference(item_id, entry)).content
            return ArtifactContent(
                artifact_type=entry.artifact_type, path=entry.artifact_id, content=content, status=entry.status
            )

        result = await asyncio.to_thread(_run)
        return _respond(ArtifactReadResponse, {**result.model_dump(mode="json"), **out.to_dict()})
    except BacklogError as e:
        return _respond(ArtifactReadResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Ready SAM Tasks",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_get_ready_sam_tasks(
    parent_issue_number: Annotated[int, Field(description="Parent story issue number (native reference)")],
) -> Annotated[dict[str, object], _wire_schema(BacklogGetReadySamTasksResponse)]:
    """Return SAM tasks whose status is not-started and all dependencies are terminal."""
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.get_ready_sam_tasks, parent_issue_number=parent_issue_number, output=out
        )
        return _respond(BacklogGetReadySamTasksResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogGetReadySamTasksResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Strike Entry", read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def backlog_strike_entry(
    selector: Annotated[
        str,
        Field(
            description="Item selector: GitHub issue URL, #N, bare number, or title substring, or beads nanoid (e.g. bd-a3f8)"
        ),
    ],
    entry_id: Annotated[
        str,
        Field(
            description=(
                "ID of the entry to strike, as returned by backlog_view for this section. "
                "When two entries in one section share a stored ID, backlog_view returns them "
                "with a positional '-N' suffix and that suffixed form is the one that targets "
                "them. An id matching no entry is an error naming the available ids, never a "
                "silent no-op."
            )
        ),
    ],
    reason: Annotated[str, Field(description="Human-readable reason for striking the entry")],
    section: Annotated[str | None, Field(description="Optional section name to scope the search within")] = None,
    allow_cached: Annotated[bool, Field(description=_ALLOW_CACHED_DESCRIPTION)] = False,
) -> Annotated[dict[str, object], _wire_schema(BacklogStrikeEntryResponse)]:
    """Strike (retract) an entry block within a backlog item.

    Wraps the entry in a collapsed details block with the reason,
    preserving the original content for audit. Syncs to the linked work item
    if the item has one.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.strike_entry,
            selector=selector,
            entry_id=entry_id,
            reason=reason,
            section=section,
            allow_cached=allow_cached,
            output=out,
        )
        return _respond(BacklogStrikeEntryResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogStrikeEntryResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Labels", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def backlog_list_labels(
    limit: Annotated[int, Field(description="Maximum labels to return")] = 100,
) -> Annotated[dict[str, object], _wire_schema(BacklogListLabelsResponse)]:
    """List repository labels. Requires a backend with label support — errors otherwise.

    Returns all labels defined on the repository, up to ``limit``. There is no
    separate label-mutation tool; labels change as a side effect of ``backlog_update``,
    ``backlog_groom``, ``backlog_resolve``, or ``backlog_close`` changing an item's status.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_labels, limit=limit, output=out)
        return _respond(BacklogListLabelsResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogListLabelsResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Merged PRs", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
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
) -> Annotated[dict[str, object], _wire_schema(BacklogListMergedPrsResponse)]:
    """List merged pull requests. Requires a backend with PR support — errors otherwise.

    Only PRs that were actually merged (not just closed) are returned.
    Use ``search`` to filter by issue reference (e.g. ``'#42'``) or any
    keyword present in the PR title or body.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_merged_prs, search=search, limit=limit, output=out)
        return _respond(BacklogListMergedPrsResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogListMergedPrsResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Milestones", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def backlog_list_milestones(
    state: Annotated[str, Field(description="Milestone state filter: open | closed | all")] = "open",
) -> Annotated[dict[str, object], _wire_schema(BacklogListMilestonesResponse)]:
    """List repository milestones filtered by state.

    Requires a backend with milestone support — errors otherwise. Returns
    milestones with their issue counts and optional due dates.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_milestones, state=state, output=out)
    except BacklogError as e:
        return _respond(BacklogListMilestonesResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})
    response = BacklogListMilestonesResponse.model_validate({**result, **out.to_dict()})
    dump = response.model_dump(exclude_none=True)
    # due_on is a meaningful, documented null per milestone (no due date set) --
    # exclude_none=True's recursive drop would otherwise remove the key from
    # any milestone lacking one. response.milestones is always a real list
    # here (never None): the operations.list_milestones result this branch
    # validated from always supplies it.
    if response.milestones is not None:
        dump["milestones"] = [m.model_dump() for m in response.milestones]
    return dump


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get Soonest Milestone",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_get_soonest_milestone() -> Annotated[
    dict[str, object], _wire_schema(BacklogGetSoonestMilestoneResponse)
]:
    """Return the open milestone with the earliest due date.

    Requires a backend with milestone support — errors otherwise. Milestones
    without a due date are excluded. If all open milestones
    lack a due date, the first one by the backend's default ordering is
    returned with a warning.

    ``milestone`` is absent when no open milestone exists.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.get_soonest_milestone, output=out)
    except BacklogError as e:
        return _respond(
            BacklogGetSoonestMilestoneResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()}
        )
    response = BacklogGetSoonestMilestoneResponse.model_validate({**result, **out.to_dict()})
    # milestone=None is a meaningful, documented success value (no open
    # milestones exist), not an absent-on-this-branch field like `error` --
    # exclude_none=True would otherwise drop the key entirely, which the
    # docstring's "milestone (or None)" contract does not allow.
    dump = response.model_dump(exclude_none=True)
    dump["milestone"] = response.milestone.model_dump() if response.milestone is not None else None
    return dump


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Milestone",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def backlog_create_milestone(
    title: Annotated[str, Field(description="Milestone title (required, must be non-empty)")],
    description: Annotated[str, Field(description="Optional milestone description")] = "",
    due_on: Annotated[
        str | None,
        Field(description="Optional due date as ISO 8601 string, e.g. '2026-06-30' or '2026-06-30T00:00:00Z'"),
    ] = None,
) -> Annotated[dict[str, object], _wire_schema(BacklogCreateMilestoneResponse)]:
    """Create a new milestone on the repository.

    Requires a backend with milestone support — errors otherwise.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.create_milestone, title=title, description=description, due_on=due_on, output=out
        )
    except BacklogError as e:
        return _respond(BacklogCreateMilestoneResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})
    response = BacklogCreateMilestoneResponse.model_validate({**result, **out.to_dict()})
    dump = response.model_dump(exclude_none=True)
    # due_on is a meaningful, legitimate null (caller can create a milestone
    # without a due date) -- exclude_none=True's recursive drop would
    # otherwise remove the key from the nested milestone.
    if response.milestone is not None:
        dump["milestone"] = response.milestone.model_dump()
    return dump


@mcp.tool(
    annotations=ToolAnnotations(
        title="Assign Item To Milestone",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_assign_item_to_milestone(
    issue_number: Annotated[int, Field(description="Issue number to assign")],
    milestone_number: Annotated[int, Field(description="Milestone number to assign the issue to")],
) -> Annotated[dict[str, object], _wire_schema(BacklogAssignItemToMilestoneResponse)]:
    """Assign a backlog item to a milestone.

    Requires a backend with milestone support — errors otherwise.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.assign_item_to_milestone,
            issue_number=issue_number,
            milestone_number=milestone_number,
            output=out,
        )
    except BacklogError as e:
        return BacklogAssignItemToMilestoneResponse.model_validate({
            "error": str(e),
            "retryable": _retryable(e),
            **out.to_dict(),
        }).model_dump(exclude_none=True)
    return BacklogAssignItemToMilestoneResponse.model_validate({**result, **out.to_dict()}).model_dump(
        exclude_none=True
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Issues", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def backlog_list_issues(
    milestone: Annotated[str | None, Field(description="Filter by milestone title")] = None,
    labels: Annotated[str | None, Field(description="Comma-separated label names to filter by")] = None,
    state: Annotated[str, Field(description="Issue state: open, closed, or all")] = "open",
    limit: Annotated[int, Field(description="Maximum issues to return")] = 30,
) -> Annotated[dict[str, object], _wire_schema(BacklogListIssuesResponse)]:
    """List GitHub issues with optional milestone, label, and state filters."""
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_issues, milestone=milestone, labels=labels, state=state, limit=limit, output=out
        )
    except BacklogError as e:
        return _respond(BacklogListIssuesResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})
    response = BacklogListIssuesResponse.model_validate({**result, **out.to_dict()})
    dump = response.model_dump(exclude_none=True)
    # milestone is a meaningful, documented null per issue (no milestone
    # assigned) -- exclude_none=True's recursive drop would otherwise remove
    # the key from any issue without one. response.issues is always a real
    # list here (never None): the operations.list_issues result this branch
    # validated from always supplies it.
    if response.issues is not None:
        dump["issues"] = [i.model_dump() for i in response.issues]
    return dump


@mcp.tool(
    annotations=ToolAnnotations(
        title="Comment on Issue",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def backlog_comment_issue(
    issue_number: Annotated[int, Field(description="GitHub issue number (integer)")],
    body: Annotated[str, Field(description="Comment body (Markdown)")],
) -> Annotated[dict[str, object], _wire_schema(BacklogCommentIssueResponse)]:
    """Add a comment to a GitHub issue.

    ``database_id`` is the id ``backlog_read_comment`` takes as its ``comment_id``; it
    is absent when GitHub reports no integer id. The ``comment_id`` returned here is a
    GraphQL node id and does not work there. ``comment_url`` is always empty.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.comment_issue, issue_number=issue_number, body=body, output=out)
        return _respond(BacklogCommentIssueResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogCommentIssueResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Issue Comments",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_list_comments(
    issue_number: Annotated[int, Field(description="GitHub issue number (integer)")],
    limit: Annotated[int, Field(description="Maximum comments to return")] = 20,
    offset: Annotated[int, Field(description="Number of comments to skip")] = 0,
) -> Annotated[dict[str, object], _wire_schema(BacklogListCommentsResponse)]:
    """List comments on a GitHub issue.

    ``database_id`` is the id to pass as ``backlog_read_comment``'s ``comment_id``.
    ``id`` is a GraphQL node id and does not work there.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.list_comments, issue_number=issue_number, limit=limit, offset=offset, output=out
        )
        return _respond(BacklogListCommentsResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogListCommentsResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Issue Comment",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def backlog_read_comment(
    issue_number: Annotated[int, Field(description="GitHub issue number (integer)")],
    comment_id: Annotated[
        int,
        Field(
            description=(
                "REST comment database ID (integer) — obtain it from the GitHub REST API, from "
                "backlog_list_comments's per-comment database_id field, or from "
                "backlog_comment_issue's database_id field. backlog_list_comments's id and "
                "backlog_comment_issue's comment_id are GraphQL node IDs and will not work here; "
                "database_id may also be absent for a given comment (e.g. non-GitHub backends)."
            )
        ),
    ],
) -> Annotated[dict[str, object], _wire_schema(BacklogReadCommentResponse)]:
    """Read the full body of a single comment on a GitHub issue.

    ``body`` is the full Markdown, never truncated.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(
            operations.read_comment, issue_number=issue_number, comment_id=comment_id, output=out
        )
        return _respond(BacklogReadCommentResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogReadCommentResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="List Projects", read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )
)
async def backlog_list_projects(
    owner: Annotated[str | None, Field(description="GitHub owner (org or user). Defaults to repo owner")] = None,
    limit: Annotated[int, Field(description="Maximum projects to return")] = 20,
) -> Annotated[dict[str, object], _wire_schema(BacklogListProjectsResponse)]:
    """List Projects V2 for the repository owner via GraphQL."""
    out = Output()
    try:
        result = await asyncio.to_thread(operations.list_projects, owner=owner, limit=limit, output=out)
        return _respond(BacklogListProjectsResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogListProjectsResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Project",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    )
)
async def backlog_create_project(
    title: Annotated[str, Field(description="Project title")],
    owner: Annotated[str | None, Field(description="GitHub owner (org or user). Defaults to repo owner")] = None,
) -> Annotated[dict[str, object], _wire_schema(BacklogCreateProjectResponse)]:
    """Create a Projects V2 project under the repository owner.

    Resolves the owner node ID then runs the createProjectV2 GraphQL mutation.
    """
    out = Output()
    try:
        result = await asyncio.to_thread(operations.create_project, title=title, owner=owner, output=out)
        return _respond(BacklogCreateProjectResponse, {**result, **out.to_dict()})
    except BacklogError as e:
        return _respond(BacklogCreateProjectResponse, {"error": str(e), "retryable": _retryable(e), **out.to_dict()})


def _dispatch_reference(milestone_number: int) -> ContentRef:
    return ContentRef(kind=ContentKind.DISPATCH_PLAN, name=f"dispatch-milestone-{milestone_number}")


def _read_dispatch_plan(milestone_number: int) -> dispatch_schema.DispatchPlan:
    return dispatch_schema.DispatchPlan.model_validate_json(
        _get_artifact_provider().get_content(_dispatch_reference(milestone_number)).content
    )


def _try_register_dispatch_plan_artifact(item_id: ItemId, artifact_id: str, content: str) -> None:
    log = logging.getLogger(__name__)
    try:
        provider = _get_artifact_provider()
        entry = ArtifactEntry(
            artifact_type=ArtifactType.DISPATCH_PLAN,
            artifact_id=artifact_id,
            status=ArtifactStatus.CURRENT,
            agent="dispatch_create_plan",
        )
        publish_artifact(provider, _manifest_reference(item_id), item_id, entry, content)
        log.info("dispatch_create_plan: registered dispatch-plan artifact %s for item %s", artifact_id, item_id)
    except (
        BacklogError,
        ContentUnavailableError,
        ContentConflictError,
        UnsupportedCapabilityError,
        GithubException,
    ) as exc:
        log.warning(
            "dispatch_create_plan: artifact registration failed for item %s (artifact=%s): %s",
            item_id,
            artifact_id,
            exc,
        )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Read Dispatch Plan",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def dispatch_read(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
) -> Annotated[dict[str, object], _wire_schema(DispatchReadResponse)]:
    """Read a dispatch plan for the given milestone.

    Returns an error response if no plan is stored for this milestone or it
    fails schema validation.
    """
    try:
        plan = await asyncio.to_thread(_read_dispatch_plan, milestone_number)
    except ContentUnavailableError:
        return _respond(
            DispatchReadResponse,
            {"error": "Dispatch plan not found", "retryable": False, "milestone_number": milestone_number},
        )
    except ValueError as exc:
        return _respond(
            DispatchReadResponse,
            {"error": str(exc), "retryable": _retryable(exc), "milestone_number": milestone_number},
        )
    return _respond(DispatchReadResponse, {"milestone_number": milestone_number, "plan": plan.model_dump()})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Validate Dispatch Plan",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def dispatch_validate(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
) -> Annotated[dict[str, object], _wire_schema(DispatchValidateResponse)]:
    """Validate an existing dispatch plan's structural integrity.

    Reads the plan file then runs five structural checks: duplicate issues,
    conflict group references, depends_on existence, wave ordering, and
    conflict group wave placement.
    """
    try:
        plan = await asyncio.to_thread(_read_dispatch_plan, milestone_number)
    except (ContentUnavailableError, ValueError) as exc:
        return _respond(
            DispatchValidateResponse,
            {"error": str(exc), "retryable": _retryable(exc), "milestone_number": milestone_number},
        )
    result = await asyncio.to_thread(dispatch_schema.validate_plan_integrity, plan)
    return _respond(DispatchValidateResponse, {"milestone_number": milestone_number, **dataclasses.asdict(result)})


@mcp.tool(
    annotations=ToolAnnotations(
        title="Check Dispatch Staleness",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def dispatch_stale_check(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    repo: Annotated[str, Field(description="Repository slug owner/name. Defaults to repo from project")] = "",
) -> Annotated[dict[str, object], _wire_schema(DispatchStaleCheckResponse)]:
    """Check whether a dispatch plan is stale relative to the current milestone.

    Requires a backend with milestone support — errors otherwise. Fetches the
    milestone's issues (open and closed), compares their issue
    numbers against those in the plan, and returns a stale/fresh indicator
    with added/removed issue lists.

    The ``dispatch stale-check`` CLI command runs the
    same implementation and returns the same result.
    """
    result = await asyncio.to_thread(operations.dispatch_stale_check, milestone_number, repo)
    return _respond(DispatchStaleCheckResponse, result)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Create Dispatch Plan",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def dispatch_create_plan(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    plan: Annotated[dispatch_schema.DispatchPlan, Field(description="The dispatch plan for this milestone.")],
    overwrite: Annotated[
        bool,
        Field(
            description=(
                "Allow overwriting an existing stored plan. When False (default), returns an "
                "error if a plan for this milestone already exists."
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
) -> Annotated[dict[str, object], _wire_schema(DispatchCreatePlanResponse)]:
    """Create or overwrite a stored dispatch plan for a milestone.

    ``plan`` is the typed plan itself, stored atomically through the configured
    content backend, and validated for structural integrity after writing unless
    ``validate`` is false. On GitHub, online writes succeed only when byte-identical
    to the stored plan. Offline writes may be queued and later rejected during replay.

    ``errors`` and ``warnings`` carry the plan's validation results, not this call's
    own output. ``milestone_number`` is absent when the plan already exists.
    """
    out = Output()
    # Verify plan.milestone.number matches the milestone_number parameter
    if plan.milestone.number != milestone_number:
        return _respond(
            DispatchCreatePlanResponse,
            {
                "error": (
                    f"Milestone number mismatch: parameter is {milestone_number} "
                    f"but plan.milestone.number is {plan.milestone.number}"
                ),
                # Two arguments that disagree disagree identically on the next call.
                "retryable": False,
                "milestone_number": milestone_number,
                **out.to_dict(),
            },
        )

    try:
        current = _get_artifact_provider().get_content(_dispatch_reference(milestone_number))
    except ContentNotFoundError:
        write = ContentWrite(
            reference=_dispatch_reference(milestone_number), content=plan.model_dump_json(), create_only=True
        )
    else:
        if not overwrite:
            return _respond(
                DispatchCreatePlanResponse,
                {
                    "error": "Dispatch plan already exists. Pass overwrite=True to replace it.",
                    # The identical call meets the identical stored plan; the message names the
                    # parameter that lifts the refusal, which is what makes it final rather than
                    # transient.
                    "retryable": False,
                    **out.to_dict(),
                },
            )
        write = ContentWrite(
            reference=_dispatch_reference(milestone_number),
            content=plan.model_dump_json(),
            expected_revision=current.revision,
        )

    # 6. Write atomically
    dispatch_content = write.content
    try:
        await asyncio.to_thread(_get_artifact_provider().put_content, write)
    except (BacklogError, ContentConflictError, UnsupportedCapabilityError) as exc:
        return _respond(
            DispatchCreatePlanResponse,
            {"error": str(exc), "retryable": _retryable(exc), "milestone_number": milestone_number, **out.to_dict()},
        )

    out.info(f"Stored dispatch plan {milestone_number}")

    # 7. Post-write validation
    is_valid: bool | None = None
    val_errors: list[str] = []
    val_warnings: list[str] = []
    if validate:
        val_result = await asyncio.to_thread(dispatch_schema.validate_plan_integrity, plan)
        is_valid = val_result.is_valid
        val_errors = list(val_result.errors)
        val_warnings = list(val_result.warnings)

    # 8. Artifact registration (best-effort)
    if issue is not None:
        _try_register_dispatch_plan_artifact(issue, _dispatch_reference(milestone_number).name, dispatch_content)

    wave_count = len(plan.waves)
    item_count = sum(len(wave.items) for wave in plan.waves)

    response = DispatchCreatePlanResponse.model_validate({
        "milestone_number": milestone_number,
        "wave_count": wave_count,
        "item_count": item_count,
        "is_valid": is_valid,
        **out.to_dict(),
        "errors": val_errors,
        "warnings": val_warnings,
    })
    dump = response.model_dump(exclude_none=True)
    dump["is_valid"] = response.is_valid
    return dump


@mcp.tool(
    annotations=ToolAnnotations(
        title="Analyze Dispatch Conflicts",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    )
)
async def dispatch_conflicts(
    milestone_number: Annotated[int, Field(description="GitHub milestone number")],
    repo: Annotated[str, Field(description="Repository slug owner/name. Defaults to repo from project")] = "",
) -> Annotated[dict[str, object], _wire_schema(DispatchConflictsResponse)]:
    """Analyze Impact Radius conflicts for items in a milestone.

    Fetches open issues for the milestone from GitHub, resolves each authoritative
    agent-managed body, extracts its Impact Radius section, then finds items that
    share canonical system identifiers or legacy paths.

    The ``dispatch conflicts`` CLI command runs the
    same implementation and returns the same result.
    """
    result = await asyncio.to_thread(operations.dispatch_conflicts, milestone_number, repo)
    return _respond(DispatchConflictsResponse, result)


# ---------------------------------------------------------------------------
# Dispatch execution tools — state management + process spawning
# ---------------------------------------------------------------------------

#: Lazily created singleton DispatchStateManager.
# TODO(H05): Move to FastMCP lifespan context — eliminate module-level singleton.
_dispatch_state_mgr: DispatchStateManager | None = None

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
    project_root = models.get_repo_root()
    return str(project_root).lstrip("/").replace("/", "-")


def _dispatch_state_manager() -> DispatchStateManager:
    """Return the lazily created DispatchStateManager singleton.

    Creates the state database under ``~/.dh/projects/{project-stub}/`` on
    first call. The parent directory is created if necessary.

    Returns:
        Shared ``DispatchStateManager`` instance for this server process.
    """
    global _dispatch_state_mgr  # ruff: ignore[global-statement]
    if _dispatch_state_mgr is None:
        db_path = Path.home() / ".dh" / "projects" / _project_stub() / "dispatch-state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _dispatch_state_mgr = DispatchStateManager(db_path)
    return _dispatch_state_mgr


@mcp.tool(
    annotations=ToolAnnotations(
        title="Start Dispatch Wave",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    )
)
async def dispatch_wave_start(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[int, Field(description="Wave number from dispatch plan (1-based)")],
    items: Annotated[
        list[dict[str, object]], Field(description="List of items, each with 'issue' (int) and 'title' (str) keys")
    ],
) -> Annotated[dict[str, object], _wire_schema(DispatchWaveStartResponse)]:
    """Record the start of a dispatch wave.

    Creates wave and item entries in the state database. Items are
    initialised with status ``pending``. Call this before spawning
    processes for a wave.

    ``error`` is set when the wave already exists, or when an item entry is malformed.
    """
    try:
        item_records = [
            DispatchItemRecord(
                milestone=milestone, wave_num=wave_num, issue=int(str(item["issue"])), title=str(item.get("title", ""))
            )
            for item in items
        ]
    except (KeyError, ValueError) as exc:
        return _respond(
            DispatchWaveStartResponse,
            {"error": f"Malformed item entry: {exc}", "retryable": False, "milestone": milestone, "wave_num": wave_num},
        )
    try:
        wave: DispatchWaveRecord = await asyncio.to_thread(
            _dispatch_state_manager().create_wave, milestone, wave_num, item_records
        )
    except sqlite3.IntegrityError:
        return _respond(
            DispatchWaveStartResponse,
            {
                "error": f"Wave {wave_num} already exists for milestone {milestone}",
                "retryable": False,
                "milestone": milestone,
                "wave_num": wave_num,
            },
        )
    return _respond(
        DispatchWaveStartResponse,
        {
            "milestone": wave.milestone,
            "wave_num": wave.wave_num,
            "items_count": len(wave.items),
            "status": wave.status,
            "messages": [f"Wave {wave_num} created with {len(wave.items)} items"],
            "warnings": [],
            "errors": [],
        },
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Update Dispatch Item Status",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def dispatch_item_status(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    issue: Annotated[int, Field(description="Issue number of the item")],
    status: Annotated[str, Field(description="New status: 'complete', 'failed', or 'skipped'")],
    result: Annotated[str, Field(description="Result summary or JSON from result file")] = "",
    error: Annotated[str, Field(description="Error details on failure")] = "",
    cost: Annotated[float | None, Field(description="USD cost if available from claude output")] = None,
) -> Annotated[dict[str, object], _wire_schema(DispatchItemStatusResponse)]:
    """Record completion or failure of a dispatch item.

    Looks up the item by milestone + issue across all waves. Updates
    status, result/error data, and completion timestamp.

    ``status`` must be ``complete``, ``failed``, or ``skipped``.
    """
    mgr = _dispatch_state_manager()

    def _find_and_update() -> dict[str, object]:
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
                                "retryable": False,
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
            "retryable": False,
            "milestone": milestone,
            "issue": issue,
        }

    result_dict = await asyncio.to_thread(_find_and_update)
    return _respond(DispatchItemStatusResponse, result_dict)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Query Dispatch Wave Status",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
)
async def dispatch_wave_status(
    milestone: Annotated[int, Field(description="GitHub milestone number")],
    wave_num: Annotated[int, Field(description="Wave number to query (1-based)")],
) -> Annotated[dict[str, object], _wire_schema(DispatchWaveStatusResponse)]:
    """Query the current status of a dispatch wave.

    Returns items as a flat list (in issue order) plus per-status counts and
    elapsed time. Before querying, checks PIDs for ALL in-progress items across
    every milestone/wave and marks dead ones as failed — this can mutate waves
    other than the one requested; only stale items in the requested wave are
    reported in the returned warnings.

    ``accumulated_usage`` is always zero. It is not wired up yet.
    """
    mgr = _dispatch_state_manager()
    warnings: list[str] = []

    def _check_and_query() -> DispatchWaveRecord | None:
        stale = mgr.check_stale_pids()
        warnings.extend(
            f"PID {stale_item.pid} for issue #{stale_item.issue} is dead — marked failed"
            for stale_item in stale
            if stale_item.milestone == milestone and stale_item.wave_num == wave_num
        )
        return mgr.get_wave(milestone, wave_num)

    wave = await asyncio.to_thread(_check_and_query)

    if wave is None:
        return DispatchWaveStatusResponse(
            error=f"Wave {wave_num} not found for milestone {milestone}", milestone=milestone, wave_num=wave_num
        ).model_dump(exclude_none=True)

    items = wave.items
    status_counts = collections.Counter(i.status for i in items)

    elapsed: float | None = None
    if wave.started_at:
        with contextlib.suppress(ValueError):
            start = datetime.fromisoformat(wave.started_at)
            end = datetime.fromisoformat(wave.completed_at) if wave.completed_at else datetime.now(UTC)
            elapsed = (end - start).total_seconds()

    # TODO: not yet wired to stored dispatch state — always zero. See docstring.
    accumulated_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "estimated_cost_usd": 0.0,
        "events_with_usage": 0,
    }

    summary = DispatchWaveStatusResponse(
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
        items=[i.model_dump(mode="json") for i in items],
        warnings=warnings,
        accumulated_usage=AccumulatedUsage.model_validate(accumulated_usage),
    )
    dump = summary.model_dump(exclude_none=True)
    # elapsed_seconds is a meaningful, documented null for a pending wave that
    # hasn't started yet -- exclude_none=True would otherwise drop the key
    # entirely instead of keeping it explicit.
    dump["elapsed_seconds"] = summary.elapsed_seconds
    return dump


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
    mgr: DispatchStateManager, milestone: int, wave_num: int, issue_num: int, pid: int, result_file: str
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
                    rj = json.loads(content)
                    item_cost = float(rj.get("cost", 0)) or None
                except (ValueError, KeyError, TypeError):
                    pass
                await asyncio.to_thread(mgr.set_item_complete, milestone, wave_num, issue_num, content, item_cost)
                return True, item_cost

        pid_alive = True
        if pid > 0:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pid_alive = False
            except PermissionError:
                pass

        if not pid_alive:
            error_msg = f"Process died unexpectedly (PID {pid})"
            await asyncio.to_thread(mgr.set_item_failed, milestone, wave_num, issue_num, error_msg)
            return False, None


async def _run_spawn_item(
    mgr: DispatchStateManager,
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
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, _ = await proc.communicate()
            stdout_text = stdout_bytes.decode(errors="replace").strip()

            try:
                spawn_data = json.loads(stdout_text)
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
        progress_message = (
            f"Wave {wave_num}: {counters.total_done}/{total_items} items — "
            f"{counters.completed} done, {counters.failed} failed"
        )
        _sync_task_log.info(progress_message)
        await ctx.report_progress(counters.total_done, total_items, message=progress_message)


@mcp.tool(
    task=True,
    annotations=ToolAnnotations(
        title="Spawn Dispatch Wave",
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
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
) -> Annotated[dict[str, object], _wire_schema(DispatchSpawnResponse)]:
    """Spawn and monitor kage-bunshin sessions for a dispatch wave.

    Runs as a background task (``task=True``). Returns a task ID immediately.
    The background task:

    1. Detects and marks stale PIDs from prior runs.
    2. Reads the dispatch plan to get wave items.
    3. Iterates waves from ``wave_num`` through the last wave in the plan.
    4. For each wave: spawns items throttled to ``max_concurrent``, monitors
       PIDs, reads result files, and reports progress as it goes.
    5. On item failure: marks failed, continues with remaining items.
    6. Reports the run summary once every wave completes.
    """
    try:
        plan = await asyncio.to_thread(_read_dispatch_plan, milestone)
    except ContentUnavailableError:
        return DispatchSpawnResponse(
            error=f"Dispatch plan not found for milestone {milestone}", milestone=milestone
        ).model_dump(exclude_none=True)
    except ValueError as exc:
        return DispatchSpawnResponse(error=f"Invalid dispatch plan: {exc}", milestone=milestone).model_dump(
            exclude_none=True
        )

    mgr = _dispatch_state_manager()
    await asyncio.to_thread(mgr.check_stale_pids)

    start_time = time.monotonic()
    integration_branch: str = plan.milestone.integration_branch
    all_waves = [w for w in plan.waves if w.wave >= wave_num]
    total_items = sum(len(w.items) for w in all_waves)
    per_wave_summaries: list[DispatchWaveSummary] = []
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
                    DispatchItemRecord(milestone=milestone, wave_num=wave.wave, issue=i.issue, title=i.title)
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
            DispatchWaveSummary(
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

    def _sum_costs() -> float | None:
        all_w = mgr.get_all_waves(milestone)
        costs = [i.cost for w in all_w if w.wave_num >= wave_num for i in w.items if i.cost is not None]
        return sum(costs) if costs else None

    total_cost = await asyncio.to_thread(_sum_costs)
    summary = DispatchSpawnResponse(
        milestone=milestone,
        waves_executed=len(all_waves),
        total_items=total_items,
        completed=overall.completed,
        failed=overall.failed,
        skipped=overall.skipped,
        elapsed_seconds=time.monotonic() - start_time,
        per_wave=[w.model_dump(mode="json") for w in per_wave_summaries],
        total_cost=total_cost,
        messages=[f"Dispatch complete: {overall.completed}/{total_items} items succeeded"],
        warnings=warnings,
    )
    dump = summary.model_dump(exclude_none=True)
    # total_cost is a meaningful, documented null when no dispatched item
    # reported a cost -- exclude_none=True would otherwise drop the key
    # entirely instead of keeping it explicit.
    dump["total_cost"] = summary.total_cost
    return dump


from agent_profile import mcp as agent_profile_mcp

mcp.mount(agent_profile_mcp, namespace="profile")

if __name__ == "__main__":
    mcp.run()
