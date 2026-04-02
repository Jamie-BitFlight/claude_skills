# Feature Context: Plugin Lifecycle Orchestration Skill

## Document Metadata

- **Generated**: 2026-03-04
- **Input Type**: simple_description
- **Source**: GitHub Issue #427 — Create `/plugin-creator:plugin-lifecycle` skill for unified plugin development workflow
- **Status**: QUESTIONS_RESOLVED

---

## Original Request

The plugin-creator plugin lacks a unified workflow skill that guides users through the full plugin lifecycle in the correct sequence. Currently, individual skills and agents exist (assessor, skill-creator, agent-creator, refactor-plugin, etc.) but there is no single entry point that chains them together with the right handoffs, decision gates, and phase transitions.

**Goal**: Create a single `/plugin-creator:plugin-lifecycle` skill that defines ordered phases, names the correct skill/agent for each phase, specifies input/output artifacts per phase, includes decision gates, and handles the full lifecycle from blank canvas to marketplace-ready plugin.

**Seven Phases**: Assess, Research, Design, Create, Debug, Optimize, Verify

**Issue**: #427 | **Priority**: P1

---

## Problem Statement

Plugin developers (both the repo owner and orchestrator agents) must manually discover which skills and agents to invoke, in what order, and with what inputs when building a plugin from scratch or improving an existing one. The plugin-creator plugin has 32 skills and 8 agents, but no single entry point that sequences them correctly. This forces users to consult `CLAUDE.md`, trial-and-error different skill names, or read individual SKILL.md files to understand the workflow.

**Evidence**: The plugin-creator `CLAUDE.md` (`plugins/plugin-creator/CLAUDE.md`:22-40) contains a Mermaid flowchart for routing by intent, but it addresses only top-level dispatch (create/validate/refactor/fix) and does not chain phases together end-to-end. The `/plugin-creator:plugin-creator` skill (`plugins/plugin-creator/skills/plugin-creator/SKILL.md`) covers creation from blank canvas but lacks phases for assessment of existing plugins, debugging, or optimization of already-created content. The `/plugin-creator:refactor-plugin` skill handles refactoring of existing plugins but starts from assessment, not from blank canvas.

**Frequency**: Every plugin creation or major improvement session requires the user to manually sequence 3-7 skill invocations.

**Impact**: Without a unified workflow, users skip phases (e.g., skipping assessment before creation leads to rework), invoke wrong skills for the phase they are in, or abandon the workflow midway because they cannot determine the next step.

---

## Core Intent Analysis

### WHO (Target Users)

1. **Orchestrator agents** (primary) -- The main Claude Code session orchestrating plugin development by delegating to specialized sub-agents. This is the most common consumer: an orchestrator that needs to know which skill/agent to invoke next and what artifacts to pass.
2. **Human developers** (secondary) -- Users who invoke `/plugin-creator:plugin-lifecycle` directly to get guided through plugin development. They want a single command that tells them the current phase, what to do, and what the next step is.

### WHAT (Desired Outcome)

A single skill (`/plugin-creator:plugin-lifecycle`) that:

- Defines ordered phases covering the full plugin lifecycle from blank canvas to marketplace-ready
- Names the exact skill or agent to invoke for each phase
- Specifies required input artifacts and expected output artifacts per phase
- Includes decision gates with observable conditions (not subjective judgments) between phases
- Can be followed end-to-end by an orchestrator without consulting other plugin-creator documentation

Success looks like: an orchestrator reads this one skill and can drive a complete plugin creation or improvement workflow without needing to discover skills/agents independently.

### WHEN (Trigger Conditions)

- User says "create a new plugin" or "build a plugin for X"
- User says "improve plugin X" or "make plugin X marketplace-ready"
- User wants to take a rough plugin from initial state to production quality
- Orchestrator needs to plan a multi-phase plugin development session
- User is unsure which plugin-creator skill to use for their current situation

### WHY (Problem Being Solved)

The plugin-creator ecosystem has grown organically to 32 skills and 8 agents. The individual components are high quality, but the connections between them are implicit. Users must either:

1. Read `CLAUDE.md` to understand routing (covers intent dispatch but not phase sequencing)
2. Read individual SKILL.md files to understand input/output contracts
3. Know from experience which skills compose into a workflow

This creates a high barrier to entry for new users and causes orchestrator agents to make incorrect sequencing decisions (e.g., trying to optimize before creating, or creating without assessing first).

---

## Non-Goals (Explicit Exclusions)

