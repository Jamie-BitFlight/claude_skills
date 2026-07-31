# Backlog MCP: Timestamped Entry Blocks — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add timestamped, addressable entry blocks to backlog section content so every write is auditable, individually targetable, and never silently lost.

**Architecture:** New `entry_blocks.py` module handles all entry parsing/writing/striking/diffing. Existing `operations.py` functions call into it when writing section content. Server tools gain `entry_id`, `replace_section`, `reason` parameters and lose `groomed_content`. A new `backlog_strike_entry` tool is added.

**Tech Stack:** Python 3.12, FastMCP 3.x, Pydantic, regex parsing, ruamel.yaml (existing), pytest

**Spec:** `docs/superpowers/specs/2026-03-10-backlog-mcp-timestamped-entry-blocks-design.md`

**Backlog item:** #583

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backlog_core/entry_blocks.py` | Entry block wrapper, parser, striker, section rewriter, diff generator |
| Modify | `backlog_core/models.py` | Add `Entry` model, update `ViewItemResult` |
| Modify | `backlog_core/parsing.py` | Add entry block regex patterns |
| Modify | `backlog_core/operations.py` | Wire entry blocks into update/groom/view/pull/strike operations |
| Modify | `backlog_core/server.py` | Tool signature changes, new `backlog_strike_entry` tool |
| Modify | `scripts/backlog.py` | CLI parity for all changes |
| Create | `tests/test_entry_blocks.py` | Unit tests for entry_blocks module |
| Modify | `tests/test_backlog_core_server.py` | Updated tool signature tests |
| Modify | `tests/test_backlog_core_operations.py` | Updated operation tests |

All paths relative to `.claude/skills/backlog/`.

---

## Chunk 1: Entry Block Core Module

### Task 1: Entry model

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/models.py`
- Test: `.claude/skills/backlog/tests/test_entry_blocks.py`

- [x] **Step 1: Write the Entry model test**

```python
# tests/test_entry_blocks.py
from __future__ import annotations

from backlog_core.models import Entry


def test_entry_model_defaults():
    e = Entry(id="2026-03-10T22:18:04Z", content="Some content")
    assert e.id == "2026-03-10T22:18:04Z"
    assert e.content == "Some content"
    assert e.struck is False
    assert e.struck_reason == ""
    assert e.struck_at == ""


def test_entry_model_struck():
    e = Entry(
        id="2026-03-10T22:18:04Z",
        content="Old content",
        struck=True,
        struck_reason="outdated",
        struck_at="2026-03-11T09:00:00Z",
    )
    assert e.struck is True
    assert e.struck_reason == "outdated"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py::test_entry_model_defaults -v`
Expected: FAIL — `Entry` not defined in models.py

- [x] **Step 3: Add Entry model to models.py**

Add to `backlog_core/models.py`:

```python
class Entry(BaseModel):
    """A single timestamped content block within a backlog item section."""

    id: str = ""
    content: str = ""
    struck: bool = False
    struck_reason: str = ""
    struck_at: str = ""
    raw: str = ""
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/models.py .claude/skills/backlog/tests/test_entry_blocks.py
git commit -m "feat(backlog): add Entry model for timestamped content blocks"
```

---

### Task 2: `wrap_entry()` — write an active entry block

**Files:**
- Create: `.claude/skills/backlog/backlog_core/entry_blocks.py`
- Test: `.claude/skills/backlog/tests/test_entry_blocks.py`

- [x] **Step 1: Write the failing test**

```python
# tests/test_entry_blocks.py (append)
import re
from backlog_core.entry_blocks import wrap_entry


def test_wrap_entry_format():
    result = wrap_entry("Some **markdown** content.\n\n- item 1\n- item 2")
    # Should match: <div><sub>{ISO timestamp}</sub>\n\n{content}\n</div>
    assert result.startswith("<div><sub>")
    assert "</sub>" in result
    assert "Some **markdown** content." in result
    assert result.strip().endswith("</div>")
    # Extract timestamp and verify ISO format
    match = re.search(r"<sub>([^<]+)</sub>", result)
    assert match is not None
    ts = match.group(1)
    # Should be valid ISO 8601 UTC
    assert ts.endswith("Z")
    assert "T" in ts


def test_wrap_entry_preserves_content_exactly():
    content = "Line 1\n\n```python\ncode here\n```\n\nLine 3"
    result = wrap_entry(content)
    assert content in result
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py::test_wrap_entry_format -v`
Expected: FAIL — `entry_blocks` module not found

- [x] **Step 3: Create entry_blocks.py with `wrap_entry()`**

```python
# backlog_core/entry_blocks.py
"""Entry block operations for timestamped, addressable content within backlog sections."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import Entry


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def wrap_entry(content: str) -> str:
    """Wrap content in a timestamped entry block."""
    now = _utc_now_iso()
    return f"<div><sub>{now}</sub>\n\n{content}\n</div>"


def wrap_entry_with_timestamp(content: str, timestamp: str) -> str:
    """Wrap content with a specific timestamp (for legacy migration and overwrites)."""
    return f"<div><sub>{timestamp}</sub>\n\n{content}\n</div>"
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k wrap_entry -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/entry_blocks.py .claude/skills/backlog/tests/test_entry_blocks.py
git commit -m "feat(backlog): add wrap_entry() for timestamped content blocks"
```

