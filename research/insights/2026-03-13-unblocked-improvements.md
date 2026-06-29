---
title: "Improvement Proposals: Unblocked"
---

## Improvement 1: Project-specific pattern retrieval in code-reviewer agent

**Source pattern**: "Code Generation Fidelity: By providing architectural context and team patterns to Claude Code's code generation capabilities, agents produce code that aligns with existing systems without requiring human review cycles." (Relevance section, item 1) and "Code Review Automation: Unblocked's AI code review feature can serve as a first-pass reviewer for Claude Code-generated PRs, catching logical errors and pattern violations before human review." (Relevance section, item 5)
**Local system**: plugins/python3-development/agents/code-reviewer.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the code-reviewer loads skills (python3-development, holistic-linting, validation-protocol) that may already inject project-specific patterns at runtime; would need to trace skill content to confirm the gap

### Current state

The code-reviewer agent (plugins/python3-development/agents/code-reviewer.md) reviews code against a static set of generic Python standards hardcoded in the agent file (layered architecture, Typer/Click patterns, shared/ module conventions, pytest). It does not dynamically retrieve project-specific conventions, historical decisions from git history, or prior PR review patterns. The agent receives the task file path and reviews against its built-in checklist.

### Target state

The code-reviewer agent incorporates project-specific context before reviewing: reads `CLAUDE.md` and any project-level `.claude/rules/` files from the target project, references prior review findings from the same feature (e.g., follow-up task files from earlier reviews), and checks git log for recent patterns in the files under review. The review checklist dynamically adapts to the project's actual conventions rather than applying only generic Python standards.

### Measurable signal

The code-reviewer agent's review output references at least one project-specific convention from CLAUDE.md or rules/ that is not hardcoded in the agent file. Visible in the NOTES section of the agent's STATUS: DONE output.

---

## Improvement 2: Source deconfliction for contradicting context sources

**Source pattern**: "Source Deconfliction -- When multiple sources contradict each other, resolves via 'recency + authority signals' to determine the authoritative answer." (Architecture section, Mechanism 3) referenced indirectly via "Code Generation Fidelity: agents produce code that aligns with existing systems" (Relevance section, item 1)
**Local system**: .claude/CLAUDE.md, .claude/rules/, MEMORY.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the research entry describes this pattern in Unblocked's Architecture section but does not explicitly name it as a pattern to adopt in the Relevance section; the gap is inferred from the code generation fidelity pattern rather than directly observed

### Current state

The local context system loads CLAUDE.md, rules/ files, and MEMORY.md into the agent's context window. When these sources contradict each other (e.g., a rule in CLAUDE.md conflicts with a skill's instructions, or a memory entry overrides an older rule), there is no explicit precedence mechanism. The agent must infer which source takes priority. The Contamination Response Protocol in CLAUDE.md addresses invalid data after discovery but does not prevent contradictions from reaching the agent in the first place.

### Target state

A documented precedence hierarchy in CLAUDE.md or a rules/ file that explicitly states resolution order when sources conflict. For example: "When MEMORY.md contradicts CLAUDE.md, MEMORY.md takes precedence (more recent). When a rules/ file contradicts CLAUDE.md, the rules/ file takes precedence (more specific). When a skill's instructions contradict CLAUDE.md, the skill takes precedence within its activation scope." The hierarchy is stated once and referenced by agents during context loading.

### Measurable signal

A section titled "Source Precedence" or equivalent exists in .claude/CLAUDE.md or .claude/rules/ that explicitly ranks context sources by authority. Agents encountering contradictions can reference this section to resolve them without human intervention.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Project-specific pattern retrieval in code-reviewer | medium | The code-reviewer loads skills (python3-development, holistic-linting, validation-protocol) that may already inject project-specific context at runtime; tracing skill content at execution time is needed to confirm the gap |
| Source deconfliction for contradicting context sources | low | The research entry describes source deconfliction in the Architecture section but does not explicitly recommend it in the Relevance section; the gap is inferred rather than directly stated; the local system may handle this implicitly through load order |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| MCP Integration for real-time context query (Relevance item 2) | This is a utilization opportunity (use Unblocked as an MCP server), not a system improvement pattern; belongs in utilization assessment, not improvement proposals |
| Development Speed -- 83% faster (Relevance item 3) | Marketing metric with no concrete mechanism to adopt; "single-pass completion with minimal rework" is the outcome of all other patterns, not an independent pattern |
| Onboarding and Knowledge Management (Relevance item 4) | Already tracked in backlog as #124 "SAM: Training/Onboarding Materials" |