| Non-Goal | Rationale |
|----------|-----------|
| Replacing existing skills/agents | The lifecycle skill composes existing components; it does not reimplement their logic |
| Automating phase transitions without user confirmation | Decision gates require observable conditions; the orchestrator or user decides to proceed |
| Adding new plugin capabilities | No new creation, validation, or refactoring logic; only orchestration of what exists |
| Handling non-plugin-creator workflows | SAM feature workflow (`/add-new-feature`) is a separate orchestration; this skill is scoped to plugin-creator's own components |

---

## Codebase Research

### Similar Patterns Found

#### Pattern 1: SAM Feature Workflow (`/add-new-feature`)

- **Location**: `.claude/skills/add-new-feature/SKILL.md:1-80`
- **Relevance**: This is the closest existing pattern -- a single skill that orchestrates multiple phases (discovery, codebase analysis, architecture spec, task decomposition, validation, context manifest) with explicit agent delegation per phase, input/output artifact specifications, and sequential phase dependencies. It covers a different domain (feature implementation) but uses the exact orchestration model the plugin-lifecycle skill needs.
- **Reusable**: The phase structure, artifact naming conventions (`plan/feature-context-{slug}.md`, `plan/architect-{slug}.md`), and the pattern of naming the agent/skill per phase with input/output are directly applicable. The decision gate pattern (Phase 5: plan-validator returning PASS/BLOCKED) is the same gate pattern needed for plugin-lifecycle.

#### Pattern 2: Refactor Plugin Workflow (`/plugin-creator:refactor-plugin`)

- **Location**: `plugins/plugin-creator/skills/refactor-plugin/SKILL.md:1-110`
- **Relevance**: This is the existing multi-phase plugin workflow that covers assessment, design, planning, execution, and validation -- 5 of the 7 proposed lifecycle phases (roughly: Assess, Design, Create, Optimize, Verify). It chains `/plugin-creator:assessor` into `/plugin-creator:implement-refactor` into `/plugin-creator:ensure-complete`.
- **Reusable**: The step structure (validate input, verify plugin exists, run assessment, review plan, await user decision) and the decision gate between assessment and implementation are directly reusable. The recursive follow-up loop in `/plugin-creator:ensure-complete` is a verified pattern for the Verify phase.

#### Pattern 3: Plugin Creator Orchestration (`/plugin-creator:plugin-creator`)

- **Location**: `plugins/plugin-creator/skills/plugin-creator/SKILL.md:1-827`
- **Relevance**: This skill already orchestrates plugin creation through 7 phases (RT-ICA, Discussion, Research, Design, Implementation, Validation, Documentation + Final Verification). It names specific agents per phase, specifies artifact paths, and includes decision gates (RT-ICA APPROVED/BLOCKED, Plan Checker PASS/FAIL). However, it covers only creation from blank canvas -- not assessment of existing plugins, debugging, or optimization.
- **Reusable**: The Phase 0 RT-ICA prerequisite check, the 4-way parallel research pattern, the Plan Checker verification loop, and the multi-layer validation (4 layers) are proven patterns that could be incorporated into the lifecycle skill.

#### Pattern 4: Assessor Multi-Tier Pipeline (`/plugin-creator:assessor`)

- **Location**: `plugins/plugin-creator/skills/assessor/SKILL.md:1-835`
- **Relevance**: Demonstrates a 4-tier assessment pipeline (Structural Analysis, Skill Lifecycle Audit, Agent Lifecycle Audit, Skill Completeness Audit) with progressive depth. This is the Assess phase's implementation. It chains into Phase 2 (design map), Phase 3 (task planning), and Phase 4 (context gathering) with explicit completion requirements and structured summaries between phases.
- **Reusable**: The tiered assessment approach (Tier 4 is optional based on conditions) and the structured phase completion display format are patterns the lifecycle skill should reference.

### Existing Infrastructure

The plugin-creator plugin already has all the components needed for each proposed lifecycle phase. What is missing is the orchestration layer that sequences them.

**Skills available for composition** (verified present at stated paths):

