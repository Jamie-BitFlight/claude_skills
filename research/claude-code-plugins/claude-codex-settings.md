---
title: "claude-codex-settings"
research_date: "2026-03-06"
source_url: "https://github.com/fcakyon/claude-codex-settings"
github_url: "https://github.com/fcakyon/claude-codex-settings"
version_at_research: "v2.2.0"
license: "Apache-2.0"
last_verified: "2026-03-06"
version_at_verification: "v2.2.0"
next_review: "2026-06-06"
---

## Overview

`fcakyon/claude-codex-settings` is a battle-tested, daily-use plugin collection for Claude Code and OpenAI Codex, structured as installable Claude Code Plugins. It provides 17 plugins covering MCP server integrations, autonomous agents, slash commands, hooks, and skills — all installable via the Claude Code plugin marketplace in a single command. The repository also ships ready-to-use configuration files for running Claude Code against alternative LLM backends (Z.ai GLM, Kimi K2, ccproxy, Azure OpenAI).

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Claude Code lacks native integrations for cloud services (Azure, GCloud, Supabase, MongoDB, Linear, Slack) | Per-service MCP plugins with pre-configured `.mcp.json` and usage skills |
| Git/GitHub workflows require manual discipline for consistent commits, PRs, and review resolution | `github-dev` plugin provides four autonomous agents (commit-creator, pr-creator, pr-reviewer, pr-comment-resolver) plus confirmation hooks |
| Claude Code is locked to Anthropic API pricing | `ccproxy-tools` and alternative config files allow routing to GitHub Copilot, Z.ai GLM (85% cheaper), Kimi K2, local Ollama, or any OpenAI-compatible API |
| No visibility into session token usage or 5-hour rate-limit window | `statusline-tools` shows context %, cost, and 5H reset countdown using the ccusage API |
| Building Claude Code plugins requires knowledge of schema, validation rules, and best practices | `plugin-dev` plugin provides 7 skills, 3 agents, guided creation command, and validation hooks |
| Code quality enforcement is ad-hoc across sessions | `ultralytics-dev` hooks auto-format Python (ruff + Google docstrings), JS/TS (prettier), Markdown, and Bash on every write |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 452 | 2026-03-06 |
| Forks | 41 | 2026-03-06 |
| Contributors | 3 | 2026-03-06 |
| Latest Release | v2.2.0 | 2026-03-06 |
| Open Issues | 2 | 2026-03-06 |
| Plugins | 17 | 2026-03-06 |
| Listed in Awesome Claude Code | Yes | 2026-03-06 |
| Context7 indexed | Yes | 2026-03-06 |

---

## Key Features

### MCP Server Integrations (9 plugins)

- `azure-tools` — Microsoft Azure MCP Server (40+ services) with Azure CLI authentication; skills for best practices and setup troubleshooting
- `gcloud-tools` — Google Cloud Observability MCP for logs, metrics, and traces via `googleapis/gcloud-mcp`
- `linear-tools` — Linear issue tracking via official Linear MCP with OAuth; workflow skills
- `mongodb-tools` — MongoDB read-only MCP via `mongodb-js/mongodb-mcp-server`; safe for production exploration
- `paper-search-tools` — Academic paper search across arXiv, PubMed, IEEE, Scopus, ACM via Docker-based `mcp/paper-search`
- `playwright-tools` — Browser automation via `microsoft/playwright-mcp`; includes `responsive-tester` agent for viewport breakpoint testing
- `slack-tools` — Slack message search and channel history via `ubie-oss/slack-mcp-server`
- `supabase-tools` — Official Supabase MCP with OAuth authentication
- `tavily-tools` — Web search and content extraction via `tavily-ai/tavily-mcp`

### Git and GitHub Workflow (`github-dev`)

- Four autonomous agents: `commit-creator` (intelligent commit messages), `pr-creator` (PR creation), `pr-reviewer` (code review), `pr-comment-resolver` (resolves review comments)
- Slash commands: `/commit-staged`, `/create-pr`, `/review-pr`, `/resolve-pr-comments`, `/update-pr-summary`, `/clean-gone-branches`
- Safety hooks: `git_commit_confirm.py` (pre-commit confirmation), `gh_pr_create_confirm.py` (pre-PR creation confirmation)
- Skills for commit message format, PR creation workflow, PR comment style

