# Plugin Lifecycle — Example Sessions

Consult these walkthroughs to understand expected phase output and decision flow for each lifecycle path.

## New Plugin (Full Lifecycle)

```text
> /plugin-lifecycle new git-workflow-helper

Loading domain knowledge skills...
  ✓ claude-plugins-reference-2026 loaded
  ✓ claude-skills-overview-2026 loaded

Phase 0: RT-ICA Prerequisite Check
  Purpose clarity:     AVAILABLE — "git workflow helper" defined
  Target users:        DERIVABLE — developers using Claude Code
  Component selection: DERIVABLE — likely skills + hooks
  Existing solutions:  MISSING — need to check plugins/
  Source material:     AVAILABLE — git documentation exists
  Verification method: DERIVABLE — validator scripts available

  RT-ICA: BLOCKED
  Missing: Existing solutions check (must search before designing to avoid duplication)

Searching plugins/ and ~/.claude/skills/ for git workflow functionality...
  Found: no similar plugin exists
  RT-ICA: APPROVED

Phase 0.5: Discussion
  Activation triggers: Auto-load on git operations? [yes/no]
  > yes — hook on PreToolUse:Bash for git commands
  Tool restrictions: Read-only or full access?
  > full access needed (creates commits)
  Verbosity: terse or explanatory?
  > terse — just the commands

  Preferences saved to .plugin-creator/plans/git-workflow-helper/discuss-CONTEXT.md

Phase 2: Research
  Spawning 4 parallel researchers...
    Researcher 1 (existing solutions) → research-1-existing.md ✓
    Researcher 2 (Claude Code features) → research-2-features.md ✓
    Researcher 3 (architecture patterns) → research-3-architecture.md ✓
    Researcher 4 (pitfalls/official docs) → research-4-pitfalls.md ✓
  Merging findings → research-FINDINGS.md ✓

Phase 3: Design
  RT-ICA on design inputs: APPROVED
  Generating design plan...
  Plan checker: PASS (3 tasks, all atomic, all verifiable)
  Saved: .plugin-creator/plans/git-workflow-helper/design-PLAN.md

Phase 4: Create
  Creating skill: git-commit-helper/SKILL.md ✓
  Creating hook: PreToolUse:Bash configuration ✓
  Creating plugin.json ✓
  All 3 planned files exist ✓

Phase 5: Debug
  Running validator...
  Exit code: 0 — 0 errors, 1 warning (SK006 — skill approaching limit)
  Warning noted in STATE.md for Phase 6 attention

Phase 6: Optimize
  Refactor-plugin: extracted 2 sections to references/ — SK006 resolved ✓
  Documentation optimizer: improved 3 descriptions ✓
  Agent prompt check: no agents in this plugin

Phase 6.5: Documentation
  Generating README.md...
  README.md created with installation, usage, and 3 examples ✓

Phase 7: Verify
  Layer 1 (validator): 0 errors ✓
  Layer 2 (claude plugin validate): PASS ✓
  Layer 3 (token complexity): all skills within limits ✓
  Layer 4 (cross-references): all links resolve ✓

  Wrote .plugin-creator/plans/git-workflow-helper/SUMMARY.md
  Plugin is marketplace-ready.
```

## Existing Plugin With Validation Errors

```text
> /plugin-lifecycle existing plugins/my-data-tool

Loading domain knowledge skills...
  ✓ claude-plugins-reference-2026 loaded
  ✓ claude-skills-overview-2026 loaded

Phase 1: Assess
  Running assessor...
  Assessment saved: .plugin-creator/plans/my-data-tool/assessment-REPORT.md

  Running validator: uvx skilllint@latest check plugins/my-data-tool
  Exit code: 1

  Errors found:
    SK007: skills/main-skill/SKILL.md exceeds token limit (8,200 tokens)
    LINK01: skills/main-skill/SKILL.md:45 → references/missing-file.md (file not found)
    FM003: skills/helper-skill/SKILL.md — validate allowed-tools against its destination schema

  → Proceeding to Phase 5: Debug

Phase 5: Debug — Iteration 1
  SK007 (skill too large):
    Invoking refactor-skill for skills/main-skill/SKILL.md...
    Split into main-skill/ (3,200 tokens) + references/advanced-usage.md ✓

  LINK01 (broken link):
    skills/main-skill/SKILL.md:45 references ./references/missing-file.md
    File does not exist — removing stale link ✓

  FM003 (destination schema):
    Running skilllint on skills/helper-skill/SKILL.md...
    Validated the tool field against its destination schema ✓

  Re-validating...
  Exit code: 0 — 0 errors ✓

Phase 6: Optimize
  Refactor-plugin: structure looks good — 2 minor description improvements ✓
  Documentation optimizer: optimized main-skill description trigger keywords ✓
  Agent optimizer: 1 agent prompt improved ✓

Phase 6.5: Documentation
  README.md exists — updating for new skill structure ✓

Phase 7: Verify
  Layer 1 (validator): 0 errors ✓
  Layer 2 (claude plugin validate): PASS ✓
  Layer 3 (token complexity): all within limits ✓
  Layer 4 (cross-references): all links resolve ✓

  Plugin is marketplace-ready.
```