| Phase (Proposed) | Existing Skill/Agent | Path | Input | Output |
|---|---|---|---|---|
| Assess | `/plugin-creator:assessor` | `plugins/plugin-creator/skills/assessor/SKILL.md` | Plugin path | Assessment report, design map, task file |
| Assess | `@plugin-assessor` agent | `plugins/plugin-creator/agents/plugin-assessor.md` | Plugin path | Assessment report |
| Assess | `/plugin-creator:audit-skill-lifecycle` | `plugins/plugin-creator/skills/audit-skill-lifecycle/SKILL.md` | Plugin path | Audit report in `.claude/audits/` |
| Assess | `/plugin-creator:audit-agent-lifecycle` | `plugins/plugin-creator/skills/audit-agent-lifecycle/SKILL.md` | Plugin path | Audit report in `.claude/audits/` |
| Assess | `/plugin-creator:audit-skill-completeness` | `plugins/plugin-creator/skills/audit-skill-completeness/SKILL.md` | Skill path | Scored completeness report |
| Research | `/plugin-creator:plugin-creator` (Phase 1) | `plugins/plugin-creator/skills/plugin-creator/SKILL.md:261-336` | Plugin concept | `research-FINDINGS.md` |
| Research | `/plugin-creator:feature-discovery` | `plugins/plugin-creator/skills/feature-discovery/SKILL.md` | Feature description | `feature-context-{slug}.md` |
| Design | `/plugin-creator:plugin-creator` (Phase 2) | `plugins/plugin-creator/skills/plugin-creator/SKILL.md:340-433` | Research findings | `design-PLAN.md` |
| Design | `/plugin-creator:rt-ica` | `plugins/plugin-creator/skills/rt-ica/SKILL.md` | Goals | APPROVED/BLOCKED |
| Create | `/plugin-creator:skill-creator` | `plugins/plugin-creator/skills/skill-creator/SKILL.md` | Skill requirements | SKILL.md + resources |
| Create | `/plugin-creator:agent-creator` | `plugins/plugin-creator/skills/agent-creator/SKILL.md` | Agent requirements | Agent `.md` file |
| Create | `/plugin-creator:hook-creator` | `plugins/plugin-creator/skills/hook-creator/SKILL.md` | Hook requirements | hooks.json + scripts |
| Optimize | `/plugin-creator:refactor-plugin` | `plugins/plugin-creator/skills/refactor-plugin/SKILL.md` | Plugin path | Refactored plugin |
| Optimize | `/plugin-creator:implement-refactor` | `plugins/plugin-creator/skills/implement-refactor/SKILL.md` | Task file path | Completed tasks |
| Optimize | `@subagent-refactorer` agent | `plugins/plugin-creator/agents/subagent-refactorer.md` | Agent file | Optimized agent |
| Optimize | `@contextual-ai-documentation-optimizer` agent | `plugins/plugin-creator/agents/contextual-ai-documentation-optimizer.md` | Doc file | Optimized doc |
| Verify | `/plugin-creator:lint` | `plugins/plugin-creator/skills/lint/SKILL.md` | Path | Validation output |
| Verify | `/plugin-creator:ensure-complete` | `plugins/plugin-creator/skills/ensure-complete/SKILL.md` | Task file | Validation report |

**Scripts available**:

| Script | Path | Purpose |
|---|---|---|
| `plugin_validator.py` | `plugins/plugin-creator/scripts/plugin_validator.py` | Frontmatter, structure, token complexity validation |
| `create_plugin.py` | `plugins/plugin-creator/scripts/create_plugin.py` | Plugin scaffolding |
| `auto_sync_manifests.py` | `plugins/plugin-creator/scripts/auto_sync_manifests.py` | Pre-commit manifest sync |
| `fix_tool_formats.py` | `plugins/plugin-creator/scripts/fix_tool_formats.py` | Tool format fixing |

**Reference skills** (loaded by agents, not directly invoked in lifecycle):

- `/plugin-creator:claude-skills-overview-2026` -- Skill system reference
- `/plugin-creator:claude-plugins-reference-2026` -- Plugin system reference
- `/plugin-creator:hooks-guide` -- Hooks reference

### Code References

