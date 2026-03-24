---
name: dot-dash
description: Start or manage the dot-dash live session dashboard
---

# dot-dash

Start the dot-dash server and open the browser dashboard.

## Usage

/dot-dash [start|stop|status|token]

## Commands

- `start` — Start the dot-dash server (port 7765 by default, set DOT_DASH_PORT to override)
- `stop` — Stop the running server
- `status` — Check if server is running and show active sessions
- `token` — Print the bearer token for dashboard access

## Setup

1. Start the server: run `bash plugins/dot-dash/scripts/start-server.sh`
2. Open browser at `http://localhost:7765` (or LAN IP)
3. Token is auto-generated at `~/.claude/dot-dash/token` on first start

## How it works

- SessionStart and SessionEnd hooks auto-register every Claude Code session
- Server tails `~/.claude/projects/*/*.jsonl` files and broadcasts events via WebSocket
- React dashboard shows all sessions with live transcripts
- UserPromptSubmit hook checks the injection queue before every user message
