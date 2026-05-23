"""Entry block operations for timestamped, addressable content within backlog sections."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import Entry
from .parsing import now_iso

ENTRY_RE = re.compile(r"<div><sub>([^<]+)</sub>\s*(.*?)</div>", re.DOTALL)
STRUCK_RE = re.compile(r"<details><summary>struck:\s*(\S+)\s*—\s*(.*?)</summary>\s*(.*?)</details>", re.DOTALL)
# Matches ISO 8601 timestamps (with or without sub-second fraction) at the start of a string.
# Used in two places: detecting unwrapped seeds in the legacy entry path, and filtering
# entries by the ``since`` parameter (entry IDs may carry a dedup suffix like ``-0``, ``-1``).
_ISO_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")


def _parse_entry_timestamp(entry_id: str) -> datetime:
    """Extract the ISO timestamp prefix from an entry ID and return a UTC-aware datetime.

    Returns:
        UTC-aware datetime parsed from the ISO timestamp prefix of ``entry_id``.

    Raises:
        ValueError: If ``entry_id`` does not start with a valid ISO timestamp.
    """
    m = _ISO_TIMESTAMP_RE.match(entry_id)
    if not m:
        msg = f"Entry ID does not contain a valid ISO timestamp prefix: {entry_id!r}"
        raise ValueError(msg)
    ts = m.group(1)
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def wrap_entry(content: str) -> str:
    """Wrap content in a timestamped entry block.

    Returns:
        HTML div string with ``<sub>`` timestamp and content.
    """
    return f"<div><sub>{now_iso()}</sub>\n\n{content}\n</div>"


def wrap_entry_with_timestamp(content: str, timestamp: str) -> str:
    """Wrap content with a specific timestamp (for legacy migration and overwrites).

    Returns:
        HTML div string with the provided timestamp and content.
    """
    return f"<div><sub>{timestamp}</sub>\n\n{content}\n</div>"


def _parse_match_to_entry(m: re.Match[str]) -> Entry:
    """Convert a regex match into an Entry object.

    Returns:
        Entry parsed from the match groups.
    """
    ts = m.group(1)
    inner = m.group(2).strip()
    struck_match = STRUCK_RE.search(inner)
    if struck_match:
        return Entry(
            id=ts,
            content=struck_match.group(3).strip(),
            struck=True,
            struck_at=struck_match.group(1),
            struck_reason=struck_match.group(2).strip(),
        )
    return Entry(id=ts, content=inner)


def _resolve_duplicate_ids(entries: list[Entry]) -> int:
    """Suffix duplicate IDs in-place with ``-0``, ``-1``, etc.

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
        counters: dict[str, int] = {}
        for e in entries:
            if e.id in has_dupes:
                idx = counters.get(e.id, 0)
                counters[e.id] = idx + 1
                e.id = f"{e.id}-{idx}"
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
    matches = list(ENTRY_RE.finditer(section_body))

    if not matches:
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
        raw_entries = [_parse_match_to_entry(m) for m in matches]
        _deduplicate_timestamps(raw_entries)

    if since:
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=UTC)

        raw_entries = [e for e in raw_entries if _parse_entry_timestamp(e.id) >= since_dt]

    return _apply_show_filter(raw_entries, show)


def strike_entry(entry_raw: str, reason: str) -> str:
    """Strike an entry block — wrap content in collapsed details with reason.

    Returns:
        Struck entry block HTML string.

    Raises:
        ValueError: If ``entry_raw`` is not a valid entry block.
    """
    now = now_iso()
    match = ENTRY_RE.search(entry_raw)
    if not match:
        msg = "Cannot strike: not a valid entry block"
        raise ValueError(msg)

    ts = match.group(1)
    content = match.group(2).strip()

    struck_match = STRUCK_RE.search(content)
    if struck_match:
        content = struck_match.group(3).strip()

    return (
        f"<div><sub>{ts}</sub>\n<details><summary>struck: {now} — {reason}</summary>\n\n{content}\n</details>\n</div>"
    )


def _rewrite_replace(
    entries_raw: list[re.Match[str]],
    is_legacy: bool,
    existing_body: str,
    new_content: str | None,
    reason: str,
    added_date: str,
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
        parts.extend(strike_entry(m.group(0), reason) for m in entries_raw)
    if new_content:
        parts.append(wrap_entry(new_content))
    return "\n\n".join(parts)


def _rewrite_by_entry_id(
    entries_raw: list[re.Match[str]],
    is_legacy: bool,
    existing_body: str,
    new_content: str | None,
    entry_id: str,
    added_date: str,
) -> str:
    """Handle the ``entry_id`` branch of rewrite_section.

    Returns:
        Rewritten section body with the target entry replaced.
    """
    result_parts: list[str] = []
    if is_legacy:
        legacy_ts = f"{added_date}T00:00:00Z"
        if entry_id == legacy_ts:
            result_parts.append(wrap_entry(new_content) if new_content else "")
        else:
            result_parts.append(wrap_entry_with_timestamp(existing_body.strip(), legacy_ts))
            if new_content:
                result_parts.append(wrap_entry(new_content))
    else:
        id_entries = [Entry(id=m.group(1), content="") for m in entries_raw]
        _resolve_duplicate_ids(id_entries)

        for m, id_entry in zip(entries_raw, id_entries, strict=False):
            if id_entry.id == entry_id:
                if new_content:
                    result_parts.append(wrap_entry_with_timestamp(new_content, m.group(1)))
            else:
                result_parts.append(m.group(0))
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
    """
    entries_raw = list(ENTRY_RE.finditer(existing_body))
    is_legacy = not entries_raw and bool(existing_body.strip())

    if replace:
        if not reason:
            msg = "reason is required when replace=True"
            raise ValueError(msg)
        return _rewrite_replace(entries_raw, is_legacy, existing_body, new_content, reason, added_date)

    if entry_id:
        return _rewrite_by_entry_id(entries_raw, is_legacy, existing_body, new_content, entry_id, added_date)

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
