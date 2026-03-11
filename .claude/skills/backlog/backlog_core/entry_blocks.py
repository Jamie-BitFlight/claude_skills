"""Entry block operations for timestamped, addressable content within backlog sections."""

from __future__ import annotations

import re

from .models import Entry
from .parsing import now_iso

ENTRY_RE = re.compile(r"<div><sub>([^<]+)</sub>\s*(.*?)</div>", re.DOTALL)
STRUCK_RE = re.compile(r"<details><summary>struck:\s*(\S+)\s*—\s*(.*?)</summary>\s*(.*?)</details>", re.DOTALL)


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
            raw=m.group(0),
        )
    return Entry(id=ts, content=inner, raw=m.group(0))


def _deduplicate_timestamps(entries: list[Entry]) -> None:
    """Suffix duplicate timestamp IDs in-place with ``-0``, ``-1``, etc."""
    seen: dict[str, int] = {}
    has_dupes: set[str] = set()
    for e in entries:
        seen[e.id] = seen.get(e.id, 0) + 1
        if seen[e.id] > 1:
            has_dupes.add(e.id)

    if has_dupes:
        counters: dict[str, int] = {}
        for e in entries:
            if e.id in has_dupes:
                idx = counters.get(e.id, 0)
                counters[e.id] = idx + 1
                e.id = f"{e.id}-{idx}"


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
        return [Entry(id=f"{added_date}T00:00:00Z", content=content, raw=section_body)]

    raw_entries = [_parse_match_to_entry(m) for m in matches]
    _deduplicate_timestamps(raw_entries)

    if since:
        raw_entries = [e for e in raw_entries if (e.id.split("Z")[0] + "Z" if "Z" in e.id else e.id) >= since]

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
        seen_counts: dict[str, int] = {}
        for m in entries_raw:
            raw_ts = m.group(1)
            seen_counts[raw_ts] = seen_counts.get(raw_ts, 0) + 1

        has_dupes = {k for k, v in seen_counts.items() if v > 1}
        counters: dict[str, int] = {}

        for m in entries_raw:
            raw_ts = m.group(1)
            if raw_ts in has_dupes:
                idx = counters.get(raw_ts, 0)
                counters[raw_ts] = idx + 1
                effective_id = f"{raw_ts}-{idx}"
            else:
                effective_id = raw_ts

            if effective_id == entry_id:
                if new_content:
                    result_parts.append(wrap_entry_with_timestamp(new_content, raw_ts))
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
            if local_e.raw == remote_e.raw:
                lines.extend(f"  {line}" for line in local_e.raw.splitlines())
            else:
                lines.extend(f"- {line}" for line in local_e.raw.splitlines())
                lines.extend(f"+ {line}" for line in remote_e.raw.splitlines())
        elif local_e:
            lines.extend(f"- {line}" for line in local_e.raw.splitlines())
        elif remote_e:
            lines.extend(f"+ {line}" for line in remote_e.raw.splitlines())

    return "\n".join(lines)
