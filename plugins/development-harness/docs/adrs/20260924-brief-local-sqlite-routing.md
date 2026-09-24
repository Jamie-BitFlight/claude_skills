# Reserve `brief~` for fail-closed local SQLite routing

**Date:** 2026-09-24
**Status:** Proposed

This record describes a proposed target. None of the behavior below is implemented by this ADR.

## Context

The current composition root resolves the configured provider once. Work-item operations use
`WorkItemBackend`; Plans and Tasks use `TaskBackend`; artifacts use `ContentProvider`; active-task
state uses `ContextBackend`. The interfaces are distinct even when one configured provider owns
their storage. The existing SQLite factory uses
`dh_paths.state_root() / "backlog.sqlite3"`, while direct `SQLiteBackend()` construction defaults
to `:memory:`.

Ad-hoc Work Briefs must remain on the requesting host while using the normal work-item, content,
Plan, Task, concern, gate, and completion contracts. Switching the project's global backend would
disrupt unrelated work. A prefix branch repeated in each caller could split one Work Brief's state
across providers.

The current provider operation is upsert-like, and SQLite and Memory can overwrite an existing
explicit reference. Adapters already expose `probe_backend_status()`, but the result does not yet
provide the proposed adapter-owned status envelope or reference-aware routing diagnostic.

## Decision

### Reserved local identity

Reserve this immutable identity shape for the local overlay:

```text
brief~<mandatory-2-3-word-slug>-<4-lowercase-hex>
```

The slug contains meaningful lowercase ASCII words and is truncated only at a word boundary; no
fallback slug is generated. When SQLite is already the configured backend, ordinary local
identifiers remain sufficient. For every non-`brief~` reference, project configuration selects the
provider; other identifier patterns remain opaque to routing.

### Composite routing

One composition boundary resolves the configured primary provider plus the reserved overlay. A
`brief~` reference selects the existing project-local SQLite adapter and database. It never falls
back to a remote provider and never creates a second local store. Callers use provider-neutral
operations and do not branch on the prefix.

The coordinated route covers work items, `sections["groomed"]` content, artifacts, Plans and Tasks,
concerns, gates, and completion while preserving the distinct backend protocols. Plan creation
atomically records `plan_id → backend + brief_reference`; any later operation holding only the Plan
address follows that binding and fails closed when the binding or selected store is unavailable.
Listings that combine primary-provider and local records carry routing provenance for each record.

A local Work Brief otherwise follows the ordinary provider lifecycle, including ordinary labels
and tags. Completed local briefs remain until explicit cleanup; defining a retention policy is
separate follow-up work.

### Provider creation contract

Generic `backlog add` accepts an optional `--reference`. A provider that supports
caller-assigned references accepts it. A provider that cannot honor it creates the record normally,
returns its canonical reference, and emits a warning. SQLite supports caller-assigned references.
The minimal creation response is:

```json
{
  "reference": "canonical-reference",
  "warnings": []
}
```

Creation and update are separate operations. Creation is create-only: a collision never
overwrites, retries automatically, falls through to update, or becomes bypassable with `force`.
The collision response identifies the colliding reference and existing title, reports
`retryable: false`, directs the caller to update or groom that reference for the same work, and
directs the caller to invoke creation again for distinct work. Existing update and groom operations
continue to modify an exact reference.

For explicit references, create-only behavior requires an atomic insert-if-absent operation at the
`WorkItemBackend`/provider boundary. A frontend check followed by an ordinary write is insufficient
because another creator can win between those operations. This provider-boundary primitive
satisfies the collision invariant without adding a separate reference-immutability subsystem.

### Provider status contract

The existing `probe_backend_status()` seam evolves or is renamed to the adapter-owned `status()`;
no parallel status mechanism is added. The proposed JSON-only frontend is:

```text
backend status [optional-reference]
```

Without a reference it reports the configured primary provider. With a reference it reports the
routed provider. The frontend owns routing and configuration context, then calls the selected
adapter's `status()`. Each adapter returns a stable result containing `availability` and an extensible
`details` object. SQLite details may include its database path and counts; GitHub details may
include authentication state, username, and offline-cache state.

Online adapters check availability and authentication by default under one 30-second overall
timeout. Reachable status exits zero. Timeout, authentication, rate-limit, and provider errors exit
nonzero and remain structured status results, including the adapter's connection-status error type.
Responses expose no secrets, raw environment values, or unsafe exception text. The initial schema
remains minimal; adapters may extend `details` for provider-specific diagnostics.

## Alternatives considered

- **Switch the global backend:** rejected because unrelated provider-backed work must retain its
  configured route.
- **Create a second SQLite store:** rejected because the project-local adapter and database already
  provide the required storage.
- **Branch on `brief~` in every caller:** rejected because one invariant would be duplicated and
  related state could split.
- **Remote fallback:** rejected because it violates the host-local guarantee.
- **Automatic collision retry, overwrite, or force:** rejected because each hides an identity
  conflict and can mutate the wrong work.

## Consequences

Ad-hoc state remains local without changing downstream logical contracts. The composition boundary
and Plan-route binding are the only provider-selection authorities. Creation becomes safe against
silent replacement, and provider diagnostics become route-aware without exposing provider secrets.
