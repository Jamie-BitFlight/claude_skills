---
name: Task-intent drift prevention for agent workflows
description: Source-bounded synthesis of agent goal drift, evaluator feedback loops, and human steering; distinguishes published findings from unproven prevention claims.
license: Multi-source research synthesis; quoted sources retain their original terms
metadata:
  topic: task-intent-drift-prevention
  category: agent-orchestration
  resource_type: research-synthesis
source_url: https://www.anthropic.com/engineering/building-effective-agents
research_date: "2026-10-14"
version_at_research: "Unversioned synthesis of articles and papers, not one software release; publication and access dates are recorded in References."
freshness_tracking:
  last_verified: "2026-10-16"
  version_at_verification: "Engineering articles read in full; goal-drift publisher abstract and MASFT v1 abstract/introduction reviewed on 2026-10-16."
  next_review: "2027-01-16"
  confidence_map: "Overview: low (mixed dated sources), Evidence Status: low (mixed dated and abstract-only sources), Problem Addressed: low (dated abstract-only studies), Key Features: low (mixed dated sources), Technical Architecture: low (dated Anthropic source), Limitations and Caveats: low (mixed dated sources), Installation & Usage: low (dated Anthropic example)"
---

## Overview

This synthesis compares published work on agent goal drift, multi-agent verification failures, evaluator feedback loops, and human steering. It summarizes the sources and their documented examples; it does not prescribe repository-specific policy or introduce a validated prevention method.

The sources distinguish task success from the mere presence of tests or review loops. Anthropic recommends adding complexity only when it demonstrably improves outcomes; Böckeler identifies misunderstood instructions and unnecessary features as problems that neither computational nor inferential controls reliably catch.

## Evidence Status

| Source | Material reviewed | What it supports | Boundary |
|--------|-------------------|------------------|----------|
| Anthropic, *Building effective agents* | Full engineering article | Workflow patterns, evaluator-optimizer fit, and simplicity/cost tradeoffs | Engineering guidance, not a universal effectiveness study |
| OpenAI, *Harness engineering* | Full engineering case study | Human steering, repository-local knowledge, and feedback loops in the authors' product | The authors explicitly limit generalization beyond their environment |
| Böckeler, *Harness engineering for coding agent users* | Full article | Feedforward/feedback and computational/inferential control distinctions | A mental model, not a controlled benchmark |
| Arike et al., *Evaluating Goal Drift in Language Model Agents* | Publisher abstract | Goal drift under competing environmental objectives | Methods and results beyond the abstract were not reviewed |
| Cemri et al., *Why Do Multi-Agent LLM Systems Fail?* | v1 abstract and introduction | An empirical failure taxonomy including verification and termination | Not an independently reproduced result or an exhaustive failure taxonomy |

No first-party incident record or repository-specific diagnosis is used as evidence in this entry.

## Problem Addressed

Arike et al. define goal drift as an agent deviating from its original objective over time. Their publisher abstract describes giving agents a goal in the system prompt and exposing them to competing environmental objectives. It reports nearly perfect adherence for more than 100,000 tokens by a scaffolded Claude 3.5 Sonnet agent in the hardest setting, while all evaluated models exhibited some drift. These are findings within that study, not measured failure rates for coding repositories.

Cemri et al.'s v1 abstract reports analysis of 5 multi-agent frameworks across over 150 tasks with 6 expert annotators. It identifies 14 failure modes grouped into 3 categories: specification/system-design failures, inter-agent misalignment, and task verification/termination. The reported Cohen's kappa is 0.88. The introduction explicitly does not claim that the taxonomy covers every possible failure pattern.

Together, these studies identify failure classes relevant to long-running or multi-agent work. They do not establish that any particular review procedure prevents those failures.

## Key Features

### Simplicity and measurable refinement

Anthropic recommends the simplest adequate solution and notes that agentic systems trade latency and cost for performance. Its evaluator-optimizer pattern is a good fit when evaluation criteria are clear and iterative refinement provides measurable value. The article does not make repeated review an unconditional requirement.

