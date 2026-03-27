# Context-Fit Complexity Model

In agent workflows, complexity is not a property of the code. It is a property of context sufficiency.

A task is simple when the agent already has, or can cheaply derive, the project-specific knowledge required to execute it, leaving enough working context to implement and iterate. A task is complex when knowledge loading, uncertainty resolution, or transient context overhead consume so much of the window that reliable execution degrades.

## The Equation

```text
Complexity = context required for (knowledge loading + uncertainty resolution + execution)
             relative to context available
```

Three cost components:

- **Required non-native knowledge** — everything not already in training weights that must be loaded for the task
- **Active uncertainty** — missing or unverified prerequisites that could block or invalidate execution
- **Live context overhead** — transient material consuming window budget while the agent works: logs, failed attempts, verbose outputs, process scaffolding

## Operational Principles

### 1. Decomposition

Split tasks at **knowledge-boundary seams**, not code seams. If two steps require the same knowledge payload, combine them. If a step requires a distinct or oversized knowledge payload, isolate it.

### 2. Guidance Over Enforcement

Constraints are not free. Every hardcoded rule has a maintenance cost proportional to how volatile the thing it references is.

- **Stable constraints** are cheap and worth encoding
- **Volatile constraints** are expensive and should be discovered dynamically

The goal is a well-lit trail, not locked gates. Excellent paths forward preserve adaptability — agents can still improvise when the path is clear. Adding constraints reduces adaptability and increases the surface area of things that must stay correct as the system evolves.

### 3. Progressive Disclosure

Do not preload all project knowledge. Load only the minimum layer needed for the current step.

### 4. Context Garbage Collection

Do not keep raw intermediate artifacts after they have been consumed. Retain only the durable findings needed downstream.

### 5. Unknown Handling

Unknown unknowns become known unknowns through structured prerequisite enumeration, domain checklists, artifact inspection, adversarial review, and early collision with reality.

RT-ICA is the intake and uncertainty-resolution method inside this broader model — it handles steps 2-3 of the operational loop.

## Operational Loop

1. Start from the goal
2. Enumerate prerequisites for success
3. Classify each prerequisite as AVAILABLE, DERIVABLE, or MISSING
4. Estimate the knowledge payload required to resolve and execute
5. Check whether the payload plus implementation fits the effective context budget
6. If not, split by knowledge boundary
7. Execute with progressive disclosure
8. Convert unknown unknowns into known unknowns through reality contact
9. Garbage-collect transient context as soon as it has been distilled
10. Preserve guidance that helps, avoid enforcement that fossilizes

## Relationship to Other Layer 0 Components

- **SAM pipeline** — the stages (S1-S7) should be evaluated through this lens: stage boundaries exist where knowledge requirements shift, not where process convention dictates
- **RT-ICA** — serves as the uncertainty-resolution method (loop steps 2-3), classifying prerequisites as AVAILABLE/DERIVABLE/MISSING
- **Orchestrator discipline** — context window management is a direct application of this model: the orchestrator delegates to preserve its own context budget
- **Task decomposition** — `swarm-task-planner` should split at knowledge boundaries, combine steps that share payloads, isolate steps with distinct requirements

## Slogans

```text
Complexity is context-fit under uncertainty.

Task complexity is the cost of loading enough project truth to act reliably.

Agent planning is context-window packing over knowledge, uncertainty, and work.
```
