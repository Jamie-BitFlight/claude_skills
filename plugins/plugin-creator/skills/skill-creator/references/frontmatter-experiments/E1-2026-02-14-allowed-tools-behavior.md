# E1: allowed-tools Frontmatter Field Behavior

**Date**: 2026-02-14
**Status**: Partial — inline and `context: fork` skill-subagent execution tested, pre-approval untested

## Question

Does the `allowed-tools` frontmatter field restrict which tools are available, pre-approve listed tools, or both?

## Documentation Claims

Three statements found in official Anthropic documentation at `https://docs.anthropic.com/en/docs/claude-code/skills.md`:

1. **Frontmatter reference table**: "Tools Claude can use without asking permission when this skill is active."
2. **"Restrict tool access" section**: "Use the `allowed-tools` field to limit which tools Claude can use when a skill is active."
3. **"Restrict Claude's skill access" section**: "Skills that define `allowed-tools` grant Claude access to those tools without per-use approval when the skill is active."

Statement 1 and 3 describe pre-approval. Statement 2 describes restriction. The documentation claims the field does both.

## Test Artifacts

Temporary files created for this experiment:

- `.claude/skills/test-allowed-tools/SKILL.md` — test skill with `allowed-tools: Read`

These files can be deleted after the experiment reaches `Complete` status, since the reproduction steps below contain the full file contents needed to recreate them.

---

## Experiment: Inline Skill (no `context: fork`)

### Setup

Created `.claude/skills/test-allowed-tools/SKILL.md` with:

