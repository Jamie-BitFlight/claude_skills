---
title: "Pilot Shell"
subtitle: "Spec-Driven Development Framework for Claude Code"
category: "coding-agents"
resource_url: "https://github.com/maxritter/pilot-shell"
github_url: "https://github.com/maxritter/pilot-shell"
date_created: "2026-05-25"
date_last_reviewed: "2026-05-25"
status: published
---

## Overview

**Pilot Shell** is a commercial spec-driven development framework that enhances Claude Code with structured workflows for feature planning, test-driven implementation, and automated verification. Version 9.0.5 (released 2026-05-22) provides a complete end-to-end development cycle from requirements to production-grade code, enforced quality gates, and persistent knowledge across sessions.

**License**: Source-available under commercial license (Solo/Team/Enterprise tiers at <https://polar.sh/max-ritter/portal>).

**Primary use**: Interactive `/spec` command for planned feature work with approval gates, TDD enforcement, and code review; `/fix` for bugfix workflows; `/prd` for requirements brainstorming; `pilot bot` for 24/7 background automation.

**Platform support**: macOS, Linux, Windows (WSL2). Installs globally via `curl -fsSL https://raw.githubusercontent.com/maxritter/pilot-shell/main/install.sh | bash` (~2 minutes).

---

## Problem Addressed

Claude Code writes code fast but without structure — contexts are lost between sessions, tests are skipped, results become inconsistent, and code quality varies. Existing frameworks add complexity (dozens of agents, thousands of lines of config) without meaningfully better output.

Pilot Shell solves this by providing engineered solutions for each stage of development:

- **No context loss**: Persistent session memory preserves decisions, discoveries, and session state across resumable sessions
- **Enforced testing**: TDD is mandatory — /spec and /fix workflows require failing tests before implementation, and tests must pass before code is merged
- **Structured workflows**: Instead of freeform chat, users invoke `/spec` (planning + implementation + verification), `/fix` (bugfix with root-cause verification), `/prd` (requirements → PRD), or `/setup-rules` (codebase conventions discovery)
- **Quality automation**: Integrated hooks enforce linting, formatting, type checking, and full test suite on every code change without manual intervention
- **Cost efficiency**: 60–90% token reduction via RTK compression and Semble code search

---

## Key Statistics

- **Current version**: 9.0.5 (released 2026-05-22)
- **Python version requirement**: 3.12 only (`requires-python = ">=3.12,<3.13"`)
- **Languages supported**: Python, TypeScript/JavaScript, Go (auto-formatted + linted); TDD and spec-driven development work with any language Claude Code supports
- **MCP servers bundled**: 7 preconfigured (library docs, persistent memory, web search, GitHub code search, web fetching, code knowledge graphs, hybrid code search via Semble)
- **Licensing tiers**:
  - Solo: 1 seat, all features, community support
  - Team: Multi-seat, extension sharing, customization, priority support
  - Enterprise: 100+ seats, full source code access, dedicated support

---

## Key Features

### /spec — Spec-Driven Development Workflow

Unified feature and bugfix workflow with planning, implementation, and verification phases. Invokes phase-specific skills (`spec-plan`, `spec-implement`, `spec-verify` for features; `spec-bugfix-plan`, `spec-bugfix-verify` for bugs).

**Planning phase**:
- Explores codebase with semantic search (Semble) and code knowledge graphs (CodeGraph)
- Asks clarifying questions
- Writes detailed spec with scope, tasks, and definition of done
- For UI features, writes E2E test scenarios (step-by-step, browser-executable) that become the verification contract
- Spec-review sub-agent validates completeness
- Optional Codex adversarial review provides independent second opinion
- Waits for user approval with inline annotation support (select text or click + to annotate; agent reads annotations at next review checkpoint)

**Implementation phase**:
- Creates isolated git worktree for branch isolation
- Strict TDD: RED → GREEN → REFACTOR for each task
- Quality hooks auto-lint, format, type-check on every edit
- Full test suite runs after each task
- No manual code edits — all changes go through Claude Code's Edit tool

**Verification phase**:
- Full test suite + actual program execution
- Unified review sub-agent (compliance + quality + goal assessment)
- For UI features, executes each E2E scenario step-by-step via browser automation (results written to plan)
- Auto-fixes findings and re-runs verification
- Squash merge to main on success

### /fix — Bugfix Workflow

Lightweight bugfix lane for single-file, obvious-once-traced root causes. No plan file, no approval mid-flow, but TDD still enforced.

**Flow**: Investigate → RED (write failing test) → Fix (at root cause) → Verify end-to-end → Quality gate → Done

**Bail-out condition**: If investigation reveals the bug is multi-component, architectural, needs defense-in-depth, or two attempts have failed, `/fix` stops cleanly and directs user to use `/spec` instead.

### /prd — Requirements Brainstorming

Converts vague problem statements into product requirements documents saved to `docs/prd/`. Automatically picks between "Ideate" mode (free-form, 3–5 directions) and "Clarify → Converge → Write" mode.

**Research tiers**:
- Quick: Skip research
- Standard: Web search for competitors, prior art, best practices
- Deep: Parallel research agents for comprehensive findings

### /setup-rules — Auto-Generated Project Context

12-phase workflow that reads codebase and generates modular AI context rules (`.claude/rules/`), MCP server documentation, and project tech stack discovery. Migrates existing `CLAUDE.md` and `AGENTS.md` into modular rules. For monorepos, organizes rules in nested subdirectories with path-scoping.

### /create-skill — Reusable Skill Creator

6-phase workflow that turns domain knowledge into reusable skills (stored in `.claude/skills/` for project scope or `~/.claude/skills/` for global). Automatically categorizes by complexity, generates frontmatter with triggering conditions, applies portability and determinism checklists, and iterates with test prompts.

### /benchmark — Impact Measurement

Runs prompts with and without a target rule or skill, grades outputs against falsifiable assertions, and produces a structured verdict + improvement plan. Isolation mode auto-hides global extensions for duration, then restores on completion (survives SIGKILL via recovery manifest).

### Console — Local Web Dashboard

Port `localhost:41777` (configurable via `CLAUDE_PILOT_WORKER_PORT`). SQLite-backed, nothing leaves the machine.

**Views**:
- Dashboard: 8 clickable stat cards (Specifications, Requirements, Sessions, Memories totals), recent items, active spec pills, notification bell
- Sessions: Browse and resume past sessions via `/resume <session-id>`
- Memories: Observations (decisions, discoveries, bugfixes) with type filters and search
- Requirements: PRD documents with view/annotate modes
- Specifications: All spec plans with task progress, phase tracking, iteration history; **Annotate mode** for marking up plans before approval; **Share with Teammate** for async review with compressed share links
- Extensions: Rules, skills, commands, agents across global/project/plugin/remote scopes; git push/pull/diff for team sharing; APM-compatible export
- Changes: Git diff viewer with staged/unstaged files, branch info; **Review mode** for inline diff annotations (agent reads before marking spec verified)
- Usage: Daily token costs, model routing breakdown, usage trends
- Settings: Spec workflow toggles (branch isolation, ask questions, plan approval, **Model Switching**), reviewer toggles (spec review, changes review, optional Codex)

**Spec sharing**: Click **Share with Teammate** to generate compressed share link with entire spec and annotations encoded into URL fragment (no server transmission). Recipients open on pilot-shell.com, add feedback inline, click Submit — annotations flow back automatically (60-second poll), grouped by author in Console. Links expire after 7 days.

### Pilot Bot — 24/7 Automation Agent

Persistent background Claude Code session with scheduled jobs, health checks, heartbeat monitoring, and optional Telegram integration (auto-detects if `Telegram Channels plugin` is installed). Runs `pilot bot` to launch.

**Bot skills**:
- `bot-boot`: Health check, job registration, heartbeat setup
- `bot-heartbeat`: Periodic checks, notifications only on issues
- `bot-jobs`: Manage scheduled jobs (add, remove, pause, resume, edit, list)
- `bot-channel-task`: Telegram task flow (acknowledge, execute, report)
- `bot-defaults`: Standard behaviors (dedup, reporting, error handling)

### Model Switching

Default: Opus for planning (hard-blocked by `spec-mode-guard` hook), Sonnet[1M] for implementation to reduce cost. `/model <model-name>` switches the active model.

**With Model Switching toggle ON** (default):
- Plan → Implement → Verify all run on selected model
- After approval, planner stops; user runs `/model sonnet[1m]` then any prompt (e.g., `continue`) to resume
- `spec_handoff_resume` hook routes next prompt directly to `spec-implement` without `/clear` or re-invoking `/spec`

**With toggle OFF**:
- Plan → Implement → Verify run continuously on active model
- No interruption for model switching

### Status Line

Real-time session metrics below every Claude Code response across 3 lines:

**Line 1 — Session metrics**:
- Model (e.g., `Opus 4.7 [1M]`)
- Context usage with progress bar (green <80%, yellow 80–95%, red 95%+)
- Lines changed in session (hidden when rate limits available)
- Git branch + staged/unstaged counts (hidden when rate limits available)
- Rate-limit % with pacing arrow and reset countdown (Pro/Max subscriptions on Claude Code 2.1.80+)
- Session cost in USD (green <$1, yellow $1–5, red $5+; hidden when rate limits available)
- Savings % from RTK proxy

**Line 2 — Mode**:
- Quick Mode
- OR Spec mode: plan name, type (feature/bugfix), phase, progress bar, task count, iteration count

**Line 3 — Version & session info**:
`Pilot <version> (<tier>) · CC <version> (<subscription>) · sessions <N> · memories <N>`

### Quality Hooks

15 hook registrations across 7 events:
- **On every file edit**: ruff (Python), ESLint (TypeScript), go vet (Go)
- **TDD enforcement**: RED → GREEN → REFACTOR validation
- **Token optimization**: RTK compression (60–90% savings)
- **Session continuity**: Memory capture, session state persistence
- **Session lifecycle**: Boot, resumption, logging

### Rules & Standards

10 built-in rules for workflow, testing, verification, debugging, code review, documentation sync, tooling, MCP routing + 5 coding standards (Python, TypeScript, Go, Frontend, Backend) auto-activated by file type.

### Context Optimization

Lean context strategies:
- RTK output compression
- Semble chunk-only code search
- Conditional rule loading (only relevant rules per file type)
- Progressive skill disclosure (frontmatter loads always, SKILL.md on activation, linked files on demand)
- Lazy MCP tool loading
- Compaction resilience for 200K windows

### Extensions Management

Unified view of skills, rules, commands, agents across global (→ `~/.claude/`), project (→ `.claude/`), plugin (read-only), and remote scopes. Console Extensions page offers:
- Browse, edit, compare all in one place
- Team sharing via git with push, pull, diff
- **APM-compatible export** (toggleable): Extensions auto-converted to APM conventions on push; `apm install owner/repo` compatible
- Conflict detection when local ≠ remote

### Customization (Team/Enterprise)

Modify what Pilot auto-installs:
- **Skills**: Overlay ops (`insert_after`, `insert_before`, `replace`, `disable`) or ship entirely new skill folder
- **Rules**: New rules additive; same filename overrides core rule
- **Hooks**: Custom scripts + registration via `hooks.json`
- **Agents**: Add review/helper agents to `~/.claude/agents/`
- **MCP servers**: Deep-merge into `~/.claude.json` `mcpServers`
- **Claude settings**: Deep-merge `settings.json` and `claude.json`

Source is a **git repo** (team-wide) or **local directory** (personal, no git).

**Skill overlay persistence**: Replaced fragments pinned to upstream by hash. `pilot customize status` surfaces drift when Pilot upgrades. `pilot customize diff <skill>/<step-id>` shows changes so improvements can be ported.

### Headless Mode

Run Pilot non-interactively in CI/CD with `-p` flag:
```bash
pilot -p "Run tests and fix failures" --allowedTools "Bash,Read,Edit"
pilot -p "Summarize this project" --output-format json
pilot --channels plugin:telegram@official -p "Check messages"
```

All Claude Code CLI flags pass through unchanged.

---

## Technical Architecture

### Core Components

**Launcher** (Cython-compiled binary):
- Compiled Python entry point for fast startup
- Handles license validation (once per 24h to `api.polar.sh`)
- Manages session state and environment setup
- Auto-updates Claude Code to latest if native installer detected

**Installer** (Python):
- 7-step idempotent installation with rollback on failure
- Checks/installs prerequisites (Homebrew, Node.js, Python 3.12+, uv, git, jq)
- Installs Claude files to `~/.claude/` (native layout): rules, commands, hooks, MCP servers, agents
- Installs language servers (basedpyright, vtsls, gopls)
- Configures `.nvmrc` and project config
- Shell integration for bash, fish, zsh with `pilot` alias
- VS Code extensions installer

**Console** (React/TypeScript web dashboard):
- Local web server at `localhost:41777`
- SQLite database for sessions, memories, specs, requirements, extensions, usage stats
- Real-time SSE updates for notifications
- Collaborative annotation panel (shared spec links with teammate feedback)
- Search, filter, browse across all views
- No data transmission to external services

**Skills** (Markdown-based workflows):
- Each skill is a folder with `manifest.json` + `orchestrator.md` + `steps/`
- Phase skills: `spec-plan`, `spec-implement`, `spec-verify`, `spec-bugfix-plan`, `spec-bugfix-verify`, `fix`, `prd`, `create-skill`, `setup-rules`, `benchmark`
- Bot skills: `bot-boot`, `bot-heartbeat`, `bot-jobs`, `bot-channel-task`, `bot-defaults`
- Sub-agents: `spec-review`, `changes-review`, `web-search-agent`, optional Codex reviewers
- Routing via orchestrator dispatcher (Bash env var reads + Read plan files only; no substantive work)

**Agents** (Claude Code sub-agents):
- `spec-review`: Validates plan completeness
- `changes-review`: Code review before merge
- `changes-review-codex`: Optional OpenAI Codex adversarial review
- `web-search-agent`: Research for `/prd` deep mode
- All sub-agents hard-coded to Sonnet (no 1M context support)

**MCP Servers** (7 preconfigured):
- Library docs search
- Persistent memory store
- Web search
- GitHub code search
- Web page fetching
- Code knowledge graph (CodeGraph)
- Hybrid code search (Semble)
- (Optional) Chrome DevTools MCP for browser automation

**Hooks** (Bash scripts registered in settings.json):
- Quality checks on every file edit (ruff, ESLint, go vet)
- TDD enforcement on test/implementation pairs
- RTK token optimization proxy
- Session state persistence
- Session resumption routing
- Memory capture on completion

**Language Servers** (LSP):
- Python: basedpyright
- TypeScript: vtsls
- Go: gopls
- Auto-installed, auto-configured

### Data Flow

1. **Session initiation**: `pilot` command → launcher checks license + Claude Code installation → sets up environment variables → hands off to Claude Code with skill loader
2. **Skill dispatch**: `/spec <task>` → `spec` orchestrator reads env vars and existing plans → routes to `spec-plan` (feature) or `spec-bugfix-plan` (bugfix) → awaits skill completion
3. **Phase execution**: Phase skill (`spec-plan` → `spec-implement` → `spec-verify`) reads plan file (if resuming), executes steps, writes plan updates, signals completion
4. **Sub-agent coordination**: Main skill calls sub-agents for review steps (Sonnet-based, no 1M context); sub-agents return findings; main skill processes and updates plan
5. **Console updates**: Phase skills write to SQLite (sessions table, specs table, memories table) via hooks; Console polls and displays updates in real-time
6. **Merge and cleanup**: After verification pass, spec workflow squash-merges worktree to main and deletes worktree; memories captured to persistent store

### Extension Points

**Customization overlays** (Team/Enterprise):
- `customization.json` metadata + optional `insert_after`, `insert_before`, `replace`, `disable` ops on skill steps
- Ship new skill folders to extend workflows
- Override rules by filename (exact path match)
- Inject hooks via `hooks.json`
- Add agents to `~/.claude/agents/`
- Deep-merge MCP and Claude settings

**MCP server registration**:
- Preconfigured in `.mcp.json`; merged into `~/.claude.json` at install time
- Custom MCP servers added via `customization.json` or manual `.mcp.json` edit

**Skill registration**:
- Detected automatically from `manifest.json` + `orchestrator.md` in `.claude/skills/` (project) or `~/.claude/skills/` (global)
- Frontmatter `name:` and `description:` determine when skill is auto-loaded
- Progressive disclosure: frontmatter loaded always (~100 tokens), `orchestrator.md` on activation, linked reference files on demand

---

## Installation & Usage

### Prerequisites

- **Claude Code**: Must use native installer (not npm/brew). Auto-detected; installer attempts setup if missing
- **Claude subscription**: Max 5x/20x (solo), Team Premium (teams), or Enterprise (organizations)
- **Terminal**: Any modern terminal; cmux, Ghostty, iTerm2 recommended for multi-session layout
- **Chrome (recommended)**: Claude Code Chrome extension for browser automation; auto-detected and preferred. Fallback: Chrome DevTools MCP → playwright-cli → agent-browser

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/maxritter/pilot-shell/main/install.sh | bash
```

**Installer steps**:
1. Prerequisites (Homebrew, Node.js, Python 3.12+, uv, git, jq)
2. Claude files to `~/.claude/` (rules, commands, hooks, MCP, agents)
3. Project config (`.nvmrc`, project settings)
4. Dependencies (Semble, RTK, CodeGraph, Chrome DevTools MCP, playwright-cli, agent-browser, language servers)
5. Shell integration (bash, fish, zsh)
6. VS Code extensions
7. Finalize and success message

Installs in ~2 minutes. Idempotent — re-running applies only new steps.

### Usage

**Interactive development**:
```bash
cd <any-project>
pilot
```

Then:
```bash
/spec "Add user authentication with OAuth and JWT tokens"
/fix "annotation persistence drops fields between save and reload"
/prd "Add real-time notifications for team updates"
/setup-rules
/create-skill "Automate the review and triaging of PR Bot comments"
/benchmark pilot/skills/create-skill
```

**Headless (CI/CD)**:
```bash
pilot -p "Run tests and fix failures"
pilot --model opus -p "Summarize this project"
```

**Background automation**:
```bash
pilot bot
```

**Management**:
```bash
pilot update                    # Check and apply updates
pilot activate <license-key>    # Activate license
pilot customize install <git-url-or-path>  # Install customization (Team/Enterprise)
pilot customize status          # Check active customization and drift
```

### Downgrade/Uninstall

```bash
# Downgrade to specific version
export VERSION=9.0.5
curl -fsSL https://raw.githubusercontent.com/maxritter/pilot-shell/main/install.sh | bash

# Uninstall
curl -fsSL https://raw.githubusercontent.com/maxritter/pilot-shell/main/uninstall.sh | bash
```

### Dev Container Support

Copy `.devcontainer` from repo, adapt (base image, extensions, dependencies), run installer inside. Auto-detects container environment and skips system-level dependencies. For tighter isolation, layer Claude Code's `/sandbox` on top; Dockerfile pre-installs `bubblewrap`, `socat`, `iptables`, `ipset`.

---

## Relevance to Claude Code Development

### Primary Use Cases

1. **Specification-driven feature development**: Users can now invoke `/spec` for planned work instead of freeform chat, getting structured planning, TDD-enforced implementation, and verification-before-merge
2. **Organized bugfix workflows**: `/fix` lane routes simple bugs away from complex code review; multi-component bugs cleanly bail out to `/spec`
3. **Persistent context across sessions**: Memories and session resumption mean decisions and discoveries are not lost between Claude Code restarts
4. **Quality automation without manual enforcement**: Hooks auto-lint, format, type-check, and run tests — no manual "forgot to lint" or "test didn't run"
5. **Cost reduction via optimization**: RTK compression + Semble code search reduce token usage by 60–90%
6. **Team coordination**: Spec sharing (no accounts, no encryption, encoded in URL), extension sharing via git, customization for team workflows

### Integration Points

- **Native plugin system**: Pilot ships as a Claude Code plugin with agents, skills, rules, hooks, and MCP servers
- **Claude Code CLI passthrough**: All Claude Code flags (`--model`, `--channels`, `--output-format`, etc.) work directly with `pilot`
- **Permission modes**: Respects Claude Code's permission settings; `/spec` uses `bypassPermissions` for autonomous workflow, but `Shift+Tab` cycles modes if user prefers
- **MCP ecosystem**: Integrates 7 MCP servers; customization allows additional servers
- **Language server integration**: basedpyright, vtsls, gopls auto-installed and configured

### Differentiation from Built-in Claude Code Features

| Feature | Claude Code | Pilot Shell |
|---------|-----------|------------|
| Plans | Shift+Tab plan mode (proposal only) | `/spec` (full workflow: plan → implement → verify with TDD) |
| Testing | Manual test writing | TDD enforced (RED → GREEN → REFACTOR) |
| Verification | Manual verification | Automated E2E scenario execution + unified review |
| Context persistence | Session logs only | Memories (decisions, discoveries, bugs) + resumable sessions |
| Quality gates | None | Hooks auto-enforce linting, formatting, type-checking, tests |
| Code review | PR comments | Real-time annotation + `/spec` blocks on failure |
| Cost optimization | No optimization | RTK + Semble reduce tokens 60–90% |
| Model switching | Manual per-session | `/model` command with `spec_handoff_resume` automation |

---

## Limitations and Caveats

### Documented Limitations

- **Python version lock**: Python 3.12 only (`requires-python = ">=3.12,<3.13"`). Python 3.13 not yet supported
- **Quality hooks scope**: Auto-linting, formatting, type-checking work only for Python, TypeScript/JavaScript, Go. Other languages require custom hooks
- **Sub-agent models**: Codex adversarial reviewers require ChatGPT Plus ($20/mo) subscription. Web search agent limited to Standard/Deep `/prd` research tiers (Quick skips research)
- **Model switching interaction**: With toggle ON, plan and implementation run on different models; requires `/model` switch between phases. Toggle OFF forces continuous model for all phases
- **Customization tier**: Customization (skill overlays, rule modifications, hook injection, MCP servers, settings merging) available on Team and Enterprise plans only
- **Data persistence scope**: Console dashboard and memories are SQLite-backed, local-only. Spec sharing uses URL-encoded data (7-day link expiry). No cloud sync of memories across machines

### Documented Absence of Limitations

Per README FAQ: "No limitations documented in reviewed sources" for offline operation, data privacy, enterprise compliance. All code and data remain on user's machine except licensing calls (3 total: daily validation, one-time activation, one-time trial start). Optional Codex plugin is the only external API integration beyond Claude Code's own API usage.

### Known Trade-offs

- **License verification overhead**: Daily check to `api.polar.sh` (cached locally, works offline 7 days). Unacceptable in airgapped environments without 7-day recycle or perpetual license (Enterprise only)
- **Launcher compilation**: Cython-compiled launcher binary (not pure Python). Adds complexity for audits but enables faster startup
- **RTK proxy cost**: Token optimization reduces API costs but requires separate RTK infrastructure setup (included in Pilot installer)
- **Git worktree isolation**: Each `/spec` creates isolated worktree for branch isolation, which increases disk usage for large repos

---

## References

- **Official website**: <https://pilot-shell.com/>
- **Documentation**: <https://pilot-shell.com/docs/>
- **Blog**: <https://pilot-shell.com/blog/>
- **Changelog**: <https://pilot.openchangelog.com/>
- **GitHub repository**: <https://github.com/maxritter/pilot-shell>
- **License management**: <https://polar.sh/max-ritter/portal> (recover lost license key)
- **Demo project**: <https://github.com/maxritter/pilot-shell-demo>

### Key Documentation Sections (verified 2026-05-25)

- **Workflows**: `/spec`, `/fix`, `/prd`, `/setup-rules`, `/create-skill`, `/benchmark` (<https://pilot-shell.com/docs/workflows>)
- **Features**: Console, Pilot Bot, Model Switching, Extensions, Customization, Rules & Standards, Context Optimization (<https://pilot-shell.com/docs/features>)
- **Permission modes**: Shift+Tab cycling through Plan/Accept Edits/Normal modes (<https://pilot-shell.com/docs/features/permission-modes>)
- **Sandboxing**: Layer Claude Code's `/sandbox` for untrusted code execution (<https://code.claude.com/docs/en/sandboxing>)
- **Codex plugin**: Independent OpenAI adversarial code review (<https://github.com/openai/codex-plugin-cc>, requires ChatGPT Plus)

---

## Freshness Tracking

**Last reviewed**: 2026-05-25

**Next review**: 2026-08-25 (3 months — update version, verify features, check changelog for breaking changes)

### Confidence Summary

| Section | Confidence | Source Quality | Notes |
|---------|-----------|----------------|-------|
| Identity/Metadata | high | README.md, pyproject.toml, git tags, LICENSE | Version verified from git tag and CHANGELOG; license verified from LICENSE file; platform support from README |
| Problem Addressed | high | README.md lines 40–50 | Direct quotes from official README; clear problem statement and solutions |
| Key Statistics | high | pyproject.toml, README FAQ, CHANGELOG, git history | Version from official tag; Python requirement from pyproject.toml; licensing tiers from README license section |
| Key Features | high | README.md Feature sections, skill manifests, orchestrator.md | Feature descriptions extracted directly from README; workflow descriptions from skill orchestrators; Console views documented in README |
| Technical Architecture | medium-high | pyproject.toml, pilot/ directory structure, orchestrator.md | Component names from actual repo structure; data flow inferred from skill descriptions and README; extension points from customization docs |
| Installation & Usage | high | README.md Getting Started section, official installer script | Installation steps extracted from README; prerequisites verified against installer script logic; usage examples from README |
| Limitations | medium | README.md FAQ, LICENSE, CHANGELOG | Documented limitations from FAQ and changelog; absence of limitations documented explicitly in FAQ section |
| References | high | README.md, LICENSE, CHANGELOG | All links extracted from official sources; access dates included |

### Confidence Rationale

- **High confidence**: Sections sourced from README, pyproject.toml, official manifests, and direct code examination
- **Medium-high confidence**: Technical Architecture inferred from directory structure and skill descriptions; some implementation details not fully documented in primary sources
- **Medium confidence**: Limitations based on FAQ absence assertions; no guarantee that absence of documentation equals absence of limitation

### Changes from Previous Research

N/A — initial research entry.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Maverick](./maverick.md) | coding-agents | Claude Code plugin with enforcement chain, three workflow modes, and upskill auto-generation from codebase |
| [SoulForge](./soulforge.md) | coding-agents | Graph-powered multi-agent architecture with live codebase indexing and task-specific model routing |
| [Cline](./cline.md) | coding-agents | Open-source autonomous agent with human-in-the-loop approvals and multi-provider LLM support |
| [Pilot](./pilot.md) | coding-agents | Autonomous development pipeline wrapping Claude Code CLI with ticket-to-PR automation |
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | Go-native guardrails and 5-verb spec-driven workflow with TDD enforcement |
| [Superpowers](../agent-frameworks/superpowers.md) | agent-frameworks | Agentic skills framework with 14 skills for TDD, debugging, and subagent-driven development |
| [Get Shit Done](../agent-frameworks/get-shit-done.md) | agent-frameworks | Spec-driven development system with 11 agents for Claude Code, OpenCode, and Gemini |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Comprehensive performance optimization system with 16 agents, 65+ skills, and hook-based automation |

