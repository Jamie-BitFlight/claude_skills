# Improvement Proposals: Jakub Krehel Interface Skills Collection

**Research entry**: ./research/developer-tools/jakubkrehel-skills.md
**Generated**: 2026-10-02
**Patterns assessed**: 10
**Backlog items created**: 0 (issues: none — `backlog_add` failed, see note below)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 7

> **Backlog creation failure.** Improvements 1 and 2 qualify for P1 backlog items. The first
> `mcp__plugin_dh_backlog__backlog_add` call returned
> `"error": "GraphQL is unavailable in this environment: GitHub GraphQL is not available from Claude Code sessions ..."`,
> `"retryable": false`. `backlog_list` failed with the same error. Per the backlog server's
> instruction ("on a failed call, report the failure and stop"), no item was created by another
> route. Both proposals below carry the exact title and priority to file once the backlog tool
> works. Duplicate check was done instead against all 819 open issue titles fetched via
> `gh api repos/Jamie-BitFlight/claude_skills/issues?state=open&per_page=100&page=N`; no open
> issue covers either proposal (closest: #1004 "Quality gate findings auto-create backlog items",
> which is downstream of Improvement 1, not the same change).

---

## Improvement 1: multi-perspective-review verdict findings carry no change-origin classification (introduced / regression / pre-existing)

**Source pattern**: "`interface-review`: change-scoped review (branches, PRs, uncommitted work) that classifies findings as Introduced/Regression/Pre-existing" (Key Features → Specialized Review Entry Points); "`interface-review` owns change scope resolution, blast radius, finding classification (Introduced/Regression/Pre-existing)" (Technical Architecture → Skill Structure and Ownership Model)
**Local system**: `plugins/development-harness/skills/review-verdict-contract/references/verdict-schema.md`, `plugins/development-harness/skills/multi-perspective-review/SKILL.md`
**Absence evidence**: `git grep -n -i -E "introduced|pre-existing|preexisting|regression" -- plugins/development-harness/agents/reviewer-*.md plugins/development-harness/agents/review-synthesizer*.md plugins/development-harness/skills/review-*-change plugins/development-harness/skills/synthesize-review-findings plugins/development-harness/skills/multi-perspective-review/SKILL.md plugins/development-harness/skills/multi-perspective-review/references` -> 3 matches, all prose in the `SKILL-GOALS.md`/`SKILL.md` description lines of review-performance-change and review-security-change ("regressions", "introduced or exposed"), no classification field; `git grep -il -E '"origin"|introduced_by|pre_existing' -- plugins/development-harness/skills/multi-perspective-review plugins/development-harness/skills/review-verdict-contract plugins/development-harness/dh_core` -> 0 matches
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — `backlog_add` failed (GraphQL unavailable, non-retryable). File as P1, type Feature.

### Current state

`multi-perspective-review/SKILL.md` builds review scope from `git diff --name-only <git-range>`
(changed files, not changed lines). The four reviewer agents
(`plugins/development-harness/agents/reviewer-{security,performance,quality,accessibility}.md`)
scan those files and write findings in the §2.1 schema of `verdict-schema.md`, whose finding object
has only `severity`, `file`, `line`, `description`, `rule`. No field records whether a finding was
introduced by the diff, is a regression, or pre-dates it on untouched lines. Under §2.4 gate logic a
BLOCKER on an untouched line of a touched file makes that perspective REJECT and FAILs the gate,
and the §2.6 punch list gives the caller no field to route pre-existing defects to the backlog
(AGENTS.md "Pre-Existing Issues and Backlog Progression") separately from defects the change must
fix.

### Target state

- `verdict-schema.md` §2.1 finding objects carry a required classification with exactly three
  values (introduced, regression, pre-existing) and a rule for determining it against the diff
  range.
- §2.4 gate logic states how each classification affects REJECT/FAIL.
- §2.6 punch-list entries carry the classification; its validity checks cover the field.
- `multi-perspective-review/SKILL.md` passes reviewers the diff range so they can classify.

### Measurable signal

- `git grep -n -i "pre-existing" plugins/development-harness/skills/review-verdict-contract/references/verdict-schema.md`
  returns the field definition in §2.1 and the gate rule in §2.4 (currently 0 matches).
