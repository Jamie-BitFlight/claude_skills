---
name: parallel-work
description: Shapes for running many sub-agents at once — fan-out with a barrier, maker/checker, generate-and-filter, tournaments for ranking, hypothesis fan-out for root cause, and loops that stop on a condition with a cap. Use when a phase has several independent targets, when a task is too large or too repetitive for one window, when the same edit applies across many files, when ranking or judging a large set, when several hypotheses compete, or when work must repeat until a signal says stop. Does not apply when units depend on each other's results or the cause is still unknown — investigate first, then parallelize.
---

# Parallel work

Parallelism buys fresh context per unit and speed. It costs coordination: a fan-in that must wait, a merge that must not collide, a judge that must not be the maker. Use it where the units are genuinely independent, and pay the coordination cost explicitly.

## Preconditions

- The units are independent: none needs another's result to start.
- You know what the units are. Unknown cause → one investigation dispatch first.
- Writes are isolated: each unit writes different files, or each runs in its own worktree (see [rules/commit-cadence-and-worktrees.md](../../../../rules/commit-cadence-and-worktrees.md)).

Missing any one → serialize, or investigate first.

## Shapes

**Fan-out, fan-in.** N dispatches of the same phase, one per unit, sent together. A single consolidating dispatch waits for all of them — that wait is the barrier — and merges their delivery files into one. Keep each unit's output in a file; the consolidator reads paths, not your context.

**Mechanical fan-out.** One `process` dispatch decides the exact change once. N generic dispatches apply it verbatim, each to its own targets. One `review` dispatch checks the whole set. The orchestrator never applies the edit itself, however small the set.

**Maker/checker.** Whoever produced a result never judges it. Route `review` to a different agent — a reviewer-typed agent for the domain where one exists, otherwise a specialist in a different role — with the success criteria and the artifact path, and nothing from the maker's reasoning.

**Generate and filter.** Fan out to produce candidates; one dispatch dedupes and scores them against a written rubric; only survivors continue. Write the rubric before generating.

**Tournament.** For ranking a set too large to judge in one window: pairwise comparison dispatches, each holding two items, with a bracket held in a file. Comparative judgments are more reliable than absolute scores.

**Hypothesis fan-out.** For root cause: one dispatch per disjoint evidence source (logs, code, data) forms a hypothesis from its source alone. Then one dispatch per hypothesis tries to refute it. What survives refutation is the finding.

**Loop until stop.** For work of unknown size: repeat a dispatch until an observable condition holds — no new findings, zero errors in the gate output, the checklist file has no unchecked items. Set the cap before the first iteration (default 5). At the cap, report `PARTIAL` with what remains.

## Checklist fan-out

A markdown file of `- [ ]` items is a ready-made unit list: one dispatch per unchecked item, each told to tick its own line on DONE, then loop-until-stop on "no unchecked items remain." Serialize items that name the same file.

## Caps and stop conditions

Every loop and every fan-in has a number written down before it starts: iterations, re-dispatches, or units. Hitting the cap is a `PARTIAL` or `BLOCKED` report to the user, never a silent retry.

## Persistent teams

Some harnesses offer long-lived agent teams with shared task lists and messaging. They add instruction and communication overhead that agents follow inconsistently, and they are not portable across harnesses. The shapes above need none of it. Reach for a team only when agents must exchange messages mid-task, and then consult the harness notes.

## Pointers

- [delegate](../delegate/SKILL.md) — the prompt template each unit uses.
- [delegate/references/harness-notes/claude-code.md](../delegate/references/harness-notes/claude-code.md) — how to send concurrent dispatches, isolate worktrees, and move a long pipeline into a workflow script on Claude Code.
