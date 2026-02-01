---
last-updated: 2026-02-01
p0-count: 0
p1-count: 7
p2-count: 9
ideas-count: 6
---

# Backlog

Tracked features, ideas, and deferred work for grooming and future sessions.

---

## P0 - Must Have

_(Empty)_

---

## P1 - Should Have

### Create ecosystem-researcher agent

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Added**: 2026-02-01
**Description**: New agent for ecosystem/domain research before roadmap creation. Supports three modes - Ecosystem discovery, Feasibility assessment, Comparison analysis.
**Patterns from**: gsd-project-researcher.md (research modes)
**Suggested location**: `plugins/python3-development/agents/ecosystem-researcher.md`

### SAM: Error Recovery / Rollback Procedures

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define explicit procedure when a task fails irrecoverably. How to undo artifact changes? How to restore artifact plane to consistent state after failure?
**Research first**: How do GSD, BMAD-METHOD, AutoGPT, and traditional CI/CD handle rollback? What patterns exist for transactional artifact updates?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (new Appendix or Part 6 addition)

### SAM: Human Escalation Criteria

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define explicit triggers for escalating to human at each stage (not just Discovery). When should agents block and ask vs attempt repair vs fail?
**Research first**: How do GSD deviation rules work? How does BMAD-METHOD handle human checkpoints? What escalation patterns exist in agent frameworks?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (each Agent Specification section)

### SAM: Timeout/Stall Detection

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define mechanism to detect when an agent is stuck or has stalled. Include timeout thresholds per stage, health check patterns, and recovery actions.
**Research first**: How do orchestration frameworks (Temporal, Prefect, Airflow) handle task timeouts? What heartbeat patterns exist? How does Gas Town handle session recycling?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (Orchestrator section 3.8)

### SAM: Artifact Schema Validation

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define formal validation rules or JSON schemas for artifact formats. Currently only templates provided. Enable automated validation at stage boundaries.
**Research first**: How do GSD artifacts (STATE.md, ROADMAP.md) enforce structure? What validation approaches exist in BMAD-METHOD? JSON Schema vs YAML validation vs custom parsers?
**Suggested location**: `methodology_development/sam-artifact-schemas/` (new directory with schema files)

### SAM: Scope Creep Detection

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define mechanism to detect when execution diverges from plan. How does Forensic Review detect that the execution agent solved a different problem than planned?
**Research first**: How does GSD plan-checker detect deviation? What diff/comparison techniques exist? How do code review tools detect scope creep in PRs?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (section 3.6 Forensic Review)

### Extract claude-plugin-lint to standalone PyPI package

