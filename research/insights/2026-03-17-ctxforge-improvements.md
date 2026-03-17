# Improvement Proposals: ctxforge

**Research entry**: ./research/prompt-engineering/ctxforge.md
**Generated**: 2026-03-17
**Patterns assessed**: 6
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Auto-applied performance and security directives for implementation agents

**Source pattern**: "PERFORMANCE-DIRECTIVES.md provides actionable quality standards (30+ rules) that can be auto-applied: algorithmic efficiency targets, memory management patterns, accessibility compliance, security baselines. These are language-agnostic and testable." (Relevance section, item 4)
**Local system**: `.claude/rules/` directory and `plugins/python3-development/skills/complete-implementation/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: existing `.claude/rules/` files cover structural and formatting concerns (silent failure prevention, markdown formatting, linting). The code-reviewer agent and complete-implementation quality gates may already enforce performance and security standards through their built-in knowledge, but this has not been verified by reading those agents' full prompts and confirming coverage of algorithmic efficiency targets, memory management patterns, or accessibility compliance.

### Current state

The `.claude/rules/` directory contains 13 rule files focused on structural concerns: silent failure prevention, large file write strategy, interactive terminal workarounds, language conventions, script invocation, linting exceptions, CI workflows, YAML/TOML libraries, plugin development, skill content optimization, frontmatter requirements, delegation format, and model selection. None of these files contain performance targets (e.g., algorithmic complexity bounds), memory management patterns (e.g., cleanup requirements, lazy loading), security baselines (e.g., input validation requirements, OWASP references), or accessibility compliance standards (e.g., WCAG). Quality enforcement occurs post-implementation via the `code-reviewer` agent in `/complete-implementation` Phase 1, but there is no pre-implementation directive document that implementation agents receive automatically.

### Target state

A `.claude/rules/implementation-quality-directives.md` file containing testable performance, security, and accessibility rules that are loaded into every implementation agent's context during `/start-task` execution. Rules would include: algorithmic efficiency bounds for user-facing operations, memory cleanup requirements, input validation standards, and error handling patterns. The `/start-task` skill would reference this file so sub-agents receive the directives before writing code, not only after (via code review).

### Measurable signal

File `.claude/rules/implementation-quality-directives.md` exists with at least 10 testable rules covering performance, security, and accessibility. The `/start-task` SKILL.md or the `feature-researcher` agent prompt references this file. Code-reviewer findings related to performance and security decrease after directives are applied (measured by comparing follow-up task file creation rate before and after).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Auto-applied performance and security directives | Medium | Need to verify whether code-reviewer agent and complete-implementation quality gates already enforce equivalent performance/security/accessibility standards through their built-in prompts. Read the full code-reviewer.md and feature-verifier.md agent files to confirm coverage gaps before creating a backlog item. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Context Engineering Patterns (requirement extraction with confidence levels) | Already covered -- the local system uses a question-first approach via feature-discovery skill and feature-researcher agent (WHO/WHAT/WHEN/WHY analysis, gap analysis, structured questions with blocking status). This is architecturally stronger than ctxforge's assumption-with-confidence approach because it prevents assumptions rather than labeling them. File: `plugins/plugin-creator/skills/feature-discovery/SKILL.md` sections Step 2-Step 5. |
| 16 Specialized Protocols (task-type workflows) | Already covered -- the local skill system provides more than 16 specialized workflows (add-new-feature, implement-feature, complete-implementation, start-task, research-curator, backlog, etc.), each with task-type-specific discovery, execution, and validation steps. File: `plugins/python3-development/skills/` directory. |
| Token Efficiency (framework overhead budget tracking) | Already in backlog as #120 "SAM: Cost/Token Management" and #119 "Configurable Token Thresholds for plugin_validator.py". |
| Multi-Protocol Session Orchestration (switching workflows mid-session) | Already covered -- the skill system supports on-demand skill loading within a session. The `/implement-feature` execution loop switches between different agent types per task based on the task's `Agent` field. File: `plugins/python3-development/skills/implement-feature/SKILL.md` Progress Loop section. |
| Custom Protocol Development (extending via markdown configuration) | Already covered -- the `/plugin-creator:skill-creator` skill provides a complete workflow for creating custom skills via markdown-based configuration, including validation, progressive disclosure, and marketplace publication. File: `plugins/plugin-creator/skills/skill-creator/SKILL.md` referenced from `plugins/plugin-creator/CLAUDE.md`. |
