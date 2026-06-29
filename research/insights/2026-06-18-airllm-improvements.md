# Improvement Proposals: AirLLM

**Research entry**: ./research/llm-infrastructure/airllm.md
**Generated**: 2026-06-18
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 0
**Skipped (already covered or tracked)**: 5

---

## Summary

The research entry has a populated "Relevance to Claude Code Development" section
(four Use Cases plus one Integration Pattern). Every item describes **deploying AirLLM
as an external local-inference dependency** for self-hosted open-weight models. None
describes a transferable mechanism that this repo's skills, agents, or workflow scripts
lack and could adopt.

AirLLM is GPU-memory-optimization infrastructure for running 70B–405B open models on
consumer hardware via layer-sharded streaming. This repo builds Claude Code
skills/agents/plugins that orchestrate the hosted Claude model. The two concerns do not
share an architecture: there is no skill structure, agent-orchestration mechanism, task-state
model, or workflow primitive in AirLLM to map onto a local system. Per the gap rules, a gap
is not actionable when "the external tool's approach is incompatible with this repo's
architecture" — which is the case for all five patterns.

The entry's own confidence table rates the Relevance section **medium** and flags the
Integration Pattern as "hypothetical (not documented in source)" (airllm.md line 340),
confirming there is no observable mechanism to extract.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Use Case 1 — Running agents on consumer hardware via local LLM | External-deployment use case, not a transferable mechanism. No local system in this repo performs or could adopt GPU layer-streaming. Incompatible with repo architecture (Claude Code plugins orchestrate the hosted model). |
| Use Case 2 — Offline agentic RAG with local LLM + vector search | External-deployment use case. No observable before/after state in any local skill, agent, or script. Incompatible with repo architecture. |
| Use Case 3 — Hardware-minimal CI/CD deployments | External-deployment use case for self-hosted inference. No mapping to any local workflow script; not an extension of an existing system. |
| Use Case 4 — Cost optimization for high-volume agent workflows | Cost/deployment strategy for self-hosted models, not a mechanism the repo's systems lack. No observable target state in a file or command. |
| Integration Pattern — MCP server wrapping AirLLM completion | Proposes a NEW application product, not an improvement to the existing fastmcp-creator skill (which already teaches building any MCP server). Entry flags this as hypothetical (line 340). Fails gap rules #3 (no observable file/command state) and #4 (adds unrelated product rather than extending a local system). |

---

**Conclusion**: No actionable patterns. The Relevance section describes external-dependency
use cases incompatible with this repo's skill/agent/workflow architecture. No improvement
proposals generated and no backlog items created.
