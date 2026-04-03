# Improvement Proposals: OpenSpace

**Research entry**: ./research/ai-research-tools/OpenSpace.md
**Generated**: 2026-03-28
**Patterns assessed**: 6
**Backlog items created**: 0 (backlog MCP tools unavailable in this session)
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: Skill Health Metrics Tracking

**Source pattern**: "Multi-layer tracking across the entire execution stack: Skills: applied rate, completion rate, effective rate, fallback rate" (Key Features, Section 2: Full-Stack Quality Monitoring)
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the task_status_hook.py tracks LastActivity timestamps and task status transitions (NOT_STARTED -> IN_PROGRESS -> COMPLETE), but does not track skill-level metrics. However, "skill" in this repo means a SKILL.md instruction set, not an executable unit with measurable success/failure rates. OpenSpace's "skill" is a reusable procedure with tool calls that can be instrumented. The local system's skills are prompt instructions loaded into context -- measuring "applied rate" or "completion rate" requires a fundamentally different instrumentation model that may not map cleanly.

### Current state

`task_status_hook.py` tracks task-level status transitions and LastActivity timestamps. No skill-level usage metrics exist anywhere in the codebase. When a skill is loaded via SKILL.md, there is no record of whether the skill's guidance was followed, whether the task succeeded while using that skill, or how often a skill is selected for tasks.

### Target state

A metrics collection mechanism that records, per skill invocation: (1) which skill was loaded, (2) whether the task completed successfully, (3) token usage during the skill-guided session. Metrics stored in a queryable format (SQLite or structured log) at `~/.dh/projects/{slug}/metrics/skill-usage.db`.

### Measurable signal

File `~/.dh/projects/{slug}/metrics/skill-usage.db` exists and contains rows with columns: `skill_name`, `session_id`, `task_id`, `outcome` (complete/failed/abandoned), `timestamp`. Query `SELECT skill_name, COUNT(*), AVG(CASE WHEN outcome='complete' THEN 1.0 ELSE 0.0 END) as success_rate FROM skill_usage GROUP BY skill_name` returns rows.

---

## Improvement 2: Post-Execution Skill Evolution Suggestions

**Source pattern**: "Post-Execution Analysis -- Runs after every task, analyzing full execution recordings and suggesting FIX/DERIVED/CAPTURED actions for involved skills" (Key Features, Section 1: Self-Evolution Engine)
**Local system**: `plugins/development-harness/skills/complete-implementation/SKILL.md`
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: the complete-implementation skill runs 6 quality gate phases (code review, feature verification, integration check, doc drift, doc update, context refinement) but none of these phases analyze whether the skills used during implementation could be improved. The "context-refinement" phase (T6) updates context files but does not propose skill modifications. The gap is real but mapping OpenSpace's automated evolution (which patches executable skill files) to this repo's prompt-based skills requires interpretation -- the "evolution" would mean updating SKILL.md content based on execution outcomes, which is a different mechanism than OpenSpace's code patching.

### Current state

`complete-implementation/SKILL.md` runs a 6-phase quality gate sequence after task completion. Phase T6 (context-refinement) updates context files but does not evaluate or suggest improvements to the skill instructions that guided execution. When a skill's guidance leads to a suboptimal outcome (e.g., the code-reviewer agent misses a pattern because the skill didn't mention it), there is no feedback loop that captures this and proposes a skill update.

### Target state

Phase T6 (context-refinement) or a new T7 phase includes a "skill retrospective" step: the agent reviews the execution transcript, identifies cases where skill guidance was insufficient or incorrect, and writes improvement suggestions to `~/.dh/projects/{slug}/skill-feedback/{skill-name}-{date}.md`. Each suggestion specifies: skill file path, section needing update, observed gap, proposed addition.

### Measurable signal

After running `/complete-implementation` on a plan file, `~/.dh/projects/{slug}/skill-feedback/` contains at least one file when skill gaps were detected. Each file contains fields: `skill_path`, `section`, `gap_description`, `proposed_change`.