### Plugin Development Toolkit (`plugin-dev`)

- 7 skills: `hook-development`, `mcp-integration`, `plugin-structure`, `plugin-settings`, `command-development`, `agent-development`, `skill-development`
- 3 agents: `agent-creator` (AI-assisted agent generation), `plugin-validator` (structural validation), `skill-reviewer` (quality improvement)
- 8-phase guided creation command `/plugin-dev:create-plugin`
- Validation hooks: SKILL.md structure, MCP/hook file locations, plugin.json paths, plugin directory structure
- Auto-sync hook: `sync_marketplace_to_plugins.py` keeps marketplace.json aligned with plugin.json files

### LLM Backend Flexibility

- **Z.ai GLM** (`settings-zai.json`): GLM-5 as default, GLM-4.7-Flash as fast model; 85% cost savings over Claude 4.5 via Anthropic-compatible API at `api.z.ai`
- **Kimi K2** (environment variables): `kimi-k2-thinking-turbo` with 256K context via `api.moonshot.ai/anthropic/`
- **ccproxy** (`ccproxy-tools`): Routes Claude Code through Claude Pro/Max subscription OAuth, GitHub Copilot, Gemini, local Ollama, or any OpenAI-compatible provider
- **OpenAI Codex** (`.codex/config.toml`): `gpt-5-codex` via Azure `responses` API surface with `model_reasoning_effort = "high"`
- **Default OpusPlan mode** (`settings.json`): plan/execute/subagent on Opus 4.5, fast on Sonnet 4.5, `CLAUDE_CODE_EFFORT_LEVEL=high`, telemetry disabled

### Developer Productivity Hooks

- `ultralytics-dev`: Auto-formatting on every write — Google-style Python docstrings, ruff quality checks, prettier for JS/TS/CSS/JSON, Markdown formatting, bash script formatting
- `general-dev`: `enforce_rg_over_grep.py` intercepts grep calls and suggests ripgrep; `code-simplifier` agent analyzes patterns and enforces conventions
- `notification-tools`: OS desktop notifications (macOS + Linux) on task completion via `notify.sh` (PostTaskComplete hook)
- `statusline-tools`: Cross-platform statusline showing session context %, cost, and 5H usage with color-coded thresholds (green/yellow/red)

### Context and Settings Management (`claude-tools`)

- `/load-claude-md` — Re-injects CLAUDE.md into context without restarting (for long sessions)
- `/sync-claude-md` — Pulls latest CLAUDE.md from GitHub repository
- `/sync-allowlist` — Syncs permissions allowlist from GitHub
- `/load-frontend-skill` — Loads Anthropic's official frontend design skill

---

## Technical Architecture

The repository is structured as a Claude Code marketplace plugin collection. The root `.claude-plugin/marketplace.json` defines the `claude-settings` marketplace with 17 plugins at v2.2.0. Each plugin lives under `plugins/{name}/` and follows the standard Claude Code plugin schema:

```text
plugins/{name}/
  .claude-plugin/plugin.json   — plugin metadata, version, keywords
  .mcp.json                    — MCP server configuration (for MCP plugins)
  agents/                      — autonomous subagent definitions (.md frontmatter)
  commands/                    — slash command definitions (.md)
  hooks/
    hooks.json                 — hook registration
    scripts/                   — Python/shell hook implementations
  skills/                      — skill content (SKILL.md files)
```

MCP server configurations reference upstream servers by npm package or Docker image — no custom server code is included. The plugin's `.mcp.json` is installed into the user's Claude Code settings at plugin install time.

Hook scripts are Python or shell and use Claude Code's prompt-based hook API. The `github-dev` hooks call back into Claude to request confirmation before destructive git operations. The `plugin-dev` validation hooks run on every Write/Edit to enforce structural correctness of plugin files being authored.

Configuration files at the repo root (`.claude/settings.json`, `.claude/settings-zai.json`) are reference configurations the user copies or symlinks to activate a particular LLM backend. The `.codex/config.toml` activates OpenAI Codex with Azure as provider.

---

## Installation & Usage

