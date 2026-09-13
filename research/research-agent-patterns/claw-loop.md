---
name: The Claw Loop - Autonomous Development Orchestration Pattern
description: The Claw Loop is an autonomous development orchestration methodology where a supervisory AI agent ("Clawdbot") drives Claude Code through entire development sprints via tmux terminal sessions, with a...
license: Not specified (prompt-based methodology, not a software package)
metadata:
  topic: claw-loop
  category: research-agent-patterns
  source_url: https://github.com/claw-loop
  version: "2.0"
  verified: "2026-02-15"
  next_review: "2026-05-15"
---

## Overview

The Claw Loop is an autonomous development orchestration methodology where a supervisory AI agent ("Clawdbot") drives Claude Code through entire development sprints via tmux terminal sessions, with a cron job polling every 3 minutes to detect completion, stalls, crashes, and context limits. It implements a hierarchical multi-agent pattern (supervisor over worker) with automatic context clearing between phases, model switching per task type, and state-file-driven workflow progression across three supported methodologies (BMAD, GSD, Custom).

---

## Problem Addressed

| Problem | Claw Loop Solution |
|---------|--------------------|
| Claude Code finishes tasks and waits -- no autonomous chaining | Clawdbot detects completion and sends the next command automatically |
| Context limits cause stalls mid-sprint | Automatic detection of context exhaustion; `/clear` wipes context and next slash command reloads exactly what is needed |
| No visibility into autonomous progress | Status updates sent to phone every 3-minute cron cycle |
| Manual context management between steps wastes developer time | `/clear` between every major step ensures clean context; slash commands are self-contained |
| Crashes and rate limits require manual intervention | Fail-gracefully principle: crashes, rate limits, context exhaustion treated as expected events with automatic recovery |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Version | 2.0 | 2026-02-15 |
| Release Date | February 12, 2026 | 2026-02-15 |
| Author | Jordan Olsen | 2026-02-15 |
| Publisher | Don't Sleep On AI | 2026-02-15 |
| Type | Prompt-based methodology (not a software package) | 2026-02-15 |
| Supported Workflows | 3 (BMAD, GSD, Custom) | 2026-02-15 |
| Core Principles | 7 | 2026-02-15 |
| Cron Interval | 3 minutes | 2026-02-15 |
| Setup Questions | 5 | 2026-02-15 |
| Tagline | "One prompt. Autonomous development." | 2026-02-15 |

Note: No GitHub repository, npm package, or download statistics exist. The Claw Loop is a prompt/methodology distributed via the author's website, not a packaged software tool.

---

## Key Features

### 7 Core Principles (v2.0)

1. **Observe before acting** -- Always capture the tmux pane first before deciding what to do
2. **One action per cycle** -- Send one command or one response per cron fire
3. **CLEAR CONTEXT BETWEEN EVERY MAJOR STEP (CRITICAL)** -- Use `/clear` between phases to reset context window to 0%
4. **Text and Enter are always separate** -- tmux quirk requiring separate send-keys for text and Enter
5. **The state file is the source of truth** -- Not memory, not the pane; all workflow state lives in the state file
6. **Fail gracefully** -- Crashes, rate limits, context exhaustion are expected events, not exceptions
7. **Report everything** -- Break visibility and you break trust; status updates every cycle

### Workflow Integrations

| Workflow | Type | Cycle Pattern |
|----------|------|---------------|
| BMAD Method | Story-driven | create-story -> dev-story -> code-review -> next story |
| GSD (Get Shit Done) | Phase-based | discuss-phase -> plan-phase -> execute-phase -> verify-work -> next phase |
| Custom | User-defined | Any sequence of slash commands the user specifies |

### Context Management Strategy

**Why `/clear` instead of kill+restart (v2.0 change):**

- `/clear` achieves the same clean context as killing and restarting Claude Code
- `CLAUDE.md` and slash commands stay loaded after `/clear`
- No 8-second boot delay from restarting the process
- `/model` command continues to work in the same session
- Kill+restart reserved only for when Claude Code has actually crashed or exited

**Why context clearing matters:**

When Claude Code runs a slash command like `/bmad-bmm-dev-story`, the command contains everything Claude Code needs. But if the next command runs in the same session without clearing, the context window is 60-100% full of previous work. `/clear` wipes all history to 0%, and the next slash command fills the context with exactly what the new task requires.

### Model Switching Pattern

| Step | Model | Rationale |
|------|-------|-----------|
| create-story | Opus 4.6 | Deep reasoning required for architecture decisions |
| dev-story | Sonnet 4.5 | Fast execution for implementation work |
| code-review | Opus 4.6 | Deep analysis required for adversarial code review |

### Automatic Error Handling

The Claw Loop treats the following as expected operational events, not exceptions:

- **Crashes** -- Detected via tmux pane state; automatic restart
- **Rate limits** -- Wait and retry on next cron cycle
- **Context exhaustion** -- Detected and handled via `/clear`
- **Stalls** -- Detected when no progress between cron cycles; intervention triggered

