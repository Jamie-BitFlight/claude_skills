---
name: kage-bunshin
description: 'Spawn and manage persistent interactive Claude Code CLI sessions with bidirectional communication via tmux. Provides spawn, send, read, status, list, and kill subcommands for orchestrating parallel peer sessions. Uses built-in --worktree and --tmux flags. Sessions stay alive for multi-turn steering. Triggers on "spawn claude session", "launch separate claude", "peer session", "inter-session communication", "shadow clone", "kage bunshin".'
---

# Kage Bunshin — Persistent Peer Claude Sessions

Spawn independent interactive `claude` CLI sessions in tmux with full bidirectional communication. The orchestrator can send messages, read responses, monitor status, and steer work mid-flight via `tmux send-keys` and `tmux capture-pane`.

This is NOT a subagent or teammate — it is an independent CLI process with its own context window, inheriting all MCP servers, skills, plugins, and agents from the project directory.

## Session Manager Script

All operations go through `${CLAUDE_SKILL_DIR}/scripts/spawn.py`:

```text
spawn.py --session-id ID spawn  --name X [--model MODEL] [--max-budget N] [--effort LEVEL] "prompt"
spawn.py --session-id ID send   --name X "message"
spawn.py --session-id ID read   --name X
spawn.py --session-id ID status --name X
spawn.py --session-id ID list
spawn.py --session-id ID stop   --name X     # graceful shutdown (Ctrl-C + wait)
spawn.py --session-id ID kill   --name X     # force kill (last resort)
```

The `--session-id` isolates each orchestrator's registry. Generate a UUID once per fleet and pass it on every call. Without it, defaults to `"default"`. Can also be set via `KB_SESSION_ID` environment variable.

## Quick Start

```bash
SPAWN="${CLAUDE_SKILL_DIR}/scripts/spawn.py"
SID=$(uuidgen)  # one UUID per fleet — isolates this orchestrator's registry

# 1. Spawn a session (interactive claude in tmux + worktree)
$SPAWN --session-id $SID spawn --name worker-42 --model haiku \
  "Load /dh:work-backlog-item #42. Execute the full work flow."

# 2. Check on it
$SPAWN --session-id $SID status --name worker-42

# 3. Read what's on screen
$SPAWN --session-id $SID read --name worker-42

# 4. Steer mid-flight
$SPAWN --session-id $SID send --name worker-42 \
  "Stop current work. Prioritize the auth module instead."

# 5. Graceful shutdown when done
$SPAWN --session-id $SID stop --name worker-42
```

## Session Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Spawning: spawn
    Spawning --> Idle: claude REPL initialized
    Idle --> Working: send (prompt delivered)
    Working --> Idle: claude finishes (❯ prompt returns)
    Working --> Working: send (steer mid-task)
    Idle --> Stopping: stop (sends Ctrl-C)
    Working --> Stopping: stop (sends Ctrl-C)
    Stopping --> Dead: session exits gracefully
    Stopping --> Dead: timeout → force kill
    Dead --> [*]: registry cleanup
    Idle --> Dead: crash
    Working --> Dead: crash
    note right of Stopping: Shutdown hooks run here
    note right of Dead: kill bypasses hooks — last resort only
```

**State detection via `read`:** The `❯` prompt at the last line of `capture-pane` output indicates Idle state. Absence of `❯` indicates Working state.

**Shutdown:** Use `stop` for graceful shutdown (Ctrl-C → poll for exit → fallback to force kill after 30s timeout). Use `kill` only for hung/unresponsive sessions — it bypasses shutdown hooks.

## How It Works

```mermaid
flowchart TD
    Start(["spawn called"]) --> Verify["Verify claude and tmux in PATH"]
    Verify --> Check{"Session name<br>already in registry?"}
    Check -->|"Alive"| Fail["Exit 1: kill it first"]
    Check -->|"Dead entry"| Clean["Remove stale entry"]
    Check -->|"Not found"| Launch
    Clean --> Launch["tmux new-session -d wrapping<br>claude --worktree {name} --tmux<br>--dangerously-skip-permissions --model {model}"]
    Launch --> Wait["Wait for claude REPL to initialize<br>(3 seconds)"]
    Wait --> Prompt["Send initial prompt via<br>tmux send-keys"]
    Prompt --> Submit["Press Enter to submit prompt<br>tmux send-keys Enter"]
    Submit --> Register["Save to registry.json"]
    Register --> Print["Print JSON record to stdout"]
