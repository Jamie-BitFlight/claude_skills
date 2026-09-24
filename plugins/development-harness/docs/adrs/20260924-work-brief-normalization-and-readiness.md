# Normalize every source into a Work Brief before Design

**Date:** 2026-09-24
**Status:** Proposed

This record describes a proposed target. None of the behavior below is implemented by this ADR.

## Context

The implemented `/dh:work-backlog-item` route begins with a provider-backed backlog item. Separately,
SAM can create and execute issue-less Plans and the local ledger can run them. What is absent is a
supplier-neutral intake seam that turns either a backlog item or interactive context into the same
design-ready input before architecture and planning.

Conversations, interviews, brainstorming sessions, and backlog items can describe the same problem
or desired outcome. Source-specific downstream pipelines would bind Design and Plan behavior to
the supplier. Sending raw conversation directly to Plan creation would leave unresolved intent,
evidence, feasibility, and user decisions implicit.

## Decision

### Domain model

A **Work Brief** is the supplier-neutral, normalized problem or outcome dataset against which
architecture, design, and planning begin. A **Work Brief source** is the backlog item, conversation,
interview, or brainstorming session from which it is normalized; this source kind is distinct from
a provider's metadata field named `source`.

The proposal uses neither “Design Workbook” nor “fully groomed”: the first adds a second name for
the same object, while the second conflates readiness for Design with readiness to implement.

A Work Brief is distinct from all of these:

- a provider-backed backlog item, which may be its source and storage representation;
- a **Plan**, which decomposes one Work Brief into executable work;
- a **Task**, which is one executable unit in a Plan; and
- a lowercase delegation “brief,” which is the instructions handed to a sub-agent.

Disparate concerns become dependency-linked Work Briefs, rather than unrelated concerns being
hidden as Tasks under one Plan.

**Ready for design** means the Work Brief is sufficiently defined for architecture, design, and
planning: every question or user-addressable blocker required by those stages is resolved and the
user has confirmed shared understanding. Non-blocking unknowns may remain only when recorded as
intentionally unresolved. This readiness gate does not rename backlog status `groomed` or the
RT-ICA decisions `APPROVED-FOR-PLANNING`, `APPROVED-WITH-GAPS`, and
`BLOCKED-FOR-PLANNING`.

### Proposed workflow

```text
conversation or backlog source
→ interactive Work Brief intake
→ persist and verify Work Brief
→ ready for design
→ architecture and design
→ Plan design
→ Task decomposition
→ implement-feature(plan_ref)
```

Normalization is before Design and outside the numbered SAM stages; it is not another execution
stage. The existing Groom Intake keeps its current meaning: eligibility and extraction for an
existing item.

`/dh:work-brief` is the proposed user-invocable ad-hoc entrypoint. It starts an offline, one-off
workflow that follows `/dh:work-backlog-item` while bypassing the configured backend in favor of a
local-only backlog item. It supports developing features, fixing bugs, and changing documentation
in any project without a configured DH backend, and work that should proceed immediately without
first being filed in the configured backlog. The resulting local item follows the ordinary
backlog-item lifecycle. Provider routing remains a separate architectural decision.

Interactive intake scales to the request. It first establishes the observable current problem or
desired outcome and whether the work remains relevant. It then uses only the clarification,
grilling, brainstorming, discovery, research, feasibility checking, examples, constraints, and
validation needed by downstream architecture and planning. A small correction may need little
intake; a cross-system feature may need all of those activities.

### Grilling state and readiness

During interactive intake, the orchestrating agent creates a scratch state file, names its exact
path at the start of every grilling response, and reads and updates it every turn. The state holds:

- settled decisions;
- answered questions and intentionally unresolved questions;
- evidence references; and
- concerns.

The scratch file keeps the question frontier and established state available across turns and
context compaction. Standalone specialist scratch reports may feed the orchestrator during intake,
but they are not expected outputs of the resulting Work Brief.

The persistent Work Brief is created only when its blocking question frontier is empty and the
user confirms shared understanding. The orchestrator writes the terminal grilling state into the
existing `sections["groomed"]` / `GroomedData` content layer. That grooming provenance contains the
settled decisions, answered and intentionally unresolved questions, evidence references, and
concerns consumed by discovery, architecture, and planning.

The orchestrator then reads the persisted content back and verifies complete conversion: every
required part of the terminal grilling state appears without omission, duplication, or speculation.
Only a successful read-back makes the Work Brief ready for design and permits deletion of the
scratch file as a second authority.

When required information is missing, intake records the unanswered questions and ends
`needs-input`; it does not claim readiness. When persistence or read-back fails, intake ends
blocked and preserves the scratch state. After handoff, architecture, Plan design, Task
decomposition, and execution proceed through the common contracts without user interaction unless
a genuine blocker or `needs-input` decision occurs.

## Alternatives considered

- **Source-specific downstream pipelines:** rejected because they duplicate Design and Plan
  behavior and make the supplier part of the domain contract.
- **Provider backlog item as the universal domain object:** rejected because detached local work
  and non-backlog sources remain valid inputs.
- **Raw conversation directly to Plan creation:** rejected because it skips relevance, readiness,
  shared-understanding, and persistence-fidelity gates.
- **A new top-level grooming section or parallel provenance document:** rejected because the
  existing `GroomedData` layer already owns grooming content and a second record can drift.

## Consequences

Every supported source reaches one design boundary, while the existing issue-less Plan capability
remains available. Architecture and planning can consume a verified state record without requiring
access to the original conversation. Intake must preserve resumable state on every non-ready
terminal path.