- `plugins/plugin-creator/CLAUDE.md:22-40` -- Usage Patterns flowchart (top-level routing by intent)
- `plugins/plugin-creator/CLAUDE.md:59-78` -- Component Inventory (13 skills, 6 agents listed in CLAUDE.md; actual count is 32 skills per Glob)
- `plugins/plugin-creator/.claude-plugin/plugin.json:1-30` -- Plugin manifest (version 6.0.6, 8 agents registered)
- `plugins/plugin-creator/skills/plugin-creator/SKILL.md:170-207` -- Phase 0 RT-ICA prerequisite check pattern
- `plugins/plugin-creator/skills/plugin-creator/SKILL.md:261-336` -- 4-way parallel research pattern
- `plugins/plugin-creator/skills/plugin-creator/SKILL.md:622-729` -- Multi-layer validation pattern (4 layers)
- `plugins/plugin-creator/skills/assessor/SKILL.md:49-224` -- 4-tier assessment pipeline
- `plugins/plugin-creator/skills/refactor-plugin/SKILL.md:19-26` -- 5-step refactoring workflow overview
- `plugins/plugin-creator/skills/ensure-complete/SKILL.md:516-525` -- Recursive validation loop
- `.claude/skills/add-new-feature/SKILL.md:11-80` -- SAM workflow phase structure (comparable orchestration pattern)
- `.claude/rules/local-workflow.md:1-50` -- SAM workflow overview documentation

---

## Use Scenarios

### Scenario 1: New Plugin from Blank Canvas

**Actor**: Human developer using Claude Code
**Trigger**: User says "I want to create a plugin for managing Terraform deployments"
**Goal**: Go from idea to a marketplace-ready plugin with validated skills, agents, and hooks
**Expected Outcome**: The lifecycle skill guides them through: (1) Research what exists, (2) Design the plugin structure, (3) Create skills/agents/hooks, (4) Validate everything passes `plugin_validator.py` and `claude plugin validate`, (5) Plugin is ready for marketplace submission. At each transition, a decision gate confirms readiness before proceeding.

### Scenario 2: Improving an Existing Plugin

**Actor**: Orchestrator agent executing a refactoring workflow
**Trigger**: User says "improve the python3-development plugin to marketplace quality"
**Goal**: Take an existing but rough plugin through assessment, identify issues, fix them, and verify improvements
**Expected Outcome**: The lifecycle skill routes to: (1) Assess the current state (assessor + audit skills), (2) Based on assessment score, decide whether to refactor or just optimize, (3) Execute improvements, (4) Verify score improved and no regressions. The orchestrator follows the skill's phase instructions without needing to know which sub-skills exist.

### Scenario 3: Resuming After Interruption

**Actor**: Human developer returning to a partially-completed plugin
**Trigger**: User says "I was building a plugin for X, what should I do next?"
**Goal**: Determine which lifecycle phase the plugin is currently in and what the next step is
**Expected Outcome**: The lifecycle skill provides observable conditions for each phase completion, so the user (or orchestrator) can evaluate which gate conditions are already met and resume from the correct phase. For example: "plugin.json exists and passes validation" -> Phase 1 (Assess) is met; "all SKILL.md files pass lint" -> Create phase is met; "assessment score > 80" -> approaching Verify phase.

### Scenario 4: Debugging a Plugin That Fails Validation

**Actor**: Human developer whose plugin has validator errors
**Trigger**: User runs `/plugin-creator:lint` and gets SK006/SK007 warnings or structural errors
**Goal**: Fix the validation errors using the correct skill for each error type
**Expected Outcome**: The lifecycle skill's Debug phase routes to the appropriate fix: SK006/SK007 -> `/plugin-creator:refactor-skill`, broken links -> direct fix, frontmatter issues -> `/plugin-creator:lint --fix`, agent description quality -> `@subagent-refactorer`. The user does not need to know the mapping; the lifecycle skill provides it.

---

## Gap Analysis

### Identified Gaps

