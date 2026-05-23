# Invented Limit Patterns — Full Taxonomy

Patterns that indicate a hard-coded truncation or length limit. Each is a violation of the
No Invented Limits rule. Source: `.claude/CLAUDE.md §No Invented Limits`.

Last verified: 2026-05-22.

---

## Python Slice Truncation

```python
# VIOLATION — silently drops content past index 500
return content[:500]
return body[:200]
output = text[:MAX_PREVIEW]
```

**Why it fails**: The consumer receives incomplete data with no indication that truncation occurred.

**Correct form**:

```python
return content  # caller controls display limit
```

Or with explicit pagination:

```python
def get_content(offset: int = 0, limit: int | None = None) -> str:
    if limit is None:
        return content[offset:]
    return content[offset:offset + limit]
```

---

## Hard-Coded Constants

```python
# VIOLATION
MAX_LEN = 1024
MAX_DESCRIPTION_LENGTH = 500
PREVIEW_CHARS = 200
TRUNCATE_AT = 256

body = body[:MAX_LEN]
description = description[:MAX_DESCRIPTION_LENGTH]
```

**Why it fails**: The constant name suggests intentional design, but the value is arbitrary
and removes the caller's ability to request the full content.

**Correct form**: Accept `max_length: int | None = None` as a parameter, defaulting to None
(no limit). Let callers pass a limit when display context requires it.

---

## Explicit Truncation Flags

```python
# VIOLATION
result = render(content, truncate=True)
output = format_output(data, max_lines=50, truncate_at_limit=True)
```

**Correct form**: The truncate flag should default to `False`. If a display component must
truncate, it passes `truncate=True` explicitly — the data layer never truncates by default.

---

## String Format Truncation

```python
# VIOLATION — f-string silently truncates
preview = f"{description:.100}"  # Python format spec width
label = "{:.50}".format(name)
```

**Correct form**: Pass the full string; format truncation is a display concern, not a data concern.

---

## JSON / API Response Truncation

```json
{
  "body": "The issue description is truncated after 500 characters...",
  "truncated": true
}
```

**Why it fails (when undocumented)**: Consumers that need the full body proceed with incomplete
data. A `truncated: true` flag is only acceptable when accompanied by a way to fetch the rest
(e.g., a `next_page` cursor or a `full_body_url`).

**Required contract when truncation is unavoidable**:

```json
{
  "body": "First 500 characters...",
  "truncated": true,
  "total_chars": 2847,
  "full_body_endpoint": "/issues/123/body"
}
```

---

## CLI Output Truncation

```python
# VIOLATION
print(output[:1000])
print("\n".join(lines[:50]))
```

**Correct form**: Print all output. If a pager is needed for terminal display, pipe to `less`
or accept `--limit N` as a CLI argument.

---

## Known Regex Patterns

These patterns represent documented invented-limit forms. When new patterns are discovered in the codebase, add a row to this table.

| Pattern | Category |
|---|---|
| `\[:\d+\]` | Slice truncation |
| `MAX_LEN\s*=\s*\d+` | Hard-coded constant |
| `max_length\s*=\s*\d+` | Hard-coded parameter |
| `truncate.*=.*True` | Explicit truncation flag |

---

SOURCE: `.claude/CLAUDE.md §No Invented Limits` (lines 15–29). Extracted 2026-05-22.
