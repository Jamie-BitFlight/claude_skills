---
name: Claude Quickstarts
description: Claude Quickstarts is the official Anthropic repository of deployable reference applications built on the Claude API. Each project is a self-contained, runnable implementation demonstrating a...
license: MIT
metadata:
  topic: claude-quickstarts
  category: developer-tools
  source_url: https://github.com/anthropics/claude-quickstarts
  github: anthropics/claude-quickstarts
  version: "No releases; tracked via main branch commits"
  verified: "2026-02-19"
  next_review: "2026-08-19"
---

## Overview

Claude Quickstarts is the official Anthropic repository of deployable reference applications built on the Claude API. Each project is a self-contained, runnable implementation demonstrating a distinct Claude capability: computer use (desktop control via Docker), browser automation (Playwright integration), autonomous multi-session coding (Claude Agent SDK two-agent pattern), a customer support agent (Next.js + TypeScript UI), a financial data analyst (interactive Recharts visualization), and a minimal agent loop reference implementation (<300 lines of Python). All projects include setup instructions, tests, and CLAUDE.md development guides aimed at getting developers from zero to running application without reading API documentation first.

---

## Problem Addressed

| Problem                                                      | Solution                                                                                           |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Claude API onboarding requires reading extensive docs        | Self-contained runnable projects with step-by-step setup instructions                             |
| Computer use beta is complex to configure safely             | Docker container with VNC + Streamlit pre-configured; security cautions documented inline          |
| Autonomous multi-session agent patterns are non-obvious      | Two-agent pattern (initializer + coding agent) with git-persisted progress across sessions         |
| Building production UIs on Claude requires front-end setup   | Next.js + TypeScript + shadcn/ui starter projects for customer support and financial analyst demos |
| Agent loop fundamentals are obscured by SDK abstractions     | <300-line `agents/` reference showing raw tool loop with MCP server integration                    |
| Browser automation with Claude has no canonical example      | Full Playwright + Claude Browser Tools API demo with Docker and pytest suite                       |

---

## Key Statistics

| Metric             | Value                       | Date Gathered |
| ------------------ | --------------------------- | ------------- |
| GitHub Stars       | 14,681                      | 2026-02-19    |
| GitHub Forks       | 2,446                       | 2026-02-19    |
| Open Issues        | 143                         | 2026-02-19    |
| Contributors       | ~28 (via Link header)       | 2026-02-19    |
| Primary Language   | Python (368KB), TypeScript (174KB) | 2026-02-19 |
| Repository Age     | Since 2024-08-29            | 2026-02-19    |
| Latest Release     | None (no versioned releases) | 2026-02-19   |
| Supported Models   | Claude Opus 4.5, Sonnet 4.5, Sonnet 4, Opus 4, Haiku 4.5, Sonnet 3.7, Sonnet 3.5 | 2026-02-19 |

---

## Key Features

### Included Quickstart Projects

**Computer Use Demo** (`computer-use-demo/`)

- Docker container with full Linux desktop (VNC + noVNC + Streamlit interface)
- Exposes ports 5900 (VNC), 8501 (Streamlit), 6080 (noVNC), 8080 (web)
- Supports Anthropic API, AWS Bedrock, and Google Vertex backends
- Uses `computer_use_20251124` tool version with zoom actions
- Uses `str_replace_based_edit_tool` (replaces deprecated `str_replace_editor`)
- Supports Claude 4 models (Opus 4.5, Sonnet 4.5, Sonnet 4, Opus 4, Haiku 4.5)
- Pre-built Docker image: `ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest`

**Browser Tools API Demo** (`browser-use-demo/`)

- Playwright integration for web navigation, DOM inspection, form manipulation
- Docker + docker-compose deployment
- pytest suite with `browser_use_demo/` package structure
- CHANGELOG.md and NOTICE file indicating third-party attribution requirements

**Autonomous Coding Agent** (`autonomous-coding/`)

