---
name: Pilot
description: Pilot is an autonomous development pipeline that ingests tickets from GitHub, Linear, Jira, or Asana and produces pull requests without human involvement in the implementation phase. Written in Go,...
license: Business Source License 1.1 (BSL 1.1) — converts to Apache 2.0 after 4 years
metadata:
  topic: pilot
  category: coding-agents
  source_url: https://pilot.quantflow.studio/
  github: alekspetrov/pilot
  version: "v1.46.7"
  verified: "2026-02-19"
  next_review: "2026-05-19"
---

## Overview

Pilot is an autonomous development pipeline that ingests tickets from GitHub, Linear, Jira, or Asana and produces pull requests without human involvement in the implementation phase. Written in Go, it wraps Claude Code CLI as its AI execution backend to perform codebase analysis, code writing, test execution, and PR creation. The operator reviews and merges; Pilot handles the end-to-end engineering work in between.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Backlog tickets stall because developers must context-switch into each one | Pilot claims labeled issues automatically, executes them sequentially or in parallel, and opens a PR |
| Coordinating AI coding tasks across multiple issue trackers and communication channels | Single daemon with adapter layer supporting GitHub, GitLab, Azure DevOps, Linear, Jira, Asana, Telegram, and Slack |
| No visibility into autonomous agent cost and progress | Real-time TUI dashboard with token/cost metrics, SQLite-persisted across restarts, per-task breakdowns |
| Autonomous agents lacking codebase context cause regressions | Navigator integration auto-detects `.agent/` project knowledge files; cross-project memory shares patterns across repos |
| Hard to trust AI PRs — no quality validation before review | Built-in quality gates run tests, lint, and build validation with auto-retry before any PR is pushed |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 110 | 2026-02-19 |
| Forks | 8 | 2026-02-19 |
| Contributors | 2 | 2026-02-19 |
| Latest Release | v1.46.7 | 2026-02-19 |
| Open Issues | 6 | 2026-02-19 |
| Repository Created | 2026-01-26 | 2026-02-19 |
| Primary Language | Go (~95% of codebase) | 2026-02-19 |

---

## Key Features

### Core Execution Engine

- Sequential execution mode: waits for PR merge before picking up the next issue, preventing branch conflicts
- Parallel execution mode: runs multiple issues concurrently across independent subsystems
- Autopilot modes: `dev` (skip CI, auto-merge), `stage` (wait for CI then auto-merge), `prod` (wait for CI and human approval)
- Epic decomposition: complex tasks auto-split into ordered subtasks via Claude Haiku API before execution begins
- Self-review: automated code review pass before pushing PR catches issues without human intervention
- Execution replay: records sessions for playback, analysis, and export to HTML/JSON/MD

### Intelligence and Model Routing

- Model routing: routes trivial tasks to Claude Haiku and standard/complex tasks to Claude Opus 4.6, auto-detected by task analysis
- Effort routing: maps task complexity to Claude thinking depth (extended thinking for complex tasks)
- Research subagents: Haiku-powered parallel subagents explore the codebase and synthesize context before implementation
- Navigator integration: auto-detects `.agent/` directory and skips for trivial tasks to avoid overhead
- Cross-project memory: shared pattern and context store across multiple repositories via knowledge graph

### Integration Adapters

- GitHub polling: monitors issues labeled `pilot`, claims with `pilot/in-progress`, completes with `pilot/done`
- GitLab and Azure DevOps: full polling plus webhook adapters
- Linear, Jira, Asana: webhook and task sync
- Telegram bot: conversational interface supporting chat, research, planning, and task creation with voice and image input
- Daily briefs: scheduled reports delivered via Slack, email, or Telegram on configurable cron schedule
- Alerting: task failure notifications, cost threshold warnings, stuck task detection

### Infrastructure and Operations

- Dashboard TUI: sparkline metric cards, queue depth, autopilot status, real-time task progress
- Persistent metrics: token/cost/task counts stored in SQLite, survives process restarts
- Hot upgrade: `pilot upgrade` command and `u` key in dashboard; `rollback` subcommand for reverting
- Cost controls: configurable budget limits with hard enforcement stopping task execution when exceeded
- Multi-backend executor: supports Claude Code CLI and OpenCode as pluggable execution backends
- BYOK: bring your own Anthropic API key, AWS Bedrock, or Google Vertex AI

---

## Technical Architecture

Pilot is a Go binary structured as a layered daemon:

<eg>
┌─────────────────────────────────────────────────────────────┐
│                          PILOT                              │
├──────────────┬──────────────────────────────────────────────┤
│ Gateway      │ HTTP/WebSocket server, routing               │
│ Adapters     │ Telegram, Slack, GitHub, Jira, Linear, Asana │
│ Executor     │ Claude Code process management               │
│ Orchestrator │ Task planning, phase management              │
│ Memory       │ SQLite + cross-project knowledge graph       │
│ Briefs       │ Scheduled reports, multi-channel delivery    │
│ Alerts       │ Failure detection, cost monitoring           │
│ Metrics      │ Token usage, execution analytics             │
└──────────────┴──────────────────────────────────────────────┘
</eg>

The execution flow when a GitHub issue is labeled `pilot`:

1. Adapter layer detects the label via polling (default 30s interval)
2. Orchestrator claims the issue (adds `pilot/in-progress` label), creates branch `pilot/GH-{number}`
3. Research subagents (Claude Haiku) perform parallel codebase exploration
4. Navigator context (`.agent/` directory) loaded if present
5. Executor spawns a Claude Code CLI process; Opus 4.6 or Haiku selected by routing logic
6. Quality gates run: tests, lint, build validation with auto-retry on failure
7. Self-review pass evaluates the diff before PR creation
8. PR opened, linked to originating issue; `pilot/done` label applied
9. Autopilot mode determines whether to wait for CI, then optionally auto-merge

The process manager runs as a background daemon with an optional HTTP/WebSocket gateway for external adapter communication and a TUI dashboard for local monitoring.

---

## Installation & Usage

```bash
# Homebrew (recommended)
brew tap alekspetrov/pilot
brew install pilot

# Go install
go install github.com/alekspetrov/pilot/cmd/pilot@latest

# From source
git clone https://github.com/alekspetrov/pilot
cd pilot
make build
sudo make install-global
```

```bash
# Initialize configuration at ~/.pilot/config.yaml
pilot init

# Start polling GitHub issues labeled "pilot"
pilot start --github

# Start with Telegram bot and real-time dashboard
pilot start --telegram --github --dashboard

# Run a one-off task directly
pilot task "Add rate limiting to /api/users" -p ~/Projects/myapp

# Balanced autopilot: wait for CI then auto-merge
pilot start --autopilot=stage --github
```

```yaml
# ~/.pilot/config.yaml
adapters:
  github:
    enabled: true
    token: "${GITHUB_TOKEN}"
    repo: "owner/repo"
    pilot_label: "pilot"
    polling:
      interval: 30s

orchestrator:
  execution:
    mode: sequential
    wait_for_merge: true

executor:
  backend: claude-code   # or "opencode"
```

---

## Relevance to Claude Code Development

### Applications

- Pilot is a direct operational wrapper around Claude Code CLI, making it a primary reference for how to orchestrate Claude Code in a production autonomous development pipeline
- The model routing pattern (Haiku for trivial/research, Opus 4.6 for complex implementation) is directly applicable to agent orchestration decisions in Claude Code skills
- Cost control and budget enforcement mechanisms are relevant to any Claude Code deployment where API spend must be bounded

### Patterns Worth Adopting

- Issue claim-and-label pattern: atomic ownership signals (`in-progress`, `done`) prevent concurrent agent conflicts on the same work item
- Tiered autopilot modes (dev/stage/prod) provide a reusable trust escalation framework for autonomous agents operating at different risk tolerances
- Epic decomposition via a lighter model (Haiku) before handing off to a heavier model (Opus 4.6) reduces cost while preserving execution quality
- Quality gate as a blocking pre-PR step, not an advisory check, ensures agents do not open low-quality PRs that waste human reviewer time
- SQLite-backed persistent metrics survive process restarts — relevant for any long-running agent daemon

### Integration Opportunities

- Pilot can be added as the execution layer beneath Claude Code skill-based workflows, handling scheduling, parallelism, and PR lifecycle while skills supply specialized context
- The Navigator integration pattern (`.agent/` directory with project-specific context) aligns with the claude_skills repository's skill plugin model and could inform how project-specific context is surfaced to Claude Code
- The Telegram bot interaction modes (chat vs research vs planning vs task) map cleanly onto interactive skill dispatch patterns in Claude Code

---

## References

- [alekspetrov/pilot GitHub Repository](https://github.com/alekspetrov/pilot) (accessed 2026-02-19)
- [Pilot Documentation Site](https://pilot.quantflow.studio/) (accessed 2026-02-19)
- [GitHub API: repos/alekspetrov/pilot](https://api.github.com/repos/alekspetrov/pilot) (accessed 2026-02-19)
- [GitHub API: releases/latest v1.46.7](https://api.github.com/repos/alekspetrov/pilot/releases/latest) (accessed 2026-02-19)
- [Business Source License 1.1](https://mariadb.com/bsl11/) (accessed 2026-02-19)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude CodePro](./claude-codepro.md) | coding-agents | referenced by Claude CodePro (coding-agents) |