### Different controls answer different questions

Böckeler distinguishes guides that act before an agent from sensors that observe its output afterward. Computational controls include deterministic tests, linters, and structural checks; inferential controls include model-based review and semantic judgment. The article says neither reliably catches misunderstood instructions, overengineering, or unnecessary features, and emphasizes human specification and steering.

### Human steering in a documented case

OpenAI describes engineers prioritizing work, translating feedback into acceptance criteria, and validating outcomes while agents use development tools and respond to reviews. The article also describes agent-to-agent review loops, versioned plans, and repository-local documentation. Those are practices reported by its team, not evidence that copying the entire environment is necessary or sufficient elsewhere.

## Technical Architecture

Anthropic's evaluator-optimizer workflow has a response-generating LLM call and another call that evaluates the response and returns feedback. The feedback informs another refinement of the response. Its documented mechanism is a generation/evaluation feedback loop, not a task store, publication service, or new evidence schema.

The article distinguishes predefined workflows from agents that dynamically choose their process and tools. For autonomous agents it discusses environmental ground truth, human checkpoints, and stopping conditions. It does not prescribe one universal iteration limit for every evaluator-optimizer use case.

## Limitations and Caveats

- The goal-drift paper was reviewed through its publisher abstract, and the multi-agent study through its v1 abstract/introduction. No independent reproduction or full-method assessment is claimed.
- The engineering articles are guidance and a case study, not controlled evidence that a specific task-admission policy prevents drift.
- Böckeler explicitly describes limits in detecting misdiagnosis, misunderstood instructions, and unnecessary features; a green test or review signal is not a general alignment guarantee.
- Anthropic's article was published in December 2024 and now notes that the tooling landscape has changed. This synthesis concerns its workflow patterns, not current SDK or API configuration.
- OpenAI states that its autonomous workflow depends heavily on its environment and should not be assumed to generalize without similar investment. Its authors also identify long-term architectural coherence as an open question.
- No resource limiter, cleanup mechanism, local incident diagnosis, or repository-specific operating procedure is implemented or validated by this research.

## Installation & Usage

There is no software package or installation command for this collection of articles and papers.

A documented usage example is Anthropic's literary-translation evaluator-optimizer case. In a minimal adaptation of that description:

1. The generator produces a translation.
2. The evaluator critiques nuances that the first response did not capture.
3. That feedback informs refinement of the translation.

Source: [Anthropic, *Building effective agents*, evaluator-optimizer section](https://www.anthropic.com/engineering/building-effective-agents). The article supplies this use case and the generator/evaluator mechanism; the steps above do not claim a tested prompt, a universal stopping rule, or a local implementation.

## References

- Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), published 2024-12-19; current article read in full, including its changed-tooling notice (accessed 2026-10-16).
- OpenAI / Ryan Lopopolo, [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/), published 2026-02-11; full case study reviewed (accessed 2026-10-16).
- Birgitta Böckeler, [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html), published 2026-04-02; full article reviewed. The former `exploring-gen-ai/harness-engineering.html` URL redirects here (accessed 2026-10-16).
- Rauno Arike, Elizabeth Donoway, Henning Bartsch, and Marius Hobbhahn, [Evaluating Goal Drift in Language Model Agents](https://doi.org/10.1609/aies.v8i1.36541), AIES, published 2025-10-15; publisher abstract retrieved through DOI/CrossRef metadata, not full-paper methods (accessed 2026-10-16).
- Mert Cemri et al., [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/html/2503.13657v1), arXiv:2503.13657v1, 2025-03-17; abstract/introduction reviewed, not the full paper (accessed 2026-10-16).

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Harness Engineering (Martin Fowler / Birgitta Böckeler)](../evaluation-testing/harness-engineering-martin-fowler.md) | evaluation-testing | distinguishes computational and inferential controls and their limits |
| [Harness Engineering: Leveraging Codex in an Agent-First World](../evaluation-testing/harness-engineering-openai.md) | evaluation-testing | documents the human-steering and repository-harness case study summarized here |