- Two-agent pattern: initializer agent (session 1) + coding agent (sessions 2+)
- Requires Claude Code CLI (`npm install -g @anthropic-ai/claude-code`) and `claude-code-sdk` Python package
- Progress persisted via `feature_list.json` (200 test cases) and git commits across sessions
- Defense-in-depth security: OS sandbox + filesystem restriction to project dir + bash command allowlist
- Allowed commands: `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `npm`, `node`, `git`, `ps`, `lsof`, `sleep`, `pkill`
- Configurable via `--project-dir`, `--max-iterations`, `--model` CLI flags

**Agents Reference Implementation** (`agents/`)

- <300 lines of Python demonstrating agent loop fundamentals
- `agent.py` handles Claude API interactions and tool execution loop
- Supports both local tool classes and MCP server connections (stdio and other transports)
- `tools/` directory with `ThinkTool` and MCP tool wrappers; `utils/` for message history + MCP connections
- Includes Jupyter notebook `agent_demo.ipynb` for interactive exploration
- Explicitly not a production SDK — educational reference only

**Customer Support Agent** (`customer-support-agent/`)

- Next.js application with TypeScript strict mode
- shadcn/ui component library; Tailwind CSS
- Three layout variants: left sidebar, right sidebar, chat-only (via `npm run dev:left/right/chat`)
- AWS Amplify deployment config (`amplify.yml`)

**Financial Data Analyst** (`financial-data-analyst/`)

- Next.js + TypeScript with Recharts visualization
- Interactive financial data analysis via chat interface
- React hooks for state management

### Development Infrastructure

- Monorepo with `pyproject.toml` and `.pre-commit-config.yaml` at root
- Python projects: ruff (lint + format) + pyright type checking + pytest
- TypeScript projects: ESLint Next.js configuration
- `CLAUDE.md` at repo root documents all build commands for Claude Code context

---

## Technical Architecture

### Repository Structure

<eg>
claude-quickstarts/
├── CLAUDE.md                    # Claude Code dev guide (build cmds, code style per project)
├── pyproject.toml               # Root Python config
├── .pre-commit-config.yaml      # Repo-wide pre-commit hooks
├── agents/                      # Minimal agent loop reference (<300 lines Python)
│   ├── agent.py                 # Core API + tool loop
│   ├── tools/                   # ThinkTool + MCP tool wrappers
│   └── utils/                   # Message history, MCP connections
├── autonomous-coding/           # Multi-session coding agent (Claude Agent SDK)
│   ├── autonomous_agent_demo.py # CLI entry point
│   ├── agent.py                 # Session logic
│   ├── client.py                # SDK client config
│   ├── security.py              # Bash allowlist + OS sandbox
│   ├── prompts/                 # initializer_prompt.md, coding_prompt.md, app_spec.txt
│   └── progress.py              # Session tracking
├── browser-use-demo/            # Playwright + Claude Browser Tools API (Docker)
├── computer-use-demo/           # Desktop control (Docker + VNC + Streamlit)
│   ├── computer_use_demo/       # Python agent loop
│   └── Dockerfile               # Full Linux desktop image
├── customer-support-agent/      # Next.js + shadcn/ui + Amplify
└── financial-data-analyst/      # Next.js + Recharts
</eg>

### Agent Loop Pattern (from `agents/agent.py`)

<eg>
User message
    → Claude API call (with tools + MCP tool list)
    → Response: text block OR tool_use block
    → If tool_use: execute locally or via MCP server
    → Append tool_result to message history
    → Loop until no more tool_use blocks
    → Return final text response
</eg>

### Autonomous Coding Two-Agent Pattern

<eg>
Session 1 (Initializer):
    app_spec.txt → generate feature_list.json (200 test cases) → git init → project scaffold

Sessions 2+ (Coding Agent):
    Read feature_list.json → pick next incomplete feature → implement → run tests → mark passing → git commit
    (Each session: fresh context window; progress via feature_list.json + git history)
</eg>

### Computer Use Tool Version

<eg>
Beta tool: computer_use_20251124
Actions: screenshot, click, type, scroll, key, zoom (new in 20251124)
Editor: str_replace_based_edit_tool (replaces str_replace_editor)
Ports: 5900/VNC, 8501/Streamlit, 6080/noVNC, 8080/web
</eg>

---

## Installation and Usage

### Computer Use Demo (quickest start)

```bash
export ANTHROPIC_API_KEY=your_api_key
docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 -p 8501:8501 -p 6080:6080 -p 8080:8080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
# Then open http://localhost:8080
```

### Agents Reference (Python)

```bash
git clone https://github.com/anthropics/claude-quickstarts.git
cd claude-quickstarts
pip install anthropic mcp
python -c "
from agents.agent import Agent
from agents.tools.think import ThinkTool
agent = Agent(name='demo', system='You are helpful.', tools=[ThinkTool()])
print(agent.run('What are 3 key benefits of async I/O?'))
"
```

### Autonomous Coding Agent

```bash
cd autonomous-coding
npm install -g @anthropic-ai/claude-code
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key
python autonomous_agent_demo.py --project-dir ./my_project --max-iterations 5
```

### Customer Support Agent (Next.js)

```bash
cd customer-support-agent
npm install
npm run dev           # full UI at localhost:3000
npm run dev:chat      # chat-only variant
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **CLAUDE.md Pattern**: The repo-root `CLAUDE.md` documents build commands and code style conventions for each sub-project — a direct reference for how Anthropic structures CLAUDE.md for multi-language monorepos. The format is per-project headings with Setup, Testing, and Code Style subsections.

