# Improvement Proposals: Claude Code CLI Power Patterns

**Research entry**: ./research/developer-tools/claude-code-cli-power-patterns.md
**Generated**: 2026-03-24
**Patterns assessed**: 8
**Backlog items created**: 2 (issues: #1061, #1062)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Add effort level control to kage-bunshin spawn and work-milestone dispatch

**Source pattern**: "Opus 4.6 Effort Levels (`/model` command + `CLAUDE_CODE_EFFORT_LEVEL` env var) [...] Being intentional about compute allocation across hundreds of automated invocations adds up fast in both cost and pipeline speed." (Relevance section, pattern 5; Key Features section 5)
**Local system**: `plugins/development-harness/skills/kage-bunshin/SKILL.md`, `plugins/development-harness/skills/work-milestone/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1061 created

### Current state

`kage-bunshin/scripts/spawn.py` accepts `--model` to select the model (haiku, sonnet, opus) but has no `--effort` flag to set `CLAUDE_CODE_EFFORT_LEVEL` on the spawned `claude` process. The `work-milestone/SKILL.md` hardcodes `--model sonnet` in its spawn command template (line 48: `claude -p --model sonnet`) without any effort level parameter. The `model-selection.md` rule in `.claude/rules/` maps agents to models but does not mention effort tiers. As a result, all spawned sessions run at the default effort level regardless of task complexity. Coordinator sessions doing simple dispatch run at the same compute intensity as sessions doing architectural reasoning.

### Target state

`spawn.py` accepts `--effort {low|medium|high|max}` flag. When provided, the spawned `claude` process inherits `CLAUDE_CODE_EFFORT_LEVEL={value}` in its environment. `work-milestone/SKILL.md` dispatch plan schema includes an optional `effort` field per wave item, defaulting to the model's default effort. The `model-selection.md` rule includes effort tier guidance alongside model selection (e.g., haiku coordinators at low effort, sonnet implementers at high effort).

### Measurable signal

1. `uv run plugins/development-harness/skills/kage-bunshin/scripts/spawn.py spawn --help` shows `--effort` flag with choices `{low,medium,high,max}`.
2. Spawning with `--effort low` results in the child process environment containing `CLAUDE_CODE_EFFORT_LEVEL=low` (observable via `tmux send-keys "! env | grep EFFORT"`).
3. `.claude/rules/model-selection.md` contains an effort tier section.

---

## Improvement 2: Add --max-turns safety cap to work-milestone spawned sessions

**Source pattern**: "You need both `--max-turns` and `--max-budget-usd`. Either one alone has gaps." (Key Features section 10; Relevance section, pattern 2)
**Local system**: `plugins/development-harness/skills/work-milestone/SKILL.md`
**Confidence**: High
**Impact**: High
**Backlog**: #1062 created

### Current state

`work-milestone/SKILL.md` spawns `claude -p` sessions per wave item (line 48) with `--model sonnet --permission-mode auto --output-format json` but passes neither `--max-turns` nor `--max-budget-usd`. The kage-bunshin skill supports `--max-budget` but not `--max-turns`. A runaway agent in a wave item can loop indefinitely, consuming API credits and blocking the wave from completing. The research entry explicitly states that budget caps alone have gaps -- a session can burn through turns doing no useful work while staying under budget.

### Target state

`work-milestone/SKILL.md` spawn command template includes both `--max-turns {N}` and `--max-budget-usd {N}` with configurable defaults. The dispatch plan schema (produced by `/groom-milestone`) includes optional `max_turns` and `max_budget` fields per wave item, with plan-level defaults. `spawn.py` accepts `--max-turns` flag and passes it through to the `claude` CLI invocation.

### Measurable signal

1. `uv run plugins/development-harness/skills/kage-bunshin/scripts/spawn.py spawn --help` shows `--max-turns` flag.
2. `work-milestone/SKILL.md` spawn command template in the Mermaid diagram includes `--max-turns` and `--max-budget-usd`.
3. A spawned session with `--max-turns 50` exits after 50 turns even if work remains (verifiable via exit status in result JSON).

---

## Improvement 3: Add JSON schema constraint to work-milestone result parsing

**Source pattern**: "`--json-schema` accepts a path to a JSON Schema file that defines the exact output shape. The model is constrained to produce exactly that schema [...] Output becomes predictable and machine-consumable." (Key Features section 7; Relevance section, pattern 8)
**Local system**: `plugins/development-harness/skills/work-milestone/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: work-milestone already uses `--output-format json` and parses specific fields (STATUS, BRANCH, FILES_CHANGED, COMMITS, NOTES) from result JSON. It is unclear whether the current parsing fails on malformed output frequently enough to justify a schema constraint. The gap is plausible but would need evidence of parsing failures to confirm.

### Current state

`work-milestone/SKILL.md` passes `--output-format json` to spawned sessions (line 48) and expects result JSON at `/tmp/kb-work-{issue}.json` with fields STATUS, BRANCH, FILES_CHANGED, COMMITS, NOTES (line 60-61). There is no JSON schema file constraining this output shape. If a spawned session produces malformed or unexpected JSON, the parsing step (Step 6b) fails silently or with an unhelpful error.

### Target state

A JSON schema file exists at `plugins/development-harness/skills/work-milestone/schemas/wave-item-result.schema.json` defining the exact output shape. The spawn command includes `--json-schema ./schemas/wave-item-result.schema.json`. Result parsing validates against the schema before extracting fields.

### Measurable signal

1. File `plugins/development-harness/skills/work-milestone/schemas/wave-item-result.schema.json` exists and validates with `python -m json.tool`.
2. `work-milestone/SKILL.md` spawn command template includes `--json-schema` flag.

---

## Improvement 4: Add effort-aware model routing to agentskill-kaizen transcript analysis

**Source pattern**: "Cost-performance misalignment -- Default configurations burn high-cost compute (Opus) on low-complexity tasks [...] leading to both poor outputs and inflated API bills." (Problem Addressed, item 3; Relevance section, pattern 5)
**Local system**: `plugins/agentskill-kaizen/skills/transcript-analysis/SKILL.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: the transcript-analysis skill analyzes session data after the fact. Adding effort-level detection to the analysis dimensions would require the transcript JSONL to contain effort level metadata, which is not confirmed to exist in the schema. The gap is inferred from the research entry's cost-optimization pattern but not directly observable in the transcript schema.

### Current state

The transcript-analysis skill (10 analysis dimensions in SKILL.md) does not include effort level analysis as a signal dimension. There is no detection of whether sessions used appropriate effort levels for their task complexity. The kaizen-improvement skill generates improvement proposals but none address effort-level misconfiguration.

### Target state

Transcript analysis includes an 11th dimension: "Effort Level Appropriateness" -- detecting sessions where high-effort was used for low-complexity tasks (boilerplate, renaming) or low-effort for high-complexity tasks (architecture, merge conflicts). Requires effort level metadata in JSONL records.

### Measurable signal

`transcript-analysis/SKILL.md` contains a section "### 11. Effort Level Appropriateness" with extraction methodology.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| JSON schema constraint for work-milestone results | Medium | Need evidence of parsing failures from malformed agent output to confirm the gap is causing real problems. The current approach (unschema'd JSON + field extraction) may be sufficient. |
| Effort-level analysis in transcript-analysis | Low | Requires confirmation that JSONL transcripts contain effort level metadata. Without that metadata, the analysis dimension cannot be implemented. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Session forking / context pre-warming | The local system uses SAM artifacts for context transfer between tasks rather than session forking. Different architectural approach -- SAM's stateless artifact handoff is intentional and provides reproducibility that session forking does not. Not a gap. |
| Code review loops (`--from-pr`) | The local system uses `complete-implementation` with backlog_view + issue linking for PR-based quality gates. Equivalent coverage via different mechanism. |
| Parallel worktrees | Already implemented in kage-bunshin (`--worktree` flag) and work-milestone. Already tracked in backlog: #974, #975, #928, #453. |
| Dynamic subagents (`--agents` JSON) | Architecturally incompatible. This repo enforces persistent agent files with frontmatter validation, quality controls, and version-tracked definitions. Ad-hoc session-scoped agents bypass these controls by design. The `--agents` pattern solves a different problem (quick prototyping) than what this repo optimizes for (reproducible, auditable agent behavior). |
| Context compaction (rewind menu) | UI-only feature. Not programmable or usable in automated workflows. No actionable gap. |
| Editor-based prompt composition (Ctrl+G) | User-facing interactive feature. No mapping to automated skill/agent workflows. |
