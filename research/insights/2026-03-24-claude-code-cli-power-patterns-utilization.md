# Utilization Proposals: Claude Code CLI Power Patterns

**Research entry**: ./research/developer-tools/claude-code-cli-power-patterns.md
**Generated**: 2026-03-24
**Integration surfaces found**: 7 (CLI flags, environment variables, JSON schema)
**Proposals written**: 4
**Skipped**: 4 — interactive REPL features (no external integration surface)

---

## Utilization 1: `/dh:work-milestone` → Parallel Worktree Isolation

**Research entry**: ./research/developer-tools/claude-code-cli-power-patterns.md
**Caller**: `plugins/development-harness/skills/work-milestone/SKILL.md`
**Integration mechanism**: CLI subprocess invocation with `--worktree` flag
**Replaces or adds**: Already in use — codifies and expands concurrent multi-agent isolation pattern
**Setup cost**: Low (flag already supported by current Claude Code CLI)
**Integration surface**: `claude -p --worktree {branch-name}` — git native worktree creation

### Why this caller

The `/work-milestone` skill spawns independent `claude -p` (kage-bunshin) sessions, one per wave item, each in its own git worktree. The research entry documents `--worktree` as a native git worktree mechanism that eliminates race conditions when multiple agents modify the same repository. The skill already uses this pattern (lines 44-46 of SKILL.md: "git worktree add worktrees/{slug}"). The integration surface validates and standardizes the current implementation: each spawned session should invoke `claude -p --worktree {branch-slug}` instead of managing worktrees manually.

### Integration sketch

Current approach (manual worktree):

```bash
cd /home/ubuntulinuxqa2/repos/claude_skills
git worktree add .claude/worktrees/feature-auth-v2 from integration-branch
cd .claude/worktrees/feature-auth-v2
claude -p --model sonnet --permission-mode auto --output-format json ...
```

Refactored approach (Claude Code native worktree isolation):

```bash
# Each kage-bunshin session invokes:
claude -p \
  --worktree feature-auth-v2 \
  --model sonnet \
  --permission-mode auto \
  --output-format json \
  'Load /dh:work-backlog-item #42'

# Claude Code creates .claude/worktrees/feature-auth-v2 automatically,
# executes the session isolated inside it, and cleans up on exit.
```

**Effect**: Simpler session startup, guaranteed git isolation without manual branch management, and transparent worktree cleanup.

---

## Utilization 2: CI/CD Safe Dispatch via `--max-turns` + `--max-budget-usd`

**Research entry**: ./research/developer-tools/claude-code-cli-power-patterns.md
**Caller**: `plugins/development-harness/skills/dispatch/SKILL.md` (and `/work-milestone` wave spawning)
**Integration mechanism**: CLI subprocess flags (`--max-turns` and `--max-budget-usd`)
**Replaces or adds**: Adds hard financial and iteration safety caps currently missing from dispatch
**Setup cost**: Low (flags are CLI standard, minimal integration effort)
**Integration surface**: `claude -p --max-turns N --max-budget-usd M "prompt"`

### Why this caller

The `/dispatch` skill spawns parallel agent teams and the `/work-milestone` skill spawns concurrent kage-bunshin sessions without explicit iteration or budget limits. The research entry identifies these flags (Tip 10, lines 220-240) as essential for safe autonomous execution: `--max-turns` prevents runaway loops and `--max-budget-usd` acts as a circuit breaker. Current implementations may loop indefinitely or accumulate untracked API costs. Adding these flags provides deterministic execution boundaries required for production CI/CD.

### Integration sketch

Current approach (no safety caps):

```bash
claude -p --permission-mode auto --output-format json 'Load /dh:work-backlog-item #42'
# If the session loops or encounters complex reasoning, it continues unbounded.
```

Refactored approach (with safety bounds):

