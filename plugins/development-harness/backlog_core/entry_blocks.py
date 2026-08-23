"""Entry block operations for timestamped, addressable content within backlog sections."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import NamedTuple

from .models import Entry, EntryNotFoundError
from .timestamps import now_iso

# Matches ISO 8601 timestamps (with or without sub-second fraction) at the start of a string.
# Used in two places: detecting unwrapped seeds in the legacy entry path, and filtering
# entries by the ``since`` parameter (entry IDs may carry a dedup suffix like ``-0``, ``-1``).
_ISO_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")
# Prefix of the fallback entry ID assigned to unwrapped (legacy) content when no real
# ``added`` date is available. It is not a representable date, so it can never be parsed.
_ZERO_DATE_PREFIX = "0000-00-00"
# An entry ID: an ISO timestamp, optionally carrying the ``-N`` dedup suffix
# ``_resolve_duplicate_ids`` appends. The zero-date fallback ID matches this shape too.
_ENTRY_ID_PATTERN = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z(?:-\d+)?"
_ENTRY_ID_RE = re.compile(rf"\A{_ENTRY_ID_PATTERN}\Z")


_ENTRY_OPEN_RE = re.compile(r"<div><sub>([^<]+)</sub>")
# A void/self-closing <div/> is not an opener that needs a matching close — counting it as
# one makes the entry's nesting never return to zero, and the whole entry is skipped as
# truncated. The negative lookahead excludes only tags that self-close before their `>`.
_DIV_OPEN_TAG_RE = re.compile(r"<div\b(?![^>]*/>)", re.IGNORECASE)
_DIV_CLOSE_TAG_RE = re.compile(r"</div\s*>", re.IGNORECASE)
_DETAILS_OPEN_TAG_RE = re.compile(r"<details\b(?![^>]*/>)", re.IGNORECASE)
_DETAILS_CLOSE_TAG_RE = re.compile(r"</details\s*>", re.IGNORECASE)
_FENCE_LINE_RE = re.compile(r" {0,3}(`{3,}|~{3,})")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"(`+)[^\n]*?\1")
# A struck-entry wrapper, anchored to the very start of the entry's (stripped) content.
# Anchoring is what tells "this entry is struck" apart from "this entry's prose happens to
# quote the struck format" — the latter must not be misread as an actual strike.
_STRUCK_HEADER_RE = re.compile(r"\A<details><summary>struck:\s*(\S+)\s*—\s*(.*?)</summary>", re.DOTALL)


class EntrySpan(NamedTuple):
    """Where one entry block sits in a section body.

    Attributes:
        start: Offset of the opening ``<div><sub>``.
        end: Offset one past the closing ``</div>``.
        entry_id: The text between ``<sub>`` and ``</sub>``.
        content_start: Offset of the first character of the entry's content.
        content_end: Offset one past the entry's content.
    """

    start: int
    end: int
    entry_id: str
    content_start: int
    content_end: int


def _opaque_mask(text: str) -> list[bool]:
    """Mark every character markdown treats as literal rather than as structure.

    A ``<div>`` inside a fenced block, an inline code span, or an HTML comment is an
    example of a tag, not a tag. Counting one as nesting made a properly closed entry look
    truncated; ignoring a real one had the opposite effect. Deciding the three contexts
    once, here, means every caller inherits the same answer instead of each rediscovering
    which contexts to skip.

    Args:
        text: Section body text.

    Returns:
        A list parallel to *text*, true where that character sits in an opaque context.
    """
    mask = [False] * len(text)

    def cover(start: int, end: int) -> None:
        for i in range(start, end):
            mask[i] = True

    fence = ""
    for line_match in re.finditer(r"[^\n]*\n?", text):
        line = line_match.group()
        if not line:
            break
        delimiter = _FENCE_LINE_RE.match(line)
        if not fence:
            if delimiter is not None:
                fence = delimiter.group(1)
                cover(line_match.start(), line_match.end())
            continue
        cover(line_match.start(), line_match.end())
        if delimiter is not None:
            run = delimiter.group(1)
            # A fence closes only on the same character, in a run at least as long as the
            # one that opened it, with nothing but whitespace after it.
            if run[0] == fence[0] and len(run) >= len(fence) and not line.strip()[len(run) :].strip():
                fence = ""

    for pattern in (_HTML_COMMENT_RE, _INLINE_CODE_RE):
        for match in pattern.finditer(text):
            if not mask[match.start()]:
                cover(match.start(), match.end())

    return mask


def _find_balanced_close(
    text: str, open_re: re.Pattern[str], close_re: re.Pattern[str], from_offset: int, mask: list[bool]
) -> tuple[int, int] | None:
    """Find the close tag matching an opener whose own tag ended at *from_offset*.

    Shared by entry-wrapper ``<div>`` nesting and struck-block ``<details>`` nesting — both
    are "one already-consumed opener, find where balanced depth returns to zero" problems,
    and giving them one implementation means a grammar fix (self-closing tags, case
    insensitivity) applies to both instead of drifting apart.

    Args:
        text: Text to search.
        open_re: Pattern matching this tag family's opening tag.
        close_re: Pattern matching this tag family's closing tag.
        from_offset: Offset just past the already-consumed opening tag.
        mask: Opaque-context mask from :func:`_opaque_mask`, parallel to *text*.

    Returns:
        ``(close_start, close_end)`` for the closing tag, or ``None`` when nesting never
        returns to zero.
    """
    events = sorted(
        [(m.start(), m.end(), 1) for m in open_re.finditer(text, from_offset)]
        + [(m.start(), m.end(), -1) for m in close_re.finditer(text, from_offset)]
    )
    depth = 1
    for start, end, delta in events:
        if mask[start]:
            continue
        depth += delta
        if depth == 0:
            return start, end
    return None


def _match_struck(content: str) -> tuple[str, str, str] | None:
    """Detect a struck-entry wrapper anchored to the start of *content*.

    Requiring the marker at the very start (not merely present somewhere inside) is what
    keeps prose that quotes the struck format — documentation, an example — from being
    misread as an actual strike. Requiring balanced ``<details>`` nesting (not a stop at the
    first ``</details>``) is what keeps a nested ``<details>`` inside genuinely struck
    content from truncating everything after it.

    Args:
        content: An entry's full (stripped) content.

    Returns:
        ``(struck_at, reason, inner_content)`` when *content* opens with a struck marker
        whose ``<details>`` balances to a matching close; ``None`` otherwise.
    """
    header = _STRUCK_HEADER_RE.match(content)
    if header is None:
        return None
    mask = _opaque_mask(content)
    close = _find_balanced_close(content, _DETAILS_OPEN_TAG_RE, _DETAILS_CLOSE_TAG_RE, header.end(), mask)
    if close is None:
        return None
    close_start, _close_end = close
    inner = content[header.end() : close_start].strip()
    return header.group(1), header.group(2).strip(), inner


def find_entry_spans(text: str) -> list[EntrySpan]:
    """Locate every complete entry block in *text*.

    This is the single definition of where an entry begins and ends. ``parse_entries``
    reads content through it, and the section splitter treats exactly these ranges as
    opaque, so the two cannot disagree about whether a heading-shaped line is an entry's
    own content or a real section boundary. They previously did: the splitter tracked
    balanced nesting while the reader stopped at the first ``</div>``, so an entry holding
    any further HTML was shown intact by one and truncated by the other, and the content
    past that inner tag was dropped from the entry without a word.

    Extent is balanced ``<div>``/``</div>`` nesting, and tags inside an opaque context do
    not count (see :func:`_opaque_mask`). An opening marker whose nesting never returns to
    zero is a truncated wrapper, not an entry; it is skipped, so whatever follows stays
    reachable rather than being swallowed to the end of the document.

    Args:
        text: Section body text.

    Returns:
        Ordered list of :class:`EntrySpan`, one per complete entry block.
    """
    mask = _opaque_mask(text)
    spans: list[EntrySpan] = []
    search_from = 0
    while True:
        opener = _ENTRY_OPEN_RE.search(text, search_from)
        if opener is None:
            return spans
        if mask[opener.start()]:
            search_from = opener.end()
            continue
        close = _find_balanced_close(text, _DIV_OPEN_TAG_RE, _DIV_CLOSE_TAG_RE, opener.end(), mask)
        if close is None:
            # A fence the entry never closed marks the rest of the text opaque, the
            # wrapper's own </div> included, so a closed entry reads as truncated. Retry
            # counting every tag: an entry is far more likely to hold an unclosed fence
            # than to be genuinely unterminated, and mistaking the former for the latter
            # drops real content.
            close = _find_balanced_close(text, _DIV_OPEN_TAG_RE, _DIV_CLOSE_TAG_RE, opener.end(), [False] * len(text))
        if close is None:
            search_from = opener.end()
            continue
        close_start, close_end = close
        spans.append(
            EntrySpan(
                start=opener.start(),
                end=close_end,
                entry_id=opener.group(1),
                content_start=opener.end(),
                content_end=close_start,
            )
        )
        search_from = close_end


def _parse_entry_timestamp(entry_id: str) -> datetime | None:
    """Extract the ISO timestamp prefix from an entry ID and return a UTC-aware datetime.

    Returns:
        UTC-aware datetime parsed from the ISO timestamp prefix of ``entry_id``, or ``None``
        when ``entry_id`` carries the zero-date fallback prefix, which encodes an unknown
        timestamp rather than a real one.

    Raises:
        ValueError: If ``entry_id`` neither starts with the zero-date fallback prefix nor
            with a valid, calendar-real ISO timestamp.
    """
    if entry_id.startswith(_ZERO_DATE_PREFIX):
        # The zero-date fallback means "this entry's timestamp is unknown", not "year zero"
        # and not "older than everything". docs/unified-section-layer-brief.md forbids
        # substituting an epoch sentinel for a missing timestamp, and mapping it to
        # datetime.min did exactly that: every ``since=`` read then silently dropped the
        # entry, leaving the caller unable to distinguish "nothing changed" from "content
        # exists whose age I cannot determine". ``None`` states the unavailable outcome the
        # brief requires and leaves the include/exclude decision to the caller.
        return None
    m = _ISO_TIMESTAMP_RE.match(entry_id)
    if not m:
        msg = f"Entry ID does not contain a valid ISO timestamp prefix: {entry_id!r}"
        raise ValueError(msg)
    ts = m.group(1)
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _is_entry_id(entry_id: str) -> bool:
    """Return whether ``entry_id`` is a well-formed, calendar-real entry ID.

    Shape alone is not enough: ``2026-13-01T00:00:00Z`` matches the ID pattern but is not a
    date any calendar has, and adopting it persists an ID that makes every later ``since=``
    read raise. The zero-date fallback is accepted — it is the codebase's own encoding for an
    unknown timestamp, not a malformed one.

    Returns:
        ``True`` when the ID matches the entry-ID shape and parses as a real timestamp.
    """
    if not _ENTRY_ID_RE.match(entry_id):
        return False
    try:
        _parse_entry_timestamp(entry_id)
    except ValueError:
        return False
    return True


def _new_entry_block(content: str) -> str:
    """Wrap ``content`` in a freshly timestamped entry block.

    Returns:
        HTML div string with a ``now_iso()`` ``<sub>`` timestamp and ``content``.
    """
    return f"<div><sub>{now_iso()}</sub>\n\n{content}\n</div>"


def wrap_entry(content: str) -> str:
    """Normalize content into a sequence of complete, well-formed entry blocks.

    ``backlog_view`` renders entries with their ``<div><sub>...</sub>`` wrapper visible, so a
    caller that echoes back what it read submits content that is already wrapped — sometimes
    wholly, sometimes with its own additions around or between the blocks it read. All three
    shapes are normalized the same way: every complete block whose ID is a real entry ID is
    kept verbatim with its original timestamp, and every run of anything else — leading text,
    text between two blocks, trailing text — becomes its own freshly timestamped block.

    Wrapping such content as one unit instead is lossy in both directions. Blindly re-wrapping
    a pre-wrapped submission nests the blocks, and the nested form does not survive a body
    round-trip: the wrapper leaks into the entry's own content and the section splitter emits
    a stray ``</div>`` entry carrying an empty ID. Adopting it whole is equally lossy the other
    way — ``parse_entries`` extracts only entries :func:`find_entry_spans` locates, so anything
    sitting between or around the blocks reaches the provider body, is absent from the parsed
    entries, and is gone after the next render.

    Returns:
        One or more ``<div><sub>...</sub>...</div>`` blocks, separated by a blank line.
        Content that contains no complete entry block becomes a single new block.
    """
    text = content.strip()
    blocks: list[str] = []
    pos = 0
    for span in find_entry_spans(text):
        if not _is_entry_id(span.entry_id):
            # An entry-shaped block whose ID is not a real timestamp is not an entry — an
            # HTML example documenting the format, say. Leave it in the surrounding prose
            # run rather than adopting it: adopting persists the label as an entry ID, and
            # the next ``since=`` read then raises on it.
            continue
        gap = text[pos : span.start].strip()
        if gap:
            blocks.append(_new_entry_block(gap))
        blocks.append(text[span.start : span.end])
        pos = span.end
    tail = text[pos:].strip()
    if tail:
        blocks.append(_new_entry_block(tail))
    if not blocks:
        return _new_entry_block(text)
    return "\n\n".join(blocks)


def wrap_entry_with_timestamp(content: str, timestamp: str) -> str:
    """Wrap content with a specific timestamp (for legacy migration and overwrites).

    Returns:
        HTML div string with the provided timestamp and content.
    """
    return f"<div><sub>{timestamp}</sub>\n\n{content}\n</div>"


def _entry_from_span(text: str, span: EntrySpan) -> Entry:
    """Convert one located entry block into an Entry object.

    Args:
        text: The section body the span was located in.
        span: The entry's extent, from :func:`find_entry_spans`.

    Returns:
        Entry carrying the span's id and its full inner content.
    """
    ts = span.entry_id
    inner = text[span.content_start : span.content_end].strip()
    struck = _match_struck(inner)
    if struck:
        struck_at, reason, struck_content = struck
        return Entry(id=ts, content=struck_content, struck=True, struck_at=struck_at, struck_reason=reason)
    return Entry(id=ts, content=inner)


def _resolve_duplicate_ids(entries: list[Entry]) -> int:
    """Suffix duplicate IDs in-place with ``-0``, ``-1``, etc.

    A generated suffix must be unique against every id in the final result,
    not merely against other members of the same duplicate group — a raw id
    that was never duplicated keeps its literal form and so reserves it just
    as much as an id already assigned earlier in this pass. The counter for
    a duplicate group keeps incrementing past any candidate that collides
    with either.

    Returns:
        Count of Entry objects whose ``id`` was modified.
    """
    seen: dict[str, int] = {}
    has_dupes: set[str] = set()
    for e in entries:
        seen[e.id] = seen.get(e.id, 0) + 1
        if seen[e.id] > 1:
            has_dupes.add(e.id)

    modified = 0
    if has_dupes:
        reserved_ids = {entry_id for entry_id, count in seen.items() if count == 1}
        counters: dict[str, int] = {}
        for e in entries:
            if e.id in has_dupes:
                base = e.id
                idx = counters.get(base, 0)
                candidate = f"{base}-{idx}"
                while candidate in reserved_ids:
                    idx += 1
                    candidate = f"{base}-{idx}"
                counters[base] = idx + 1
                reserved_ids.add(candidate)
                e.id = candidate
                modified += 1
    return modified


def _deduplicate_timestamps(entries: list[Entry]) -> int:
    """Suffix duplicate timestamp IDs in-place with ``-0``, ``-1``, etc.

    Returns:
        Count of Entry objects whose ``id`` was modified.
    """
    return _resolve_duplicate_ids(entries)


def _apply_show_filter(raw_entries: list[Entry], show: str | int | None) -> list[Entry]:
    """Apply the ``show`` filter to parsed entries.

    Returns:
        Filtered list of Entry objects.
    """
    active = [e for e in raw_entries if not e.struck]

    if show is None or show == "all":
        return raw_entries
    if show == "struck":
        return [e for e in raw_entries if e.struck]
    if show == "last":
        return active[-1:] if active else []
    if show == "first":
        return active[:1] if active else []
    if isinstance(show, int):
        return active[:show] if show >= 0 else active[show:]
    msg = f"Unrecognized show filter: {show!r}"
    raise ValueError(msg)


def parse_entries(
    section_body: str, show: str | int | None = "all", since: str | None = None, added_date: str = "0000-00-00"
) -> list[Entry]:
    """Parse entry blocks from a section body.

    Args:
        section_body: Raw section text to parse.
        show: Filter — "all", "last", "first", "struck", positive int (first N),
              negative int (last N).
        since: ISO date/datetime string. Only entries at or after this are included.
        added_date: Fallback date for legacy (unwrapped) content.

    Returns:
        List of Entry objects, in chronological order.
    """
    spans = find_entry_spans(section_body)

    if not spans:
        content = section_body.strip()
        if not content:
            return []
        # If the content begins with an ISO timestamp (now_iso() format), use it
        # directly as the entry id so that round-trips after an unwrapped seed
        # preserve the original id rather than reconstructing from added_date.
        ts_match = _ISO_TIMESTAMP_RE.match(content)
        entry_id = ts_match.group(1) if ts_match else f"{added_date}T00:00:00Z"
        raw_entries = [Entry(id=entry_id, content=content)]
    else:
        raw_entries = [_entry_from_span(section_body, s) for s in spans]
        _deduplicate_timestamps(raw_entries)

    if since:
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=UTC)

        # An entry whose timestamp is unknown (the zero-date fallback ID) is kept, not
        # dropped. Excluding it makes "no entry is newer than the cutoff" indistinguishable
        # from "entries exist whose age cannot be determined", and the caller — a stateless
        # agent asking what changed since it last looked — then proceeds having never seen
        # that content. The unknown-ness is visible in the returned entry's own ``0000-00-00``
        # ID, so the caller can act on it; silently withholding the entry gives it nothing.
        raw_entries = [e for e in raw_entries if (ts := _parse_entry_timestamp(e.id)) is None or ts >= since_dt]

    return _apply_show_filter(raw_entries, show)


def strike_entry(entry_raw: str, reason: str) -> str:
    """Strike an entry block — wrap content in collapsed details with reason.

    Returns:
        Struck entry block HTML string.

    Raises:
        ValueError: If ``entry_raw`` is not a valid entry block.
    """
    now = now_iso()
    spans = find_entry_spans(entry_raw)
    if not spans:
        msg = "Cannot strike: not a valid entry block"
        raise ValueError(msg)

    span = spans[0]
    ts = span.entry_id
    content = entry_raw[span.content_start : span.content_end].strip()

    struck = _match_struck(content)
    if struck:
        content = struck[2]

    return (
        f"<div><sub>{ts}</sub>\n<details><summary>struck: {now} — {reason}</summary>\n\n{content}\n</details>\n</div>"
    )


def _rewrite_replace(
    existing_body: str, spans: list[EntrySpan], is_legacy: bool, new_content: str | None, reason: str, added_date: str
) -> str:
    """Handle the ``replace=True`` branch of rewrite_section.

    Returns:
        Rewritten section body with all existing entries struck and new content appended.
    """
    parts: list[str] = []
    if is_legacy:
        legacy_wrapped = wrap_entry_with_timestamp(existing_body.strip(), f"{added_date}T00:00:00Z")
        parts.append(strike_entry(legacy_wrapped, reason))
    else:
        parts.extend(strike_entry(existing_body[s.start : s.end], reason) for s in spans)
    if new_content:
        parts.append(wrap_entry(new_content))
    return "\n\n".join(parts)


def resolve_all_entry_ids(stored_ids: list[str]) -> list[str]:
    """Return *stored_ids* with duplicate-id collisions suffixed the way backlog_view shows them.

    Applies :func:`_resolve_duplicate_ids` to a throwaway id-only copy of
    *stored_ids*, so the result matches exactly what a body-parsed section
    (via :func:`parse_entries`) already publishes for the same collision
    shape. This is the single implementation of "what id does backlog_view
    show for this entry" -- both :func:`resolve_entry_id` (mapping an
    incoming id back to its index) and
    ``operations._build_sections_from_yaml_item`` (publishing ids for a
    backend-owned structured section, which has no body to parse) resolve
    against *this* function rather than each keeping a private copy of the
    suffixing loop.

    Because *stored_ids* is copied 1:1 into the throwaway ``Entry`` list
    below, the result aligns positionally with *stored_ids* itself -- and
    with any other list built from the same source in the same order (e.g.
    ``spans`` or a ``Section``'s ``entries``). No further positional pairing
    (``zip`` or otherwise) is needed beyond that alignment.

    Args:
        stored_ids: A section's entry ids, in storage order.

    Returns:
        *stored_ids*, collision-resolved: unique ids unchanged, duplicate ids
        suffixed ``-0``, ``-1``, etc. in storage order.
    """
    id_entries = [Entry(id=stored_id, content="") for stored_id in stored_ids]
    _resolve_duplicate_ids(id_entries)
    return [e.id for e in id_entries]


def resolve_entry_id(stored_ids: list[str], entry_id: str) -> int:
    """Return the index *entry_id* targets, after positional collision resolution.

    Args:
        stored_ids: A section's entry ids, in storage order.
        entry_id: The id to resolve, as returned by backlog_view.

    Returns:
        Index into *stored_ids* that *entry_id* targets.

    Raises:
        EntryNotFoundError: When ``entry_id`` matches neither a raw id nor a
            collision-resolved id. Names every id backlog_view would show for
            *stored_ids*.
    """
    resolved_ids = resolve_all_entry_ids(stored_ids)
    for idx, resolved_id in enumerate(resolved_ids):
        if resolved_id == entry_id:
            return idx
    raise EntryNotFoundError(entry_id, resolved_ids)


def _rewrite_by_entry_id(
    existing_body: str, spans: list[EntrySpan], is_legacy: bool, new_content: str | None, entry_id: str, added_date: str
) -> str:
    """Handle the ``entry_id`` branch of rewrite_section.

    Returns:
        Rewritten section body with the target entry replaced.
    """
    result_parts: list[str] = []
    if is_legacy:
        legacy_ts = f"{added_date}T00:00:00Z"
        if entry_id != legacy_ts:
            raise EntryNotFoundError(entry_id, [legacy_ts])
        result_parts.append(wrap_entry(new_content) if new_content else "")
    else:
        target_idx = resolve_entry_id([s.entry_id for s in spans], entry_id)
        for idx, span in enumerate(spans):
            if idx == target_idx:
                if new_content:
                    result_parts.append(wrap_entry_with_timestamp(new_content, span.entry_id))
            else:
                result_parts.append(existing_body[span.start : span.end])
    return "\n\n".join(p for p in result_parts if p)


def rewrite_section(
    existing_body: str,
    new_content: str | None = None,
    entry_id: str | None = None,
    replace: bool = False,
    reason: str | None = None,
    added_date: str = "0000-00-00",
) -> str:
    """Orchestrate section content modifications using entry blocks.

    Returns:
        Modified section body string.

    Raises:
        ValueError: If ``replace=True`` but ``reason`` is not provided.
        EntryNotFoundError: If ``entry_id`` matches no entry in ``existing_body``.
    """
    spans = find_entry_spans(existing_body)
    is_legacy = not spans and bool(existing_body.strip())

    if replace:
        if not reason:
            msg = "reason is required when replace=True"
            raise ValueError(msg)
        return _rewrite_replace(existing_body, spans, is_legacy, new_content, reason, added_date)

    if entry_id:
        return _rewrite_by_entry_id(existing_body, spans, is_legacy, new_content, entry_id, added_date)

    # Default: append
    parts: list[str] = []
    if is_legacy:
        parts.append(wrap_entry_with_timestamp(existing_body.strip(), f"{added_date}T00:00:00Z"))
    elif existing_body.strip():
        parts.append(existing_body.strip())

    if new_content:
        parts.append(wrap_entry(new_content))

    return "\n\n".join(parts)


def _render_entry_raw(entry: Entry) -> str:
    """Reconstruct the raw HTML entry block from a parsed Entry.

    Used when the original ``raw`` text is not available (e.g. entries parsed
    from YAML structured data or after round-tripping through the model).

    Returns:
        HTML div block string equivalent to the original source text.
    """
    if entry.struck:
        inner = (
            f"<details><summary>struck: {entry.struck_at} — {entry.struck_reason}</summary>"
            f"\n\n{entry.content}\n</details>"
        )
    else:
        inner = entry.content
    return f"<div><sub>{entry.id}</sub>\n\n{inner}\n</div>"


def generate_diff(local: str, remote: str) -> str:
    """Generate a git-diff style comparison of entry blocks between local and remote.

    Returns:
        Multi-line string with ``- `` / ``+ `` / ``  `` prefixes per line.
    """
    local_entries = {e.id: e for e in parse_entries(local, show="all")}
    remote_entries = {e.id: e for e in parse_entries(remote, show="all")}

    all_ids = sorted(set(local_entries) | set(remote_entries))
    lines: list[str] = []

    for eid in all_ids:
        local_e = local_entries.get(eid)
        remote_e = remote_entries.get(eid)

        if local_e and remote_e:
            local_raw = _render_entry_raw(local_e)
            remote_raw = _render_entry_raw(remote_e)
            if local_raw == remote_raw:
                lines.extend(f"  {line}" for line in local_raw.splitlines())
            else:
                lines.extend(f"- {line}" for line in local_raw.splitlines())
                lines.extend(f"+ {line}" for line in remote_raw.splitlines())
        elif local_e:
            lines.extend(f"- {line}" for line in _render_entry_raw(local_e).splitlines())
        elif remote_e:
            lines.extend(f"+ {line}" for line in _render_entry_raw(remote_e).splitlines())

    return "\n".join(lines)