**Source**: Gap analysis - no existing Claude Code plugin linters exist
**Added**: 2026-02-01
**Description**: Extract and enhance `validate_frontmatter.py` into a standalone open-source project. First dedicated linter for Claude Code plugin frontmatter (SKILL.md, agents/*.md, commands/*.md). Official `claude plugin validate` only checks plugin.json structure.
**Features to include**:
- YAML frontmatter schema validation with Pydantic models
- Auto-fix capabilities (arrays → comma-separated, multiline → single-line)
- Token-based complexity metrics (tiktoken) instead of line counts
- Cross-reference validation (agent references non-existent skill)
- Marketplace readiness scoring
- Pre-commit hook integration
- CLI with `--fix` and `--report` modes
**Current source**: `plugins/plugin-creator/scripts/validate_frontmatter.py`
**Suggested repo name**: `claude-plugin-lint` or `cc-plugin-validator`

---

## P2 - Could Have

### Enhance swarm-task-planner with multi-source synthesis

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Added**: 2026-02-01
**Description**: Add pattern for synthesizing outputs from multiple parallel research agents into unified summary documents.
**Patterns from**: gsd-research-synthesizer.md
**Suggested location**: `plugins/python3-development/agents/swarm-task-planner.md`

### Add context compliance checking

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Added**: 2026-02-01
**Description**: Verify plans comply with user decisions (Decisions/Discretion/Deferred format). Requires adopting GSD CONTEXT.md artifact format.
**Patterns from**: gsd-plan-checker.md (context compliance dimension)
**Suggested location**: `plugins/python3-development/agents/plan-validator.md` or new CONTEXT.md format

### SAM: Artifact Versioning Strategy

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define versioning strategy for artifacts. How to track artifact evolution? How to reference specific versions? Git-based vs embedded version fields?
**Research first**: How do GSD STATE.md and CONTEXT.md handle versioning? How does git-based versioning work in document-heavy workflows? What patterns exist in event sourcing?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (section 2.1.2)

### SAM: Parallel Execution Details

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Detail safe parallelization within SAM pipeline. When can tasks run in parallel? How to handle merge conflicts? Reference GSD wave execution pattern.
**Research first**: How does GSD wave execution work in detail? How do task orchestrators (Temporal, Prefect) handle parallel dependencies? What conflict resolution patterns exist?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (new section 2.4 or Appendix)

### SAM: Multi-Model Strategy

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define guidance for using different models for different agent types. E.g., cheaper/faster models for simple verification, stronger models for planning.
**Research first**: How do agent frameworks handle model selection? What cost/quality tradeoffs exist? How does Claude Code's haiku/sonnet/opus selection work?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (Implementation Roadmap or new Appendix)

### SAM: Audit Trail / Observability

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Beyond artifacts, define logging/metrics/tracing guidance. How to diagnose pipeline issues? What telemetry to capture?
**Research first**: How do GSD and BMAD-METHOD handle logging? What observability patterns exist in agent frameworks? OpenTelemetry for LLM workflows?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (new Appendix I)

### SAM: Partial Success Handling

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define how to represent and handle partial task success. Task completes some DoD items but not all. How is this state represented in artifacts?
**Research first**: How do GSD checkpoints represent partial progress? How do CI/CD systems handle partial test passes? What state machine patterns exist?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (section 3.5 Execution Agent output)

### SAM: Context Size Management

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define explicit guidance for measuring and managing context size per agent. What's the target token budget? How to detect context pressure?
**Research first**: How do agent frameworks measure context usage? What token counting approaches exist? How does Claude Code handle context limits internally?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (section 2.1 or Appendix C)

### SAM: Conflicting Review Findings

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Define protocol when forensic review and self-verification disagree. Which takes precedence? How to adjudicate conflicts?
**Research first**: How do code review systems handle conflicting reviewers? What adjudication patterns exist in multi-agent systems? How does GSD handle verification disagreements?
**Suggested location**: `methodology_development/stateless-software-engineering-framework.md` (section 3.6 Forensic Review)

---

## Ideas

### SAM: Cost/Token Management

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Explore token budgets and cost controls per agent/stage. Track API costs. Set limits per task.
**Research first**: How do LLM cost management tools work (LangSmith, Helicone)? What budget enforcement patterns exist?

### SAM: Team Coordination Protocols

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Explore how multiple humans interact with the pipeline concurrently. Locking? Ownership? Notifications?
**Research first**: How do collaborative editing systems handle concurrent users? What patterns exist in git-based workflows?

### SAM: External System Integration Patterns

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Explore patterns for integrating with issue trackers (GitHub Issues, Jira), CI/CD pipelines, git hooks.
**Research first**: How does GSD integrate with external tools? What MCP servers exist for issue trackers? How do agent frameworks bridge to CI/CD?

### SAM: Migration Strategy Guide

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Explore how to migrate existing projects to SAM. Incremental adoption? Parallel running? Artifact bootstrap?
**Research first**: How do organizations adopt new methodologies incrementally? What migration patterns exist for process changes?

### SAM: Training/Onboarding Materials

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Explore creating materials for new team members learning the methodology. Tutorials, examples, quick-start guides.
**Research first**: What training materials exist for GSD, BMAD-METHOD? What makes effective agent methodology onboarding?

### SAM: Non-Code Workflow Guidance

**Source**: Gap analysis of SAM framework
**Added**: 2026-02-01
**Description**: Explore how SAM handles documentation-only tasks, configuration changes, infrastructure work. Adapt templates?
**Research first**: How do GSD and BMAD-METHOD handle non-code work? What artifact types exist beyond code?

---

## Completed

_(Move items here when done, with completion date)_

---

## Format Guide

```markdown
### Item title

**Source**: [link or description of where this came from]
**Added**: YYYY-MM-DD
**Description**: What needs to be done
**Research first**: (for SAM items) Questions to answer via competitive analysis before implementing
**Patterns from**: (optional) External source if from pattern integration
**Suggested location**: (optional) Where this should be implemented
```

### Research Resources

**Skill for research phase**: `/research-and-compare <methodology-name-or-url>`

- Produces structured comparison documents following SAM comparison template
- Includes overlap/divergence analysis, weakness discovery, implementation pairing
- Outputs to `methodology_development/.meta/v1_comparisons/`

**Existing SAM comparisons** (start here before running new research):

- [methodology_development/.meta/v1_comparisons/](../methodology_development/.meta/v1_comparisons/)
  - sam-vs-get-shit-done.md
  - sam-vs-bmad-method.md
  - sam-vs-gastown.md
  - sam-vs-taskmaster.md
  - sam-vs-octocode.md
  - sam-vs-superclaude.md
  - sam-vs-ralph-loop-orchestrator.md
  - sam-vs-cc-sessions.md
  - sam-vs-v-model.md
  - sam-infrastructure-layer.md

**Workflow for SAM gap items**:

1. Check existing comparisons for relevant findings
2. If more research needed: `/research-and-compare <framework>` for specific topics
3. Synthesize findings into SAM framework update
4. Mark backlog item complete
