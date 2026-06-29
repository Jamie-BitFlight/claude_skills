---
title: "Using tmux with Claude Code"
research_date: "2026-03-01"
source_url: "https://hboon.com/using-tmux-with-claude-code/"
github_url: "N/A (blog post/guide, no associated repository)"
version_at_research: "Published 2025-11-28"
license: "All rights reserved (blog post — no open-source license)"
last_verified: "2026-03-01"
version_at_verification: "Published 2025-11-28"
next_review: "2026-06-01"
---

## Overview

A practical guide by Hwee-Boon Yar showing how tmux's built-in features satisfy the workflow needs of Claude Code and other LLM CLI agents without requiring application-level pagination or scrollback features. The post covers copy mode navigation, buffer capture, control-key passthrough configuration, and multi-window orchestration patterns where Claude Code coordinates with tmux panes running servers or parallel agents.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Claude Code output scrolls off screen with no way to review history | tmux copy mode (`ctrl-w [`) provides full vi-style scrollback, search, and page navigation over the entire session history |
| Need to extract long agent output for editing or archiving | `tmux capture-pane -t 0 -p -S -10000` pipes up to 10,000 lines of history to stdout, which can be piped to an editor |
| tmux intercepts control sequences intended for Claude Code or other coding agents | Bind tmux passthroughs (e.g., `bind o send-keys C-o`) to forward native agent shortcuts through tmux |
| Monitoring a background server while Claude Code modifies code | Run the server in a separate tmux window/pane; tell Claude Code to reference that pane by its tmux address (e.g., "window 9, pane 0") |
| Running multiple agent sessions in parallel with no coordination | Claude Code understands tmux addressing syntax and can read pane contents, issue commands to panes, or delegate subtasks to an agent running in another window |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Author | Hwee-Boon Yar (hboon) | 2026-03-01 |
| Publication Date | 2025-11-28 | 2026-03-01 |
| Format | Blog post (hboon.com) | 2026-03-01 |
| Follow-up post | Auto-Renaming tmux Windows for AI Coding Agents | 2026-03-01 |
| GitHub Stars | N/A | 2026-03-01 |
| Package Registry | N/A | 2026-03-01 |

No repository or package is associated with this resource. It is a workflow guide.

---

## Key Features

### Copy Mode Navigation

- Enter copy mode with `ctrl-w [` (requires prefix key bound to `ctrl-w` or equivalent)
- Page up/down: `ctrl-u` / `ctrl-d`
- Line-by-line scroll: `j` / `k` (vi bindings)
- Forward search: `/` followed by pattern
- Backward search: `?` followed by pattern
- Jump to next/previous match: `n` / `N`
- Exit copy mode: `ctrl-c`
- Eliminates the need for Claude Code to implement its own pagination or scrollback

### Buffer Capture to Editor

