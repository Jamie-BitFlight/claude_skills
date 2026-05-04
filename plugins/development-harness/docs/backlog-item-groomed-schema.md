# Backlog Item Groomed Schema

**Purpose**: Define the structure of groomed content written into backlog item files. Grooming (backlog refinement) transforms items from vague ("this problem happens") to ready for planning — problem is clear, facts are verified, resources are mapped, effort is estimated, and blockers are surfaced. The agent does this autonomously: fact-checking claims, searching the codebase for related work, and identifying gaps. It does NOT produce architecture, task decomposition, or implementation plans — those happen in the SAM planning phase.

**Location**: Groomed content lives in the **body** of `~/.dh/projects/{slug}/backlog/{priority}-{slug}.md` (resolved via `dh_paths.backlog_dir()`). Frontmatter uses the research-style `metadata:` block (aligned with `./research/` entries). Body has no duplication of frontmatter — only extra fields when present, plus `## Groomed` when groomed.

---

## Frontmatter (Research-Style)

Aligned with [research/README.md](../../research/README.md) metadata format:

```yaml
---
name: "Item title"
description: "Main problem statement or description"
metadata:
  topic: "slug-from-title"
  source: "Source description"
  added: "YYYY-MM-DD"
  priority: P0|P1|P2|Ideas
  type: Feature|Bug|Refactor|Docs|Chore
  status: open|in-progress|done|resolved
  # optional:
  issue: "#N"
  plan: "path/to/plan.md"
  groomed: "YYYY-MM-DD"
  layer: "0"|"1"|"2"
  language: python|typescript|...
  stack: fastapi|python-cli|...
---
```

---

## Body (No Duplication)

Body is **empty** when un-groomed and no extra details. When present, body contains only:

- **Suggested location** — when applicable
- **Research first** — when applicable
- **Decision needed** — when applicable
- **Files** — when applicable
- **## Groomed (YYYY-MM-DD)** — when groomed (see below)

Do **not** duplicate `name`, `description`, `source`, `added`, `priority`, `type`, `issue` in the body — they live in frontmatter.

---

## Content Rules

| Rule | Requirement |
|------|-------------|
| **Problem space** | Describe what is broken, where it lives, and what is affected. Give the specialist enough context to reason about the full scope. |
| **Desired outcome** | Describe what done looks and feels like — not the steps to get there. The specialist chooses how; the item defines what success is. |
| **Verification signal** | State how the specialist will know they have reached the outcome as they work toward it. Acceptance criteria serve this purpose — observable checks, not implementation steps. |
| **No HOW** | Do not prescribe the fix, implementation approach, or code to write. That belongs in the planning phase (`/add-new-feature`). Examples of broken behaviour are fine; proposed solutions are not. |
| **No line numbers** | Reference files and function names only. Line numbers go stale as code changes. Use `path/to/file.py — FunctionName()` not `path/to/file.py:42`. |

---

## Groomed Sections (Body, under ## Groomed)

| Section | Purpose | Required |
|---------|---------|----------|
| **Reproducibility** | Steps x, y, z to replicate the problem | When applicable |
| **Output / Evidence** | Steps to see the issue; screenshot or log references | When applicable |
| **Priority** | Numeric (e.g., 8/10) with rationale | Yes |
| **Impact** | Bottleneck to x, y, z; who/what is blocked | When applicable |
| **Benefits** | What doing this unlocks (x, y, z) | When applicable |
| **Expected Behavior** | How it should work | Yes |
| **Desired Structure** | The target state we want | When applicable |
| **Acceptance Criteria** | Concrete checks for "done" | Yes |
| **Human Input** | Output of interviewing the human partner; desired outcome | When BLOCKED or human input needed |
| **Questions for Human** | Prompts to ask when info is missing (ARL human-probing) | When BLOCKED |
| **Resources** | Compact table: skills, agents, prior work | Yes |
| **Dependencies** | Items this depends on; items this unblocks | When applicable |
| **Blockers** | Missing prerequisites; RT-ICA BLOCKED reason | When BLOCKED |
| **Effort** | Small / Medium / High | When estimable |
| **Issue Classification** | Classification type and rationale | When groomed after Issue #314 |
| **Root-Cause Analysis** | Evidence chain from `/find-cause` or 6 Sigma measurement | When `issue-classification` is `defect` or `recurring-pattern` |

### Issue Classification Section Format

```markdown
### Issue Classification

**Type**: procedural | defect | recurring-pattern | missing-guardrail | unbounded-design
**Rationale**: {1-2 sentence explanation of why this classification was chosen}
**Analysis Method**: none | 5-whys | 6-sigma | design-framing
**Scenario Target**: {what scenario exposed this} -> {what should improve}
```

### Root-Cause Analysis Section Format

**5-whys variant** (for `defect` classification):

```markdown
### Root-Cause Analysis

**Method**: 5-whys
**Classification**: defect

#### Evidence Chain

1. CLAIM: {symptom observed}
   EVIDENCE: {source}
   VERIFIED: yes
   DEPENDS ON: none (symptom)

2. CLAIM: {why 1}
   EVIDENCE: {source}
   VERIFIED: yes
   DEPENDS ON: 1

**Root Cause**: {single actionable statement}
**Scenario Target**: {what scenario exposed this} -> {what should improve}
```

**6-sigma variant** (for `recurring-pattern` classification):

```markdown
### Root-Cause Analysis

**Method**: 6-sigma
**Classification**: recurring-pattern

#### Measurement

- **Frequency**: {N occurrences in {time period or batch}}
- **Common factors**: {what the occurrences share}
- **Affected scope**: {what parts of the system are impacted}

#### Analysis

- **Root cause pattern**: {why this class of defect recurs}
- **Missing guardrail**: {what gate or instruction should prevent this}

#### Improvement

- **Proposed guardrail**: {specific instruction, gate, or check to add}
- **Verification**: {how to confirm the guardrail works}
```

---

## RT-ICA Integration

- **APPROVED**: Item is ready; groomed sections filled
- **BLOCKED**: Include **Blockers** and **Questions for Human**; do not treat as ready for planning

---

## Example Groomed Body

```markdown
## Description

Original problem statement from backlog.

## Groomed (2026-02-23)

### Reproducibility

1. Run `uv run prek run --files foo.py`
2. Observe LK001 on line 42

### Output / Evidence

- Screenshot: `~/.dh/projects/{slug}/backlog/assets/p1-foo-screenshot.png`
- Log excerpt in `plugins/plugin-creator/planning/qa-report.md`

### Priority

8/10 — Blocks plugin validation CI gate; affects all contributors.

### Impact

- Blocks: manifest-sync job, pre-commit hooks
- Bottleneck: Every PR runs `uvx skilllint@latest check`

### Benefits

- CI gate becomes reliable
- Pre-commit output actionable

### Expected Behavior

Plugin validator should report unique files, not validator invocations.

### Acceptance Criteria

1. Running validator on 1 file shows "Total files: 1"
2. Summary counts unique files

### Issue Classification

**Type**: defect
**Rationale**: Plugin validator double-counts files — traceable failure with identifiable cause chain.
**Analysis Method**: 5-whys
**Scenario Target**: Run validator on 1 file, see "Total files: 2" -> shows "Total files: 1"

### Resources

| Type | Item |
|------|------|
| Skill | plugin-creator:claude-hooks-reference-2026 |
| Agent | @refactor-executor |
| Prior work | ~/.dh/projects/{slug}/plan/tasks-2-validator-ux-coverage.md |
```