```bash
claude -p \
  --max-turns 5 \
  --max-budget-usd 2.00 \
  --permission-mode auto \
  --output-format json \
  'Load /dh:work-backlog-item #42'

# Session terminates after 5 turns OR $2.00 spend, whichever comes first.
# Result JSON is incomplete but captures what was accomplished before exit.
```

**Dispatch spawning pattern** (in `/work-milestone` Step 5c):

```bash
for item in $WAVE_ITEMS; do
  (
    cd .claude/worktrees/${item-slug}
    claude -p \
      --max-turns 8 \
      --max-budget-usd 5.00 \
      --worktree ${item-slug} \
      'Load /dh:work-backlog-item #${ISSUE_NUMBER}' > /tmp/kb-work-${ISSUE_NUMBER}.json
  ) &
done
wait
```

---

## Utilization 3: Effort-Based Model Routing via `CLAUDE_CODE_EFFORT_LEVEL`

**Research entry**: ./research/developer-tools/claude-code-cli-power-patterns.md
**Caller**: `plugins/development-harness/skills/dispatch/SKILL.md` (task spawning and wave dispatch)
**Integration mechanism**: Environment variable (`CLAUDE_CODE_EFFORT_LEVEL={low|medium|high|max}`)
**Replaces or adds**: Adds compute-aware task routing — currently sessions default to single model
**Setup cost**: Medium (requires task classification to determine appropriate effort level per task)
**Integration surface**: Environment variable passed to spawned `claude` session

### Why this caller

The `/dispatch` skill treats all tasks uniformly: each spawned session runs at the same model capability regardless of task complexity. The research entry (Tip 5, lines 117-135) documents `CLAUDE_CODE_EFFORT_LEVEL` as Opus 4.6 Adaptive Thinking exposure with 4 tiers. Boilerplate generation, variable renaming, and test scaffolding waste High/Max effort; complex architectural decisions run poorly on Low effort. Current implementation routes all SAM tasks to the same model (default Sonnet). Adding effort-level classification enables cost-optimized execution: simple tasks run Low (fast, cheap), architectural decisions run High/Max (better results).

### Integration sketch

**Task classification at dispatch time:**

```python
# In dispatch_helper.py or work-milestone prompting:
task_complexity = classify_task(task_content)
# Returns: "low" (boilerplate, docs), "medium" (feature impl), "high" (architecture)

effort_level = {
    "low": "low",        # Fast, cheap, deterministic
    "medium": "medium",
    "high": "high",      # Deep reasoning, slower
}[task_complexity]
```

**Environment variable injection:**

```bash
# In work-milestone or dispatch spawning loop:
export CLAUDE_CODE_EFFORT_LEVEL=${effort_level}
claude -p \
  --max-turns 5 \
  --model ${model} \
  --permission-mode auto \
  --output-format json \
  'Load /dh:work-backlog-item #42'
```

**Real-world example**:
- T1 (Boilerplate test scaffolding) → `low` effort → Haiku, 2 min latency, cost minimal
- T3 (API schema design) → `high` effort → Opus, 8 min latency, deep reasoning
- T5 (Bug fix, clear scope) → `medium` effort → Sonnet, 3 min latency, balanced

---

## Utilization 4: Structured JSON Output via `--json-schema` Validation

**Research entry**: ./research/developer-tools/claude-code-cli-power-patterns.md
**Caller**: `plugins/development-harness/skills/work-milestone/SKILL.md` (and dispatch wave spawning)
**Integration mechanism**: CLI flags `--output-format json` + `--json-schema {path}`
**Replaces or adds**: Currently returns raw conversational output; adds strict schema validation
**Setup cost**: High (requires designing JSON schema for task completion reports, integrating schema validation into wave parsing)
**Integration surface**: `claude -p --output-format json --json-schema ./schemas/task-result.schema.json "prompt"`

### Why this caller