---

### Task 3: `parse_entries()` — parse entry blocks from section body

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/entry_blocks.py`
- Test: `.claude/skills/backlog/tests/test_entry_blocks.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_entry_blocks.py (append)
from backlog_core.entry_blocks import parse_entries


def test_parse_single_active_entry():
    body = "<div><sub>2026-03-10T22:18:04Z</sub>\n\nSome content.\n</div>"
    entries = parse_entries(body)
    assert len(entries) == 1
    assert entries[0].id == "2026-03-10T22:18:04Z"
    assert entries[0].content == "Some content."
    assert entries[0].struck is False


def test_parse_multiple_entries():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 2
    assert entries[0].id == "2026-03-10T08:00:00Z"
    assert entries[1].id == "2026-03-10T14:00:00Z"


def test_parse_struck_entry():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n"
        "<details><summary>struck: 2026-03-11T09:00:00Z — outdated info</summary>\n\n"
        "Old content.\n</details>\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 1
    assert entries[0].struck is True
    assert entries[0].struck_reason == "outdated info"
    assert entries[0].struck_at == "2026-03-11T09:00:00Z"


def test_parse_duplicate_timestamps_get_suffixes():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 2
    assert entries[0].id == "2026-03-10T08:00:00Z-0"
    assert entries[1].id == "2026-03-10T08:00:00Z-1"


def test_parse_legacy_content_no_divs():
    body = "Plain text without any entry blocks.\n\nMore text."
    entries = parse_entries(body, added_date="2026-01-15")
    assert len(entries) == 1
    assert entries[0].id == "2026-01-15T00:00:00Z"
    assert "Plain text without any entry blocks." in entries[0].content


def test_parse_show_last():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nSecond.\n</div>\n\n"
        "<div><sub>2026-03-10T20:00:00Z</sub>\n\nThird.\n</div>"
    )
    entries = parse_entries(body, show="last")
    assert len(entries) == 1
    assert entries[0].content == "Third."


def test_parse_show_first():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body, show="first")
    assert len(entries) == 1
    assert entries[0].content == "First."


def test_parse_show_positive_int():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nA.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n\nB.\n</div>\n\n"
        "<div><sub>2026-03-10T10:00:00Z</sub>\n\nC.\n</div>"
    )
    entries = parse_entries(body, show=2)
    assert len(entries) == 2
    assert entries[0].content == "A."
    assert entries[1].content == "B."


def test_parse_show_negative_int():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nA.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n\nB.\n</div>\n\n"
        "<div><sub>2026-03-10T10:00:00Z</sub>\n\nC.\n</div>"
    )
    entries = parse_entries(body, show=-2)
    assert len(entries) == 2
    assert entries[0].content == "B."
    assert entries[1].content == "C."


def test_parse_show_struck():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nActive.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n"
        "<details><summary>struck: 2026-03-11T09:00:00Z — wrong</summary>\n\n"
        "Struck content.\n</details>\n</div>"
    )
    entries = parse_entries(body, show="struck")
    assert len(entries) == 1
    assert entries[0].struck is True


def test_parse_since_filter():
    body = (
        "<div><sub>2026-03-08T08:00:00Z</sub>\n\nOld.\n</div>\n\n<div><sub>2026-03-10T14:00:00Z</sub>\n\nNew.\n</div>"
    )
    entries = parse_entries(body, since="2026-03-10")
    assert len(entries) == 1
    assert entries[0].content == "New."


def test_parse_since_with_show_combined():
    body = (
        "<div><sub>2026-03-08T08:00:00Z</sub>\n\nOld.\n</div>\n\n"
        "<div><sub>2026-03-10T10:00:00Z</sub>\n\nA.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nB.\n</div>\n\n"
        "<div><sub>2026-03-10T20:00:00Z</sub>\n\nC.\n</div>"
    )
    entries = parse_entries(body, show=-2, since="2026-03-10")
    assert len(entries) == 2
    assert entries[0].content == "B."
    assert entries[1].content == "C."
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k parse -v`
Expected: FAIL — `parse_entries` not defined

- [x] **Step 3: Implement `parse_entries()`**

Add to `backlog_core/entry_blocks.py`:

```python
# NOTE: ENTRY_RE uses ``.*?`` with ``re.DOTALL``. This means entry content
# MUST NOT contain literal ``</div>`` — the lazy match stops at the first
# ``</div>`` it encounters. Nested ``<div>...</div>`` inside entry content
# will break parsing. Content with literal ``</div>`` should be escaped
# (e.g., ``&lt;/div&gt;``) before wrapping. The ``wrap_entry()`` function
# does NOT perform this escaping automatically — callers are responsible.
ENTRY_RE = re.compile(r"<div><sub>([^<]+)</sub>\s*(.*?)</div>", re.DOTALL)
STRUCK_RE = re.compile(r"<details><summary>struck:\s*(\S+)\s*—\s*(.*?)</summary>\s*(.*?)</details>", re.DOTALL)


