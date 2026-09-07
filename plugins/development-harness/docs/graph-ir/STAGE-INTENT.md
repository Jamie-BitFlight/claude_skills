# The stages, and what each is for

Design-time. Stated by the repository owner, 2026-09-07, as what the harness was built to do and
what it solves. `docs/PURPOSE.md` "Closed-Loop Work Management" is the older ten-step summary of
the same thing; where the two differ, this file is the intent and that one is the abbreviation.

This is what an extraction is checked against. It says what each stage is for, what it reads and
what it produces — not how the current implementation does it. A stage the system implements
badly is a finding; a stage the system never implemented is `CONTRACT_UNSPECIFIED`.

## 1. Create

Step through creating a requirement, feature or issue **without speculating how it should work in
the system before understanding the system as a whole**.

Output: the backlog item, in the backend store.

## 2. Groom

Gather details, question the user, research the state of the art, understand the existing system
and the impact of a change to it, check and correct every claim, and assess whether the problem is
being considered from the right altitudes.

Output: the backlog item, plus report artifacts in the backend.

## 3. Design / architect

Reads the grooming reports, the backlog item, the existing architecture documents — ADRs, PRDs —
and the project's rules, ways of working and documented conventions from `AGENTS.md` and
`CLAUDE.md`. Designs or modifies architecture that is compliant with those, correcting for the
groomed bug or admitting the groomed feature, documentation or chore.

Then adversarially challenges the design: pokes holes in it, challenges its reasoning and its
existence, and offers alternatives, so that the change holds up against the problems and scenarios
the groomed item states.

Output: an artifact on the backlog item, plus ADRs and local documentation such as
`ARCHITECTURE.md`.

## 4. Plan

Reads the architecture and works out how to achieve it, how to validate that it was achieved, and
how to document it — so the outcome is demonstrable against the architecture and against the
original problem statement.

Identifies claims with no evidence, and functional gaps, and **surfaces them back upstream** into
the data-gathering and research stages.

Output: a plan.

## 5. Decomposition

Splits the plan into atomic tasks carrying dependencies, verification steps, acceptance criteria,
and a goal to reach. A task may carry specialist skills or agent knowledge, because the agent
doing it can see its task, the plan it belongs to, and the research that justifies the work.

A task states its output, its guardrails and how to tell it is done. **It does not prescribe how
to achieve it**, so the agent can reach the goal while handling environmental problems its own
way.

Output: the main work graph.

## 6. Orchestration

Reads the graph, assigns agents within it, gives them worktrees and task ids.

## 7. Act

A tasked agent loads its task and works. When it needs clarification it reaches the plan and the
gathered documentation for background and reasoning. It attempts the acceptance criteria and runs
the task's validation; those outcomes decide completion. On ending, it updates the task's status so
the orchestrator can coordinate what follows.

The output is completed work. That may be generated or modified content in a repository, and it
may equally be validation of an external system — a UI test against a web page, a radio reading
from an ESP32. The report of outcomes is appended to the task. Repository changes are committed on
the worktree and either raised as a pull request when standalone, or merged back to the trunk the
orchestrator is on under a single-PR workflow.

## 8. Loop

New information, concerns, gaps, adjacent broken systems, environmental failures, security issues
and the like are surfaced and routed:

- an architectural issue goes to the architect, which then goes to the planner to consider what
  changes;
- an environmental or external factor goes directly to the planner.

The planner assesses the new factors and amends the plan; the decomposer adds or changes tasks and
updates the graph; the orchestrator loop moves work through those steps and dispatches what is
new.

## 9. Bookend

The end of the graph checks for and updates documentation, and reviews the whole changeset. The
review is **conditional on what changed**: code review where code changed, prose review where
prose was edited, and where the task evaluated a system, a check that the reports exist and the
desired outcomes were met.

It checks the change is demonstrably effective at what it needed to achieve. Every blocker or
issue found goes back to stage 8.

## What this fixes

Each stage answers a failure the owner met repeatedly in agentic engineering and AI co-working.
An assessment that cannot say which stage a defect belongs to has not understood the system.
