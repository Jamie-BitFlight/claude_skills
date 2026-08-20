# Development Harness — Component Architecture

Read this before working in any package in this plugin. It maps every code package to its
role, states which package owns which responsibility, and names the places where two
components look alike and are not.

This document states the intended architecture. Where the implementation differs, the
difference is a tracked gap, not a description of how things should stay. Gaps are recorded
as backlog items rather than as caveats here.

Behavioural requirements for markdown consumption live in
[Agent Markdown Consumption](./agent-markdown-consumption-contract.md). This document does
not restate them; it says which package is responsible for satisfying them.

## Transports

The harness exposes the same operations through two transports: MCP servers and a CLI. Both
are thin. Neither owns behaviour.

`dh_core` is the unified operations layer both transports call. A behavioural requirement
binds every transport, and a capability added to one transport without the other is a gap.
Never describe a behaviour as belonging to MCP or to the CLI.

## Package map

### `progressive_markdown`

Role: the markdown engine. The single path through which markdown reaches an agent.

Owns: parsing markdown into an addressable tree, assigning addresses, pagination of every
result including a table of contents, token budgeting, and the content-provider protocol
that lets markdown arrive from any source.

Consumed by: `backlog_core`, `sam_schema`.

Do not confuse with: the navigation and pagination logic currently living inside
`backlog_core`. That logic duplicates this package's `Navigator` and `Paginator` and is
scheduled for deletion, not maintenance. A second implementation of addressing or pagination
is a defect regardless of whether it works.

Two numbering schemes exist today and they are not the same thing. The engine's dot-path
addresses reach sections, sub-headings, and code fences at any depth; they are the surviving
scheme. The bracket-numbered index emitted by the hand-built section directory addresses only
top-level sections, does not paginate, and is removed with the code that produces it. When a
document refers to an address, it means the dot-path form.

### `backlog_core`

Role: the backlog domain — items, their sections and entries, provider adapters, and
synchronisation.

Owns: item lifecycle, the canonical section-name registry, entry identity and timestamps,
provider adapters, and reconciliation between local and remote state.

Consumes: `progressive_markdown` for all markdown handling.

Detail: [backlog_core/ARCHITECTURE.md](../backlog_core/ARCHITECTURE.md).

Do not confuse with: two distinct concerns live here and a finding in one does not
generalise to the other.

- Storage keying decides which canonical key a heading maps to, so the same logical section
  is addressed consistently across providers.
- Navigation indexing decides how an agent walks a document's tree.

These answer different questions. Navigation belongs to `progressive_markdown`; where
`backlog_core` implements it, that is a gap.

### `sam_schema`

Role: the plan and task domain, plus the CLI application.

Owns: plan and task models, plan lifecycle, and the CLI entry point.

Consumes: `progressive_markdown` for all markdown handling; `dh_core` for shared operations.

Constraint: plan mutation is single-writer. Operations that append a task or finalise a plan
must not be performed concurrently by more than one writer. See
[ADR-1770-1](./adrs/ADR-1770-1-single-writer-task-backend.md) — this constraint is easy to
violate silently when adding a new mutation path.

Do not confuse with: `dispatch_schema`. Plans describe work; dispatch plans describe how
work is distributed to agents.

### `dh_core`

Role: the unified operations layer shared by the CLI and the MCP servers.

Owns: operations both transports invoke, and the protocols defining them.

Do not confuse with: transport modules. An operation implemented in a transport rather than
here is reachable from one transport only, which violates the transport rule above.

### `dispatch_schema`

Role: dispatch plan models, their serialisation, validation, and gates.

Do not confuse with: `sam_schema`'s plans and tasks. See the distinction above.

### `agent_profile`

Role: an MCP package exposing agent profile discovery and loading.

### `hooks`

Role: Claude Code hook scripts bound to harness events.

### `scripts`

Role: entry-point wrappers that let packages run standalone, including the self-resolving
server and CLI launchers.

## Content model

An item carries two kinds of associated content, and an agent discovers both from one
response rather than by querying separate tools.

- Sections: the item's own body content, addressed by the engine's addressing scheme.
- Artifacts: reports and assets produced during grooming, associated with the item and
  requestable by name.

Artifact identity and retrieval are provider-independent: the same name resolves the same
artifact regardless of which provider stores it.

Ownership divides as follows. Verified against the current code (not assumed): registration
and durability are already split exactly as intended; delivery is not.

- `backlog_core` owns artifact registration, identity, and the association between an
  artifact and its item — artifact discovery is part of item state. Confirmed:
  `artifact_register()` computes identity and writes the manifest entry; this is the only
  place that does.
- The storage provider owns durability of artifact content. Confirmed: the GitHub backend's
  `put_content()` writes directly when online and queues durably via `FileCache` when
  offline; no other component performs physical persistence.
- `progressive_markdown` **should** own delivery of artifact content to an agent, on the same
  terms as any other markdown — this is intended behaviour, not current behaviour.
  `artifact_read()` today calls the provider's `get_content()` directly and returns raw
  content, with no engine involvement at all. This is the same "second implementation"
  pattern R1 forbids elsewhere: artifact content delivery is a markdown consumption path with
  no navigation, pagination, or content identity, entirely outside the engine described by R1.
  Tracked in #3078.

Discovery is not a provider concern and not an engine concern. An artifact registered as
`current` whose content cannot be retrieved is a defect — concretely, `artifact_migration.py`
can write a manifest entry with `status: current` before its content write is confirmed to
succeed, with no verification step tying the two together. Tracked in #3055.

## Provider independence

Items may be stored by any supported provider. Provider-specific serialisation stays inside
its adapter. A read, write, or navigation operation returns the same logical result
regardless of provider, or reports an explicit unavailable or stale outcome when a provider
cannot supply it.

Detail: [Backend Providers](./backend-providers.md),
[Unified Section Layer](./unified-section-layer-brief.md).

## Test layout

Tests live with the subsystem they cover, inside that subsystem's directory. The plugin-level
test directory is for plugin-level concerns only. Before adding a test file, search the whole
plugin for an existing suite covering that module and extend it rather than creating a
second file.

## Where workflow is described

This document maps packages and their responsibilities. It does not describe the workflows
that run across them — grooming phases, gate sequencing, agent dispatch, or status
transitions. Those live in the lifecycle and pipeline documents indexed by the Required
Reading table. Adding workflow description here would recreate the everything-document
problem this map exists to avoid.

## Documentation layout

Documents live in this directory and are indexed by the Required Reading table in the
plugin's `AGENTS.md`. A document that no index references is unreachable. When adding one,
add its index entry in the same change, and check whether an existing document already
covers the topic — two documents describing one component will drift into contradiction.