```yaml
---
description: 'Test skill to verify allowed-tools behavior. Invoke with /test-allowed-tools to run the test.'
allowed-tools: Read
disable-model-invocation: true
---

# Test: allowed-tools behavior

This skill has `allowed-tools: Read` set. Test what happens:

1. Use the Read tool to read this file: `.claude/skills/test-allowed-tools/SKILL.md`
2. Use the Grep tool to search for "allowed-tools" in `.claude/skills/test-allowed-tools/SKILL.md`
3. Use the Glob tool to find `.claude/skills/test-allowed-tools/*`

Report which tools succeeded and which were blocked or unavailable.
```

### Reproduction Steps

1. Create the directory: `mkdir -p .claude/skills/test-allowed-tools/`
2. Write the file above to `.claude/skills/test-allowed-tools/SKILL.md`
3. Start a Claude Code session in the repo root
4. Type `/test-allowed-tools` to invoke the skill
5. Observe which of the three tool calls (Read, Grep, Glob) succeed or fail
6. Record the session's permission mode (check with `/permissions` or note the mode displayed in the UI)

### Execution

Invoked `/test-allowed-tools` in an active session.

### Results

| Tool | Listed in `allowed-tools`? | Outcome |
|------|---------------------------|---------|
| Read | Yes | Succeeded |
| Grep | No | Succeeded |
| Glob | No | Succeeded |

### Observation

All three tools executed without error. The `allowed-tools: Read` field did NOT prevent Grep or Glob from being used in an inline (non-forked) skill context.

### Permission Mode

Not recorded for this run.

---

## Experiment: Inline Skill Replication (no `context: fork`) — 2026-02-14 session 2

### Setup

Same `.claude/skills/test-allowed-tools/SKILL.md` as the first experiment. No changes to the skill file between runs.

### Reproduction Steps

1. Confirm `.claude/skills/test-allowed-tools/SKILL.md` exists with the contents from the first experiment's Setup section
2. Start a Claude Code session in the repo root
3. Type `/test-allowed-tools .prettierrc` to invoke the skill with an argument
4. Observe which of the three tool calls (Read, Grep, Glob) succeed or fail
5. Record the session's permission mode

### Execution

Three tool calls issued in parallel:

1. `Read` — `.claude/skills/test-allowed-tools/SKILL.md`
2. `Grep` — pattern `allowed-tools` in `.claude/skills/test-allowed-tools/SKILL.md`
3. `Glob` — pattern `.claude/skills/test-allowed-tools/*`

### Results

| Tool | Listed in `allowed-tools`? | Outcome |
|------|---------------------------|---------|
| Read | Yes | Succeeded — returned file contents (16 lines) |
| Grep | No | Succeeded — returned 7 matching lines |
| Glob | No | Succeeded — returned 1 file path |

### Observation

All three tools executed without error. This replicates the first test result. In inline (non-forked) context, `allowed-tools: Read` does not prevent unlisted tools from executing.

### Permission Mode

Not recorded for this run. ASSUMPTION: the session was running in a permissive permission mode. This assumption has not been tested. Pre-approval behavior (documentation claims 1 and 3) cannot be evaluated until a test is run in a restrictive permission mode where unlisted tools would normally require approval.

---

## Experiment: Forked Context (`context: fork`) — 2026-02-14 session 3

### Setup

Modified `.claude/skills/test-allowed-tools/SKILL.md` to add `context: fork` and a Bash test:

```yaml
---
description: 'Test skill to verify allowed-tools behavior in a context: fork skill subagent. Invoke with /test-allowed-tools to run the test.'
allowed-tools: Read
disable-model-invocation: true
context: fork
---

# Test: allowed-tools behavior (`context: fork` skill subagent)

This skill has `allowed-tools: Read` and `context: fork` set. Test what happens:

1. Use the Read tool to read this file: `.claude/skills/test-allowed-tools/SKILL.md`
2. Use the Grep tool to search for "allowed-tools" in `.claude/skills/test-allowed-tools/SKILL.md`
3. Use the Glob tool to find `.claude/skills/test-allowed-tools/*`
4. Use the Bash tool to run: `echo "bash tool test"`

Report which tools succeeded and which were blocked or unavailable. For each tool, state:
- Tool name
- Whether it was listed in allowed-tools
- Exact outcome (succeeded with output, failed with error, or tool not available)
```

### Reproduction Steps

1. Write the file above to `.claude/skills/test-allowed-tools/SKILL.md`
2. Start a Claude Code session in the repo root
3. Type `/test-allowed-tools .prettierrc` to invoke the skill
4. The skill runs in a fresh skill subagent due to `context: fork`
5. Observe which of the four tool calls (Read, Grep, Glob, Bash) succeed or fail
6. Record the session's permission mode

### Execution

Invoked `/test-allowed-tools .prettierrc`. The skill ran in a fresh `context: fork` subagent. Four tool calls were issued:

1. `Read` — `.claude/skills/test-allowed-tools/SKILL.md`
2. `Grep` — pattern `allowed-tools` in `.claude/skills/test-allowed-tools/SKILL.md`
3. `Glob` — pattern `.claude/skills/test-allowed-tools/*`
4. `Bash` — `echo "bash tool test"`

### Results

| Tool | Listed in `allowed-tools`? | Outcome |
|------|---------------------------|---------|
| Read | Yes | Succeeded — returned full 21-line file contents |
| Grep | No | Succeeded — returned 8 matching lines |
| Glob | No | Succeeded — returned 1 file path |
| Bash | No | Succeeded — output was `bash tool test` |

### Observation

All four tools executed without error in the fresh skill subagent. The `allowed-tools: Read` field did NOT prevent Grep, Glob, or Bash from being used. This matches the inline context results from the previous two experiments.

### Permission Mode

Not recorded for this run.

---

## Untested

- **Pre-approval behavior**: Whether `allowed-tools` bypasses permission prompts for listed tools has not been isolated. All three test sessions had permissive tool settings. A test in a restrictive permission mode is required to evaluate this.
- **Agent-preloaded context**: Does `allowed-tools` restrict tools when the skill is preloaded into an agent via the `skills:` frontmatter key? Untested.

## Permission Mode Discovery — 2026-02-14 session 4

Examined `.claude/settings.json` in this session. The allow list contains: `Glob`, `Grep`, `Read`, `Bash(gh issue list:*)`, `Bash(git worktree:*)`, and several MCP tools. Deny list contains: `WebFetch`, `WebSearch`.

However, the session is running with bypass permissions enabled. This means all permission rules are not enforced — every tool executes without approval prompts regardless of the allow/deny list.

**Consequence for U3**: The pre-approval test (U3) cannot be run in this session. Distinguishing "pre-approved by allowed-tools" from "permitted by bypass mode" is not possible when bypass is active.

**Consequence for all prior E1 runs**: The three prior runs did not record permission mode. If those sessions also had bypass enabled, the observation "unlisted tools succeeded" does not test whether `allowed-tools` restricts tools — it only confirms bypass mode overrides everything. The non-restriction finding remains valid for bypass-mode sessions but does not generalize to restrictive-mode sessions.

**What is needed**: A session started WITHOUT bypass permissions, where the allow list does not include the tools being tested (e.g., Bash is not in the allow list). Then invoke a skill with `allowed-tools: Bash` and observe whether Bash executes without a prompt.

## Impact on skill-creator

The skill-creator SKILL.md describes `allowed-tools` as:

> "Tools Claude can use without asking permission when this skill is active (comma-separated)."

This description matches documentation claim 1 and 3 but omits claim 2 (restriction). The observed runtime behavior in both inline and `context: fork` skill-subagent execution showed no restriction effect across three test runs.

The skill-creator guided the creation of `/find-cause` with `allowed-tools: Read, Grep, Glob, Bash, AskUserQuestion` — a field that was applied without understanding its runtime effect. The field was subsequently removed.

The official documentation claim 2 ("Use the `allowed-tools` field to limit which tools Claude can use when a skill is active") was not observed in any test. In all three runs, unlisted tools executed without error.

## Next Steps

1. Test pre-approval by invoking in a restrictive permission mode and checking whether listed tools skip permission prompts while unlisted tools require approval
2. Test with skill preloaded into an agent via `skills:` key
3. Update skill-creator documentation based on confirmed behavior