```

The claude CLI's built-in `--worktree` creates a git worktree at `.claude/worktrees/{name}`. The built-in `--tmux` creates a tmux session named `{repo}_worktree-{name}`. The script wraps the launch in `tmux new-session -d` to provide the TTY that `--tmux` requires in headless environments.

**Verify prompt submission after spawn.** The script sends the initial prompt with Enter via `tmux send-keys`, but the REPL may not be fully initialized when the prompt arrives (race condition with the 3-second wait). After spawning, read the pane within 15 seconds. If `capture-pane` still shows the `❯` prompt with no tool use or response text below the prompt, the Enter was swallowed — resend it:

```bash
tmux send-keys -t {tmux_session} Enter
```

Retry up to 2 times (15s apart). If the session still shows `❯` with no activity after 2 retries, the session failed to initialize — kill it and re-spawn.

**Verify `send` delivery.** After sending a message, read the pane within 5 seconds. If `capture-pane` still shows `❯` with the sent text but no response in progress, the message was not submitted — resend with Enter: `tmux send-keys -t {tmux_session} Enter`. Retry once. If still no activity after the second Enter, the session is stuck — `stop` it and re-spawn.

**Permission prompts use cursor selection, not text input.** When the session shows a numbered menu (e.g., "1. Yes / 2. No"), send `Enter` to accept the highlighted option or arrow keys to change selection. Do NOT send "1" or "2" as text — the REPL uses a cursor-based selection widget.

## Subcommand Reference

### spawn

Launch a new persistent interactive claude session in tmux.

```bash
$SPAWN spawn --name my-session --model haiku "Your initial prompt"
$SPAWN spawn --name my-session --max-budget 5.00 "Your prompt"
```

**Flags:**

- `--name` — Session name (auto-derived from first 30 chars of prompt if omitted)
- `--model` — Model for the spawned session (default: sonnet)
- `--max-budget` — Maximum USD spend cap
- `--effort` — Effort level (low, medium, high, max) for reasoning depth. Injects CLAUDE_CODE_EFFORT_LEVEL into the child env.

**Output** (JSON to stdout):

```json
{
  "name": "worker-42",
  "tmux_session": "claude_skills_worktree-worker-42",
  "model": "haiku",
  "spawned_at": "2026-03-22T01:30:00+00:00",
  "worktree": true
}
```

Every session gets its own git worktree via the built-in `--worktree` flag. Configure `worktree.symlinkDirectories` in project settings to share `.venv`, `node_modules`, etc. across worktrees.

### send

Send a message to a running session via `tmux send-keys`.

```bash
$SPAWN send --name worker-42 "Check the test results and report back"
```

Types the message into the session's interactive REPL as if a human typed it. The session processes it as a new conversation turn. Use this to steer, redirect, or provide additional context.

### read

Read the current screen content from a session via `tmux capture-pane`.

```bash
$SPAWN read --name worker-42
```

Captures the last 200 lines of the tmux pane output. Shows the rendered conversation including prompts, responses, and tool use.

### status

Check session health.

```bash
$SPAWN status --name worker-42
```

Reports whether the tmux session is alive, the model, age, and tmux session name.

### list

List all registered sessions with live/dead status.

```bash
$SPAWN list
```

Prints a columnar table: NAME, MODEL, STATUS (alive/dead), AGE, TMUX_SESSION.

### stop

Graceful shutdown — sends Ctrl-C, waits for the session to exit, cleans up registry.

```bash
$SPAWN stop --name worker-42
```

Sends `C-c` to the claude REPL, then polls for up to 30 seconds. If the session exits within the timeout, shutdown hooks run and the session is persisted. If the timeout is exceeded, falls back to force kill.

Output: `{"status": "stopped", "name": "worker-42", "forced": false}`

### kill

Force-kill a session — last resort for hung/unresponsive sessions.

```bash
$SPAWN kill --name worker-42
```

Calls `tmux kill-session` directly. Bypasses shutdown hooks and session persistence. Use only when `stop` fails or the session is unresponsive.

## Session State

The registry is stored as one file per session under `~/.dh/projects/{slug}/kage-bunshin/sessions/{session-id}/{name}.json`. `list` and `status` aggregate by globbing that directory. The `{slug}` is derived from the git repo root path by replacing `/` with `-` (leading hyphen is intentional). Override the base directory with `DH_STATE_HOME` environment variable.

## Capability Inheritance

A spawned session inherits identical capabilities when launched from the same working directory:

```mermaid
flowchart LR
    CWD["Same working directory"] --> P1[".mcp.json — project MCP servers"]
    CWD --> P2["~/.claude.json — user/local MCP servers"]
    CWD --> P3[".claude/CLAUDE.md — project instructions"]
    CWD --> P4["~/.claude/plugins/cache/ — installed plugins"]
    CWD --> P5[".claude/skills/ — project skills"]