| # | Category | Gap Description | Impact |
|---|----------|-----------------|--------|
| 1 | Scope | The proposed seven phases (Assess, Research, Design, Debug, Create, Optimize, Verify) do not clearly distinguish "new plugin" vs "existing plugin" entry points. Assessment of a non-existent plugin is meaningless. | Orchestrator may attempt to assess a plugin that does not yet exist, causing errors or wasted work |
| 2 | Scope | The "Debug" phase is not clearly defined by existing skills. No current skill is named "debug" -- the closest are `/plugin-creator:lint` (validation) and individual fix patterns in CLAUDE.md. The phase needs clearer definition. | Without a concrete skill/agent mapping, the Debug phase becomes a vague catch-all |
| 3 | Behavior | Decision gate conditions between phases are not specified in the request. The request says "decision gates with observable conditions" but does not define what those conditions are. | Cannot build the Mermaid flowchart or gate logic without knowing what observable conditions to check |
| 4 | Behavior | Phase ordering for existing plugins differs from new plugins. For a new plugin, Research precedes Create. For an existing plugin, Assess precedes Optimize. The lifecycle skill must handle both paths. | A single linear sequence will not work for both entry points |
| 5 | Integration | Multiple existing skills overlap in scope. `/plugin-creator:plugin-creator` already covers Research+Design+Create+Validate. `/plugin-creator:refactor-plugin` covers Assess+Design+Execute+Validate. The lifecycle skill must compose these without creating redundant workflow paths. | Risk of two competing orchestration layers if the lifecycle skill duplicates existing skill logic instead of delegating to them |
| 6 | Integration | The CLAUDE.md component inventory (`plugins/plugin-creator/CLAUDE.md:59-78`) lists 13 skills but actual Glob reveals 32 skills. The lifecycle skill needs an accurate component map. | If the skill references skills that are not listed in CLAUDE.md, the reference may be inconsistent with documentation |
| 7 | User | It is unclear whether the lifecycle skill should be `user-invocable: true` (human invokes `/plugin-lifecycle`) or `user-invocable: false` (only orchestrators use it). The request says "single entry point" which implies user-invocable. | Affects frontmatter configuration, description wording, and whether it appears in the `/` menu |
| 8 | Scope | The relationship between this lifecycle skill and `/plugin-creator:plugin-creator` is ambiguous. Does the lifecycle skill replace plugin-creator, wrap it, or sit alongside it? | If both exist as user-invocable skills, users will be confused about which to use |

---

## Questions Requiring Resolution

### Q1: Dual entry point or single linear sequence?

- **Category**: Behavior
- **Owner**: User/Stakeholder
- **Blocking**: Yes
- **Gap**: The lifecycle for a new plugin (Research -> Design -> Create -> Verify) differs from an existing plugin (Assess -> Debug/Optimize -> Verify). A single linear 7-phase sequence cannot serve both.
- **Question**: Should the lifecycle skill support two entry points (new plugin vs existing plugin) with different phase orderings, or should it enforce a single sequence where some phases are skipped based on conditions?
- **Options**:
  - A) Two entry points: "new" path skips Assess and enters at Research; "existing" path skips Research/Create and enters at Assess
  - B) Single sequence with conditional skip gates: all 7 phases present, but decision gates allow skipping (e.g., "Does plugin.json exist? If no, skip Assess and go to Research")
  - C) Always run all 7 phases in order, even for new plugins (Assess would detect "nothing exists" and pass through)
- **Why It Matters**: Determines the Mermaid flowchart structure and whether the skill has one or two primary code paths
- **Resolution**: **Option A — Two explicit entry points.** "New" path skips Assess, enters at Research. "Existing" path skips Research/Create, enters at Assess. Two code paths in the Mermaid flowchart.

### Q2: Relationship to existing `/plugin-creator:plugin-creator` skill

- **Category**: Integration
- **Owner**: User/Stakeholder
- **Blocking**: Yes
- **Gap**: The existing `/plugin-creator:plugin-creator` skill already orchestrates plugin creation through 7 phases (RT-ICA, Discussion, Research, Design, Implementation, Validation, Documentation). The new lifecycle skill covers overlapping territory.
- **Question**: Should the lifecycle skill replace `/plugin-creator:plugin-creator`, wrap it (delegate to it for the creation phases), or coexist alongside it with different scope?
- **Options**:
  - A) Replace: The lifecycle skill subsumes plugin-creator and becomes the single orchestration entry point. Plugin-creator is deprecated or becomes a reference.
  - B) Wrap: The lifecycle skill delegates to `/plugin-creator:plugin-creator` for the Create phase, and to `/plugin-creator:refactor-plugin` for the Optimize phase.
  - C) Coexist: Plugin-creator handles creation-only; lifecycle handles the full lifecycle including assessment, debugging, and optimization. Users choose based on whether they need just creation or the full lifecycle.
- **Why It Matters**: Determines scope of the new skill, whether existing skills are modified, and how to avoid user confusion from competing orchestration layers
- **Resolution**: **Option A — Replace.** The lifecycle skill subsumes `/plugin-creator:plugin-creator` and becomes the single orchestration entry point. Plugin-creator is deprecated or becomes a reference.

### Q3: What constitutes the "Debug" phase?

- **Category**: Scope
- **Owner**: User/Stakeholder
- **Blocking**: Yes
- **Gap**: No existing skill in plugin-creator is explicitly named "debug." The closest is `/plugin-creator:lint` (runs `plugin_validator.py`), but debugging could also include fixing frontmatter issues, resolving broken links, fixing tool format patterns, or splitting oversized skills.
- **Question**: What specific activities belong in the Debug phase, and how does it differ from the Optimize phase?
- **Options**:
  - A) Debug = fix validation errors (lint failures, schema violations, broken links). Optimize = improve quality (better descriptions, progressive disclosure, agent prompt improvements).
  - B) Debug = any fix triggered by a specific error. Optimize = proactive improvement without a triggering error.
  - C) Merge Debug and Optimize into a single "Improve" phase that handles both error fixing and quality improvements.
