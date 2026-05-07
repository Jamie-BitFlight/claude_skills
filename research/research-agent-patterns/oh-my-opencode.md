# Oh My OpenCode

**Research Date**: 2026-03-06
**Source URL**: <https://github.com/code-yeongyu/oh-my-opencode>
**GitHub Repository**: <https://github.com/code-yeongyu/oh-my-opencode>
**npm Package**: <https://www.npmjs.com/package/oh-my-opencode>
**Version at Research**: v3.10.0 (latest release) / v3.10.1 (package.json)
**License**: SUL-1.0 (Sisyphus Use License — custom, non-OSI)

---

## Overview

Oh My OpenCode is a batteries-included agent orchestration harness built as an OpenCode plugin. It transforms the OpenCode TUI into a coordinated multi-agent development team by layering specialized agents (Sisyphus, Hephaestus, Prometheus, Atlas, Oracle), category-based model routing, and pre-integrated tools (LSP, AST-Grep, Tmux, MCP servers) on top of the base OpenCode runtime. Its defining principle is multi-provider freedom: tasks are routed across Claude, GPT, Gemini, Kimi, and GLM based on task category rather than manual model selection.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Single-model lock-in reduces quality and raises costs | Category-based routing (`visual-engineering`, `ultrabrain`, `quick`, `deep`) selects the best model automatically — Claude for orchestration, GPT-5.3 Codex for deep reasoning, Gemini for frontend, Haiku for speed |
| One agent doing everything creates context bloat and slow execution | Parallel background agents: Sisyphus fires 5+ specialist subagents simultaneously; each receives only the context relevant to its task |
| Stale-line errors when agents edit files with incorrect line references | Hash-anchored edit tool (`hashline_edit`) validates every change with `LINE#ID` content hashes, eliminating stale-line mismatches |
| No strategic planning before code execution | Prometheus agent conducts interview-mode planning — questions scope, identifies ambiguities, and produces a detailed plan before any code is touched |
| AI-generated comments pollute codebases with slop | Comment Checker rejects AI-sounding language in comments; agents write comments that read like a senior engineer wrote them |
| Agents go idle mid-task | Todo Enforcer detects idle agents and pulls them back to the active task automatically |
| OpenCode agents cannot run interactive programs (REPLs, debuggers, TUIs) | Full Tmux integration provides a live interactive terminal session within the agent context |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 37,517 | 2026-03-06 |
| GitHub Forks | 2,820 | 2026-03-06 |
| Contributors | 143 (last page of paginated results) | 2026-03-06 |
| Open Issues | 344 | 2026-03-06 |
| Latest Release | v3.10.0 | 2026-03-02 |
| Total Releases | 147 | 2026-03-06 |
| Primary Language | TypeScript (99.3%) | 2026-03-06 |
| npm Package | oh-my-opencode | 2026-03-06 |
| Created | 2025-12-03 | 2026-03-06 |
| Last Push | 2026-03-06 | 2026-03-06 |

---

## Key Features

### Agent Orchestration System

- **Sisyphus** (orchestrator): Plans, delegates to specialists, drives tasks to completion with aggressive parallel execution. Runs on Claude Opus 4.6, Kimi K2.5, or GLM 5. Does not stop halfway.
- **Hephaestus** (autonomous deep worker): GPT-5.3 Codex-native agent. Given a goal, not a recipe — explores codebase, researches patterns, executes end-to-end.
- **Prometheus** (strategic planner): Interview mode before any execution. Questions scope, identifies ambiguities, produces a detailed plan. Activated via Tab or `@plan`.
- **Atlas** (conductor): Executes Prometheus plans. Distributes tasks across subagents, accumulates learnings, verifies completion independently. Activated via `/start-work`.
- **Oracle** (consultant): Read-only high-IQ consultant for architecture decisions and complex debugging. Not used for implementation.
- **Supporting agents**: Metis (gap analyzer), Momus (ruthless plan reviewer), Explore (fast grep), Librarian (docs/OSS search), Multimodal Looker (vision/screenshots).

