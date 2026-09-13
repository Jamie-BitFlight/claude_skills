---
name: Yume - Native Desktop GUI for Claude Code CLI
description: 'Yume (Japanese: "dream") is a native desktop GUI wrapper around the Claude Code CLI that adds 30+ features the CLI does not provide, including zero-flicker rendering, parallel agent orchestration,...'
license: Not specified (advertised as free forever)
metadata:
  topic: yume
  category: developer-tools
  source_url: https://github.com/yume
  verified: "2026-02-15"
  next_review: "2026-05-15"
---

## Overview

Yume (Japanese: "dream") is a native desktop GUI wrapper around the Claude Code CLI that adds 30+ features the CLI does not provide, including zero-flicker rendering, parallel agent orchestration, auto-compaction, crash recovery, and multi-provider model support. It spawns the real Claude CLI process (not an API wrapper), so all CLI-native functionality -- subagents, MCP, hooks, skills, CLAUDE.md, @mentions, /commands -- works without modification. Built with Tauri + Rust (claimed 10x lighter than Electron), it also supports Gemini and OpenAI models via a yume-cli shim layer.

---

## Problem Addressed

| Problem | Yume Solution |
|---------|---------------|
| CLI terminal flickering (700+ developer upvotes on the issue) | Native rendering engine with zero flickering via Tauri + Rust |
| Input lag of 10+ seconds in long CLI sessions | Sub-50ms input response time regardless of session length |
| CLI crashes every 10-20 minutes in extended sessions (per Yume's claims) | 24-hour crash recovery with 5-minute state snapshots |
| No visibility into token usage or context window limits | Live mid-stream token count, token usage analytics by project/model/date, auto-compaction at 75% capacity |
| CLI is single-session only (no tabs or windows) | Tabs + windows with multiple simultaneous sessions |
| No visual tracking of file changes made by agents | Visual timeline of all file changes per message, with undo capability |
| CLI shows thinking output only after completion | Live interleaved thinking streamed in real-time |
| CLI uses a single generalist agent for all tasks | 4 specialist agents (Architect, Explorer, Implementer, Guardian) with role-based task decomposition |
| No built-in security guardrails beyond CLI permissions | Yume Guard: configurable security hook that blocks dangerous commands (e.g., rm -rf) |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Platform Support | macOS (Apple Silicon + Intel), Windows, Linux | 2026-02-15 |
| Runtime Framework | Tauri + Rust | 2026-02-15 |
| Feature Count | 30+ (per website) | 2026-02-15 |
| Supported Models | 6 models across 3 providers | 2026-02-15 |
| Claude Models | Sonnet, Opus | 2026-02-15 |
| Gemini Models | 2.5 Pro, 2.5 Flash | 2026-02-15 |
| OpenAI Models | GPT-5.2, Codex | 2026-02-15 |
| Parallel Agents | 4 (on isolated git branches) | 2026-02-15 |
| Keyboard Shortcuts | 30+ | 2026-02-15 |
| Command Palette Commands | 56 across 10 categories | 2026-02-15 |
| Themes | 12 + custom accent colors | 2026-02-15 |
| Hook Event Types | 9 | 2026-02-15 |
| Auto-Compaction Threshold | 75% context window | 2026-02-15 |
| Crash Recovery Window | 24 hours (5-minute snapshots) | 2026-02-15 |
| Telemetry | Zero | 2026-02-15 |
| Input Response Time | <50ms (claimed) | 2026-02-15 |
| Price | Free forever (per website) | 2026-02-15 |

---

## Key Features

### Agent System

- **4 specialist agents**: Architect (planning, risk identification), Explorer (read-only codebase reconnaissance), Implementer (small precise edits, minimal diffs), Guardian (bug detection, security holes, performance issues)
- **Task decomposition workflow**: Understand, decompose, act, verify
- **Parallel execution**: 4 agents run simultaneously on isolated git branches
- **Agent-managed orchestration**: "You describe what. Yume figures out how." -- user provides intent, system handles decomposition and agent selection

### UI/UX

- **Zero flickering**: Native rendering eliminates terminal flicker (addresses 700+ upvoted CLI issue)
- **Live interleaved thinking**: Thinking output streams in real-time (CLI shows after completion)
- **Tabs + windows**: Multiple simultaneous sessions (CLI is single-session)
- **12 themes + custom accent colors**: Visual customization
- **30+ keyboard shortcuts**: cmd+t (new tab), cmd+o (switch model), cmd+k (ultrathink), cmd+l (clear)
- **Command palette**: 56 commands across 10 categories with fuzzy search
- **Virtualized rendering**: Handles 10,000+ messages without performance degradation
- **Message rollback/branching**: Undo and branch conversation history
- **@ mention system**: Autocomplete for file and context references
- **CLAUDE.md editor**: Built-in editor with live preview
- **Project browser**: Search, filter, view git changes across projects
- **Voice dictation**: Native speech-to-text input

### Performance

- **Sub-50ms input response time**: Maintains responsiveness in long sessions (CLI degrades to 10+ seconds)
- **Auto-compaction at 75%**: Automatic context management prevents hitting context limits
- **24-hour crash recovery**: 5-minute state snapshots enable recovery from crashes
- **Stream timers**: Live duration display for thinking, bash execution, and compaction phases

### Developer Tools

- **Full CLI compatibility**: Spawns real Claude CLI process; subagents, MCP, hooks, skills, CLAUDE.md, @mentions, /commands all function
- **One-click extension install**: Commands, agents, hooks, skills installable from GUI
- **Context auto-loading skills**: Opening a .tsx file automatically loads React knowledge
- **Yume Guard**: Built-in security hook, blocks rm -rf and other dangerous commands, configurable
- **Visual file change timeline**: Track every file change per message with undo capability
- **Token usage analytics**: Usage breakdown by project, model, and date
- **Mid-stream context**: Live token count during generation
- **MCP support**: Full Model Context Protocol integration
- **Hooks system**: 9 event types for extensibility

### Multi-Provider Support

- **Claude**: Sonnet, Opus
- **Gemini**: 2.5 Pro, 2.5 Flash (via yume-cli shim)
- **OpenAI**: GPT-5.2, Codex (via yume-cli shim)

---

## Technical Architecture

<eg>
┌──────────────────────────────────────────────────────────────────┐
│                     Yume Desktop Application                      │
│                       (Tauri + Rust)                               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Native GUI Layer                          │  │
│  │                                                              │  │
│  │  - Zero-flicker rendering engine                             │  │
│  │  - Virtualized message list (10k+ messages)                  │  │
│  │  - Tabs/windows management                                   │  │
│  │  - Command palette (56 commands, fuzzy search)               │  │
│  │  - 12 themes + accent color system                           │  │
│  │  - CLAUDE.md editor with live preview                        │  │
│  │  - Token usage analytics dashboard                           │  │
│  │  - Voice dictation (native speech-to-text)                   │  │
│  └──────────────────┬──────────────────────────────────────────┘  │
│                     │                                              │
│  ┌──────────────────v──────────────────────────────────────────┐  │
│  │                 Agent Orchestration Layer                     │  │
│  │                                                              │  │
│  │  Workflow: understand --> decompose --> act --> verify         │  │
│  │                                                              │  │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌────────┐ │  │
│  │  │ Architect  │ │ Explorer   │ │ Implementer  │ │Guardian│ │  │
│  │  │ (planning, │ │ (read-only │ │ (precise     │ │(bugs,  │ │  │
│  │  │  risk ID)  │ │  recon)    │ │  edits)      │ │security│ │  │
│  │  └────────────┘ └────────────┘ └──────────────┘ │review) │ │  │
│  │                                                  └────────┘ │  │
│  │  4 parallel agents on isolated git branches                  │  │
│  └──────────────────┬──────────────────────────────────────────┘  │
│                     │                                              │
│  ┌──────────────────v──────────────────────────────────────────┐  │
│  │                 CLI Process Manager                           │  │
│  │                                                              │  │
│  │  - Spawns real Claude CLI (not API wrapper)                  │  │
│  │  - yume-cli shim for Gemini/OpenAI model routing             │  │
│  │  - Auto-compaction at 75% context capacity                   │  │
│  │  - 24hr crash recovery (5-min state snapshots)               │  │
│  │  - Yume Guard security hook layer                            │  │
│  │  - Live interleaved thinking stream capture                  │  │
│  └──────────────────┬──────────────────────────────────────────┘  │
│                     │                                              │
└─────────────────────┼──────────────────────────────────────────────┘
                      │
          ┌───────────v───────────┐
          │    Claude Code CLI    │
          │                       │
          │  - Subagents          │
          │  - MCP servers        │
          │  - Hooks              │
          │  - Skills             │
          │  - CLAUDE.md          │
          │  - @mentions          │
          │  - /commands          │
          └───────────────────────┘
</eg>

### Key Architectural Decisions

1. **Tauri + Rust over Electron**: Claimed 10x lighter memory footprint than Electron-based alternatives. Native rendering avoids the terminal flickering inherent in web-based terminal emulators.

2. **CLI spawning (not API wrapping)**: Yume spawns the actual Claude Code CLI binary rather than making direct API calls. This ensures full compatibility with the CLI ecosystem (MCP, hooks, skills, CLAUDE.md, etc.) without reimplementation.

3. **yume-cli shim for multi-provider**: A shim layer intercepts CLI calls and routes them to Gemini or OpenAI when those models are selected, enabling multi-provider support without modifying the Claude CLI itself.

4. **Isolated git branches for parallel agents**: Each of the 4 parallel agents operates on its own git branch, preventing file conflicts during simultaneous execution.

5. **Auto-compaction at 75%**: Proactive context management triggers compaction before reaching the context window limit, preventing the session-ending "context full" state.

---

## Installation and Usage

### Download

Downloads available from the official website:

- **macOS (Apple Silicon)**: <https://aofp.github.io/yume/> (Apple Silicon build)
- **macOS (Intel)**: <https://aofp.github.io/yume/> (Intel build)
- **Windows**: <https://aofp.github.io/yume/> (Windows build)
- **Linux**: <https://aofp.github.io/yume/> (Linux build)

### Prerequisites

- Claude Code CLI must be installed and authenticated (`claude` command available in PATH)
- For Gemini/OpenAI model support: yume-cli shim (bundled with Yume)

### Basic Usage

1. Download and install Yume for your platform
2. Launch Yume -- it automatically detects the Claude Code CLI
3. Open a project directory (project browser or file dialog)
4. Begin a session in a tab; all CLI features (MCP, hooks, skills, CLAUDE.md) work automatically
5. Use cmd+t for new tabs, cmd+o to switch models, cmd+k for ultrathink mode

### Key Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| cmd+t | New tab |
| cmd+o | Switch model |
| cmd+k | Ultrathink mode |
| cmd+l | Clear session |

---

## Relevance to Claude Code Development

### Applications

1. **Agent Specialization Reference**: The 4-agent architecture (Architect/Explorer/Implementer/Guardian) demonstrates a structured approach to task decomposition where each agent has a constrained role. This mirrors the principle of specialized sub-agents found in the agent-orchestration skill, where task-appropriate agent selection improves output quality.

2. **Context Management Strategy**: Auto-compaction at 75% context capacity is a proactive approach to the context window limit problem. Rather than letting sessions fail at 100%, Yume compacts before reaching the limit. This pattern is relevant to any long-running Claude Code session management.

3. **Desktop GUI as CLI Enhancement Layer**: Yume demonstrates that a GUI wrapper can add substantial value (parallel agents, crash recovery, visual timelines) without replacing the underlying CLI. The "spawn real CLI" architecture preserves full ecosystem compatibility.

### Patterns Worth Adopting

1. **Specialist Agent Roles**: The Architect/Explorer/Implementer/Guardian decomposition maps to distinct phases of software development (plan, understand, implement, review). This pattern aligns with and extends the sub-agent selection guidance in this repository's CLAUDE.md, which distinguishes between explore agents (read-only search) and context-gathering agents (reasoning tasks).

2. **Proactive Context Compaction**: Triggering compaction at 75% rather than waiting for context exhaustion is a defensive pattern. Claude Code sessions that approach context limits often produce degraded output before hitting the hard limit. The 75% threshold provides a buffer.

3. **Context Auto-Loading by File Type**: Opening a .tsx file automatically loading React knowledge is a pattern for automatic skill activation. This aligns with the skill activation trigger concept where context is loaded based on detected conditions rather than explicit user invocation.

4. **Security Hook Layer (Yume Guard)**: A configurable security hook that blocks dangerous commands (rm -rf) before they execute is a pattern for agent safety. This parallels the hooks system in Claude Code but with a pre-built security-focused default configuration.

5. **Visual Change Timeline with Undo**: Tracking every file change per message and offering undo capability provides transparency into agent actions. This addresses the "what did the agent change?" visibility problem that exists in CLI-only workflows.

### Integration Opportunities

1. **Agent Role Definitions**: The Architect/Explorer/Implementer/Guardian role definitions could inform the design of specialized Claude Code agents or sub-agent selection criteria in the agent-orchestration skill.

2. **Compaction Threshold as a Configurable Setting**: The 75% auto-compaction threshold could be adopted as a recommended practice for long-running Claude Code sessions, potentially implemented as a hook that monitors context usage.

3. **File-Type Skill Activation**: The context auto-loading pattern (file type triggers skill loading) could be implemented as a Claude Code hook that detects opened/referenced file types and suggests or loads relevant skills.

### Considerations

1. **Unverified Claims**: Performance claims (sub-50ms response, CLI crashes every 10-20 minutes, 10x lighter than Electron) are sourced from Yume's marketing website. Independent benchmarks have not been located. These claims should be treated as unverified marketing assertions until independently confirmed.

2. **License Ambiguity**: The website states "free forever" but no specific open-source license is identified. The source code availability and terms of use are unclear. This affects any consideration of studying or adapting Yume's implementation patterns.

3. **CLI Dependency**: Yume requires the Claude Code CLI to be installed and functional. It is an enhancement layer, not a standalone product. Changes to the CLI's process model, output format, or authentication could break Yume's integration.

4. **Multi-Provider via Shim**: Gemini and OpenAI support is achieved through a yume-cli shim that intercepts CLI calls. This is an indirect integration that may not fully replicate the behavior or capabilities of native provider SDKs.

5. **Closed Source (Assumed)**: No public source repository has been identified for Yume itself (the GitHub profile github.com/aofp hosts the GitHub Pages site but the application source has not been located). This limits the ability to verify architectural claims or study implementation patterns directly.

6. **New Project**: No version number, release history, or community size metrics have been identified. The project's longevity and maintenance trajectory are unknown.

---

## References

1. **Yume Official Website** - <https://aofp.github.io/yume/> (accessed 2026-02-15)
2. **Yume GitHub Pages Host** - <https://github.com/aofp> (inferred from GitHub Pages domain, accessed 2026-02-15)
3. **Claude Code CLI Flickering Issue** - Referenced by Yume website as having 700+ upvotes (accessed 2026-02-15; original GitHub issue URL not provided by source)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [cmux](../agent-infrastructure/cmux.md) | agent-infrastructure | referenced by cmux (agent-infrastructure) |
| [happycapy](../agent-infrastructure/happycapy.md) | agent-infrastructure | referenced by happycapy (agent-infrastructure) |
| [emqutiti](./emqutiti.md) | developer-tools | referenced by emqutiti (developer-tools) |
| [ghost-desk](./ghost-desk.md) | developer-tools | referenced by ghost-desk (developer-tools) |
| [gridland](./gridland.md) | developer-tools | referenced by gridland (developer-tools) |
| [tabularis](./tabularis.md) | developer-tools | Shares Tauri + Rust cross-platform desktop architecture; Yume focuses on multi-agent orchestration UI (bidirectional) |
