# Improvement Proposals: Solace Agent Mesh

**Research entry**: ./research/agent-frameworks/solace-agent-mesh.md
**Generated**: 2026-03-28
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Permission scope propagation through agent delegation chains

**Source pattern**: "Agent A delegates a subtask to Agent B, it constructs a new A2A task request that propagates the original user's permission scopes, maintaining security context throughout the delegation chain." (Section: Agent-to-Agent Communication, line 49)
**Local system**: `.claude/skills/swarm-operations/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: Claude Code's subprocess model manages permissions at the harness level, not at the inter-agent message level. The local system has `permission_request` messages (line 254 of swarm-operations/SKILL.md) but these are for sandbox tool permissions requested by a single agent, not for propagating user-scoped access control through a delegation chain. Verifying whether this gap causes actual failures would require observing a scenario where a delegated agent acts outside its intended scope, which has not been documented.

### Current state

`swarm-operations/SKILL.md` defines a `permission_request` message type (line 254) that allows a single agent to request sandbox/tool permissions from the user. When an orchestrator spawns a teammate via `Agent()`, no permission scope is propagated in the spawn call or in subsequent `SendMessage` calls. Each spawned agent inherits the session-level permission set, not a task-scoped subset.

### Target state

The `Agent()` tool call or `SendMessage` protocol would include an optional `scopes` field that narrows the spawned agent's available tools to a subset of the orchestrator's permissions. The orchestrator would declare `scopes: ["Read", "Grep", "Glob"]` when spawning a research-only agent, preventing that agent from using `Write`, `Edit`, or `Bash`. The swarm-patterns skill would document the scope propagation pattern.

### Measurable signal

`swarm-operations/SKILL.md` documents a `scopes` parameter on the `Agent()` tool. `swarm-patterns/SKILL.md` includes at least one pattern demonstrating scoped delegation. A spawned agent's tool list is filtered to match the declared scopes.

---

## Improvement 2: Agent capability discovery via structured capability cards

**Source pattern**: "Agent Hosts periodically publish AgentCards (JSON documents describing capabilities) to a well-known discovery topic. When Agent A delegates a subtask to Agent B, it constructs a new A2A task request." (Section: Agent-to-Agent Communication, line 49)
**Local system**: `.claude/skills/swarm-operations/SKILL.md`, `.claude/skills/swarm-patterns/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: The local system relies on the orchestrator knowing which `subagent_type` to use at delegation time. There is no runtime discovery mechanism where agents advertise their capabilities and other agents select based on capability match. However, the local system's skill/agent registry in plugin.json and SKILL.md frontmatter serves a similar purpose at design time (loaded when skills are registered). Whether runtime discovery would provide material benefit over design-time registration in the Claude Code architecture requires investigation.

### Current state

Agent selection in swarm-operations requires the orchestrator to know the exact `subagent_type` string (e.g., `"compound-engineering:review:security-sentinel"`) at delegation time. There is no mechanism for a spawned agent to advertise its capabilities to the team, or for the orchestrator to query available agent capabilities at runtime. The `TaskList` and `SendMessage` tools operate on tasks and messages, not on agent capability metadata.

### Target state

A `TeamCapabilities` or equivalent query would return structured capability metadata for all registered agents in the current team, enabling the orchestrator to match tasks to agents based on declared capabilities rather than hardcoded `subagent_type` strings. Each agent spawned into a team would publish a capability card (name, tools, domain, skills) readable by other team members.

### Measurable signal

`swarm-operations/SKILL.md` documents a capability query mechanism. At least one pattern in `swarm-patterns/SKILL.md` demonstrates dynamic agent selection based on queried capabilities rather than hardcoded agent names.

---

## Improvement 3: Automatic metadata injection on artifact creation

**Source pattern**: "SAM provides built-in tools for artifact management... These tools are available to agents and include automatic metadata injection for created artifacts." (Section: Built-In Tools, line 59)
**Local system**: `plugins/development-harness/CLAUDE.md` (Artifact Manifest System section)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence Low: The local system's `artifact_register` MCP tool records artifact metadata in the GitHub Issue body manifest, and `sam_create` auto-registers artifacts. The research entry's "automatic metadata injection" is described at a high level without specifying what metadata fields are injected or how. The local system may already have equivalent behavior through `artifact_register`'s `status` and `agent` fields. Without examining SAM's actual metadata injection implementation, the gap cannot be confirmed.

### Current state

The local artifact system requires explicit `artifact_register` calls after artifact creation, passing `issue_number`, `type`, `path`, `status`, and `agent`. The `sam_create` tool auto-registers the task plan artifact. Other artifact types (feature-context, architect spec) require manual registration by the producing agent.

### Target state

All artifact-producing operations (Write calls that create plan artifacts) would automatically register the artifact in the manifest with standardized metadata (creation timestamp, producing agent, artifact type, file hash). No manual `artifact_register` call would be needed after creating a known artifact type.

### Measurable signal

Creating a feature-context artifact via the feature-researcher agent automatically produces an `artifact_register` entry without an explicit call in the agent's workflow. The artifact manifest for a completed feature shows all artifacts with creation timestamps and producing agent names.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Permission scope propagation through delegation chains | Medium | Claude Code subprocess model manages permissions at harness level; would need a documented failure case where a delegated agent exceeded intended scope to confirm the gap is material |
| Agent capability discovery via structured capability cards | Medium | Local system uses design-time agent registration via plugin.json and SKILL.md frontmatter; whether runtime discovery provides material benefit over this approach requires investigation |
| Automatic metadata injection on artifact creation | Low | Local system already has artifact_register with auto-registration in sam_create; SAM's specific metadata injection mechanism is not described in enough detail to confirm a gap |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Event-Driven Architecture (decoupled async agent coordination via event broker) | Architecturally incompatible -- Claude Code uses subprocess-based agents with file-based message passing, not event broker services. Replacing the communication layer would require replacing the local system entirely. |
| Tool and Gateway Integration (REST, WebSocket, Slack protocol translation) | Already covered -- fastmcp-creator skill provides transport selection (stdio, HTTP, in-memory) and provider composition (ProxyProvider, FileSystemProvider) for MCP server integration |
| MCP Integration (embedding MCP toolsets into agent capabilities) | Already covered -- fastmcp-creator skill is a comprehensive MCP server creation reference with trigger matrix covering tool/resource creation, auth, client SDK, and testing |
| CLI-Driven Configuration (GUI-based agent/plugin creation via `sam init --gui`) | Architecturally incompatible -- Claude Code operates as a CLI tool where agents are configured via markdown files and YAML frontmatter, not GUI wizards. The local plugin-creator and agent-creator skills serve the equivalent function through prompt-driven workflows. |
