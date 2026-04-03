# Utilization Assessment: PocketBase

**Research entry**: ./research/data-infrastructure/pocketbase.md
**Generated**: 2026-03-28
**Assessment**: No viable utilization opportunities identified

---

## Finding Summary

PocketBase documents concrete integration surfaces (REST API, JavaScript/Dart SDKs, CLI binary, realtime subscriptions via SSE, hook-based extensibility), but the Claude Skills codebase has **no systems that would benefit from PocketBase integration**.

### Why No Utilization Surface

1. **Architectural Incompatibility**
   - PocketBase is a self-contained application server (includes database, auth, file storage, API, UI)
   - Current architecture uses pluggable cloud backend providers (GitHub, Linear, GitLab, Supabase)
   - These backends are accessed via API (GraphQL, REST)
   - PocketBase would require either deployment as external service (adds infrastructure complexity) or embedding as library (complicates backend abstraction)
   - Neither pattern aligns with existing architecture

2. **Redundant with GitHub Backend**
   - Development harness treats GitHub as source of truth for coordination state (issues, tasks, sub-items)
   - All task state, dependencies, claims, status transitions flow through GitHub Issues + GraphQL
   - Introducing PocketBase would either duplicate this functionality or require replacing GitHub (architectural redesign)
   - No capability gap exists between current GitHub usage and what PocketBase provides

3. **No Standalone Application Consumers**
   - All local agents, skills, scripts are stateless orchestrators (terminate after task delegation)
   - Persistent state is explicitly managed via GitHub Issues (backend-agnostic design)
   - No local applications need self-hosted infrastructure independent of GitHub
   - Filesystem persistence (plan files, local caching) is deliberate and sufficient for current use

4. **Alignment with Documented Architecture**
   - Development harness CLAUDE.md explicitly states: "Backend Providers — Support pluggable backends via Protocol-based abstractions. Current: GitHub. Future: GitLab, Linear, Supabase."
   - PocketBase is not mentioned in future roadmap because it is categorically different (application server, not API provider)
   - Extending backend providers requires API-oriented design, not embedded database + server pattern

---

## Candidate Systems Evaluated

| System | Role | Backend | Finding |
|---|---|---|---|
| Development Harness (backlog MCP) | Coordination state, task scheduling | GitHub Issues + GraphQL | GitHub is intentional choice; no gap |
| Sam Task Planner | Task decomposition orchestrator | Stateless, outputs to files | No persistence needed beyond GitHub |
| Dispatch Orchestration | Wave-based parallel execution | SQLite state DB at `~/.dh/dispatch-state.db` | Already has embedded persistence; PocketBase would replace rather than supplement |
| Agents (various) | Reasoning + delegation | Stateless (inherit orchestrator context) | No local persistence requirement |
| Skills (various) | Workflows + MCP orchestration | Stateless; delegate to agents | No persistence needed |

**Note on Dispatch Orchestration**: The only system that uses embedded persistence (SQLite) is the dispatch state manager at `~/.dh/projects/{project-slug}/dispatch-state.db`. This is intentionally lightweight and local. Replacing it with PocketBase would add infrastructure complexity without functional benefit — it serves dispatch state during execution, not durable cross-session state.

---

## Why PocketBase Was Considered

The research entry describes several attributes that could theoretically align with Claude Skills:

- **Rapid backend prototyping** — Stand up a backend without infrastructure setup
- **Realtime subscriptions** — SSE for task status updates
- **Hook system** — Align with plugin architecture
- **Multi-SDK support** — JavaScript, Dart, Go

However, none of these attributes address actual gaps in the current system:

- Prototyping is not a use case (system is production orchestrator, not prototype sandbox)
- Realtime subscriptions would require decoupling coordination state from GitHub (architectural change)
- Hook system is for PocketBase extensibility, not Claude Code plugins (different scopes)
- Multi-SDK support is available but not needed (no new consumer services being built)

---

## Conclusion

**Status**: `no_utilization_surface`

PocketBase has a well-documented, concrete integration surface. However, it is architecturally orthogonal to the Claude Skills repository's design patterns. The system is explicitly built around GitHub as a pluggable backend provider accessed via API, not around self-contained application servers. No local system needs the capability PocketBase provides, and introducing it would require either:

1. Running as external service (adds infrastructure, duplicates GitHub functionality)
2. Embedding as library (breaks backend abstraction pattern)

Neither path is justified by current capability gaps.

**Recommendation**: Archive this research as reference material for future discussions about self-hosted infrastructure patterns, but do not pursue implementation at this time.

---

## Research Citation

- Research entry: `./research/data-infrastructure/pocketbase.md` (created 2026-03-28, accessed 2026-03-28)
- Development harness architecture: `./plugins/development-harness/CLAUDE.md`, `./plugins/development-harness/docs/backend-providers.md`
- Dispatch state manager: `./plugins/development-harness/backlog_core/dispatch_state.py`
