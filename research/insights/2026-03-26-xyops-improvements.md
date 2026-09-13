---
title: "Improvement Proposals: xyOps"
---

<!-- removed-skill-citations -->
> **Removed-skill citations:** `swarm-operations` were removed in PR #3422 (commit `4e1e73bd6`, 2026-09-06) and **retired in favour of** `plugins/agent-orchestration/skills/parallel-work/`, with what delegation guidance survives in `plugins/agent-orchestration/skills/delegate/`. "Retired in favour of" is that PR's own wording, at `plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md` — not a capability-preserving consolidation: `parallel-work/SKILL.md` § "Persistent teams" argues against the long-lived-team model outright, and the `TeamCreate` call that model relied on no longer exists in Claude Code as of v2.1.178 (`plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md`). The removal replaced roughly 2080 lines with roughly 330; the line numbers, pattern numbers, and named sections cited below have no surviving equivalent, and grep over `plugins/` and `.claude/` returns zero hits for them (`Handling Crashed Teammates`, `permission_request`, and the rest). Any "already covered" conclusion resting on them is therefore **refuted by the current tree, not merely unverified against it**.

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Workflow Orchestration Systems | Already covered. Local SAM pipeline (implement-feature SKILL.md) provides 7-stage orchestration with event-driven hooks (SubagentStop, PostToolUse in task_status_hook.py) and multi-step job execution. Visual workflow editor is a UI concern not applicable to CLI-based skill framework. |
| Distributed Agent Patterns (xysat satellites) | Incompatible architecture. xyOps satellite agents coordinate remote server execution over network protocols. Local system uses in-process Claude Code agents via TeamCreate/SendMessage (swarm-operations SKILL.md) which operate within a single host. The distributed infrastructure coordination pattern does not map to the local agent model. **[Refuted — the skill(s) cited here were retired in PR #3422 (`4e1e73bd6`) and are absent from the current tree; see the removed-skill note at the top of this file.]** |
| Real-Time Monitoring Integration | Too abstract / domain mismatch. xyOps consolidates server monitoring (CPU, processes, network) with job execution for operations teams. This is an infrastructure monitoring concern with no concrete mechanism transferable to an AI skill orchestration framework. The local system already tracks task activity timestamps via task_status_hook.py PostToolUse handler. |
| Enterprise Operations Patterns (multi-tenancy, RBAC, fleet management) | Domain mismatch. These are multi-tenant SaaS platform concerns (role-based access control, fleet management, audit logging) with no mapping to a single-user CLI plugin system. |
| Custom Framework Development | Too abstract. The research entry describes building on a non-Express stack as a design philosophy. No concrete mechanism is named that could produce an observable gap in a local file. |
| Security and Operations (SSO, secret management, air-gapped deployment) | Domain mismatch. SSO integration, air-gapped deployment support, and enterprise secret management are server platform features. The local system operates within Claude Code's existing security model. No transferable mechanism identified. |
