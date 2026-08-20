# Agent Markdown Consumption — Behaviour Specification

Every consumer of every operation described here is an AI agent. There is no human reader.

Requirements R1–R8 are normative. Design decisions resulting from questions raised while
implementing this contract are recorded as ADRs in `docs/adrs/`, referenced from the
requirement they resolve — not left as unresolved prose in this document.

## Purpose

Define one contract for how markdown reaches an agent. An agent must never receive an
unbounded dump, must never receive silently truncated content, and must always receive
enough structure to request exactly the part it needs next.

## Scope — operations bound by this contract

Every operation that returns markdown to an agent is bound, on every transport. This
includes, and is not limited to:

- reading an item and any filtered view of one
- reading a plan or a task
- reading an artifact's content
- any listing operation whose result embeds content rather than only metadata

An operation is not exempt because its content is usually small. Requirements apply to the
operation, not to a size class of its typical payload.

## Normative requirements

### R1 — One markdown engine, all consumption

A single markdown engine serves every markdown consumption path across the plan/task system
and the backlog system. It parses content from any source, builds an addressable tree, and
returns paginated results.

No component may hand-build a table of contents, a section listing, a content excerpt, or a
bounded response of its own. Where such an implementation exists today it is deleted, not
maintained in parallel. A second implementation is a defect regardless of whether it works.

Sources include, and are not limited to: issue and item bodies, plan documents, task
documents, and the reports and artifacts produced during grooming.

**Pipeline layering** (ADR-3072-1): three stages, in order — Collection (gathering source
content from wherever it lives), Generation (assembling the complete document for a requested
scope: description, table of contents, every requested section or artifact), and Navigation
(this engine). Collection and Generation are unbounded — never truncated, never budget-checked.
The engine's authority is over Navigation only: it receives a complete generated document,
gives it a content identity (R8), caches it for the session, and is the only point anywhere in
the path where a size budget is applied. "Unbounded" is a real cost for a pathological source,
not a theoretical one — see ADR-3072-1's known limitation for a concrete measurement and why
this decision does not add a ceiling to fix it.

**Navigation is source-agnostic.** It has no knowledge of, and no need to know, what kind of
thing it is windowing — an issue, a PR, a plan, an artifact, a local file. It receives markdown
text and the parameters of the current request (scope, address, page) and renders a view; it
never learns where that text came from or reaches back to a backend to get more of it. This is
a global markdown viewer, not a per-source one — the same relationship a browser's chrome has
to the page it renders, indifferent to whether the page came from `file://` or `https://`. The
`MarkdownContentProvider` protocol (implementation appendix) is the seam that makes this true:
every source implements `get_markdown(source) -> str`, and nothing past that seam is
source-specific.

### R2 — Everything paginates, including the table of contents

Every response that can exceed the window budget paginates. This applies recursively and
without exception — a table of contents that exceeds the budget paginates exactly as a
content body does.

No response may drop, elide, or truncate addressable nodes to fit a budget. Content that
does not fit the current page is reachable on a subsequent page, never merely implied.

Harnesses commonly cap a single tool response at ~10,000 tokens, adjustable. The engine's
budget is configurable and must not exceed the harness cap, is sourced from one constant
(ADR-3072-1), and is never applied outside the Navigation stage (R1).

A caller may request a page smaller than the configured default. A tool response has no local
equivalent of `tail` — a caller that wants to peek at part of a large result depends on the
server accepting an explicit, smaller page-size request.

### R3 — Threshold triggers the compact form, automatically

When a response would exceed the budget, the compact form is returned instead. This is
automatic: no opt-in parameter, no prior knowledge required of the caller.

The compact form contains item metadata, the top description, the table of contents, the
inventory of associated reports and artifacts, and a hint naming the exact next call.

This is progressive disclosure: an agent never receives structure it has no use for. The
table of contents is not the whole item's table of contents by default — it is scoped to
exactly what was requested (R5), and sized accordingly. Requesting one section with several
subheadings returns a table of contents no larger than that section's own subheadings.
Requesting two or three sections returns a table of contents spanning only those. Requesting
the item as a whole returns a table of contents spanning the whole item. If what was
requested fits in one page regardless of scope, no table of contents is returned at all —
there is nothing to navigate when everything already fits, so the navigational aid is pure
overhead and is omitted, not just collapsed to a stub.

### R4 — One addressing scheme

Addresses in a table of contents are the same addresses accepted by every retrieval
operation. An agent copies an address from a response and passes it back unchanged. Exactly
one scheme exists across the whole system.

### R5 — Addresses accepted wherever content is requested

Every operation that returns markdown accepts an address to scope what it returns, and a
page selector to traverse it.

### R6 — Sections and artifacts are one inventory

