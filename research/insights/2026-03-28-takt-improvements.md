# Improvement Proposals: TAKT (TAKT Agent Koordination Topology)

**Research entry**: ./research/research-agent-patterns/takt.md
**Generated**: 2026-03-28
**Patterns assessed**: 11
**Backlog items created**: 0
**Deferred (low confidence)**: 4
**Skipped (already covered or tracked)**: 7

---

## Improvement 1: Faceted prompt composition for skill instructions

**Source pattern**: "Faceted Prompting: Decompose agent instructions into independent facets (role, policies, domain knowledge, procedure) that compose freely. This enables high reusability and maintainability compared to monolithic prompts" (Patterns Worth Adopting, item 1)
**Local system**: plugins/plugin-creator/skills/skill-creator/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: SKILL.md files already separate concerns into sections (frontmatter for identity, workflow steps, references for domain knowledge), but the composition is monolithic per-file rather than faceted. Whether the existing progressive disclosure pattern (SKILL.md + references/) already achieves equivalent reusability to TAKT's four-facet model would require measuring actual reuse rates across skills. The skill-creator does not currently emit reusable facet files that compose across multiple skills.

### Current state

Skills are self-contained SKILL.md files with optional references/ subdirectories. Each SKILL.md contains all four concerns (role via description, policies via rules sections, domain knowledge via inline or references, procedure via workflow steps) in a single file. There is no mechanism to share a policy facet (e.g., "always run linting before commit") across multiple skills without duplicating the text. File: plugins/plugin-creator/skills/skill-creator/SKILL.md -- the skill creation workflow produces monolithic SKILL.md files.

### Target state

A shared facets directory (e.g., `.claude/facets/` or per-plugin `facets/`) contains reusable policy, persona, and knowledge files. SKILL.md frontmatter includes a `facets:` field listing facets to compose at load time. The skill-creator workflow offers facet selection during skill creation.

### Measurable signal

At least 2 skills reference the same shared facet file via a `facets:` field in frontmatter. Running `Grep` for `facets:` across SKILL.md files returns 2+ matches pointing to the same facet file.

---

## Improvement 2: Deterministic rule evaluation with AI judge fallback for workflow routing

**Source pattern**: "Explicit Rule Evaluation: 5-stage fallback rule evaluation (aggregate -> tag-based -> AI judge) provides deterministic routing with graceful fallbacks, applicable to skill workflow decisions" (Patterns Worth Adopting, item 2)
**Local system**: plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: The implement-feature loop uses `sam_ready` and `sam_status` for task routing, which is dependency-graph-based rather than rule-evaluated. The routing is deterministic but lacks conditional branching based on agent output (e.g., "if review found critical issues, route to fix instead of next task"). Whether adding rule evaluation would prevent concrete failures requires examining actual workflow failures where the current dependency-only routing was insufficient. No such failure evidence was found in the research entry or local files.

### Current state

The implement-feature progress loop (lines 36-114 of SKILL.md) routes tasks purely by dependency graph readiness (`sam_ready` returns tasks whose dependencies are all COMPLETE). There is no mechanism for conditional routing based on agent output content -- e.g., routing to a fix movement if a review agent flags critical issues, or aborting if a security check fails. The complete-implementation quality gates (6 sequential phases) are also fixed-order without conditional branching based on phase output.

### Target state

Implement-feature supports optional `rules:` blocks in task YAML that evaluate agent output against conditions (tag-based patterns first, AI judge fallback). When a rule matches, the task routes to a specified next task or ABORT state instead of the default dependency-based next task.

### Measurable signal

A task YAML file contains a `rules:` block with at least one condition. Running the implement-feature loop with that task demonstrates conditional routing (the next dispatched task differs based on agent output matching or not matching the rule condition).

---

## Improvement 3: Loop detection with max-iteration guard for implement-feature

**Source pattern**: "Loop Detection and Cycle Management: TAKT's cycle detector with synthetic judge movements prevents infinite review-fix-review loops, a pattern applicable to skill error recovery" (Applications, item 6) and "Supports loop detection and cycle detection with synthetic judge movements to prevent infinite loops" (Core Piece Engine, bullet 1)
**Local system**: plugins/development-harness/skills/implement-feature/SKILL.md
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: The implement-feature loop is dependency-graph-based and tasks move only forward (PENDING -> IN_PROGRESS -> COMPLETE/BLOCKED). Cycles require a task to re-enter PENDING state, which the current SAM schema does not support. The complete-implementation quality gates do have a "Recursive Follow-up Handling" section that creates new task files for follow-ups, which could theoretically create unbounded recursion. However, no evidence of actual infinite loops in the current system was found in local files or the research entry. The gap is inferred from architectural similarity rather than observed failure.

### Current state

