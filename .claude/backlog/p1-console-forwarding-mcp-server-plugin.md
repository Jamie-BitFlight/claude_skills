---
name: Console Forwarding MCP Server Plugin
description: "Create a new plugin with a FastMCP server that enables Claude Code sessions to communicate with other Claude sessions locally (via dtach/tmux) and on remote hosts (via SSH). The server should allow monitoring of long-running multi-agent sessions, reading terminal output, sending commands, and coordinating across sessions.\n\nReferences:\n- ./research/developer-tools/dtach.md — minimal detach/reattach for long-running sessions\n- ./research/developer-tools/tabz-browser-console-forwarder.md — browser console to terminal forwarding pattern\n- ./research/developer-tools/using-tmux-with-claude-code.md — tmux + Claude Code workflow patterns\n- ./research/developer-tools/psmux.md — Windows tmux replacement (Rust) with drop-in compatibility\n- ./research/developer-tools/shpool.md — shell session pool with detach/reattach and daemon mode\n- ./research/developer-tools/byobu.md — enhanced tmux/screen wrapper with 40+ status bar plugins and F-key layer\n- ./research/developer-tools/tmuxp.md — Python tmux session manager with YAML/JSON workspace configs and plugin hooks\n- ./research/developer-tools/libtmux.md — typed Python API for tmux: Server/Session/Window/Pane dataclasses with send_keys and capture_pane\n- ./research/async-libraries/asyncssh.md — asyncio-native SSH with reverse tunnels, SFTP, jump-host chaining, pure-Python keys\n- ./research/research-agent-patterns/gastown.md — Gas Town multi-agent workspace manager with tmux, Dolt, witness zombie detection, convoy tracking\n- /fastmcp-creator skill for MCP server implementation"
metadata:
  topic: console-forwarding-mcp-server-plugin
  source: User request
  added: '2026-03-01'
  priority: P1
  type: Feature
  status: in-progress
  issue: '#364'
  last_synced: '2026-03-12T12:48:29Z'
  groomed: '2026-03-01'
  plan: plan/tasks-14-console-forwarding-mcp-server-plugin.md
---

## Story

As a **developer**, I want **Create a new plugin with a FastMCP server that enables Claude Code sessions t...** so that **backlog items are tracked in GitHub**.

## Description

Create a new plugin with a FastMCP server that enables Claude Code sessions to communicate with other Claude sessions locally (via dtach/tmux) and on remote hosts (via SSH). The server should allow monitoring of long-running multi-agent sessions, reading terminal output, sending commands, and coordinating across sessions.

References:
- ./research/developer-tools/dtach.md — minimal detach/reattach for long-running sessions
- ./research/developer-tools/tabz-browser-console-forwarder.md — browser console to terminal forwarding pattern
- ./research/developer-tools/using-tmux-with-claude-code.md — tmux + Claude Code workflow patterns
- ./research/developer-tools/psmux.md — Windows tmux replacement (Rust) with drop-in compatibility
- ./research/developer-tools/shpool.md — shell session pool with detach/reattach and daemon mode
- ./research/developer-tools/byobu.md — enhanced tmux/screen wrapper with 40+ status bar plugins and F-key layer
- ./research/developer-tools/tmuxp.md — Python tmux session manager with YAML/JSON workspace configs and plugin hooks
- ./research/developer-tools/libtmux.md — typed Python API for tmux: Server/Session/Window/Pane dataclasses with send_keys and capture_pane
- ./research/async-libraries/asyncssh.md — asyncio-native SSH with reverse tunnels, SFTP, jump-host chaining, pure-Python keys
- ./research/research-agent-patterns/gastown.md — Gas Town multi-agent workspace manager with tmux, Dolt, witness zombie detection, convoy tracking
- /fastmcp-creator skill for MCP server implementation

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None

## Fact-Check

**Date**: 2026-03-01
**Claims checked**: 5
**VERIFIED**: 3 | **PARTIALLY VERIFIED**: 2 | **REFUTED**: 0

