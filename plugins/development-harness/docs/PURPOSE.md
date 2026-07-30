# Development Harness Purpose

## Purpose

Development Harness targets a generic agent work-management system that
preserves logical work and the evidence needed to move it from intake to
validated closure.

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

## Closed-Loop Work Management

The system is intended to support a full closed loop:

1. Intake a backlog item and groom its scope and evidence.
2. Research and assess the existing system factually, then produce architecture.
3. Produce a plan.
4. Decompose work into atomic tasks; sequence, distribute, and coordinate them.
5. Execute tasks.
6. Append findings, workarounds, concerns, and validation evidence upstream.
7. Revise the plan, add tasks, or create a follow-up backlog item when evidence requires it.
8. Review the plan and architecture.
9. Validate the product-level outcome, including documentation, tests, end-to-end checks, and CI when applicable.
10. Close work with evidence.

This model is domain-generic. It applies to software, Markdown agent and plugin
work, design, TUI, web, and font work, job search, research, ranking, and other
work that benefits from durable scope, relationships, coordination, and evidence.

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

The preceding sections describe the target contract, not fully implemented
behavior today.

- MCP is currently the primary structured interface for many operations; the
  CLI does not expose every MCP capability surface, and neither surface proxies
  every provider-native tool. The authoritative list of MCP-only operations is
  in [backend-providers.md](./backend-providers.md) "CLI vs MCP Capability
  Surface". In Beads-backed projects, `bd` is the native interface for issue
  graph, status, dependency, readiness, label, notes, and metadata operations.
  Close/resolve satisfies the "delete" CRUD verb per DEC-1; no destructive
  delete is planned.
- CLI and MCP durability differs: MCP plan paths use Gist write-through, while
  CLI and direct paths can remain local-only. The backlog persistence boundary
  (GitHub Issues source of truth for the default backend; only `GitHubBackend`
  remote-backed; branch operations not capability-gated) is documented in
  [backend-providers.md](./backend-providers.md) "Backlog Persistence Boundary".
- Present interfaces expose GitHub issue numbers and file or path addressing;
  agents do not yet see only logical objects.
- Plans and tasks are mostly provider-neutral, but select CLI and manager paths
  remain backend-coupled.
- Artifact manifests may use remote providers, while established content-serving
  paths currently use or fall back to the local filesystem.
- Backlog persistence remains partly GitHub- and filesystem-shaped.

Until these boundaries are removed, consumers must treat provider neutrality and
frontend interchangeability as target, domain-specific properties—not blanket
properties of the current system.
