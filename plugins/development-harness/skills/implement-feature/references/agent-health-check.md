# Agent Health Check Procedure

Full procedure for `implement-feature`'s Agent Health Check step. Reached only when one of the
trigger conditions in the main skill fires — most dispatches never reach this file.

**Never read JSONL session files directly in the orchestrator context.** Session files can exceed
40K tokens. Always delegate to `agentskill-kaizen:transcript-analyst` with an empty context window.

Session JSONL files are at `~/.claude/projects/{project-slug}/*.jsonl`, filterable by `agentId`
field. The `{project-slug}` is the absolute project path with `/` replaced by `-` (e.g.
`/home/user/repos/myproject` → `-home-user-repos-myproject`).

```mermaid
flowchart TD
    Trigger([Health check triggered]) --> Spawn
    Spawn["Task is session health summary<br>subagent_type='agentskill-kaizen:transcript-analyst'<br>Context: agent name or teammate ID to check,<br>JSONL dir ~/.claude/projects/{project-slug}/*.jsonl<br>Report: last turn timestamp, last tool call,<br>verdict of crashed / idle / active"]
    Spawn --> Verdict{Analyst verdict}
    Verdict -->|"Crashed — session ended abruptly<br>after sam_task(action=claim) with no further turns"| Confirm
    Confirm["Confirm task state via sam_task read<br>using plan_ref + task_id<br>Verify task is still CLAIMED"] --> Respawn
    Respawn["Re-spawn agent with the same plan_ref and task ID<br>SubagentStop hook updates status on completion"]
    Verdict -->|"Idle — no tool calls for 5+ min<br>agent appears stuck mid-task"| Activity["Read the task via sam_task read<br>Note its last-activity timestamp<br>Wait 2 minutes and read it again"]
    Activity --> ActCheck{last-activity advanced?}
    ActCheck -->|"Yes — the agent is still writing task state"| Waiting
    ActCheck -->|"No — task state is frozen"| Respawn
    Verdict -->|"Active — tool calls within last 2–3 min"| Waiting
    Waiting[Continue waiting] --> Later["Re-check after 5–10 min<br>if completion message still absent"]
```
