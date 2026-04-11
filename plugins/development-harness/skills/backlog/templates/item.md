---
name: ITEM TITLE HERE
description: One-sentence summary of the problem or goal.
metadata:
  topic: item-title-slug-here
  source: Session observation | Code review | User request | Research finding
  added: YYYY-MM-DD
  priority: P1
  type: Feature
  status: needs-grooming
  # groomed: YYYY-MM-DD       # set by groom-backlog-item when all required sections present (see finalize.md)
  # issue: '#N'               # set by backlog script on GitHub issue creation
  # milestone: N              # set by group-items-to-milestone
  # plan: plan/slug.md        # set by work-backlog-item when SAM plan created
---

<!-- Description: prose summary of the observed problem or need. Do not describe the solution. -->

**Suggested location**: `plugins/plugin-name/` <!-- optional: codebase path where work lands -->

**Research first**: <!-- optional: questions to answer before grooming can proceed -->

**Acceptance Criteria**:
<!-- Required for P0. Recommended for P1. Each criterion must be a specific, verifiable condition. -->
<!-- Examples:
  - Running `uv run backlog.py list --format json` outputs valid JSON
  - File `~/.dh/projects/{slug}/backlog/p1-{slug}.md` exists with correct frontmatter
  - `backlog_view(selector="#N")` returns `state: "open"` in the dict
-->
- <!-- criterion 1 -->
- <!-- criterion 2 -->

---

<!-- The following sections are written by downstream skills. Do not fill them at creation time. -->

## Fact-Check

<!-- Written by: groom-backlog-item Step 4 (fact-check skill) -->
<!-- Format:
Claims checked: N
VERIFIED: N | REFUTED: N | INCONCLUSIVE: N
Refuted claims: [list]
Inconclusive claims: [list]
Citations: [list]
-->

## RT-ICA

<!-- Written by: groom-backlog-item Step 5b (MUST be written before groomer agent runs) -->
<!-- Format:
Goal: {one sentence}
Conditions:
1. {condition} | Status: AVAILABLE|DERIVABLE|MISSING | Info needed: {what}
Decision: APPROVED|BLOCKED
Missing: {list or "None"}
-->

## Groomed

<!-- Written by: backlog-item-groomer agent (spawned by groom-backlog-item Step 8) -->

### Reproducibility

<!-- Can the problem be reproduced? Steps to reproduce, or "N/A for feature work". -->

### Priority

<!-- Justification for the assigned priority tier. -->

### Impact

<!-- What breaks or degrades if this item is not addressed? -->

### Scope

<!-- What is in scope? What is explicitly out of scope? -->

### Output / Evidence

<!-- What artifact or observable change proves this is done? -->

### Dependencies

<!-- Other backlog items, external tools, or conditions that must be true first. -->

### Research

<!-- Findings from research-first questions, if any. -->

### Skills

<!-- Claude Code skills needed to implement this item, or "None". -->

### Agents

<!-- Claude Code agents needed, or "None". -->

### Prior Work

<!-- Related commits, PRs, or prior attempts. -->

### Files

<!-- Specific files expected to be modified. -->

### Decision

<!-- groomer's final assessment: PROCEED, DEFER, CLOSE, or NEEDS_RESEARCH with rationale. -->

## Acceptance Criteria Verification

<!-- Written by: work-backlog-item close — per-criterion PASS/FAIL with file:line evidence -->
<!-- complete-milestone pre-flight gate detects verified items by grepping for this section header -->
<!-- Format:
[PASS] {criterion} — verified at {file}:{line}
[FAIL] {criterion} — {what was not found}

Overall: PASS|FAIL ({N}/{M} criteria met)
-->
