# Improvement Proposals: Empirica

**Research entry**: ./research/agent-infrastructure/empirica.md
**Generated**: 2026-04-05
**Patterns assessed**: 6
**Backlog items created**: 1 (issues: #1572)
**Deferred (low confidence)**: 4
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: Structured epistemic artifact logging per task (findings, unknowns, dead-ends)

**Source pattern**: "Artifact types (logged separately): Finding (verified fact, source, confidence), Unknown (unanswered question, why it matters), Dead-End (tried approach, outcome, what was learned), Decision (choice made, rationale, alternatives considered), Assumption (unstated premise, risk level)" — Data Model section, lines 252-258
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`, `plugins/development-harness/skills/complete-implementation/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1572 created

### Current state

`task_status_hook.py` records task status transitions (not-started, in-progress, complete) and timestamps (Started, LastActivity, Completed). `complete-implementation/SKILL.md` runs quality gates (code review, test verification, acceptance check) and records pass/fail outcomes. Neither system captures structured epistemic artifacts — what was learned during implementation, what questions remained unanswered, what approaches were tried and abandoned, what assumptions were made, or what decisions were taken with their rationale.

When a task fails or produces unexpected results, the only audit trail is the session transcript (analyzed post-hoc via kaizen). There is no structured, queryable record of what the agent knew, did not know, or tried and rejected during task execution.

### Target state

The SAM task model (`sam_schema/core/models.py`) includes optional structured artifact fields on each task record:

- `findings`: list of `{fact, source, confidence}` dicts logged during implementation
- `unknowns`: list of `{question, impact}` dicts for unanswered questions at task completion
- `dead_ends`: list of `{approach, outcome, lesson}` dicts for abandoned approaches
- `decisions`: list of `{choice, rationale, alternatives}` dicts for implementation decisions

The `start-task` skill instructs agents to log artifacts via `sam_update` as they work. The `complete-implementation` skill summarizes artifacts in quality gate output. Artifacts persist in the SAM task YAML and are queryable via `sam_read`.

### Measurable signal

Run `mcp__plugin_dh_sam__sam_read(plan="P{N}", task="T{M}")` on a completed task. The response JSON includes non-empty `findings`, `unknowns`, `dead_ends`, or `decisions` arrays. At least one artifact type is populated for tasks that involved investigation or debugging.

---

## Improvement 2: Investigation-phase tool gating before task implementation

**Source pattern**: "The Sentinel is a governance layer that controls the transition between investigation (noetic) and action (praxic) phases. Before the AI is permitted to edit code, it must demonstrate understanding through the Sentinel gate." — Key Features section 1, lines 57-65
**Local system**: `plugins/development-harness/skills/work-backlog-item/SKILL.md`, `.claude/CLAUDE.md` (Debugging Protocol Planning Gate)
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred — confidence medium: the local system has prompt-based gating (CLAUDE.md Planning Gate checklist, work-backlog-item phase separation) which serves a similar purpose. Whether the tool-blocking mechanism would provide materially better outcomes than the existing prompt-based approach requires operational testing to confirm. The existing `start-task` skill already separates claim/read phases from implementation, and the SAM pipeline enforces S1 Discovery before S5 Execution.

### Current state

The CLAUDE.md "Debugging Protocol — Planning Gate" is a checklist the agent must answer before writing code, but it is not enforced by any hook or tool restriction — the agent can skip it. The `work-backlog-item` skill separates Locate/Groom/Plan phases, and the SAM pipeline enforces S1-S4 before S5, but within task execution (`start-task`), there is no mechanism that blocks Write/Edit tools until the agent has demonstrated understanding of the task's codebase context.

### Target state

A PreToolUse hook (or start-task workflow step) that blocks Write/Edit tool calls during an initial investigation phase of each task. The agent must explicitly signal readiness (e.g., via a structured output or tool call) before modification tools are permitted. The gate is configurable per-task via a frontmatter field (e.g., `investigation_required: true`).

### Measurable signal

A PreToolUse hook exists that returns `{"decision": "block"}` for Write/Edit tools when the active task's investigation phase has not been completed. The hook reads from the active-task context file to determine phase state.

---

## Improvement 3: Workflow pattern outcome correlation in kaizen

**Source pattern**: "Sequential pattern analysis (PrefixSpan algorithm) identifies repeated tool call sequences. Each pattern is ranked by: Frequency, Success rate (what % of transactions using this pattern complete), Learning delta" — Key Features section 7, lines 152-161
**Local system**: `plugins/agentskill-kaizen/skills/transcript-analysis/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: kaizen already performs tool sequence mining via `find_frequent_patterns` and DuckDB queries over transcripts. The gap is that kaizen does not currently correlate discovered patterns with task-level outcomes (success/failure). Confirming this requires examining the kaizen MCP tools' output schemas to verify outcome data is truly absent vs available but not surfaced. The research entry's "success rate" metric also depends on having structured outcome data per transaction, which the local system only partially provides via SAM task status.

### Current state

The kaizen `transcript-analysis` skill mines tool sequences from JSONL transcripts using `find_frequent_patterns` (MCP tool). It reports pattern frequency and supports DuckDB SQL queries over transcript data. However, patterns are ranked by frequency only — there is no correlation between a tool sequence pattern and the outcome of the task or session where it appeared. The kaizen system cannot answer "which investigation patterns lead to successful implementations?"

### Target state

Kaizen's pattern mining output includes a `success_rate` field per pattern, computed by joining tool sequence occurrences with SAM task outcomes (complete/failed/blocked status from `sam_status`). A new kaizen MCP tool or DuckDB view (`workflow_pattern_outcomes`) correlates session IDs from transcripts with plan/task status from SAM data.

### Measurable signal

`mcp__plugin_agentskill-kaizen_kaizen-analysis__find_frequent_patterns` output includes a `success_rate` field (float, 0-1) for each pattern. Or: a DuckDB query `SELECT pattern, success_rate FROM workflow_pattern_outcomes ORDER BY success_rate DESC` returns results.

---

## Improvement 4: Auto-curated memory index ranked by confidence

**Source pattern**: "MEMORY.md is automatically maintained at ~200 lines, ranking findings by epistemic confidence. This hot cache prevents context bloat while preserving critical learnings." — Key Features section 4, lines 117-118
**Local system**: `.claude/CLAUDE.md`, user MEMORY.md at `~/.claude/projects/-home-user-repos-claude-skills/memory/MEMORY.md`
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred — confidence medium: the local MEMORY.md is a manually curated index of memory files organized by topic. Whether auto-curation ranked by confidence would produce better outcomes than the current topic-organized manual approach requires testing. The local system's architecture (separate `.md` files per memory item linked from an index) is fundamentally different from Empirica's single ranked file, and the local approach has the advantage of granular file-level updates without rewriting the entire index.

### Current state

The project MEMORY.md at `~/.claude/projects/.../memory/MEMORY.md` is a manually maintained index of topic-organized memory files. Each entry links to a separate `.md` file. Entries are organized by domain (user preferences, completion standards, plugin patterns, etc.) with no ranking by confidence or recency. All entries are treated as equally important. New entries are appended manually during sessions.

### Target state

A SessionEnd hook or periodic process that re-ranks memory entries by a confidence score (derived from how recently the memory was validated, how many sessions have relied on it, and whether it has been contradicted). The top N entries by confidence score appear first in MEMORY.md. Low-confidence or stale entries are moved to an archive section.

### Measurable signal

MEMORY.md entries include a `confidence: high|medium|low` annotation or are sorted by a computed score. A hook or script exists that updates the ranking on session end.

---

## Improvement 5: Pre/post task confidence delta measurement

**Source pattern**: "POSTFLIGHT: Learning measurement. After completing work, AI measures what it learned — computing a delta between preflight and postflight vectors. This delta persists to memory and feeds calibration." — Key Features section 2, lines 73-74
**Local system**: `plugins/development-harness/skills/complete-implementation/SKILL.md`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence low: the research entry describes a 13-vector measurement system calibrated over 600+ sessions. Implementing a meaningful equivalent requires defining what vectors to measure and how to assess them reliably. The local system might already capture equivalent data implicitly through the T0-baseline and TN-verification gate comparison, which measures observable system state (test counts, lint errors) rather than epistemic state. Whether epistemic self-assessment adds value beyond observable metrics is unverified.

### Current state

The SAM pipeline includes T0-baseline-capture (pre-implementation state) and TN-verification-gate (post-implementation state), but these measure observable system metrics (test pass counts, lint error counts, type checker results) — not the agent's self-assessed understanding or confidence. There is no mechanism for the agent to record "what I knew before" vs "what I learned after" for a task, and no calibration system that compares confidence predictions to outcomes.

### Target state

`start-task` records a structured pre-task assessment (agent's stated confidence, identified unknowns, predicted difficulty). `complete-implementation` or task completion records a post-task assessment (actual difficulty, what was learned, confidence delta). The delta is stored in the SAM task record and available for analysis.

### Measurable signal

`sam_read` output for a completed task includes `preflight_confidence` and `postflight_confidence` float fields, and a `learning_delta` dict showing what changed. At least 10 completed tasks have non-null values in these fields.

---

## Improvement 6: Cross-project solution search

**Source pattern**: "When working on multiple Claude Code projects, --global search surfaces solutions and patterns from prior projects without manual knowledge transfer." — Relevance section, point 6, lines 399
**Local system**: `plugins/development-harness/skills/backlog/SKILL.md`, research directory
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: the local system might have equivalent behavior via research entries (which catalog external solutions) and backlog search (which is project-scoped but could be extended). The gap is inferred — the research system and backlog system are project-scoped by design, but whether cross-project search would provide value depends on the user having multiple active projects, which has not been verified.

### Current state

The backlog MCP server (`backlog_list`, `backlog_view`) searches within a single project's backlog items. The research directory contains entries about external tools but not about solutions implemented in other local projects. There is no mechanism to search across multiple DH project state directories (`~/.dh/projects/*/`) for prior solutions to similar problems.

### Target state

A `backlog_search_global` MCP tool or CLI command that searches across all project state directories under `~/.dh/projects/*/backlog/` for matching items. Results include the project slug and item title/description.

### Measurable signal

`mcp__plugin_dh_backlog__backlog_list` accepts a `global=true` parameter, or a new `backlog_search_global` tool exists. Running it with a search term returns results from multiple projects.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Investigation-phase tool gating (Sentinel Gate) | medium | Local system has prompt-based equivalent (Planning Gate + SAM phase separation). Operational testing needed to confirm tool-blocking provides materially better outcomes. |
| Workflow pattern outcome correlation | medium | Kaizen already mines patterns; need to verify its output schema to confirm outcome data is truly absent vs available but unsurfaced. |
| Auto-curated memory index ranked by confidence | medium | Local architecture (topic-organized separate files) is fundamentally different; need testing to confirm ranked single-file approach is better. |
| Pre/post confidence delta measurement | low | T0/TN baselines already measure observable metrics; whether epistemic self-assessment adds value beyond observable metrics is unverified. |
| Cross-project solution search | low | Value depends on multi-project usage patterns not yet verified; research directory may partially cover this. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Task Decomposition Measurement (measuring epistemic state at decomposition boundaries) | Already covered by RT-ICA gate in `plugins/development-harness/skills/planner-rt-ica/SKILL.md` which gates planning on information completeness analysis. The RT-ICA produces APPROVED/BLOCKED/MISSING verdicts that serve the same gating function at decomposition boundaries. |
