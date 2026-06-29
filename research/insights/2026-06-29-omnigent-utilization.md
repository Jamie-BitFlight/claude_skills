# Utilization Proposals: Omnigent

**Research entry**: ./research/agent-frameworks/omnigent.md
**Generated**: 2026-06-29
**Integration surfaces found**: 4 (CLI | SDK | YAML agent definitions | Policy configuration)
**Proposals written**: 2
**Skipped**: 2 — orchestrating-swarms (facade router, not orchestration engine); swarm-operations (documentation only, no executable component)

---

## Utilization 1: swarm-from-markdown → Omnigent Agent YAML Export

**Research entry**: ./research/agent-frameworks/omnigent.md
**Caller**: .claude/skills/swarm-from-markdown/SKILL.md
**Integration mechanism**: CLI subprocess (omnigent run)
**Replaces or adds**: Adds capability — extends swarm task dispatch beyond Claude Code to Codex, Cursor, and Pi via Omnigent's unified harness
**Setup cost**: Medium (omnigent CLI dependency v0.1.0+, YAML schema learning, Python ≥ 3.12 runtime)
**Integration surface**: `omnigent run <agent.yaml>` (documented in research entry lines 137–138); custom agent YAML format (lines 172–182)

### Why this caller

**Current behavior**: swarm-from-markdown parses markdown checklists and generates a JSON task pool, then emits Claude Code–specific tool invocations: `TeamCreate()`, `TaskCreate()`, and `Agent()` calls. The skill is hardwired to dispatch tasks only within Claude Code's native orchestration system. Lines 62–64 of the SKILL.md show direct `Agent()` calls with `subagent_type: "general-purpose"` — locked into Claude Code.

**Gap identified**: Organizations managing multiple AI agent harnesses (Claude Code, OpenAI Codex, Cursor, Pi) must either duplicate orchestration logic per harness or abandon unified tooling. A markdown checklist cannot be dispatch across harnesses without rewriting the orchestration layer.

**How Omnigent closes it**: Omnigent's `omnigent run <agent.yaml>` command (research entry line 137) accepts custom YAML agent definitions (documented lines 172–182: `name:`, `prompt:`) and executes them on any configured harness (research entry lines 18–19: "Claude Code, Codex, Cursor, Pi"). By transforming swarm-from-markdown's JSON pool into Omnigent YAML agent files instead of Claude Code tool calls, a single checklist becomes executable across all four harnesses **without rewriting the scheduler logic**.

### Integration sketch

```python
# Current: swarm-from-markdown outputs Claude Code calls
# (lines 52–64 of SKILL.md)
TaskCreate({ subject: "Implement the login endpoint", ... })
Agent({ team_name: "swarm-tasks", name: "worker-0", subagent_type: "general-purpose", prompt: "...", run_in_background: true })

# Proposed: Output Omnigent agent YAML definitions instead
# For each unchecked checklist item, write a YAML file:
# worker-0.yaml:
name: worker-0
prompt: |
  Implement the login endpoint.

  OBSERVATIONS:
  - Task ID: worker-0
  - Part of swarm: swarm-tasks

  DEFINITION OF SUCCESS:
  - Endpoint /login accepts POST with email/password
  - Returns JWT token on success
  - Returns 401 on invalid credentials

# Then dispatch via omnigent run (research entry line 137):
import subprocess
subprocess.run(["omnigent", "run", "worker-0.yaml"])
subprocess.run(["omnigent", "run", "worker-1.yaml"])
# Agents execute on configured backend (Claude Code, Codex, Cursor, or Pi)
# determined by omnigent setup, not hardcoded in swarm-from-markdown
```

**Grounded in research entry**:
- `omnigent run <path/to/agent.yaml>` is the documented invocation (lines 137–138, 180)
- YAML schema with `name:` and `prompt:` fields documented (lines 172–182)
- Multi-harness support: "Claude Code, Codex, Cursor, Pi" (lines 18–19)
- No rewrite of core logic required — swarm-from-markdown's parser stays intact; only the output format changes

---

## Utilization 2: delegate skill → Omnigent Policy-Enforced Execution

