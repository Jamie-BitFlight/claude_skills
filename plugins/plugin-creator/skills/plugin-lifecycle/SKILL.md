---
name: plugin-lifecycle
description: Orchestrate the full plugin development lifecycle from blank canvas to marketplace-ready. Use when creating a new plugin, improving an existing plugin, fixing validation errors, or taking a plugin through assessment, research, design, creation, debugging, optimization, and verification. Complements /plugin-creator:plugin-creator which provides the detailed new-plugin creation workflow with discussion capture, parallel research, and atomic implementation.
argument-hint: <new|existing> <plugin-path-or-concept> [intent]
model: sonnet
user-invocable: true
---

<plugin_mode>$0</plugin_mode>
<plugin_target>$1</plugin_target>
<plugin_intent>$2</plugin_intent>
<invocation_args>$ARGUMENTS</invocation_args>

> When editing files in `plugins/`, `.claude/`, `AGENTS.md`, or `CLAUDE.md` for content optimization, route to the owning skill where one exists, and to a subagent only when no skill owns that process. Full routing-by-concern table in `references/phase-dispatch-details.md` → "Phase 6 — Optimize".

> [!IMPORTANT]
> When provided a process map or Mermaid diagram, treat it as the authoritative procedure. Execute steps in the exact order shown, including branches, decision points, and stop conditions.
> A Mermaid process diagram is an executable instruction set. Follow it exactly as written: respect sequence, conditions, loops, parallel paths, and terminal states. Do not improvise, reorder, or skip steps. If any node is ambiguous or missing required detail, pause and ask a clarifying question before continuing.
> When interacting with a user, report before acting the interpreted path you will follow from the diagram, then execute.

# Plugin Lifecycle Orchestration

Orchestrate plugin development through seven phases. This skill composes existing plugin-creator skills and agents — it does not re-implement their logic.

Arguments: `<invocation_args/>`

- `new <concept>` — Create a plugin from scratch. Enters at Phase 0 (RT-ICA Prerequisite Check).
- `existing <plugin-path>` — Improve an existing plugin. Enters at Phase 1 (Assess).

## Domain Knowledge Prerequisites

Load these skills at session start before executing any phase. Full skill descriptions and what each provides: `references/domain-knowledge-prerequisites.md`.

Before any phase writes a path, command, fact, or cross-plugin reference into runtime text, confirm it is present in every environment, bundled and reached by a relative path inside the plugin, or inlined; otherwise inline, bundle, guard, or delete it. A harness variable counts only where that harness substitutes it.

Required — load at session start:

1. `Skill(skill="plugin-creator:claude-plugins-reference-2026")` — plugin.json schema, component types, environment variables, installation scopes, path rules
2. `Skill(skill="plugin-creator:claude-skills-overview-2026")` — SKILL.md format, all 14 frontmatter fields, YAML multiline bug, allowed-tools string format, context fork behavior

Required for phases involving hooks (Phase 4: Create, Phase 5: Debug):

3. `Skill(skill="plugin-creator:hooks-guide")` — 13 hook event types, exit codes, tool denial mechanisms, agent frontmatter fields

Required for phases involving agents (Phase 4: Create):

4. `Skill(skill="plugin-creator:claude-subagent-reference")` — all agent frontmatter fields with descriptions, built-in agents, scope and file locations, tool restrictions, permission modes, hooks and memory configuration, fork mode, agent teams

Recommended for component selection and plugin configuration decisions:

5. `Skill(skill="plugin-creator:component-patterns")` — component lifecycle, discovery and activation phases, decision framework for choosing commands vs skills vs agents vs hooks vs MCP servers
6. `Skill(skill="plugin-creator:plugin-settings")` — .local.md per-project configuration pattern, YAML frontmatter parsing from hooks, configuration-driven behavior

## Workflow Overview

The authoritative top-level routing diagram lives in `references/master-workflow-diagram.md`. Load it once at session start to determine the entry phase from `<invocation_args>`. After routing, each Phase section below carries its own authoritative gate diagram for in-phase behavior.