An agent viewing an item receives, in one response, both awareness of its sections and the
associated reports and artifacts. Both are requestable by name. Discovering what exists never
requires a second call to a different tool. This is the invariant R6 guarantees; it does not
require a table-of-contents structure to always be present. When content fits in one page
(R3), sections and artifacts appear directly in that single response, without table-of-contents
scaffolding around them — there is nothing to navigate, so there is nothing to name a table of
contents. The table of contents exists only when there is more than one page's worth of content
to navigate (R3); R6's discoverability guarantee holds either way.

This requirement changes the response shape of the item-view operation on every transport,
and supersedes the current arrangement in which artifacts are discovered through a separate
lookup. It states intended behaviour, not current behaviour.

The Generation stage (R1) realizes this directly: sections and artifact content are assembled
into one document, in one address space (R4), before Navigation windows it. There is no
separate pagination path for the artifact inventory — it pages exactly as the rest of the
generated document does (ADR-3072-1).

### R7 — Hints must be actionable

A response that withholds content states what the caller must do to obtain it, using
addresses valid in that same response. A hint must never recommend retrieving everything as
its first suggestion, never recommend an action the caller has already exhausted, and never
name a mechanism absent from the response it accompanies.

### R8 — Paginated content is addressed by content identity

A response that paginates returns a stable identifier derived from the content it paginates,
alongside the page position. Subsequent pages are requested with that identifier plus a page
selector or an address, never by re-describing the source. The original scope or query is not
repeated on follow-up calls — it is retained server-side as the entry's stored command (see
below), not something the caller carries forward. Concretely, an initial request states scope
(`selector="#2529", section="RT-ICA"` or similar); every request after that states only
`hash="<identifier>"` plus `page`, `navigate` (R4's address), and `pagesize` (the caller
override from R2) — nothing about where the content came from.

The identifier resolves against cached parsed content. Serving a later page does not
re-collect from the provider and does not re-parse.

A request whose identifier no longer matches current content is reported as stale. Pages
from two different versions of a document are never returned as though they were one
document. **This is not a contradiction of "does not re-collect" above** (flagged in review —
worth stating plainly): staleness is detected by write-triggered invalidation (below), a side
effect of the write that changed the source, not by the read path re-collecting to compare.
The one path that does re-collect on a read is explicit, caller-requested revalidation — an
opt-in exception the caller chooses, never something the server does silently on an ordinary
page request.

The identifier is derived from both the command (source, scope, parameters) and the Generation
stage's output for that command — not a hash of the raw upstream source alone (ADR-3075-1), and
not a hash of the generated content alone either. Content-only hashing was flagged in review as
a real collision: two different commands can produce byte-identical generated documents (a
coincidence, not a contract violation), and a content-only hash would give them the same
identifier while the entry retains only one command — a later requery or revalidation could
then execute the wrong command entirely and return content unrelated to what the caller asked
for. The identifier binds command and content together precisely so two different commands
never collide even when their output happens to match. Two different scopes of the same source
(the whole item vs. one filtered section) produce different generated documents and, by the
same binding, different identifiers. The cache backing this is held for the duration of the
requesting session only; it is not persisted across sessions (ADR-3075-1).

**One shared control set for the whole session — out-of-process, not an in-process cache**
(ADR-3075-4). The control set is a single store for the whole session, not reinstantiated per
operation, per subcommand, or per transport — but it cannot be an in-process cache (a
server-held dict, an MCP lifespan context) and satisfy that, because the CLI is a separate OS
process per invocation with no shared memory to an MCP server process, by construction, no
matter how the MCP side is wired. The store is out-of-process, keyed by session — the same
pattern already used by `get-gate-token.mjs`, which persists to
`$DH_STATE_HOME/sessions/{CLAUDE_CODE_SESSION_ID}/` (default `~/.dh/sessions/...`) using the
session-ID environment variable both MCP-tool-calling agents and CLI invocations already share.
An item viewed through one MCP tool and then again through a different tool, or through the
CLI, still hits the same entry if the request scope and content identity match — because both
sides read and write the same session-keyed store on disk, not because either holds the other
in memory. A cache scoped to one process is a violation of R1 (a second, narrower
implementation of what the engine already owns), not a smaller version of a correct
implementation.

**Stale entries are recoverable, not dead ends** (ADR-3075-2). A control-set entry retains the
command that produced it — the source, scope, and parameters Collection and Generation used to
build it — not only its content identity. When a request's identifier no longer matches
current content, the stored command is used to requery the backend and regenerate the
document, serving against the new identity and informing the caller the identity changed. The
caller is not required to restate its whole request from scratch.

**Writes invalidate; reads do not have to discover staleness on their own** (ADR-3075-2). A
control-set entry is not left to be discovered stale only when a later read happens to hit it
with a mismatched hash. A write that modifies the source a cache entry was generated from
invalidates that entry as a side effect of the write. Every mutation path bound by this
contract's sources — item updates, section writes, artifact registration, task and plan state
changes — is a source of invalidation for any control-set entry generated from what it
touched.

