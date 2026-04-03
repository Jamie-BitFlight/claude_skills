# cmux — Ghostty-based macOS Terminal for AI Coding Agents

## Overview

cmux is a native macOS terminal application built with Swift/AppKit that extends the Ghostty terminal with features specifically designed for AI coding agents like Claude Code and Codex. It provides vertical tabs in a sidebar, visual notification rings for agent attention, an in-app browser with a scriptable API, and a CLI socket interface for workspace and pane automation.

**Homepage**: <https://cmux.com>
**Repository**: <https://github.com/manaflow-ai/cmux>
**Latest Release**: v0.63.0 (released 2026-03-28)
**License**: AGPL-3.0-or-later (open source) + commercial license option
**Stars**: 11,108 (as of 2026-03-28)

## Problem Addressed

AI developers running multiple Claude Code and Codex sessions in parallel face two core challenges:

1. **Context loss across splits**: With traditional Ghostty (or tmux) and macOS native notifications, the notification body is generic ("Claude is waiting for your input") with no context. With many panes open, the notification doesn't identify which session needs attention.

2. **Opaque agent orchestration**: GUI-based agent orchestrators constrain workflows and typically use Electron/Tauri (performance penalty). Developers prefer terminal-native tools but lack a terminal UI layer designed for multi-agent workflows.

SOURCE: README.md, "Why cmux?" section (accessed 2026-03-28): "I run a lot of Claude Code and Codex sessions in parallel. I was using Ghostty with a bunch of split panes, and relying on native macOS notifications to know when an agent needed me. But Claude Code's notification body is always just 'Claude is waiting for your input' with no context..."

cmux solves this by layering notification awareness, workspace organization, and browser automation on top of Ghostty's rendering engine—all composable via CLI and socket APIs so developers control their workflows.

## Key Statistics

| Metric | Value |
|--------|-------|
| **Repository Stars** | 11,108 (as of 2026-03-28) |
| **Forks** | 765 |
| **Open Issues** | 906 |
| **Primary Language** | Swift |
| **Current Version** | 0.63.0 |
| **Latest Release Date** | 2026-03-28 |
| **License** | AGPL-3.0-or-later (open) + commercial option |
| **Platform** | macOS 14+ |
| **Build System** | Xcode 15+, Zig (for xcframework) |

## Key Features

### Notification System

**Notification Rings & Tabs**: Panes with agent activity get a blue visual ring around them. The sidebar tabs for those workspaces light up, making it trivial to identify which of many concurrent sessions needs attention without reading generic notifications.

**Notification Panel**: Centralized view of all pending notifications. `Cmd+I` toggles the notification panel; `Cmd+Shift+U` jumps to the most recent unread notification.

**Terminal Sequence Integration**: Reads OSC 9/99/777 terminal escape sequences. Agents can wire hooks to emit these sequences via the `cmux notify` CLI command to signal context-rich events.

SOURCE: README.md features table and "Why cmux?" section (accessed 2026-03-28): "The main additions are the sidebar and notification system. The sidebar has vertical tabs that show git branch, linked PR status/number, working directory, listening ports, and the latest notification text for each workspace. When an agent is waiting, its pane gets a blue ring and the tab lights up in the sidebar."

### Vertical & Horizontal Tabs

**Sidebar Workspace Tabs**: Display per-workspace metadata: git branch, linked PR status/number, working directory, listening ports, latest notification text. Tabs are reorderable via drag-and-drop.

**Horizontal Surfaces**: Traditional pane splits (horizontal/vertical) within each workspace. Combine vertical workspace organization with horizontal pane organization.

SOURCE: README.md features table (accessed 2026-03-28): "Sidebar shows git branch, linked PR status/number, working directory, listening ports, and latest notification text. Split horizontally and vertically."

### In-App Browser

**WKWebView-based Browser**: Safari-compatible rendering engine. Panes can be split horizontally or vertically with a browser surface alongside terminal.

**Scriptable API**: Ported from Vercel's `agent-browser` project. Agents can snapshot the accessibility tree, get element refs, click elements, fill forms, and evaluate JavaScript. The API is both CLI and socket-accessible.