```bash
# Step 1: Register the marketplace
/plugin marketplace add fcakyon/claude-codex-settings

# Step 2: Install individual plugins (select as needed)
/plugin install github-dev@claude-settings
/plugin install plugin-dev@claude-settings
/plugin install statusline-tools@claude-settings
/plugin install ccproxy-tools@claude-settings
/plugin install ultralytics-dev@claude-settings

# Step 3: Run setup for MCP-backed plugins
/github-dev:setup
/statusline-tools:setup

# Step 4: Create AGENTS.md symlink for cross-tool compatibility
ln -s CLAUDE.md AGENTS.md
```

```bash
# Use Z.ai GLM backend (85% cheaper)
# Copy settings-zai.json to ~/.claude/settings.json
# Set ANTHROPIC_AUTH_TOKEN=<your_zai_api_key>

# Use Kimi K2 backend
export ANTHROPIC_BASE_URL="https://api.moonshot.ai/anthropic/"
export ANTHROPIC_API_KEY="your-moonshot-api-key"
export ANTHROPIC_MODEL=kimi-k2-thinking-turbo
```

```bash
# Plugin development workflow
/plugin-dev:load-skills          # Load all 7 plugin development skills
/plugin-dev:create-plugin        # Start 8-phase guided creation
```

---

## Relevance to Claude Code Development

### Applications

- The `plugin-dev` plugin is directly applicable to our plugin authoring workflow — its 7 skills cover the same domains as our own plugin development documentation, and its validation hooks could supplement our `plugin_validator.py`
- The `github-dev` agents (commit-creator, pr-creator, pr-reviewer, pr-comment-resolver) are analogous to our own `commit-creator` and related workflow agents — studying the implementation reveals patterns for confirmation hooks and agent structure
- The `statusline-tools` approach (ccusage API + color-coded thresholds) is a concrete implementation pattern for usage visibility that users of our plugins would benefit from
- The `ultralytics-dev` hook architecture (one hook file per formatter, auto-triggered on Write/Edit) is a clean pattern for code quality enforcement without blocking the user

### Patterns Worth Adopting

- **Per-plugin `.mcp.json` pattern**: Each MCP-backed plugin ships its own `.mcp.json` rather than requiring manual configuration — the install command deploys it automatically. This is cleaner than our current approach of documenting MCP config manually.
- **Setup command pattern**: Every MCP plugin includes a `/plugin-name:setup` slash command that walks through configuration. This decouples "install" from "configure" and handles first-run friction.
- **Confirmation hook pattern**: `git_commit_confirm.py` and `gh_pr_create_confirm.py` use the prompt hook API to gate destructive operations — a safety pattern worth adopting in our own git-workflow plugins.
- **`sync_marketplace_to_plugins.py` auto-sync hook**: Keeps marketplace registry in sync with per-plugin metadata automatically on every write — prevents version drift between `marketplace.json` and individual `plugin.json` files.
- **Kimi K2 / Z.ai config templates**: Providing ready-to-use settings files for alternative backends removes the research burden from users wanting cost savings.

### Integration Opportunities

- Our research-curator plugin could reference this repo's `plugin-dev` skill content as a reference implementation for plugin structure documentation
- The `plugin-dev` validation hooks (`validate_skill.py`, `validate_plugin_structure.py`) could be cross-referenced with our own `plugin_validator.py` to identify coverage gaps
- The statusline color-coding approach (green/yellow/red at 50%/70% thresholds) could be adopted in our own session management tooling

---

## References

- [fcakyon/claude-codex-settings — GitHub](https://github.com/fcakyon/claude-codex-settings) (accessed 2026-03-06)
- [Awesome Claude Code — hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) (accessed 2026-03-06)
- [Context7 index — context7.com/fcakyon/claude-codex-settings](https://context7.com/fcakyon/claude-codex-settings) (accessed 2026-03-06)
- [Z.ai GLM-4.6 pricing announcement](https://z.ai/blog/glm-4.6) (accessed 2026-03-06)
- [Kimi K2 Claude Code guide — platform.moonshot.ai](https://platform.moonshot.ai/docs/guide/agent-support) (accessed 2026-03-06)
- [ccproxy — starbased-co/ccproxy](https://github.com/starbased-co/ccproxy) (accessed 2026-03-06)
- Local worktree at `.worktrees/claude-codex-settings/` — files: `README.md`, `.claude/settings.json`, `.claude/settings-zai.json`, `.codex/config.toml`, `.claude-plugin/marketplace.json`

---