### Category-Based Model Routing

When Sisyphus delegates to a subagent, it picks a category — not a model name. The harness maps categories to models:

| Category | Use Case | Model Assignment |
|----------|----------|-----------------|
| `visual-engineering` | Frontend, UI/UX, design | Gemini |
| `deep` | Autonomous research + execution | Hephaestus / GPT-5.3 Codex |
| `quick` | Single-file changes, typos | Haiku |
| `ultrabrain` | Hard logic, architecture decisions | GPT-5.3 Codex |

### Ultrawork Mode

Single command `ultrawork` (or `ulw`) activates the full agent stack. The agent explores the codebase, researches patterns, implements the feature, verifies with diagnostics, and loops until done. Requires no configuration beyond installation.

### Ralph Loop / `/ulw-loop`

Self-referential execution loop that does not terminate until the task reaches 100% completion. Designed for long-running autonomous sessions.

### Tooling Integration

- **LSP**: `lsp_rename`, `lsp_goto_definition`, `lsp_find_references`, `lsp_diagnostics` — IDE-precision refactoring for agents
- **AST-Grep**: Pattern-aware code search and rewriting across 25 languages via `@ast-grep/napi`
- **Tmux**: Full interactive terminal with live REPL, debugger, and TUI session support
- **Built-in MCPs**: Exa (web search), Context7 (official docs), Grep.app (GitHub code search) — always on, no configuration

### Skill-Embedded MCPs

MCP servers are scoped to skills rather than globally loaded. Servers spin up on-demand for the relevant skill and terminate when done — keeping the context window clean.

### Security Hardening (v3.10.0)

- HTTP hooks validate URL schemes (`http:` and `https:` only) — prevents SSRF via `file://` or `data:` schemes
- `disabled_hooks` now applies to HTTP hooks, not just command hooks
- Message/part IDs include process-unique prefix (`msg_<hex>_<counter>`) — eliminates storage collisions across parallel sessions

### Claude Code Compatibility

All Claude Code hooks, commands, skills, MCPs, and plugins work without modification inside Oh My OpenCode.

---

## Technical Architecture

```text
User Request
    |
[Intent Gate] — classifies true intent before routing, prevents literal misinterpretation
    |
[Sisyphus] — main orchestrator
    |
    |-- [Prometheus] — strategic interview-mode planning (Tab key or @plan)
    |-- [Atlas] — todo orchestration and execution (/start-work)
    |-- [Oracle] — read-only architecture consultation
    |-- [Librarian] — documentation and OSS code search
    |-- [Explore] — fast codebase grep
    |-- [Category-based subagents] — model selected by task category, not model name
```

**Build system**: Bun (compile target), TypeScript source, distributed as standalone binaries (no Node/Bun runtime required post-install). Platform binaries published as separate optional npm packages (`oh-my-opencode-linux-x64`, `oh-my-opencode-darwin-arm64`, etc.).

**Key dependencies**:

- `@opencode-ai/plugin` — OpenCode plugin SDK
- `@opencode-ai/sdk` — OpenCode SDK
- `@ast-grep/napi` — AST-aware code search/rewrite
- `@modelcontextprotocol/sdk` — MCP server implementation
- `zod` — schema validation
- `vscode-jsonrpc` — LSP communication

**Configuration**: Provider subscriptions configured at install time via CLI flags (`--claude=max20`, `--openai=yes`, `--gemini=yes`, `--copilot=yes`, `--zai-coding-plan=yes`). Provider priority: Native (anthropic/, openai/, google/) > GitHub Copilot > OpenCode Zen > Z.ai Coding Plan.

---

## Installation & Usage

```bash
# Recommended — let an agent handle it
# Paste into Claude Code, AmpCode, or Cursor:
# "Install and configure oh-my-opencode by following the instructions here:
#  https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/refs/heads/dev/docs/guide/installation.md"

# Direct CLI install
bunx oh-my-opencode install
# or
npx oh-my-opencode install
```

