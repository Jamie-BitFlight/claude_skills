---
title: "OpenAI Symphony"
research_date: "2026-03-06"
source_url: "https://github.com/openai/symphony"
github_url: "https://github.com/openai/symphony"
version_at_research: "Draft v1 (language-agnostic spec); no tagged releases"
license: "Apache License 2.0"
last_verified: "2026-03-06"
version_at_verification: "Draft v1 spec; no tagged releases"
next_review: "2026-06-06"
---

## Overview

Symphony is a long-running automation service that continuously reads work from an issue tracker, creates an isolated workspace for each issue, and runs a coding agent session for that issue inside the workspace. It turns project work into isolated, autonomous implementation runs, allowing teams to manage work instead of supervising coding agents. The repository ships a language-agnostic specification (`SPEC.md`) and an experimental Elixir/OTP reference implementation.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Engineers must supervise coding agents task-by-task instead of delegating at the work level | Symphony polls an issue tracker and dispatches agents autonomously per issue, requiring human input only at review/merge gates |
| Agent execution is not isolated — commands can affect the wrong filesystem paths | Per-issue workspace directories are enforced with three safety invariants: agent runs only inside `workspace_path`; `workspace_path` must have `workspace_root` as a directory prefix; workspace key characters are restricted to `[A-Za-z0-9._-]` |
| Workflow behavior is baked into service code, not version-controlled with the repo | `WORKFLOW.md` in the repository defines the prompt template and all runtime settings; Symphony hot-reloads it on change without restart |
| Multiple concurrent agents produce no unified observability | Structured logs, optional Phoenix LiveView dashboard, and a JSON API (`/api/v1/state`, `/api/v1/<issue_identifier>`, `/api/v1/refresh`) expose orchestrator state |
| Agent sessions that stall block progress indefinitely | Stall detection fires after `codex.stall_timeout_ms` (default `300000` ms / 5 minutes) of no Codex events; the worker is terminated and an exponential-backoff retry is scheduled |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 5,530 | 2026-03-06 |
| Forks | 341 | 2026-03-06 |
| Watchers (subscribers) | 41 | 2026-03-06 |
| Contributors | Not returned in paginated header (API returned inline JSON only) | 2026-03-06 |
| Latest Release | No tagged releases (404 from releases/latest API) | 2026-03-06 |
| Repository Created | 2026-02-26 | 2026-03-06 |
| Last Push | 2026-03-05 | 2026-03-06 |
| Primary Language | Elixir (530,358 bytes); Python (19,585 bytes) | 2026-03-06 |

---

## Key Features

### Issue Tracker Integration (Linear)

- Polls Linear for candidate issues on a configurable cadence (`polling.interval_ms`, default `30000` ms).
- Fetches issues in configurable `active_states` (default: `Todo`, `In Progress`) and excludes `terminal_states` (default: `Closed`, `Cancelled`, `Canceled`, `Duplicate`, `Done`).
- Normalizes tracker payloads into a stable issue model with fields: `id`, `identifier`, `title`, `description`, `priority`, `state`, `branch_name`, `url`, `labels`, `blocked_by`, `created_at`, `updated_at`.
- Blocker-aware dispatch: issues in `Todo` state are not dispatched when any blocker issue is non-terminal.
- Dispatch priority sorts by `priority` ascending (1..4 preferred; null sorts last), then `created_at` oldest first, then `identifier` lexicographically.

### Concurrency Control

- Global concurrency cap: `agent.max_concurrent_agents` (default `10`).
- Per-state concurrency cap: `agent.max_concurrent_agents_by_state` (map of state name to positive integer, default empty).
- Available slots computed as `max(max_concurrent_agents - running_count, 0)`.
- Both limits can be changed in `WORKFLOW.md` and take effect at runtime without restart.

### Per-Issue Workspace Isolation