Argument-to-phase routing summary:

- `new <concept>` → Phase 0 (RT-ICA Prerequisite Check)
- `existing <plugin-path>` with no intent → ask user for intent, then route by intent
- `existing` + `validate` / `fix-bugs` / `debug` → Phase 5 (Debug)
- `existing` + `audit` / `assess` → Phase 1 (Assess), then Phase 5 or Phase 6 based on validator exit code
- `existing` + `refactor` / `optimize` / `evaluate` → Phase 6 (Optimize)
- `existing` + `create` / `skill` / `agent` / `workflow` / `hooks` → Phase 4 (Create)
- `existing` + `test` / `verify` → Phase 7 (Verify)

## Artifact System

All work artifacts are stored in `.plugin-creator/plans/{plugin-name}/`. The full directory layout, per-artifact descriptions, and `STATE.md` read/update protocol live in `references/artifact-templates.md` → "Artifact Directory Layout".

Before starting any phase, read `STATE.md` if it exists to determine current progress. After completing each phase, update `STATE.md` with the phase completed and any decisions made.

---

## Phase 0: RT-ICA Prerequisite Check (New Plugin Only)

Entry condition: User provides `new <concept>`.

Before creating any plugin, verify all prerequisites are in place. Perform an RT-ICA assessment using the `RT-ICA SUMMARY` template in `references/artifact-templates.md`. The assessment checks 6 conditions (purpose clarity, target users, component selection, existing solutions, source material, verification method) and returns APPROVED or BLOCKED.

The following diagram is the authoritative procedure for Phase 0 RT-ICA decision gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Q{"RT-ICA decision?"}
    Q -->|"APPROVED — all 6 conditions available or derivable"| Next["Proceed to Phase 0.5 — Discussion"]
    Q -->|"BLOCKED — one or more conditions MISSING"| Block(["STOP — present missing conditions to user<br>Do not proceed to Phase 0.5 or Phase 2<br>until all conditions are AVAILABLE or DERIVABLE"])
```

---

## Phase 0.5: Discussion — Capture User Preferences (New Plugin Only)

Entry condition: RT-ICA gate returned APPROVED.

Before research, identify gray areas and capture user preferences to guide all subsequent phases.

Ask targeted questions to eliminate ambiguity. The full question set (skill-focused / agent-focused / hook-focused plugins) and the `discuss-CONTEXT.md` artifact template live in `references/artifact-templates.md`. For agent-focused plugin decisions (tools, model, permissionMode, memory, hooks), also load `/plugin-creator:claude-subagent-reference`.

Save preferences to `.plugin-creator/plans/{plugin-name}/discuss-CONTEXT.md` using the template from the artifact-templates file. These preferences guide all subsequent research and planning phases.

The following diagram is the authoritative procedure for Phase 0.5 discussion completion gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Q{"File .plugin-creator/plans/NAME/discuss-CONTEXT.md<br>exists and is non-empty?"}
    Q -->|"Yes — user preferences captured and written"| Next["Proceed to Phase 2 — Research"]
    Q -->|"No — file absent or empty"| Retry["Re-run Phase 0.5 discussion<br>Ask targeted questions again<br>Write preferences to discuss-CONTEXT.md"]
    Retry --> Q
```

---

## Phase 1: Assess (Existing Plugin Only)

Entry condition: User provides `existing <plugin-path>`.

Dispatch the assessor with the plugin directory path. Full task spec (context, output) in `references/phase-dispatch-details.md` → "Phase 1 — Assess".

The following diagram is the authoritative procedure for Phase 1 Assess decision gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    %% Gate 1: assessor output must exist before validator can be meaningful
    AssessFile{"File .plugin-creator/plans/NAME/assessment-REPORT.md<br>exists and is non-empty?"}
    AssessFile -->|"No — assessor did not complete"| RetryAssess["Re-run assessor skill<br>with plugin directory path"]
    RetryAssess --> AssessFile
    AssessFile -->|"Yes — assessment written"| ValidatorGate{"Run: uvx skilllint@latest check PATH<br>Exit code?"}
    ValidatorGate -->|"0 — no validation errors"| Skip["Proceed to Phase 6 — Optimize"]
    ValidatorGate -->|"non-zero — errors found"| Next["Proceed to Phase 5 — Debug"]
