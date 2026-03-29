# Improvement Proposals: GitAgent

**Research entry**: ./research/agent-frameworks/gitagent.md
**Generated**: 2026-03-29
**Patterns assessed**: 10
**Backlog items created**: 0
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 7

---

## Improvement 1: Add examples/ directory convention to skill structure

**Source pattern**: "Skills are stored in a `skills/` directory with: [...] examples/ -- Example inputs and outputs" (Key Features, Section 4: Skills System)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence Medium: the local skill-creator's `references/` directory may already serve this purpose for some skills; would need a survey of existing skills to confirm that examples are systematically absent and that a dedicated `examples/` convention would add value beyond what `references/` provides.

### Current state

The skill-creator SKILL.md defines three bundled resource directories: `scripts/`, `references/`, and `assets/` (lines 164-167 of skill-creator/SKILL.md). There is no `examples/` directory in the skill anatomy. GitAgent's skill structure includes an explicit `examples/` directory for calibration interactions (example inputs and outputs). The `init_skill.py` scaffolding script does not create an `examples/` directory.

### Target state

The skill-creator's "Anatomy of a Skill" section includes `examples/` as an optional bundled resource directory. The `init_skill.py` scaffold creates an `examples/` directory with a placeholder file when the skill's purpose involves input/output transformation. `skilllint` recognizes `examples/` as a valid skill subdirectory.

### Measurable signal

Read `plugins/plugin-creator/skills/skill-creator/SKILL.md` -- the "Anatomy of a Skill" section lists `examples/` alongside `scripts/`, `references/`, `assets/`. Run `uv run plugins/plugin-creator/scripts/init_skill.py` with a test skill -- output directory contains `examples/` subdirectory.

---

## Improvement 2: Declarative inter-step data flow in SAM task plans

**Source pattern**: "Data flows between steps via template syntax `${{ steps.step-name.outputs.field }}`. No LLM discretion on execution order" (Key Features, Section 6: Deterministic Workflows / SkillsFlow)
**Local system**: .claude/skills/implement-feature/SKILL.md (SAM task plans)
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: SAM task plans have `depends_on` for ordering but agent delegation in this repo passes context via file paths in the task body, not template expressions. The file-path-based approach may already be equivalent in practice since agents read files directly. Would need to examine cases where inter-step data is lost or misrouted to confirm this is a real gap rather than a stylistic difference.

### Current state

SAM task plans (YAML files in `plan/`) define tasks with `depends_on` for ordering, but there is no template expression language for referencing outputs of previous steps. When task T3 needs the output of task T2, the orchestrator must manually include the file path or artifact reference in the delegation prompt. The `sam_schema` does not define an `outputs` field on tasks or a template resolution mechanism.

### Target state

SAM task definitions support an `outputs` field (list of named artifact paths) and an `inputs` field that can reference prior task outputs via `${{ tasks.T2.outputs.artifact_name }}`. The `implement-feature` orchestrator resolves these templates before delegation, substituting actual file paths. This makes data flow between tasks explicit and auditable in the plan file itself.

### Measurable signal

Read a SAM task plan YAML file -- tasks contain `outputs:` and `inputs:` fields with template references. Run `uv run implementation_manager.py ready-tasks` on a plan with templates -- output shows resolved input paths for each ready task.

---

## Improvement 3: Agent-level bootstrap and teardown hooks

**Source pattern**: "Define `bootstrap.md` and `teardown.md` in `hooks/` folder to control agent startup and shutdown behavior" (Examples & Patterns, Agent Lifecycle with Hooks)
**Local system**: .claude/skills/start-task/SKILL.md, plugins/plugin-creator/skills/hooks-guide/SKILL.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence Low: the local system has session-level hooks (via hooks.json) and task-level hooks (task_status_hook.py), but per-agent bootstrap/teardown is a different concept. It is unclear whether per-agent hooks would add value given that agents in this repo are stateless markdown files, not persistent processes. The GitAgent pattern assumes agents with persistent memory that needs initialization, which does not match the local architecture.

### Current state

The hooks system (hooks.json, hooks-guide skill) supports session-level hooks (PreToolUse, PostToolUse, Notification, Stop) and task-level hooks (task_status_hook.py). There are no per-agent hooks that run when a specific agent is invoked or completes. Agent files (.claude/agents/*.md) are pure prompt definitions with no lifecycle behavior.

### Target state

Agent frontmatter supports optional `bootstrap` and `teardown` fields pointing to scripts or markdown instructions that execute when the agent is spawned and when it completes. This enables per-agent setup (loading specific context, checking prerequisites) and cleanup (archiving working memory, reporting metrics).

### Measurable signal

Read an agent file in `.claude/agents/` -- frontmatter contains `bootstrap: ./scripts/setup.sh`. Spawn the agent via Agent tool -- bootstrap script executes before the agent prompt is delivered.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| examples/ directory in skill structure | Medium | Need survey of existing skills to confirm `references/` does not already serve this purpose; GitAgent's `examples/` may map directly to what some skills already put in `references/` |
| Declarative inter-step data flow (template expressions) | Medium | File-path-based context passing may be functionally equivalent; need evidence of data loss or misrouting between SAM tasks to confirm this is a real gap |
| Per-agent bootstrap/teardown hooks | Low | Local agents are stateless markdown prompts, not persistent processes; GitAgent's pattern assumes agent memory initialization which does not match local architecture |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Portable agent definitions / framework export adapters | Not applicable -- this repo is Claude Code-specific; cross-framework export is outside architectural scope |
| Compliance and audit configuration (FINRA, SEC, etc.) | Not applicable -- specialized regulated-industry domain not relevant to a skills marketplace plugin |
| Version control for agent definitions | Already covered -- the repository IS a git repo; all agents, skills, and plugins are version-controlled with full git history |
| Framework porting (import/export adapters) | Same as portable agent definitions; outside scope |
| Composable agent hierarchies with extends/dependencies | Architectural incompatibility -- local system uses delegation-based composition (Agent tool, TeamCreate) rather than inheritance; the patterns serve different design goals |
| Skill marketplace/registry with remote install | Already covered by Claude Code's native plugin marketplace (`.claude-plugin/marketplace.json`, `claude plugin install`) which provides equivalent discovery and installation |
| Schema validation (AJV for agent.yaml) | Already covered -- `skilllint` validates skill frontmatter schema, `claude plugin validate` validates plugin.json; agent frontmatter validation exists via skilllint |
