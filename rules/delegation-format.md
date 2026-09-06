# Delegation Format Standard — Wrong Formats

Scope: documenting a delegation step in prose or workflow docs (SKILL.md, agent files, command
files, reference files) — not constructing an actual dispatch prompt. For that, see
`agent-orchestration:delegate`.

## Wrong Formats

### 1. Agent reference alone

```text
# WRONG
@subagent-refactorer
```

No context, no output, no agent routing — Claude reads `@name` as reference notation, not instruction.

### 2. Tool API call templates

```text
# WRONG
Agent(subagent_type="plugin-creator:subagent-refactorer", prompt="Fix the agent")
```

Tool API syntax belongs in code, not workflow docs.

### 3. Arrow routing notation

```text
# WRONG
Step 3 → subagent_type="plugin-creator:subagent-refactorer"
```

Omits context (what to pass) and output (what to verify).

### 4. Act-as roleplay in general-purpose Task

```text
# WRONG
Use a general-purpose agent and tell it to act as @subagent-refactorer
```

Roleplay does not load the specialist's skills or training. Use the actual specialist agent.

### 5. Tables with subagent_type column

```text
# WRONG
| Step | Agent | Notes |
|------|-------|-------|
| 3    | plugin-creator:subagent-refactorer | fix prompt |
```

Tables flatten context and output into generic columns. The agent cannot determine what to pass or verify. Tables are acceptable for flat data — not for workflow steps.