- A multi-perspective-review run over a diff touching a file with a defect on an unchanged line
  produces a punch-list entry classified pre-existing, with the gate outcome §2.4 prescribes.

---

## Improvement 2: dh accessibility reviewer does not check reduced-motion handling

**Source pattern**: "Escalation triggers (accessibility failures, keyboard reachability, contrast, reduced-motion, content clipping, destructive actions without confirmation) rank HIGH severity immediately" (Key Features → Multi-Domain Review Orchestration)
**Local system**: `plugins/development-harness/skills/review-accessibility-change/SKILL.md`, `plugins/development-harness/agents/reviewer-accessibility.md`, `plugins/development-harness/skills/code-review-web/SKILL.md`
**Absence evidence**: `git grep -il -E "reduced-motion|reduce.motion" -- plugins/ .claude/skills .claude/agents` -> 2 matches, `.claude/skills/agent-browser/references/commands.md` (a browser emulation command) and `plugins/development-harness/docs/dh-system-model.html` (a page's own CSS); neither is a review check. `git grep -n -i -E "contrast|motion|keyboard|focus" -- plugins/development-harness/skills/code-review-web/SKILL.md` -> contrast, focus, keyboard present; no motion line.
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — `backlog_add` failed (GraphQL unavailable, non-retryable). File as P1, type Feature.

### Current state

`review-accessibility-change/SKILL.md` inspects "accessible names/labels, semantic roles,
keyboard/focus operation, dynamic announcements, meaningful image alternatives, color-only state,
and CLI output whose meaning depends only on ANSI color". `code-review-web/SKILL.md` adds WCAG AA
contrast ratios, focus management and keyboard order. Neither names motion: an animation or
transition added in a change without a `prefers-reduced-motion` path passes both reviewers
unexamined. Of the entry's six escalation triggers, accessible names, keyboard reachability and
contrast are covered locally; reduced-motion is not.

### Target state

`review-accessibility-change/SKILL.md`'s inspection list names motion: animations/transitions
introduced by the change honour `prefers-reduced-motion` (or equivalent user setting), with the
condition under which a missing reduced-motion path is a REJECT versus a MINOR finding stated.
`code-review-web/SKILL.md` carries the matching check so the single-reviewer path agrees.

### Measurable signal

`git grep -n -i "reduced-motion" plugins/development-harness/skills/review-accessibility-change/SKILL.md plugins/development-harness/skills/code-review-web/SKILL.md`
returns at least one match in each file (currently 0).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| `break` component stress testing routed into review gates (Integration Opportunities → `review-verdict-contract`) | low | The entry's suggested target is a static diff-review verdict schema; `break` renders components in a browser across content lengths, states and container widths. No local reviewer renders UI, and the entry gives only a summary of `break`'s mechanism (`break/scenarios.md` was not read in the research). To raise confidence: read `break/SKILL.md` and `scenarios.md` upstream, and decide whether the owner is a new skill built on `.claude/skills/agent-browser/` rather than the verdict schema. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Skill dispatch and orchestration (`better-interface` routing) | Entry itself states "Change: none"; covered by `plugins/agent-orchestration/skills/delegate/SKILL.md` and `plugins/development-harness/skills/multi-perspective-review/SKILL.md` (parallel perspectives + synthesis) |
| Plugin distribution / marketplace registration | Entry states "Change: none"; `.claude-plugin/marketplace.json` already in use |
| Respect existing design decisions (`.claude/agents/code-review.md`) | Entry states "Change: none"; too abstract for an observable target |
| Evidence-first review criteria (`rules/fact-verification-first.md`) | Entry states "Change: none"; philosophical, already a rule |
| ARL stress-test integration (`plugins/agentskill-kaizen/references/arl-ARL-agent-instructions.md`) | Incompatible: the ARL phase stress-tests scientific rigor of a research synthesis, not rendered UI components; no shared mechanism |
| Domain marked "Not reviewed" when a domain skill is unavailable | Already covered more strictly: `verdict-schema.md` §2.4/§2.6 put a perspective with no verdict in `missing` and FAIL the gate |
| Report capped at 15 findings | Incompatible with AGENTS.md "No Invented Limits"; local §2.6 deduplicates and orders by severity instead of capping |