2. **Agent SDK Integration**: The `autonomous-coding/` project demonstrates the `claude-code-sdk` Python package integration pattern — specifically how to spawn Claude Code sessions programmatically, manage context windows across sessions, and persist state via file + git. Directly applicable to Claude Code skill orchestration patterns.

3. **Two-Agent Orchestration**: The initializer + coding agent split (session 1 generates plan; sessions 2+ execute) is a concrete multi-session orchestration pattern applicable to claude_skills multi-agent workflows.

4. **Security Hook Pattern**: `security.py` shows how to implement a bash command allowlist as a pre-execution hook — directly analogous to Claude Code `PreToolUse` hooks for constraining tool execution scope.

5. **MCP Integration Reference**: `agents/` shows how to connect both local tools and MCP servers in a single agent loop — relevant to the `mcp-ecosystem` research category and claude_skills MCP plugin development.

6. **Computer Use Tool Version**: Documents the `computer_use_20251124` tool API with zoom support and `str_replace_based_edit_tool` — authoritative reference for current beta computer use tool versions.

### Patterns Worth Examining

1. **Feature list as session handoff**: `feature_list.json` as the durable cross-session progress tracker (rather than a database or external state store) is a simple, git-trackable pattern for long-running agent workflows.

2. **Per-project CLAUDE.md in monorepo**: Project-level build command docs in a single shared CLAUDE.md at monorepo root — provides all tool context without per-directory CLAUDE.md proliferation.

3. **Layout variants via npm scripts**: `npm run dev:left/right/chat` for shipping multiple UI configurations from one codebase — relevant when building multi-surface Claude Code skill UIs.

4. **Docker as isolation boundary for computer use**: Using Docker to scope filesystem access and network exposure for computer use agents — a security pattern for any Claude Code plugin that invokes desktop tools.

---

## References

| Source                     | URL                                                                              | Accessed   |
| -------------------------- | -------------------------------------------------------------------------------- | ---------- |
| GitHub Repository          | <https://github.com/anthropics/claude-quickstarts>                               | 2026-02-19 |
| README.md                  | <https://github.com/anthropics/claude-quickstarts/blob/main/README.md>           | 2026-02-19 |
| CLAUDE.md                  | <https://github.com/anthropics/claude-quickstarts/blob/main/CLAUDE.md>           | 2026-02-19 |
| agents/README.md           | <https://github.com/anthropics/claude-quickstarts/blob/main/agents/README.md>    | 2026-02-19 |
| autonomous-coding/README.md | <https://github.com/anthropics/claude-quickstarts/blob/main/autonomous-coding/README.md> | 2026-02-19 |
| computer-use-demo/README.md | <https://github.com/anthropics/claude-quickstarts/blob/main/computer-use-demo/README.md> | 2026-02-19 |
| GitHub API (repo meta)     | `gh api repos/anthropics/claude-quickstarts`                                    | 2026-02-19 |
| GitHub API (languages)     | `gh api repos/anthropics/claude-quickstarts/languages`                          | 2026-02-19 |
| GitHub API (contributors)  | `gh api repos/anthropics/claude-quickstarts/contributors?per_page=1&anon=true`  | 2026-02-19 |

**Research Method**: GitHub API for repository metadata, language breakdown, and contributor count (Link header pagination). README and sub-project READMEs decoded from base64 GitHub contents API. CLAUDE.md read for development patterns.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [gstack](../agent-frameworks/gstack.md) | agent-frameworks | referenced by gstack (agent-frameworks) |
| [vibium](../agent-infrastructure/vibium.md) | agent-infrastructure | referenced by vibium (agent-infrastructure) |
| [anything_about_game_ai_resources](./anything_about_game_ai_resources.md) | developer-tools | referenced by anything_about_game_ai_resources (developer-tools) |
| [pyscript](./pyscript.md) | developer-tools | referenced by pyscript (developer-tools) |
| [scrapling-skill](./scrapling-skill.md) | developer-tools | referenced by scrapling-skill (developer-tools) |