- Command: `tmux capture-pane -t 0 -p -S -10000 | v` (where `v` is the user's editor alias)
- `-t 0` targets pane 0 of the current window
- `-p` prints captured content to stdout
- `-S -10000` captures up to 10,000 lines of scrollback history
- Enables full extraction of agent output for archiving, diffing, or editing

### Control-Key Passthrough

- tmux intercepts many `ctrl-*` sequences before they reach the running program
- Bind passthroughs in `.tmux.conf` for shortcuts used by coding agents:

  ```text
  bind o send-keys C-o
  ```

- Allows agents like Droid (and others with native keyboard shortcuts) to receive their own control sequences

### Multi-Pane Orchestration with Claude Code

- Claude Code understands tmux window and pane addressing: referencing "tmux 9.0" means window 9, pane 0
- Claude Code knows the tmux subcommands to read pane contents, issue commands, scroll back history, or re-run commands from history
- Enables live-server monitoring: run a backend with live reload in one pane, instruct Claude Code to inspect that pane's output after making code changes
- Enables parallel agent coordination: one Claude Code session can send tasks to, and check output from, another agent running in a separate tmux window

---

## Technical Architecture

The workflow rests on two tmux capabilities:

1. **Session persistence and pane addressability** — Every tmux pane has a `[window].[pane]` address that Claude Code can reference in natural language and use in tmux subcommands (`capture-pane`, `send-keys`, `pipe-pane`).

2. **Copy mode as a full-featured scrollback viewer** — tmux's copy mode is a vi-style buffer navigator built into the terminal multiplexer, completely independent of the application running in the pane.

```text
User terminal
    |
    v
tmux session (prefix: ctrl-w)
    |-- Window 0: Claude Code agent
    |       |-- Pane 0: claude (reads pane output from other windows)
    |
    |-- Window 9: Backend API server (live reload)
    |       |-- Pane 0: server output (readable by Claude Code as "tmux 9.0")
    |
    |-- Window N: Parallel coding agent (Droid, another Claude, etc.)
            |-- Pane 0: agent output (addressable, inspectable)
```

Claude Code's understanding of tmux addressing is intrinsic — no plugin or wrapper is required. The user communicates window/pane references in natural language and Claude Code translates them into tmux subcommands.

---

## Installation & Usage

tmux is a standard terminal multiplexer available on all major platforms. The techniques in this guide require no additional installation beyond tmux itself.

```bash
# Install tmux
# macOS
brew install tmux

# Debian/Ubuntu
sudo apt-get install tmux

# Arch Linux
sudo pacman -S tmux
```

```text
# .tmux.conf — recommended additions for Claude Code / coding-agent workflows

# Set prefix to ctrl-w (author's preference; ctrl-b is default)
set -g prefix C-w
unbind C-b
bind C-w send-prefix

# Passthrough shortcuts used by coding agents (example: ctrl-o for Droid)
bind o send-keys C-o

# Increase scrollback buffer to capture long agent output
set -g history-limit 50000
```

```bash
# Capture pane history to editor (10,000 lines)
tmux capture-pane -t 0 -p -S -10000 | v

# Copy mode — enter, navigate, search, exit
# Enter:          ctrl-w [
# Page down:      ctrl-d
# Page up:        ctrl-u
# Scroll down:    j
# Scroll up:      k
# Search forward: /pattern  then n / N
# Exit:           ctrl-c

# Reference a specific window and pane to Claude Code in natural language:
# "Look at the server output in tmux window 9, pane 0"
# Claude Code will use: tmux capture-pane -t 9.0 -p
```

---

## Relevance to Claude Code Development

### Applications

- The interactive terminal workarounds rule at `.claude/rules/interactive-terminal-workarounds.md` already recommends tmux for PTY allocation and output capture — this guide validates and extends that practice specifically for Claude Code agent sessions
- The `tmux capture-pane -t mysession -p` pattern in the rules file is identical to the technique described in this post, confirming the approach as an established Claude Code workflow
- Running Claude Code inside tmux is the standard pattern for sessions that must survive SSH disconnection or terminal closure

### Patterns Worth Adopting

- **10,000-line capture buffer**: The `-S -10000` flag with `capture-pane` is a practical default for extracting full agent output without truncation — consistent with this repository's No Invented Limits principle
- **Pane-address references in prompts**: Instructing Claude Code to read "tmux 9.0" rather than copy-pasting server output reduces prompt size and keeps context fresh
- **Parallel agent windows**: Running subordinate agents in separate tmux windows that the primary Claude Code session can inspect and coordinate with is a lightweight multi-agent orchestration pattern requiring no framework

### Integration Opportunities

- Skills that spawn long-running processes (test runners, build servers, live-reload backends) can document their tmux window address so a Claude Code session in another window can monitor them without interrupting the process
- The `.claude/rules/interactive-terminal-workarounds.md` pattern for `tmux capture-pane -t mysession -p -e` can be referenced in agent prompts directly — agents already understand the syntax
- The control-key passthrough technique applies to any Claude Code skill that relies on terminal shortcuts that would otherwise be intercepted by the tmux prefix key

---

## References

- [Using tmux with Claude Code — hboon.com](https://hboon.com/using-tmux-with-claude-code/) (accessed 2026-03-01)
- [Auto-Renaming tmux Windows for AI Coding Agents — hboon.com](https://hboon.com/auto-renaming-tmux-windows-for-ai-coding-agents/) (accessed 2026-03-01)
- [tmux man page — official reference](https://man.openbsd.org/tmux) (accessed 2026-03-01)
- [Interactive Terminal Workarounds — .claude/rules/interactive-terminal-workarounds.md](./../../.claude/rules/interactive-terminal-workarounds.md) (accessed 2026-03-01)

---