- **Why It Matters**: Determines which skills/agents map to the Debug phase and whether it is distinct enough from Optimize to warrant a separate phase
- **Resolution**: **Option A — Debug = fix validation errors (lint failures, schema violations, broken links). Optimize = improve quality (descriptions, progressive disclosure, agent prompt improvements).**

### Q4: Decision gate observable conditions

- **Category**: Behavior
- **Owner**: Engineering
- **Blocking**: No (can proceed with assumptions, refine later)
- **Gap**: The request requires "decision gates with observable conditions" but does not specify what those conditions are. Observable conditions must be evaluable by a command or file check, not by subjective judgment.
- **Question**: What observable conditions should gate each phase transition? Here are proposed defaults -- are these acceptable?
- **Options**:
  - Assess -> Research: `plugin_validator.py` ran without SK007 errors (or plugin does not exist yet)
  - Research -> Design: `research-FINDINGS.md` or equivalent artifact exists
  - Design -> Create: `design-PLAN.md` exists and plan-checker returned PASS
  - Create -> Debug: All planned SKILL.md/agent files exist
  - Debug -> Optimize: `plugin_validator.py` reports 0 errors (warnings acceptable)
  - Optimize -> Verify: Assessment score >= target threshold
  - Verify -> Done: All validation layers pass
- **Why It Matters**: These conditions become the diamond nodes in the Mermaid flowchart and determine whether an orchestrator can automatically advance through phases
- **Resolution**: **Proposed defaults accepted.** Decision gates use observable conditions (command exits, file existence, score thresholds). Will be refined during architecture.

### Q5: Should the skill be user-invocable or orchestrator-only?

- **Category**: User
- **Owner**: User/Stakeholder
- **Blocking**: No
- **Gap**: The request implies user-invocable ("single entry point") but the acceptance criteria mention "an orchestrator can follow the skill end-to-end."
- **Question**: Should `/plugin-creator:plugin-lifecycle` appear in the `/` autocomplete menu for direct user invocation, or should it be orchestrator-only (user-invocable: false)?
- **Options**:
  - A) User-invocable (default). Users and orchestrators both invoke it.
  - B) Orchestrator-only (`user-invocable: false`). Only loaded programmatically.
- **Why It Matters**: Affects the description wording (must include trigger keywords if user-invocable), frontmatter flags, and whether it competes with existing user-facing skills in the `/` menu
- **Resolution**: **Option A — User-invocable.** The skill should appear in the `/` autocomplete menu. Both users and orchestrators invoke it.

---

## Goals (Finalized)

1. **Single orchestration skill exists** at `plugins/plugin-creator/skills/plugin-lifecycle/SKILL.md` with valid frontmatter that passes `plugin_validator.py` with no SK006/SK007 warnings. User-invocable.
2. **All seven phases documented** with: the correct skill/agent to invoke, required input artifacts, expected output artifacts, and a completion condition for each
3. **Mermaid flowchart** with two explicit entry points (new plugin vs existing plugin) showing phase transitions and decision gates with observable conditions (command exits, file existence checks, score thresholds)
4. **Two entry points**: "New" path starts at Research (skips Assess). "Existing" path starts at Assess (skips Research/Create).
5. **Replaces `/plugin-creator:plugin-creator`** — the lifecycle skill subsumes plugin-creator as the single orchestration entry point. Plugin-creator is deprecated.
6. **Debug phase** handles validation error fixing (lint failures, schema violations, broken links). **Optimize phase** handles quality improvements (descriptions, progressive disclosure, agent prompts).
7. **No duplication of existing skill logic** — the lifecycle skill delegates to existing skills/agents for execution
8. **References section** documents which existing skills are composed (maps phase -> skill/agent)
9. **Orchestrator self-sufficiency** — an agent reading only the lifecycle skill can execute the full workflow without consulting CLAUDE.md or individual SKILL.md files

---

## Next Steps

After questions are resolved:

1. Update "Resolution" fields in Questions section
2. Finalize Goals section
3. Proceed to RT-ICA assessment
4. Then proceed to architecture design