---

## Improvement 3: Skill Version Lineage DAG

**Source pattern**: "SkillStore: SQLite-based persistence with version DAG, quality metrics, and lineage tracking" and "FIX: Repairs broken or outdated instructions in-place... producing a new version in a lineage DAG; DERIVED: Creates enhanced or specialized variants from parent skills" (Technical Architecture, Key Features Section 1)
**Local system**: `plugins/plugin-creator/skills/skill-creator/SKILL.md`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the local skill system has no versioning mechanism. Skills are files that are edited in place via git commits. Git itself provides version history, but there is no structured lineage tracking (parent-child relationships between skill variants, evolution mode tags like FIX/DERIVED/CAPTURED). Whether a dedicated DAG adds value over git history is unclear -- git already tracks every change with full diff history. The gap may be covered by existing git workflows without needing a separate system.

### Current state

Skills are single SKILL.md files edited in place. Git provides change history but no structured lineage metadata. When a skill is split (via `/refactor-skill`), the parent-child relationship is documented in cross-references within the new skills but not in a queryable database. There is no `metadata.version` field convention enforced across skills (some skills have `metadata.version` in frontmatter, most do not).

### Target state

Every SKILL.md includes a `metadata.version` field bumped on each edit. A lineage file at `plugins/{plugin}/skills/{skill}/lineage.json` records: parent skill (if derived), evolution mode (fix/derived/new), version history with dates. The `/skill-creator` skill enforces version bumping on edits.

### Measurable signal

Run `grep -r 'metadata:' plugins/*/skills/*/SKILL.md | grep version` -- returns a version field for every skill. At least one `lineage.json` file exists for a derived skill showing parent relationship.

---

## Improvement 4: Cascade Quality Monitoring for Tool Degradation

**Source pattern**: "When any component degrades (skill workflow or single tool call), cascade evolution automatically triggers for all upstream dependent skills, maintaining system-wide coherence" and "QualityManager: Tool success rate tracking with automatic degradation detection and cascade evolution" (Key Features Section 2, Technical Architecture)
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the local system does not track tool call success rates or detect degradation. However, the local system's "tools" are Claude Code built-in tools (Read, Write, Edit, Bash, Grep, Glob) and MCP tools -- these are platform-provided and not under local control. OpenSpace tracks success rates of external API tools that change independently. The local equivalent would be tracking MCP server tool reliability, but MCP servers in this repo are self-hosted and tested via CI. The degradation detection pattern may not apply to the same degree. Would need to verify whether MCP tool failures are a real problem in this repo before this pattern adds value.

### Current state

`task_status_hook.py` does not track tool call outcomes. No mechanism exists to detect when a tool (MCP or built-in) starts failing at a higher rate than normal. If an MCP server tool begins returning errors due to a schema change or dependency update, the failure surfaces only when an agent encounters it during task execution.

### Target state

The task_status_hook PostToolUse handler logs tool call outcomes (tool name, success/failure, error type) to a structured log. A periodic check (or pre-execution check) reads the log and flags tools with success rates below a configurable threshold, warning the orchestrator before dispatching tasks that depend on degraded tools.

### Measurable signal

File `~/.dh/projects/{slug}/metrics/tool-health.jsonl` exists with entries containing `tool_name`, `success`, `error_type`, `timestamp`. A command `uv run sam tool-health` outputs a table of tool success rates.

---

## Improvement 5: Hybrid Skill Discovery with Ranking