1. **dtach: minimal detach/reattach via Unix sockets** — VERIFIED
   Sources: GitHub crigler/dtach, Linux Command Library man page, Void Linux docs (accessed 2026-03-01)

2. **FastMCP: creates MCP server plugins for Claude Code** — VERIFIED
   Sources: gofastmcp.com, gofastmcp.com/integrations/claude-code, PrefectHQ/fastmcp GitHub (accessed 2026-03-01)

3. **asyncssh: asyncio-native SSH with reverse tunnels, SFTP, jump-host chaining** — VERIFIED
   Sources: asyncssh.readthedocs.io, ronf/asyncssh GitHub, PyPI (accessed 2026-03-01)
   Note: "pure-Python keys" claim REFUTED — current versions (2.0+) depend on PyCA/cryptography (C-based). Earlier versions had pure-Python crypto but were replaced for performance. Core capabilities (async, reverse tunnels, SFTP, jump-host) all confirmed.

4. **libtmux: typed Python API with send_keys/capture_pane** — VERIFIED
   Sources: libtmux.git-pull.com, tmux-python/libtmux source code (accessed 2026-03-01)
   Note: Server class is NOT a dataclass (traditional class with mixins). Session, Window, Pane ARE @dataclasses.dataclass(). send_keys() on Pane and capture_pane() on Pane both confirmed in source.

5. **gastown: multi-agent workspace manager with tmux** — VERIFIED (from research entry, 10.7K stars, uses tmux session transport)

## RT-ICA

**Goal**: Create a FastMCP plugin that enables Claude Code sessions to communicate with other sessions locally (tmux/dtach) and remotely (SSH), enabling monitoring, output capture, command sending, and coordination.

**Decision**: APPROVED

**Conditions**:
1. FastMCP framework supports MCP server creation with Claude Code integration | AVAILABLE | Verified via gofastmcp.com/integrations/claude-code
2. libtmux provides programmatic tmux control (send_keys, capture_pane) | AVAILABLE | Verified: Pane.send_keys(), Pane.capture_pane() in source
3. asyncssh provides asyncio-native SSH for remote session access | AVAILABLE | Verified: reverse tunnels, SFTP, jump-host chaining confirmed
4. dtach available as lightweight alternative to tmux for session detach | AVAILABLE | Verified: Unix socket-based, minimal binary
5. Existing plugin pattern available for reference | AVAILABLE | agentskill-kaizen plugin has FastMCP MCP server (mcp/server.py) with plugin.json mcpServers declaration
6. Research entries covering terminal multiplexing, SSH, multi-agent patterns | AVAILABLE | 11 research entries in research/ directory
7. Plugin structure conventions (plugin.json, agents/, skills/, mcp/) | AVAILABLE | Observed in agentskill-kaizen, fastmcp-creator plugins
8. tmux available in runtime environment | DERIVABLE | Assumed available on Linux — verify at runtime
9. SSH key configuration for remote access | DERIVABLE | User-provided at runtime, not needed at build time

**Assumptions to confirm**:
- tmux is installed in target runtime environments
- Users will provide SSH credentials/keys for remote sessions

## Groomed (2026-03-01)

### Problem Space: Orchestrator Observability

AI orchestrators (e.g., Claude Code running `/implement-feature`) managing parallel agent sessions face five critical gaps:

1. **Blind between spawn and return** — zero visibility into agent progress until completion; no heartbeat, no elapsed time, no progress estimation
2. **No inter-agent communication** — agents are fire-and-forget; no way to signal dependent agents when assumptions change
3. **No runtime routing intelligence** — task routing uses static metadata; no real-time signal for agent struggle, stuck loops, or early failure
4. **Unstructured output** — agents return text blobs; orchestrators need structured status (files changed, decisions made, blockers hit)
5. **No failure recovery** — only retry-from-scratch or ask-the-user; no partial work preservation, failure taxonomy, or cascading failure detection

