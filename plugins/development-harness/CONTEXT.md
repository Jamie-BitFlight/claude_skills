# Development Harness — Markdown Consumption

How markdown content is collected, generated, and windowed to an AI agent across the plan/task
system and the backlog system. Every consumer is an agent; there is no human reader. Normative
behaviour lives in `docs/agent-markdown-consumption-contract.md` — this file is vocabulary only.

## Language

**Collection**:
Gathering source content from wherever it lives — issue body, plan file, task file, artifact.
Unbounded: never truncated, never budget-checked. Already backed by `FileCache`
(`backlog_core/file_cache.py`), a durable, provider-owned local cache of raw content — a
Collection re-run is routinely a local cache hit, not a network round-trip. Distinct from
Control set below: Collection-layer raw content vs. Navigation-layer generated documents;
durable vs. session-scoped.

**Generation**:
Assembling the complete markdown document for a requested scope — description, table of
contents, and every section or artifact content the request covers — before any windowing.
Unbounded, same as Collection.

**Navigation** (pipeline stage):
The one system that takes a generated document, gives it a content identity, caches it for the
session, and windows it to the agent. The only stage where a size budget applies. Source-agnostic:
it has no knowledge of what kind of thing it is windowing — issue, PR, plan, artifact, local
file — the same relationship a browser's chrome has to the page it renders. Global, not
per-source: one Navigation stage serves every source, never one implementation per source type.
_Avoid_: "pagination layer" as a synonym for the whole stage — pagination is one of the things
Navigation does, not the stage's name.

**Provider**:
The seam that makes Navigation source-agnostic. Implements `get_markdown(source) -> str`;
supplies markdown text for a source without Navigation ever knowing what that source is.
Matches `MarkdownContentProvider` already in code.

**Control set**:
The single, session-shared store backing Navigation's content identity (R8). One store for the
whole session, not one per tool, subcommand, or transport — every operation touching the same
generated content resolves against the same control set, regardless of which tool made the
request. Out-of-process by necessity, not by preference: the CLI is a separate OS process per
invocation, so an in-process cache (an MCP server's lifespan context, a module-level dict)
cannot be shared with it. Session-keyed on disk, following the existing
`$DH_STATE_HOME/sessions/{CLAUDE_CODE_SESSION_ID}/` pattern (`get-gate-token.mjs`), not a new
storage convention.
_Avoid_: "in-process cache" or "shared dict" as a mental model — that shape cannot satisfy
"same entry regardless of transport" no matter how carefully it's wired.

**Navigate** (action):
Requesting content at a specific address from the table of contents. Matches the `navigate`
parameter and `NavigateResponse` type already in code. Distinct from the Navigation stage above —
one is the system, the other is a single request against it.
_Avoid_: "content navigation", "browse"

**Table of contents (TOC)**:
The addressable index of an item's sections. `map` is the parameter name used to request it;
"table of contents" is the concept's name in prose.
_Avoid_: "map" outside of naming the literal parameter

**Budget**:
The size limit applied exclusively at the Navigation stage when windowing a generated document
to an agent. Never applied at Collection or Generation — there is nothing to fit a budget to
until Navigation has a complete document in hand.
