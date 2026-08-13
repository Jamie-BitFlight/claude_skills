# Design Brief: Unified Section Layer for `backlog_core`

This contributor brief defines the section-wire contract. Consumer workflows must use the
configured backlog MCP/CLI operations and must not parse provider bodies, cache files, or wire
timestamps themselves.

## Outcome

Make every section use one addressable entry representation. Preserve the logical section and
entry model across GitHub, Beads, SQLite, and memory providers while keeping provider-specific
serialization inside each adapter.

Completion criterion: a read, append, replace, strike, `since`, or show operation returns the
same logical result regardless of the selected provider, or returns an explicit unavailable or
stale outcome when that provider cannot supply it.

## Root cause

The writer was not enforced. Entry sections use timestamped `<div>` blocks while prose sections
can still be emitted as plain text. Readers consequently contain fallback parsing, YAML/body
reconciliation, and synthetic-ID branches. Fix the writer and adapter boundary; do not add a
third reader path.

## Canonical logical contract

The unified layer owns these operations:

- `write_entry_section(name, entries)` for tracked discrete entries;
- `write_prose_section(name, text)` for one freeform entry;
- read, append, replace, strike, `show`, and `since` operations over logical entries.

Every emitted entry has an opaque stable `id`, content, and provider-normalized timestamp
metadata. The `<div><sub>...</sub>...</div>` block is the GitHub-compatible wire primitive,
but callers never write that markup directly. Local providers may use native structured rows;
their adapters must expose the same logical result without pretending to be GitHub.

### ID and timestamp rules

1. Never emit or preserve a zero timestamp as an entry ID. It cannot support ordering,
   deduplication, strike targeting, or `since` filtering.
2. Prefer an explicit entry write timestamp. When a legacy entry lacks one, derive a deterministic
   baseline from the adapter's authoritative item creation metadata, section identity, and
   position: `{item_created_at}-{section_name}-{position_index}`. The baseline must be non-empty,
   stable for the same input, and unique within the item.
3. GitHub's GraphQL adapter reads raw `createdAt` and `updatedAt` fields and converts them at the
   adapter boundary to the canonical timestamp fields. Do not expose `createdAt` as a universal
   domain field and do not make Beads, SQLite, or memory adapters fabricate GitHub wire keys.
4. A provider that has no authoritative creation timestamp must use its own stable record
   metadata or report that the legacy entry is unavailable for timestamp-sensitive operations;
   it must not substitute `0000-00-00` or an epoch sentinel.
5. Suffix duplicate IDs deterministically only after the authoritative baseline is chosen.

## Read and migration behavior

Use one logical read path:

1. Ask the configured provider for the item/section.
2. Let the adapter decode its native representation into logical sections and entries.
3. Normalize legacy plain-text content once through the writer, using the adapter's creation
   metadata for the baseline ID.
4. Apply `show`/`since` in the logical layer and return the result.

The YAML or private provider cache is downstream state, never a second source of entry IDs.
Use it as an optimization only when its revision matches the provider result. If content is
served from a remote provider's cache, mark it stale; if no record can be obtained, propagate
an unavailable error. Do not silently replace remote data with a local file or claim that a
queued write reached the remote provider.

## Mechanical boundary

Known-input parsing, search, filtering, section addressing, artifact lookup, plan lookup, and
progress counting belong in scripts, CLI commands, or MCP tools. Consumer instructions should
name the operation and interpret its returned evidence; they should not reproduce a grep,
parser, filter pipeline, or multi-call state update. Keep unique evidence interpretation,
diagnosis, synthesis, and design decisions in the agent reasoning layer.

## Contributor acceptance criteria

- [ ] All section writers route through the unified layer; no provider adapter writes an
  unwrapped section when it claims the canonical wire contract.
- [ ] No reader or migration path creates a zero-timestamp ID.
- [ ] GitHub `createdAt`/`updatedAt` conversion is confined to the GitHub adapter and tests cover
  both raw wire keys and canonical fields.
- [ ] Beads uses its native `bd` records/KV store without a GitHub-shaped cache; SQLite and memory
  remain native local providers.
- [ ] Remote cache reads expose `stale`; queued writes expose `pending`; missing or unavailable
  provider data remains an error.
- [ ] `show` and `since` operate on normalized logical entries, with deterministic duplicate-ID
  handling.
- [ ] Consumer docs point to MCP/CLI/script operations for mechanical lookup and leave evidence
  interpretation to the agent.

## Out of scope

- Do not change the lifecycle state machine or invent provider-specific consumer workflows.
- Do not make provider identifiers, file paths, cache roots, or GitHub API objects part of the
  logical section contract.
- Do not preserve a permanent dual-path reader for legacy content.
