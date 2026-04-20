# Utilization Assessment: Orchestra

**Research entry**: ./research/agent-frameworks/orchestra.md
**Generated**: 2026-04-20
**Integration surfaces found**: Yes (CLI commands, state files, configuration)
**Proposals written**: 0
**Skipped**: 3
**Assessment**: Integration surfaces identified, but no suitable local integration proposals

---

## Integration Surface Analysis

Orchestra documents the following callable surfaces:

| Surface Type | Details |
|---|---|
| **CLI commands** | `/orchestra run`, `/orchestra resume`, `/orchestra status` (documented in README and SKILL.md) |
| **State files** | `.orchestra/` directory with YAML/markdown config, DAG, task files, history (documented in state-manager.md) |
| **Autonomy modes** | `full_auto`, `checkpoint`, `per_task` (documented in README) |
| **Configuration** | token_budget, max_parallel, agent_model, use_worktrees settings (documented in config schema) |

All surfaces are **documented and callable**. Orchestra registers as a Claude Code **skill** and **plugin** for orchestrating multi-agent work.

---

## Competitive Technology Analysis

Orchestra solves the problem of "orchestrating complex multi-agent work with context optimization and token budgeting."

Three local systems already solve this same problem with mature, production-grade implementations:

### 1. `/dispatch` Skill (Development Harness Plugin)

**Located**: `plugins/development-harness/skills/dispatch/SKILL.md`

**Functionality**:
- Multi-agent team orchestration via TeamCreate and SendMessage
- Wave-based parallel execution (SAM task wave dispatch)
- Discovery relay between waves (experience sharing)
- Blocker handling and worker coordination
- Synthesis of team results

**Matches Orchestra on**:
- Context curation (passes only what workers need)
- Parallel execution (waves run independently)
- Task dependencies (blocks/depends_on fields)
- Autonomy levels (implicit via wave gates)

**Differs from Orchestra**:
- Uses existing Claude Code team primitives (TeamCreate, SendMessage, Agent tool)
- Rooted in SAM (Stateless Agent Methodology) with proven integration
- Supports discovery relay between waves (explicit knowledge sharing)
- Tied to development-harness lifecycle (S1-S7 pipeline)

### 2. Development Harness 7-Stage Pipeline (SAM)

**Located**: `plugins/development-harness/skills/development-harness/SKILL.md`

**Functionality**:
- 7-stage feature development pipeline (Discovery, Planning, Context Integration, Task Decomposition, Execution, Forensic Review, Final Verification)
- Automatic language-specific role resolution (Python/TypeScript/Rust/fallback)
- Task decomposition from specs/plans
- Per-task execution via language specialists
- ARL-driven human touchpoint gates (constraint analysis, not arbitrary checkpoints)

**Matches Orchestra on**:
- Complex work decomposition (stage S4)
- Multi-agent dispatch (stage S5)
- Token-aware execution (implicit via per-task context)
- Resumability (state management in `~/.dh/`)

**Differs from Orchestra**:
- Owns entire feature development workflow, not just orchestration
- Language-plugin composition model (specialists snap in)
- Artifact-based state management (GitHub Issues as source of truth)
- ARL constraint analysis for human escalation

### 3. Swarm Operations (`orchestrating-swarms` Facade)

**Located**: `.claude/skills/orchestrating-swarms/SKILL.md`

**Functionality**:
- Multi-agent team orchestration primitives (TeamCreate, SendMessage, TeamDelete)
- Sub-agent spawning with agent type selection (built-in types: Explore, Plan, general-purpose, Bash; plugin types)
- Team inbox for message routing
- Teammate failure recovery

**Matches Orchestra on**:
- Multi-agent coordination
- Parallel execution
- Message-based communication

**Differs from Orchestra**:
- Lower-level primitives (facade to TeamCreate/SendMessage, not an orchestration framework)
- No DAG decomposition
- No token budgeting
- No dashboard or visualization

---

## Why No Integration Is Proposed

**Same Problem, Different Solutions:**

All three local systems orchestrate multi-agent work. Orchestra introduces a fourth solution with:
- DAG-based task decomposition
- Context curation per task
- Token budgeting
- Optional dashboard

However, each local system is already **deeply integrated** into the repository's workflow:

1. **`dispatch`** — Used in `/dh:work-milestone` for concurrent task execution. Tightly coupled to SAM task format and development-harness stage gates.

2. **Development Harness** — Owns the end-to-end feature development process. Integrated with language plugins, quality gates, artifact lifecycle, and ARL human touchpoints.

3. **Swarm Operations** — Primitive layer for low-level team orchestration. Used by dispatch and development-harness.

**Adding Orchestra Would Require:**

- Deciding which system (dispatch, development-harness, or Orchestra) owns feature orchestration
- Migrating existing work from one system to another
- Maintaining two competing implementations in parallel
- Complex glue code to reconcile their state models

This is an **architectural decision**, not an integration opportunity.

---

## Skipped Systems

| Local System | Reason Skipped |
|---|---|
| `@dh:swarm-task-planner` | Already uses development-harness SAM dispatch; Orchestra would replace, not enhance. No incremental integration point. |
| `/dh:implement-feature` | Tightly coupled to SAM task format and quality gates. Orchestra uses different decomposition (DAG procedures A/B/C); incompatible models. |
| `/dh:dispatch` | Mature implementation with wave-based execution, discovery relay, blocker handling. Orchestra's context curation and token budgeting are orthogonal improvements, but would require rearchitecting entire skill. |

---

## Recommendation

**Do not propose Orchestra as a local integration.**

Orchestra is a **competing architecture** for multi-agent orchestration, not a complementary service. Adopting it would require a system-wide decision to replace existing orchestration (dispatch + development-harness) — that is a strategic choice, not a tactical integration.

### When Orchestra Might Be Relevant

- **Comparison research**: If evaluating whether to migrate from SAM+dispatch to Orchestra's DAG model, this research provides the feature comparison needed.
- **Dashboard enhancement**: If seeking visualization of task execution and token usage, Orchestra's dashboard approach could inform design decisions for development-harness.
- **Context curation patterns**: Orchestra's three decomposition procedures (Rich/Medium/Lean input handling) could be adapted for SAM task context assembly.

These are **pattern adoptions**, not integrations. If the decision is made to study or adopt Orchestra patterns, create a new research entry in `./research/insights/` with the title `2026-04-20-orchestra-pattern-analysis` documenting which patterns are candidates for adoption and how they would integrate with existing SAM/dispatch systems.

---

## Assessment Summary

**STATUS**: Integration surfaces identified, but no suitable local integration opportunities.

**REASON**: Orchestra and local orchestration systems (dispatch, development-harness) solve the same problem with competing approaches. Integration would require architectural replacement decisions, not incremental enhancements.

**NEXT STEPS**: If you want to adopt Orchestra patterns (DAG decomposition, context curation, token budgeting), file a backlog item for pattern analysis and strategic evaluation.
