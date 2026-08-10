---
name: cmux
research_date: "2026-08-10"
source_url: https://github.com/manaflow-ai/cmux
github_repository: https://github.com/manaflow-ai/cmux
version_at_research: v1.38.1
license: "GPL-3.0-or-later (open source) + commercial license option"
freshness_tracking:
  last_verified: "2026-08-10"
  version_at_verification: v1.38.1
  next_review: "2026-11-10"
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high, Installation & Usage: high, Relevance: medium"
---

# cmux

## Overview

cmux is an open-source Ghostty-based terminal multiplexer for macOS, purpose-built for developers running multiple AI coding agents simultaneously. Created by Manaflow AI, it combines Ghostty's GPU-accelerated terminal rendering with specialized UI features for agent monitoring: vertical tabs displaying git branch, PR status, listening ports, and real-time notifications that alert developers when agents require attention. (SOURCE: [GitHub - manaflow-ai/cmux](https://github.com/manaflow-ai/cmux), accessed 2026-08-10)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Managing multiple concurrent AI agents without tab overload | Vertical tabs in sidebar showing git branch, PR number, working directory, listening ports, and latest notification for each session |
| Agent notification blindness — missing critical alerts from running agents | Notification rings around active panes; blue highlight indicators when agents require attention |
| Coordinating remote agent execution across multiple machines | Native SSH support via `cmux ssh user@remote` for creating remote workspaces |
| Lack of programmatic control and automation for agent workflows | Socket API and CLI interface (`cmux notify`) for wiring agent hooks and custom automation |

---

## Key Features

### Terminal Multiplexing

- **Vertical tabs with sidebar metadata**: Each workspace displays git branch, linked PR status/number, working directory, and listening ports at a glance
- **Horizontal and vertical pane splitting**: Organize multiple agent sessions within a single window
- **Native Ghostty integration**: GPU-accelerated rendering via libghostty with direct Ghostty configuration file compatibility
- **Session persistence**: Workspaces persist across application restarts

### Agent-Focused Notifications

- **Notification rings and highlighting**: Blue rings appear around active panes; tabs illuminate when agents emit notifications
- **OSC sequence support**: Reads terminal sequences (OSC 9/99/777) for structured notifications
- **CLI notification interface**: `cmux notify` command for wiring Claude Code and other agent frameworks directly into cmux
- **Selective attention**: Scan up to 10 running sessions without switching into any of them

### Extensibility & Integration

- **Socket API**: Programmatic control via socket connections for custom integrations
- **CLI automation**: Full command-line interface for scripting and remote operation
- **Agent ecosystem compatibility**: Works with Claude Code, Codex, OpenCode, Gemini CLI, Aider, Goose, and any terminal-based agent
- **Built-in browser**: Integrated web browser pane for agents that need to interact with web applications

---

## Technical Architecture

cmux is implemented in Swift and AppKit as a native macOS application. It wraps libghostty, Ghostty's terminal rendering library, providing GPU-accelerated text rendering while adding the sidebar and notification system on top.

