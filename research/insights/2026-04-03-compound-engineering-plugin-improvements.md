# Improvement Proposals: Compound Engineering Plugin

**Research entry**: ./research/skill-generation-tools/compound-engineering-plugin.md
**Generated**: 2026-04-03
**Patterns assessed**: 6
**Backlog items created**: 1 (issues: #1430)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Confidence gating and deduplication pipeline for multi-agent review findings

**Source pattern**: "Parallel agent dispatch with confidence scoring... Deduplication pipelines to suppress duplicate findings... Gating logic (confidence thresholds, question tools)" (Section: Relevance to Claude Code Development, item 2)
**Local system**: `.claude/skills/swarm-patterns/SKILL.md`, `.claude/agents/code-review.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1430 created

### Current state

The `swarm-patterns` skill (Pattern 1 -- Parallel Specialists) dispatches multiple review agents in parallel, but agents return unstructured findings as free-text messages via `SendMessage`. There is no mechanism to:

1. Assign confidence scores to individual findings (e.g., "high confidence: SQL injection in auth.py line 42" vs "low confidence: possible performance issue")
2. Deduplicate findings when multiple review agents flag the same issue from different perspectives
3. Gate whether a finding is surfaced to the user based on a confidence threshold

The `code-review` agent (`.claude/agents/code-review.md`) produces categorized output (critical/warning) but has no structured confidence scoring schema. When multiple review agents run in parallel (as in the swarm-patterns parallel specialists recipe), duplicate findings accumulate without consolidation.

Issue #1423 tracks persona-based specialized review agents but does NOT address confidence scoring or deduplication -- it focuses on splitting the single code-reviewer into domain-specific agents.

### Target state

The `swarm-patterns` skill's "Pattern 1 -- Parallel Specialists" recipe includes a post-collection consolidation step. Review agents emit structured findings with a confidence field (e.g., `confidence: high | medium | low`). The orchestrator applies two post-processing steps before presenting results:

1. **Dedup**: Findings from different agents referencing the same file + line range + issue category are merged into a single finding, noting which agents flagged it
2. **Confidence gate**: Findings below a configurable threshold (default: medium) are grouped into a "Low confidence -- verify manually" section rather than presented as blocking issues

The consolidation logic lives in a reference file (e.g., `swarm-patterns/references/review-consolidation.md`) that teaches the orchestrator how to merge and filter findings.

### Measurable signal

The `swarm-patterns` SKILL.md Pattern 1 recipe includes a "Consolidate findings" step between "Wait for results" and "Synthesize findings and cleanup". A reference file `references/review-consolidation.md` exists in the swarm-patterns skill directory. The reference file defines the structured finding schema (file, line range, category, confidence, description) and the dedup/gating algorithm.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Automated changelog generation from conventional commits (semantic-release) | Low | The local repo uses pre-commit hook-based version bumping (`auto_sync_manifests.py`) which serves a different release model. Would need to verify whether semantic-release adds value on top of the existing pre-commit automation, and whether the repo follows conventional commit format consistently enough to benefit. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Skill design patterns (reference file inclusion, `@` inline syntax, cross-platform compatibility) | Already covered in `/plugin-creator:skill-creator` SKILL.md -- progressive disclosure, reference file patterns, and tokenomics are documented extensively. The `@` inline syntax is a Compound Engineering convention not applicable to Claude Code's skill system. Cross-platform compatibility is not relevant since this repo targets Claude Code only. |
| Agent namespacing (fully-qualified `plugin:category:name` references) | Already covered -- the local system uses `plugin:agent-name` namespacing and the swarm-patterns examples already demonstrate three-level namespacing (e.g., `compound-engineering:review:security-sentinel`). |
| Knowledge compounding after implementation | Already in backlog as #1424: "Knowledge compounding -- capture solved-problem artifacts after implementation" (source: this same research entry) |
| Persona-based specialized review agents | Already in backlog as #1423: "Persona-based specialized review agents for quality gates" (source: this same research entry) |
