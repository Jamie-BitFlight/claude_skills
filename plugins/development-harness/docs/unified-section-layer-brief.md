# Design Brief: Unified Section Layer for backlog_core

Surfaced through code review and conversation, 2026-06-05.
This brief must be handed to the discovery and architecture agents before any
planning begins. It contains constraints that the codebase alone will not reveal.

---

## Root Cause

The writer was never enforced. Two rendering paths exist because prose sections
were added after entry sections without holding the line on format:

- **Entry sections**: `## Header\n\n<div><sub>{timestamp}</sub>content</div>`
- **Prose sections**: `## Header\n\nplain text`

Every complexity downstream — `_sections_from_body_or_yaml`, the YAML fallback,
the subset check, the two-path read logic — is a symptom of this writer
inconsistency. The fix is at the writer, not the reader.

---

## Constraint 1: Zero-timestamp IDs are invalid

`_build_sections_metadata` generates synthetic IDs with a zero timestamp when
parsing a body that has no `<div>` blocks. This is not a parsing limitation —
it is a writer failure that the reader papered over.

A zero-timestamp ID is not unique. Multiple entries written this way get the
same ID, silently breaking:
- `since` filtering — all entries look like epoch
- deduplication — different entries are indistinguishable
- struck tracking — cannot reliably target a specific entry

**The zero-timestamp fallback must be eliminated entirely.** It must not survive
into the unified layer in any form.

---

## Constraint 2: Real IDs are always derivable

The GitHub issue `createdAt` is available on every item. When an entry has no
explicit write timestamp, the correct baseline is:

```
{issue.createdAt}-{section_name}-{position_index}
```

This gives a non-colliding ID that:
- sorts correctly relative to entries with real timestamps
- is deterministic (same input → same ID, safe to regenerate)
- is unique within an issue (section + index suffix)

The architecture must use this baseline for any entry that arrives without a
real timestamp. There is no valid case for a zero-timestamp ID.

---

## Constraint 3: All sections use the same wire format

The unified layer must enforce one wire format for all sections — prose and
entry alike. The `<div>` block is the correct primitive because it already
carries the ID and timestamp that makes entries addressable.

For prose sections, the wrapper is one `<div>` block containing the full prose
text as its content. The ID is derived per Constraint 2.

**Callers never write raw `<div>` tags.** The unified layer provides:
- `write_entry_section(name, entries)` — list of tracked discrete items
- `write_prose_section(name, text)` — freeform text, wrapped as single entry

The layer decides the wire format. No caller bypasses it.

---

## Constraint 4: The reader becomes trivial

Once the writer is enforced, every body has `<div>` blocks on every section.
The reader has one path:

1. Parse `<div>` blocks → extract real IDs and timestamps
2. Associate each block with its owning `##`/`###` header

`_sections_from_body_or_yaml`, the YAML subset check, and the zero-timestamp
avoidance logic are all deleted. They exist only to compensate for writer
inconsistency.

---

## Constraint 5: Migration path for existing items

Items already written in the old format (plain `##` headers, no `<div>` blocks)
must be migrated on first read or first write — not left as a permanent
special case.

On first read of a plain-text section: wrap it using the `createdAt` baseline
ID (Constraint 2), write it back through the unified writer, then return the
normalised form. This is a one-time migration per item, not a permanent
two-path read.

---

## Constraint 6: The YAML cache is downstream, not a source of truth

The YAML local cache stores structured `Section` objects with entry IDs. Those
IDs come from the wire format. If the wire format is unified, the YAML cache
is always consistent with it — there is no divergence to handle.

`_build_sections_from_yaml_item` may survive as an optimisation (avoid
re-parsing the body when the YAML is fresh), but it must never be the fallback
for missing IDs. The body is always the source of truth for IDs.

---

## Known affected systems (preliminary — codebase analysis will expand this)

| File | Role |
|---|---|
| `backlog_core/github_sync.py` | `render_issue_body`, `_render_section_entries` — primary writers |
| `backlog_core/gh_client.py` | body write paths, groomed section appending |
| `backlog_core/parsing.py` | `## Story`, `## Description`, `## Acceptance Criteria` construction |
| `backlog_core/operations.py` | `_build_sections_metadata`, `_build_sections_from_yaml_item`, `_sections_from_body_or_yaml`, `_paginate_body_result` |
| `backlog_core/rendering.py` | groomed section rendering |
| `backlog_core/backends/sqlite_backend.py` | direct `## heading\n\n` writes |
| `backlog_core/backends/memory_backend.py` | direct `## heading\n\n` writes |
| `backlog_core/backends/beads_artifact_provider.py` | section handling |

---

## Open questions for the architecture agent

1. Does a "markdown navigator system" already exist partially in the codebase,
   or does it need to be built from scratch? Search for any existing section
   abstraction layer before designing a new one.

2. Are there other rendering inconsistencies beyond prose vs entry sections?
   The codebase analysis agent must audit all write paths for any section
   format that bypasses the `<div>` wrapper.

3. What is the correct behaviour when a body arrives from an external source
   (e.g. a manually edited GitHub issue) that does not use `<div>` blocks?
   The unified layer must define a clear normalisation policy.

4. Does the `since` filter need to be preserved exactly as-is, or is this an
   opportunity to redesign it against the unified ID format?

---

## What the architecture must NOT do

- Add a third read path to handle the migration case
- Preserve the zero-timestamp fallback for any reason
- Leave `_sections_from_body_or_yaml` in place as a permanent bridge
- Design the unified layer as a wrapper around the existing two paths

The existing two-path complexity is the problem. The architecture replaces it,
not wraps it.