```

Flags that break inheritance — do not use:

- `--bare` — strips auto-discovery of CLAUDE.md, hooks, plugins, MCP
- `--strict-mcp-config` — overrides inherited MCP servers
- `--disable-slash-commands` — removes skill access

## Worktree Settings

Configure these in your project or user settings to share heavy directories across worktrees:

```json
{
  "worktree.symlinkDirectories": [".venv", "node_modules", ".cache"]
}
```

## Parallel Fleet Management

Spawn and control multiple coordinators simultaneously. Each returns immediately.

```bash
SPAWN="${CLAUDE_SKILL_DIR}/scripts/spawn.py"
SID=$(uuidgen)
ITEMS=(10 11 12 13 14 15 16 17 18 19)

# Spawn all coordinators
for ITEM in "${ITEMS[@]}"; do
  $SPAWN --session-id $SID spawn --name "coord-${ITEM}" --model haiku \
    "Load /dh:work-backlog-item #${ITEM}. Execute the full work flow."
done

# Dashboard
$SPAWN --session-id $SID list

# Steer one mid-flight
$SPAWN --session-id $SID send --name coord-14 \
  "Deprioritize the UI work. Focus on the API contract first."

# Read what a coordinator is showing
$SPAWN --session-id $SID read --name coord-12

# Shut down the fleet
for ITEM in "${ITEMS[@]}"; do
  $SPAWN --session-id $SID stop --name "coord-${ITEM}"
done
```

### Model Selection

The `--model` flag controls the spawned session's orchestrator model. Each sub-agent spawned inside the session uses its own model per its agent frontmatter definition.

Use `--model haiku` for coordinator sessions that dispatch work to sub-agents — haiku is fast and cheap as an orchestrator. Use `--model sonnet` for sessions doing technical implementation work.

## Milestone Dispatch Patterns

Used by `/groom-milestone` and `/work-milestone` to spawn parallel kage-bunshin workers.

### Groom Dispatch

```bash
SPAWN="${CLAUDE_SKILL_DIR}/scripts/spawn.py"
SID=$(uuidgen)

for ISSUE in "${UNGROOMED_ISSUES[@]}"; do
  $SPAWN --session-id $SID spawn --name "groom-${ISSUE}" --model haiku \
    "Load /dh:groom-backlog-item #${ISSUE}. Execute the full grooming flow."
