---
name: Harness Engineering (Martin Fowler / Birgitta Böckeler)
description: "\"Harness Engineering\" is a memo by Birgitta Böckeler, a Distinguished Engineer at Thoughtworks, published as part of Martin Fowler's \"Exploring Gen AI\" series. It analyzes and contextualizes the..."
license: Copyright Martin Fowler (all rights reserved; article content)
metadata:
  topic: harness-engineering-martin-fowler
  category: evaluation-testing
  source_url: https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html
  version: "N/A"
  verified: "2026-02-21"
  next_review: "2026-05-21"
---

## Overview

"Harness Engineering" is a memo by Birgitta Böckeler, a Distinguished Engineer at Thoughtworks, published as part of Martin Fowler's "Exploring Gen AI" series. It analyzes and contextualizes the concept of building deterministic and LLM-based infrastructure (a "harness") to constrain, guide, and verify AI coding agents during both code generation and maintenance. The article synthesizes insights from OpenAI's production experience with Codex agents, Mitchell Hashimoto's blog, and Chad Fowler's "Relocating Rigor" to argue that trustworthy AI-maintained codebases require deliberately constrained solution spaces—not unconstrained generation.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI agents repeat mistakes and have no feedback loop for self-correction | Build a harness: programmatic tools (linters, structural tests, AGENTS.md) that prevent the agent from repeating known-bad behaviors |
| LLM-generated code decays over time due to inconsistent architectural adherence | Periodic "garbage collection" agents detect and fix inconsistencies; deterministic constraints enforce structure continuously |
| Trusting AI-generated code at scale requires wide flexibility, which reduces reliability | Constrain the solution space intentionally: specific architectural patterns, enforced module boundaries, and standardized structures increase reliability |
| Existing codebases are hard to retroactively harness | Harness design is most effective when designed from the start; retrofitting an existing codebase is comparable to running a static analyzer for the first time on an unchecked codebase |
| Context for AI agents degrades without maintenance | Continuously updated knowledge bases and dynamic context providers (observability data, browser navigation) supply fresh, accurate context |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Article published | 17 February 2026 | 2026-02-21 |
| Author count | 1 (Birgitta Böckeler) | 2026-02-21 |
| Series article count | ~22 articles (Exploring Gen AI series) | 2026-02-21 |
| OpenAI harness codebase size cited | 1 million+ lines of code after 5 months | 2026-02-21 |
| OpenAI harness build duration cited | 5 months | 2026-02-21 |

---

## Key Features

### Core Harness Component Model (from OpenAI, interpreted by Böckeler)

- **Context Engineering**: Continuously maintained knowledge base embedded in the codebase; agents given dynamic context including observability data and browser navigation access
- **Architectural Constraints**: Enforced by both LLM agents and deterministic custom linters; structural tests enforce module boundaries and data shape contracts
- **Garbage Collection Agents**: Periodic agentic jobs that detect documentation inconsistencies and constraint violations, actively fighting entropy

### Harness as Forcing Function

- Teams use "no manually typed code" as a discipline to reveal where agents fail—each failure becomes a harness improvement task
- Iterative improvement loop: agent struggle signals missing tools, guardrails, or documentation; those gaps are closed by having the AI agent itself write the fix
- Harness components are the primary focus of engineering effort, not application feature code

### Conceptual Framework Contributions

- Böckeler introduces "harness" as a preferred term over alternatives (test harness, agent scaffolding, etc.) for tooling and practices that keep AI agents in check
- Proposes harnesses as the successor to service templates on "golden paths"—prebuilt harnesses for common application topologies
- Raises the distinction between pre-AI applications (where retrofitting may be cost-prohibitive) and post-AI applications (designed from the start for harness-based maintenance)
- Notes that what is good for human developers is repeatedly shown to be good for AI agents (usability of frameworks and SDKs)

### Constraints as a Design Principle

- Increasing AI autonomy requires decreasing solution space flexibility: specific architectural patterns, stable data structures, enforced module boundaries
- Convergence toward fewer tech stacks and topologies is predicted as a side effect of prioritizing "AI-friendliness" in stack selection
- Böckeler contrasts this with the industry hype that LLMs enable unlimited runtime flexibility

---

## Technical Architecture

The harness engineering pattern comprises three layers, based on Böckeler's categorization of the OpenAI team's approach:

<eg>
+-----------------------------------------------------------+
|                  AI Coding Agent (e.g., Codex)            |
+-----------------------------------------------------------+
          |                    |                   |
          v                    v                   v
