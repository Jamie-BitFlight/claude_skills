# Improvement Proposals: Merly Mentor

**Research entry**: ./research/ai-research-tools/merly-mentor.md
**Generated**: 2026-03-18
**Patterns assessed**: 10
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 9

---

## Improvement 1: Code Snippet Syntax Validation in Research Entries

**Source pattern**: "Use Mentor to verify that research entry examples and code snippets are syntactically sound and follow language-specific best practices" (Integration Opportunities section)
**Local system**: .claude/skills/research-curator/references/validation-rules.md, .claude/skills/research-curator/scripts/validate_research.py
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: the research entry suggests using Merly (a proprietary tool) rather than describing a transferable mechanism; the generalized idea of "validate code snippets in research entries" is inferred, not directly observed as a pattern

### Current state

`validate_research.py` performs structural validation of research entries: section completeness, header fields, empty sections, access dates, freshness tracking, statistics currency, URL format, cross-references, and formatting suggestions. No check exists for whether code blocks within research entries contain syntactically valid code. File: `.claude/skills/research-curator/references/validation-rules.md` lists all current checks -- none address code snippet validity.

### Target state

`validate_research.py` includes a new check (warning severity) that extracts fenced code blocks with language specifiers, runs a syntax check appropriate to the declared language (e.g., `python -c "import ast; ast.parse(code)"` for Python, `node --check` for JavaScript), and reports blocks that fail parsing. Research entries with invalid code snippets receive a warning during `--validate` mode.

### Measurable signal

Run `uv run .claude/skills/research-curator/scripts/validate_research.py` against a research entry containing an intentionally malformed Python code block. Output includes a warning-severity issue identifying the code block line number and syntax error. The check name `code_snippet_syntax` appears in the validation-rules.md check definitions.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Code snippet syntax validation in research entries | Medium | Research entry suggests using Merly (proprietary tool) for this, not a transferable mechanism. The generalized pattern is inferred. Would need to verify that invalid snippets actually exist in current research entries to confirm the gap causes real problems. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-tiered Abstraction for Code Understanding | Too abstract -- describes Merly's internal model architecture, not a transferable mechanism. The suggestion to "organize information hierarchically" has no concrete observable target state. |
| Deterministic AI Reasoning | Architecturally incompatible -- this repo's systems are LLM-based; adopting logic-based deterministic reasoning would require replacing the core architecture, not extending it. |
| Federated, Self-Supervised Learning | Requires ML infrastructure not present in this repo. Not an extension of existing systems. |
| Lifetime Repository Analysis | Freshness tracking already exists in validation-rules.md (Last Verified, Next Review Recommended). Merly's specific mechanism is proprietary and non-transferable. |
| Plugin Quality Certification | Suggests integrating Merly as an external commercial tool, not adopting a transferable pattern. |
| Skill Developer Feedback Loop | Depends on Merly specifically as the feedback source. Not a generalizable pattern. |
| Backlog Prioritization via Defect Detection | Suggests using Merly's proprietary defect detection. Not a transferable mechanism. |
| Code Quality Baseline Measurement | Already covered by T0 baseline capture and TN verification gate in the SAM workflow (see .claude/rules/local-workflow.md, Bookend Tasks section). |
| CI/CD Quality Gates | Already covered by /complete-implementation skill with 6 quality gate phases (code-reviewer, feature-verifier, integration-checker, doc-drift-auditor, service-docs-maintainer, context-refinement). |
