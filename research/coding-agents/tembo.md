---
title: "Tembo"
research_date: "2026-02-23"
source_url: "https://www.tembo.io/"
github_url: "<https://github.com/tembo-io/tembo> (private / organization page)"
version_at_research: "Cloud service (SaaS)"
license: "Proprietary (commercial SaaS)"
last_verified: "2026-02-23"
version_at_verification: "Cloud service (SaaS)"
next_review: "2026-05-23"
---

## Overview

Tembo is a cloud-based AI coding agent orchestration platform that delegates software engineering work
to autonomous agents (Claude Code, Cursor, OpenAI Codex, Amp, OpenCode) on behalf of development
teams. It integrates with existing project management tools (Linear, Jira), source control (GitHub,
GitLab, Bitbucket), error tracking (Sentry), and communication platforms (Slack) to automatically
generate pull requests, fix bugs, update documentation, and reduce technical debt — all without
requiring developer context switching.

> **Note**: Tembo previously operated as a managed PostgreSQL cloud platform ("Tembo Stacks")
> before pivoting to the AI coding agent orchestration product described here.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Context switching between project management and coding tools | Tag @tembo in Slack, Linear, Jira, or GitHub to create tasks without leaving the tool |
| Repetitive, low-value engineering work consuming developer time | Automations detect and action recurring tasks (bug fixes, doc updates, dependency audits) automatically |
| Coordinating changes across multiple repositories | Single task can open coordinated PRs across many repos, even across platforms |
| Staying up to date with production errors | Sentry integration triggers automatic PR generation within seconds of a new error being detected |
| Vendor lock-in to a specific AI model | Agent-agnostic: run Claude Code, Codex, Cursor, Amp, or OpenCode; swap per-task or per-integration |
| Lack of review control over AI-generated code | All changes submitted as PRs; @tembo feedback loop iterates on changes in response to review comments |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Pricing (Free tier) | 10 credits/week, 1 repo | 2026-02-23 |
| Pricing (Pro) | $60/mo, 100 credits/mo, unlimited repos | 2026-02-23 |
| Pricing (Max) | $200/mo, 400 credits/mo | 2026-02-23 |
| Default coding agent | Claude Code (`claude-opus-4-5`) | 2026-02-23 |
| Supported coding agents | 5 (Claude Code, Codex, OpenCode, Amp, Cursor) | 2026-02-23 |
| Supported LLM providers | Anthropic, OpenAI, Google, Moonshot, Cursor, XAI | 2026-02-23 |
| Source control integrations | GitHub, GitLab, Bitbucket | 2026-02-23 |

---

## Key Features

### Agent Orchestration

- Supports Claude Code, OpenAI Codex, OpenCode, Amp, and Cursor as execution backends
- Per-task and per-integration agent selection (`agentType:model[:reasoningLevel]` syntax)
- Each agent runs inside an isolated sandbox environment with full repository access
- Rule files (`AGENTS.md`, `tembo.md`, `.cursorrules`) guide agent behavior per project conventions

### Task Management & Integrations

- Assign tasks by tagging `@tembo` in Slack, Linear, Jira, GitHub Issues, or the Tembo dashboard
- Pulls issues directly from Linear and Jira for automated implementation
- Sentry integration auto-generates fix PRs within seconds of new error detection
- Raycast extension for launching tasks from the desktop

### Multi-Repository Support

- Single task can open PRs across multiple repositories simultaneously
- Supports cross-platform operations (e.g., GitHub + GitLab in one task)
- Useful for coordinated API + client library updates or monorepo-to-multirepo workflows

### Automations

- Schedule-based triggers: hourly, daily, weekly, monthly (cron syntax supported)
- Event-based triggers: PR opened/merged, Sentry error, Linear issue created, Slack @mention
- Pre-built templates for common patterns (PR descriptions, changelog generation, security scans)
- Each automation selects its own coding agent and MCP server configuration

### MCP (Model Context Protocol) Support

- Built-in MCP servers for GitHub, GitLab, Sentry, Linear, Slack, PostgreSQL, Supabase, AWS RDS
- Supports any custom MCP server for extending agent capabilities
- MCP servers are composable per-task or per-automation

### API & SDK

- Fully-typed TypeScript SDK for embedding Tembo as a tool call in custom agents/apps
- REST API for programmatic task creation and management
- Webhook support for event-driven integrations

### Feedback Loop

- Review PRs using standard team process; mention `@tembo` in PR comments to request changes
- Compatible with AI code review tools (Graphite, CodeRabbit, Cursor Bug Bot) — Tembo validates
  and auto-commits relevant suggestions when enabled
- Full audit trail of agent actions

---

## Technical Architecture

Tembo operates as a background orchestration layer:

