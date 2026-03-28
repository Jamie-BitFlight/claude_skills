# Utilization Proposals: OpenBao

**Research entry**: ./research/llm-infrastructure/openbao.md
**Generated**: 2026-03-28
**Integration surfaces found**: 3 (HTTP API | Go SDK | Docker test cluster API | CLI)
**Proposals written**: 0
**Skipped**: 12 — no suitable callers identified

---

## Integration Surfaces Identified

OpenBao exposes callable integration surfaces at three layers:

| Surface Type | Mechanism | Reference |
|---|---|---|
| **HTTP API** | REST endpoints at `http://localhost:8200/v1/...` | Research entry lines 189–203 |
| **Go SDK** | Importable packages `github.com/openbao/openbao/api/v2` and `github.com/openbao/openbao/sdk/v2` | Research entry lines 39–40, 134–136 |
| **Docker Test API** | Test cluster helpers in `github.com/openbao/openbao/sdk/v2/helper/testcluster/docker` | Research entry lines 172–187 |
| **CLI** | Binary `bin/bao` compiled from source | Research entry lines 140–147 |

---

## Skipped Systems

| Local System | Reason Skipped |
|---|---|
| `.claude/agents/c-systems-programmer.md` | Specialist developer agent for C code review and systems programming. OpenBao integration would require infrastructure orchestration layer (agent spawning, credential injection) not present in developer agents. |
| `.claude/agents/javascript-pro.md` | Modern JavaScript specialist for application code review and development. Does not manage external services or credential infrastructure. |
| `.claude/agents/code-review.md` | Code quality reviewer. Does not execute or integrate external services; only reviews code artifacts. |
| `.claude/agents/research-context-agent.md` | Research cross-referencer. Analyzes research files for opportunities; does not execute or integrate external services. |
| `.claude/agents/context-gathering.md` | Reads codebase and builds context manifests. Does not manage secrets or external services. |
| `.claude/agents/context-refinement.md` | Updates agent prompts with discovered context. Does not integrate external services. |
| `.claude/agents/backlog-mcp-validator.md` | Validates MCP server implementations. Does not integrate application-layer services. |
| `.claude/agents/logging.md` | Task log consolidator. Does not manage infrastructure or external services. |
| `.claude/agents/fact-checker.md` | Verifies claims in research. Does not integrate external services. |
| `.claude/agents/doc-drift-auditor.md` | Audits documentation vs. code. Does not manage external services. |
| `.claude/agents/plugin-docs-writer.md` | Generates plugin documentation. Does not integrate external services. |
| `.claude/agents/research-insight-extractor.md` | Creates backlog items from research. Does not integrate external services. |

---

## Analysis

The Claude Code repository contains specialized agents for:
- **Code review and development** (C systems, JavaScript, code review)
- **Research processing** (research context cross-reference, insight extraction)
- **Workflow management** (logging, backlog validation, context gathering)
- **Documentation** (plugin docs, drift auditing)

None of these agent types is an **infrastructure-layer orchestrator** that would:
1. Execute external services on behalf of other agents
2. Manage shared credential repositories
3. Provide credential injection or rotation to running agents
4. Handle secret lease lifecycle management

OpenBao's designed use cases (per research entry lines 209–217) include:
- AI agent secret management (agents requesting temporary credentials)
- Multi-agent secret sharing
- Audit trails for agent access
- Custom auth methods for agent identity validation

These use cases require an **agent orchestration or infrastructure supervisor** that does not exist in the current agent roster. Such an agent would:
- Spawn other agents with injected OpenBao credentials
- Manage credential renewal and revocation
- Audit which agents accessed which secrets
- Coordinate authentication across agent instances

**No such orchestration agent exists** in this repository. The current agents are either:
- Specialists solving narrow problems (code review, docs)
- Self-contained workflow processors (research, logging)
- Not infrastructure-facing (no external service management layer)

---

## Next Steps (For Future Work)

If OpenBao integration becomes relevant:

1. **Create an agent orchestration layer** — a coordinator agent that spawns and manages other agents, handles credential injection, and tracks secret access
2. **Create an OpenBao credential provider skill** — a reusable skill for requesting temporary credentials from OpenBao and injecting them into child agent environments
3. **Integrate with agent spawning hooks** — hook into the agent invocation mechanism to automatically request and inject OpenBao credentials before agent execution

Until such infrastructure exists, OpenBao remains a valuable tool for production agent deployment but cannot be integrated into the current local system roster.

---

## Notes

- This assessment is based on the **actual local systems present** as of 2026-03-28. No proposed agents were hallucinated.
- The integration surface is real and well-documented in the research entry. The gap is in **local orchestration infrastructure**, not in OpenBao's API completeness.
- When infrastructure agents are added to the repository in the future, OpenBao should be revisited as a candidate integration for those new systems.
