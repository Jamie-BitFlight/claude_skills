---
title: "Claude Code Prompt Improver"
---

# Claude Code Prompt Improver

## Identity

**Repository:** [severity1/claude-code-prompt-improver](https://github.com/severity1/claude-code-prompt-improver)
**Author:** severity1
**Version:** 0.5.1 (released 2026-02-14)
**License:** MIT
**Language:** Python
**Repository size:** 3,227 KB (GitHub-reported)

## Overview

"A UserPromptSubmit hook that enriches vague prompts before Claude Code executes them. Uses the AskUserQuestion tool (Claude Code 2.0.22+) for targeted clarifying questions" (README.md, line 3). The tool intercepts user prompts submitted to Claude Code and evaluates their clarity before execution. Clear prompts proceed without modification; vague prompts trigger the invocation of the `prompt-improver` skill, which conducts systematic research and asks 1-6 grounded clarifying questions based on actual project context before proceeding with the original request.

## Repository Statistics

- **GitHub stars:** 1,198 (as of 2026-03-07)
- **Forks:** 104
- **Open issues:** 4
- **Contributors:** 2 (severity1: 27 commits; claude: 3 commits)
- **Repository created:** 2025-10-18
- **Last updated:** 2026-03-07
- **Last commit pushed:** 2026-02-14

SOURCE: GitHub REST API (`repos/severity1/claude-code-prompt-improver`) (accessed 2026-03-07)

## Architecture

The system is composed of two primary layers working in concert:

### Hook Layer (scripts/improve-prompt.py)

The hook is a lightweight evaluation orchestrator (~70 lines of Python) that acts as the entry point for all prompt submissions.

**Mechanism:**
- Intercepts prompts via the `UserPromptSubmit` hook mechanism
- Reads stdin JSON formatted as `{"prompt": "user input"}`
- Handles three bypass prefixes: `*` (skip evaluation), `/` (slash commands), `#` (memorize)
- Wraps the original prompt with an evaluation instruction block (~189 tokens)
- Outputs structured JSON: `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}`

**Evaluation phase:**
"Wraps prompts with evaluation instructions (~189 tokens); Claude evaluates clarity using conversation history; If vague: Instructs Claude to invoke prompt-improver skill" (README.md, lines 168-170).

**Bypass behavior:**
When a prompt begins with `*`, the hook strips the prefix and outputs the cleaned prompt without evaluation. Slash commands (e.g., `/help`, `/plugin`) and memorize commands (prefixed with `#`) pass through unchanged, bypassing evaluation entirely.

### Skill Layer (skills/prompt-improver/)

"SKILL.md: Research and question workflow (~170 lines); Assumes prompt already determined vague by hook; 4-phase process: Research → Questions → Clarify → Execute; Links to reference files for progressive disclosure" (README.md, lines 174-176).

**When invoked:**
The skill is invoked ONLY when the hook-level evaluation determines the prompt is vague (missing target, context, or specificity). The skill assumes evaluation is complete and proceeds directly to research and question generation.

**Four-phase workflow:**

1. **Research:** "Create a dynamic research plan using TodoWrite before asking questions" (SKILL.md, line 35). Research plan template includes: check conversation history first, review codebase using Task/Explore for architecture and Grep/Glob for patterns, gather additional context via local files or web, and document findings (SKILL.md, lines 37-48).

2. **Generate Targeted Questions:** "Based on research findings, formulate 1-6 questions that will clarify the ambiguity" (SKILL.md, lines 59). Guidelines require that every option comes from research (codebase findings, documentation, common patterns), avoiding generic or assumption-based options (SKILL.md, lines 62-66).

3. **Get Clarification:** "Use the AskUserQuestion tool to present your research-grounded questions" (SKILL.md, line 77). Questions are presented in structured format with header, multiple choice options, descriptions, and multiSelect field.

4. **Execute with Context:** "Proceed with the original user request using original prompt intent, clarification answers from user, research findings and context, and conversation history" (SKILL.md, lines 92-97).

**Reference files (progressive disclosure):**
- `references/question-patterns.md` — Question templates and effective patterns (200-300 lines)
- `references/research-strategies.md` — Context gathering strategies (300-400 lines)
- `references/examples.md` — Real prompt transformations and examples (200-300 lines)

Reference files load only when the skill is invoked for a vague prompt, ensuring zero overhead for clear prompts.

### Architectural Separation

"Flow for Clear Prompts: 1. Hook wraps with evaluation prompt (~189 tokens); 2. Claude evaluates: prompt is clear; 3. Claude proceeds immediately (no skill invocation); 4. Total overhead: ~189 tokens" (README.md, lines 182-186).

"Flow for Vague Prompts: 1. Hook wraps with evaluation prompt (~189 tokens); 2. Claude evaluates: prompt is vague; 3. Claude invokes prompt-improver skill; 4. Skill loads research/question guidance; 5. Claude creates research plan, gathers context, asks questions; 6. Total overhead: ~189 tokens + skill load" (README.md, lines 188-195).

This architectural separation achieves significant token savings for the common case (clear prompts) while maintaining comprehensive guidance for vague prompts.

## Features

### 1. Clarity Evaluation

The hook evaluates whether a prompt is clear enough to execute immediately or requires enrichment. Evaluation uses conversation history to avoid redundant exploration.

**Implementation:** "Wrapped prompt includes evaluation instructions: PROCEED IMMEDIATELY if prompt is detailed/specific OR has sufficient context OR can infer intent. ONLY USE SKILL if genuinely vague" (scripts/improve-prompt.py, lines 58-61).

### 2. Bypass Prefixes

Users can skip evaluation entirely using three bypass mechanisms:

- **`*` prefix:** "User explicitly bypassed improvement - remove * prefix" (scripts/improve-prompt.py, line 36). Example: `claude "* add dark mode"` skips evaluation.
- **`/` prefix:** Slash commands (built-in and custom) bypass automatically without modification.
- **`#` prefix:** Memorize feature (e.g., `# remember to use rg over grep`) bypasses evaluation.

### 3. Research Planning

For vague prompts, the skill generates a dynamic research plan before asking questions. "Create a dynamic research plan using TodoWrite before asking questions" (SKILL.md, line 35). The plan is structured as:

1. Check conversation history first (avoid redundant exploration)
2. Review codebase (Task/Explore for architecture, Grep/Glob for patterns, git log for recent changes, search for errors/TODOs)
3. Gather additional context (local docs, web documentation, best practices via WebSearch)
4. Document findings to ground questions

### 4. Question Generation

Questions are generated from research findings, not assumptions. "Grounded: Every option comes from research (codebase findings, documentation, common patterns)" (SKILL.md, line 62). Questions follow multiple-choice format with 2-4 concrete options per question.

**Question count guidance:**
- **1-2 questions:** Simple ambiguity (which file? which approach?)
- **3-4 questions:** Moderate complexity (scope + approach + validation)
- **5-6 questions:** Complex scenarios (major feature with multiple decision points)

### 5. Conversation History Awareness

"Check conversation history before exploring codebase" (SKILL.md, line 52). The evaluation and research phases check existing conversation context to avoid redundant exploration, making the tool more efficient in multi-turn conversations.

### 6. Token Efficiency

"v0.4.0 Update: Skill-based architecture with hook-level evaluation achieves 31% token reduction. Clear prompts have zero skill overhead, vague prompts get comprehensive research and questioning via the skill" (README.md, line 17).

**Metrics:**
- **Per-prompt overhead (v0.4.0):** ~189 tokens (evaluation prompt only)
- **Per-prompt overhead (v0.3.x):** ~275 tokens (embedded evaluation logic)
- **Token reduction:** ~86 tokens saved per prompt (31% decrease)
- **30-message session:** ~5.7k tokens (~2.8% of 200k context window), down from ~8.3k (4.1% of 200k)

## Usage

### Normal Use

Prompts submitted normally trigger the hook evaluation and may result in clarifying questions:

```bash
claude "fix the bug"      # Hook evaluates, may ask questions
claude "add tests"        # Hook evaluates, may ask questions
```

### Vague Prompt Example

```bash
claude "fix the error"
```

Claude asks (using AskUserQuestion):

```
Which error needs fixing?
  ○ TypeError in src/components/Map.tsx (recent change)
  ○ API timeout in src/services/osmService.ts
  ○ Other (paste error message)
```

User selects, Claude proceeds with full context.

### Clear Prompt Example

```bash
claude "Fix TypeError in src/components/Map.tsx line 127 where mapboxgl.Map constructor is missing container option"
```

Claude proceeds immediately without questions (evaluation overhead only, ~189 tokens).

### Bypass Usage

- **Skip evaluation:** `claude "* add dark mode"` (evaluates to "add dark mode")
- **Slash commands:** `/help`, `/plugin` bypass automatically
- **Memorize:** `claude "# remember to use rg over grep"` bypasses evaluation

## Installation

### Option 1: Via Marketplace (Recommended)

1. Add marketplace: `claude plugin marketplace add severity1/severity1-marketplace`
2. Install plugin: `claude plugin install prompt-improver@severity1-marketplace`
3. Restart Claude Code
4. Verify: `/plugin` command should show "prompt-improver" installed

### Option 2: Local Development Installation

1. Clone the repository: `git clone https://github.com/severity1/claude-code-prompt-improver.git && cd claude-code-prompt-improver`
2. Add local marketplace: `claude plugin marketplace add /absolute/path/to/claude-code-prompt-improver/.dev-marketplace/.claude-plugin/marketplace.json`
3. Install: `claude plugin install prompt-improver@local-dev`
4. Restart Claude Code

### Option 3: Manual Hook Installation

1. Copy hook: `cp scripts/improve-prompt.py ~/.claude/hooks/ && chmod +x ~/.claude/hooks/improve-prompt.py`
2. Update `~/.claude/settings.json` with hook configuration
3. Restart Claude Code

## Compatibility & Requirements

"Requirements: Claude Code 2.0.22+ (uses AskUserQuestion tool for targeted clarifying questions)" (README.md, line 48).

The tool requires Claude Code version 2.0.22 or later because it depends on the `AskUserQuestion` tool for presenting structured multiple-choice questions. Older versions lack this tool and will not function properly.

## Design Philosophy

"Rarely intervene - Most prompts pass through unchanged; Trust user intent - Only ask when genuinely unclear; Use conversation history - Avoid redundant exploration; Max 1-6 questions - Enough for complex scenarios, still focused; Transparent - Evaluation visible in conversation" (README.md, lines 155-159).

The tool prioritizes non-interference—most prompts bypass questioning entirely. When questions are asked, they are grounded in actual project research rather than generic assumptions. Users remain in control through bypass prefixes and explicit confirmation before execution.

## Limitations and Caveats

1. **Evaluation accuracy depends on conversation context:** The hook's clarity evaluation uses conversation history, which means earlier clarifications or context may influence later evaluation. Out-of-context requests may be flagged as vague even if the user intends them to be terse.

2. **Vague prompts may require extensive research:** For genuinely ambiguous requests in complex projects, research phase may need to read multiple files, codebase sections, and documentation. This can be slower than direct execution.

3. **Limited to Claude Code environment:** The tool is designed specifically for Claude Code and integrates with its hook system and tools (AskUserQuestion, TodoWrite, Task/Explore, Grep/Glob, WebSearch). It does not work in other environments.

4. **Four-phase workflow adds latency for vague prompts:** While clear prompts have minimal overhead, vague prompts incur overhead from research planning (TodoWrite), context gathering (reads/searches), and question presentation (AskUserQuestion). The total latency depends on research scope.

5. **No persistent memory of research across sessions:** Research findings and clarifications are documented within the current session but are not automatically preserved between Claude Code sessions. Users may need to re-answer similar questions in new sessions.

6. **Question generation depends on research depth:** If the research phase returns minimal findings (e.g., in a new project with little documentation), generated questions may lack specificity. The tool performs research but cannot guarantee rich context will be found.

## Testing

"Test suite: 24 tests (100% passing) validate all components. Tests include: Hook tests (8 tests); Skill tests (9 tests); Integration tests (7 tests)" (CHANGELOG.md, lines 25-28).

The repository includes a comprehensive test suite:

- **Hook tests (`tests/test_hook.py`):** Validates JSON output, bypass prefix handling, escape sequences
- **Skill tests (`tests/test_skill.py`):** YAML frontmatter validation, file structure, reference file existence
- **Integration tests (`tests/test_integration.py`):** End-to-end flow, plugin configuration, token overhead calculations

All tests use pytest and the Python standard library only. Tests can be run via `pytest tests/` or `python -m pytest`.

## Relevance to Claude Code Development

This tool directly addresses a common pain point in Claude Code usage: prompts that are too vague or lack sufficient context often result in sub-optimal outcomes. By automatically detecting vagueness and asking clarifying questions before execution, the tool improves first-attempt accuracy and reduces back-and-forth iterations.

For Claude Code plugin developers, this repository demonstrates best practices for:

- **Hook-based architecture:** Using hooks to intercept and modify behavior without modifying core Claude Code
- **Skill integration:** Building skills that integrate with hook evaluation
- **Progressive disclosure:** Loading reference materials only when needed
- **Testing plugins:** Comprehensive test suite for hooks, skills, and end-to-end flows
- **Token efficiency:** Optimizing for the common case (clear prompts) while maintaining comprehensive guidance for complex scenarios

## References

- [GitHub Repository](https://github.com/severity1/claude-code-prompt-improver) (accessed 2026-03-07)
- [README.md](https://github.com/severity1/claude-code-prompt-improver/blob/main/README.md) (accessed 2026-03-07)
- [CHANGELOG.md](https://github.com/severity1/claude-code-prompt-improver/blob/main/CHANGELOG.md) (accessed 2026-03-07)
- [SKILL.md](https://github.com/severity1/claude-code-prompt-improver/blob/main/skills/prompt-improver/SKILL.md) (accessed 2026-03-07)
- [CLAUDE.md](https://github.com/severity1/claude-code-prompt-improver/blob/main/CLAUDE.md) (accessed 2026-03-07)
- [scripts/improve-prompt.py](https://github.com/severity1/claude-code-prompt-improver/blob/main/scripts/improve-prompt.py) (accessed 2026-03-07)
- [hooks/hooks.json](https://github.com/severity1/claude-code-prompt-improver/blob/main/hooks/hooks.json) (accessed 2026-03-07)
- [.claude-plugin/plugin.json](https://github.com/severity1/claude-code-prompt-improver/blob/main/.claude-plugin/plugin.json) (accessed 2026-03-07)
