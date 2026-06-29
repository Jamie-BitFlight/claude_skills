# Improvement Proposals: iii — Unified Backend Composition Engine

**Research entry**: ./research/agent-infrastructure/iii.md
**Generated**: 2026-06-18
**Patterns assessed**: 6
**Backlog items created**: 0
**Deferred (low/medium confidence)**: 3
**Skipped (already covered or architecturally incompatible)**: 3

---

## Summary

The iii entry's "Relevance to Claude Code Development" section lists 6 patterns. All 6 derive
from iii's central architecture: a **persistent Rust engine** that holds a live function catalog,
routes invocations over a WebSocket protocol, and emits OpenTelemetry traces for every call.
Claude Code's multi-agent model is the opposite: **stateless, file-based agents** selected by
static `subagent_type` strings, communicating through inbox JSON files (`swarm-operations`,
`swarm-patterns`). This architectural mismatch is the dominant finding — most iii patterns cannot
be adopted without a persistent engine that Claude Code does not have, and the local swarm skills
correctly describe a different model.

Three patterns are already covered (MCP tool discovery, agent skill packaging) or
architecturally impossible (runtime creation of new agent *types*). Three describe real gaps in
the local swarm model — runtime capability discovery, unified execution observability, and durable
task queueing — but each, as described in the entry, depends on the iii engine rather than a change
expressible in a local skill file. None reached High confidence; no backlog items were created.

---

## Improvement 1: Runtime capability discovery for swarm agents

**Source pattern**: "Relevance §1 Multi-Agent Coordination and Capability Discovery" — "Agents register their capabilities as named functions ... Other agents discover capabilities without hardcoded configuration ... eliminates the need for agent-to-agent API contracts and version negotiation"
**Local system**: .claude/skills/swarm-patterns/SKILL.md, .claude/skills/swarm-spawning/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence Low: the local "absence" is inferred against an architecturally different model

### Current state

In `swarm-patterns/SKILL.md`, every worker is spawned with a hardcoded `subagent_type` string
(e.g. `subagent_type: "compound-engineering:review:security-sentinel"`, lines 24–43) chosen by the
orchestrator at authoring time. There is no runtime catalog a worker can query to discover which
peer capabilities exist; the available agent-type list is supplied to the orchestrator as static
session context, not queryable by spawned teammates.

### Target state

A worker could query a live index of available agent types / capabilities and route work to a peer
without the orchestrator pre-wiring the `subagent_type`. In iii this is the WebSocket function
catalog; the Claude Code equivalent would be a discovery surface over the agent-type registry.

### Measurable signal

Not specified at High confidence. The iii mechanism (persistent catalog broadcast over WebSocket)
has no stateless file-based equivalent that a skill edit alone could deliver. Confirming this gap
as actionable would require deciding whether Claude Code's agent-type registry can be exposed to
running teammates — a platform capability question, not a skill-content gap. Deferred for that
reason.

---

## Improvement 2: Unified execution observability for multi-agent swarms

**Source pattern**: "Relevance §3 Unified Observability for Agent Execution" — "Every function invocation across all agents produces a unified trace ... Debugging multi-agent workflows requires inspecting a single trace, not correlating separate logs"
**Local system**: .claude/skills/swarm-operations/SKILL.md (Debugging section)
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: the local equivalent of "a single trace" must be inferred; the iii mechanism (OpenTelemetry collector) is not directly portable

### Current state

`swarm-operations/SKILL.md` Debugging section (lines ~320–336) instructs the operator to debug a
swarm by manually reading separate files: `~/.claude/teams/{team}/config.json`, each
`inboxes/{agent}.json`, and `~/.claude/tasks/{team}/*.json`. There is no aggregated, time-ordered
view of what every teammate did across one swarm run — exactly the "correlating separate logs"
problem iii calls out.

### Target state

A single command or skill that reads the team's inbox and task JSON files and emits one
time-ordered trace of the swarm run (spawn → claim → message → completion per teammate), so a
multi-agent failure is diagnosable from one artifact rather than N inbox files.

### Measurable signal

Would be: run a swarm-trace command for a team and receive a single chronologically merged log of
all teammate events. Held at Medium confidence because the entry's mechanism is a persistent
OpenTelemetry collector emitting traces at invocation time — the local artifacts (inbox/task JSON)
are written for messaging, not tracing, so whether they contain enough event detail to reconstruct
a faithful trace is unverified. Confirming that would require auditing the actual JSON event schema
written by the swarm runtime. Deferred pending that verification.

---

## Improvement 3: Durable task queue with retry and dead-lettering for swarm workers

**Source pattern**: "Relevance §5 Queue-Based Agent Task Distribution" — "Agents can enqueue long-running tasks ... Automatic retry, dead-lettering, and observability"
**Local system**: .claude/skills/swarm-patterns/SKILL.md (Pattern 3 Swarm), .claude/skills/swarm-operations/SKILL.md (Handling Crashed Teammates)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence Low: the gap maps to a Claude Code task-system platform feature, not a skill-content change

### Current state

`swarm-patterns/SKILL.md` Pattern 3 implements a file-based task pool where workers race to claim
`TaskCreate` items. `swarm-operations/SKILL.md` ("Handling Crashed Teammates", lines ~311–318)
states a crashed worker's tasks "remain in the task list" and "another teammate can claim their
tasks" — but reclamation is manual/opportunistic, with no automatic retry budget and no
dead-letter destination for tasks that fail repeatedly.

### Target state

A task that fails or is abandoned N times is automatically routed to a dead-letter state rather
than silently re-claimed indefinitely, with a bounded retry count visible on the task.

### Measurable signal

Would be: a task field tracking retry count and a terminal dead-letter status after a threshold.
Held at Low confidence because retry/dead-letter semantics live in the Claude Code TaskCreate/
TaskUpdate platform tools, not in a skill the repo owns — a skill edit cannot add durable queue
semantics the runtime does not provide. Deferred as out of scope for skill-level improvement.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason / what would raise confidence |
|---|---|---|
| §1 Runtime capability discovery | Low | Requires deciding whether Claude Code's agent-type registry can be exposed to running teammates — a platform question, not a skill-content gap. |
| §3 Unified execution observability | Medium | Requires auditing the actual inbox/task JSON event schema to confirm it carries enough detail to reconstruct a faithful single-run trace. |
| §5 Durable task queue retry/dead-letter | Low | Retry/dead-letter semantics live in the TaskCreate/TaskUpdate platform tools, not in any repo-owned skill; a skill edit cannot deliver them. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| §2 Live system extensibility / agent self-extension (`iii worker add` at runtime) | Architecturally incompatible — Claude Code `subagent_type` values must pre-exist; agents cannot create new agent *types* at runtime. Stated explicitly as incompatible per gap rule. |
| §4 Function calling / tool discovery | Already covered — the entry itself frames this as "analogous to Claude's function calling and MCP tool discovery"; MCP already provides dynamic tool discovery (plugins/plugin-creator/skills/mcp-integration). |
| §6 Agent skill packaging (`npx skills add`) | Already covered — this repo already packages AI-readable skills extensively (.claude/skills/, plugins/*/skills/); the pattern is the repo's existing core practice, not a gap. |
