# Development Harness Architecture

How the harness achieves what [docs/PURPOSE.md](./docs/PURPOSE.md) states it is for. Repository-level
design is in the [root ARCHITECTURE.md](../../ARCHITECTURE.md); storage internals are in
[backlog_core/ARCHITECTURE.md](./backlog_core/ARCHITECTURE.md).

## The workflow

One loop, from a requirement to a closed change with evidence. Each stage below states what it
reads and what it produces. The outcomes these exist to deliver are in
[docs/PURPOSE.md](./docs/PURPOSE.md).

**Create.** Steps through creating a requirement, feature or defect without speculating how it
should work in the system before understanding the system as a whole. Produces the backlog item in
the backend store. Implemented by `skills/create-backlog-item`, routing through
`work-backlog-item`'s `create` route.

**Groom.** Gathers detail, questions the user, researches the state of the art, understands the
existing system and the impact of changing it, checks and corrects every claim, and assesses whether
the problem is being considered from the right altitudes. Produces the groomed item plus report
artifacts. Implemented by `skills/groom-backlog-item` and `agents/backlog-item-groomer.md`.

**Design.** Reads the grooming reports, the item, the existing architecture documents, and the
project's rules and documented conventions. Designs or modifies architecture compliant with those,
correcting for the groomed defect or admitting the groomed feature. Then adversarially challenges
the design — pokes holes in it, challenges its reasoning and its existence, and offers alternatives
— so the change holds against the problems the groomed item states. Produces an artifact on the item
plus local architecture documentation.

**Plan.** Reads the architecture and works out how to achieve it, how to validate that it was
achieved, and how to document it, so the outcome is demonstrable against both the architecture and
the original problem statement. Identifies claims with no evidence and functional gaps, and surfaces
them back upstream into the data-gathering and research stages. Produces a plan.

**Decomposition.** Splits the plan into atomic pieces of work carrying dependencies, verification
steps, acceptance criteria and a goal. A piece may carry specialist skills or agent knowledge,
because the agent doing it can see its own work, the plan it belongs to, and the research
justifying it. It states its output, its guardrails and how to tell it is done, and does not
prescribe how to achieve it, so the agent can reach the goal while handling environmental problems
its own way. Produces the work graph. Implemented by `skills/task-decomposition` and
`agents/swarm-task-planner.md`.

**Orchestration.** Reads the graph, assigns agents within it, and gives them worktrees and
addresses. Implemented by `skills/dispatch` and `skills/work-milestone`.

**Act.** A tasked agent loads its work and proceeds, reaching the plan and the gathered
documentation when it needs background or reasoning. It attempts the acceptance criteria and runs
the validation; those outcomes decide completion. On ending it updates status so the orchestrator
can coordinate what follows. The output is completed work — generated or modified content in a
repository, or equally the validation of an external system. The report of outcomes is appended to
the work item. Implemented by `skills/execution` and `agents/task-worker.md`.

**Loop.** New information, concerns, gaps, adjacent broken systems, environmental failures and
security issues are surfaced and routed by cause: an architectural issue to Design, which then
reaches Plan to consider what changes; an environmental or external factor directly to Plan. Plan
amends, Decomposition adds or changes work and updates the graph, and Orchestration dispatches what
is new.

**Closure.** The end of the graph checks and updates documentation and reviews the whole changeset,
conditionally on what changed: code review where code changed, prose review where prose was edited,
and where the work evaluated a system, a check that the reports exist and the desired outcomes were
met. It checks the change is demonstrably effective at what it needed to achieve. Every blocker or
issue found returns to Loop.

### Naming

This document calls the last stage **Closure**, not "bookend". `BookendType` in
`sam_schema/core/models.py` names a different and narrower thing — the `t0-baseline` and
`tn-verification` pair around one plan's acceptance criteria — and using one word for both would
read as though the stage were already built out of that mechanism.

Likewise **create** is the stage and the route; `intake` is a step inside grooming
(`skills/work-backlog-item/references/workflows/groom/intake.md`) and does not name this stage.

Where this plugin's prose and its code disagree, the code's identifier is canonical. The artifact
that Design and Plan produce is registered as `architect`; several skills call it `ARTIFACT:PLAN`,
which names no registered type and is a defect in those documents rather than a synonym.

### Acceptance criteria

A structured acceptance criterion carries an executable check command
(`AcceptanceCriterion.check_command` in `sam_schema/core/models.py`), and the baseline and
verification agents iterate over the list to compare before against after. Verification is therefore
what a machine can run: a UI test and a microcontroller reading are criteria; an assessment such as
"the design holds up" is not, and needs a criterion shape that carries evidence and a judgement
instead of an exit code.

### Relation to the SAM stage numbering

`skills/dh-meta-docs/references/sdlc-stage-taxonomy.md` defines a numbered pipeline whose stages are
the skill directory names `discovery`, `planning`, `context-integration`, `task-decomposition`,
`execution`, `forensic-review` and `final-verification`. That numbering does not partition the
workflow above, and forcing either onto the other loses distinctions both make.

| stage above | numbered pipeline |
|---|---|
| Create, Groom | outside it; `create-backlog-item` and `groom-backlog-item` run before it, and `discovery` re-surveys more narrowly inside it |
| Design, Plan | both inside `planning`, which produces one `architect` artifact for the two |
| Decomposition | `task-decomposition` |
| Orchestration | outside it; `dispatch` and `work-milestone` have no numbered slot |
| Act | `execution` |
| Loop | outside it; the pipeline has loop-back edges scoped to a task verdict in `forensic-review` and a feature verdict in `final-verification`, not routing by cause |
| Closure | `final-verification`, partially |

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

## The logical model

Agents work only with logical objects and relationships:

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

## The frontend contract

CLI and MCP should expose stable logical CRUD and workflow operations for:

- creating, reading, updating, and deleting logical objects;
- updating fields and sections, including append and delete operations;
- recording and retrieving references and evidence;
- managing architecture, plan, and task lifecycles;
- returning task feedback upstream;
- assigning sequence and ownership; and
- querying by logical ID, relationship, status, capability, and provenance.

The frontend contract treats CLI and MCP as interchangeable structured
transports for the logical operations they expose. They are not required to
proxy every provider-native capability. Skills and agents may use an existing
backend tool directly when it is the authoritative and capable interface (for
example, `bd` for Beads issue graphs and readiness). Both structured surfaces
remain supported; this document makes no retirement or deprecation claim about
either one.

The frontend contract must not depend on a selected provider's object model or
addressing scheme.

## The backend guarantee

Storage is an implementation detail. Logical objects may be stored together or
across providers such as GitHub, GitLab, Linear, SQLite, Beads, local storage,
or Gist-backed storage.

The backend contract is canonical and provider-neutral. It defines object
and relationship semantics, content and revisions, links, append behavior,
statuses, query capabilities, ownership, and provenance. Adding a provider must
change only provider implementation, registration, and configuration—not CLI or
MCP commands or workflow behavior.

## Storage and routing

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
Consumers should use logical identifiers and the supported MCP/CLI operations. Direct YAML access and independent-provider code paths are not supported
workflow contracts.
