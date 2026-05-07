# Gas Town (gastown)

**Research Date**: 2026-03-01
**Source URL**: <https://github.com/steveyegge/gastown>
**GitHub Repository**: <https://github.com/steveyegge/gastown>
**Version at Research**: v0.9.0
**License**: MIT

---

## Overview

Gas Town is a multi-agent workspace manager built by Steve Yegge that coordinates large fleets of Claude Code agents (comfortably scaling to 20-30+ agents) with persistent work state. The system uses tmux as the session transport layer, git worktrees as isolated agent sandboxes, Dolt SQL (a MySQL-compatible version-controlled database) as the work ledger, and a novel role taxonomy (Mayor, Witness, Polecat, Refinery, Deacon) to orchestrate autonomous end-to-end software development workflows. Work items are called "beads" and workflows are called "molecules" or "formulas" — TOML-defined DAGs that agents execute step-by-step with dependency tracking and parallel execution support.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Agents lose context on restart | All work state persists in git-backed Dolt database; `gt prime` reinjects full context at session start |
| Manual coordination of 4-10+ agents becomes chaotic | Mayor role + Convoy work-tracking units provide visibility across all rigs from a single interface |
| Zombie sessions: tmux alive but Claude process dead | ZFC (Zero-state-File Compliance) principle: tmux session IS the source of truth; Witness cross-references tmux session health against agent bead state every patrol cycle |
| Work state lost when agent dies mid-task | Molecules (chained bead workflows) are durable; Witness detects stalled/zombie polecats and respawns sessions, preserving the existing git worktree and branch |
| No attribution or audit trail for AI-generated code | Every action attributed to a named agent identity; CV chains track work history per agent across all assignments |
| Sequential agent spawning limits throughput | Convoy formula supports parallel "legs" with a synthesis step; polecats run in isolated git worktrees that enable concurrent branches without conflict |
| Context window exhaustion kills long-running work | Handoff protocol: polecat voluntarily cycles session, new session re-primes from persistent bead state; session death is normal operation, not failure |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 10,665 | 2026-03-01 |
| Forks | 844 | 2026-03-01 |
| Contributors | 150 (page count from API response Link header page=150) | 2026-03-01 |
| Open Issues | 101 | 2026-03-01 |
| Latest Release | v0.9.0 | 2026-03-01 |
| Primary Language | Go | 2026-03-01 |
| Created | 2025-12-16 | 2026-03-01 |

