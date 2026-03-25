<p align="center">
  <a href="#available-plugins"><img src="https://img.shields.io/badge/Claude_Code-Plugin_Marketplace-6B4FBB?style=for-the-badge&logo=anthropic&logoColor=white" alt="Claude Code Plugin Marketplace"></a>
  <a href="#full-featured-development-systems"><img src="https://img.shields.io/badge/Plugins-27-blue?style=for-the-badge" alt="27 Plugins"></a>
  <a href="#full-featured-development-systems"><img src="https://img.shields.io/badge/Agents-56-orange?style=for-the-badge" alt="56 Agents"></a>
  <a href="#full-featured-development-systems"><img src="https://img.shields.io/badge/Skills-119-green?style=for-the-badge" alt="119 Skills"></a>
</p>

<p align="center">
  <a href="https://github.com/Jamie-BitFlight/claude_skills/stargazers"><img src="https://img.shields.io/github/stars/Jamie-BitFlight/claude_skills?style=flat-square&logo=github" alt="GitHub stars"></a>
  <a href="https://github.com/Jamie-BitFlight/claude_skills/commits/main"><img src="https://img.shields.io/github/last-commit/Jamie-BitFlight/claude_skills?style=flat-square" alt="GitHub last commit"></a>
  <a href="https://github.com/Jamie-BitFlight/claude_skills/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Jamie-BitFlight/claude_skills?style=flat-square" alt="License"></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/uv-package_manager-DE5FE9?style=flat-square&logo=uv&logoColor=white" alt="uv"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-enabled-6B4FBB?style=flat-square" alt="MCP enabled"></a>
  <a href="https://www.conventionalcommits.org/"><img src="https://img.shields.io/badge/Conventional_Commits-1.0.0-FE5196?style=flat-square&logo=conventionalcommits&logoColor=white" alt="Conventional Commits"></a>
</p>

<p align="center">
  <a href="https://github.com/bitflight-devops/skilllint"><img src="https://img.shields.io/badge/Plugins_validated_with-skilllint-22C55E?style=for-the-badge&logo=python&logoColor=white" alt="Plugins validated with skilllint"></a>
  <a href="https://pypi.org/project/skilllint/"><img src="https://img.shields.io/pypi/v/skilllint?style=for-the-badge&label=skilllint&color=3775A9&logo=pypi&logoColor=white" alt="skilllint on PyPI"></a>
</p>

# Claude Skills Collection

> AI reflects what's expressed, not what's true.

Professional development workflow extensions for Claude Code. Make Claude more thorough, accurate, and productive across Python, shell, Perl, CI/CD, and AI tooling.

## What Problem Does This Solve?

| Without plugins | With plugins |
| --- | --- |
| Claude gives generic Python advice | Claude applies Python 3.11+, Typer, Rich, httpx conventions specific to your stack |
| Claude says "done" before linters pass | holistic-linting enforces root-cause fixes before any task completes |
| Claude speculates and hallucinates | hallucination-detector blocks completion on ungrounded claims |
| Claude jumps to solutions without investigating | verification-gate forces evidence gathering before action |
| Session transcripts disappear with no learning | agentskill-kaizen mines transcripts for anti-patterns and generates skill patches |
| Commit messages are inconsistent | conventional-commits enforces feat/fix/chore format for semantic versioning |
| Claude reads source files when it should delegate | orchestrator-discipline hooks block investigation escalation at the tool level |

## Quick Start

```bash
# Add the marketplace (one-time setup)
/plugin marketplace add Jamie-BitFlight/claude_skills

# Install a plugin
/plugin install plugin-name@jamie-bitflight-skills
```

### Verify Installation

Start a new session and ask Claude to perform a task the plugin handles (for example, write a Python function after installing `python3-development`). Claude should automatically apply the plugin's conventions rather than generic defaults.

## Available Plugins

### Full-Featured Development Systems

Comprehensive frameworks with multiple skills, commands, and specialized agents.

