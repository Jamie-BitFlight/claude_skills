# Improvement Proposals: Meta-Harness

**Research entry**: ./research/ai-research-tools/meta-harness.md
**Generated**: 2026-04-06
**Patterns assessed**: 8
**Backlog items created**: 0 (backlog MCP unavailable during extraction — items listed for manual creation)
**Deferred (low confidence)**: 5
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: Filesystem-based optimization history for kaizen improvement loop

**Source pattern**: "Agentic Proposer: An LLM agent that generates candidate harness modifications by accessing 'the source code, scores, and execution traces of all prior candidates through a filesystem.'" (Key Features > Optimization Framework)
**Local system**: `plugins/agentskill-kaizen/skills/kaizen-improvement/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the kaizen-improvement skill reads analysis findings from `.planning/kaizen/` but the research entry's specific mechanism (filesystem-based history of all prior optimization candidates with scores) would require verifying whether kaizen currently retains candidate history across sessions or only operates on the latest analysis findings.

### Current state

The kaizen-improvement skill reads findings from `.planning/kaizen/` (analysis output from transcript-analysis), scores them by frequency x impact, and generates improvement proposals. However, it operates on the current session's findings only. There is no structured filesystem store that accumulates: (a) all prior improvement candidates proposed, (b) their measured effectiveness after deployment, (c) execution traces showing the before/after behavior. Each kaizen cycle starts fresh from transcript analysis without access to the history of what was already tried. File: `plugins/agentskill-kaizen/skills/kaizen-improvement/SKILL.md`, lines 28-47 (workflow diagram shows a linear flow from findings to proposals with no feedback from prior candidates).

### Target state

A `.planning/kaizen/candidates/` directory structure that persists: each proposed improvement as a dated file containing the proposal, the measured outcome (if deployed), and a link to the execution trace that motivated it. The kaizen-improvement skill's proposer step reads this history before generating new proposals, enabling it to avoid re-proposing failed improvements and to build on partially successful ones.

### Measurable signal

Directory `.planning/kaizen/candidates/` exists and contains at least one structured candidate file with fields: `proposal`, `deployed_date`, `measured_outcome`, `source_trace`. The kaizen-improvement SKILL.md workflow includes a "Read prior candidates" step before the scoring step.

---

## Improvement 2: Execution trace recording beyond LastActivity timestamps

**Source pattern**: "Execution Traces: Detailed logs of how prior candidates performed during inference and evaluation, including intermediate states and model outputs" (Technical Architecture > Agentic Proposer Design)
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: task_status_hook.py writes LastActivity timestamps on every tool call (confirmed in lines 11-16), and the transcript-analysis skill can query full JSONL session logs via DuckDB. The gap may already be partially addressed by the existing JSONL session log infrastructure — would need to verify whether the kaizen system actually uses execution traces from JSONL when proposing improvements (not just aggregate signal counts).

### Current state

The task_status_hook.py updates a `LastActivity` timestamp on every Write/Edit/Bash tool call (PostToolUse hook) and marks tasks COMPLETE on SubagentStop. This provides status tracking but not execution traces — it records "when" but not "what happened in detail." Full session JSONL logs exist at `~/.claude/projects/` and are queryable via the transcript-analysis skill's DuckDB integration, but these traces are not linked to specific improvement proposals or used as feedback for the kaizen improvement loop.

### Target state

When the kaizen-improvement skill generates improvement proposals, it includes a reference to the specific execution trace (session ID + line range in JSONL) that motivated each proposal. When measuring improvement effectiveness, it links to the post-deployment trace showing the changed behavior. This creates a closed loop: trace -> proposal -> deployment -> trace -> evaluation.

### Measurable signal

Kaizen improvement proposal files in `.planning/kaizen/improvements/` include a `source_trace` field containing session ID and JSONL line range. At least one proposal file contains both `source_trace` (pre-improvement) and `validation_trace` (post-improvement) fields.

---

## Improvement 3: Domain-specific skill prompt variants based on task type

**Source pattern**: "The finding that different optimal harnesses exist for classification, reasoning, and coding tasks suggests Claude Code skills should be optimized per-domain rather than using a universal approach." (Patterns Worth Adopting)
**Local system**: `plugins/development-harness/skills/context-integration/SKILL.md`, `plugins/development-harness/skills/start-task/SKILL.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: the local system already implements domain-specific behavior through the Voltron composition model (language plugins provide specialist agents, quality gates, and optionally custom flows — see development-harness CLAUDE.md "Composition Model" section). The research entry's pattern of different optimal harnesses per task domain is already addressed architecturally by the role resolution and language manifest system.