**Core Components** (SOURCE: [GitHub - manaflow-ai/cmux README](https://github.com/manaflow-ai/cmux), accessed 2026-08-10):

- **Terminal Engine**: libghostty (GPU-accelerated PTY rendering)
- **Window Management**: AppKit (native macOS UI framework)
- **Sidebar System**: Custom metadata display for each workspace (git, PR, ports, notifications)
- **Notification System**: OSC sequence parser and visual alert engine
- **Socket Server**: IPC interface for programmatic control via `cmux notify` CLI and socket connections

The architecture prioritizes performance (GPU rendering, native UI) and simplicity (builds on Ghostty's proven rendering pipeline rather than reimplementing terminal logic).

---

## Installation & Usage

### Installation

**Homebrew (recommended)**:
```bash
brew tap manaflow-ai/cmux
brew install --cask cmux
```

**DMG (direct download)**:
```bash
# Download from GitHub releases
# https://github.com/manaflow-ai/cmux/releases
```

**Nightly builds**:
```bash
brew tap manaflow-ai/cmux --force
brew install --cask cmux --no-quarantine
```

(SOURCE: [GitHub - manaflow-ai/cmux](https://github.com/manaflow-ai/cmux), accessed 2026-08-10)

### Basic Usage

```bash
# Create a new workspace
cmux new -s workspace-name

# SSH into a remote machine and create a workspace
cmux ssh user@remote

# Split panes horizontally
cmux split -h

# Split panes vertically
cmux split -v

# Send a notification to the current pane
cmux notify "Agent completed task"
```

### Agent Integration Example

**Claude Code Integration**:
```bash
# Start cmux and Claude Code in a new pane
cmux new -s claude
cmux send "claude" "claude code myproject/" Enter
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Multi-Agent Monitoring**: Claude Code developers running multiple concurrent agents can monitor all sessions from a single sidebar without switching panes, addressing a critical UX need for complex multi-agent workflows.

2. **Notification Integration**: The OSC sequence support and `cmux notify` CLI allow Claude Code to emit structured notifications that cmux displays, improving agent-developer communication patterns.

3. **Workspace Organization**: Git branch and PR status display in the sidebar provides context-aware organization for multi-project agent development.

### Patterns Worth Adopting

1. **Metadata-Rich Tab Display**: cmux's approach of showing git branch, PR status, and ports in workspace tabs demonstrates how terminal UX can be enhanced without visual clutter — applicable to Claude Code's own shell representation.

2. **Agent-Centric Notification Design**: The notification ring and highlight system is specifically designed for handling multiple concurrent agents. Claude Code's orchestration layer could adopt similar principles for reporting agent state changes.

### Integration Opportunities

1. **Claude Code Agent Hooks**: Extend Claude Code's hook system to emit OSC sequences that cmux can display, enabling real-time agent status notification.

2. **Multi-Agent Dashboard**: A Claude Code skill could leverage cmux's socket API to build a custom dashboard showing runtime stats from multiple concurrent agents.

---

## References

- [GitHub - manaflow-ai/cmux](https://github.com/manaflow-ai/cmux) (accessed 2026-08-10)
- [cmux: Ghostty-Based Terminal for AI Agents](https://akmatori.com/blog/cmux-terminal-for-ai-agents) (accessed 2026-08-10)
- [Best terminal for agentic coding in 2026](https://agentsroom.dev/blog/best-terminal-for-agentic-coding) (accessed 2026-08-10)
- [cmux: The Terminal Built for Multitasking with AI Agents](https://dudarik.com/en/blog/cmux-the-terminal-built-for-multitasking/) (accessed 2026-08-10)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [kernel-sh.md](../agent-infrastructure/kernel-sh.md) | agent-infrastructure | complementary cloud browser infrastructure for AI agents; kernel provides servers, cmux provides the client UI |
| [vibium.md](../agent-infrastructure/vibium.md) | agent-infrastructure | alternative W3C standard browser automation via WebDriver BiDi; cmux uses WKWebView with scriptable API |
| [using-tmux-with-claude-code.md](../developer-tools/using-tmux-with-claude-code.md) | developer-tools | terminal multiplexing workflow predecessor; cmux extends tmux's multi-pane coordination with native UI and notifications |
| [shpool.md](../developer-tools/shpool.md) | developer-tools | raw PTY session persistence without intermediate terminal rendering; cmux manages Ghostty-rendered surfaces with extended metadata |
| [byobu.md](../developer-tools/byobu.md) | developer-tools | terminal multiplexer wrapper with status bar UI; cmux replaces this pattern with native macOS app and agent-focused notifications |
| [yume.md](../developer-tools/yume.md) | developer-tools | native Tauri+Rust GUI for Claude Code CLI parallelizing agents; cmux focuses on terminal pane organization and visual agent attention signals |
| [orbstack.md](../developer-tools/orbstack.md) | developer-tools | native macOS VM and container management with resource optimization; cmux applies similar efficiency principles to terminal workspace organization |

---

**Entry Status**: Complete
**Created**: 2026-03-28
**Resource Name**: cmux
**Category**: agent-infrastructure