---

## Technical Architecture

<eg>
┌──────────────────────────────────────────────────────────────────┐
│                     The Claw Loop (v2.0)                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Cron Job (every 3 min)                  │  │
│  │                          │                                 │  │
│  │                          v                                 │  │
│  │                   ┌─────────────┐                          │  │
│  │                   │  Clawdbot   │  (Supervisory AI Agent)  │  │
│  │                   │             │                          │  │
│  │                   │  1. Capture tmux pane                  │  │
│  │                   │  2. Read state file                    │  │
│  │                   │  3. Decide action                      │  │
│  │                   │  4. Send ONE command                   │  │
│  │                   │  5. Update state file                  │  │
│  │                   │  6. Send status update                 │  │
│  │                   └──────┬──────┘                          │  │
│  │                          │                                 │  │
│  │            tmux send-keys (text + Enter separately)        │  │
│  │                          │                                 │  │
│  │                          v                                 │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │            tmux Session                              │  │  │
│  │  │   Socket: ${TMPDIR}/clawdbot-tmux-sockets/           │  │  │
│  │  │           clawdbot.sock                              │  │  │
│  │  │                                                      │  │  │
│  │  │   ┌──────────────────────────────────────────────┐   │  │  │
│  │  │   │           Claude Code (Worker)               │   │  │  │
│  │  │   │                                              │   │  │  │
│  │  │   │   Executes slash commands:                   │   │  │  │
│  │  │   │   /bmad-bmm-create-story                     │   │  │  │
│  │  │   │   /bmad-bmm-dev-story                        │   │  │  │
│  │  │   │   /bmad-bmm-code-review                      │   │  │  │
│  │  │   │   /clear  (context reset between steps)      │   │  │  │
│  │  │   │   /model  (switch models between steps)      │   │  │  │
│  │  │   └──────────────────────────────────────────────┘   │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   State File (source of truth)             │  │
│  │                                                            │  │
│  │   - Current workflow step                                  │  │
│  │   - Progress indicator                                     │  │
│  │   - Error state                                            │  │
│  │   - Story/task queue                                       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Status Updates (every 3 min)                  │  │
│  │              -> Phone / Messaging Channel                  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
</eg>

### Cron Cycle Flow

<eg>
Cron fires (every 3 min)
    │
    v
Capture tmux pane content
    │
    v
Read state file
    │
    v
┌─────────────────────────┐
│   Evaluate pane state   │
│                         │
│   Completed? ──────> /clear + next command
│   Stalled?   ──────> Intervention
│   Crashed?   ──────> Kill + restart
│   Running?   ──────> Wait (do nothing)
│   Rate limit? ─────> Wait (retry next cycle)
│   Context full? ───> /clear + retry
└─────────────────────────┘
    │
    v
Update state file
    │
    v
Send status update to phone
    │
    v
Exit (wait for next cron fire)
</eg>

---

## Installation and Usage

### Setup Flow (5 Questions)

1. **What type of automation?** -- BMAD / GSD / Custom
2. **Where is your project?** -- Full filesystem path to project directory
3. **Where to send status updates?** -- Messaging channel or phone integration
4. **What is your story/task queue?** -- Story IDs (BMAD), phase numbers (GSD), or custom command list
5. **Do you have Claude Code installed?** -- Verification step

### Technical Requirements

- **Claude Code** installed and configured with project slash commands
- **tmux** available on the system
- **Cron** configured to fire every 3 minutes
- **Clawdbot** (supervisory AI agent) with access to tmux and state file
- **Messaging integration** for status updates (optional but recommended)

### tmux Socket Configuration

<eg>
Socket path: ${TMPDIR:-/tmp}/clawdbot-tmux-sockets/clawdbot.sock
</eg>

### BMAD Workflow Example

<eg>
1. Clawdbot sends: /bmad-bmm-create-story [story-id]
2. Claude Code executes story creation (Opus 4.6)
3. Clawdbot detects completion -> sends /clear
4. Clawdbot sends: /model sonnet
5. Clawdbot sends: /bmad-bmm-dev-story [story-id]
6. Claude Code executes development (Sonnet 4.5)
7. Clawdbot detects completion -> sends /clear
8. Clawdbot sends: /model opus
9. Clawdbot sends: /bmad-bmm-code-review [story-id]
10. Claude Code executes review (Opus 4.6)
11. Clawdbot detects completion -> sends /clear
12. Advance to next story in queue -> repeat from step 1
</eg>

---

## Relevance to Claude Code Development

### Applications

1. **Hierarchical Multi-Agent Pattern**: The Claw Loop demonstrates a production-tested supervisor-worker architecture where one AI agent orchestrates another through a terminal interface. This is distinct from in-process agent orchestration -- the supervisor operates entirely through the same interface a human would use (tmux send-keys), making it tool-agnostic and debuggable.

