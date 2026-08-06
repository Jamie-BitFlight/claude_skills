# Plugin Lifecycle — Per-Phase Dispatch Details

For each phase, this file specifies the dispatch task(s) the orchestrator must execute: the skill or subagent to invoke, the context to include in the prompt, and the expected output artifact. Load this file when entering any phase below.

For the invocation syntax-only lookup table, see `./phase-skill-mapping.md`.
For Phase 2 researcher prompts (Researchers 0–4), see `./phase-2-researcher-prompts.md`.
For artifact templates referenced from these outputs, see `./artifact-templates.md`.

---

## Phase 0.6 — Mission Statement Draft

1. Task is mission statement drafting with `Skill(skill="plugin-creator:mission-statement")`
   - Context to include in the prompt: plugin concept from `<plugin_target/>`, path to `discuss-CONTEXT.md`
   - Output: `{plugin-path}/mission.json` with `status: "draft"` — a GitHub backlog interview task is created automatically by the skill

The mission statement is never a blocker. Research and all subsequent phases proceed without waiting for the interview. The `[draft]` status on `mission.json` signals this is a hypothesis, not a decision.

---

## Phase 1 — Assess (existing plugin only)

1. Task is plugin assessment with `Skill(skill="plugin-creator:assessor")`
   - Context to include in the prompt: plugin directory path from `<plugin_target/>`
   - Output: `.plugin-creator/plans/{plugin-name}/assessment-REPORT.md` — assessment report with design map and task file

---

## Phase 3 — Design

1. Task is prerequisite check with `Skill(skill="dh:rt-ica")`
   - Context to include in the prompt: `research-FINDINGS.md`, plugin concept, user requirements from `discuss-CONTEXT.md`
   - Output: APPROVED or BLOCKED verdict — if BLOCKED, resolve blockers before proceeding

2. Task is design plan creation with `subagent_type="general-purpose"`
   - Context to include in the prompt: `research-FINDINGS.md`, rt-ica output, `discuss-CONTEXT.md`
   - Output: `.plugin-creator/plans/{plugin-name}/design-PLAN.md` — design plan with XML task specs defining every skill, agent, and hook to create. Each task must have: single responsibility, testable `<verify>` command, clear `<done>` criteria.

3. Task is plan verification with `subagent_type="general-purpose"`
   - Context to include in the prompt: `design-PLAN.md`, `discuss-CONTEXT.md`, `research-FINDINGS.md` key sections
   - Prompt: Verify this plan achieves the plugin goals. Check: (1) do tasks cover all required components? (2) are tasks truly atomic? (3) are `<verify>` commands testable? (4) are there gaps between tasks? (5) does sequence respect dependencies? Return PASS or FAIL with specific issues.
   - Output: PASS verdict (proceed) or FAIL with feedback (return to step 2)

The Design phase iteration limit is 3 plan-checker FAIL verdicts — track count in `STATE.md`. On the third FAIL, escalate to the user.

---

## Phase 4 — Create

For each component defined in `design-PLAN.md`, invoke the appropriate creator skill:

1. Task is skill creation with `Skill(skill="plugin-creator:skill-creator")`
   - Context to include in the prompt: `design-PLAN.md` task spec for this skill, plugin path
   - Output: `{plugin-path}/skills/{skill-name}/SKILL.md` and any bundled resources

2. Task is agent creation with `Skill(skill="plugin-creator:agent-creator")`
   - Context to include in the prompt: `design-PLAN.md` task spec for this agent, plugin path
   - Output: `{plugin-path}/agents/{agent-name}.md`

3. Task is hook creation with `Skill(skill="plugin-creator:hook-creator")`
   - Context to include in the prompt: `design-PLAN.md` task spec for this hook, plugin path
   - Output: hook scripts and `hooks.json` configuration

Repeat for each planned component. Create `plugin.json` via `uv run plugins/plugin-creator/scripts/create_plugin.py` if it does not exist.

For agent-frontmatter decisions during agent creation, also load `/plugin-creator:claude-subagent-reference`.

---

## Phase 6 — Optimize

Routing by concern (use when editing files in `plugins/`, `.claude/`, `AGENTS.md`, or `CLAUDE.md`):

- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `subagent_type="plugin-creator:ai-doc-optimizer"`
- Audit quality (read-only, no writes, score against completeness categories) → `subagent_type="plugin-creator:skill-auditor"`
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `subagent_type="plugin-creator:skill-content-updater"`
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly
- Resolve prose duplicated across 2+ skills or agent files (shared reference material, not one skill's own bloat) → `Skill(skill="plugin-creator:shared-content-references")`

Dispatches:

1. Task is structural plugin improvement with `Skill(skill="plugin-creator:refactor-plugin")`
   - Context to include in the prompt: plugin path, `assessment-REPORT.md` (if available from Phase 1)
   - Output: improved plugin structure, updated SKILL.md files, better progressive disclosure

2. Task is content quality optimization with `subagent_type="plugin-creator:ai-doc-optimizer"`
   - Context to include in the prompt: SKILL.md or CLAUDE.md files needing improvement, assessment findings
   - Output: optimized documentation with better Claude comprehension

3. Task is agent prompt optimization with `subagent_type="plugin-creator:subagent-refactorer"`
   - Context to include in the prompt: agent .md files needing improvement
   - Output: optimized agent prompts using Anthropic best practices

---

## Phase 6.5 — Documentation

1. Task is plugin documentation generation with `subagent_type="plugin-creator:plugin-assessor"`
   - Context to include in the prompt: plugin path, all SKILL.md files, agent files, plugin.json, `assess-REPORT.md` or `design-PLAN.md` (whichever is available)
   - Prompt: Generate comprehensive documentation. Create: README.md with installation, usage, and examples; `docs/skills.md` if multiple skills exist; configuration guide if hooks or MCP servers are included. Ensure all features are documented, installation instructions are accurate, and examples are runnable.
   - Output: `{plugin-path}/README.md` and any additional documentation files

---

## Phase 7 — Verify

1. Task is recursive validation with `Skill(skill="plugin-creator:ensure-complete")`
   - Context to include in the prompt: plugin path, task file (if applicable)
   - Output: `.plugin-creator/plans/{plugin-name}/validation-REPORT.md`

2. Run all four validation layers — see the Phase 7 gate diagram in `./phase-gate-diagrams.md`:
   - Layer 1: `uvx skilllint@latest check <plugin-path>` (structural)
   - Layer 2: `claude plugin validate <plugin-path>` (runtime)
   - Layer 3: SK006/SK007 token complexity check from skilllint output
   - Layer 4: Cross-reference integrity (internal links, plugin.json skill paths, agent references)