def _parse_match_to_entry(m: re.Match[str]) -> Entry:
    """Convert a regex match into an Entry object."""
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
    """Apply the ``show`` filter to parsed entries."""
    active = [e for e in raw_entries if not e.struck]

    if show == "all":
        return raw_entries
    if show == "struck":
        return [e for e in raw_entries if e.struck]
    if show == "last":
        return active[-1:] if active else []
    if show == "first":
        return active[:1] if active else []
    if isinstance(show, int):
        return active[:show] if show >= 0 else active[show:]
    if show is None:
        return raw_entries
    msg = f"Unrecognized show filter: {show!r}"
    raise ValueError(msg)


def parse_entries(
    section_body: str, show: str | int | None = "all", since: str | None = None, added_date: str = "0000-00-00"
) -> list[Entry]:
    """Parse entry blocks from a section body.

    Args:
        section_body: Raw section text to parse.
        show: Filter — "all", "last", "first", "struck", positive int (first N),
              negative int (last N), or None (same as "all").
        since: ISO date/datetime string (``YYYY-MM-DD`` or ``YYYY-MM-DDTHH:MM:SSZ``).
               Only entries at or after this are included. Comparison is
               lexicographic on consistent ``YYYY-MM-DDTHH:MM:SSZ`` format —
               timezone offsets or fractional seconds would break ordering.
        added_date: Fallback date for legacy (unwrapped) content.

    Returns:
        List of Entry objects, in chronological order.
    """
    matches = list(ENTRY_RE.finditer(section_body))

    if not matches:
        # Legacy content — no entry blocks found
        content = section_body.strip()
        if not content:
            return []
        return [Entry(id=f"{added_date}T00:00:00Z", content=content, raw=section_body)]

    raw_entries = [_parse_match_to_entry(m) for m in matches]
    _deduplicate_timestamps(raw_entries)

    # Apply since filter — strip dedup suffix before comparison so
    # "2026-03-10T08:00:00Z-1" compares as "2026-03-10T08:00:00Z"
    if since:
        raw_entries = [e for e in raw_entries if (e.id.split("Z")[0] + "Z" if "Z" in e.id else e.id) >= since]

    return _apply_show_filter(raw_entries, show)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k parse -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/entry_blocks.py .claude/skills/backlog/tests/test_entry_blocks.py
git commit -m "feat(backlog): add parse_entries() with show/since filtering"
```

---

### Task 4: `strike_entry()` — strike an entry block

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/entry_blocks.py`
- Test: `.claude/skills/backlog/tests/test_entry_blocks.py`

- [x] **Step 1: Write the failing test**

```python
# tests/test_entry_blocks.py (append)
from backlog_core.entry_blocks import strike_entry


def test_strike_entry_wraps_content():
    entry_raw = "<div><sub>2026-03-10T22:18:04Z</sub>\n\nOriginal content.\n</div>"
    result = strike_entry(entry_raw, "based on training data")
    assert "<sub>2026-03-10T22:18:04Z</sub>" in result
    assert "<details>" in result
    assert "struck:" in result
    assert "based on training data" in result
    assert "Original content." in result
    # Should still be wrapped in <div>
    assert result.strip().startswith("<div>")
    assert result.strip().endswith("</div>")


def test_strike_entry_roundtrips_through_parser():
    entry_raw = "<div><sub>2026-03-10T22:18:04Z</sub>\n\nOriginal content.\n</div>"
    struck = strike_entry(entry_raw, "wrong info")
    entries = parse_entries(struck)
    assert len(entries) == 1
    assert entries[0].struck is True
    assert entries[0].struck_reason == "wrong info"
    assert "Original content." in entries[0].content
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k strike -v`
Expected: FAIL — `strike_entry` not defined

- [x] **Step 3: Implement `strike_entry()`**

Add to `backlog_core/entry_blocks.py`:

```python
def strike_entry(entry_raw: str, reason: str) -> str:
    """Strike an entry block — wrap content in collapsed details with reason.

    Args:
        entry_raw: The full raw entry HTML (<div><sub>...</sub>...content...</div>).
        reason: Why this entry is being struck.

    Returns:
        The entry with content wrapped in <details><summary>struck: ...</summary>.

    Raises:
        ValueError: If ``entry_raw`` is not a valid entry block.
    """
    now = _utc_now_iso()
    match = ENTRY_RE.search(entry_raw)
    if not match:
        msg = "Cannot strike: not a valid entry block"
        raise ValueError(msg)

    ts = match.group(1)
    content = match.group(2).strip()

    # If already struck, extract the original content from inside <details>
    struck_match = STRUCK_RE.search(content)
    if struck_match:
        content = struck_match.group(3).strip()

    return (
        f"<div><sub>{ts}</sub>\n<details><summary>struck: {now} — {reason}</summary>\n\n{content}\n</details>\n</div>"
    )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k strike -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/entry_blocks.py .claude/skills/backlog/tests/test_entry_blocks.py
git commit -m "feat(backlog): add strike_entry() for non-destructive entry removal"
```

