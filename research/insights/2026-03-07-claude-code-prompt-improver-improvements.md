---
title: "Improvement Proposals: Claude Code Prompt Improver"
---

## Improvement 1: Add hook+skill two-layer prompt evaluation recipe to hooks-patterns

**Source pattern**: "Wraps prompts with evaluation instructions (~189 tokens); Claude evaluates clarity using conversation history; If vague: Instructs Claude to invoke prompt-improver skill" (research entry, Architecture section, lines 44-46). The hook layer evaluates prompt clarity at ~189 tokens overhead; only when the prompt is vague does it invoke a full skill. This creates a two-layer architecture: lightweight hook for evaluation, heavyweight skill for deep research.
**Local system**: plugins/plugin-creator/skills/hooks-patterns/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #505 created

### Current state

The `hooks-patterns` SKILL.md contains a `UserPromptSubmit` example (line 306, "Python: UserPromptSubmit Context and Validation") that demonstrates JSON output and context injection. However, this example only shows how to validate and add context to a prompt. It does not demonstrate the pattern of:
1. Evaluating prompt clarity within the hook (lightweight, ~189 tokens)
2. Conditionally invoking a skill only when the prompt is vague (via `additionalContext` instructing Claude to call `Skill()`)
3. Providing bypass prefixes to skip evaluation entirely

The `hooks-core-reference` SKILL.md lists `UserPromptSubmit` as an event (line 24) with use case "Input validation" but does not document the hook-to-skill conditional invocation pattern.

### Target state

The `hooks-patterns` SKILL.md includes a new recipe section titled "UserPromptSubmit: Conditional Skill Invocation (Two-Layer Pattern)" that demonstrates:
1. A hook script that reads stdin JSON, checks for bypass prefixes (e.g., `*`, `/`), wraps the prompt with a clarity evaluation instruction, and outputs `additionalContext` that tells Claude to invoke a specific skill only if the prompt is vague
2. The corresponding skill structure (SKILL.md with research and question-generation phases)
3. Token overhead measurement: documenting the hook's token cost for the common case (clear prompts)

### Measurable signal

`hooks-patterns/SKILL.md` contains a section header matching "Conditional Skill Invocation" or "Two-Layer Pattern". The section includes a code example showing `UserPromptSubmit` hook output with `additionalContext` that references `Skill()` invocation. The section documents bypass prefix handling.

---

## Improvement 2: Add per-hook token overhead measurement to hook-creator guidance

**Source pattern**: "Per-prompt overhead (v0.4.0): ~189 tokens (evaluation prompt only)" and "30-message session: ~5.7k tokens (~2.8% of 200k context window)" (research entry, Features section, lines 124-127). The prompt-improver project explicitly measures and documents per-hook token overhead.
**Local system**: plugins/plugin-creator/skills/hook-creator/SKILL.md
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: The local hook-creator skill focuses on Node.js .cjs scripts, and token overhead measurement would require a different approach than the Python-based prompt-improver. The repo already has token counting infrastructure in `plugin_validator.py` for skills, but extending it to measure hook injection overhead would require verifying that the same counting approach applies to hook `additionalContext` strings. The gap is real in concept but the implementation path is unclear.

### Current state

The `hook-creator` SKILL.md provides a Node.js hook template and guidance on event selection, timeout sizing, and stdio suppression. It does not include any guidance on measuring or documenting the token overhead that a hook's `additionalContext` or evaluation prompt adds to the context window.

### Target state

The `hook-creator` SKILL.md includes a "Token Overhead" section advising hook authors to: (a) count the tokens in their `additionalContext` string, (b) document the per-invocation overhead in the hook's description or README, and (c) calculate cumulative session overhead (overhead x expected invocations per session).

### Measurable signal

`hook-creator/SKILL.md` contains a section on token overhead measurement. The section references the repo's existing token counting approach from `plugin_validator.py`.

---

## Improvement 3: Add conversation-history-first check to research-phase agent prompts

**Source pattern**: "Check conversation history before exploring codebase" (research entry, Features section, line 117). The prompt-improver's research phase explicitly checks existing conversation context before launching codebase exploration to avoid redundant work.
**Local system**: .claude/skills/add-new-feature/SKILL.md (Phase 1 agents: feature-researcher, codebase-analyzer)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: The local research agents (feature-researcher, codebase-analyzer) are delegated via the Agent tool, which provides them with the full conversation context implicitly. Claude models naturally consider conversation history. Whether an explicit instruction to "check conversation history first" would materially change behavior is unverifiable without experimentation. The absence of the instruction does not confirm the absence of the behavior.

### Current state

The `add-new-feature` SKILL.md spawns a `feature-researcher` agent and a `codebase-analyzer` agent sequentially. Neither agent's delegation prompt explicitly instructs "check conversation history before exploring the codebase." The agents receive conversation context implicitly through the Agent tool.

### Target state

The `feature-researcher` agent prompt includes an explicit instruction: "Before starting codebase exploration, check the conversation history for context already provided by the user (file paths mentioned, error messages shared, prior answers to questions). Skip research steps that would duplicate information already in the conversation."

### Measurable signal

The feature-researcher agent prompt (in `.claude/agents/` or in the delegation prompt within `add-new-feature/SKILL.md`) contains an instruction referencing conversation history as a first step before codebase exploration.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Per-hook token overhead measurement | Medium | Implementation path unclear -- would need to verify that plugin_validator.py token counting can be reused for hook additionalContext strings. Read hook-creator SKILL.md and plugin_validator.py token counting module to confirm feasibility. |
| Conversation-history-first check in research agents | Low | Claude models implicitly use conversation context. Would need A/B experiment to verify whether explicit instruction changes behavior. Check feature-researcher agent prompt for existing implicit handling. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Progressive disclosure (loading reference materials only when needed) | Already covered. The skill-creator SKILL.md documents progressive disclosure as a core principle. The plugin_validator.py includes a progressive disclosure validator (test_progressive_disclosure_validator.py). Reference files are widely used across the repo. |
| Testing plugins (comprehensive test suite for hooks, skills, end-to-end) | Already covered. The plugin-creator plugin has 21 test files in plugins/plugin-creator/tests/ including test_hook_validator.py, test_hook_script_discovery.py, test_progressive_disclosure_validator.py, and more. |
| Research-grounded question generation using TodoWrite | Too abstract for this repo's context. The prompt-improver uses TodoWrite for research planning before asking clarifying questions, which is specific to the prompt-improvement domain. The repo's /add-new-feature skill uses a different multi-agent research approach. No concrete local file gap identified. |
