# Plugin Lifecycle — Per-Phase Dispatch Details

For each phase, this file specifies the dispatch task(s) the orchestrator must execute: the skill or subagent to invoke, the context to include in the prompt, and the expected output artifact. Load this file when entering any phase below.

For the invocation syntax-only lookup table, see `./phase-skill-mapping.md`.
For Phase 2 researcher prompts (Researchers 0–4), see `./phase-2-researcher-prompts.md`.
For artifact templates referenced from these outputs, see `./artifact-templates.md`.

---

## Phase 0.6 — Mission Statement Draft

1. Activate `/plugin-creator:mission-statement` for mission statement drafting.
   - Context to include in the prompt: plugin concept from `<plugin_target/>`, path to `discuss-CONTEXT.md`
   - Output: `{plugin-path}/mission.json` with `status: "draft"` — a GitHub backlog interview task is created automatically by the skill

The mission statement is never a blocker. Research and all subsequent phases proceed without waiting for the interview. The `[draft]` status on `mission.json` signals this is a hypothesis, not a decision.

---

## Phase 1 — Assess (existing plugin only)

1. Activate `/plugin-creator:assessor` for plugin assessment.
   - Context to include in the prompt: plugin directory path from `<plugin_target/>`
   - Output: `.plugin-creator/plans/{plugin-name}/assessment-REPORT.md` — assessment report with design map and task file

---

## Phase 3 — Design

1. Activate `/dh:rt-ica` for the prerequisite check.
   - Context to include in the prompt: `research-FINDINGS.md`, plugin concept, user requirements from `discuss-CONTEXT.md`
   - Output: APPROVED or BLOCKED verdict — if BLOCKED, resolve blockers before proceeding

2. Dispatch the harness-native `general-purpose` agent for design plan creation.
   - Context to include in the prompt: `research-FINDINGS.md`, rt-ica output, `discuss-CONTEXT.md`
   - Output: `.plugin-creator/plans/{plugin-name}/design-PLAN.md` — design plan with XML task specs defining every skill, agent, and hook to create. Each task must have: single responsibility, testable `<verify>` command, clear `<done>` criteria.

3. Dispatch a separate harness-native `general-purpose` agent for plan verification.
   - Context to include in the prompt: `design-PLAN.md`, `discuss-CONTEXT.md`, `research-FINDINGS.md` key sections
   - Prompt: Verify this plan achieves the plugin goals. Check: (1) do tasks cover all required components? (2) are tasks truly atomic? (3) are `<verify>` commands testable? (4) are there gaps between tasks? (5) does sequence respect dependencies? Return PASS or FAIL with specific issues.
   - Output: PASS verdict (proceed) or FAIL with feedback (return to step 2)

The Design phase iteration limit is 3 plan-checker FAIL verdicts — track count in `STATE.md`. On the third FAIL, escalate to the user.

---

## Phase 4 — Create

For each component defined in `design-PLAN.md`, invoke the appropriate creator skill:

1. Activate `/plugin-creator:skill-creator` for skill creation.
   - Context to include in the prompt: `design-PLAN.md` task spec for this skill, plugin path
   - Output: `{plugin-path}/skills/{skill-name}/SKILL.md` and any bundled resources

2. Activate `/plugin-creator:agent-creator` for agent creation.
   - Context to include in the prompt: `design-PLAN.md` task spec for this agent, plugin path
   - Output: `{plugin-path}/agents/{agent-name}.md`

3. Activate `/plugin-creator:hook-creator` for hook creation.
   - Context to include in the prompt: `design-PLAN.md` task spec for this hook, plugin path
   - Output: hook scripts and `hooks.json` configuration

Repeat for each planned component. Keep a manifestless plugin when default component paths are
sufficient; create `plugin.json` only when stable metadata or custom component paths are required.

For agent-frontmatter decisions during agent creation, also load `/plugin-creator:claude-subagent-reference`.

---

## Phase 6 — Optimize

Semantic skill refinement is owned by Skill Lapidary, not Plugin Creator.

Before Phase 6 skill optimization, check for the `/skill-lapidary:skill-lapidary` skill. If unavailable and installation is permitted, install it for the current harness as Skill Lapidary's [packaging README](https://github.com/Jamie-BitFlight/skill-lapidary/blob/main/packaging/README.md) documents. If installation/loading is unavailable, mark semantic refinement BLOCKED; do not substitute Plugin Creator goal extraction or tightening heuristics.

Routing by concern:

1. **Skill semantic refinement** — activate `/skill-lapidary:skill-lapidary` for each skill requiring goal recovery, authority resolution, semantic conservation, tightening, or instruction optimization. Preserve its native result/evidence. If it blocks on consequential intent/authority, stop dependent optimization for that skill and present the blocker.
2. **Structural plugin improvement** — activate `plugin-creator:refactor-plugin` only after any required Lapidary refinement has completed or the structural work is demonstrably independent of the blocked semantic decision.
3. **Prose quality** — activate `plugin-creator:optimize-claude-md` only for surviving content. For SKILL.md targets, pass the applicable Lapidary result/contract identity when available; do not independently rediscover goals.
4. **Audit quality** — dispatch `plugin-creator:skill-auditor`.
5. **Sync upstream docs** — dispatch `plugin-creator:skill-content-updater`.
6. **Description-only rewrite** — activate `/plugin-creator:write-frontmatter-description`.
7. **Shared duplicated prose** — activate `plugin-creator:shared-content-references`.
8. **Agent prompt optimization** — activate `plugin-creator:subagent-refactoring-methodology`, then dispatch `plugin-creator:subagent-refactorer`.

After structural work creates, splits, merges, renames, or materially changes a skill, rerun Skill Lapidary on the affected skill before prose optimization. Do not carry a pre-refactor semantic result across a changed target without the owning Lapidary process accepting that revision.

---

## Phase 6.5 — Documentation

1. Dispatch `plugin-creator:plugin-assessor` for plugin documentation generation.
   - Context to include in the prompt: plugin path, all SKILL.md files, agent files, plugin.json, `assess-REPORT.md` or `design-PLAN.md` (whichever is available)
   - Prompt: Generate comprehensive documentation. Create: README.md with installation, usage, and examples; `docs/skills.md` if multiple skills exist; configuration guide if hooks or MCP servers are included. Ensure all features are documented, installation instructions are accurate, and examples are runnable.
   - Output: `{plugin-path}/README.md` and any additional documentation files

---

## Phase 7 — Verify

1. Activate `/plugin-creator:ensure-complete` for recursive validation.
   - Context to include in the prompt: plugin path, task file (if applicable)
   - Output: `.plugin-creator/plans/{plugin-name}/validation-REPORT.md`

2. Run all four validation layers — see the Phase 7 gate diagram in `./phase-gate-diagrams.md`:
   - Layer 1: `uvx skilllint@latest check <plugin-path>` (structural)
   - Layer 2: `claude plugin validate <plugin-path>` (runtime)
   - Layer 3: SK006/SK007 token complexity check from skilllint output
   - Layer 4: Cross-reference integrity (internal links, plugin.json skill paths, agent references)
