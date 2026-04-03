# Improvement Proposals: Fleet

**Research entry**: ./research/agent-infrastructure/fleet.md
**Generated**: 2026-03-28
**Patterns assessed**: 6
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 4

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Plugin Architecture via Service Overrides | Already covered: the development harness uses Voltron-style composition with language manifests and Protocol-based abstractions for role resolution. See `plugins/development-harness/CLAUDE.md` (Composition Model section) and `plugins/development-harness/docs/backend-providers.md`. |
| Modular Component Design | Already covered: the repo separates heterogeneous subsystems into independent plugins (python3-development, fastmcp-creator, plugin-creator, development-harness) with auto-discovery. Each plugin owns its agents, skills, and scripts independently. |
| Datastore Abstraction | Already covered and actively being developed: `plugins/development-harness/docs/backend-providers.md` documents Protocol-based abstractions for GitHub (current), Linear, GitLab, and Supabase backends with three-primitive storage model (Work Item, Sub-item, Document). |
| Configuration Management | Too abstract to be actionable: Fleet's centralized YAML+env-var config manager serves a long-running Go server with database connections, TLS, and object storage. The local system is a CLI plugin ecosystem where configuration is per-plugin `plugin.json` plus `CLAUDE.md` rules. The problem domains are incompatible -- a centralized config manager would not serve the same purpose in a stateless agent tool. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Event-Driven Integration (webhooks to external systems) | Low | Fleet's webhook system streams events (policy violations, vulnerability detections) to external systems like Splunk and Slack. The local system has hook-based lifecycle events (`PostToolUse`, `SubagentStop`) that update local task state via `task_status_hook.py`, but no mechanism emits events to external integrations when task status changes. However, the gap is inferred rather than directly observed as a deficiency -- it is unclear whether external event emission is a need in this repo's architecture. The hook system is designed for local agent coordination, not system integration. Would need evidence of users requesting external notifications or integration failures to raise confidence. |
| Observability (OTEL instrumentation) | Low | Fleet uses OpenTelemetry for logs, traces, and metrics in its Go server (`otelsql` wrapper, OTEL configuration). The local system has zero OTEL instrumentation in plugin code -- Grep for `OTEL`, `OpenTelemetry`, `tracing` in `plugins/development-harness/` returned only test fixtures and documentation about user projects, not actual instrumentation of the harness itself. However, the local system is a CLI tool ecosystem, not a long-running server. OTEL tracing is designed for request-scoped server workloads. The local system's observability model is file-based (task status in YAML, `LastActivity` timestamps, active-task context JSON). It is unclear whether OTEL would provide value over the existing file-based observability in a CLI-agent context. Would need evidence of debugging difficulties or lost-state incidents that file-based tracking fails to address. |

