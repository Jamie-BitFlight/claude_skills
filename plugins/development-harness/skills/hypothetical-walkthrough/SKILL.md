---
name: hypothetical-walkthrough
description: Use when the user asks for a hypothetical walkthrough of a system to expose tensions, frictions, gaps, or contradictions between its expected and evidenced flow.
---

# Hypothetical Walkthrough

Use the requested effort, defaulting to medium: **Low** gives a concise, focused end-to-end scenario; **Medium** uses representative end-to-end scenarios to reveal interactions and transitions; **High** simulates agent-generated user stories step by step across every relevant change and reaction.
When no scenario or user story is supplied, state the contextual interpretation and ask whether to proceed; when no interpretation is supportable, ask which scenario or user story to simulate.
When the target under test is absent or unclear, ask which system or process to trace.
Begin the walkthrough only after both the scenario or user story and target under test are clear.
Trace the configured system in ordered, step-by-step form from entry to completion, following how its parts, actors, and state interact. Let the goals and evidence direct attention rather than a fixed checklist.
Contrast the expected flow with repository and runtime evidence. Mark facts, inferences, and unknowns; do not invent missing scenario facts or branch conditions, and keep unknown-dependent steps conditional. This is a simulation, not an observed end-to-end demonstration.
Report process, system, or transactional frictions, tensions, contradictions, and outcomes unexpected from the stated goals. Give each finding's evidence, impact, and a concrete validation check. End every report by offering to address, backlog, or discuss/split the findings.