**Research entry**: ./research/agent-frameworks/omnigent.md
**Caller**: .claude/skills/delegate/SKILL.md
**Integration mechanism**: CLI subprocess (omnigent server start + omnigent run) + policy configuration file (server_config.yaml)
**Replaces or adds**: Adds capability — extends delegate template with declarative policy gates (cost limits, tool-call caps, approval workflows)
**Setup cost**: Low (reuses omnigent CLI from Proposal 1; requires server_config.yaml setup once per session)
**Integration surface**: `omnigent run <agent.yaml>` (lines 137–138); `server_config.yaml` policy configuration (lines 184–212)

### Why this caller

**Current behavior**: The delegate skill (SKILL.md) defines a prompt template for routing work to sub-agents. It enforces structure (`OBSERVATIONS`, `DEFINITION OF SUCCESS`, `CONTEXT`, `ECOSYSTEM CONTEXT`, `YOUR TASK`) but has no runtime enforcement mechanism. Once a sub-agent is spawned via the `Agent()` tool, there are no gates on what it can do — no cost limits, no tool-call quotas, no approval workflows. The orchestrator must trust that every sub-agent will respect informal constraints.

**Gap identified**: Multi-agent teams need declarative policies that apply uniformly across all agents without per-agent customization. An agent that should never execute shell commands without approval, or that must never exceed $5 spend per session, requires either embedding these checks in the agent's own prompt (non-scalable, easy to bypass) or enforcing them externally at the tool-invocation layer (Omnigent's domain).

**How Omnigent closes it**: Omnigent's policy system (research entry §Declarative Policy Enforcement, lines 54–62) defines three verdict types (`ALLOW`, `DENY`, `ASK`) that apply globally to all agents in a session. Policy enforcement points include tool calls, shell commands, file operations, and cost tracking (lines 72–75). By adding a `--policy-config` option to the delegate template, sub-agents delegated via `omnigent run` automatically inherit server-wide policies without modification to their prompts.

### Integration sketch

```python
# Current: delegate template defines structure only
# (lines 19–49 of SKILL.md)
"""
Your ROLE_TYPE is sub-agent.

OBSERVATIONS:
- [Factual observations already in your context]
...

DEFINITION OF SUCCESS:
- [Specific measurable outcome]
"""

# Proposed: Optional omnigent policy backend selection
# At orchestration time:
# 1. Start Omnigent server with policy config
omnigent.policies = [
    cost_budget(max_cost_usd=5.00, ask_thresholds_usd=[3.00]),
    max_tool_calls_per_session(limit=50),
    ask_on_os_tools(shell=True, file_writes=True),
]

# 2. Serialize delegate agent config to omnigent agent.yaml
# (via proposed --backend omnigent flag on delegate template)
# 3. Execute via omnigent run with inherited policies
subprocess.run(["omnigent", "run", "agent.yaml", "--policy-config", "server_config.yaml"])

# If agent attempts to exceed $3 spend:
#   Policy verdict: ASK → orchestrator must approve
# If agent attempts 51st tool call:
#   Policy verdict: DENY → agent receives error, cannot proceed
# If agent attempts shell command without override:
#   Policy verdict: ASK → user must approve via omnigent UI
```

**Grounded in research entry**:
- Policy system with ALLOW/DENY/ASK verdicts (lines 54–57)
- Enforcement points: tool calls, shell, file ops, cost tracking (lines 72–75)
- Built-in policy examples: `cost_budget`, `max_tool_calls_per_session`, `ask_on_os_tools` (lines 206–211, exact policy names from research entry)
- Policy configuration via YAML (lines 184–212 show server_config.yaml structure)
- No changes to delegate template structure required — only optional backend selection

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| orchestrating-swarms (.claude/skills/orchestrating-swarms/SKILL.md) | Facade router that delegates to specialist skills (swarm-primitives, swarm-spawning, swarm-operations, swarm-patterns). Not an executable orchestration engine itself; Omnigent is a framework for orchestration, not a specialist skill. No direct caller relationship. |
| swarm-operations (.claude/skills/swarm-operations/SKILL.md) | Documentation and API reference for Claude Code swarm tools (TeamCreate, SendMessage, TaskCreate). Contains no executable code or subprocess dispatch; documents internal tooling only. Omnigent policy engine (research entry §Declarative Policy Enforcement) is conceptually related but does not substitute for swarm-operations' tool documentation. No integration surface match for a documentation-only skill. |

