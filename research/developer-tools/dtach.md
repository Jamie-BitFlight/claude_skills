---
title: "dtach"
research_date: "2026-03-01"
source_url: "https://github.com/crigler/dtach"
github_url: "https://github.com/crigler/dtach"
version_at_research: "v0.9"
license: "GNU General Public License v2.0"
last_verified: "2026-03-01"
version_at_verification: "v0.9"
next_review: "2026-06-01"
---

## Overview

dtach is a minimal C program that emulates only the detach feature of GNU screen, allowing a process to run in a pseudo-terminal that is disassociated from the controlling terminal. Unlike screen or tmux, dtach has no terminal emulation layer and passes the raw output stream of the managed program directly to attached terminals. Its primary value is small binary size, auditability, and transparent operation for AI agent workflows and remote sessions that must survive terminal disconnection.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Long-running agent processes die when SSH connection drops | dtach wraps the process in a master daemon tied to a Unix-domain socket, not the terminal; the process survives disconnection |
| screen/tmux impose terminal emulation that corrupts full-screen applications | dtach has no terminal emulation layer; it passes the raw byte stream between program and terminal |
| screen/tmux are too large and complex to audit for embedded or rescue environments | dtach compiles to a tiny binary (~20 KB), with ~1,000 lines of C across three source files |
| Multiple terminals need to share one running process | Multiple dtach instances can attach to the same session socket simultaneously |
| Sending scripted input to a detached session | `dtach -p <socket>` pipes stdin directly into the running session |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 619 | 2026-03-01 |
| GitHub Forks | 61 | 2026-03-01 |
| Contributors | 6 | 2026-03-01 |
| Open Issues | 17 | 2026-03-01 |
| Latest Tag | v0.9 | 2026-03-01 |
| Last Commit | 2025-06-20 | 2026-03-01 |
| Language | C | 2026-03-01 |
| License | GPL-2.0 | 2026-03-01 |

No formal releases exist on GitHub; the sole tagged version is v0.9, corresponding to the man page date of May 2016. Active maintenance continues, with whitespace and style commits as recently as June 2025.

---

## Key Features

### Session Management via Unix-Domain Sockets

- Each session is represented by a Unix-domain socket path in the filesystem, specified by the user
- Filesystem permissions are the only access control: no passwords, no usernames
- The executable bit on the socket is set when clients are attached and cleared when all clients detach, providing a visible attached/detached state indicator
- Stale sockets from crashed sessions are automatically detected and removed by `dtach -A`

### Attach and Create Modes

- `-c <socket> <cmd>` — create a new session and attach to it immediately
- `-A <socket> <cmd>` — attach to an existing session or create one if absent (most common mode)
- `-n <socket> <cmd>` — create a session and daemonize without attaching (fire-and-forget)
- `-N <socket> <cmd>` — create a session without attaching but stay in the foreground until program exits
- `-a <socket>` — attach to an existing session only; exits if socket does not exist
- `-p <socket>` — pipe stdin into a running session without a detach character scan

### No Terminal Emulation

- dtach passes raw bytes between the managed program and attached terminals
- There is no screen buffer, no virtual terminal, and no scrollback
- Screen redraws on attach use one of three configurable methods: `ctrl_l` (sends Ctrl-L to program), `winch` (sends SIGWINCH), or `none`
- This transparency makes it compatible with any full-screen application: editors, debuggers, REPLs, AI agent shells

### Detach and Suspend Controls

- Default detach character: `^\` (Ctrl-Backslash); configurable with `-e <char>`
- Detach character can be disabled entirely with `-E` (useful for sessions that receive binary input)
- Suspend key (`Ctrl-Z`) suspends only the attaching dtach client, not the managed program; disable with `-z` to pass through to the program

### Input Piping for Automation

- `dtach -p <socket>` connects to a running session and writes stdin verbatim, then exits
- Control characters (newlines, escape sequences) are sent as-is; no detach scanning is performed
- Enables scripted interactions with long-running processes: `echo 'command\n' | dtach -p /tmp/session`

---

## Technical Architecture

dtach is structured as three C source files and a shared header:

- `main.c` — argument parsing, mode dispatch, signal and terminal setup
- `master.c` — the daemon process that manages the PTY master, the session socket, and relays data between attached clients and the program
- `attach.c` — the client process that connects to the session socket, handles terminal raw mode, forwards keystrokes, and processes detach/suspend characters

The communication model:

```text
User terminal  <-->  attach process  <-->  Unix-domain socket  <-->  master daemon  <-->  PTY master
                                                                                              |
                                                                                         program (PTY slave)