**Feature Set** (v0.63.0):
- Browser profile import — cookies, history, and settings from Chrome, Firefox, Safari, and others ([#318](https://github.com/manaflow-ai/cmux/pull/318), [#1582](https://github.com/manaflow-ai/cmux/pull/1582))
- Popup window support with shared OAuth context ([#1150](https://github.com/manaflow-ai/cmux/pull/1150), [#1600](https://github.com/manaflow-ai/cmux/pull/1600))
- Image drag-and-drop into SSH terminals ([#1838](https://github.com/manaflow-ai/cmux/pull/1838))

SOURCE: README.md features table (accessed 2026-03-28): "Split a browser alongside your terminal with a scriptable API ported from agent-browser" + CHANGELOG.md v0.63.0 (accessed 2026-03-28).

### CLI & Socket Automation

**CLI Interface**: Commands like `cmux new-workspace`, `cmux split-pane`, `cmux send-key`, `cmux notify`, and `cmux browser` enable external scripts and agents to control the terminal.

**Socket API**: Unix domain socket at `~/.cmux.sock` (or custom path via `CMUX_SOCKET` env var) for programmatic control. Python/TypeScript clients can connect and dispatch commands.

**Keyboard Modifier Support**: v0.63.0 added support for modifier+key combinations in `send-key` CLI (ctrl+enter, shift+tab, arrow keys, home/end/delete/pageup/pagedown) ([#1994](https://github.com/manaflow-ai/cmux/pull/1994), [#1920](https://github.com/manaflow-ai/cmux/pull/1920)).

SOURCE: README.md (accessed 2026-03-28): "Scriptable — CLI and socket API to create workspaces, split panes, send keystrokes, and automate the browser" + CHANGELOG.md v0.63.0.

### Native Performance

**Swift/AppKit Implementation**: Built in native Swift with macOS AppKit (not Electron or Tauri). Fast startup, low memory footprint.

**GPU-Accelerated Rendering**: Powered by `libghostty` (same library powering the standalone Ghostty terminal). Smooth rendering, minimal input latency.

**Ghostty Config Compatibility**: Reads existing `~/.config/ghostty/config` for themes, fonts, and colors. Drop-in replacement for Ghostty users.

SOURCE: README.md (accessed 2026-03-28): "Native macOS app — Built with Swift and AppKit, not Electron. Fast startup, low memory" + "GPU-accelerated — Powered by libghostty for smooth rendering" + "Ghostty compatible — Reads your existing ~/.config/ghostty/config for themes, fonts, and colors".

### Additional Capabilities (v0.63.0)

- **Minimal Mode**: Hide titlebar for distraction-free terminal ([#1479](https://github.com/manaflow-ai/cmux/pull/1479), [#2218](https://github.com/manaflow-ai/cmux/pull/2218))
- **Custom Commands via `cmux.json`**: Define project-specific actions launched from command palette ([#2011](https://github.com/manaflow-ai/cmux/pull/2011), [#2122](https://github.com/manaflow-ai/cmux/pull/2122))
- **oh-my-openagent Integration**: `cmux omo` command for agent integration ([#2087](https://github.com/manaflow-ai/cmux/pull/2087), [#2230](https://github.com/manaflow-ai/cmux/pull/2230), [#2280](https://github.com/manaflow-ai/cmux/pull/2280))
- **Codex CLI Hooks Integration**: Terminal notifications wired to Codex agent hooks ([#2103](https://github.com/manaflow-ai/cmux/pull/2103))
- **Multi-Window Support**: Cmd+Shift+N for per-window workspaces with synchronized notifications
- **Session Persistence**: Restores window/workspace/pane layout and working directories on relaunch

SOURCE: CHANGELOG.md v0.63.0 (accessed 2026-03-28).

## Technical Architecture

### Core Components (from source inspection)

| Component | File | Responsibility |
|-----------|------|-----------------|
| **Workspace Manager** | `Workspace.swift` | Manages multi-surface layouts, inherits Ghostty surface config (font size, working directory, environment), reconciles geometry after splits/closes |
| **Terminal View** | `GhosttyTerminalView.swift` | Wraps libghostty rendering surface, manages Ghostty wakeups and CVDisplayLink refresh |
| **Notification Store** | `TerminalNotificationStore.swift` | Captures OSC 9/99/777 sequences from terminal output, dedupes notifications, manages macOS UNUserNotificationCenter (off-main-thread to avoid UI freeze from XPC blocking) |
| **Sidebar & Tabs** | `TabManager.swift`, `ContentView.swift`, `SidebarSelectionState.swift` | SwiftUI-based sidebar with per-workspace metadata, drag-reorder, keyboard shortcut hints; uses `.equatable()` conformance to skip re-renders during typing |
| **Browser Integration** | `BrowserPanelView.swift`, `CmuxWebView.swift`, `BrowserPopupWindowController.swift` | WKWebView host, popup window management, scriptable API via socket messages |
| **Socket Control** | `SocketControlSettings.swift` | Unix domain socket listener for CLI/programmatic control; off-main dispatch for telemetry commands |
| **Configuration** | `CmuxConfig.swift`, `GhosttyConfig.swift` | Loads cmux + Ghostty config files, parses `~/.config/ghostty/config` for themes/fonts/colors |

### Data Flow

1. **Terminal Output → Notification Capture**: libghostty renders to PTY; cmux reads output and parses OSC sequences for notifications.
2. **Workspace Changes → Sidebar Update**: User closes/splits/renames → `Workspace` notifies `TabManager` → sidebar re-renders (optimized via `Equatable`).
3. **CLI/Socket Command → Ghostty State**: External process sends socket command (e.g., `new-surface`) → parsed off-main → validated → dispatched to `TerminalController` which calls libghostty APIs and schedules UI update on main thread.
4. **Browser Action → Accessibility Tree Snapshot**: `cmux browser snapshot` → `BrowserPanelView` calls WKWebView JS to extract tree → serialized as JSON → returned to caller.

SOURCE: Code inspection of source files listed above (accessed 2026-03-28). `Workspace.swift` shows `ghostty_surface_inherited_config()` integration; `GhosttyTerminalView.swift` shows CVDisplayLink wakeup handling; `TerminalNotificationStore.swift` shows `UNUserNotificationCenter.removeDeliveredNotificationsOffMain()` pattern; `ContentView.swift` shows `.equatable()` tab rendering optimization; `SocketControlSettings.swift` shows off-main parse/validate pattern.

### Extension Points

**OSC Notification Sequences**: Agents emit OSC 9/99/777 sequences to trigger notifications with custom context. Example:

```bash
cmux notify "Build failed: src/main.rs:42"
```

**CLI Command Hooks**: Scripts can wire agent lifecycle events (on-start, on-complete, on-error) to cmux CLI commands:

```bash
# Hypothetical hook in Claude Code settings
on_completion_hook="cmux notify 'Task completed: $TASK_NAME'"
```

**Custom Commands via `cmux.json`**: Define project-specific actions in `.cmux.json` at project root; these appear in the command palette.

SOURCE: README.md "Why cmux?" and CLI documentation references (accessed 2026-03-28); CHANGELOG.md v0.63.0 mentions custom commands and Codex/OMO integration ([#2103](https://github.com/manaflow-ai/cmux/pull/2103), [#2087](https://github.com/manaflow-ai/cmux/pull/2087)).

## Installation & Usage

### Install via Homebrew (recommended for most users)

```bash
brew tap manaflow-ai/cmux
brew install --cask cmux
```

Update later:
```bash
brew upgrade --cask cmux
```

### Install via DMG

1. Download from [releases/latest](https://github.com/manaflow-ai/cmux/releases/latest/download/cmux-macos.dmg)
2. Open `.dmg` and drag cmux to Applications folder
3. Launch cmux

Auto-updates via Sparkle, so you only need to download once.

### Build from Source

**Prerequisites**: macOS 14+, Xcode 15+, Zig

```bash
git clone --recursive https://github.com/manaflow-ai/cmux.git
cd cmux
./scripts/setup.sh       # Initialize submodules, build GhosttyKit.xcframework
./scripts/reload.sh --tag my-feature --launch  # Build and launch debug app
```

SOURCE: README.md Install section + CONTRIBUTING.md (accessed 2026-03-28).

### Basic Usage

#### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Cmd+N** | New workspace |
| **Cmd+1-8** | Jump to workspace 1-8 |
| **Cmd+9** | Jump to last workspace |
| **Cmd+T** | New surface (tab) |
| **Cmd+D** | Split right |
| **Cmd+Shift+D** | Split down |
| **Cmd+I** | Show notifications panel |
| **Cmd+Shift+U** | Jump to latest unread notification |
| **Cmd+B** | Toggle sidebar |
| **Cmd+Shift+L** | Open browser in split |
| **Cmd+L** | Focus browser address bar (or open browser if focused panel is terminal) |
| **Cmd+F** | Find in terminal |
| **Cmd+K** | Clear scrollback |
| **Cmd+,** | Settings |

SOURCE: README.md Keyboard Shortcuts section (accessed 2026-03-28).

#### CLI Usage Examples

```bash
# Create a new workspace named "dev"
cmux new-workspace --name dev

# Split the focused surface right and run a command
cmux split-pane --direction right --command "npm start"

# Send keystrokes to a surface
cmux send-key --surface-id <id> Tab Return

# Open a browser pane
cmux browser --direction right --url https://example.com

# Snapshot browser accessibility tree
cmux browser snapshot --surface-id <id> | jq .

# Emit a notification from a script
cmux notify "Build succeeded"
```

### Configuration

cmux reads `~/.config/ghostty/config` for themes, fonts, and colors. Example:

```ini
# ~/.config/ghostty/config
font-family = Monaco
font-size = 14
theme = dracula
```

Custom cmux settings are configured in **Settings → Preferences** (Cmd+,) or via `~/.config/cmux/config.json`.

Project-specific commands go in `.cmux.json` at the project root.

SOURCE: README.md and CONTRIBUTING.md (accessed 2026-03-28).

## Limitations & Caveats

### Session Restoration

On relaunch, cmux restores **layout and metadata only**:
- Window/workspace/pane layout
- Working directories
- Terminal scrollback (best effort)
- Browser URL and navigation history

cmux does **NOT** restore live process state (e.g., active Claude Code/tmux/vim sessions are not resumed after restart).

SOURCE: README.md "Session restore (current behavior)" section (accessed 2026-03-28).

### Platform Constraints

- **macOS only**: No Linux or Windows ports currently planned. cmux uses AppKit (macOS native framework) and libghostty, both macOS-specific.
- **macOS 14+**: Requires Sonoma or later.

### Multi-Agent Context Limits

While the sidebar and notification system help, managing 10+ concurrent Claude Code sessions still requires discipline:
- The notification panel can become crowded
- Workspace switching keyboard shortcuts (Cmd+1-9) max out at 9 workspaces
- No automatic routing or intelligent grouping of agent sessions (by project, priority, etc.) — users must organize manually

### Browser Limitations

The in-app WKWebView browser lacks some features of standalone browsers:
- Certain browser extensions not supported
- Profile sync is manual (import via Settings), not continuous
- Video playback and some modern web APIs have limited support compared to Chrome/Safari

SOURCE: CHANGELOG.md and README.md (accessed 2026-03-28) document features but do not explicitly list these browser gaps; inference is from standard WKWebView constraints and the fact that v0.63.0 added browser profile import as a new feature.

## Relevance to Claude Code Development

### Direct Use Case

cmux is purpose-built for Claude Code developers. It solves the exact workflow problem: running multiple Claude Code instances in parallel and knowing which one needs attention without context-switching to notifications.

**Integration Points**:
1. **Notification Hooks**: Wire Claude Code's `on_completion`, `on_error`, `on_waiting` hooks to emit OSC sequences via `cmux notify` so the sidebar lights up when Claude needs input.
2. **Browser Automation**: For Claude Code tasks that require browser interaction, split a cmux browser pane and use the scriptable API to automate clicks/form-fills/snapshots.
3. **Workspace Organization**: Dedicate one cmux workspace per Claude Code project or milestone; the sidebar metadata (git branch, PR status) helps track context.
4. **Socket API Integration**: Claude Code hooks can emit arbitrary socket commands (e.g., `cmux split-pane --command "python my-script.py"`) to orchestrate multi-step agent workflows.

### Why It Matters

- **Agent-Aware UI**: Unlike generic Ghostty or iTerm2, cmux's design assumes you're managing multiple agentic processes in parallel.
- **No Workflow Lock-in**: Unlike GUI orchestrators (AMP, Codex Dashboard, etc.), cmux stays terminal-native with composable APIs. Developers are not forced into a specific orchestration pattern.
- **Low Latency**: Native AppKit + libghostty means no Electron overhead. Important when agents iterate rapidly and UI responsiveness matters.

### Limitations for Claude Code

1. **No Built-in Agent Scheduling**: cmux does not prioritize or order agent execution. It's a UI primitive, not an orchestrator.
2. **Manual Notifications**: Agents must explicitly emit OSC sequences; there's no automatic detection of "Claude Code is waiting." (Though integration with Claude Code settings/hooks could automate this.)
3. **macOS-Only**: Claude Code developers on Linux/Windows cannot use cmux. They would need to run Claude Code via SSH or use cmux on a macOS box as a relay.

## References

| Source | URL | Accessed |
|--------|-----|----------|
| cmux Official Homepage | <https://cmux.com> | 2026-03-28 |
| GitHub Repository | <https://github.com/manaflow-ai/cmux> | 2026-03-28 |
| README.md | <https://github.com/manaflow-ai/cmux/blob/main/README.md> | 2026-03-28 |
| CHANGELOG.md | <https://github.com/manaflow-ai/cmux/blob/main/CHANGELOG.md> | 2026-03-28 |
| CONTRIBUTING.md | <https://github.com/manaflow-ai/cmux/blob/main/CONTRIBUTING.md> | 2026-03-28 |
| GitHub API — Repository | `gh api repos/manaflow-ai/cmux` | 2026-03-28 |
| GitHub API — Latest Release | `gh api repos/manaflow-ai/cmux/releases/latest` | 2026-03-28 |
| PROJECTS.md | <https://github.com/manaflow-ai/cmux/blob/main/PROJECTS.md> | 2026-03-28 |
| Source Code — Workspace.swift | <https://github.com/manaflow-ai/cmux/blob/main/Sources/Workspace.swift> | 2026-03-28 |
| Source Code — TerminalNotificationStore.swift | <https://github.com/manaflow-ai/cmux/blob/main/Sources/TerminalNotificationStore.swift> | 2026-03-28 |
| Agent-Browser (Inspiration) | <https://github.com/vercel-labs/agent-browser> | Referenced in README.md |

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|---------------|-------|
| **Identity/Metadata** | high | 2026-03-28 | GitHub API, official homepage, v0.63.0 release confirmed |
| **Problem Addressed** | high | 2026-03-28 | Extracted from README.md "Why cmux?" with direct quotes |
| **Key Statistics** | high | 2026-03-28 | GitHub API snapshot (11,108 stars, v0.63.0, AGPL-3.0-or-later) |
| **Key Features** | high | 2026-03-28 | README.md features table + CHANGELOG.md v0.63.0 verified; extracted with PR links |
| **Technical Architecture** | medium | 2026-03-28 | Source code inspection of Workspace.swift, TerminalNotificationStore.swift, TabManager.swift, etc.; component names and data flow inferred from code structure; high confidence in structure but limited by not running the app |
| **Installation & Usage** | high | 2026-03-28 | README.md and CONTRIBUTING.md instructions; keyboard shortcuts from official docs |
| **Limitations & Caveats** | high | 2026-03-28 | README.md "Session restore (current behavior)" section; platform constraints are documented in CONTRIBUTING.md |
| **Relevance to Claude Code** | medium | 2026-03-28 | Based on repository description, features, and use case; not verified against Claude Code's actual hook API but inferred from cmux's CLI/notification design |

**Next Review**: 2026-06-28 (3 months from 2026-03-28)

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
