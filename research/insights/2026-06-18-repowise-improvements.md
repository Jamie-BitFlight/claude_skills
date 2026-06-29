# Improvement Proposals: repowise

**Research entry**: ./research/mcp-ecosystem/repowise.md
**Generated**: 2026-06-18
**Patterns assessed**: 5
**Backlog items created**: 2 (issues: #2589, #2590)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Command output distillation hook — compress noisy shell stdout before the agent reads it

**Source pattern**: "Command Distillation — `repowise distill <cmd>` compresses shell command output before agent reads it — errors-first, exit code preserved, every omission reversible via `[repowise#<ref>]` marker ... Opt-in Claude Code hook rewrites noisy commands automatically." (Key Features §6, lines 135–144). Example savings: `git log -50` 3,064 → 331 tokens (89% saved); `git diff` (30 commits) 62,833 → 8,635 tokens (86% saved).
**Local system**: `.claude/rules/` (No Invented Limits policy) and the PostToolUse hook surface (`plugins/development-harness/hooks/hooks.json`, `task_status_hook.py`). No local skill or hook implements shell-command output compression.
**Confidence**: High
**Impact**: High
**Backlog**: #2589 created

### Current state

There is no local mechanism that compresses verbose shell-command output (stdout/stderr) before it enters an agent's conversation. A Grep across the repo for `distill`, `reversible truncation`, and `omission store` returns only research entries and unrelated reference files — no implementation. The closest existing backlog items (#1089 SAM-task compaction, #930 wave discovery-relay compression, #1858 conventions extraction, #2096 PostToolUse observation classification) all operate on internal harness data (SAM task bodies, worker outputs, tool-call metadata), not raw command stdout. The repo's own `.claude/rules/` "No Invented Limits" policy forbids silent truncation, which means any compression added must be reversible — exactly the property repowise's omission-store + `[repowise#<ref>]` marker provides, and which no current rule or tool supplies.

### Target state

A new opt-in capability (skill plus optional PostToolUse hook) compresses noisy command output following repowise's three invariants: errors-first ordering, exit code preserved verbatim, and every omission reversible via a stored reference marker (analogous to `[repowise#<ref>]`). Small outputs pass through untouched (a size threshold gates compression). A companion "expand" path recovers any dropped span on demand. This satisfies the repo's No Invented Limits rule because nothing is silently lost — the consumer can always retrieve the full content.

### Measurable signal

Running the distill capability on a verbose command (e.g. `git log -50` or a multi-failure `pytest -q`) produces output that (a) preserves the exact exit code, (b) places error/failure lines first, (c) is materially smaller than the raw output (verify by character/token count before vs after), and (d) contains a reference marker for each omitted span that, when expanded, returns the original bytes. A Grep for the new skill directory under `plugins/*/skills/` or a new PostToolUse entry in `hooks.json` returns a match.

---

## Improvement 2: Add a complexity dimension to git-history-recon hotspot ranking (churn ∩ complexity)

**Source pattern**: "Hotspots: files in top 25% of both churn AND complexity (empirically where bugs live)" (Git Intelligence, line 61). repowise defines a hotspot as the intersection of high churn and high complexity, a defect-calibrated signal (Code Health AUC 0.731), not churn alone.
**Local system**: `.claude/skills/git-history-recon/SKILL.md` — Pipeline 1 (Hotspots) and Pipeline 2 (Bug Magnets) plus the Phase 2 cross-reference computation.
**Confidence**: High
**Impact**: Medium
**Backlog**: #2590 created

### Current state

`git-history-recon` defines a hotspot purely as change frequency: Pipeline 1 is `git log --name-only ... | sort | uniq -c | sort -rn | head -N` (SKILL.md lines 93–107) — churn only, no complexity dimension. The only refinement is the Phase 2 intersection of churn with *commit-message-keyword* bug-magnets (Pipeline 2, lines 109–124), which the skill itself flags as "convention-dependent" and prone to under-reporting on ticket-ID-only or non-English commit conventions (lines 117–119, EC-2). A file that is large and structurally complex but rarely touched, or churned heavily without fix-keyword commits, never surfaces as high-risk. repowise's churn ∩ complexity definition is absent: the word "complexity" appears nowhere in a hotspot computation in the skill.

### Target state

`git-history-recon` computes a complexity proxy per candidate hotspot file (e.g. line count, or a tree-sitter/cyclomatic measure for supported languages) and ranks high-risk files by the intersection of high churn AND high complexity, in addition to the existing keyword-based Bug Magnets intersection. The `## High-Risk Files` section (SKILL.md lines 273–296) gains a complexity-derived column or a second risk lane so a high-churn high-complexity file is flagged even when no fix-keyword commit touched it. The convention-dependence caveat is reduced because risk no longer depends solely on commit-message keywords.

### Measurable signal

Running `/git-history-recon` on a repo where a file is high-churn and high-complexity but has no fix/bug/hotfix commit message produces that file in the `## High-Risk Files` section (it would be absent under the current churn ∩ keyword-only logic). The generated `walkthrough/recon-report.md` contains a complexity metric column or a documented churn∩complexity lane in the High-Risk Files section, and the SKILL.md pipeline reference documents the complexity computation.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| `get_risk()` PR-mode directive block (`will_break`, `missing_cochanges`, `missing_tests`, `governance_risk`) for pre-merge review (Relevance §4, lines 277, 108) | Low | The directive block depends on an indexed dependency + co-change graph that this repo does not maintain. The local `multi-perspective-review` and `code-reviewer` systems review a diff with no persistent graph, so the target state ("emit will_break / missing_cochanges directives") cannot be stated as an observable change to one file — it requires first building the graph layer, a separate unbounded-design effort. To raise confidence: verify whether any local indexing layer (or the installed context-mode / octocode MCP graph) could supply dependents and co-change pairs, then express a concrete per-file before/after target. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Defect-validated code-health score (1–10 / 25 biomarkers) surfaced on review verdict (Code Health Intelligence, lines 85–95; Relevance §6, line 281) | Already tracked as backlog #2253 ("code-review: Quantified Health Score (0–100) with severity-weighted deductions on review verdict") — same gap: ternary PASS/NEEDS-WORK/FAIL verdict lacks a quantified severity-weighted score. |
| `_meta` staleness envelope (`index_age_days`, `indexed_commit`, `stale_warning` when indexed HEAD diverges from live `.git/HEAD`) (line 113) | Not actionable for this repo. The envelope is meaningful only for a tool that maintains a persistent index against a HEAD commit; this repo's review/recon systems read live state on each run and hold no index to go stale, so there is no observable target state to extend. |

---

## Notes

- repowise is delivered as an installable MCP server (`/plugin marketplace add repowise-dev/repowise`). The two proposals above deliberately extract repowise's *patterns* into local systems rather than proposing a dependency on repowise itself — that direct-integration question is the research-utilization-assessor's scope, not this insight pass.