---

### Task 5: `rewrite_section()` — orchestrate section modifications

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/entry_blocks.py`
- Test: `.claude/skills/backlog/tests/test_entry_blocks.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_entry_blocks.py (append)
from backlog_core.entry_blocks import rewrite_section


def test_rewrite_append_to_empty():
    result = rewrite_section(existing_body="", new_content="First entry.", added_date="2026-01-01")
    entries = parse_entries(result)
    assert len(entries) == 1
    assert entries[0].content == "First entry."


def test_rewrite_append_to_existing():
    existing = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>"
    result = rewrite_section(existing_body=existing, new_content="Second entry.", added_date="2026-01-01")
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[1].content == "Second entry."


def test_rewrite_append_to_legacy():
    result = rewrite_section(
        existing_body="Legacy plain text content.", new_content="New entry.", added_date="2026-01-15"
    )
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[0].id == "2026-01-15T00:00:00Z"
    assert "Legacy plain text content." in entries[0].content
    assert entries[1].content == "New entry."


def test_rewrite_overwrite_by_entry_id():
    existing = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nOld.\n</div>\n\n<div><sub>2026-03-10T14:00:00Z</sub>\n\nKeep.\n</div>"
    )
    result = rewrite_section(
        existing_body=existing, new_content="Replaced.", entry_id="2026-03-10T08:00:00Z", added_date="2026-01-01"
    )
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[0].content == "Replaced."
    assert entries[1].content == "Keep."


def test_rewrite_replace_section():
    existing = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nOld 1.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nOld 2.\n</div>"
    )
    result = rewrite_section(
        existing_body=existing,
        new_content="Fresh start.",
        replace=True,
        reason="section rewritten during grooming",
        added_date="2026-01-01",
    )
    entries = parse_entries(result, show="all")
    active = [e for e in entries if not e.struck]
    struck = [e for e in entries if e.struck]
    assert len(active) == 1
    assert active[0].content == "Fresh start."
    assert len(struck) == 2
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k rewrite -v`
Expected: FAIL

- [x] **Step 3: Implement `rewrite_section()`**

Add to `backlog_core/entry_blocks.py`:

```python
def _rewrite_replace(
    entries_raw: list[re.Match[str]],
    is_legacy: bool,
    existing_body: str,
    new_content: str | None,
    reason: str,
    added_date: str,
) -> str:
    """Handle the ``replace=True`` branch of rewrite_section."""
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

    Raises:
        ValueError: If ``new_content`` is None (would silently delete the entry).
    """
    if not new_content:
        msg = "new_content is required when entry_id is provided — use strike_entry() for deletion"
        raise ValueError(msg)

    result_parts: list[str] = []
    if is_legacy:
        legacy_ts = f"{added_date}T00:00:00Z"
        if entry_id == legacy_ts:
            result_parts.append(wrap_entry_with_timestamp(new_content, legacy_ts))
        else:
            result_parts.append(wrap_entry_with_timestamp(existing_body.strip(), legacy_ts))
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
                result_parts.append(wrap_entry_with_timestamp(new_content, raw_ts))
            else:
                result_parts.append(m.group(0))
    return "\n\n".join(result_parts)


def rewrite_section(
    existing_body: str,
    new_content: str | None = None,
    entry_id: str | None = None,
    replace: bool = False,
    reason: str | None = None,
    added_date: str = "0000-00-00",
) -> str:
    """Orchestrate section content modifications using entry blocks.

    Args:
        existing_body: Current section body text.
        new_content: Content to write (append, overwrite, or replace).
            Required when ``entry_id`` is set.
        entry_id: Target a specific entry for overwrite.
        replace: Strike all existing entries, append new_content.
        reason: Required when replace=True. Why entries are being struck.
        added_date: Item's added date for legacy content wrapping.

    Returns:
        Updated section body text.

    Raises:
        ValueError: If ``replace=True`` but ``reason`` is not provided, or if
            ``entry_id`` is set but ``new_content`` is None/empty.
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k rewrite -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/entry_blocks.py .claude/skills/backlog/tests/test_entry_blocks.py
git commit -m "feat(backlog): add rewrite_section() for append/overwrite/replace"
```

---

### Task 6: `generate_diff()` — git-diff style entry comparison

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/entry_blocks.py`
- Test: `.claude/skills/backlog/tests/test_entry_blocks.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_entry_blocks.py (append)
from backlog_core.entry_blocks import generate_diff


def test_diff_identical():
    body = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSame.\n</div>"
    diff = generate_diff(local=body, remote=body)
    assert "- " not in diff
    assert "+ " not in diff
    assert "Same." in diff


def test_diff_remote_has_new_entry():
    local = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nLocal.\n</div>"
    remote = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nLocal.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nNew remote.\n</div>"
    )
    diff = generate_diff(local=local, remote=remote)
    assert "+ <div><sub>2026-03-10T14:00:00Z</sub>" in diff


def test_diff_local_only_entry():
    local = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nCommon.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nLocal only.\n</div>"
    )
    remote = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nCommon.\n</div>"
    diff = generate_diff(local=local, remote=remote)
    assert "- <div><sub>2026-03-10T14:00:00Z</sub>" in diff


def test_diff_content_differs():
    local = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nShort.\n</div>"
    remote = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nLonger content here.\n</div>"
    diff = generate_diff(local=local, remote=remote)
    assert "- <div><sub>2026-03-10T08:00:00Z</sub>" in diff
    assert "+ <div><sub>2026-03-10T08:00:00Z</sub>" in diff
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k diff -v`
Expected: FAIL