| Plugin | What It Does |
| --- | --- |
| [development-harness](./plugins/development-harness) | Language-agnostic SAM 7-stage pipeline (Discovery → Planning → Context → Decomposition → Execution → Review → Verification) with backlog management, milestone dispatch, and kage-bunshin parallel sessions. 31 skills, 15 agents, MCP backlog server. |
| [python3-development](./plugins/python3-development) | Python 3.11+ specialist with 35 skills, 5 agents, and TDD workflows. Covers Typer/Rich CLI development, pytest test suites, code review, type checking, and PEP 723 inline script metadata. MCP semantic code search included. |
| [bash-development](./plugins/bash-development) | Write robust Bash 5.1+ scripts with modern patterns, error handling, POSIX portability, and specialized agents for development and auditing |
| [perl-development](./plugins/perl-development) | Build production-quality Perl 5.30+ scripts with modern practices, CPAN ecosystem integration, comprehensive testing, and CLI architecture |
| [plugin-creator](./plugins/plugin-creator) | Complete toolkit for creating, refactoring, and validating Claude Code plugins with 36 skills, 8 specialized agents, automated version bumping, and `skilllint` integration |
| [uv](./plugins/uv) | Expert guidance for Astral's uv — the fast Python package manager that replaces pip, poetry, pyenv, and virtualenv with modern lockfiles |
| [clang-format](./plugins/clang-format) | Configure clang-format to match your existing C/C++ code style by analyzing patterns and showing impact before changes (install name: `clang-format-configuration`) |
| [holistic-linting](./plugins/holistic-linting) | Automatic code quality enforcement — Claude won't say "done" until code passes all configured linters with root-cause fixing. Covers ruff, mypy, and bandit. |
| [summarizer](./plugins/summarizer) | Faithful information summarization with anti-hallucination methodology, structured output templates, and autonomous agents for file, URL, and image summarization |
| [agentskill-kaizen](./plugins/agentskill-kaizen) | Analyze Claude Code session transcripts to find inefficiencies, anti-patterns, and repeated mistakes with DuckDB process-mining and live sentiment dashboard. Two MCP servers included. |
| [dasel](./plugins/dasel) | Query, transform, and convert structured data files (JSON, YAML, TOML, XML, CSV, HCL, INI) using dasel v3 with exploration agents |
| [the-rewrite-room](./plugins/the-rewrite-room) | Documentation workflow router — routes tasks like drift audits, doc sync, prompt optimization, and summarization to canonical workflows with validation (install name: `rwr`). Includes MCP file-reader server. |
| [process-siren](./plugins/process-siren) | Converts bullet steps, ASCII art, markdown tables, and prose workflows into Mermaid diagrams for AI-facing documents, with process quality methodology for improving ambiguous or incomplete processes before conversion |
| [fastmcp-creator](./plugins/fastmcp-creator) | Build production-ready MCP servers with FastMCP 3.x — covers provider/transform architecture, authorization, session state, async patterns, STDIO/HTTP transports, and deployment. Includes a live FastMCP reference MCP server. |
| [dot-dash](./plugins/dot-dash) | Real-time browser dashboard for monitoring every active Claude Code session — live transcript streaming, prompt injection, and session termination from a single React UI. Node.js/Hono backend with WebSocket updates and token-based authentication. |

### Lightweight Knowledge Clip-Ins

Focused plugins that teach Claude specific conventions or tools without heavy workflows.

#### Python and Package Management

| Plugin | What It Does |
| --- | --- |
| [litellm](./plugins/litellm) | Call any LLM API (OpenAI/Anthropic/local) from Python with unified interface and retry logic |
| [llamafile](./plugins/llamafile) | Run local GGUF models with OpenAI-compatible API for offline/air-gapped inference |
| [xdg-base-directory](./plugins/xdg-base-directory) | Store config and data files in correct XDG-compliant directories using platformdirs |

#### Git and CI/CD

| Plugin | What It Does |
| --- | --- |
| [conventional-commits](./plugins/conventional-commits) | Write consistent commit messages (feat/fix/chore) for semantic versioning and changelog generation |
| [commitlint](./plugins/commitlint) | Configure and validate commit messages against commitlint rules for CI/CD enforcement |
| [gitlab-skill](./plugins/gitlab-skill) | Write GitLab CI pipelines and GLFM documentation with local testing via gitlab-ci-local before pushing |

#### Better Claude Behavior

