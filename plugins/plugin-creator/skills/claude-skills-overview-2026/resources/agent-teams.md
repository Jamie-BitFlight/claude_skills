# Agent Teams - Claude Code Reference (February 2026)

Agent teams coordinate multiple Claude Code instances working as a team. One session acts as lead; teammates work independently in their own context windows with inter-agent messaging.

**Status**: Experimental. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` in settings.json or environment.

**Source**: [Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams.md) (accessed 2026-03-07)

---

## When to Use Agent Teams vs Subagents

| Criterion | Subagents | Agent Teams |
| --- | --- | --- |
| Context | Own window; results return to caller | Own window; fully independent |
| Communication | Report results back to main agent only | Teammates message each other directly |
| Coordination | Main agent manages all work | Shared task list with self-coordination |
| Best for | Focused tasks where only the result matters | Complex work requiring discussion and collaboration |
| Token cost | Lower (results summarized back) | Higher (each teammate is separate instance) |

### Decision Rule

Use subagents when workers report back independently. Use agent teams when workers must share findings, challenge each other, and coordinate on their own.

### Team-Worthy Workflow Criteria

A workflow is a strong candidate for agent teams when ALL of these are true:

1. **3+ independent units of work** - enough parallelism to justify coordination overhead
2. **Units benefit from cross-communication** - findings from one unit inform or challenge another (not just "do N things and collect results")
3. **No shared file mutations** - two teammates editing the same file leads to overwrites
4. **Result is a synthesis, not a concatenation** - value comes from combining, deduplicating, or reconciling findings across units

A workflow is NOT a good candidate when:

- Work is sequential (each step depends on the previous)
- Only 1-2 sources/targets (subagent overhead is lower)
- Units are fully independent with no cross-communication need (subagents suffice)
- Result is just collecting N outputs (no synthesis step)

---

## Enabling Agent Teams

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Place in settings.json or set as environment variable.

---

## Architecture

| Component | Role |
| --- | --- |
| Team lead | Main session that creates team, spawns teammates, coordinates work |
| Teammates | Separate Claude Code instances working on assigned tasks |
| Task list | Shared list of work items that teammates claim and complete |
| Mailbox | Messaging system for communication between agents |

### Storage Locations

- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

The team config contains a `members` array with each teammate's name, agent ID, and agent type. Teammates can read this file to discover other team members.

---

## Display Modes

| Mode | Behavior | Requirement |
| --- | --- | --- |
| in-process | All teammates in main terminal. Shift+Up/Down to select. | Any terminal |
| split panes | Each teammate gets own pane. Click to interact. | tmux or iTerm2 |
| auto (default) | Split panes if in tmux; in-process otherwise | - |

Override with `teammateMode` in settings.json or `--teammate-mode` flag.

---

## Team Control Patterns

### Spawning Teammates

Natural language to the lead. Specify count and models when needed:

<eg>
Create a team with 4 teammates to refactor these modules in parallel.
Use Sonnet for each teammate.
</eg>

### Plan Approval for Teammates

Require teammates to plan before implementing:

<eg>
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
</eg>

The lead reviews and approves/rejects plans. Give the lead criteria: "only approve plans that include test coverage."

### Delegate Mode

Press Shift+Tab to restrict lead to coordination-only tools: spawning, messaging, shutting down teammates, and managing tasks. Prevents lead from implementing directly.

### Direct Teammate Interaction

- In-process: Shift+Up/Down to select; Enter to view session; Escape to interrupt; Ctrl+T for task list
- Split panes: Click into a pane to interact directly

### Task Assignment

- Lead assigns tasks explicitly, or teammates self-claim
- Tasks have states: pending, in progress, completed
- Tasks support dependencies: blocked tasks cannot be claimed until dependencies complete
- File locking prevents race conditions on simultaneous claims

### Teammate Communication

- **message**: Send to one specific teammate
- **broadcast**: Send to all teammates simultaneously (use sparingly; costs scale with team size)

---

## Context and Permissions

### Context Loading

- Teammates load same project context as regular session: CLAUDE.md, MCP servers, skills
- Teammates receive spawn prompt from lead
- Lead's conversation history does NOT carry over

### Information Sharing

- Automatic message delivery (no polling needed)
- Idle notifications when teammates finish
- Shared task list visible to all agents

### Permissions

- Teammates start with lead's permission settings
- Individual teammate modes can be changed after spawning
- Cannot set per-teammate modes at spawn time

---

## Best Practices

### Context

Include task-specific details in spawn prompts (teammates do not inherit lead conversation):

<eg>
Spawn a security reviewer teammate with the prompt: "Review the authentication
module at src/auth/ for security vulnerabilities. Focus on token handling,
session management, and input validation. The app uses JWT tokens stored in
httpOnly cookies. Report any issues with severity ratings."
</eg>

### Task Sizing

- Too small: coordination overhead exceeds benefit
- Too large: teammates work too long without check-ins
- Right: self-contained units producing a clear deliverable (function, test file, review)
- Target 5-6 tasks per teammate for productive flow

### File Conflict Prevention

Break work so each teammate owns a different set of files. Two teammates editing the same file leads to overwrites.

### Monitoring

Check in on progress, redirect approaches that are not working, synthesize findings as they arrive. Unattended teams risk wasted effort.

---

## Quality Gates via Hooks

Two hook events enforce quality on teammate work:

### TeammateIdle

Fires when a teammate is about to go idle. Exit with code 2 to send feedback and keep the teammate working.

Configure in project-level settings.json:

```json
{
  "hooks": {
    "TeammateIdle": [
      {
        "matcher": "worker",
        "hooks": [
          { "type": "command", "command": "./scripts/validate-teammate-work.sh" }
        ]
      }
    ]
  }
}
```

Use for: enforcing coding standards before a teammate stops, running tests before marking work complete, validating output quality.

### TaskCompleted

Fires when a task is being marked complete. Exit with code 2 to prevent completion and send feedback.

```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          { "type": "command", "command": "./scripts/verify-task.sh" }
        ]
      }
    ]
  }
}
```

Use for: preventing tasks from being marked done without passing tests, enforcing acceptance criteria checks, requiring documentation before task closure.

Both hooks support matchers to target specific teammate names or task types. Exit code 2 blocks the action and sends stderr back to the teammate as feedback.

SOURCE: <https://code.claude.com/docs/en/agent-teams.md> (accessed 2026-03-07) and <https://code.claude.com/docs/en/sub-agents.md> (accessed 2026-03-07)

---

## Use Case Patterns

### Parallel Code Review

<eg>
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
</eg>

Each reviewer applies a different filter. Lead synthesizes findings.

### Competing Hypotheses Investigation

<eg>
Users report the app exits after one message instead of staying connected.
Spawn 5 agent teammates to investigate different hypotheses. Have them talk to
each other to try to disprove each other's theories, like a scientific
debate. Update the findings doc with whatever consensus emerges.
</eg>

Cross-challenge structure: each teammate actively tries to disprove others. Surviving theory is more likely correct.

### Map-Challenge-Reduce Pattern

Common structural pattern for team workflows:

1. **Map phase**: 3+ independent workers each investigate/produce
2. **Cross-challenge**: one worker's finding invalidates or refines another's
3. **Reduce phase**: synthesize, deduplicate, and resolve contradictions

---

## Lifecycle Management

### Shutdown

<eg>
Ask the researcher teammate to shut down
</eg>

Teammate can approve (exits gracefully) or reject (with explanation).

### Cleanup

<eg>
Clean up the team
</eg>

Lead checks for active teammates and fails if any still running. Always shut down teammates before cleanup. Only the lead should run cleanup.

---

## Constraints on Team Design

The orchestrator MUST account for these constraints when designing team workflows:

- **No resumption**: In-process teammates are lost on `/resume` or `/rewind`. For interruptible work, prefer subagents with `run_in_background` or use tmux backend.
- **Task status lag**: Teammates sometimes fail to mark tasks completed, blocking dependent tasks. The lead should verify task completion rather than relying solely on status.
- **Slow shutdown**: Teammates finish their current request before exiting. Factor this into cleanup timing.
- **Single team per session**: Plan all parallel work into one team. Use subagents for secondary parallel tasks outside the team.
- **No nesting**: Teammates cannot spawn their own teams. If a teammate needs parallel work, it uses subagents (Agent tool).
- **Fixed lead**: The session that creates the team remains lead for its lifetime. Design the lead's coordination role before spawning.
- **Permissions at spawn**: All teammates start with lead's permission mode. Individual modes can be changed after spawning but not at spawn time.
- **Split panes**: Require tmux or iTerm2. Not supported in VS Code terminal, Windows Terminal, or Ghostty.
- **Hook-enforced quality gates**: Use `TeammateIdle` and `TaskCompleted` hooks to prevent teammates from stopping or marking tasks done without passing quality checks. Exit code 2 sends feedback back to the teammate.

---

## Relation to Skills and Subagents

- Teammates load CLAUDE.md files from their working directory
- Teammates have access to all skills the lead has
- Skills provide project-specific guidance to all teammates automatically
- For lightweight delegation without inter-agent coordination, use subagents instead
- For manual parallel sessions, use git worktrees

---

## Related Skills

- `agent-orchestration:parallel-work` — portable fan-out shapes; Claude Code team mechanics in its `delegate/references/harness-notes/claude-code.md`.
- `/summarizer:multi-source-synthesis` — Working example of team coordination in practice. The summarizer plugin uses teammates for parallel source summarization with cross-checking, then synthesis by the leader.

**Source**: [Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams.md) (accessed 2026-03-07)