```

---

## Phase 0.6: Mission Statement Draft (New Plugin Only)

Entry condition: Discussion phase completed and discuss-CONTEXT.md written.

Before research begins, draft an initial mission statement for the plugin. This anchors all subsequent phases to the plugin's purpose and values and creates a backlog interview task for async human refinement.

Dispatch the mission-statement skill. Full task spec in `references/phase-dispatch-details.md` → "Phase 0.6 — Mission Statement Draft".

The following diagram is the authoritative procedure for Phase 0.6 completion gate.

```mermaid
flowchart TD
    Q{"File {plugin-path}/mission.json<br>exists and status field is present?"}
    Q -->|"Yes — draft mission written"| Next["Proceed to Phase 2 — Research"]
    Q -->|"No — mission.json absent"| Retry["Re-run mission-statement skill<br>with plugin concept and discuss-CONTEXT.md path"]
    Retry --> Q
```

---

## Phase 2: Research (New Plugin Only)

Entry condition: Discussion phase completed and discuss-CONTEXT.md written.

First run Researcher 0 (feature discovery) to produce the feature context. Then spawn Researchers 1–4 in a single message to run concurrently with that context as input. Merge results into `research-FINDINGS.md` before proceeding to Design.

Full prompts, contexts, and outputs for all five researchers live in `references/phase-2-researcher-prompts.md`. Summary:

- Researcher 0 — Feature discovery → `feature-context-{slug}.md`
- Researcher 1 — Existing solutions → `research-1-existing.md`
- Researcher 2 — Claude Code features → `research-2-features.md`
- Researcher 3 — Architecture patterns → `research-3-architecture.md`
- Researcher 4 — Pitfalls and official docs → `research-4-pitfalls.md`

After all four parallel researchers complete, consolidate into `.plugin-creator/plans/{plugin-name}/research-FINDINGS.md` using the template in `references/artifact-templates.md`.

The following diagram is the authoritative procedure for Phase 2 Research decision gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    %% All 4 individual research files must exist before merge is valid
    R1{"File .plugin-creator/plans/NAME/research-1-existing.md<br>exists and is non-empty?"}
    R1 -->|"No — researcher 1 (existing solutions) failed"| Retry1["Re-spawn researcher 1<br>with more specific prompt"]
    Retry1 --> R1
    R1 -->|"Yes"| R2{"File .plugin-creator/plans/NAME/research-2-features.md<br>exists and is non-empty?"}
    R2 -->|"No — researcher 2 (Claude Code features) failed"| Retry2["Re-spawn researcher 2<br>with more specific prompt"]
    Retry2 --> R2
    R2 -->|"Yes"| R3{"File .plugin-creator/plans/NAME/research-3-architecture.md<br>exists and is non-empty?"}
    R3 -->|"No — researcher 3 (architecture patterns) failed"| Retry3["Re-spawn researcher 3<br>with more specific prompt"]
    Retry3 --> R3
    R3 -->|"Yes"| R4{"File .plugin-creator/plans/NAME/research-4-pitfalls.md<br>exists and is non-empty?"}
    R4 -->|"No — researcher 4 (pitfalls/docs) failed"| Retry4["Re-spawn researcher 4<br>with more specific prompt"]
    Retry4 --> R4
    R4 -->|"Yes — all 4 researcher outputs exist"| Merge{"File .plugin-creator/plans/NAME/research-FINDINGS.md<br>exists and is non-empty?"}
    Merge -->|"Yes — merge complete"| Next["Proceed to Phase 3 — Design"]
    Merge -->|"No — merge not yet written"| DoMerge["Consolidate all 4 research files<br>into research-FINDINGS.md"]
    DoMerge --> Merge
```

