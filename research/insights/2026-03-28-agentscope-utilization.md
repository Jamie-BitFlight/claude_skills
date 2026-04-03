# Utilization Proposals: AgentScope

**Research entry**: ./research/agent-frameworks/agentscope.md
**Generated**: 2026-03-28
**Integration surfaces found**: 2 (SDK | Architecture Pattern)
**Proposals written**: 0
**Skipped**: 4 — architectural mismatch with local orchestration model

---

## Analysis Summary

AgentScope is a production-ready agent framework providing:

1. **Python SDK** (`pip install agentscope`) — Async agents, Toolkit system, ChatModelBase abstraction, memory backends, MsgHub multi-agent orchestration
2. **Architecture Pattern** — ReActAgent, hook middleware, model-agnostic tool composition, voice/realtime streaming

The integration surface is strong, but the **orchestration model is fundamentally different** from Claude Code's architecture:

- **AgentScope** orchestrates LLM agents at the framework level — agent-to-agent communication, distributed memory, production K8s/serverless deployment with OTel observability
- **Claude Code + Development Harness** orchestrates specialist language agents at the **orchestrator level** — human-in-the-loop coordination, synchronous task dispatch, artifact-based handoff

Claude Code agents (ReActAgent, context-gathering, code-reviewer) operate within a single synchronous orchestrator thread, not as a distributed multi-agent system.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/agents/context-gathering.md` | Reads codebase to gather context — domain does not overlap with multi-agent orchestration or distributed agents |
| `.claude/skills/orchestrating-swarms/SKILL.md` | Already uses Claude Code's native TeamCreate for agent orchestration; AgentScope is a separate framework for LLM-level agent systems, not Claude Code agents. Integration would require replacing Claude Code's swarm system entirely, a destructive architectural change outside this assessment scope |
| `plugins/development-harness/` (SAM orchestration) | Coordinates agent specialists synchronously through artifact-based handoff (plan → task file → agent execution → artifact output → next stage). AgentScope's async-first, message-driven, distributed architecture is incompatible without reimplementation of core orchestration. Potential future work: implement AgentScope-Runtime as an alternative backend for long-running milestone tasks, but requires new plugin rather than utilization of existing caller |
| `.claude/agents/research-utilization-assessor.md` (this agent) | Self-referential; this agent assesses utilization but is not itself a caller of external services in this domain |

---

## Why No Proposals

**AgentScope's value** lies in:

1. **Multi-agent systems** at the *LLM framework level* — agents coordinate with each other via MsgHub, exchange messages, maintain distributed memory, call tools independently
2. **Production deployment** — K8s, serverless, distributed Redis memory, OTel observability for production-grade agent systems
3. **Model-agnostic** — works with OpenAI, Anthropic Claude, Alibaba DashScope, Ollama, etc.

**Claude Code's local systems** assume:

1. **Synchronous orchestration** — one orchestrator thread, one active agent at a time
2. **Local execution** — agents spawn in tmux/iterm2/subprocess on local machine
3. **Artifact-based handoff** — output of one agent (file) becomes input to next
4. **Human-in-the-loop** — orchestrator makes decisions based on constraint analysis (ARL), not autonomous agent reasoning

**The gap**: To integrate AgentScope meaningfully, Claude Code would need to:

- Replace TeamCreate/Agent tool with AgentScope's ReActAgent class
- Replace synchronous orchestration with async MsgHub
- Restructure artifact handoff to message-based agent communication
- Add distributed memory (Redis) and production deployment infrastructure

This is not a "utilization" (calling existing service) but a **complete replacement of the multi-agent subsystem** — architectural scope beyond utilization assessment.

---

## Recommendations for Future Investigation

1. **AgentScope-Runtime as optional deployment backend** — Implement as a new plugin that provides K8s/serverless deployment for existing Claude Code development tasks. This would be a *new system* (not utilization of existing), useful when milestone work needs to run in cloud with distributed agents.

2. **Tool integration pattern study** — AgentScope's Toolkit + MCP integration pattern (lines 377-381 of research entry) is worth documenting as a reference for Claude Code skill tool registry design.

3. **ReActAgent pattern reference** — The ReActAgent implementation (built-in tool invocation, streaming, async nature) provides a reference design for Claude Code's agent architecture, but adoption would require major refactoring.

---

## Assessment Closure

**STATUS**: Complete — No utilization proposals.

**Surfaces found** match the research entry's documented capabilities (SDK, architecture patterns), but integration opportunities with existing local systems do not meet the utilization criterion: "would integrating this service replace a weaker local implementation OR add a capability the system lacks?"

- CloudOrchestration and distributed agents are **not current capabilities** of Claude Code (not "weaker implementation")
- AgentScope as a drop-in replacement would require **architectural reimplementation**, not integration
- Local systems' synchronous, artifact-driven orchestration is **intentionally different** from AgentScope's async message-driven design — they solve different problems

No backlog items created — this is a conclusive assessment. If future work requires cloud agent deployment, create a new feature proposal (not a utilization item) to design AgentScope-Runtime integration as an optional plugin.
