# Improvement Proposals: Arxitect

**Research entry**: ./research/agent-frameworks/arxitect.md
**Generated**: 2026-04-08
**Patterns assessed**: 4
**Backlog items created**: 0 (backlog MCP tools unavailable — GITHUB_TOKEN not set)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Add software design principle dimensions to code-reviewer quality checks

**Source pattern**: "Three Specialized Architecture Reviewers — Assesses naming conventions, method signatures, parameter design, type safety...checks compliance with SOLID principles, identifies DRY violations, evaluates composition vs. inheritance choices...evaluates component cohesion (REP, CRP, CCP), component coupling (ADP, SDP, SAP), and quality attributes including maintainability, extensibility, and testability." (Key Features section, lines 36-45)
**Local system**: plugins/development-harness/agents/code-reviewer.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the local code-reviewer applies 7 universal quality dimensions (security, correctness, test coverage, API contracts, naming/readability, error handling, performance). These dimensions partially overlap with Arxitect's design principles (API contracts covers some of API design review; naming/readability covers some of OO design review). A definitive gap assessment requires reviewing real code-review reports to see whether design principle violations are caught in practice by existing dimensions or fall through the cracks. The code-reviewer agent already includes "Functions have a single clear responsibility" (SRP) and "Public function signatures match what callers expect" (contract compliance), suggesting partial coverage that is not trivially separable from "absent."

### Current state

The `@dh:code-reviewer` agent (plugins/development-harness/agents/code-reviewer.md, Step 5 "Apply Universal Quality Dimensions") checks 7 dimensions: Security, Correctness, Test Coverage, API Contract Compliance, Naming and Readability, Error Handling, and Performance Indicators. These dimensions focus on correctness and operational quality. Explicit software design principles — SOLID compliance as a named check, DRY violation detection, composition vs. inheritance evaluation, component cohesion metrics (REP, CRP, CCP), and component coupling analysis (ADP, SDP, SAP) — are absent as named review dimensions. Some SOLID principles are partially covered by existing checks (SRP under "Naming and Readability", LSP partially under "API Contract Compliance") but not as a systematic evaluation.

### Target state

The code-reviewer agent includes two additional quality dimensions: "Software Design Principles" (covering SOLID, DRY, composition vs. inheritance, pattern applicability) and "Architectural Structure" (covering component cohesion, component coupling, dependency direction). Each dimension has specific check items analogous to the existing 7 dimensions, producing findings with file:line references. Stack-specific code-review skills (e.g., `dh:code-review-python`) may define language-specific design pattern checks.

### Measurable signal

Run `@dh:code-reviewer` on a SAM task. The generated `codebase-analysis` artifact includes a "Software Design Principles" section with at least one finding (blocking or non-blocking) that references a SOLID principle by name (SRP, OCP, LSP, ISP, DIP) or identifies a DRY violation. The output format template in the agent file includes the new dimensions in its structured report.

---

## Improvement 2: Add iterative implement-review feedback loop with finding ID tracking to S6 Forensic Review

**Source pattern**: "The @architect agent orchestrates an iterative implement-review-feedback cycle: 1. Implement — A code implementer writes or modifies code based on design guidelines 2. Review — All three design reviewers evaluate the implementation 3. Iterate — The architect compiles feedback and instructs the implementer to revise code 4. Safety valve — After 3 iterations, if critical findings remain, the architect presents them to the user for decision. Each iteration preserves finding IDs to track fixes and detect regressions." (Key Features section, lines 49-57)
**Local system**: plugins/development-harness/skills/forensic-review/SKILL.md, plugins/development-harness/skills/complete-implementation/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the local system already has a remediation loop in forensic-review (NEEDS_WORK verdict -> extract blocking findings -> create remediation tasks -> re-execute -> re-review). This loop is structurally similar to Arxitect's iterate cycle. The local system does NOT assign finding IDs or track which findings persist across iterations, but it tracks remediation via SAM task state. Whether finding IDs would provide meaningful additional value over the existing SAM-based task tracking requires examining real remediation cycles to see if finding regression (a fixed finding re-appearing) occurs in practice. The safety valve pattern (stop after N iterations) is partially present in the local system through SAM status tracking and manual intervention, but is not a formal mechanism.

### Current state

The forensic-review skill (plugins/development-harness/skills/forensic-review/SKILL.md, "NEEDS_WORK Remediation Loop" section) implements a remediation cycle: NEEDS_WORK verdict -> extract blocking findings from codebase-analysis artifact -> create remediation tasks -> S5 execute -> S6 re-review. Findings are described in prose (file:line references and descriptions) but do not have stable identifiers that persist across iterations. There is no mechanism to detect that a finding from iteration 1 was fixed but then regressed in iteration 2. There is no explicit safety valve that stops the loop after N iterations — the loop continues until PASS or until an orchestrator intervenes.

### Target state

Each finding in the codebase-analysis artifact has a stable identifier (e.g., `F001`, `F002`) assigned by the code-reviewer. When the code-reviewer runs a subsequent iteration on the same task, it reads the previous codebase-analysis artifact, maps current findings to prior finding IDs, and annotates each finding as `new`, `persists`, `regressed` (was fixed in a prior iteration but reappeared), or `resolved`. The forensic-review skill enforces a 3-iteration safety valve: after 3 NEEDS_WORK cycles on the same task, it presents remaining critical findings to the orchestrator for manual decision rather than creating more remediation tasks.

### Measurable signal

Run forensic-review on a task that produces a NEEDS_WORK verdict. The codebase-analysis artifact includes a `Finding-ID` column or field in its structured findings. After remediation and re-review, the second artifact references the same finding IDs with `resolved` or `persists` annotations. After 3 consecutive NEEDS_WORK verdicts on the same task, the forensic-review skill outputs a "SAFETY VALVE: 3 iterations reached — presenting critical findings for manual decision" message instead of creating remediation tasks.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Software design principle dimensions in code-reviewer | medium | Existing universal quality dimensions partially overlap with SOLID/DRY checks; need real code-review report analysis to confirm whether design principle violations are caught or missed by current dimensions |
| Iterative implement-review feedback loop with finding ID tracking | medium | Existing remediation loop in forensic-review is structurally similar; finding ID tracking value depends on whether finding regression occurs in practice; need to examine real remediation cycles |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Read-only reviews (architecture-review skill) | Already covered — `@dh:code-reviewer` operates read-only by design ("You do NOT: Implement fixes yourself, Modify code, tests, or documentation being reviewed") at plugins/development-harness/agents/code-reviewer.md lines 28-33 |
| Multi-platform portability (Claude Code, Cursor, Codex, Gemini CLI) | Too abstract for local repo — this repo IS a Claude Code plugin marketplace; multi-platform targeting is outside its architectural scope. Multi-ecosystem frontmatter preservation (ecosystem_registry.py) already handles the relevant cross-platform concern at the skill definition level |