- Each issue gets a deterministic workspace path: `<workspace.root>/<sanitized_issue_identifier>`.
- Workspace key sanitization: any character outside `[A-Za-z0-9._-]` is replaced with `_`.
- Workspaces persist across runs for the same issue; successful runs do not auto-delete them.
- Lifecycle hooks: `after_create` (fatal on failure), `before_run` (fatal on failure), `after_run` (logged, ignored), `before_remove` (logged, ignored). Default hook timeout: `60000` ms.

### WORKFLOW.md Contract (Repository-Owned Policy)

- Single Markdown file with YAML front matter (config) and a Markdown body (Liquid-compatible prompt template).
- Config keys: `tracker`, `polling`, `workspace`, `hooks`, `agent`, `codex` (plus optional extensions like `server`).
- Prompt template variables: `issue` (all normalized fields) and `attempt` (null on first run, integer on retry).
- Unknown template variables and filters cause render failure (strict mode — no silent fallback).
- Symphony watches the file and hot-reloads it on change; invalid reloads keep the last known good config and emit an operator error.

### Retry and Backoff

- Normal continuation retry (issue still active after clean worker exit): fixed delay of `1000` ms.
- Failure-driven retry: `delay = min(10000 * 2^(attempt - 1), agent.max_retry_backoff_ms)` where `max_retry_backoff_ms` defaults to `300000` (5 minutes).
- On retry, Symphony re-fetches active candidates; if the issue is no longer active, the claim is released.

### Coding Agent Protocol (Codex App-Server)

- Launches `codex.command` (default `codex app-server`) via `bash -lc <command>` in the workspace directory.
- Communicates over stdio using a line-delimited JSON-RPC-like protocol.
- Startup handshake: `initialize` request → `initialized` notification → `thread/start` request → `turn/start` request.
- Session identifiers: `thread_id` from `thread/start` result; `turn_id` from each `turn/start` result; `session_id = "<thread_id>-<turn_id>"`.
- Multi-turn support: after a successful turn, if the issue remains active, the worker issues another `turn/start` on the same live thread (up to `agent.max_turns`, default `20`). Continuation turns receive only continuation guidance, not the full original prompt.
- Turn timeout: `codex.turn_timeout_ms` (default `3600000` ms / 1 hour).
- Token usage and rate-limit snapshots are tracked per session in `LiveSession` state.

### Observability

- Structured runtime logs are the minimum required observability surface.
- Optional Phoenix LiveView dashboard at `/` and JSON API at `/api/v1/state`, `/api/v1/<issue_identifier>`, `/api/v1/refresh` (enabled via `server.port` in `WORKFLOW.md` or `--port` CLI flag).
- Orchestrator runtime state tracks: `running` map, `claimed` set, `retry_attempts` map, `completed` set, `codex_totals` (aggregate tokens and runtime seconds), `codex_rate_limits`.

---

## Technical Architecture

### Abstraction Layers (from SPEC.md Section 3.2)

Symphony is designed for portability across languages. The SPEC.md defines six layers:

1. **Policy Layer** (repo-defined): `WORKFLOW.md` prompt body and team-specific ticket-handling rules.
2. **Configuration Layer** (typed getters): Parses YAML front matter into typed runtime settings; handles defaults, environment token indirection (`$VAR_NAME`), and path normalization.
3. **Coordination Layer** (orchestrator): Polling loop, issue eligibility, concurrency, retries, reconciliation. This is the single authoritative authority for in-memory state — all worker outcomes are routed through it.
4. **Execution Layer** (workspace + agent subprocess): Filesystem lifecycle, workspace preparation, and the Codex app-server stdio protocol.
5. **Integration Layer** (Linear adapter): API calls and normalization for tracker data.
6. **Observability Layer** (logs + optional status surface): Operator visibility into orchestrator and agent behavior.

### Orchestrator State Machine

Symphony defines five orchestration states per issue (distinct from tracker states like `Todo`):