+------------------+  +------------------+  +-------------------+
| Context Layer    |  | Constraint Layer |  | Entropy-Fighting  |
| - Knowledge base |  | - Custom linters |  | Agents (GC)       |
|   (curated docs) |  | - Structural     |  | - Doc consistency |
| - Observability  |  |   tests          |  | - Constraint      |
|   data access    |  | - Module boundary|  |   violation scan  |
| - Browser nav    |  |   enforcement    |  | - Periodic runs   |
+------------------+  +------------------+  +-------------------+
          |                    |                   |
          +--------+-----------+-------------------+
                   v
          +------------------+
          | Harness Feedback |
          | Loop             |
          | Agent fails -->  |
          | identify gap --> |
          | agent writes fix |
          +------------------+
</eg>

The harness is not a single tool but a system of deterministic checks (linters, structural tests) and LLM-based agents (context providers, garbage collectors) working together. Deterministic components provide reliable guardrails; LLM agents handle semantic checks and adaptive maintenance.

---

## Installation & Usage

This is an article, not a software package. Key actionable patterns derived from the content:

**Assessing your current harness (from article's "What's your harness today?" section):**

- Audit existing pre-commit hooks: what behaviors do they enforce?
- Identify custom linter opportunities for architectural constraints
- Define explicit architectural constraints you want enforced
- Evaluate structural testing frameworks such as ArchUnit (Java) for boundary enforcement

**Harness improvement loop:**

<eg>
1. Observe agent mistake
2. Identify what is missing: tools, guardrails, documentation
3. Add the missing element to the harness (preferably via the agent itself)
4. Verify the agent no longer makes that class of mistake
5. Repeat
</eg>

**Harness component checklist (derived from OpenAI case study):**

- AGENTS.md (or equivalent): behavioral instructions to prevent known failure modes
- Custom linters: encode architectural rules as static analysis
- Structural tests: enforce module boundaries and data shape contracts at build time
- Observability integration: give agents access to runtime data for self-diagnosis
- Garbage collection agents: schedule periodic consistency checks

---

## Relevance to Claude Code Development

### Applications

- Claude Code skill development benefits directly from harness thinking: CLAUDE.md files, pre-commit hooks, and validation scripts are components of a harness for Claude agents
- The iterative feedback loop (agent fails -> identify gap -> add to harness) maps directly to how Claude Code skills and AGENTS.md files should be maintained and improved
- The distinction between deterministic constraints (linters, structural tests) and LLM-based checks (garbage collection agents) informs how to layer Claude Code validation infrastructure

### Patterns Worth Adopting

- **Harness-first development**: when building new Claude Code workflows, define the harness (validation, structural tests, AGENTS.md constraints) before or alongside the workflow itself
- **Failure-as-signal**: when Claude Code makes a class of mistake, treat it as a gap in the harness rather than a one-off correction; fix the harness so the mistake cannot recur
- **Periodic entropy agents**: schedule or trigger agents to check for consistency violations in documentation, skill files, and manifest files (analogous to garbage collection agents)
- **Constraint engineering for reliability**: the article's argument that constrained solution spaces increase trustworthiness applies to Claude Code skill design—narrow scope with explicit constraints produces more reliable agent behavior than open-ended instructions

### Integration Opportunities

- The harness feedback loop could be formalized in Claude Code skill development: validation scripts (`validate_frontmatter.py`, `auto_sync_manifests.py`) are already harness components; extend them to catch more agent failure modes
- ArchUnit-style structural tests for skill file structure and cross-reference integrity would function as a harness for skill authoring agents
- The "harness as service template" concept suggests that Claude Code could offer pre-built harness configurations for common skill development patterns, analogous to the project's existing plugin structure

---

## References

- [Harness Engineering (Birgitta Böckeler, martinfowler.com)](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) (accessed 2026-02-21)
- [Exploring Generative AI series index (martinfowler.com)](https://martinfowler.com/articles/exploring-gen-ai.html) (accessed 2026-02-21)
- [Harness engineering: leveraging Codex in an agent-first world (OpenAI)](https://openai.com/index/harness-engineering/) (referenced in article; JavaScript-rendered, not directly accessible)
- [My AI Adoption Journey — Step 5: Engineer the Harness (Mitchell Hashimoto)](https://mitchellh.com/writing/my-ai-adoption-journey#step-5-engineer-the-harness) (accessed 2026-02-21)
- [Relocating Rigor (Chad Fowler, The Phoenix Architecture)](https://aicoding.leaflet.pub/3mbrvhyye4k2e) (accessed 2026-02-21)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [research-mode](../ai-observability/research-mode.md) | ai-observability | referenced by research-mode (ai-observability) |
| [meta-harness](../ai-research-tools/meta-harness.md) | ai-research-tools | referenced by meta-harness (ai-research-tools) |
| [agent-skills-eval](./agent-skills-eval.md) | evaluation-testing | referenced by agent-skills-eval (evaluation-testing) |
| [TheAlgorithms-Python](../learning-resources/TheAlgorithms-Python.md) | learning-resources | referenced by TheAlgorithms-Python (learning-resources) |
