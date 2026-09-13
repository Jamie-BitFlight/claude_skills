---
name: pi-mono - AI Agent Toolkit and Coding Agent CLI
description: A TypeScript monorepo providing a minimal, extensible coding agent CLI, unified multi-provider LLM API, TUI and web UI libraries, Slack bot, and vLLM pod management. Designed for workflow adaptability via extensions, skills, and prompt templates rather than opinionated built-in features.
license: MIT
metadata:
  topic: pi-mono
  category: coding-agents
  source_url: https://github.com/badlogic/pi-mono
  github: badlogic/pi-mono
  version: "v0.55.1"
  verified: "2026-02-26"
  next_review: "2026-05-26"
---

## Overview

pi-mono is an open-source TypeScript monorepo maintained by Mario Zechner (badlogic) that packages a suite of AI agent tools including an interactive coding agent CLI (`pi`), a unified multi-provider LLM API library, a terminal UI library with differential rendering, web UI components for AI chat, a Slack bot, and a CLI for managing vLLM deployments on GPU pods. The coding agent `pi` emphasizes minimalism and extensibility: it ships with four default tools (read, write, edit, bash) and allows users to extend behavior via TypeScript Extensions, Skills (following the Agent Skills standard), Prompt Templates, and Themes packaged in shareable npm/git Pi Packages. The project reached 16,621 GitHub stars and 1,745 forks within approximately 6 months of creation (August 2025 to February 2026), indicating rapid adoption.