1. **Detection** — Signals arrive via integrations (Sentry errors, Linear tickets, Slack messages,
   scheduled cron) or manual task creation through the dashboard/API.
2. **Execution** — Tembo provisions an isolated sandbox environment, clones the target repositories,
   and delegates the task to the configured coding agent (Claude Code by default). The agent reads
   rule files for project conventions and uses enabled MCP servers for tool access.
3. **Pull Request** — Changes are packaged as a pull request with contextual description submitted
   to the source control provider.
4. **Feedback Loop** — Team reviews the PR; `@tembo` mentions in comments trigger the agent to
   iterate. Compatible AI review bots' feedback is also consumed automatically.

**Infrastructure Note**: Sandbox environments have full repository access scoped per-task; MCP
servers provide the bridge to external services (databases, monitoring, issue trackers).

---

## Installation & Usage

```bash
# No local installation required — Tembo is fully cloud-hosted

# 1. Sign up at https://app.tembo.io/sign-up
# 2. Connect your source control (GitHub/GitLab/Bitbucket via OAuth)
# 3. Connect optional integrations (Linear, Jira, Sentry, Slack)
# 4. Create a task from the dashboard, API, or by tagging @tembo

# API: Create a task programmatically
curl -X POST https://api.tembo.io/tasks \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Fix the null pointer exception in user service",
    "repositories": ["my-org/my-repo"],
    "agent": "claudeCode:claude-opus-4-5"
  }'

# TypeScript SDK
import { Tembo } from "@tembo/sdk";
const tembo = new Tembo({ apiKey: process.env.TEMBO_API_KEY });
await tembo.tasks.create({
  description: "Update API docs for the new /users endpoint",
  repositories: ["my-org/api", "my-org/docs"],
  agent: "claudeCode:claude-4-5-sonnet"
});
```

### Rule Files

Add a `tembo.md` (or `AGENTS.md`) to your repo root to guide agent behavior:

```markdown
# Tembo Rules
- Use TypeScript strict mode
- Follow the existing test patterns in /tests
- Never modify migration files directly
- All PRs must include updated CHANGELOG.md
```

---

## Relevance to Claude Code Development

### Applications

- Automate routine skill/plugin maintenance across the `claude_skills` repository
- Use Tembo automations to keep `research/` entries fresh (weekly review + PR generation)
- Automatically generate PR descriptions for skill updates using event triggers on PR open
- Integrate with Sentry (if instrumented) for automated error-to-fix pipelines
- Delegate repetitive refactoring tasks (e.g., updating frontmatter schema across all SKILL.md files)

### Patterns Worth Adopting

- **Rule file conventions**: The `tembo.md` / `AGENTS.md` pattern of per-repo coding standards
  files is directly analogous to this repository's `CLAUDE.md` — worth aligning naming
- **Agent-agnostic task description**: Writing task descriptions that are model/agent-agnostic
  (describe _what_, not _how_) so any LLM backend can execute them
- **Feedback loop PR comments**: Iterating on AI work through natural-language PR review comments
  rather than re-submitting full tasks is a composable pattern for any agentic workflow
- **Automation templates**: Pre-built automation templates (like Tembo's PR description generator)
  are a good pattern for the `skills/` directory — parameterized reusable prompt patterns

### Integration Opportunities

- **Claude Code + Tembo**: Tembo's default agent is Claude Code (`claude-opus-4-5`), making it a
  natural orchestration layer for Claude Code-powered workflows across multiple repositories
- **MCP ecosystem**: Tembo's MCP server support means custom MCP servers built for this repo
  could be consumed by Tembo automations with no additional integration work
- **TypeScript SDK**: The Tembo SDK could be used in `scripts/` to trigger research-refresh or
  plugin-validation tasks programmatically
- **Skill development**: Skills that document agent orchestration patterns (multi-repo, feedback
  loops, event-driven automations) are directly informed by Tembo's architecture

---

## References

- [Tembo Website](https://www.tembo.io/) (accessed 2026-02-23)
- [Tembo Documentation](https://docs.tembo.io/) (accessed 2026-02-23)
- [Tembo Coding Agents Docs](https://docs.tembo.io/features/coding-agents) (accessed 2026-02-23)
- [Tembo Automations Docs](https://docs.tembo.io/features/automations) (accessed 2026-02-23)
- [Tembo Pricing](https://www.tembo.io/pricing) (accessed 2026-02-23)
- [Tembo Integrations](https://www.tembo.io/integrations) (accessed 2026-02-23)
- [Tembo November 2025 Release Notes](https://www.tembo.io/blog/nov-2025-release) (accessed 2026-02-23)
- [Tembo: The Background Coding Agents Company — Cerebral Valley](https://cerebralvalley.beehiiv.com/p/tembo-the-background-coding-agents-company) (accessed 2026-02-23)

---