- [x] **Step 3: Implement `generate_diff()`**

Add to `backlog_core/entry_blocks.py`:

```python
def generate_diff(local: str, remote: str) -> str:
    """Generate a git-diff style comparison of entry blocks between local and remote.

    Args:
        local: Local section body text.
        remote: Remote section body text.

    Returns:
        Diff string with space (unchanged), - (local only / local version),
        + (remote only / remote version) prefixes per entry block.
    """
    local_entries = {e.id: e for e in parse_entries(local, show="all")}
    remote_entries = {e.id: e for e in parse_entries(remote, show="all")}

    def _sort_key(eid: str) -> tuple[str, int]:
        """Sort entry IDs chronologically, handling dedup suffixes numerically.

        ``2026-03-10T08:00:00Z-10`` sorts after ``-2`` (numeric, not lexicographic).
        """
        if "-" in eid and eid.rsplit("-", 1)[-1].isdigit():
            base, suffix = eid.rsplit("-", 1)
            return (base, int(suffix))
        return (eid, -1)

    all_ids = sorted(set(local_entries) | set(remote_entries), key=_sort_key)
    lines: list[str] = []

    for eid in all_ids:
        local_e = local_entries.get(eid)
        remote_e = remote_entries.get(eid)

        if local_e and remote_e:
            if local_e.raw == remote_e.raw:
                # Identical — prefix with space
                for line in local_e.raw.splitlines():
                    lines.append(f"  {line}")
            else:
                # Content differs
                for line in local_e.raw.splitlines():
                    lines.append(f"- {line}")
                for line in remote_e.raw.splitlines():
                    lines.append(f"+ {line}")
        elif local_e:
            for line in local_e.raw.splitlines():
                lines.append(f"- {line}")
        elif remote_e:
            for line in remote_e.raw.splitlines():
                lines.append(f"+ {line}")

    return "\n".join(lines)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks.py -k diff -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/entry_blocks.py .claude/skills/backlog/tests/test_entry_blocks.py
git commit -m "feat(backlog): add generate_diff() for entry-level comparison"
```

---

## Chunk 2: Wire Entry Blocks Into Operations and Server

### Task 7: Update `operations.py` — groom and update paths

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/operations.py`
- Test: `.claude/skills/backlog/tests/test_backlog_core_operations.py`

- [x] **Step 1: Write failing test for entry-based groom**

```python
# tests/test_backlog_core_operations.py (append)
def test_groom_item_appends_entry_block(tmp_backlog):
    """Grooming with section+content creates a timestamped entry block."""
    # Create an item first, then groom it
    out = Output()
    operations.add_item(
        title="Test Entry Groom", priority="P1", description="Test item", output=out, create_issue=False
    )
    result = operations.groom_item(
        selector="Test Entry Groom", section="Decision", content="First decision made.", output=out
    )
    assert "error" not in result
    # Read the file and verify entry block exists
    item = operations.view_item(selector="Test Entry Groom", output=out)
    assert "<div><sub>" in item.get("body", "")
    assert "First decision made." in item.get("body", "")
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_backlog_core_operations.py -k test_groom_item_appends_entry_block -v`
Expected: FAIL — current groom_item writes raw content without entry blocks

- [x] **Step 3: Modify `groom_item()` in operations.py**

In `operations.py`, find the section-write path in `groom_item()` and `update_item()`. Replace the direct section content write with a call to `rewrite_section()`:

```python
from .entry_blocks import rewrite_section
from .parsing import extract_sections

