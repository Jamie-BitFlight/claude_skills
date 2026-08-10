---
name: Superpowers - Agentic Skills Framework and Software Development Methodology
description: Superpowers is a complete software development workflow for AI coding agents, built on composable skills that transform how agents approach development tasks. Rather than letting agents jump directly...
license: MIT
metadata:
  topic: superpowers
  category: agent-frameworks
  source_url: https://github.com/obra/superpowers
  version: "v4.1.1"
  verified: "2026-01-31"
  next_review: "2026-04-30"
---

## Overview

Superpowers is a complete software development workflow for AI coding agents, built on composable skills that transform how agents approach development tasks. Rather than letting agents jump directly into writing code, Superpowers enforces a structured methodology: specification refinement, design validation, implementation planning, and subagent-driven execution with automated review.

**Core Value Proposition**: Turn undirected AI coding sessions into disciplined, test-driven development workflows where agents can work autonomously for hours without deviating from approved plans.

---

## Problem Addressed

| Problem | How Superpowers Solves It |
|---------|---------------------------|
| AI agents jump directly to code without understanding requirements | Brainstorming skill forces design refinement before implementation |
| No test coverage, tests written after implementation | Test-driven-development skill enforces RED-GREEN-REFACTOR cycle |
| Agent context pollution across tasks | Fresh subagent per task with explicit context handoff |
| Quality issues discovered late | Two-stage review (spec compliance, then code quality) after each task |
| Implementation drift from specifications | Spec reviewer verifies code matches requirements exactly |
| Debugging by random changes | Systematic-debugging skill enforces root cause analysis |
| No clear completion criteria | Execution plans with verification steps and human checkpoints |

---

## Key Statistics (as of 2026-01-31)

| Metric | Value |
|--------|-------|
| GitHub Stars | 40,911 |
| Forks | 3,113 |
| Contributors | 15 |
| Open Issues | 108 |
| Skills Included | 14 |
| Supported Platforms | 3 (Claude Code, Codex, OpenCode) |
| Created | 2025-10-09 |
| Latest Release | v4.1.1 (2026-01-23) |

---

## Supported Platforms

| Platform | Installation Method | Integration Type |
|----------|---------------------|------------------|
| **Claude Code** | Plugin marketplace | Native plugin system |
| **Codex** | Manual fetch and follow | Instruction injection |
| **OpenCode** | Symlink to skills directory | Native skill tool |

---

## Key Features

### Workflow Skills

The framework provides 14 composable skills organized by function, each enforcing a specific discipline in the software development process.

#### Testing

- **test-driven-development**: RED-GREEN-REFACTOR cycle enforcement with testing anti-patterns reference

#### Debugging

- **systematic-debugging**: 4-phase root cause process with root-cause-tracing, defense-in-depth, and condition-based-waiting techniques
- **verification-before-completion**: Ensures fixes are actually verified before declaring success

#### Collaboration & Orchestration

- **brainstorming**: Socratic design refinement before implementation
- **writing-plans**: Detailed implementation plan creation with bite-sized tasks
- **executing-plans**: Batch execution with human checkpoints
- **dispatching-parallel-agents**: Concurrent subagent workflows
- **requesting-code-review**: Pre-review checklist for PR submissions
- **receiving-code-review**: Systematic response to feedback
- **using-git-worktrees**: Parallel development branches in isolated workspaces
- **finishing-a-development-branch**: Merge/PR decision workflow and cleanup
- **subagent-driven-development**: Fast iteration with two-stage review (spec compliance, then code quality)

#### Meta Skills

- **writing-skills**: Create new skills following TDD principles for documentation
- **using-superpowers**: Introduction to the skills system and discovery

---

## Skills Library

### Testing

| Skill | Purpose |
|-------|---------|
| **test-driven-development** | RED-GREEN-REFACTOR cycle enforcement; includes testing anti-patterns reference |

### Debugging

| Skill | Purpose |
|-------|---------|
| **systematic-debugging** | 4-phase root cause process; bundles root-cause-tracing, defense-in-depth, condition-based-waiting techniques |
| **verification-before-completion** | Ensure fixes are actually verified before declaring success |