The `/work-milestone` skill spawns kage-bunshin sessions and parses their results from JSON files (lines 50-60 of SKILL.md: "Read result JSON from each /tmp/kb-work-{issue}.json"). Current implementation relies on agents to produce parseable JSON without schema enforcement, causing parsing brittleness. The research entry (Tip 7, lines 159-176) documents `--json-schema` as strict output constraint: the model must produce output matching an exact JSON Schema. This prevents hallucinated field names, missing fields, or invalid structure — guaranteeing downstream parsing always succeeds.

### Integration sketch

**Define task result schema** (`schemas/task-result.schema.json`):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "task_id", "files_changed", "commits"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["complete", "blocked", "partial"]
    },
    "task_id": {
      "type": "string",
      "pattern": "^P\\d+/T\\d+$"
    },
    "files_changed": {
      "type": "array",
      "items": {"type": "string"}
    },
    "commits": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["hash", "message"],
        "properties": {
          "hash": {"type": "string"},
          "message": {"type": "string"}
        }
      }
    },
    "notes": {
      "type": "string"
    }
  }
}
```

**Spawn with schema constraint** (in work-milestone):

```bash
cd .claude/worktrees/${item-slug}
claude -p \
  --max-turns 5 \
  --max-budget-usd 3.00 \
  --output-format json \
  --json-schema ./schemas/task-result.schema.json \
  'Load /dh:work-backlog-item #42' > /tmp/kb-work-${ISSUE_NUMBER}.json

# Output is guaranteed to match the schema.
# Parsing downstream is deterministic — no error handling needed for malformed JSON.
```

**Parsing wave results** (in work-milestone Step 6b):

```python
import json

for issue_file in glob.glob("/tmp/kb-work-*.json"):
    with open(issue_file) as f:
        result = json.load(f)  # No try/except needed — schema validation ensures valid JSON
        status = result["status"]
        files_changed = result["files_changed"]
        commits = result["commits"]
```

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/skills/swarm-spawning/SKILL.md` | Already documents subagent spawning via Agent tool (TaskCreate). `--agents` JSON injection (Tip 9) provides dynamic session-scoped agents without persisting to disk — orthogonal use case. Current spawn mechanisms are sufficient; dynamic agents would be additive, not replacement. Skipped due to orthogonal scope (would need SAM task workflow changes to integrate). |
| `.claude/agents/code-review.md` | Code review executes after implementation, not during dispatch. Integration surfaces (effort levels, budget caps, schema validation) are relevant to dispatch spawning, not to post-implementation review workflow. Skipped due to workflow stage mismatch. |
| `plugins/development-harness/skills/implement-feature/SKILL.md` | Executes agent delegation loop via Agent tool, not subprocess invocation. `--max-turns`, `--max-budget-usd`, and `--json-schema` apply to headless `claude -p` invocations, not to interactive orchestrator context. Skipped due to invocation mechanism mismatch (Agent tool vs. subprocess). |
| `plugins/development-harness/skills/dispatch/SKILL.md` (PR rehydration) | `--from-pr` rehydrates agent state when resuming from a PR created during original session (Tip 2). Current dispatch creates agents mid-session; agents do not create PRs as part of task completion. Skipped due to workflow mismatch (no PR creation during task dispatch). |

---

## Summary

Four utilization proposals identified with concrete integration surfaces:

1. **Worktree Isolation (Utilization 1)** — Standardize current manual worktree pattern to native `--worktree` CLI flag
2. **Safety Caps (Utilization 2)** — Add `--max-turns` and `--max-budget-usd` bounds to all dispatch spawning
3. **Effort Routing (Utilization 3)** — Classify tasks by complexity and route via `CLAUDE_CODE_EFFORT_LEVEL` env var
4. **Schema Validation (Utilization 4)** — Define JSON schemas for task result outputs and enforce via `--json-schema`

Three features (interactive rewind menu, `Ctrl+G` editor, shell `!` prefix) have no external integration surface — they are REPL-only.

Four candidate local systems reviewed and skipped due to workflow/invocation mechanism mismatch or orthogonal scope.