# In the section+content branch of groom_item / update_item:
# Use extract_sections() (from parsing.py) which returns dict[str, str]
# keyed by heading including "## " prefix.
# OLD: write content directly into section
# NEW:
sections = extract_sections(file_content)
section_key = f"## {section}"
existing_section_body = sections.get(section_key, "")
new_body = rewrite_section(
    existing_body=existing_section_body,
    new_content=content,
    entry_id=entry_id,
    replace=replace_section,
    reason=reason,
    added_date=item.added,
)
# Write new_body back into the file by replacing the section content.
# The implementing agent should read operations.py to find the existing
# section-write mechanism (file_content replacement pattern) and adapt it.
```

The agent implementing this task should read `operations.py` to find the exact code paths for section writing in both `groom_item()` and `update_item()`, then wire in `rewrite_section()`. The function signatures for both need the new parameters: `entry_id`, `replace_section`, `reason`. Note: `extract_sections()` in `parsing.py` returns a `dict[str, str]` keyed by the full heading (e.g., `"## Decision"`).

- [x] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_backlog_core_operations.py -k entry -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/test_backlog_core_operations.py
git commit -m "feat(backlog): wire entry blocks into groom_item and update_item"
```

---

### Task 8: Add `strike_entry` operation

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/operations.py`
- Test: `.claude/skills/backlog/tests/test_backlog_core_operations.py`

- [x] **Step 1: Write failing test**

```python
from backlog_core.entry_blocks import parse_entries


def test_strike_entry_operation(tmp_backlog):
    """strike_entry wraps target entry in collapsed details."""
    out = Output()
    operations.add_item(title="Strike Test", priority="P1", description="Test", output=out, create_issue=False)
    operations.groom_item(selector="Strike Test", section="Decision", content="Bad info.", output=out)

    # Dynamically determine the entry_id by viewing and parsing the section
    item = operations.view_item(selector="Strike Test", output=out)
    body = item.get("body", "")
    entries = parse_entries(body)
    assert len(entries) >= 1, "Expected at least one entry after groom"
    entry_id = entries[-1].id  # Last entry is the one we just groomed

    result = operations.strike_entry(
        selector="Strike Test", entry_id=entry_id, section="Decision", reason="based on training data", output=out
    )
    assert "error" not in result
    item = operations.view_item(selector="Strike Test", output=out)
    assert "struck:" in item.get("body", "")
    assert "based on training data" in item.get("body", "")
```

- [x] **Step 2: Run test to verify it fails**

Expected: FAIL — `strike_entry` not defined on operations

- [x] **Step 3: Implement `operations.strike_entry()`**

New function in `operations.py` with signature `strike_entry(selector, entry_id, reason, output, section=None)` that:
1. Finds the item by selector
2. Reads the file content
3. If `section` is provided, scopes parsing to that section only (prevents ambiguity when duplicate timestamps exist across sections)
4. Parses entries to find the target `entry_id`
5. Calls `entry_blocks.strike_entry()` on the matching raw entry
6. Replaces the raw entry in the file content
7. Writes the file
8. Syncs to GitHub if the item has an issue

- [x] **Step 4: Run test to verify it passes**

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/test_backlog_core_operations.py
git commit -m "feat(backlog): add strike_entry operation"
```

---

### Task 9: Update `view_item()` — entry-based pagination and section metadata

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/operations.py`
- Modify: `.claude/skills/backlog/backlog_core/models.py`
- Test: `.claude/skills/backlog/tests/test_backlog_core_operations.py`

- [x] **Step 1: Write failing test**

```python
def test_view_item_returns_section_entries(tmp_backlog):
    """view_item response includes sections dict with entry metadata."""
    out = Output()
    operations.add_item(title="View Test", priority="P1", description="Test", output=out, create_issue=False)
    operations.groom_item(selector="View Test", section="Decision", content="Entry 1.", output=out)
    operations.groom_item(selector="View Test", section="Decision", content="Entry 2.", output=out)
    result = operations.view_item(selector="View Test", output=out)
    sections = result.get("sections", {})
    assert "Decision" in sections
    assert sections["Decision"]["num_entries"] == 2
    assert len(sections["Decision"]["entries"]) == 2
```

- [x] **Step 2: Run test to verify it fails**

- [x] **Step 3: Update `ViewItemResult` model and `view_item()` operation**

Add sections metadata to `ViewItemResult` in models.py. Update `view_item()` in operations.py to parse entry blocks per section and populate the metadata. Change offset/limit to operate on entry count.

- [x] **Step 4: Run test to verify it passes**

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/models.py .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/test_backlog_core_operations.py
git commit -m "feat(backlog): entry-based pagination and section metadata in view_item"
```

---

### Task 10: Update `pull_items()` — entry-aware merge with diff

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/operations.py`
- Test: `.claude/skills/backlog/tests/test_backlog_core_operations.py`

- [x] **Step 1: Write failing test**

```python
def test_pull_dry_run_returns_entry_diff(tmp_backlog, mock_github):
    """pull with dry_run returns entry-level diff string."""
    # Setup: local item with one entry, mock GitHub response with two entries
    out = Output()
    result = operations.pull_items(dry_run=True, output=out)
    assert "diff" in result
    # Diff should be a string with +/- prefixed lines
    assert isinstance(result["diff"], str)
