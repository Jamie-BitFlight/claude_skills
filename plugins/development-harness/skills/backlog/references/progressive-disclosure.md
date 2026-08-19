# Navigating Inside a Backlog Item

`backlog_view` addresses any node of an item by dot-path ordinal. Use `map` to discover ordinals,
`navigate` to fetch one, `head` and `skip_tokens` to bound and page a large one.

## When to navigate instead of fetching the item

Reach for `map` plus `navigate` whenever the target is one part of a large item — a single
acceptance-criteria block, one code fence, one sub-heading. `section` filtering returns a whole
named section; `navigate` reaches inside one, at any nesting depth.

Fetch the whole item only when every section will be read.

## Ordinal syntax

Ordinals must match `^\d+(\.\d+)*(\.code\.\d+)?$`.

- `4` — top-level section
- `4.0` — first entry within that section
- `4.0.1` — second sub-heading inside that entry; nesting depth is unbounded
- `4.0.code.0` — first code fence in that entry's direct body

An ordinal that matches no node returns an error listing every valid ordinal in the item.

## Parent versus leaf (ADR-7)

A node with sub-heading children returns `content=""`, `has_children=true`, and a `child_map`
listing the child ordinals. Drill into a child ordinal to reach prose.

A leaf node returns full `content`, `child_map=null`, and `has_children=false`. A node holding
prose and code fences but no sub-headings is a leaf.

## Drill-down sequence

1. Call `backlog_view(selector="#2969", map=True)`. The response is bounded under 2,000 tokens
   regardless of item size. Each `map_text` line reads
   `{ordinal} {title} ({est_tokens}t) — "{first content line}"`. Select the ordinal whose title and
   preview match the target.
2. Call `backlog_view(selector="#2969", navigate="4.0")`. When `has_children=true`, read `child_map`
   and repeat this step with a child ordinal such as `4.0.1`. When `has_children=false`, `content`
   holds the full node.
3. When the node is larger than needed, bound it:
   `backlog_view(selector="#2969", navigate="4.0", head=4000)`. While `truncated=true`, repeat using
   the `skip_tokens` value from the response's `next_call` hint until `truncated=false`.

## Parameter interactions

`map=True` is mutually exclusive with `navigate`. `head` and `skip_tokens` each require `navigate`.
`skip_tokens` counts tokens within the navigated node; `offset` counts entry blocks in the item
body. They address different concerns — do not substitute one for the other.