- `Unclaimed`: Issue is not running and has no retry scheduled.
- `Claimed`: Reserved to prevent duplicate dispatch (encompasses `Running` and `RetryQueued`).
- `Running`: Worker task exists and is tracked in the `running` map.
- `RetryQueued`: Retry timer exists in `retry_attempts`, no active worker.
- `Released`: Claim removed because issue is terminal, non-active, missing, or retry exhausted.

A single poll tick executes: (1) reconcile running issues, (2) dispatch preflight validation, (3) fetch candidates, (4) sort by priority, (5) dispatch while slots remain, (6) notify observability consumers.

### Restart Recovery

No persistent database is required. Recovery is tracker-driven and filesystem-driven: on startup, Symphony queries the tracker for terminal-state issues and removes their workspace directories, then begins the poll loop fresh.

### Elixir Reference Implementation

The `elixir/` directory contains the reference implementation built on Erlang/BEAM/OTP, chosen because "Erlang/BEAM/OTP is great for supervising long-running processes" and "supports hot code reloading without stopping actively running subagents." The implementation uses Phoenix LiveView for the dashboard, Bandit as the HTTP server, and `mise` for Elixir/Erlang version management.

---

## Installation & Usage

The README offers two paths: build your own implementation from `SPEC.md`, or use the Elixir reference implementation.

### Option 1: Build from spec

Provide `SPEC.md` to any coding agent:

```text
Implement Symphony according to the following spec:
https://github.com/openai/symphony/blob/main/SPEC.md
```

### Option 2: Elixir reference implementation

Prerequisites: `mise` for Elixir/Erlang version management.

```bash
git clone https://github.com/openai/symphony
cd symphony/elixir
mise trust
mise install
mise exec -- mix setup
mise exec -- mix build
mise exec -- ./bin/symphony ./WORKFLOW.md
```

Optional flags:

- `--logs-root <path>` — write logs under a different directory (default: `./log`)
- `--port <integer>` — start the Phoenix observability service (default: disabled)

### Minimal WORKFLOW.md

```yaml
---
tracker:
  kind: linear
  project_slug: "..."
workspace:
  root: ~/code/workspaces
hooks:
  after_create: |
    git clone git@github.com:your-org/your-repo.git .
agent:
  max_concurrent_agents: 10
  max_turns: 20
codex:
  command: codex app-server
---

You are working on a Linear issue {{ issue.identifier }}.

Title: {{ issue.title }} Body: {{ issue.description }}
```

### Required environment variable

```bash
export LINEAR_API_KEY="<your-linear-personal-api-key>"
```

Obtain via Linear: Settings → Security & access → Personal API keys.

### Default safety posture (Elixir implementation)

When `codex.approval_policy` is omitted, the Elixir implementation defaults to:

```yaml
codex:
  approval_policy:
    reject:
      sandbox_approval: true
      rules: true
      mcp_elicitations: true
  thread_sandbox: workspace-write
```

---

## Limitations and Caveats

- **Engineering preview only**: "Symphony is a low-key engineering preview for testing in trusted environments." The Elixir implementation is additionally labeled "prototype software intended for evaluation only."
- **Linear-only tracker**: The current specification version supports only `tracker.kind: linear`. Support for other trackers is not documented.
- **No tagged releases**: The repository has no tagged releases as of 2026-03-06. There is no versioned artifact to pin.
- **Requires harness engineering**: "Symphony works best in codebases that have adopted harness engineering." Repositories without agent-oriented structure (`WORKFLOW.md`, Codex skills, structured issue states) will require significant setup.
- **Custom Linear states required**: The reference `WORKFLOW.md` depends on non-standard Linear issue statuses: `Rework`, `Human Review`, and `Merging`. These must be created in Linear Team Settings → Workflow.
- **No built-in sandbox**: The spec does not mandate sandbox controls. "Mandating strong sandbox controls beyond what the coding agent and host OS provide" is explicitly listed as a non-goal. High-trust configurations (e.g., `approval_policy: never`) run with no human approval gates.
- **No multi-tenant control plane**: Explicitly listed as a non-goal in the spec. Symphony is a single-team daemon, not a hosted platform.
- **Restart does not resume in-flight sessions**: Implementations are not required to restart in-flight agent sessions automatically when config changes. Restart recovery is tracker-driven, not session-state-driven.
- **No persistent DB, so aggregate stats reset on restart**: `codex_totals` (aggregate token counters and runtime seconds) are in-memory only.