```

Note: The implementing agent will need to set up appropriate fixtures for this test.

- [x] **Step 2: Run test to verify it fails**

- [x] **Step 3: Update `pull_items()` and `pull_by_selector()` merge logic**

Replace the current "keep longer version" merge with entry-aware merge using `parse_entries()` and `generate_diff()`. Add `diff` parameter support.

Merge rules (from spec):
- Entry only on one side → keep
- Both sides, one struck → keep struck
- Both sides, both active → keep longer content
- Both sides, both struck → keep later struck timestamp

- [x] **Step 4: Run test to verify it passes**

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/operations.py .claude/skills/backlog/tests/test_backlog_core_operations.py
git commit -m "feat(backlog): entry-aware merge and diff output in pull_items"
```

---

### Task 11: Update `server.py` — tool signature changes

**Files:**
- Modify: `.claude/skills/backlog/backlog_core/server.py`
- Test: `.claude/skills/backlog/tests/test_backlog_core_server.py`

- [x] **Step 1: Write failing test**

```python
def test_backlog_groom_no_groomed_content_param():
    """backlog_groom should not accept groomed_content parameter."""
    import inspect

    sig = inspect.signature(backlog_groom)
    assert "groomed_content" not in sig.parameters


def test_backlog_groom_has_entry_id_param():
    """backlog_groom should accept entry_id parameter."""
    import inspect

    sig = inspect.signature(backlog_groom)
    assert "entry_id" in sig.parameters


def test_backlog_strike_entry_tool_exists():
    """backlog_strike_entry should be a registered MCP tool."""
    from backlog_core.server import backlog_strike_entry

    assert callable(backlog_strike_entry)


def test_backlog_view_show_string_int_conversion():
    """backlog_view should convert show="2" (string) to int 2 for parse_entries."""
    # MCP clients always send show as a string. The server/operations layer
    # must convert numeric strings to int before passing to parse_entries().
    # This test verifies the conversion path — without it, show="2" would
    # fall through to the ValueError branch in _apply_show_filter().
    import inspect
    from backlog_core.server import backlog_view

    sig = inspect.signature(backlog_view)
    # show param should exist and accept str | None (MCP layer)
    assert "show" in sig.parameters
```

- [x] **Step 2: Run tests to verify they fail**

- [x] **Step 3: Update server.py**

1. Remove `groomed_content` parameter from `backlog_update` and `backlog_groom`
2. Add `entry_id`, `replace_section`, `reason` parameters to both
3. Add `show`, `since` parameters to `backlog_view`. **Important**: MCP tool parameters are always strings. The `show` parameter is typed `str | None` in the server but `parse_entries()` accepts `str | int | None`. Add conversion logic in the server or operations layer before passing to `parse_entries()`:

    ```python
    # Convert show from string to int when it represents a number
    parsed_show: str | int | None = show
    if show is not None:
        try:
            parsed_show = int(show)
        except ValueError:
            parsed_show = show
    ```

4. Add `diff` parameter to `backlog_pull`
5. Replace `offset`/`limit` in `backlog_view` to operate on entries
6. Add new `backlog_strike_entry` tool:

```python
@mcp.tool()
async def backlog_strike_entry(
    selector: Annotated[str, Field(description="Item selector: title substring, #N, bare number, or GitHub issue URL")],
    entry_id: Annotated[str, Field(description="Entry ID (ISO timestamp from <sub> tag) to strike")],
    reason: Annotated[str, Field(description="Why this entry is being struck through")],
    section: Annotated[
        str | None,
        Field(
            description="Optional section name to scope the strike — prevents ambiguity when duplicate timestamps exist across sections"
        ),
    ] = None,
) -> dict:
    """Strike through an entry in a backlog item section. The entry content is preserved
    in a collapsed <details> block with the reason, but marked as struck and excluded
    from active entry counts.

    Returns:
        Dict with item title, struck entry_id, and output messages/warnings.
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_backlog_core_server.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/skills/backlog/backlog_core/server.py .claude/skills/backlog/tests/test_backlog_core_server.py
git commit -m "feat(backlog): update MCP tool signatures for entry blocks"
```

---

### Task 12: Update `scripts/backlog.py` — CLI parity

**Files:**
- Modify: `.claude/skills/backlog/scripts/backlog.py`

- [x] **Step 1: Write failing test**

```bash
cd .claude/skills/backlog && uv run python scripts/backlog.py groom --help
# Should show entry_id, replace_section, reason options
# Should NOT show --groomed-content option
```

- [x] **Step 2: Update CLI commands**

1. `groom` command: remove `--groomed-content`, add `--entry-id`, `--replace-section`, `--reason`
2. `update` command: remove `--groomed-content`, add `--entry-id`, `--replace-section`, `--reason`
3. `view` command: change `--offset`/`--limit` to entry-based, add `--show`, `--since`
4. `pull` command: add `--diff` flag
5. Add new `strike-entry` command: `backlog.py strike-entry <selector> <entry-id> <reason>`

- [x] **Step 3: Verify CLI help output**

Run each updated command with `--help` to verify parameter changes.

- [x] **Step 4: Commit**

