---
last-updated: 2026-02-06
p0-count: 0
p1-count: 6
p2-count: 6
ideas-count: 10
---

# Backlog

Tracked features, ideas, and deferred work for grooming and future sessions.

---

## P0 - Must Have

_(Empty)_

---

## P1 - Should Have

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

### Carbonyl Browser Integration for Claude Code

**Source**: Session experimentation 2026-02-05
**Added**: 2026-02-05
**Description**: Research whether carbonyl (terminal Chromium browser) can work with Claude Code for reliable web content extraction. Carbonyl renders pages in terminal but needs a TTY.
**Research areas**:
- Can carbonyl run via tmux/screen/script to provide a pseudo-TTY?
- Could carbonyl be wrapped with a screenshot tool (e.g., termshot, asciinema) that passes images back to Claude?
- What's the minimal TTY setup needed for headless carbonyl operation?
- Compare with is-fast, lynx, w3m for text extraction capabilities
**Context**: WebFetch is unreliable (summarizing agents hallucinate), Playwright requires browser downloads that may be blocked. Carbonyl is self-contained but needs TTY.

### Validate is-fast for Web Content Extraction

**Source**: Session experimentation 2026-02-05
**Added**: 2026-02-05
**Description**: Test is-fast CLI tool on host with unrestricted network access.
**Validation steps**:
- Install: `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/Magic-JD/is-fast/releases/latest/download/is-fast-installer.sh | sh`
- Test: `is-fast --direct https://code.claude.com/docs/en/skills --piped`
- Verify it extracts text content from JS-rendered pages
- Compare output quality with curl, lynx, w3m
- Test CSS selector filtering with `--selector`
**Blocked on 2026-02-05**: DNS resolution failed in restricted environment

### Validate agent-browser for Web Automation

**Source**: Session experimentation 2026-02-05
**Added**: 2026-02-05
**Description**: Test agent-browser (Playwright-based) on host with unrestricted network and Playwright browsers installed.
**Validation steps**:
- Install browsers: `npx playwright install`
- Test: `npx agent-browser open https://code.claude.com/docs/en/skills`
- Test: `npx agent-browser snapshot -i` (get element refs)
- Test: `npx agent-browser get text body` (extract page text)
- Verify snapshot/interact/re-snapshot workflow works
- Document prerequisites for skill to function
**Blocked on 2026-02-05**: Could not download Playwright browsers (DNS resolution failed, missing system libs)
**Skill location**: `.claude/skills/agent-browser/SKILL.md`

### Validate carbonyl Terminal Browser

**Source**: Session experimentation 2026-02-05
**Added**: 2026-02-05
**Description**: Test carbonyl on host with proper TTY and network access.
**Validation steps**:
- Test basic: `npx -y carbonyl --no-sandbox https://example.com`
- Test with tmux: `tmux new-session -d -s carbonyl 'npx -y carbonyl --no-sandbox https://example.com'`
- Test screenshot capture: Can we grab terminal output as image?
- Test text extraction: Can we pipe output or capture rendered text?
- Compare JS rendering quality with other tools
**Blocked on 2026-02-05**: Needs TTY (Inappropriate ioctl for device), DNS also blocked

---

## Completed

### Replace requests with httpx in all scripts

**Source**: CI/pre-commit inconsistency discovery (2026-02-05)
**Completed**: 2026-02-06
**Description**: Migrated `validate-glfm.py` from `requests` to `httpx`. Added TID251 ruff ban rule for `requests` imports. Removed `types-requests` from dev dependencies. `sync-gitlab-docs.py` was already using httpx.
**Location**: `plugins/gitlab-skill/skills/gitlab-skill/scripts/validate-glfm.py`, `pyproject.toml`

### Enhance swarm-task-planner with multi-source synthesis

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Completed**: 2026-02-06
**Description**: Multi-source synthesis implemented via CLEAR+CoVe standard and Project Awareness section with investigation commands for searching documentation, assessing project structure, and identifying progress.
**Location**: `plugins/python3-development/agents/swarm-task-planner.md`

### Add context compliance checking

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Completed**: 2026-02-06
**Description**: Complete plan-validator agent implements 8 validation dimensions including Requirement Coverage, Task Completeness, Dependency Correctness, Agent Capability Match, Input/Output Validity, Artifact Wiring, Testability, and Scope Sanity.
**Location**: `plugins/python3-development/agents/plan-validator.md`

### SAM: Artifact Versioning Strategy

**Source**: Gap analysis of SAM framework
**Completed**: 2026-02-06
**Description**: Implemented storage-agnostic semantic tokens using pattern `ARTIFACT:{TYPE}({SCOPE_OR_ID})` with disambiguators (CTX, PREREQ, EXEC, VERIFY). Provides both filesystem-backed and SQL-backed example implementations.
**Location**: `methodology_development/stateless-software-engineering-framework.md` (section 2.1.2)

### Create ecosystem-researcher agent

**Source**: [external-pattern-integration-2026-02-01.md](.claude/external-pattern-integration-2026-02-01.md)
**Completed**: 2026-02-05
**Description**: New agent for ecosystem/domain research before roadmap creation. Supports three modes - Ecosystem discovery, Feasibility assessment, Comparison analysis.
**Patterns from**: gsd-project-researcher.md (research modes)
**Location**: `plugins/python3-development/agents/ecosystem-researcher.md`

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
