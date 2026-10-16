---
name: Task-intent drift prevention for agent workflows
description: Evidence-backed guidance for keeping agent validation and review work tied to the user's original outcome, rather than recursively inventing new gates.
license: Multi-source research synthesis; quoted sources retain their original terms
metadata:
  topic: task-intent-drift-prevention
  category: agent-orchestration
  resource_type: research-synthesis
source_url: https://www.anthropic.com/engineering/building-effective-agents
research_date: "2026-10-14"
version_at_research: "Unversioned research synthesis; the reviewed sources are articles and papers, not one software release. Source access dates are recorded in References."
freshness_tracking:
  last_verified: "2026-10-14"
  version_at_verification: source pages accessed 2026-10-14
  next_review: "2027-01-14"
  confidence_map: "Overview: medium, Evidence Status: medium, Problem Addressed: low (illustrative), Key Features: low (proposed), Technical Architecture: low (proposed), Limitations and Caveats: high, Installation & Usage: low (untested), Compact Acceptance Scenarios: low (untested)"
---

## Overview

This entry addresses task-intent drift in agent work: validation or review expands from the user's requested outcome into a self-justifying chain of new tests, runtime environments, and review passes. The prevention point is earlier than resource cleanup: preserve the original task and acceptance criteria as the authority for admitting work.

A reported local incident motivated this research, but no durable first-party incident record is included in this entry. Treat that account as unverified motivation, not a confirmed local root-cause finding. The scenario below illustrates the proposed failure mode; it is not a reproduced incident.

## Evidence Status

| Claim | Status | Basis and limit |
| --- | --- | --- |
| A local incident followed the failure mode described below. | Unverified report | No durable first-party incident record is published with this entry; the scenario is illustrative and was not independently reproduced. |
| Explicit skill invocation does not itself require an automatic-discovery test. | Proposed routing principle | A direct `/<skill>` route identifies the intended skill. Discovery may still be relevant when an applicable product contract requires autonomous routing. |
| An evaluator loop needs stated criteria and measurable value. | Supported by source | Anthropic presents evaluator-optimizer loops as suitable when evaluation criteria are clear and refinement has measurable value. This is engineering guidance, not a universal rule. |
| Long-running agents can drift from their original objective. | Supported by controlled research | Arike et al. show goal drift under their simulated conditions. The study does not measure this repository or PR-review workflows. |
| Multi-agent systems exhibit specification, alignment, and verification/termination failure modes. | Supported by empirical taxonomy | Cemri et al. studied traces from several frameworks. The taxonomy identifies a relevant failure class; it does not prove any particular local review loop will recur. |
| Existing task/backlog acceptance criteria and review/delegation reports can prevent this incident class. | Proposed | This entry recommends the workflow; it neither implements the safeguards nor provides empirical evidence of their effectiveness. |
| Disk, memory, and cleanup controls prevent task-intent drift. | Not supported | They contain consequences after bad work is admitted. They do not determine whether the work belongs to the task. |

## Problem Addressed

The failure mode considered here is not simply excessive scratch usage. The following illustrative scenario starts when an agent or reviewer treats a method suggestion as a new acceptance requirement:

1. The user asks for a directed action and named outcome.
2. A reviewer adds an unrequested proof obligation, such as automatic discovery for an explicit route.
3. The new obligation generates another test or harness.
4. Reviews begin evaluating that harness, producing further obligations unrelated to the original outcome.
5. Disposable environments and evidence accumulate around the invented branch.

Repository instructions, skills, and review output remain important, but they do not replace the user task. They can constrain the requested work through an applicable safety, data-loss, or source-contract concern. They do not create a new blocking product requirement merely because a broader experiment would be useful.

## Key Features

### Acceptance provenance

Use the existing backlog item's acceptance criteria, approved plan, and direct user request as the task's source of truth. Before new work begins, record the specific criterion or applicable contract it serves in the existing task, delegation, or review report.

A blocking finding must name all of the following:

- the existing acceptance criterion or applicable source contract;
- observed evidence;
- concrete impact on the user outcome, safety, data, or contract;
- the smallest correction; and
- a concrete verification method, followed by observed verification after a correction exists.

Unknown criterion identifiers do not prove that a concern is irrelevant. A reviewer may block for a directly applicable security, data-loss, or correctness contract when it shows the concrete impact. Suggestions without that connection remain advisory and must not start a new test, subtask, or merge block.

### Admission and reviewer authority

Treat an explicit skill or command as a route selection. Validate the requested artifact, caller link, parser, or tool outcome unless the task or an applicable contract names automatic discovery as behavior to prove.

Reviewers may identify evidence and recommend a correction. The task owner changes the goal, acceptance criteria, interface, or user-visible deliverable. Agents retain ordinary implementation discretion within those boundaries; this is not a requirement to seek user approval for routine technical choices.

### Progress-based loop termination

Reassess the original outcome before each new branch of work. Continue only when new source evidence or a source change bears on an existing criterion or applicable contract. New evidence on unchanged source can be valid when it supplies that connection; an arbitrary one-pass rule would hide such findings.

Stop a branch when its remaining purpose is proving a newly invented test or harness rather than the original outcome. If a criterion cannot be proven with available evidence, report it as `evidence-limited` with the missing observation and user-facing qualification. Do not call it complete or fabricate a pass.

### Secondary resource containment

Only after a runtime-level criterion is admitted should a separate containment policy apply. This is proposed containment, not current repository behavior or tested enforcement. Reuse immutable source references and installed runtimes; retain the compact receipt, logs, and source references needed for the claim rather than full runnable copies. Aggregate any resource budget across the parent task, workers, retries, and reviewers, rather than giving each worker an independent allowance.