done

$SPAWN --session-id $SID list
$SPAWN --session-id $SID read --name "groom-42"

# Clean up after wave
for ISSUE in "${UNGROOMED_ISSUES[@]}"; do
  $SPAWN --session-id $SID stop --name "groom-${ISSUE}"
done
```

### Work Dispatch

```bash
SPAWN="${CLAUDE_SKILL_DIR}/scripts/spawn.py"
SID=$(uuidgen)

for ISSUE in "${WAVE_ISSUES[@]}"; do
  $SPAWN --session-id $SID spawn --name "work-${ISSUE}" --model haiku \
    "Load /dh:work-backlog-item #${ISSUE}. Execute the full work flow."
done

$SPAWN --session-id $SID list

# Steer if needed
$SPAWN --session-id $SID send --name "work-42" \
  "The auth module has a dependency on #43. Coordinate accordingly."

# Clean up after wave
for ISSUE in "${WAVE_ISSUES[@]}"; do
  $SPAWN --session-id $SID stop --name "work-${ISSUE}"
done
```

## Monitoring spawned sessions

After spawning one or more sessions, the orchestrator SHOULD spawn a background Haiku subagent to watch for interactive states that require a response — permission approvals, Y/n prompts, and `AskUserQuestion` events. Without a monitor, these states block the child session silently until the orchestrator happens to `read` the pane.

The monitor is `${CLAUDE_SKILL_DIR}/scripts/monitor.py`. It has two subcommands: `poll` (watch sessions, emit JSON on completion or intervention) and `health` (snapshot team state, exit immediately). All monitoring uses `poll`; team inspection uses `health`.

### Spawning the monitor — choose based on what you need

**Option A — Background bash (passive wait, no intervention needed)**

Use when all sessions were spawned with `--dangerously-skip-permissions` (bypass mode). In bypass mode, no permission prompts can occur, so passive notification on completion or timeout is sufficient. Zero LLM tokens.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" poll \
  --session-id <SID> --interval 15 --timeout 1800 \
  > /tmp/monitor-<SID>.json 2>&1
```

Pass `run_in_background: true` to the Bash tool. When notified, read `/tmp/monitor-<SID>.json` for the JSON result.

**Option B — Background agent (intervention-capable)**

Use when sessions may hit permission prompts, Y/n gates, or `AskUserQuestion` events that require a response back into the tmux pane. The agent can relay the content and the orchestrator can act.

```text
Task — model: haiku, run_in_background: true

Prompt:
  Run: uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" poll \
         --session-id <SID> --interval 5

  Wait for the script to exit and read its JSON output.

  If status == "intervention_needed": return the session name, type, and content.
  If status == "all_complete" or "timeout": return that status and the active_sessions list (if present).
  If status == "error": return the error message.
```

**Decision rule:**

| Sessions running with... | Use |
|---|---|
| `--dangerously-skip-permissions` (bypass mode) | Option A — bash |
| Default permissions (prompts expected) | Option B — agent |
| Unknown / mixed | Option B — agent |

Replace `<SID>` with the same UUID passed to `spawn.py`.

### Monitoring lifecycle

```mermaid
flowchart TD
    Spawn(["Orchestrator spawns sessions"]) --> Q0{Permissions bypassed?}
    Q0 -->|"Yes — skip-permissions"| BashMon["Option A: Bash run_in_background\nmonitor.py > /tmp/out.json"]
    Q0 -->|"No — prompts expected"| AgentMon["Option B: Agent haiku run_in_background\nmonitor.py → relay result"]
    BashMon --> Poll["monitor.py polls tmux panes\nevery --interval seconds"]
    AgentMon --> Poll
    Poll --> Q{Detected?}
    Q -->|"intervention_needed"| Intervene["Orchestrator receives\nsession, type, content\nReads pane, responds via send"]
    Q -->|"all_complete"| StopFleet["Orchestrator calls stop\nfor each session in fleet"]
    StopFleet --> Done(["Fleet stopped — cleanup complete"])
    Q -->|"timeout"| Check{"active_sessions empty?"}
    Check -->|"Yes — all dead"| Done
    Check -->|"No — sessions still running"| ReadPanes["Orchestrator reads each active pane\nto determine state manually"]
    ReadPanes --> Decide{"Intervention\nneeded?"}
    Decide -->|"Yes"| Intervene
    Decide -->|"No — working normally"| Respawn
    Intervene --> Respawn["Orchestrator re-spawns monitor\n--timeout 1800 to continue watching"]
    Respawn --> Poll
```