SOURCE: [GitHub repository](https://github.com/badlogic/pi-mono) (accessed 2026-02-26)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Existing coding agents are opinionated and require forking to adapt to custom workflows | pi ships minimal defaults; users extend via TypeScript Extensions and Skills without modifying core |
| Switching between LLM providers requires different API clients and authentication patterns | `@mariozechner/pi-ai` provides a unified multi-provider API covering 20+ providers via subscription or API key |
| Long-running agent sessions exhaust context windows and require manual management | Automatic and manual session compaction with full JSONL history preserved; `/tree` for non-destructive branching |
| Integrating a coding agent into existing apps (RPC, embedded SDK) requires re-architecture | pi runs in four modes: interactive TUI, print/JSON, RPC for process integration, and SDK for embedding |
| Managing vLLM deployments across GPU pods is operationally complex | `@mariozechner/pi-pods` CLI manages vLLM pod lifecycle independently |
| Sharing custom agent behaviors with teams requires custom tooling or forks | Pi Packages (npm or git) bundle Extensions, Skills, Prompt Templates, and Themes for distribution |

SOURCE: [coding-agent README](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (accessed 2026-02-26)

---

## Key Statistics (as of February 26, 2026)

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 16,621 | 2026-02-26 |
| Forks | 1,745 | 2026-02-26 |
| Open Issues | 8 | 2026-02-26 |
| Contributors | 122 | 2026-02-26 |
| Latest Release | v0.55.1 | 2026-02-26 |
| Repository Created | 2025-08-09 | 2026-02-26 |
| Primary Language | TypeScript (97.8%) | 2026-02-26 |
| License | MIT | 2026-02-26 |

SOURCE: [GitHub API](https://api.github.com/repos/badlogic/pi-mono) (accessed 2026-02-26)

---

## Key Features

### Coding Agent CLI (`@mariozechner/pi-coding-agent`)

- Interactive terminal mode with differential TUI rendering, fuzzy file search via `@` references, image paste via Ctrl+V, and inline bash execution via `!command`
- Session management stored as JSONL with tree structure supporting in-place branching; `/tree` navigates and continues from any prior point without file duplication
- Automatic and manual context compaction; configurable proactive compaction when approaching context limit
- Four run modes: interactive TUI, print/JSON (for scripting), RPC (for process integration), SDK (for embedding in apps)
- Message queue: steering messages interrupt current tool execution; follow-up messages queue until agent finishes
- Session export to HTML and shareable GitHub gist via `/share`

### Multi-Provider LLM Support (`@mariozechner/pi-ai`)

- Subscription providers: Anthropic Claude Pro/Max, OpenAI ChatGPT Plus/Pro (Codex), GitHub Copilot, Google Gemini CLI, Google Antigravity
- API key providers: Anthropic, OpenAI, Azure OpenAI, Google Gemini, Google Vertex, Amazon Bedrock, Mistral, Groq, Cerebras, xAI, OpenRouter, Vercel AI Gateway, ZAI, OpenCode Zen, Hugging Face, Kimi For Coding, MiniMax
- Custom providers via `~/.pi/agent/models.json` for any OpenAI/Anthropic/Google-compatible API
- Auth file (`~/.pi/agent/auth.json`) with `0600` permissions; key value supports shell command execution (`!command`) for secrets managers (e.g., 1Password CLI, macOS Keychain)

### Extensibility System

- **Extensions**: TypeScript modules loaded at startup from `~/.pi/agent/extensions/` or `.pi/extensions/`; subscribe to lifecycle events (`session_start`, `tool_call`, `agent_turn_start`, etc.), register custom tools via `pi.registerTool()`, add commands via `pi.registerCommand()`, inject custom TUI components via `ctx.ui.custom()`
- **Skills**: On-demand capability packages following the [Agent Skills standard](https://agentskills.io); invoked via `/skill:name` or auto-loaded; placed in `~/.pi/agent/skills/`, `~/.agents/skills/`, or `.pi/skills/`
- **Prompt Templates**: Markdown files with `{{variable}}` substitution; expanded via `/templatename` in the editor
- **Themes**: Hot-reloaded at runtime without restart
- **Pi Packages**: npm or git packages bundling Extensions, Skills, Prompt Templates, and Themes for sharing

### Terminal UI Library (`@mariozechner/pi-tui`)

- Differential rendering for terminal UIs (only re-renders changed portions)
- Supports custom UI components with full keyboard input handling
- Used by the coding agent for all TUI interactions; available as standalone library

### Additional Packages

- **`@mariozechner/pi-agent-core`**: Agent runtime with tool calling and state management; core building block for the coding agent
- **`@mariozechner/pi-mom`**: Slack bot that delegates incoming messages to the pi coding agent
- **`@mariozechner/pi-web-ui`**: Web components for AI chat interfaces
- **`@mariozechner/pi-pods`**: CLI for provisioning and managing vLLM deployments on GPU pods

SOURCE: [coding-agent README](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (accessed 2026-02-26), [providers docs](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/providers.md) (accessed 2026-02-26), [extensions docs](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md) (accessed 2026-02-26)

---

## Technical Architecture

<eg>
pi-mono (TypeScript monorepo, npm workspaces)
├── packages/
│   ├── ai/              @mariozechner/pi-ai
│   │   └── Unified LLM API: 20+ providers, OAuth + API key auth,
│   │       env-api-keys.ts maps providers to env vars
│   │
│   ├── agent/           @mariozechner/pi-agent-core
│   │   └── Agent runtime: tool calling loop, state management,
│   │       context compaction logic
│   │
│   ├── coding-agent/    @mariozechner/pi-coding-agent
│   │   ├── Interactive TUI (uses pi-tui), 4 default tools:
│   │   │   read, write, edit, bash
│   │   ├── Session engine: JSONL tree format, branching/forking
│   │   ├── Extension loader: ~/.pi/agent/extensions/, .pi/extensions/
│   │   ├── Skills loader: agent skills standard, /skill:name dispatch
│   │   ├── Context files: AGENTS.md / CLAUDE.md (walks parent dirs)
│   │   └── Run modes: interactive | print/JSON | RPC | SDK
│   │
│   ├── tui/             @mariozechner/pi-tui
│   │   └── Differential TUI rendering, custom component API
│   │
│   ├── web-ui/          @mariozechner/pi-web-ui
│   │   └── Web components for AI chat interfaces
│   │
│   ├── mom/             @mariozechner/pi-mom
│   │   └── Slack bot -> pi agent delegation
│   │
│   └── pods/            @mariozechner/pi-pods
│       └── vLLM pod lifecycle management CLI
│
├── Build: npm workspaces, TypeScript, Biome (lint/format)
├── CI: GitHub Actions (.github/workflows/ci.yml)
└── Releases: GitHub Actions bot, binaries for
    darwin-arm64, darwin-x64, linux-arm64, linux-x64, windows-x64
</eg>

The coding agent reads `AGENTS.md` (or `CLAUDE.md`) from the global `~/.pi/agent/AGENTS.md`, parent directories of cwd, and current directory — the same context-file convention used by Claude Code. Settings cascade from global (`~/.pi/agent/settings.json`) to project (`.pi/settings.json`).

SOURCE: [GitHub repository structure](https://github.com/badlogic/pi-mono/blob/main/README.md) (accessed 2026-02-26)

---

## Installation & Usage

### Install the coding agent CLI

```bash
npm install -g @mariozechner/pi-coding-agent
```

### Authenticate and run

```bash
# Via API key
export ANTHROPIC_API_KEY=sk-ant-...
pi

# Via subscription (OAuth)
pi
# Then type: /login
# Select provider (Claude Pro/Max, ChatGPT Plus, GitHub Copilot, etc.)
```

### Offline / restricted environments

```bash
# Disable startup network operations
pi --offline
# or: export PI_OFFLINE=1
```

### Common session commands

<eg>
/model          - Switch models (or Ctrl+L)
/resume         - Browse and continue past sessions
/tree           - Navigate session tree, continue from any point
/compact        - Manually compact context
/share          - Upload session as shareable GitHub gist HTML
/skill:name     - Invoke an installed skill
/settings       - TUI settings panel (thinking level, theme, etc.)
</eg>

### Write a TypeScript Extension

```typescript
// ~/.pi/agent/extensions/confirm-dangerous.ts
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash" && event.input.command?.includes("rm -rf")) {
      const ok = await ctx.ui.confirm("Dangerous command", "Allow rm -rf?");
      if (!ok) return { block: true, reason: "Blocked by user" };
    }
  });
}
```

### Use as an SDK (embed in another app)

```typescript
import { createAgent } from "@mariozechner/pi-coding-agent";

const agent = await createAgent({ provider: "anthropic", model: "claude-3-5-sonnet" });
const result = await agent.run("Refactor authentication module");
```

SOURCE: [coding-agent README](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (accessed 2026-02-26), [extensions docs](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md) (accessed 2026-02-26)

---

## Relevance to Claude Code Development

### Direct Applications

1. **Agent Skills Standard Compatibility**: pi reads `AGENTS.md` and `.agents/skills/` using the same Agent Skills standard convention that this repository implements. Skills developed here are directly usable in pi without modification.
2. **Competitive Landscape**: pi is a direct alternative to Claude Code for interactive coding sessions; understanding its extensibility model informs skill design decisions for Claude Code users who compare tools.
3. **Extension Patterns for Skill Design**: pi's TypeScript Extension API (event hooks, custom tools, custom commands, custom UI components) maps closely to Claude Code's skill concept — patterns from pi Extension examples inform what well-structured Claude Code skills should accomplish.
4. **Provider Abstraction Reference**: `@mariozechner/pi-ai`'s 20+ provider support and auth patterns provide a reference for how users expect multi-provider agent setups to work.

### Patterns Worth Adopting

1. **Cascading Context Files**: pi walks parent directories for `AGENTS.md`/`CLAUDE.md` files — the same pattern Claude Code uses. This validates the approach and demonstrates it's worth supporting robustly in skill documentation.
2. **JSONL Session Tree with Non-Destructive Branching**: Storing sessions as JSONL with `id`/`parentId` allows in-place branching without file proliferation — a data model pattern worth documenting for multi-session agent workflows.
3. **Offline Startup Mode**: The `--offline`/`PI_OFFLINE` flag for restricted environments (v0.55.1) addresses a real deployment pain point; Claude Code skills operating in CI/CD contexts should document equivalent patterns.
4. **Shell Command Key Resolution**: Auth file supporting `"key": "!security find-generic-password..."` for secrets managers is a clean credential management pattern for agent documentation.
5. **Pi Packages for Skill Distribution**: The Pi Package model (npm or git bundles of Extensions + Skills + Prompts + Themes) is structurally similar to how this repository distributes Claude Code plugins — examining pi's package loading provides design feedback.

### Integration Opportunities

1. **Cross-Tool Skill Testing**: Since pi loads `.agents/skills/` directories, Claude Code skills in this repository can be tested directly in pi without modification, providing a second validation surface.
2. **Skills Authored for pi**: Community pi Skills following the Agent Skills standard (`~/.pi/agent/skills/`) are compatible with Claude Code's skills loading — the two ecosystems share a skill format.
3. **`@mariozechner/pi-ai` as LLM Abstraction Reference**: When evaluating unified LLM API libraries for agent infrastructure, pi-ai's provider coverage and auth model serves as a current implementation benchmark.

### Competitive Context

| Feature | pi (pi-mono) | Claude Code |
|---------|--------------|-------------|
| Model support | 20+ providers, subscription + API key | Claude only (Anthropic) |
| Extensibility | TypeScript Extensions, Skills, Prompt Templates | Skills (Markdown + references) |
| Open source | MIT | Closed source |
| Skill format | Agent Skills standard (SKILL.md) | Agent Skills standard (SKILL.md) |
| Context files | AGENTS.md / CLAUDE.md | CLAUDE.md |
| Session branching | JSONL tree, in-place branching | Not exposed |
| SDK mode | Yes (`createAgent()`) | No |
| Platform | macOS, Linux, Windows (native binaries) | macOS, Linux (Node.js) |

---

## References

- [GitHub Repository](https://github.com/badlogic/pi-mono) (accessed 2026-02-26)
- [Coding Agent README](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (accessed 2026-02-26)
- [Providers Documentation](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/providers.md) (accessed 2026-02-26)
- [Extensions Documentation](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md) (accessed 2026-02-26)
- [GitHub API - Repository Metadata](https://api.github.com/repos/badlogic/pi-mono) (accessed 2026-02-26)
- [GitHub API - Latest Release v0.55.1](https://api.github.com/repos/badlogic/pi-mono/releases/latest) (accessed 2026-02-26)
- [npm package @mariozechner/pi-coding-agent](https://www.npmjs.com/package/@mariozechner/pi-coding-agent) (accessed 2026-02-26)
- [Discord Community](https://discord.com/invite/3cU7Bz4UPx) (accessed 2026-02-26)

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-02-26 |
| Version at Verification | v0.55.1 |
| Next Review Recommended | 2026-05-26 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [opencut](./opencut.md) | coding-agents | referenced by opencut (coding-agents) |
| [agent-skills](../skill-generation-tools/agent-skills.md) | skill-generation-tools | referenced by agent-skills (skill-generation-tools) |