**Source pattern**: "SkillRegistry: Discovery and ranking of skills using BM25 + embedding pre-filter and LLM-based selection" and "Smart Discovery: Auto-imports relevant skills based on BM25 + embedding ranking and LLM filtering" (Technical Architecture, Key Features Section 3)
**Local system**: `plugins/plugin-creator/skills/skill-creator/SKILL.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: Claude Code's skill discovery is handled by the platform itself -- skills are loaded based on frontmatter `description` keyword matching and user invocation. The platform's skill selection mechanism is not exposed for customization. OpenSpace's hybrid ranking applies to a much larger skill pool (community-shared skills) where discovery is a real problem. With the local repo's ~50-100 skills, platform-native discovery may be sufficient. Would need evidence that skill selection failures are occurring before this pattern adds value.

### Current state

Skill discovery relies on Claude Code platform-native matching: frontmatter `description` fields are matched against user queries. There is no BM25 or embedding-based ranking. The `/plugin-creator:skill-creator` skill lists existing skills via directory listing but does not rank them by relevance to a given task.

### Target state

Not clearly defined -- the platform controls skill discovery. If a custom discovery layer were added, it would need to sit between the user's request and skill loading, which is not an extension point available in the current plugin architecture.

### Measurable signal

N/A -- this improvement is blocked by the platform architecture. No local extension point exists for skill discovery ranking.

---

## Improvement 6: Anti-Loop Guards for Recursive Quality Gates

**Source pattern**: "Anti-loop guards prevent runaway evolution cycles" and "Confirmation gates reduce false-positive triggers" (Intelligent Evolution Safety section)
**Local system**: `plugins/development-harness/skills/complete-implementation/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: Backlog item not created -- backlog MCP tools unavailable in this session. **Should be created as P1** with title: "Add anti-loop guard to complete-implementation recursive follow-up handling"

### Current state

`complete-implementation/SKILL.md` (line 19) states: "If follow-up task files are created, route them to backlog items first, then recurse only when the follow-up matches the current scope and priority (see Recursive Follow-up Handling section)." The recursion guard is textual guidance in the skill prompt -- it relies on the agent correctly interpreting "matches the current scope and priority." There is no programmatic guard that limits recursion depth or detects cycles (e.g., the same follow-up being generated repeatedly). If a quality gate consistently identifies the same issue and generates the same follow-up, the system could loop indefinitely.

### Target state

The complete-implementation skill includes a concrete recursion guard: (1) a maximum recursion depth parameter (e.g., `max_recursion_depth: 2` in the plan frontmatter, defaulting to 2), (2) a cycle detection check that compares follow-up task titles against previously generated follow-ups in the same session and rejects duplicates, (3) a hard stop that reports BLOCKED when depth is exceeded rather than silently continuing. The guard is implemented in the plan YAML schema (`sam_schema`) as a `recursion_depth` counter incremented by `sam_update` on each recursive invocation.

### Measurable signal

`sam_schema` models include a `recursion_depth` field. Running `/complete-implementation` on a plan that generates identical follow-ups twice results in a BLOCKED status with message "Recursion depth exceeded" rather than infinite recursion. The `recursion_depth` field in the plan YAML shows the current depth value.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Skill Health Metrics Tracking | Medium | Local "skills" are prompt instructions, not executable procedures -- mapping OpenSpace's metrics model requires verifying that skill usage frequency and outcome correlation are meaningful for prompt-based skills |
| Post-Execution Skill Evolution Suggestions | Medium | The mechanism for "evolving" a prompt-based skill differs fundamentally from patching executable code -- would need a prototype to confirm value |
| Skill Version Lineage DAG | Low | Git already provides version history; unclear whether a separate lineage system adds value over existing git workflows |
| Cascade Quality Monitoring for Tool Degradation | Low | Local tools are platform-provided or CI-tested MCP servers; degradation detection may not address a real problem in this environment |
| Hybrid Skill Discovery with Ranking | Low | Platform controls skill discovery; no extension point exists for custom ranking in the current Claude Code plugin architecture |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Collective Agent Intelligence / Cloud Skill Sharing | Requires external cloud infrastructure (open-space.cloud); incompatible with local repo architecture; would require building/integrating a skill registry service, which is beyond extending existing systems |