The implement-feature SKILL.md (line 155-161) invokes complete-implementation when all tasks are COMPLETE. Complete-implementation can create follow-up task files and "recurse only when the follow-up matches the current scope and priority." There is no explicit max-iteration counter or cycle detection. If follow-ups generate further follow-ups, the recursion depth is unbounded.

### Target state

Complete-implementation tracks recursion depth via a counter passed through follow-up invocations. When depth exceeds a configurable maximum (e.g., `max_quality_gate_recursions: 3`), the skill stops recursing and reports the remaining follow-ups as backlog items instead.

### Measurable signal

Complete-implementation SKILL.md contains a `max_quality_gate_recursions` parameter or equivalent guard. A test scenario with a follow-up that generates another follow-up terminates after the configured depth and creates a backlog item instead of recursing further.

---

## Improvement 4: NDJSON execution logging for skill and agent runs

**Source pattern**: "NDJSON Logging: Append-only session logs support real-time streaming and analysis; applicable to skill execution tracing and analytics" (Patterns Worth Adopting, item 5) and "NDJSON Session Logging: All piece executions logged to .takt/logs/{sessionId}.jsonl with record types: piece_start, movement_start, movement_complete, piece_complete, piece_abort" (Analytics and Reporting section)
**Local system**: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: Already tracked as #109 (SAM: Audit Trail / Observability) and #317 (Structured session work logs). The TAKT-specific NDJSON format with typed records (piece_start, movement_start, etc.) is one possible implementation of the observability gap already identified. Previous insights (trainloop, emqutiti, oh-my-claudecode) have all mapped to #109/#317. No new gap beyond what is already tracked.

### Current state

task_status_hook.py writes `LastActivity` timestamps and status transitions to task YAML files. There is no append-only session log capturing the full sequence of events across a multi-task implementation run. Event reconstruction requires parsing multiple task YAML files and inferring order from timestamps.

### Target state

Each implement-feature run produces an NDJSON log file at `~/.dh/projects/{slug}/logs/{session-id}.jsonl` with typed records (task_start, task_complete, quality_gate_start, quality_gate_complete, session_abort) appended in real time.

### Measurable signal

After an implement-feature run completes, a `.jsonl` file exists at the expected path containing at least one `task_start` and one `task_complete` record per dispatched task.

---

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Faceted prompt composition | Medium | Need to measure actual facet reuse rates across skills to confirm monolithic SKILL.md is a real bottleneck vs. TAKT's faceted approach. The existing references/ pattern may already provide equivalent modularity. |
| Deterministic rule evaluation with AI judge fallback | Medium | No evidence of concrete workflow failures caused by lack of conditional routing. Would need to examine actual implement-feature sessions where dependency-only routing produced wrong outcomes. |
| Loop detection with max-iteration guard | Low | No evidence of actual infinite recursion in complete-implementation. Gap is inferred from architectural possibility, not observed failure. |
| NDJSON execution logging | Low | Already tracked as #109 and #317. TAKT's specific format is one implementation option, not a new gap. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Session Continuity Across Phases | Claude Code agents do not support session resumption across separate Agent tool invocations. Each Agent call creates a fresh context. This is a platform constraint, not an extensible gap in the local skill system. TAKT achieves this because it controls the agent SDK session lifecycle directly. |
| Worktree Isolation (git clone --shared) | Already tracked as #453 "Systematic git worktree isolation for concurrent task agents". The local system already implements worktree isolation via `/work-milestone` (using `git worktree` rather than `git clone --shared`). |
| SAM Task to TAKT Piece Generation | Integration opportunity requires TAKT to be installed as a dependency. This is a cross-tool integration, not an improvement to a local system. No local file would change -- it would be a new tool dependency. Too abstract without a concrete use case driving adoption. |
| Claude Code Skill as TAKT Facet | Same as above -- requires TAKT adoption as a dependency. No concrete local gap identified. |
| Skill Repertoire Packages | The local plugin marketplace (`.claude-plugin/marketplace.json`) already provides package management for skills. TAKT's repertoire model addresses the same need in a different format. No gap -- equivalent capability exists. |
| Quality Gate Automation via audit pieces | complete-implementation already runs 6 sequential quality gate phases (code review, feature verification, integration check, doc drift audit, doc update, context refinement) using specialized agents. TAKT's audit pieces (audit-architecture, audit-security) are equivalent in intent. The local system's agent-based approach is more flexible than YAML-defined read-only pieces. |
| Skill Permission Management (readonly/edit/full) | Claude Code sandbox configuration and tool permissions are controlled at the Agent tool level (via `allowed_tools` parameter) and in agent frontmatter (`tools:` field). TAKT's permission mode system maps to existing functionality. No gap -- equivalent capability exists in plugins/plugin-creator/skills/skill-creator/SKILL.md via the tools frontmatter field. |