```

On session creation, the master process forks via `forkpty()`, which allocates a pseudo-terminal pair. The child executes the target program with the PTY slave as its controlling terminal. The master daemon then listens on the socket for attaching clients and uses `select()` to multiplex I/O between all clients and the PTY master.

When all clients detach, the program continues running. When a new client attaches, the master sends a redraw trigger (configurable) and begins forwarding output.

The master process runs as a background daemon; it is not tied to any terminal. The only relationship between the process and the filesystem is the socket path.

Build system: autoconf/automake. Dependencies: POSIX `termios`, `forkpty` (from `util.h` on Linux, `libutil` on BSD). No third-party libraries.

---

## Installation & Usage

```bash
# Build from source
./configure
make
sudo make install
```

```bash
# Available in most Linux distributions
# Debian/Ubuntu
sudo apt-get install dtach

# Arch Linux
sudo pacman -S dtach

# macOS via Homebrew
brew install dtach
```

```bash
# Create a new session running bash, attach immediately
dtach -c /tmp/my-session bash

# Attach or create (most common invocation)
dtach -A /tmp/my-session bash

# Create session without attaching (fire-and-forget daemon)
dtach -n /tmp/agent-session ./run-agent.sh

# Reattach to an existing session
dtach -a /tmp/my-session

# Detach from session (inside attached terminal)
# Press: Ctrl-\  (default detach character)

# Disable detach character and suspend passthrough for binary-safe sessions
dtach -c /tmp/session -Ez bash

# Pipe commands into a running session
echo -e 'ls -la\n' | dtach -p /tmp/my-session

# Attach with winch redraw method for programs that use SIGWINCH
dtach -a /tmp/my-session -r winch

# Change detach character to Ctrl-A
dtach -a /tmp/my-session -e '^A'
```

---

## Relevance to Claude Code Development

### Applications

- AI agent processes spawned via Claude Code can be wrapped in dtach sessions, ensuring they survive SSH disconnection or terminal closure
- The `-n` mode allows launching agent background workers that run independently of the invoking terminal
- The `-p` mode provides a mechanism to inject commands or data into a running agent session from scripts or orchestrators without a full attach cycle
- Relevant to the Interactive Terminal Workarounds rule in `.claude/rules/interactive-terminal-workarounds.md`: dtach satisfies the PTY requirement that many terminal-dependent tools impose, without the overhead of tmux session management

### Patterns Worth Adopting

- The socket-as-session-identifier pattern is a clean, filesystem-visible way to track running processes; each socket path is an explicit, inspectable artifact
- The executable-bit-as-attachment-indicator is a low-overhead way to expose session state to monitoring scripts without an IPC query
- The separation between session creation (`-n`) and later attachment (`-a`) maps well to orchestrator-worker patterns where the orchestrator starts work and observers attach asynchronously

### Integration Opportunities

- Wrap long-running Claude Code agent loops: `dtach -n /tmp/claude-agent-$(date +%s) ./run-agent.sh`
- Use `dtach -p` in CI/CD or agent orchestration pipelines to feed input into an already-running interactive tool
- Combine with the tmux-based PTY pattern from `.claude/rules/interactive-terminal-workarounds.md` as a lighter alternative when only detach (not capture-pane) is needed
- Could replace ad-hoc `nohup` or `&` background invocations in skill scripts where reattachability is valuable

---

## References

- [dtach GitHub repository — crigler/dtach](https://github.com/crigler/dtach) (accessed 2026-03-01)
- [dtach README — primary documentation](https://github.com/crigler/dtach/blob/master/README) (accessed 2026-03-01)
- [dtach man page — dtach.1](https://github.com/crigler/dtach/blob/master/dtach.1) (accessed 2026-03-01)
- [dtach main.c — architecture reference](https://github.com/crigler/dtach/blob/master/main.c) (accessed 2026-03-01)
- [GitHub API — repo metadata](https://api.github.com/repos/crigler/dtach) (accessed 2026-03-01)

---