---

## Phase 3: Design (New Plugin Only)

Entry condition: Research gate passed.

Execute three dispatch steps: (1) prerequisite check via `dh:rt-ica`, (2) design plan creation, (3) plan verification. Full task specs in `references/phase-dispatch-details.md` → "Phase 3 — Design". Track plan-checker iteration count in `STATE.md`; escalate to user on the third FAIL.

The following diagram is the authoritative procedure for Phase 3 Design decision gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    %% Track iteration count to enforce the 3-attempt limit from Error Handling
    IterCheck{"Current plan-checker iteration count<br>(track in STATE.md — how many FAIL verdicts so far)?"}
    IterCheck -->|"Count = 3 — limit reached"| Escalate(["STOP — escalate to user<br>Plan checker has returned FAIL 3 times<br>Present FAIL feedback and await direction"])
    IterCheck -->|"Count < 3 — iterations remain"| PlanCheck{"design-PLAN.md exists<br>AND plan-checker returns PASS?"}
    PlanCheck -->|"PASS — plan complete and verified"| Next["Proceed to Phase 4 — Create"]
    PlanCheck -->|"FAIL — plan incomplete or unverifiable"| Revise["Increment iteration count in STATE.md<br>Pass design-PLAN.md and FAIL feedback<br>to planner for revision"]
    Revise --> IterCheck
```

---

## Phase 4: Create

Entry condition: Design gate passed (new plugin path) OR user selected a create intent on the existing plugin path (no design plan required — use the user's stated component description directly).

For each component defined in `design-PLAN.md`, invoke the appropriate creator skill (skill-creator, agent-creator, or hook-creator). Full task specs in `references/phase-dispatch-details.md` → "Phase 4 — Create". For agent-frontmatter decisions during agent creation, also load `/plugin-creator:claude-subagent-reference`. Create `plugin.json` via `uv run plugins/plugin-creator/scripts/create_plugin.py` if it does not exist.

The following diagram is the authoritative procedure for Phase 4 Create decision gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Q{"All file paths listed in design-PLAN.md<br>exist on disk at their specified paths?"}
    Q -->|"Yes — all components created"| Next["Proceed to Phase 5 — Debug"]
    Q -->|"No — one or more planned files are absent"| Retry["Identify which planned files are missing<br>Create remaining components using the appropriate creator skill<br>Return to gate check"]
    Retry --> Q
```

---

## Phase 5: Debug (Both Paths)

Entry condition: Create gate passed (new path) OR Assess gate failed (existing path).

Debug fixes validation errors. Run `uvx skilllint@latest check <plugin-path>` first to identify issues. The authoritative Phase 5 error-routing diagram lives in `references/phase-gate-diagrams.md` — load it when entering this phase. It routes SK007, SK006, broken links, frontmatter errors, tool format errors, and other structural errors to their specific fix and loops back to re-validate.

---

## Phase 6: Optimize (Both Paths)

Entry condition: Debug gate passed OR Assess gate passed with no errors.

Optimize improves quality — descriptions, progressive disclosure, agent prompts, documentation. This phase is not about fixing errors (that is Debug) but about raising quality.

Execute five dispatches in order: (1) skill goal resolution via `skill-goal-extractor`, (2) pre-optimization tightening via `evaluate-and-tighten-skills`, (3) structural plugin improvement via `refactor-plugin`, (4) content quality optimization via `optimize-claude-md`, (5) agent prompt optimization via `subagent-refactorer`, preceded by loading `subagent-refactoring-methodology`. Full task specs in `references/phase-dispatch-details.md` → "Phase 6 — Optimize".

After structural plugin improvement, re-resolve and approve goals for every skill that was created,
renamed, split, merged, or materially changed before content optimization. Reuse the initial goals
only for unchanged skills.

Enter each step through its skill where one exists. `optimize-claude-md` owns baseline measurement, goal resolution, agent delegation, independent verification, and reporting — dispatching `ai-doc-optimizer` directly skips all of it and yields an unmeasured, unverified rewrite.