**Cache metadata is visible to the agent, not only used internally** (ADR-3075-3). Every
response backed by the control set carries its content identity, the command that produced it,
and when it was generated — the same three things the cache uses internally to detect
staleness. This is not exposed as a debugging aid; it gives the agent a basis to judge
freshness itself, independent of the server's own write-triggered invalidation (which may not
have run yet, or may not know about a write made through a path outside this contract). An
agent that just wrote to something it is about to re-read, or that otherwise has reason to
distrust automatic invalidation, may explicitly request revalidation or a forced refresh
instead of trusting whatever the control set already holds.

## Required flow

```mermaid
flowchart TD
    Req([Agent requests content<br>from any source]) --> Coll[Collection: gather source content<br>unbounded — no budget check]
    Coll --> Gen["Generation: assemble the complete document<br>for the requested scope — description +<br>table of contents + every requested<br>section or artifact — unbounded R1"]
    Gen --> Nav[Navigation engine: parse, build<br>addressable tree, hash the generated<br>document for content identity R8]
    Nav --> Cache["Cache the generated document<br>for the session, keyed by that identity R8"]
    Cache --> Eng[Window the cached document<br>to the agent]
    Eng --> Measure{Response exceeds<br>window budget?<br>only checked here}

    Measure -->|No| Full[Return full content]
    Measure -->|Yes| Compact["Return compact form R3:<br>metadata + description<br>+ table of contents R4<br>+ artifact inventory R6<br>+ actionable hint R7"]

    Compact --> TocFits{Table of contents<br>itself exceeds budget?}
    TocFits -->|Yes| TocPage["Paginate the table of contents R2<br>nothing dropped — page selector returned"]
    TocFits -->|No| Select
    TocPage --> Select[Agent selects an address<br>or artifact name from the response]

    Select --> Fetch[Request that address]
    Fetch --> Children{Node has children?}
    Children -->|Yes| ChildMap[Return child listing<br>agent drills further]
    ChildMap --> Select
    Children -->|No| Fits{Content exceeds<br>window budget?}

    Fits -->|No| Deliver[Return full node content]
    Fits -->|Yes| Window["Return page 1 + page selector R2<br>no content dropped — caller may<br>request a smaller page than default R2"]
    Window --> Cont[Agent requests next page]
    Cont --> Fits
```

## Design decisions

The five questions previously open in this section (#3072–#3076) are resolved and folded into
R1, R2, R6, and R8 above. The reasoning, rejected alternatives, and why each choice is hard to
reverse are recorded in ADRs, not restated here:
[ADR-3072-1](./adrs/ADR-3072-1-budget-applies-only-at-navigation.md) (budget/layering),
[ADR-3075-1](./adrs/ADR-3075-1-content-identity-and-cache-scope.md) (identity/scope),
[ADR-3075-2](./adrs/ADR-3075-2-stale-cache-recovery-and-write-invalidation.md) (requery on
stale, write invalidation),
[ADR-3075-3](./adrs/ADR-3075-3-cache-metadata-visible-to-agent.md) (agent-visible cache
metadata), and
[ADR-3075-4](./adrs/ADR-3075-4-out-of-process-session-keyed-control-set.md) (out-of-process,
session-keyed store).

Vocabulary introduced by these decisions — Collection, Generation, Navigation, Navigate, table
of contents, budget — is defined once in [`CONTEXT.md`](../CONTEXT.md), not duplicated in this
contract.

## Implementation appendix — shape to code

The engine described by R1 exists as the `progressive_markdown` package:
`ProgressiveMarkdownNavigator` (`map`, `view_section`, `view_code`, `links`,
`search_sections`, each taking `page` and `budget`), `Paginator` (`paginate_blocks`,
`paginate_text`), and a `MarkdownContentProvider` protocol for arbitrary sources.

`ProgressiveMarkdownNavigator` and `Paginator` currently have no consumers. The engine's
parser and indexer are imported by the address-navigation path; its navigation and
pagination layer is not used by anything.

Duplicate implementations to delete rather than refactor, in the backlog server layer
(`backlog_core/server.py`, `backlog_core/operations.py`) shared by the MCP tool and CLI paths
that call it:

- the compact manifest, over-budget directory, and section-index builders, which emit a
  bracket-numbered index that neither paginates nor matches the engine's addresses — the
  same index format is hand-built in three separate functions
- the entry-block pagination and paged-body rendering, which duplicate `Paginator`
- the section-filter assembly, which duplicates parser-level node extraction

The address-based navigation path (`disclosure_handler`, `ordinal_mapper`) already routes
through the engine and is the reference for how the remaining paths should call it.

## Related documents

- [MCP Progressive-Disclosure Contract](./mcp-progressive-disclosure-contract.md) — mechanical
  reference for ordinal addressing, navigation parameters, and response shapes on one conforming
  implementation. Subordinate to this contract for behaviour.
- [Unified Section Layer Brief](./unified-section-layer-brief.md) — defines the cross-provider
  entry and ID contract that markdown sources are built from. Complementary, not overlapping:
  that brief owns entry and ID identity; this contract owns pagination and disclosure of the
  content built from those entries.
