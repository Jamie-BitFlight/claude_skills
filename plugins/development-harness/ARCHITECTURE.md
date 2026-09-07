# Development Harness Architecture

How the harness achieves what [docs/PURPOSE.md](./docs/PURPOSE.md) states it is for. Repository-level
design is in the [root ARCHITECTURE.md](../../ARCHITECTURE.md); storage internals are in
[backlog_core/ARCHITECTURE.md](./backlog_core/ARCHITECTURE.md).

## Automation Boundary

The harness exists to turn repeatable agent instructions into reliable workflow
capabilities. A general provider CLI or MCP server can perform many underlying
operations, but the harness adds value by making the complete workflow
consistent and addressable through stable logical operations.

The governing rule is:

- If known inputs can be mechanically parsed or transformed into a required
  output, implement that work in a script or tool.
- If a repeated sequence can be made more consistent, observable, or atomic,
  expose it as one structured operation rather than a prose checklist.
- If the work requires interpretation of unique evidence, trade-off analysis,
  judgment, or generation of novel content, keep it in the agent reasoning
  layer.

Scripts and tools therefore own schema validation, stable input/output shapes,
provider abstraction, event-driven progress updates, deterministic searches and
filters, section addressing, artifact lookup, and other repeatable mechanics.
Agents own research, diagnosis, synthesis, design decisions, prioritization,
review, and other context-dependent reasoning.

Prose must not require an agent to reproduce a deterministic multi-call lookup,
grep pipeline, parsing routine, or state update when the harness can expose the
same operation safely as a script, hook, CLI command, or MCP tool. Automation
must simplify the agent's work without hiding the logical workflow or the
evidence needed to reason about it.

## Target Logical Model

Under the target contract, agents work only with logical objects and
relationships:

- backlog item;
- research, reference, guide, or note;
- architecture;
- plan;
- atomic task;
- coordination or dispatch state;
- review, validation, or result evidence; and
- follow-up item.

An agent uses logical identifiers and relationships, not provider IDs, file
paths, issue bodies, database rows, Gists, or API-specific objects.

## Target Frontend Contract

CLI and MCP should expose stable logical CRUD and workflow operations for:

- creating, reading, updating, and deleting logical objects;
- updating fields and sections, including append and delete operations;
- recording and retrieving references and evidence;
- managing architecture, plan, and task lifecycles;
- returning task feedback upstream;
- assigning sequence and ownership; and
- querying by logical ID, relationship, status, capability, and provenance.

The target frontend contract treats CLI and MCP as interchangeable structured
transports for the logical operations they expose. They are not required to
proxy every provider-native capability. Skills and agents may use an existing
backend tool directly when it is the authoritative and capable interface (for
example, `bd` for Beads issue graphs and readiness). Both structured surfaces
remain supported; this document makes no retirement or deprecation claim about
either one.

The frontend contract must not depend on a selected provider's object model or
addressing scheme.

## Target Backend Guarantee

Storage is an implementation detail. Logical objects may be stored together or
across providers such as GitHub, GitLab, Linear, SQLite, Beads, local storage,
or Gist-backed storage.

The target backend contract is canonical and provider-neutral. It defines object
and relationship semantics, content and revisions, links, append behavior,
statuses, query capabilities, ownership, and provenance. Adding a provider must
change only provider implementation, registration, and configuration—not CLI or
MCP commands or workflow behavior.

## Current Boundary

The configured backend is the single routing decision for work items, grooming, plans, tasks,
artifact manifests, and artifact content. MCP and CLI expose interchangeable logical operations;
`bd` remains the native interface for Beads issue graphs and readiness where that capability is
stronger than the structured adapter.

Remote-capable providers privately own `FileCache` for stale snapshots, durable queued offline
mutations, revisions, and provider-specific persistence. Beads, SQLite, and Memory use native
storage directly and never read or write backlog YAML or instantiate `FileCache`. Backend failures,
cache misses, conflicts, and unsupported capabilities are explicit results; callers do not route
to an independent task backend, artifact provider, local filesystem fallback, or per-plan provider.

Provider IDs, issue bodies, paths, database rows, and wire formats remain implementation details.
Consumers should use logical identifiers and the supported MCP/CLI operations. The architecture
spec marks any remaining direct YAML or independent-provider code paths as migration debt; those
paths are not supported workflow contracts.