Order is load-bearing: goals are the standard every later dispatch judges content against, and tightening runs before structural and content work because removing dead weight can drop a skill back under the split threshold and stops later passes from polishing prose that should have been deleted.

The following diagram is the authoritative procedure for Phase 6 Optimize completion gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    %% Score line presence determines which branch to take
    ScoreCheck{"Run: uvx skilllint@latest check PATH<br>Does output contain a 'Score:' line?"}
    ScoreCheck -->|"Yes — score present in output"| ScoreVal{"Score value >= 80?"}
    ScoreCheck -->|"No — validator produces no score"| UserAccept{"Ask user — accept current quality<br>and proceed to documentation?"}

    ScoreVal -->|"Yes — score >= 80, quality target met"| Next["Proceed to Phase 6.5 — Documentation"]
    ScoreVal -->|"No — score < 80, quality below target"| Retry["Identify lowest-scoring components<br>Re-run optimization steps targeting those components"]
    Retry --> ScoreCheck

    UserAccept -->|"Yes — user accepts current quality"| Next
    UserAccept -->|"No — user wants more improvement"| Retry
```

---

## Phase 6.5: Documentation (Both Paths)

Entry condition: Optimize phase complete.

Generate comprehensive documentation for the plugin by dispatching `plugin-assessor` with the full set of plugin artifacts. Full task spec (context, prompt, output) in `references/phase-dispatch-details.md` → "Phase 6.5 — Documentation".

The following diagram is the authoritative procedure for Phase 6.5 Documentation completion gate. Execute steps in the exact order shown, including branches, decision points, and stop conditions.

```mermaid
flowchart TD
    Q{"File {plugin-path}/README.md<br>exists and is non-empty?"}
    Q -->|"Yes — documentation generated"| Next["Proceed to Phase 7 — Verify"]
    Q -->|"No — README.md absent or empty"| Retry["Re-run documentation task<br>with explicit instruction to create README.md<br>at {plugin-path}/README.md"]
    Retry --> Q
```

---

## Phase 7: Verify (Both Paths)

Entry condition: Documentation phase complete.

Run multi-layer validation. Full task spec in `references/phase-dispatch-details.md` → "Phase 7 — Verify". The authoritative 4-layer validation gate diagram lives in `references/phase-gate-diagrams.md` — load it when entering this phase. Any layer failure routes to Phase 5 (Debug).

---

## Phase-to-Skill Mapping

Full lookup table with exact invocation syntax for all phase-skill pairings: `references/phase-skill-mapping.md`.

Key invocations:
- Phase 1: `Skill(skill="plugin-creator:assessor")`
- Phase 2: `Skill(skill="plugin-creator:feature-discovery")` + 4-way parallel researchers via subagent_type
- Phase 4: skill-creator, agent-creator, hook-creator (one Skill call per component type)
- Phase 5: lint, refactor-skill (one Skill call per error type)
- Phase 7: `Skill(skill="plugin-creator:ensure-complete")`

---

## Error Handling

14 failure modes with recovery actions: `references/error-handling.md`.

Key rules:
- SK007 (token limit exceeded) — run `/plugin-creator:refactor-skill`; editing alone is not sufficient
- SK006 (approaching limit) — extract content to `references/` and re-validate
- RT-ICA BLOCKED — do not proceed to Discussion or Research until all conditions resolve
- STATE.md absent — read all `.plugin-creator/plans/{plugin-name}/` artifacts to reconstruct phase

---

## Example Sessions

Two complete walkthroughs (new plugin full lifecycle + existing plugin with validation errors): `references/example-sessions.md`.

---

## Sources

- Architecture spec: `../../../../plan/architect-plugin-lifecycle.md`
- Feature context: `../../../../plan/feature-context-plugin-lifecycle.md`
- Plugin-creator CLAUDE.md: `../../CLAUDE.md`
- GitHub Issue: #427