### Current state

The development harness already resolves domain-specific behavior through language manifests. Different language plugins (Python, TypeScript, Rust) provide different specialist agents and quality gates. The `agent:` field in SAM task YAML selects the specialist profile loaded by task-worker. This is a form of domain-specific harness variation.

### Target state

Not applicable — the existing architecture already addresses this pattern through the Voltron composition model. A potential extension would be task-type-specific prompt variants within a single language plugin (e.g., different prompts for "add feature" vs "fix bug" vs "refactor" tasks), but this is speculative and not directly supported by the research entry's evidence.

### Measurable signal

N/A — already covered by existing architecture.

---

## Improvement 4: Token efficiency measurement for skill prompts

**Source pattern**: "The 4x token reduction demonstrates that optimization can improve both performance AND efficiency simultaneously." (Patterns Worth Adopting > Token Efficiency as a First-Class Objective)
**Local system**: `.claude/CLAUDE.md` (No Invented Limits section), `plugins/agentskill-kaizen/skills/transcript-analysis/SKILL.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the transcript-analysis skill can query token usage from JSONL session logs via DuckDB, but it is unclear whether any existing analysis dimension specifically measures skill prompt token consumption as a metric for optimization. The "No Invented Limits" rule in CLAUDE.md focuses on not truncating content, which is philosophically opposite to token reduction — the two are not contradictory but the interaction needs careful examination.

### Current state

The transcript-analysis skill has 10 analysis dimensions (tool misuse, repeated errors, etc.) but none specifically measure token efficiency of skill prompts or context loading. The JSONL session logs contain token counts per turn, but no kaizen analysis dimension aggregates "tokens consumed by skill/reference loading" vs "tokens consumed by actual work." There is no mechanism to compare two versions of a SKILL.md on token efficiency while holding task performance constant.

### Target state

The transcript-analysis skill includes an 11th analysis dimension: "Prompt Token Efficiency" — measuring tokens consumed by skill loading, reference file loading, and context management relative to useful work output (tool calls producing artifacts). The kaizen-improvement skill uses this dimension to flag skills where token consumption is disproportionate to output.

### Measurable signal

Transcript-analysis SKILL.md Signal Catalog includes a "Prompt Token Efficiency" section. A DuckDB query in the extraction patterns can compute `tokens_context_loading / tokens_productive_output` ratio for a session. At least one kaizen analysis report includes this metric.

---

## Improvement 5: Automated skill prompt refinement based on effectiveness metrics

**Source pattern**: "Skill Prompt Optimization: Implement a Meta-Harness-style system to automatically refine SKILL.md prompts and reference documentation based on observed skill effectiveness metrics." (Integration Opportunities)
**Local system**: `plugins/agentskill-kaizen/skills/kaizen-improvement/SKILL.md`
**Confidence**: Low
**Impact**: High
**Backlog**: Deferred — confidence low: the kaizen-improvement skill already generates "skill patches" (improvement type 3) and delegates to `/plugin-creator:skill-creator` for implementation. However, the research entry describes an automated closed-loop system where the proposer iteratively refines prompts based on measured performance — the local system requires human review between cycles (draft mode is default, install mode is hooks-only). The gap is real but implementing a fully automated prompt refinement loop would require significant new infrastructure (automated evaluation, candidate management, rollback) that goes beyond extending the existing system.

### Current state

Kaizen-improvement generates skill patch proposals as markdown files in `.planning/kaizen/improvements/`. These are delegation prompts for specialist agents, requiring human review before application (draft mode is default per SKILL.md line 64-65). There is no automated cycle of: propose SKILL.md change -> deploy -> measure effectiveness -> propose next change.

### Target state

A `/kaizen:auto-refine` mode where the kaizen system: (1) proposes a SKILL.md modification, (2) applies it in a test branch, (3) runs a defined evaluation task using the modified skill, (4) measures effectiveness via transcript analysis, (5) accepts or reverts based on measured improvement. This would implement the Meta-Harness outer-loop pattern for skill prompt optimization.

### Measurable signal

A skill or command exists that accepts a SKILL.md path and an evaluation task, runs the propose-apply-evaluate-measure cycle, and produces a report comparing before/after token usage and task success rate. At least one SKILL.md has been refined through this automated process with measured improvement recorded.

---

## Improvement 6: Structured evaluation harness for agent performance benchmarking

**Source pattern**: "Agent Evaluation Harness: Use the framework to discover optimal harnesses for evaluating agent performance on tasks, replacing current manual benchmark definitions." (Integration Opportunities)
**Local system**: `plugins/development-harness/skills/complete-implementation/SKILL.md`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence low: the complete-implementation skill runs quality gates (code review, feature verification, integration check, documentation drift audit) but these are pass/fail gates, not performance benchmarks. The research entry proposes discovering optimal evaluation harnesses through search — the local system uses manually defined quality gates. However, the gap requires inference: it is unclear whether the manually defined gates are suboptimal or whether automated discovery would produce materially better evaluation criteria for this codebase.

### Current state

Complete-implementation runs a fixed set of quality gates: code review, feature verification, integration check, doc drift audit, context refinement. These are manually defined in the SKILL.md and run sequentially. There is no mechanism to compare different evaluation configurations or to discover which combination of gates most effectively catches real defects.

### Target state

A configurable evaluation harness where different gate combinations and orderings can be tested against historical task completion data. The harness records which gates caught which issues, enabling data-driven selection of the most effective gate configuration per task type.

### Measurable signal

Quality gate execution produces structured output including: gate name, pass/fail, issues found (count and severity), time consumed. Historical gate effectiveness data is stored and queryable. At least one gate configuration change is justified by measured effectiveness data.

---

## Improvement 7: Tool presentation optimization for agent dispatch

**Source pattern**: "Tool Calling Optimization: Apply harness optimization to discover the most effective way to present available tools to Claude Code agents during execution." (Integration Opportunities)
**Local system**: `plugins/agent-orchestration/skills/agent-orchestration/SKILL.md`
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: Claude Code's tool presentation is controlled by the platform (tools are listed based on skill/plugin configuration), not by user-space code. The local system cannot control how tools are ordered or described in the system prompt — this is a platform-level concern. The gap exists but is not addressable within the current architecture without platform changes.

### Current state

Tools available to agents are determined by skill frontmatter (`tools:` field), plugin configuration, and MCP server registration. The order and description of tools in the agent's context is controlled by the Claude Code platform, not by the skill or agent definitions in this repo.

### Target state

Not actionable within current architecture — tool presentation order and format are platform-controlled.

### Measurable signal

N/A — outside local system control.

---

## Improvement 8: Context ordering and selection optimization

**Source pattern**: "Context Management Automation: Auto-tune the order, format, and selection of context (research entries, skill documentation, prior examples) based on downstream task performance." (Integration Opportunities)
**Local system**: `plugins/development-harness/skills/context-integration/SKILL.md`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence low: the context-integration skill (S3) grounds plans in codebase reality through scope analysis, conflict detection, and resource mapping. However, this is a one-time pipeline stage, not an ongoing context selection optimizer. The research entry's pattern of auto-tuning context selection based on downstream performance would require measuring which context elements contributed to task success — infrastructure that does not exist. The gap is real but the path to implementation is speculative.

### Current state

Context-integration (S3) performs scope analysis, conflict detection, and resource mapping as a pipeline stage. Context is assembled based on the plan's requirements, not optimized based on historical effectiveness. CLAUDE.md rules load based on file changes (system-reminder mechanism), not based on measured downstream impact.

### Target state

A context selection system that tracks which context elements (skill references, CLAUDE.md rules, research entries) were loaded for each task and correlates context composition with task outcome (success, failure, token usage). Over time, this enables data-driven context selection: for a given task type, load the context elements historically correlated with success.

### Measurable signal

A log or database records: session ID, loaded context elements (file paths), task outcome, token usage. A query can answer "which CLAUDE.md rules were loaded in sessions where task X succeeded vs failed."

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Filesystem-based optimization history for kaizen | Medium | Need to verify whether kaizen retains candidate history across sessions or only operates on latest findings |
| Execution trace recording beyond LastActivity | Medium | Need to verify whether kaizen already uses JSONL execution traces when proposing improvements |
| Token efficiency measurement for skill prompts | Medium | Need to verify interaction between "No Invented Limits" rule and token efficiency optimization |
| Automated skill prompt refinement | Low | Requires significant new infrastructure (automated evaluation, candidate management, rollback) beyond extending existing system |
| Structured evaluation harness for benchmarking | Low | Unclear whether automated gate discovery would produce materially better results than manually defined gates |
| Tool presentation optimization | Low | Tool presentation order is platform-controlled, not addressable in user-space |
| Context ordering and selection optimization | Low | No infrastructure exists to correlate context composition with task outcome |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Domain-Specific Harness Variants | Already covered by Voltron composition model in development-harness (language manifests, role resolution, specialist agents per language/domain) |
