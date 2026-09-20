# Orchestrator Discipline

Orchestrators delegate; agents implement. The orchestrator's context window is shared across the session — agents get fresh context per task.

---

## Anti-Patterns

| Anti-Pattern | Trigger | Response |
|--------------|---------|----------|
| **Investigation Escalation** | 3+ Read/Grep/Bash on source files without Edit/Write/Task | STOP. Delegate. Do not read one more file. |
| **Agent Output Polling** | TaskOutput block=false on running agent; Read on .output/transcript | Wait for completion notification. Never poll. |

**No exemption categories**: "config changes", "small edits", "just TOML/YAML" are not valid reasons to skip delegation.

---

## Read Constraints

**PERMITTED**: Task status, agent output artifacts, backlog items (~/.dh/projects/{slug}/backlog/ per-item files), plan files (~/.dh/projects/{slug}/plan/), skill/agent configs, files you will Edit/Write this turn.

**NEVER**: Source/config/test files you will not edit; diagnostic command output; agent .output files; TaskOutput block=false on running agent.

**Falsifiable test**: "Will I Edit or Write this file this turn?" If NO — delegate.

---

## CoVe Bypass Anti-Pattern

Orchestrators pass paths and outcomes; agents discover and verify. Do not pre-gather data for agents.

---

## Source

- `orchestrator-discipline:orchestrator-discipline` skill (separate plugin; load it when installed)