2. **Context Window as Managed Resource**: The methodology treats context window capacity as an explicitly managed resource rather than an implicit constraint. The mandatory `/clear` between every major step ensures each phase starts with maximum available context, filled precisely by the slash command's self-contained instructions.

3. **State File Over Memory**: By making the state file the single source of truth (not the AI's conversational memory), the pattern decouples workflow progress from any single AI session. This enables crash recovery, session restart, and audit trailing without information loss.

4. **Model Selection Per Task Type**: The explicit mapping of reasoning-heavy tasks to Opus and execution-heavy tasks to Sonnet demonstrates a practical cost/speed optimization pattern that could be formalized in any multi-step AI workflow.

### Patterns Worth Adopting

1. **One Action Per Cycle**: The discipline of sending exactly one command per observation cycle prevents race conditions and makes the system's behavior deterministic and debuggable. This principle applies to any polling-based orchestration.

2. **Observe Before Acting**: Capturing the terminal state before deciding what to do ensures decisions are based on actual system state rather than assumed state. This maps directly to the state-file pattern used in CI/CD and deployment systems.

3. **`/clear` as Context Management Primitive**: The insight that `/clear` is superior to kill+restart for context management (retains CLAUDE.md, slash commands, and session state while resetting conversational context) is directly applicable to any long-running Claude Code automation.

4. **Fail-Gracefully as Design Principle**: Treating crashes, rate limits, and context exhaustion as expected operational events rather than exceptional errors leads to more robust orchestration. The system does not need special error-handling code paths -- the normal observation cycle handles all failure modes.

5. **Separation of Text and Enter in tmux**: The tmux quirk requiring separate send-keys calls for text content and the Enter keystroke is a practical implementation detail that any tmux-based automation must account for.

### Integration Opportunities

1. **Claude Code Hook Integration**: The Claw Loop's cron-based polling pattern could be replaced or augmented with Claude Code hooks that fire on task completion, reducing the 3-minute polling latency to near-instant orchestration.

2. **State File Standardization**: The state file pattern could be standardized into a reusable schema for any multi-step Claude Code automation, enabling different supervisory agents to interoperate with shared workflow state.

3. **Workflow Method Library**: The three workflow integrations (BMAD, GSD, Custom) suggest a pattern where orchestration methods are pluggable. A library of workflow templates with standardized interfaces could enable users to define new orchestration patterns without modifying the core loop.

4. **Status Reporting Pipeline**: The mandatory status reporting after every cycle could be extended with structured logging, enabling analytics on sprint velocity, failure rates, and model efficiency across workflows.

### Considerations

1. **Prompt-Based Distribution**: The Claw Loop is a prompt/methodology, not packaged software. Users must configure cron, tmux, state files, and messaging integration manually. There is no installer, package manager entry, or version-locked dependency.

2. **Cron Polling Latency**: The 3-minute cron interval introduces up to 3 minutes of idle time between Claude Code completing a task and Clawdbot sending the next command. For short tasks, this overhead is significant.

3. **tmux Coupling**: The architecture is tightly coupled to tmux as the terminal multiplexer. Alternative terminal management approaches (screen, direct process management, API-based orchestration) are not supported.

4. **Single Worker Limitation**: The documented pattern supervises a single Claude Code instance. Scaling to multiple parallel workers would require multiple tmux sessions and state files, which is not addressed in the methodology.

5. **No License Specified**: The methodology has no explicit license. Users should verify usage terms with the author before commercial application.

---

## References

1. **The Claw Loop v2.0** - <https://www.dontsleeponai.com/claw-loop> (accessed 2026-02-15)
2. **Don't Sleep On AI (Publisher)** - <https://dontsleeponai.com> (accessed 2026-02-15)
3. **BMAD Method** - Referenced as story-driven workflow integration within the Claw Loop; methodology for create-story / dev-story / code-review cycles (accessed 2026-02-15 via [1])
4. **GSD (Get Shit Done) Method** - Referenced as phase-based workflow integration within the Claw Loop; methodology for discuss / plan / execute / verify cycles (accessed 2026-02-15 via [1])

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [octogent](../agent-frameworks/octogent.md) | agent-frameworks | referenced by octogent (agent-frameworks) |
| [AutoResearchClaw](../agent-infrastructure/AutoResearchClaw.md) | agent-infrastructure | referenced by AutoResearchClaw (agent-infrastructure) |
| [holyclaude](../agent-infrastructure/holyclaude.md) | agent-infrastructure | referenced by holyclaude (agent-infrastructure) |
| [oh-my-claudecode](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | referenced by oh-my-claudecode (agent-orchestration) |
| [claude-code-cli-power-patterns](../developer-tools/claude-code-cli-power-patterns.md) | developer-tools | referenced by claude-code-cli-power-patterns (developer-tools) |
| [no-mistakes](../developer-tools/no-mistakes.md) | developer-tools | referenced by no-mistakes (developer-tools) |
| [takt](./takt.md) | research-agent-patterns | referenced by takt (research-agent-patterns) |