---

## Relevance to Claude Code Development

### Applications

- **Autonomous issue execution**: Symphony's architecture directly maps to Claude Code workflows where a coding agent (Claude Code / Codex) should execute Linear issues end-to-end without human supervision.
- **`WORKFLOW.md` as versioned agent policy**: The pattern of storing the agent prompt, concurrency limits, and tracker config in a repository-owned Markdown file is directly adoptable for Claude Code skills that configure agent behavior per-project.
- **Workspace isolation model**: The per-issue workspace isolation invariants (agent runs only inside `workspace_path`, path must be inside `workspace_root`, sanitized key) are directly applicable to any multi-agent Claude Code setup that needs to prevent agents from clobbering each other's state.

### Patterns Worth Adopting

- **Dispatcher-as-single-authority pattern**: The orchestrator is the only component that mutates scheduling state. All worker outcomes are reported back and converted into explicit state transitions. This prevents duplicate dispatch and makes state auditable — a pattern applicable to any Claude Code orchestration layer.
- **Continuation turn protocol**: After a successful Codex turn, Symphony re-checks the issue state and starts another turn on the same thread (reusing thread context) rather than spawning a new agent session. This minimizes context re-loading and is applicable to long-running Claude Code tasks.
- **Backoff formula**: `min(10000 * 2^(attempt - 1), max_retry_backoff_ms)` with a 5-minute cap is a well-specified exponential backoff usable in any retry-capable Claude Code workflow.
- **Stall detection with configurable timeout**: Tracking `last_codex_timestamp` and terminating workers that exceed `stall_timeout_ms` prevents unbounded hangs — directly applicable to monitoring Claude Code subagent sessions.

### Integration Opportunities

- **Replace Codex with Claude Code**: The Codex app-server protocol (JSON-RPC-like over stdio) could be adapted for a Claude Code app-server mode. Symphony's `codex.command` field is a shell command string, so swapping `codex app-server` for a Claude Code equivalent requires only a config change.
- **Adopt `WORKFLOW.md` convention**: The pattern of a repo-level `WORKFLOW.md` with YAML front matter for agent config and a Liquid-template prompt body could be directly added to the `claude_skills` repository, allowing Symphony (or a Symphony-compatible runner) to manage Claude Code tasks from a Linear board.
- **Build a Python/TypeScript implementation from SPEC.md**: The spec is explicitly language-agnostic. A Python implementation using Claude Code instead of Codex could be generated from `SPEC.md` and integrated into the `claude_skills` agent-infrastructure toolset.

---

## References

- [openai/symphony GitHub repository](https://github.com/openai/symphony) (accessed 2026-03-06)
- [SPEC.md — Symphony Service Specification, Draft v1](https://github.com/openai/symphony/blob/main/SPEC.md) (accessed 2026-03-06)
- [elixir/README.md — Elixir reference implementation](https://github.com/openai/symphony/blob/main/elixir/README.md) (accessed 2026-03-06)
- [README.md — Top-level README](https://github.com/openai/symphony/blob/main/README.md) (accessed 2026-03-06)
- GitHub API: `repos/openai/symphony` (accessed 2026-03-06) — stars, forks, license, language breakdown
- GitHub API: `repos/openai/symphony/releases/latest` — HTTP 404, no tagged releases (accessed 2026-03-06)

---
