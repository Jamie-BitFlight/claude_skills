---
name: project-progressive-markdown
description: progressive_markdown package: markdown-it-py architecture, token budgeting, SOLID design, linting patterns (2026-05-31 rewrite)
metadata:
  type: project
---

## Package architecture (SOLID rewrite, 2026-05-31)

**Location**: `plugins/development-harness/progressive_markdown/`

**12-module structure:**
- `exceptions.py` — typed exception hierarchy (ProgressiveMarkdownError base)
- `models.py` — Pydantic v2 models (PMBaseModel, SectionNode, MarkdownDocument, NavigationResult, NavigatorOptions)
- `providers.py` — MarkdownContentProvider Protocol, CallableMarkdownContentProvider, MCPMarkdownContentProvider
- `tokenizer.py` — TokenBudgeter (tiktoken); lossless split_to_budget algorithm
- `parser.py` — MarkdownParser Protocol + MarkdownItParser (markdown-it-py, NOT marko)
- `indexer.py` — MarkdownIndexer builds MarkdownDocument from ParserResult via token stream walk
- `links.py` — LinkExtractor walks inline token children for links/images/ref-defs
- `codeblocks.py` — CodeBlockStubRenderer (line-based), CodeBlockExtractor
- `pagination.py` — Paginator (paginate_text and paginate_blocks)
- `renderers.py` — 5 renderers (DocumentMap, SectionMap, SectionBody, LinkInventory, CodeBlock)
- `navigator.py` — ProgressiveMarkdownNavigator facade (DI injectable, classmethods)
- `list_navigator.py` — moved from dh_progressive_disclosure.py; TOKEN_BUDGET=4400

**dh_progressive_disclosure.py was DELETED** — content is now `progressive_markdown/list_navigator.py`
`test_paginate_results_boundary.py` imports from `progressive_markdown.list_navigator`

## markdown-it-py API patterns (verified 2026-05-31)

**Token types in parse() output:**
- `heading_open`: `token.tag = "h1".."h6"`, `token.map = [start_line, end_line]` (end_line exclusive)
- Next token after heading_open is always `type == "inline"`, `.content` = heading text
- `fence`: `token.info` = full info string, `token.content` = code body, `token.map = [start, end]` (end exclusive)
- `inline`: iterate `.children` for `link_open` (href in `.attrs`), `image` (src in `.attrs`)
- `link_open.attrs = {"href": "...", "title": "..."}` (dict, not list of lists — use attrGet or .get())
- `env["references"]` = `{"LABEL": {"href": "...", "title": "...", "map": [start, end]}}`

**Body span calculation:**
- heading body_start = `heading_open.map[1]` (line after heading, map[1] is exclusive end)
- body_end = line before first child section's heading_start, OR section_end when leaf

## Token budget architecture — TWO SEPARATE CONSTANTS

**Never cross-contaminate these:**
- `list_navigator.TOKEN_BUDGET = 4400` — structured data pagination (ProgressiveDisclosure, paginate_results)
- `NavigatorOptions.default_budget = 11000` — markdown text navigation (ProgressiveMarkdownNavigator)

The 4400 constant is calibrated by `test_paginate_results_boundary.py` with exact token counts. Changing it breaks test calibration assertions.

## sam_schema/server.py does NOT import dh_progressive_disclosure

`server.py` has its own local `_paginate_results` at line ~189. Only `test_paginate_results_boundary.py` was affected by the deletion of `dh_progressive_disclosure.py`.

## Key linting patterns

- `_default_budget` accessed via `# noqa: SLF001` in paginator (private attribute of injected object)
- Pydantic field validators use `@field_validator` with `@classmethod` decorator
- Pydantic validation errors are `pydantic.ValidationError`, not `ValueError`
- `test_paginate_results_boundary.py` needs `@settings(max_examples=100, deadline=None)` on hypothesis tests

## chunk_text losslessness (shared with list_navigator)

- `re.split(r'(\n\n+)', text)` with capturing group keeps delimiters in output list
- Level 1: blank-line paragraphs → Level 2: single newlines → Level 3: char bisection
- Character bisection: binary search for largest char offset i where `count(text[:i]) <= budget`
- `"".join(chunks) == original_text` is guaranteed by slicing source string, never token sub-lists

**How to apply:** When extending progressive_markdown or building marko/markdown-it-py parsers in this plugin, use these verified patterns and constants directly.