The monitor exits immediately on first detection — it does not continue watching after reporting. Re-spawn it after handling an intervention to resume coverage.

**On `all_complete`:** Call `stop` for every session in the fleet before continuing. Sessions left running after their task completes hold git worktrees open and consume tmux resources.

**On `timeout`:** Read each active pane with `spawn.py read`. If sessions are working normally (no `❯` prompt, tool use visible), re-spawn the monitor with `--timeout 1800`. If any session shows `❯` with unexpected content, read and act before re-spawning.

### CLI flags

- `--session-id ID` (required) — resolves `registry-<ID>.json`; must match the `--session-id` used with `spawn.py`
- `--state-dir PATH` — base state directory; defaults to `~/.dh/projects/<git-slug>/`; override via `DH_STATE_HOME` env var
- `--interval SECONDS` — seconds between polls; default 5
- `--timeout SECONDS` — maximum seconds before emitting `timeout`; default 300

### JSON output statuses

- `{"status": "intervention_needed", "session": "<tmux-session-name>", "type": "<type>", "content": "<last 10 pane lines>"}` — a session needs a response; `type` is one of `permission_approval`, `yes_no_prompt`, or `question`
- `{"status": "all_complete"}` — all registered sessions have exited
- `{"status": "timeout", "active_sessions": ["<name>", ...]}` — timeout elapsed; sessions listed are still running
- `{"status": "error", "message": "<description>"}` — fatal error (registry missing, git not available); exit code 1

## Team Health Check

Inspect a running Claude Code agent team's live state — last JSONL tool calls per member and current tmux pane snapshot. Use this after spawning a team via `TeamCreate` to see what teammates are doing without waiting for message delivery.

**Script**: `${CLAUDE_SKILL_DIR}/scripts/monitor.py health`

```bash
# Most recently modified team
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health

# Specific team by name
uv run "${CLAUDE_SKILL_DIR}/scripts/monitor.py" health {team-name}
```

### Team name discovery

Team names come from `~/.claude/teams/` — each subdirectory is a team. The script defaults to the most recently modified team (by `config.json` mtime). Pass an explicit name to target a specific team.

### Output per member

For each team member the script prints:

- **name** and **agentType** from the team config
- **Last 5 JSONL tool calls**: timestamp, tool name, and first 60 characters of input — drawn from the member's session file
- **tmux pane snapshot**: full visible content of the member's assigned tmux pane

### Session file lookup

JSONL session files are searched under `~/.claude/projects/{project-slug}/` (derived from the current git repository root). For each member, the script reads the first 3 KB of each candidate `.jsonl` file and picks the one where the member's `name` OR `agentId` (`{name}@{team-name}`) appears earliest. The team-lead session is resolved directly from `leadSessionId` in the team config.

### When to use

Call `monitor.py health` after spawning a team to verify agents are progressing. Unlike the poll-based monitor, this subcommand exits immediately after printing — it is a snapshot tool, not a watcher.

For other skills that want to reference this capability: load the `/dh:kage-bunshin` skill and invoke `monitor.py health {team-name}`.

## Reference

See [./references/stream-json-protocol.md](./references/stream-json-protocol.md) for the stream-json output event type catalog and raw experiment data from earlier protocol exploration.