SOURCE: [GitHub API repos/steveyegge/gastown](https://api.github.com/repos/steveyegge/gastown) (accessed 2026-03-01)

---

## Key Features

### tmux-Based Session Management

- Every agent role (Mayor, Witness, Polecat, Refinery, Deacon) runs as a named tmux session within a dedicated socket scoped to the current town workspace
- Session names follow a prefix convention: `hq-mayor`, `hq-deacon`, `gt-witness`, `gt-polecat-<name>` etc.
- `gt cycle next/prev` (bound to `C-b n/p`) cycles between sessions within a logical group (crew, rig ops, town) — not across unrelated sessions
- `gt feed` launches a three-panel Bubble Tea TUI: Agent Tree (hierarchical by rig/role), Convoy Panel (in-progress work), Event Stream (chronological activity feed)
- Dashboard (`gt dashboard`) serves an HTMX-based web UI with auto-refresh for workspace-wide visibility from a browser
- Session health detection distinguishes four states: SessionHealthy, SessionZombie (tmux alive, Claude dead), SessionHung (Claude alive but no output in maxInactivity period), SessionMissing

SOURCE: [gastown/internal/tmux/tmux.go](https://github.com/steveyegge/gastown/blob/main/internal/tmux/tmux.go) (accessed 2026-03-01)

### ZFC (Zero-state-File Compliance) Principle

- Architectural constraint: no state is stored in PID files, lock files, or on-disk state files for session liveness tracking
- tmux session existence IS the sole source of truth for whether an agent is running
- Witness `IsRunning()` queries `tmux has-session` then cross-checks `IsAgentAlive()` (verifies Claude process inside the session) to distinguish healthy from zombie
- `IsHealthy()` adds a third check: whether the session produced output within `maxInactivity` duration to catch hung sessions where Claude is alive but not responding
- Prevents stale state files from reporting false-positive health on crashed sessions

SOURCE: [gastown/internal/witness/manager.go](https://github.com/steveyegge/gastown/blob/main/internal/witness/manager.go) (accessed 2026-03-01)

### Witness / Zombie Detection

- Witness is a per-rig patrol agent that monitors all polecats on a continuous loop defined by the `mol-witness-patrol` TOML formula
- Patrol cycle: `inbox-check → process-cleanups → check-refinery → survey-workers → check-timer-gates → check-swarm-completion → patrol-cleanup → context-check → loop-or-exit`
- PRIMARY detection path: scans agent beads in Dolt for `exit_type` + `completion_time` fields written by `gt done` — does not rely on mail messages as primary signal
- ZOMBIE detection: for every polecat with `agent_state=running`, cross-references tmux session existence. A running bead state + missing tmux session = zombie. Checks if hook_bead is already closed before escalating (avoids false positives when `gt done` killed the session normally)
- ORPHANED bead detection: second scan from beads side for in-progress/hooked beads whose assignee polecat has both session and directory gone — resets bead to open and notifies Deacon for re-dispatch
- `ZombieStatus` type: `SessionHealthy | SessionZombie | SessionHung | SessionMissing` — callers distinguish failure modes for appropriate recovery action
- Swim lane rule: Witness only closes cleanup wisps it created; never touches formula wisps or polecat work wisps owned by other agents

SOURCE: [gastown/internal/witness/manager.go](https://github.com/steveyegge/gastown/blob/main/internal/witness/manager.go), [gastown/internal/formula/formulas/mol-witness-patrol.formula.toml](https://github.com/steveyegge/gastown/blob/main/internal/formula/formulas/mol-witness-patrol.formula.toml) (accessed 2026-03-01)

### Formula / DAG-Based Task Orchestration

- Workflows are defined as TOML files (`.formula.toml`) embedded in the binary under `internal/formula/formulas/`
- Four formula types: `convoy` (parallel legs + synthesis), `workflow` (sequential steps with `needs` DAG), `expansion` (template-based step generation), `aspect` (multi-aspect parallel analysis)
- `Step.Needs []string` field declares dependencies; executor resolves ready steps and runs them in topological order
- Steps carry `Acceptance` field for exit criteria used by Ralph loop mode; `Parallel bool` for steps that can run concurrently when sharing the same needs
- Molecules are durable instances of a formula executed on specific beads; wisps are ephemeral one-shot instances destroyed after completion
- ~40 built-in formulas: `mol-polecat-work`, `mol-witness-patrol`, `mol-deacon-patrol`, `mol-refinery-patrol`, `mol-polecat-code-review`, `mol-convoy-feed`, `release`, `shiny`, `security-audit`, `design`, `code-review`, etc.
- `bd cook <formula>` executes a formula; `bd mol pour <formula>` creates a trackable molecule instance

SOURCE: [gastown/internal/formula/types.go](https://github.com/steveyegge/gastown/blob/main/internal/formula/types.go), [gastown/internal/formula/formulas/](https://github.com/steveyegge/gastown/tree/main/internal/formula/formulas) (accessed 2026-03-01)

### Convoy Formula for Parallel Agents

- Convoy (work-tracking unit) wraps related beads across multiple rigs under a single `hq-cv-*` bead for dashboard visibility
- Convoy lifecycle: `open → landed/closed` when all tracked issues close; auto-reopens if new issues added to a closed convoy
- `gt convoy create "name" <bead-id...> --notify <recipient>` bundles beads and spawns the swarm
- Convoy formula type uses parallel `[[legs]]` (each a separate Claude invocation focusing on a specific aspect) with a `[synthesis]` step that combines outputs after all legs complete
- Swarm concept: ephemeral collection of polecats currently executing a convoy's issues; "swarm" dissolves when issues close, convoy tracking persists
- `SWARM_START` protocol message from Mayor triggers Witness to create a swarm tracking wisp; `SWARM_COMPLETE` mail closes the wisp and notifies Mayor when all polecats report `MERGED`
- `gt sling <bead-id> <rig>` assigns a single bead to a polecat; auto-creates a convoy so single-bead work appears in the dashboard ("swarm of one")

SOURCE: [gastown/docs/concepts/convoy.md](https://github.com/steveyegge/gastown/blob/main/docs/concepts/convoy.md) (accessed 2026-03-01)

### Persistent Polecat Identity with Ephemeral Sessions

- Three-layer architecture: Identity (permanent agent bead + CV chain), Sandbox (persistent git worktree, reused across assignments), Session (ephemeral Claude context window)
- Sessions cycle frequently (handoff, compaction, crash) without destroying the sandbox; sandbox survives all session cycles
- Lifecycle: `spawning → working → idle` — polecats are NOT destroyed on work completion; sandbox is preserved, sessions are killed; idle polecat reused by next `gt sling` avoiding worktree recreation overhead (~5s saved)
- `gt done` writes `exit_type`, `completion_time`, `mr_id`, `branch` to agent bead; transitions polecat to idle; kills session; submits work to Refinery merge queue
- Pool of named slots (Toast, Shadow, Copper, Ash, Storm...); `gt sling` finds an idle slot before allocating a new one
- Restart-first policy: Witness NEVER auto-nukes polecats; always restarts the session first to preserve worktree and branch; explicit `gt polecat nuke` required for permanent destruction

SOURCE: [gastown/docs/concepts/polecat-lifecycle.md](https://github.com/steveyegge/gastown/blob/main/docs/concepts/polecat-lifecycle.md) (accessed 2026-03-01)

### GUPP and Mail / Messaging Protocol

- GUPP (Gas Town Universal Propulsion Principle): "If there is work on your hook, YOU MUST RUN IT" — agents autonomously proceed without external confirmation
- Hook bead is each agent's work queue; GUPP prevents the failure mode where an agent announces itself and waits for confirmation instead of executing
- Mail system routes protocol messages between roles via `type=message` beads: `POLECAT_DONE`, `MERGE_READY`, `MERGED`, `MERGE_FAILED`, `HELP`, `HANDOFF`, `SWARM_START`, `LIFECYCLE:Shutdown`
- `gt nudge --mode=queue <rig>/polecats/<name>` sends asynchronous messages without interrupting in-flight tool calls; serialized per-session via channel semaphore with 30s timeout
- `gt mail drain --identity <role> --max-age 30m` bulk-archives stale protocol messages to prevent context consumption; HELP and HANDOFF messages exempt from drain (require attention)
- Nudge lock serialization prevents garbled input from concurrent nudges to the same session

SOURCE: [gastown/internal/witness/protocol.go](https://github.com/steveyegge/gastown/blob/main/internal/witness/protocol.go), [gastown/docs/concepts/propulsion-principle.md](https://github.com/steveyegge/gastown/blob/main/docs/concepts/propulsion-principle.md) (accessed 2026-03-01)

### Dolt SQL Storage Layer

- All beads data stored in a single Dolt SQL Server process per town (MySQL protocol, port 3307)
- Each rig gets its own database under `~/gt/.dolt-data/<rig>/`; `routes.jsonl` maps bead ID prefixes (e.g., `gt-`, `hq-`) to rig paths for transparent cross-rig operations
- Polecats and refinery use `.beads/redirect` files pointing to `mayor/rig/.beads/` so all agents in a rig share one database without individual beads dirs
- Write concurrency: all agents write directly to `main` branch using `BEGIN / DOLT_COMMIT / COMMIT` atomically; no branch proliferation
- Data lifecycle: `CREATE → LIVE → CLOSE → DECAY → COMPACT → FLATTEN` — automated through six stages via Dog agents (Reaper, Compactor, Doctor)
- Daemon monitors server health on every patrol heartbeat and auto-restarts on crash

SOURCE: [gastown/docs/design/architecture.md](https://github.com/steveyegge/gastown/blob/main/docs/design/architecture.md) (accessed 2026-03-01)

### Multi-Runtime Support

- Claude Code is the default runtime; Codex CLI supported as an alternative via per-rig `settings/config.json`
- Built-in agent presets: `claude`, `gemini`, `codex`, `cursor`, `auggie`, `amp`
- `gt sling <bead-id> <rig> --agent cursor` overrides runtime for a single spawn
- Per-agent custom commands: `gt config agent set claude-glm "claude-glm --model glm-4"`
- Future: Claude Code Agent Teams (AT) is being explored as a replacement for the tmux session transport layer (design doc: `docs/design/witness-at-team-lead.md`), where Witness would become an AT team lead spawning polecats as teammates

SOURCE: [gastown/README.md](https://github.com/steveyegge/gastown/blob/main/README.md), [gastown/docs/design/witness-at-team-lead.md](https://github.com/steveyegge/gastown/blob/main/docs/design/witness-at-team-lead.md) (accessed 2026-03-01)

---

## Technical Architecture

```text
~/gt/ (Town workspace)
├── .beads/           hq-* prefix beads (Mayor, Deacon, Convoys, Role templates)
├── .dolt-data/       Centralized Dolt SQL Server data (one DB per rig)
├── mayor/            Mayor agent home (cross-rig coordinator)
├── deacon/           Deacon daemon + Dog worker home
└── <rig>/            Per-project container (NOT a git clone)
    ├── mayor/rig/    Canonical git clone (all rig beads live here)
    ├── refinery/rig/ Git worktree — Refinery merge queue processor
    ├── witness/      Witness monitoring agent home (no git clone)
    ├── crew/<name>/  Full git clones for human developers
    └── polecats/<name>/<rig>/  Git worktrees from mayor/rig
```

**Role taxonomy:**

| Role | Scope | Persistence | Function |
|------|-------|-------------|----------|
| Mayor | Town | Persistent session | Cross-rig coordinator; creates convoys; orchestrates agent spawning |
| Deacon | Town | Persistent daemon | Watchdog beacon; runs patrol cycles; monitors Witness/Refinery health |
| Boot (Dog) | Town | Ephemeral | Checks Deacon every 5 min; triage when Deacon is down |
| Dogs | Town | Long-running | Automated maintenance: Reaper (delete), Compactor (rebase), Doctor (gc), Backup |
| Witness | Rig | Persistent session | Per-rig polecat monitor; zombie detection; escalation; merge tracking |
| Refinery | Rig | Persistent session | Merge queue processor; batch-then-bisect Bors-style merge strategy |
| Polecat | Rig | Persistent identity, ephemeral session | Named worker slots executing issue beads in isolated git worktrees |
| Crew | Rig | Persistent (human-managed) | Human developer workspaces; full git clones |

**Agent communication layers:**

```text
Nudge     — real-time tmux send-keys (serialized per session)
Mail      — beads type=message routed by recipient identity
Events    — gt mol step emit-event (unblocks await-signal)
Protocol  — structured POLECAT_DONE / MERGED / HELP / HANDOFF messages
```

**Merge queue (Refinery — batch-then-bisect):**

```text
MRs waiting: [A, B, C, D]
  → Rebase A..D as a stack on main
  → Test tip (D)
  → PASS: fast-forward merge all 4
  → FAIL: binary bisect → test B (midpoint) → recurse
```

SOURCE: [gastown/docs/design/architecture.md](https://github.com/steveyegge/gastown/blob/main/docs/design/architecture.md) (accessed 2026-03-01)

---

## Installation & Usage

```bash
# Install (Homebrew, recommended)
brew install gastown

# Or npm
npm install -g @gastown/gt

# Or from source
go install github.com/steveyegge/gastown/cmd/gt@latest

# Prerequisites
# Go 1.23+, Git 2.25+, Dolt 1.82.4+, beads (bd) 0.55.4+, sqlite3, tmux 3.0+

# Initialize workspace
gt install ~/gt --git
cd ~/gt

# Add a project
gt rig add myproject https://github.com/you/repo.git

# Create a human crew workspace
gt crew add yourname --rig myproject

# Start the Mayor (primary interface)
gt mayor attach
```

```bash
# Core workflow (inside Mayor session)
gt convoy create "Feature X" gt-abc12 gt-def34 --notify --human
gt sling gt-abc12 myproject          # assign work to a polecat
gt convoy list                        # track progress
gt feed                               # real-time TUI dashboard
gt feed --problems                    # stuck agent detection view

# Context recovery (run inside any agent session)
gt prime

# Beads (bd) workflow
bd ready                              # unblocked issues ready to work
bd update <id> --status=in_progress
bd close <id>
bv --robot-triage                     # graph-ranked work picks
bv --robot-plan                       # parallel execution tracks
```

SOURCE: [gastown/README.md](https://github.com/steveyegge/gastown/blob/main/README.md) (accessed 2026-03-01)

---

## Relevance to Claude Code Development

### Applications

- Gas Town directly targets Claude Code as its primary runtime and is built specifically to address the multi-agent coordination challenges that arise at 10-50+ concurrent Claude Code sessions
- The tmux-based session management architecture is a production-tested pattern for running many Claude Code instances without losing work state across restarts, compaction, or crashes
- The `gt prime` command (context recovery injection via Claude Code's `SessionStart` hook) is a reusable pattern for any multi-agent framework that needs to reinject persistent context into fresh sessions

### Patterns Worth Adopting

- **ZFC / single source of truth for session state**: Using tmux session existence as the authoritative liveness signal rather than PID files or lock files eliminates stale state bugs and simplifies restart logic
- **Three-layer agent lifecycle separation** (Identity permanent / Sandbox persistent / Session ephemeral): Decoupling these layers prevents unnecessary work loss and allows session cycling as a first-class operation rather than a failure mode
- **Cross-reference health detection**: Checking agent self-reported bead state against actual tmux session existence catches zombies that cannot self-report; never trust self-reported state alone for liveness
- **Swim lane discipline for shared resources**: Each agent role only manages wisps/state it created; other agents' artifacts are reported, not modified. Prevents accidental destruction of in-flight work
- **Drain + batch processing for inbox backlog**: At scale (10+ concurrent agents), message inboxes accumulate faster than linear processing allows; bulk-drain stale protocol messages first, then batch-process by type
- **Persistent sandbox with ephemeral sessions**: Preserving git worktrees between assignments (rather than destroying and recreating) saves 5+ seconds per spawn and maintains branch state through crashes
- **GUPP (autonomous execution mandate)**: Agents that check for work and execute without waiting for confirmation prevent the "announce and wait" failure mode that stalls pipelines

### Integration Opportunities

- Gas Town's `AGENTS.md` / `CLAUDE.md` priming pattern (`gt prime --hook`) is directly compatible with Claude Code's `SessionStart` hook mechanism and can be adopted for multi-agent skill orchestration in this repository
- The formula TOML format (workflow type with `needs` DAG, parallel execution flag, acceptance criteria) is a well-designed specification language for multi-step agent tasks that could inform the `/implement-feature` skill's task file format
- The Convoy tracking concept (persistent cross-agent work unit with lifecycle notifications) maps cleanly onto the backlog system in this repository and could serve as a reference for cross-session task visibility
- The batch-then-bisect merge queue (Bors-style) is a production-ready approach to integrating parallel agent branches without manual conflict resolution bottlenecks
- Gas Town's distinction between `bd` (CRUD) and `bv` (graph analysis with `--robot-*` flags for non-interactive use) is a strong pattern: separate read-only analysis tools from write tools and always provide machine-readable output flags for agent consumption

---

## References

- [Gas Town README](https://github.com/steveyegge/gastown/blob/main/README.md) (accessed 2026-03-01)
- [Gas Town Glossary](https://github.com/steveyegge/gastown/blob/main/docs/glossary.md) (accessed 2026-03-01)
- [Architecture Design Doc](https://github.com/steveyegge/gastown/blob/main/docs/design/architecture.md) (accessed 2026-03-01)
- [Propulsion Principle](https://github.com/steveyegge/gastown/blob/main/docs/concepts/propulsion-principle.md) (accessed 2026-03-01)
- [Convoy Concept Doc](https://github.com/steveyegge/gastown/blob/main/docs/concepts/convoy.md) (accessed 2026-03-01)
- [Polecat Lifecycle](https://github.com/steveyegge/gastown/blob/main/docs/concepts/polecat-lifecycle.md) (accessed 2026-03-01)
- [Witness Manager Source](https://github.com/steveyegge/gastown/blob/main/internal/witness/manager.go) (accessed 2026-03-01)
- [Witness Protocol Source](https://github.com/steveyegge/gastown/blob/main/internal/witness/protocol.go) (accessed 2026-03-01)
- [Tmux Package Source](https://github.com/steveyegge/gastown/blob/main/internal/tmux/tmux.go) (accessed 2026-03-01)
- [Formula Types Source](https://github.com/steveyegge/gastown/blob/main/internal/formula/types.go) (accessed 2026-03-01)
- [Witness Patrol Formula](https://github.com/steveyegge/gastown/blob/main/internal/formula/formulas/mol-witness-patrol.formula.toml) (accessed 2026-03-01)
- [Why These Features Doc](https://github.com/steveyegge/gastown/blob/main/docs/why-these-features.md) (accessed 2026-03-01)
- [Witness AT Team Lead Design](https://github.com/steveyegge/gastown/blob/main/docs/design/witness-at-team-lead.md) (accessed 2026-03-01)
- [GitHub API — Repository Metadata](https://api.github.com/repos/steveyegge/gastown) (accessed 2026-03-01)
- [DoltHub Blog: "A Day in Gas Town"](https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town/) (Tim Sehn, 2026-01-15, accessed 2026-03-01) — early snapshot of Gas Town usage; describes Beads (Git+SQLite memory), Mayor coordination, tmux multi-terminal management, ~10x cost of standard Claude Code sessions, autonomous PR creation. **Note**: This blog captures Gas Town circa January 2026; the project has evolved significantly since then with hundreds of iterations

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-03-01 |
| Version at Verification | v0.9.0 |
| Next Review Recommended | 2026-06-01 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](../agent-frameworks/claude-code-harness.md) | agent-frameworks | referenced by Claude Code Harness (agent-frameworks) |