| Plugin | What It Does |
| --- | --- |
| [agent-orchestration](./plugins/agent-orchestration) | Structures delegation prompts with world-building context (WHERE, WHAT, WHY) while preserving agent autonomy on implementation decisions |
| [verification-gate](./plugins/verification-gate) | Forces Claude to verify its hypothesis matches its target before executing writes or edits — blocks correct diagnoses from producing wrong implementations |
| [hallucination-detector](https://github.com/bitflight-devops/hallucination-detector) | Blocks task completion when Claude speculates or makes ungrounded claims, forcing evidence-first rewrites |
| [scientific-method](./plugins/scientific-method) | Structures hypothesis-driven debugging and investigation with experiment protocols and evidence-first methodology |
| [brainstorming-skill](./plugins/brainstorming-skill) | Significantly improves brainstorming with 30+ research-validated prompt patterns across 14 categories |
| [orchestrator-discipline](./plugins/orchestrator-discipline) | Enforces context window discipline via PreToolUse hooks — blocks source-file reads without edits and blocks diagnostic commands that should be delegated to agents |

#### Architecture

| Plugin | What It Does |
| --- | --- |
| [twelve-factor-app](./plugins/twelve-factor-app) | Apply twelve-factor app methodology (15 principles including 3 modern extensions) to your projects for portable, scalable, cloud-native architecture (not yet in marketplace — use `--plugin-dir ./plugins/twelve-factor-app` for local use) |

## Plugin Details

### development-harness

The SAM (Stateless Agent Methodology) pipeline in a single plugin. Every feature request moves through seven stages that each produce a file artifact: Discovery, Planning (with RT-ICA information completeness analysis), Context Integration, Task Decomposition, Execution, Forensic Review, and Final Verification.

Language plugins (like `python3-development`) compose with the harness by providing a manifest that maps abstract roles to concrete agents. Without a language plugin, the harness falls back to general-purpose agents.

**Skills include:** `/dh:add-new-feature`, `/dh:implement-feature`, `/dh:complete-implementation`, `/dh:groom-milestone`, `/dh:work-milestone`, `/dh:dispatch`, `/dh:backlog`, and 24 more.

**Agents include:** `@dh:swarm-task-planner`, `@dh:feature-researcher`, `@dh:codebase-analyzer`, `@dh:feature-verifier`, `@dh:doc-drift-auditor`, and 10 more.

**MCP servers:** Backlog server (GitHub Issues sync, artifact management, dispatch orchestration), sequential-thinking server.

### python3-development

Python specialist that composes with `development-harness`. Install both for the full Python development pipeline.

**Skills include:** Python 3.11+ patterns, Typer/Rich CLI development, pytest workflows, type checking, linting resolution, PEP 723 inline script metadata, pyproject.toml configuration, and more.

**Agents include:**
- `@python3-development:python-cli-architect` — implements Python CLI features end-to-end
- `@python3-development:python-cli-design-spec` — produces architecture specs
- `@python3-development:python-pytest-architect` — writes pytest test suites
- `@python3-development:code-reviewer` — code review with Python idiom awareness
- `@python3-development:semantic-code-search` — semantic search over Python codebases

**MCP servers:** cocoindex-code semantic code search, sequential-thinking server.

### plugin-creator

Toolkit for building, refactoring, and validating plugins. Claude won't drift from current schema when creating agents or skills — the plugin loads the authoritative reference documentation automatically.

**Skills include:** `/plugin-creator:skill-creator`, `/plugin-creator:agent-creator`, `/plugin-creator:plugin-lifecycle`, `/plugin-creator:refactor-plugin`, `/plugin-creator:refactor-skill`, `/plugin-creator:claude-skills-overview-2026`, `/plugin-creator:claude-plugins-reference-2026`, `/plugin-creator:hooks-guide`, and more.

**Agents include:** `refactor-planner`, `refactor-executor`, `refactor-validator`, `subagent-refactorer` (applies Anthropic prompt engineering best practices), `contextual-ai-documentation-optimizer`, `plugin-assessor`.

**Scripts include:** `create_plugin.py` (interactive scaffolding), `auto_sync_manifests.py` (pre-commit hook that bumps versions and syncs component arrays automatically).

**Validation:** Integrates with `skilllint` (`uvx skilllint@latest check <path>`) for frontmatter validation, skill complexity checking, and auto-fix of common errors.

### orchestrator-discipline

Installs three PreToolUse hooks that run before every Read, Grep, and Bash call:

- **Read/Grep hook** — warns when Claude reads a source file it is not about to edit, prompting delegation instead
- **Diagnostic command gate** — blocks linter/type-checker/test commands from running directly in the orchestrator context window
- **Bash misuse prevention** — catches other patterns where the orchestrator should delegate rather than act

These hooks structurally prevent the investigation escalation anti-pattern: the progressive cycle of reading files that justifies reading more files until Claude implements the task itself instead of delegating.

### agentskill-kaizen

Two MCP servers surface transcript analysis directly in your session:

- **kaizen-duckdb** — DuckDB read-only access to the session transcript database for SQL-based process mining
- **kaizen-analysis** — analysis server for anti-pattern detection, sentiment signals, and improvement recommendations

Run after sessions to identify what went wrong, what tooling Claude was missing, and where repeated mistakes occurred.

### fastmcp-creator

Covers the full FastMCP 3.x development surface: provider/transform architecture (CodeMode, Tool Search, server-level transforms), component versioning, session state, MultiAuth authorization, PropelAuth integration, Pydantic validation, async patterns, STDIO/HTTP transports, nginx reverse proxy deployment, background tasks, Prefab Apps UI, security patterns, client SDK usage, testing, and migration from FastMCP v2.

Includes a live FastMCP reference MCP server that provides `search_docs`, `scaffold_server`, `validate_server`, and `version_check` tools.

### dot-dash

A browser-based control panel for Claude Code. When you are running multiple sessions simultaneously — across projects, worktrees, or machines — dot-dash gives you a single place to watch what each session is doing and to interact with it.

**What it does:**

- **Live transcript view** — streams JSONL transcript events from each session to the browser in real time via WebSocket, so you can read Claude's reasoning and tool calls as they happen
- **Session list** — shows all active and recently stopped sessions with project name, working directory, PID, and last-event timestamp
- **Prompt injection** — lets you queue a message in the browser that will be prepended to the next prompt the user submits in a specific session, without interrupting the current turn
- **Session termination** — send a stop signal to any session from the dashboard

**How it works:**

Three hooks wire each Claude Code session into the server automatically:

- `SessionStart` — registers the session (ID, CWD, PID) with the local server
- `SessionEnd` — marks the session stopped and cleans up
- `UserPromptSubmit` — checks the injection queue before every prompt; if a message is queued, prepends it transparently

The server runs locally at `http://127.0.0.1:7765` by default. A React/TypeScript frontend (built with Vite) is served from the same process. Authentication uses a token stored at `~/.claude/dot-dash/token` (generated on first run, file-permissions 600).

**Starting the server:**

```bash
cd plugins/dot-dash/server
npm install
npm run build
node dist/main.js
```

Or use the bundled script:

```bash
bash plugins/dot-dash/scripts/start-server.sh
```

Then open `http://127.0.0.1:7765` in a browser. The server must be running before Claude Code sessions start for those sessions to appear in the dashboard.

**Configuration:**

Set `DOT_DASH_PORT` in your environment to use a port other than `7765`:

```bash
DOT_DASH_PORT=8080 node dist/main.js
```

## How Plugins Work

Plugins contain:

- **Skills** — Knowledge and workflows that guide Claude's behavior
- **Commands** — Slash commands you can invoke directly (like `/dh:add-new-feature`)
- **Agents** — Specialized sub-agents for complex tasks (like code review or architecture design)
- **Hooks** — Automation that runs at specific lifecycle events
- **MCP Servers** — Additional tools Claude can call (backlog management, code search, file reading, etc.)

Once installed, plugins work automatically. Claude knows when to apply them based on your project context.

## Plugin Structure

```text
plugins/plugin-name/
├── .claude-plugin/
│   └── plugin.json       # Plugin manifest
├── skills/               # What Claude learns
├── commands/             # Slash commands you can use
├── agents/               # Specialized sub-agents
├── hooks/                # hooks.json and hook scripts
└── README.md             # Documentation
```

## Local Development

```bash
# Option 1: Load specific plugins for this session
claude --plugin-dir ./plugins/python3-development --plugin-dir ./plugins/holistic-linting

# Option 2: Add local marketplace for persistent enable/disable
/plugin marketplace add ./.claude-plugin/marketplace.json

# Install plugins you need (--scope local keeps it gitignored)
/plugin install python3-development@jamie-bitflight-skills --scope local

# Disable when not needed
/plugin disable python3-development@jamie-bitflight-skills

# Re-enable when needed
/plugin enable python3-development@jamie-bitflight-skills
```

## Troubleshooting

**Plugin commands not found after install?**

Restart Claude Code to reload commands. Verify the plugin installed:

```bash
/plugin list
```

**Plugin not influencing Claude's behavior?**

Check that the plugin is enabled and not scoped to a different project:

```bash
/plugin list --all
```

**Want to test a plugin before committing to it?**

Use `--scope local` when installing. This keeps the plugin active only in your current project and gitignored.

**Something broken after an update?**

Reinstall the specific plugin:

```bash
/plugin install plugin-name@jamie-bitflight-skills
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines on adding, removing, or updating plugins.

Quick overview:

1. Fork the repository
2. Create your plugin using `/plugin-creator` or manually
3. Update `.claude-plugin/marketplace.json`
4. Validate with `uvx skilllint@latest check` and `claude plugin validate`
5. Test locally before submitting PR
6. Submit pull request with description

## Requirements

- Claude Code v2.0 or later
- Individual plugins may have additional requirements (see plugin READMEs)

## License

MIT License — see individual plugins for specifics.
