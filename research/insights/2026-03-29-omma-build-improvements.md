# Improvement Proposals: Omma (omma.build)

**Research entry**: ./research/ai-design-tools/omma-build.md
**Generated**: 2026-03-29
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Real-Time Cross-Agent Dependency Resolution

**Source pattern**: "Parallel execution resolves dependencies as they complete, reducing wall-clock time" and "dependencies between code and assets are resolved in real-time" (Technical Architecture > Key Design Decisions)
**Local system**: .claude/skills/swarm-patterns/SKILL.md, plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence Low: research entry describes pattern at architectural level without naming a concrete mechanism (no API, no protocol, no data format for partial-output streaming between agents)

### Current state

The SAM task plan uses a static dependency DAG defined at plan-creation time. Tasks become ready only when all predecessor tasks reach COMPLETE status. An agent working on Task B cannot consume partial output from Task A -- it must wait for Task A to fully complete. File: plugins/development-harness/skills/implement-feature/SKILL.md, Progress Loop step 2 (`sam_ready` returns tasks whose dependencies are all COMPLETE).

### Target state

Agents could publish intermediate artifacts (partial outputs) to a shared workspace. Other agents with dependencies on those artifacts would be notified and could begin work on the portions that are unblocked, rather than waiting for full task completion. This would require: (1) a partial-output publication mechanism, (2) a notification channel from producer to consumer agents, (3) a dependency resolution model that understands artifact-level granularity rather than task-level granularity.

### Measurable signal

A task with a dependency on another in-progress task could begin execution when the specific artifact it needs is published, rather than waiting for full predecessor completion. Observable as: Task B starts while Task A status is still IN_PROGRESS, because Task A published the artifact Task B needs.

---

## Improvement 2: Output Synthesis Pattern for Parallel Agent Results

**Source pattern**: "Merging outputs from heterogeneous agents into a cohesive result is a core challenge in agent-driven development" (Relevance to Claude Code Development > Direct Relevance)
**Local system**: .claude/skills/swarm-patterns/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence Medium: swarm-patterns SKILL.md has a comment placeholder for synthesis (line 339-340: "// === STEP 4: Synthesize findings === // Combine all reviewer findings into a cohesive report") but no documented pattern or instructions. The research entry identifies this as a core challenge but does not describe a specific synthesis mechanism -- only that Omma has an "Output Synthesis" step that merges code + assets.

### Current state

The swarm-patterns skill documents parallel specialist patterns (Pattern 1 -- Parallel Specialists, Pattern 6 -- Coordinated Refactoring) where multiple agents produce independent outputs. Step 4 in the Coordinated Refactoring example (line 339) contains a comment "Synthesize findings" with no implementation guidance. The orchestrator is expected to manually read all agent outputs and synthesize them, but no pattern, agent prompt, or structured approach is documented. File: .claude/skills/swarm-patterns/SKILL.md, lines 339-340.

### Target state

The swarm-patterns skill would include a documented "Output Synthesis" pattern describing: (1) how to collect heterogeneous outputs from parallel agents, (2) a synthesis agent prompt template that merges findings into a unified artifact, (3) conflict resolution when agents produce contradictory outputs. The pattern would be as concrete as the existing Pattern 1-6 recipes, with example TeamCreate/Agent/SendMessage calls.

### Measurable signal

The swarm-patterns SKILL.md contains a new numbered pattern (e.g., "Pattern N -- Output Synthesis") with: (a) a complete code example showing synthesis after parallel agent completion, (b) a synthesis agent prompt template, (c) at least one conflict resolution strategy. The comment at line 339 is replaced with a reference to this pattern.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Real-Time Cross-Agent Dependency Resolution | Low | Research entry describes pattern at architectural level ("resolved in real-time") without naming a concrete mechanism. Would need Omma's actual API documentation or source code to identify the specific protocol for partial-output streaming. The local SAM system's static DAG may be sufficient for current task granularity. |
| Output Synthesis Pattern | Medium | Gap is observable (placeholder comment in swarm-patterns line 339), but the research entry does not describe Omma's specific synthesis mechanism -- only that it exists. To raise confidence, would need to examine Omma's actual output synthesis implementation or find detailed documentation of their merge strategy. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Parallel Agent Coordination | Already covered: implement-feature SKILL.md dispatches ready tasks in parallel via TeamCreate when 2+ tasks are ready (lines 67-75). swarm-patterns SKILL.md documents Pattern 1 (Parallel Specialists), Pattern 3 (Swarm), and Pattern 6 (Coordinated Refactoring). |
| Post-generation editing / creator control | Incompatible with repo architecture: Omma's pattern relies on Spline's visual GUI editor for post-generation refinement. This repo operates as a CLI-based agent orchestration system with no visual editor component. |
| Multi-Modal Code Generation | Too abstract: Omma's LLM-based code generation targeting Tailwind CSS/Three.js is a product feature, not an orchestration pattern. No actionable gap for agent workflow tooling. |
| Natural Language Interface for Non-Developers | Too abstract: accessibility patterns for non-technical users. No concrete mechanism described that maps to agent orchestration, skill structure, or workflow scripts. |
| Data Integration Patterns (multi-modal input) | Too abstract: Omma's data ingestion layer (CSV, JSON, 3D assets) is a product feature for content creation, not an agent orchestration pattern. No actionable gap for skill or workflow systems. |
