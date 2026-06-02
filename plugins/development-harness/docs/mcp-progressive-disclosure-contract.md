# MCP Progressive-Disclosure Contract

The `backlog_view` MCP tool exposes progressive disclosure for backlog items — a two-call
navigation protocol that lets agents browse large items incrementally, from a token-efficient
map down to full section, sub-heading, or code-fence content.

Design decisions are specified in the architecture spec for issue #2529 (artifact type
`architect`). This document describes the shipped contract — what agents observe.

---

## Ordinal Grammar

An ordinal is a dot-separated path that addresses a node within the item tree. The validation
pattern (from `disclosure_handler.py`, `_ORDINAL_PATTERN`) is:

```text
^\d+(\.\d+)*(\.code\.\d+)?$
```

Examples of accepted ordinals:

```text
"4"            level-1 section
"4.0"          level-2 entry
"4.0.1"        sub-heading (level 3+)
"4.0.1.2"      deeper sub-heading
"4.0.code.0"   code fence in the direct body of entry 4.0
"4.0.1.code.0" code fence in the direct body of sub-heading 4.0.1
```

Rules:

- All numeric segments are 0-based.
- The terminal `.code.K` suffix addresses a code fence by its 0-based position within the
  **direct body** of the parent node — not across all descendants.
- A bare `code.0` without a leading numeric path is rejected.
- `4.0.code` without an index is rejected.
- Non-numeric, non-`code` segments (e.g. `4.0.foo.0`) are rejected.

---

## Navigation Token

When a node contains code fences in its prose body, each fence is replaced by an inline
navigation token in the returned `content`:

```text
[code:{ordinal}]
```

Example — an entry at `4.0` whose body contains two fences:

```text
Install the package:

[code:4.0.code.0]

Then configure it:

[code:4.0.code.1]
```

Navigate to the ordinal in each token to retrieve the raw fence body.

---

## NavigateResponse Shape

`navigate=<ordinal>` (without `head`) returns a `NavigateResponse`
(`disclosure_types.py`, `NavigateResponse` dataclass):

| Field          | Type          | Description                                                                              |
|----------------|---------------|------------------------------------------------------------------------------------------|
| `ordinal`      | `str`         | Echoed ordinal.                                                                          |
| `title`        | `str`         | Heading text or code-block language tag.                                                 |
| `content`      | `str`         | Full body text. Empty string (`""`) when `has_children=True` (ADR-7).                   |
| `total_tokens` | `int`         | tiktoken `cl100k_base` count of `content`. `0` when `has_children=True`.                |
| `truncated`    | `bool`        | Always `False` for navigate-without-head responses.                                     |
| `child_map`    | `str \| None` | Formatted listing of direct sub-heading children. `None` for leaves and code blocks.    |
| `has_children` | `bool`        | `True` iff the node has sub-heading children (ADR-4). `False` for code-only nodes.      |

---

## Navigate-on-Parent Semantics

The handler (`disclosure_handler.py`, `_handle_navigate`) branches on `has_children`.

### Parent node (`has_children=True`)

The node has sub-heading children. `content` is an empty string — prose is accessed by
navigating to individual child ordinals.

```text
navigate="4.0"

NavigateResponse:
  ordinal:       "4.0"
  title:         "Installation"
  content:       ""
  total_tokens:  0
  truncated:     false
  has_children:  true
  child_map:     "4.0.0 | Overview | ~45 tokens\n4.0.1 | Steps | ~120 tokens\n..."
```

Read `child_map` to discover child ordinals, then navigate to a specific child.

### Leaf node (`has_children=False`, not a code block)

Full prose with inline `[code:...]` tokens substituted for any fences in the body.

```text
navigate="4.0.1"

NavigateResponse:
  ordinal:       "4.0.1"
  title:         "Steps"
  content:       "### Steps\n\nRun the following:\n\n[code:4.0.1.code.0]\n\nVerify output."
  total_tokens:  47
  truncated:     false
  has_children:  false
  child_map:     null
```

### Code-block node (`has_children=False`, code fence body)

Raw fence body — no surrounding markdown, no fence delimiters.

```text
navigate="4.0.1.code.0"

NavigateResponse:
  ordinal:       "4.0.1.code.0"
  title:         "bash"
  content:       "npm install my-package\nnpm run build"
  total_tokens:  12
  truncated:     false
  has_children:  false
  child_map:     null
```

---

## Typical Navigation Flow

```text
1. backlog_view(selector="#2529", map=true)
   → MapResponse: map_text lists ordinals at sections and entries

2. backlog_view(selector="#2529", navigate="4.0")
   → NavigateResponse
     if has_children=true  → read child_map, navigate to a child ordinal
     if has_children=false → read content directly

3. backlog_view(selector="#2529", navigate="4.0.1")
   → NavigateResponse: prose with [code:...] tokens for any fences

4. backlog_view(selector="#2529", navigate="4.0.1.code.0")
   → NavigateResponse: raw code fence body
```

---

## Resolution Index vs Map Text

The resolution index inside `OrdinalPathMapper` is built eagerly to all depths during
`build_map()`. `resolve()` and `valid_ordinals()` operate on this complete index.

The `map_text` field in `MapResponse` is bounded by the token budget (from
`progressive_markdown.list_navigator.TOKEN_BUDGET`). Deep ordinals may be absent from the
rendered map text but remain resolvable via `navigate=`.

Source: architecture spec §5.3 and `backlog_core/ordinal_mapper.py`.

---

## Backward Compatibility

For entries that contain no headings and no code fences, `OrdinalPathMapper` short-circuits
and emits no level-3+ ordinals. The ordinal list for that entry is byte-for-byte identical to
pre-feature output.

Source: architecture spec §5.2 and `backlog_core/ordinal_mapper.py`.