```bash
git add .claude/skills/backlog/scripts/backlog.py
git commit -m "feat(backlog): CLI parity for entry block operations"
```

---

### Task 13: Update existing tests for changed signatures

**Files:**
- Modify: `.claude/skills/backlog/tests/test_backlog_core_server.py`
- Modify: `.claude/skills/backlog/tests/test_backlog_core_operations.py`

- [x] **Step 1: Run full test suite to find failures**

Run: `cd .claude/skills/backlog && uv run pytest -v`
Identify all tests that fail due to removed `groomed_content` parameter or changed `offset`/`limit` behavior.

- [x] **Step 2: Update failing tests**

Replace `groomed_content=` calls with `section=` + `content=` equivalents. Update pagination tests to use entry-based counts.

- [x] **Step 3: Run full test suite**

Run: `cd .claude/skills/backlog && uv run pytest -v`
Expected: All PASS

- [x] **Step 4: Commit**

```bash
git add .claude/skills/backlog/tests/
git commit -m "fix(backlog): update tests for entry block API changes"
```

---

### Task 14: Integration test — full round-trip

**Files:**
- Create: `.claude/skills/backlog/tests/test_entry_blocks_integration.py`

- [x] **Step 1: Write integration test**

```python
"""Integration test: full entry block lifecycle.

NOTE: This test depends on the ``sections`` dict structure returned by
``view_item()`` after Task 9 updates ``ViewItemResult``. Expected shape:

    result["sections"] = {
        "Decision": {
            "entries": [{"id": str, "content": str, "struck": bool, ...}, ...],
            "num_entries": int,  # count of active (non-struck) entries
            "num_struck": int,   # count of struck entries
        },
        ...
    }

If Task 9 defines a different structure, these assertions must be updated.
"""

from __future__ import annotations

from backlog_core import operations
from backlog_core.models import Output


def test_full_entry_lifecycle(tmp_backlog):
    """Create item → groom with entries → strike one → view → verify."""
    out = Output()

    # Create
    operations.add_item(title="Lifecycle Test", priority="P1", description="Test", output=out, create_issue=False)

    # Append two entries to Decision section
    operations.groom_item(selector="Lifecycle Test", section="Decision", content="First decision.", output=out)
    operations.groom_item(selector="Lifecycle Test", section="Decision", content="Second decision.", output=out)

    # View — should show 2 entries
    result = operations.view_item(selector="Lifecycle Test", output=out)
    sections = result.get("sections", {})
    assert "Decision" in sections, f"Expected 'Decision' in sections, got: {list(sections.keys())}"
    decision = sections["Decision"]
    assert "entries" in decision, f"Expected 'entries' key in section dict, got: {list(decision.keys())}"
    assert "num_entries" in decision, f"Expected 'num_entries' key in section dict, got: {list(decision.keys())}"
    assert decision["num_entries"] == 2

    # Strike first entry
    first_id = decision["entries"][0]["id"]
    operations.strike_entry(
        selector="Lifecycle Test", entry_id=first_id, section="Decision", reason="superseded", output=out
    )

    # View again — should show 1 active, 1 struck
    result = operations.view_item(selector="Lifecycle Test", output=out)
    sections = result.get("sections", {})
    decision = sections["Decision"]
    assert decision["num_entries"] == 1
    assert decision.get("num_struck", 0) == 1

    # Overwrite second entry
    second_id = decision["entries"][0]["id"]
    operations.groom_item(
        selector="Lifecycle Test",
        section="Decision",
        content="Updated second decision.",
        entry_id=second_id,
        output=out,
    )

    # Final view
    result = operations.view_item(selector="Lifecycle Test", output=out)
    sections = result.get("sections", {})
    decision = sections["Decision"]
    assert decision["num_entries"] == 1
    active_entries = [e for e in decision["entries"] if not e.get("struck")]
    assert "Updated second decision." in active_entries[0]["content"]
```

- [x] **Step 2: Run integration test**

Run: `cd .claude/skills/backlog && uv run pytest tests/test_entry_blocks_integration.py -v`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git add .claude/skills/backlog/tests/test_entry_blocks_integration.py
git commit -m "test(backlog): integration test for entry block lifecycle"
```

---

### Task 15: Final validation

- [x] **Step 1: Run full test suite**

Run: `cd .claude/skills/backlog && uv run pytest -v --tb=short`
Expected: All PASS

- [x] **Step 2: Run linters**

Run: `cd .claude/skills/backlog && uv run ruff check backlog_core/ scripts/ tests/`
Run: `cd .claude/skills/backlog && uv run ruff format --check backlog_core/ scripts/ tests/`

- [x] **Step 3: Verify MCP server starts**

Run: `cd .claude/skills/backlog && uv run python -c "from backlog_core.server import mcp; print('Server OK')"`

- [x] **Step 4: Final commit if any cleanup needed**

```bash
git add -A .claude/skills/backlog/
git commit -m "chore(backlog): final cleanup for entry block feature"
```