This is a mitigation, not a guarantee. Disk quotas and cgroups constrain different resources; tmpfs consumes RAM and possibly swap, so it is not a fallback staging area. Cleanup hooks and `finally` blocks do not cover host crashes. A janitor must use ownership and liveness, never age alone. Enforcement also depends on the actual harness restricting writable paths and launching work through the limiter; it cannot be claimed where the systemd user bus is unavailable, quotas are absent, or an unrestricted agent can write elsewhere.

## Technical Architecture

No new task-charter command, runtime gate, or quota tool is proposed by this entry. Apply the checks at existing seams:

| Existing artifact | Addition to record | Decision |
| --- | --- | --- |
| Backlog item or approved plan | The criterion or contract that admits the next action | Does this action advance the requested outcome? |
| Delegation request | The named outcome, criterion, and explicit route | Is the delegated scope bounded to the task? |
| Review report | Evidence, impact, smallest correction, verification, and scope status | Is the finding blocking or advisory? |
| Completion/PR report | Criteria proved, not applicable with evidence, or evidence-limited | Is the result truthful about remaining limits? |

Mechanical schemas can require these references and fields, but they cannot decide semantic relevance or prove alignment. Human or task-owner judgment remains necessary for conflicts between the requested outcome and an applicable contract.

## Limitations and Caveats

- No durable first-party record accompanies the reported local incident; it is motivation, not a reproduced causal finding.
- The cited studies and case studies concern their own settings. They do not measure this repository or establish the effectiveness of the proposed safeguards here.
- The procedures and acceptance scenarios below are proposals, not observed runtime results. This entry neither implements enforcement nor establishes cost, resource, or correctness guarantees.
- Resource containment depends on the actual host and harness boundaries. Cleanup handlers do not cover every termination mode, and no containment implementation is validated by this research.

## Installation & Usage

Use the pattern on the next task without new infrastructure:

1. Read the requested deliverable and the existing backlog/plan acceptance criteria before choosing validation.
2. Select the cheapest direct check that can distinguish the requested behavior from failure.
3. When delegating or reviewing, require the report to connect each blocking action to a criterion or applicable contract and its concrete impact.
4. Re-read that connection before adding another reviewer, test, runtime, or environment. Record unrelated improvements as advisory follow-ups.
5. Close only after every relevant criterion has direct evidence, an evidence-backed non-applicability decision, or an explicit evidence limit.

## Compact Acceptance Scenarios

| Scenario | Expected result |
| --- | --- |
| User explicitly invokes a review skill and requests prose/tool validation. | Check the prose, route, and named tool behavior; do not require automatic discovery or a native-agent environment. |
| A reviewer finds a broken changed link tied to a stated documentation criterion. | It blocks until the smallest link correction and focused link check succeed. |
| A reviewer finds a data-loss or security concern on unchanged source. | It can block when it cites the applicable contract and concrete harm; unchanged source alone is not a dismissal. |
| A reviewer requests a runtime matrix with no connection to a criterion or contract. | Record it as advisory; do not create a subtask, environment, or merge gate. |
| Fresh evidence on unchanged source contradicts an existing criterion. | Admit a targeted investigation because it can change the original outcome. |
| A proposed branch now only tests the harness created by an earlier review. | Stop it and report that it no longer advances the original task. |
| A required criterion lacks a discriminating observation. | Mark it evidence-limited and qualify the result; do not report completion. |
| An admitted runtime task is cancelled or a worker fails. | Preserve a compact receipt and clean only owner-registered disposable state; do not create sibling copies or use RAM staging. |

The last scenario describes an untested mitigation target. A future implementation would need small controlled checks of cancellation, failed setup, and sibling isolation before claiming those safeguards work; this research entry supplies no such result and does not require building that implementation.

## References

- Anthropic, "Building effective agents" — “finding the simplest solution possible, and only increasing complexity when needed”; evaluator-optimizer loops fit when there are “clear evaluation criteria” and refinement has measurable value. <https://www.anthropic.com/engineering/building-effective-agents> (accessed 2026-10-14)
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world" — “Humans steer. Agents execute.” It describes humans translating user feedback into acceptance criteria and validating outcomes. <https://openai.com/index/harness-engineering/> (accessed 2026-10-14)
- Birgitta Böckeler, "Harness engineering for coding agent users" — computational controls are “deterministic and fast”; inferential controls are “slower and more expensive.” The article says neither reliably catches “overengineering and unnecessary features” or “misunderstood instructions.” <https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html> (accessed 2026-10-14)
- Rauno Arike, Elizabeth Donoway, Henning Bartsch, and Marius Hobbhahn, "Evaluating Goal Drift in Language Model Agents" — the abstract defines goal drift as “an agent’s tendency to deviate from its original objective over time”; the paper gives an AI-coding example of expanding into forbidden directories. <https://doi.org/10.1609/aies.v8i1.36541> (accessed 2026-10-14)
- Mert Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" — the abstract groups failure modes into “(i) specification and system design failures, (ii) inter-agent misalignment, and (iii) task verification and termination.” <https://arxiv.org/html/2503.13657v1> (accessed 2026-10-14)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Harness Engineering (Martin Fowler / Birgitta Böckeler)](../evaluation-testing/harness-engineering-martin-fowler.md) | evaluation-testing | distinguishes deterministic enforcement from inferential review and their limits |
| [Harness Engineering: Leveraging Codex in an Agent-First World](../evaluation-testing/harness-engineering-openai.md) | evaluation-testing | supplies the human-steering and repository-harness case study cited in the scope discussion |
