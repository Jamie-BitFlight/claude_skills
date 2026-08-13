# Development Harness Purpose

**Audience**: Mixed overview. Use this document to orient contributors and agents to the logical
product contract; follow linked contributor references for implementation detail.

## Purpose

Development Harness targets a generic agent work-management system that
preserves logical work and the evidence needed to move it from intake to
validated closure.

The plugin is primarily an agent-facing workflow system expressed in Markdown.
Skills and reference documents carry the reasoning process; scripts, hooks,
CLI commands, and MCP tools remove repeatable mechanics and provide stable
interfaces between stages.

## Documentation Frames and Audiences

Development Harness documentation has two primary frames. A document must make
its frame clear and include only the detail needed by that audience.

### Contributor and developer frame

This frame explains how the plugin and its workflow are designed, implemented,
extended, tested, and operated as a software system. It includes:

- workflow and package architecture;
- Markdown skill, command, agent, and reference composition;
- Python modules and PEP 723 script entry points;
- MCP and CLI transport boundaries;
- hooks and agent-event integration;
- provider protocols, cache ownership, and persistence design;
- `uv` runtime, dependency, test, lint, and packaging requirements; and
- contributor troubleshooting that requires tracing implementation behavior.

Its primary audience is an AI agent changing or diagnosing the plugin. These
documents must understand the consumer workflow so implementation preserves
observable behavior, but they may expose internal structure where that is
necessary for correct engineering.

### Installation, configuration, and usage frame

This frame explains how an agent installs, configures, uses, and troubleshoots
the plugin through its supported capabilities. It describes logical workflows,
inputs, outputs, configuration choices, supported provider behavior, failure
messages, and recovery actions.

Consumer documents do not teach internal implementation unless a detail is
required to configure the plugin, interpret behavior, or perform a bounded
troubleshooting trace. They refer to logical operations and supported tool
surfaces rather than Python modules, cache files, provider wire formats, or
internal call graphs.

### Audience rule

Almost all plugin documentation is written for AI agents. The plugin README and
a small set of overview or selection documents are the exception: they serve
both humans evaluating the plugin and agents orienting themselves. Those mixed-
audience documents use plain capability and workflow language, with links to
agent-facing operational or contributor references for depth.

Contributor documentation may depend on consumer documentation to understand
the product contract. Consumer documentation must not require contributor
documentation for ordinary installation, configuration, usage, or recovery.

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