Console forwarding solves these by giving orchestrators real-time terminal access to agent sessions — enabling monitoring, intervention, and informed recovery decisions.

Full analysis: [plan/feature-context-console-forwarding-mcp-server-plugin.md](./../../plan/feature-context-console-forwarding-mcp-server-plugin.md) § "Problem Space: Orchestrator Observability Gaps"

### Expected Behavior

A FastMCP server runs as a plugin, exposing tools that enable Claude Code sessions to:
- Monitor and read output from other Claude Code sessions running locally in tmux/dtach or on remote hosts via SSH
- Send commands and keystrokes to remote or local sessions
- Query session metadata (status, pane dimensions, active window)
- Detect stuck/hung/zombie agent sessions via health checks
- Coordinate work across multiple sessions by reading/writing shared state over SSH tunnels

The server communicates via MCP standard tools; Claude Code clients load it via plugin.json mcpServers declaration. The primary consumer is AI orchestrators managing parallel agent fleets, not just human developers.

### Desired Structure

plugins/console-forwarding/
- .claude-plugin/plugin.json (mcpServers declaration)
- mcp/server.py (FastMCP server with PEP 723 inline script metadata)
- mcp/backends/tmux_backend.py (libtmux-based local session control)
- mcp/backends/dtach_backend.py (dtach-based local detach/reattach)
- mcp/backends/ssh_backend.py (asyncssh-based remote session access)
- mcp/session_manager.py (abstraction over backends, session registry)
- skills/console-forwarder/SKILL.md (user-facing skill)
- tests/ (pytest tests for MCP tools)
- README.md

### Acceptance Criteria

1. FastMCP server runs via uv run plugins/console-forwarding/mcp/server.py with no external daemon dependencies
2. plugin.json declares the server; Claude Code can load it and call MCP tools immediately
3. MCP tools expose: list_sessions, capture_pane, send_keys, get_session_info, check_session_health
4. source parameter accepts tmux session names and SSH URIs (ssh://user@host/session)
5. Local tmux sessions auto-discovered; remote sessions queried over SSH with key-based auth
6. capture_pane supports `lines` + `offset` pagination for orchestrator polling patterns
7. check_session_health returns status enum (Healthy, Idle, Hung, Zombie, Missing) using inactivity timeout + process liveness
8. capture_pane and list_sessions are read-only; send_keys marked destructive hint
9. No blocking I/O; all operations use asyncio with configurable timeouts
10. Unit tests cover tmux pane capture, SSH key loading, remote command execution, health check states
11. SKILL.md documents session naming conventions, SSH setup, troubleshooting, and orchestrator integration patterns

### Resources

- research/developer-tools/libtmux.md - typed Python API for tmux
- research/developer-tools/dtach.md - minimal detach/reattach utility
- research/async-libraries/asyncssh.md - async SSH client/server
- research/developer-tools/using-tmux-with-claude-code.md - tmux workflow patterns
- research/research-agent-patterns/gastown.md - multi-agent session coordination
- research/developer-tools/tabz-browser-console-forwarder.md - console output forwarding pattern
- plugins/agentskill-kaizen/mcp/server.py - FastMCP server implementation reference
- plugins/agentskill-kaizen/.claude-plugin/plugin.json - plugin declaration pattern

### Dependencies

- fastmcp>=3.0.0 (MIT, PrefectHQ/fastmcp)
- libtmux>=0.53.1 (MIT, zero runtime deps, requires tmux>=3.2a)
- asyncssh>=2.22.0 (EPL-2.0/GPL-2.0, requires PyCA/cryptography)

### Effort

Medium - Three backends (tmux, dtach, SSH) with async I/O, session abstraction, MCP tool definitions, and test coverage. Libraries are mature; primary work in integration layer.

### Priority

9/10 - Enables cross-session monitoring and remote agent orchestration. Unblocks dashboards and multi-agent coordination.
