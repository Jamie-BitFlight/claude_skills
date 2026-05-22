# Groom - backlog item - Scope boundary

Grooming is the intake-clarification step that prepares a change request for later planning. Its job is to answer:

- What work is being requested?
- Is the problem statement clear enough to proceed?
- What facts, artifacts, prior work, and constraints are already available?
- When is the work needed, if any deadline or target timing is known?
- What is the current priority, if known?
- What does the work depend on?
- Does this work block other known work?

Grooming is a stand-alone pre-planning step. It prepares the request so that a later planning phase can produce design, architecture, task decomposition, and implementation approach.

Grooming covers the request's purpose, problem framing, context, constraints, urgency, dependencies, and blocking relationships for a feature, fix, or other inbound change.

Grooming does NOT produce:
- architecture
- implementation design
- task decomposition
- execution plan

Those outputs belong to the planning phase after grooming is complete.

**Required outputs**

A completed grooming result must produce:
- a DEEP item (Detailed, Estimated, Emergent, Prioritized)
- an RT-ICA completeness assessment
- an Impact Radius assessment — rows may include an optional `pattern:` annotation for
  enumerable changes; see [impact-analyst.md](../../../../../agents/impact-analyst.md) for format
- a Fact-Check section
- an Issue Classification
- all required groomed subsections defined elsewhere in this workflow