```bash
# After installation — start a task
ultrawork       # full automatic: explore, implement, verify, loop until done
ulw             # alias for ultrawork

# Prometheus planning mode
# Press Tab in OpenCode session to enter interview mode
# Then:
/start-work     # Atlas executes the plan

# Deep worker
# Route to Hephaestus explicitly for GPT-5.3 Codex tasks
```

```bash
# Agent-assisted install (for LLM agents)
curl -fsSL https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/refs/heads/dev/docs/guide/installation.md
# Follow flags: --claude=<yes|no|max20> --openai=<yes|no> --gemini=<yes|no> --copilot=<yes|no>
```

---

## Relevance to Claude Code Development

### Applications

- **Direct analog**: Oh My OpenCode is a production-scale reference implementation of the agent orchestration patterns this repo implements as skills. Its architecture (Sisyphus/Atlas/Prometheus/Oracle) mirrors the skill system (orchestrator + specialist agents + planning agents + consultants).
- **Category routing pattern**: The `visual-engineering` / `ultrabrain` / `quick` / `deep` taxonomy is a concrete, field-tested approach to task routing without hardcoding model names. Applicable to the agent selection decision flows in this repo.
- **Skill-embedded MCPs**: The pattern of scoping MCP servers to skills rather than global context is directly relevant to skill design in this repo — reduces context bloat.
- **Intent Gate**: Pre-classification of user intent before routing is a pattern worth studying for improving the orchestrator's task dispatch logic.

### Patterns Worth Adopting

- **Discipline enforcement**: Todo Enforcer (detects idle agents and re-activates them) and the Ralph Loop (self-referential until 100% done) solve the agent-abandonment problem that affects long-running tasks.
- **Hash-anchored edits**: The `hashline_edit` tool's content-hash validation approach is a direct solution to stale-line errors in multi-file edits — a known problem in agent-based editing.
- **Accumulated learnings**: Subagents in Atlas receive conventions and lessons from prior tasks in the same session. This cross-task learning reduces repeated mistakes.
- **Comment Checker**: Automated enforcement of comment quality (no AI slop) is applicable to any agent that writes code with comments.
- **Prometheus interview mode**: Structured interview before implementation — identifying scope, ambiguities, and plan — is a direct pattern for the `/add-new-feature` skill's feature-researcher phase.

### Integration Opportunities

- **OpenCode plugin as distribution mechanism**: Oh My OpenCode ships as an `@opencode-ai/plugin`, a different distribution model from the Claude Code skills/plugins system. The two ecosystems target different base runtimes (OpenCode vs. Claude Code) but both support hooks, agents, and MCPs.
- **Cross-runtime compatibility**: Oh My OpenCode explicitly supports Claude Code hooks, commands, skills, and MCPs unchanged — enabling research into shared agent configuration formats.
- **Standalone binary distribution**: The Bun-compiled binary approach (no runtime required post-install, platform-specific optional npm packages) is a packaging model worth considering for CLI tools in this repo.

---

## References

- [GitHub Repository: code-yeongyu/oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) (accessed 2026-03-06)
- [GitHub API: repo metadata](https://api.github.com/repos/code-yeongyu/oh-my-opencode) (accessed 2026-03-06)
- [GitHub API: latest release v3.10.0](https://api.github.com/repos/code-yeongyu/oh-my-opencode/releases/latest) (accessed 2026-03-06)
- [Overview Guide (raw)](https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/refs/heads/dev/docs/guide/overview.md) (accessed 2026-03-06)
- [Installation Guide (raw)](https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/refs/heads/dev/docs/guide/installation.md) (accessed 2026-03-06)
- [npm package: oh-my-opencode](https://www.npmjs.com/package/oh-my-opencode) (accessed 2026-03-06)
- [Homepage: ohmyopencode.org](https://ohmyopencode.org) (not fetched — redirects to GitHub)
- [Exa web search: oh-my-opencode multi-model orchestration](https://exa.ai) (accessed 2026-03-06)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-06 |
| Version at Verification | v3.10.0 |
| Next Review Recommended | 2026-06-06 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | referenced by Claude Code Harness (agent-frameworks) |