### Collaboration

| Skill | Purpose |
|-------|---------|
| **brainstorming** | Socratic design refinement before implementation |
| **writing-plans** | Detailed implementation plan creation with bite-sized tasks |
| **executing-plans** | Batch execution with human checkpoints |
| **dispatching-parallel-agents** | Concurrent subagent workflows |
| **requesting-code-review** | Pre-review checklist for PR submissions |
| **receiving-code-review** | Responding to feedback systematically |
| **using-git-worktrees** | Parallel development branches in isolated workspaces |
| **finishing-a-development-branch** | Merge/PR decision workflow and cleanup |
| **subagent-driven-development** | Fast iteration with two-stage review (spec compliance, then code quality) |

### Meta

| Skill | Purpose |
|-------|---------|
| **writing-skills** | Create new skills following TDD principles for documentation |
| **using-superpowers** | Introduction to the skills system and discovery |

---

## Core Workflow

<eg>
User Request
     |
     v
+---------------------+
| 1. Brainstorming    |  <-- Questions one at a time, design in 200-300 word sections
| (before any code)   |      Saves design to docs/plans/YYYY-MM-DD-<topic>-design.md
+---------------------+
     |
     v
+---------------------+
| 2. Using Git        |  <-- Creates isolated workspace on new branch
|    Worktrees        |      Runs project setup, verifies clean test baseline
+---------------------+
     |
     v
+---------------------+
| 3. Writing Plans    |  <-- Breaks work into 2-5 minute tasks
| (with design)       |      Each task: file paths, complete code, verification steps
+---------------------+
     |
     v
+---------------------+
| 4. Subagent-Driven  |  <-- Fresh subagent per task
|    Development      |      Two-stage review: spec compliance, then code quality
|    OR               |      Review loops until approved
|    Executing Plans  |      Batch execution with human checkpoints
+---------------------+
     |
     v
+---------------------+
| 5. TDD Enforcement  |  <-- RED: Write failing test, watch it fail
|    (per task)       |      GREEN: Minimal code to pass
|                     |      REFACTOR: Clean up while staying green
+---------------------+
     |
     v
+---------------------+
| 6. Code Review      |  <-- Reviews against plan, reports by severity
| (between tasks)     |      Critical issues block progress
+---------------------+
     |
     v
+---------------------+
| 7. Finishing Branch |  <-- Verifies all tests pass
|                     |      Options: merge/PR/keep/discard
|                     |      Cleans up worktree
+---------------------+
</eg>

---

## Technical Architecture

### Subagent-Driven Development Architecture

The flagship workflow dispatches fresh subagents per task with explicit context and two-stage review:

<eg>
Controller (Main Agent)
         |
         | Reads plan once, extracts all tasks, creates TodoWrite
         |
         v
    +----+----+
    | Task N  |
    +----+----+
         |
         | Dispatches implementer with full task text + context
         v
  +--------------+
  | Implementer  |  <-- May ask clarifying questions
  | Subagent     |      Implements, tests, commits
  |              |      Self-reviews before reporting
  +--------------+
         |
         | Dispatches spec reviewer
         v
  +--------------+
  | Spec Review  |  <-- Verifies code matches spec exactly
  | Subagent     |      Catches missing AND extra features
  +--------------+
         |
         | If issues: implementer fixes, re-review
         | If pass: dispatches code quality reviewer
         v
  +--------------+
  | Code Quality |  <-- Reviews for clean code, test coverage
  | Subagent     |      Maintainability checks
  +--------------+
         |
         | If issues: implementer fixes, re-review
         | If pass: mark task complete, next task
         v
    [Next Task or Final Review]
</eg>

**Key Design Decisions**:

- Fresh subagent per task prevents context pollution
- Controller provides full task text (no file references)
- Questions surfaced before work begins
- Two-stage review catches spec drift AND quality issues
- Review loops ensure fixes actually work

---

## Installation & Usage

### Claude Code

```bash
# Register marketplace
/plugin marketplace add obra/superpowers-marketplace

# Install plugin
/plugin install superpowers@superpowers-marketplace

# Verify
/help
# Should show: /superpowers:brainstorm, /superpowers:write-plan, /superpowers:execute-plan
```

### Codex

<eg>
Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md
</eg>

### OpenCode

<eg>
Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
</eg>

---

## Key Technical Decisions

### DOT Flowcharts as Executable Specifications

Skills use GraphViz DOT flowcharts as the authoritative process definition, with prose as supporting content. This addresses the "Description Trap" where Claude follows short descriptions instead of detailed flowcharts.

**Rule**: Skill descriptions must be trigger-only ("Use when X") with no process details.

### Skill Triggering

Skills trigger automatically based on descriptions. The `using-superpowers` skill establishes the rule: "Invoke relevant or requested skills BEFORE any response or action."

**Priority Order**: Process skills (brainstorming, debugging) come before implementation skills.

### TDD for Skills

The `writing-skills` skill treats skill creation as TDD for documentation:

| TDD Concept | Skill Creation |
|-------------|----------------|
| Test case | Pressure scenario with subagent |
| Production code | SKILL.md document |
| RED (test fails) | Agent violates rule without skill |
| GREEN (test passes) | Agent complies with skill present |
| Refactor | Close loopholes while maintaining compliance |

---

## Philosophy

- **Test-Driven Development** - Write tests first, always
- **Systematic over ad-hoc** - Process over guessing
- **Complexity reduction** - Simplicity as primary goal
- **Evidence over claims** - Verify before declaring success
- **YAGNI ruthlessly** - Remove unnecessary features from all designs

---

## Relevance to Claude Code Development

### Direct Applications

1. **Skill Structure Reference**: The 14 skills provide battle-tested examples of SKILL.md format, frontmatter conventions, and reference file organization
2. **Subagent Coordination Patterns**: The subagent-driven-development workflow demonstrates effective Agent tool usage with explicit prompts
3. **Two-Stage Review Pattern**: Separating spec compliance from code quality review is adoptable for any multi-agent workflow
4. **TDD for Documentation**: The `writing-skills` approach of testing skills with subagent pressure scenarios is applicable to skill creation in this repository

### Patterns Worth Adopting

1. **Trigger-Only Descriptions**: Skill descriptions should say "Use when X" not "Does Y" to avoid the description trap
2. **DOT Flowcharts**: Using GraphViz diagrams as authoritative process definitions with prose as support
3. **Fresh Context Per Task**: Dispatching new subagents prevents context pollution in long workflows
4. **Questions Before Work**: Encouraging subagents to ask clarifying questions before implementation
5. **Review Loops Not One-Shots**: Reviews should verify fixes, not just report issues

### Integration Opportunities

1. The marketplace pattern (`/plugin marketplace add`) could inform plugin distribution for this repository
2. Cross-platform installation docs (Claude Code, Codex, OpenCode) provide templates for multi-agent-IDE skills
3. The test infrastructure (`tests/skill-triggering/`, `tests/claude-code/`) offers patterns for validating skill behavior

---

## Recent Release Highlights

### v4.1.1 (2026-01-23)

- OpenCode standardized on `plugins/` directory per official docs
- Fixed symlink instructions for reinstallation

### v4.1.0 (2026-01-23)

- OpenCode switched to native skills system (breaking change)
- Fixed agent reset on session start
- Fixed Windows installation across Claude Code, OpenCode

### v4.0.0 (2025-12-17)

- Two-stage code review (spec compliance + code quality)
- Debugging techniques consolidated with tools
- Testing anti-patterns reference
- Skill test infrastructure
- DOT flowcharts as executable specifications

---

## References

1. **GitHub Repository**: <https://github.com/obra/superpowers> (accessed 2026-01-31)
2. **Marketplace Repository**: <https://github.com/obra/superpowers-marketplace> (accessed 2026-01-31)
3. **Author Blog Post**: <https://blog.fsck.com/2025/10/09/superpowers/> (referenced in README)
4. **Release Notes**: <https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md> (accessed 2026-01-31)
