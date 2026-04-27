# mattpocock/skills

**Resource**: Agent Skills for Real Engineers (Matt Pocock's Claude Code Skills Collection)

**Repository**: <https://github.com/mattpocock/skills>

**Primary Language**: Shell (distribution scripts)

**License**: MIT (Copyright 2026 Matt Pocock)

---

## Overview

mattpocock/skills is a curated collection of 21 specialized Claude Code skills authored by Matt Pocock for professional software engineering tasks. Rather than general-purpose abilities, each skill encodes a specific engineering discipline or workflow pattern that Pocock uses daily in production development. The repository describes itself as "Agent Skills for real engineers. Straight from my .claude directory," emphasizing practical, battle-tested patterns over hypothetical capabilities.

The skills cover four primary domains: **Planning & Design** (architectural thinking, requirement specification), **Development** (test-driven development, code refactoring, bug investigation), **Tooling & Setup** (git safety guardrails, pre-commit configuration), and **Writing & Knowledge** (article editing, domain glossaries, note management in Obsidian vaults).

---

## Problem Addressed

Software engineers using Claude Code often face friction between **high-level conversation** and **structured, repeatable engineering workflows**. General-purpose AI agents excel at discussing problems but may lack discipline around:

1. Interface design (exploring alternatives before committing to one approach)
2. Test-first development (resisting the urge to write all tests first, then all code)
3. Architectural deepening (identifying shallow modules and increasing leverage)
4. Git safety (preventing destructive git operations in automated flows)
5. Specification capture (converting conversation into formal requirements documents)

mattpocock/skills addresses this gap by encoding **specific engineering practices as reusable, discoverable skills**. Each skill is self-contained, has explicit activation triggers, embeds anti-patterns and checklist guidance, and includes reference materials (e.g., "How to Mock Effectively," "When to Extract Deep Modules"). The repository serves as both a personal knowledge base and a distribution mechanism for others to adopt Pocock's engineering discipline.

---

## Key Statistics

- **23,883 stars** (as of 2026-04-27)
- **1,936 forks** (as of 2026-04-27)
- **Repository created**: 2026-02-03
- **Last updated**: 2026-04-27 (very recent — active maintenance)
- **21 distinct skills** in organized directories
- **60,000+ subscribers** to associated newsletter (mentioned in README)

---

## Key Features

### Skill Categories and Examples

1. **Planning & Design** (5 skills)
   - `to-prd`: Converts conversation context into a formal PRD and files it as a GitHub issue. Does not interview; synthesizes existing discussion. Template includes Problem Statement, Solution, extensive User Stories, Implementation Decisions, Testing Decisions, and Out of Scope.
   - `design-an-interface`: Applies "Design It Twice" pattern—generates 3+ radically different module interface options via parallel sub-agents, then compares on simplicity, flexibility, efficiency, and depth (small interface hiding large complexity vs. large interface with thin implementation).
   - `grill-me`: Conducts relentless interview-style questioning about a plan or design until every branch of the decision tree is resolved.
   - `to-issues`: Breaks plans into independently-grabbable GitHub issues using vertical slices.
   - `request-refactor-plan`: Creates detailed refactor plans with commit-sized steps via user interview, files as GitHub issue.

2. **Development** (6 skills)
   - `tdd`: Test-driven development with explicit red-green-refactor loops. Core teaching: **vertical slices via tracer bullets, not horizontal slicing**. One test → one implementation → repeat. Prevents writing all tests first (imagined behavior) then all code. Includes embedded references: tests.md, mocking.md, refactoring.md, interface-design.md, deep-modules.md.
   - `triage-issue`: Investigates bugs by exploring codebase, identifies root cause, files GitHub issue with TDD-based fix plan.
   - `improve-codebase-architecture`: Finds deepening opportunities—refactors that turn shallow modules (interface complexity ≈ implementation complexity) into deep ones (small interface hiding significant complexity). Uses domain-aware language from CONTEXT.md and decisions from docs/adr/ to avoid re-litigating settled choices. Teaches deletion test: would removing this module concentrate complexity or just move it?
   - `qa`: Quality assurance skill (specific content not examined in depth).
   - `migrate-to-shoehorn`: Automates migration from TypeScript `as` type assertions to @total-typescript/shoehorn library.
   - `scaffold-exercises`: Creates exercise directory structures with sections, problems, solutions, and explainers (used for teaching/knowledge capture).

3. **Tooling & Setup** (2 skills)
   - `setup-pre-commit`: Configures Husky pre-commit hooks with lint-staged, Prettier, type checking, and tests in one operation.
   - `git-guardrails-claude-code`: Sets up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, etc.) before execution.

4. **Writing & Knowledge** (4 skills)
   - `write-a-skill`: Creates new skills with proper structure, progressive disclosure, and bundled resources (teaches skill authoring discipline).
   - `edit-article`: Restructures, clarifies, and tightens prose in articles.
   - `ubiquitous-language`: Extracts a Domain-Driven Design (DDD) ubiquitous language glossary from conversation.
   - `obsidian-vault`: Searches, creates, and manages notes in Obsidian vaults with wikilinks and index notes.

5. **Additional Skills**
   - `domain-model`: Supports domain-driven design patterns (CONTEXT.md format, ADR format).
   - `github-triage`: GitHub issue triage (detailed content not examined).
   - `caveman`: (Purpose not clear from directory alone; contains SKILL.md requiring deeper read).
   - `zoom-out`: (Purpose not clear; file present but not examined in depth).

### Consistent Skill Structure

Every skill follows this architecture:

- **Frontmatter** (YAML): `name` (matches directory), `description` (includes trigger keywords and use cases)
- **Markdown body**: Philosophy, anti-patterns, workflow steps with checkpoints, evaluation criteria, examples
- **Embedded reference files**: Thematic deep-dives (e.g., tdd/mocking.md covers when to mock vs. integration test)
- **Progressive disclosure**: Core philosophy first, then detailed workflow, then checklists and evaluation criteria

Example from `tdd/SKILL.md`:
- Philosophy section establishes principle: "tests verify behavior through public interfaces, not implementation"
- Anti-Pattern section explicitly warns against horizontal slicing
- Workflow section breaks down planning → tracer bullet → loop → refactor
- Checklist per cycle ensures each RED-GREEN-REFACTOR iteration follows discipline

### Key Architectural Principles Across Skills

1. **Vertical Slices Over Horizontal**: tdd, to-issues, design-an-interface all teach decomposing work into thin, complete end-to-end slices rather than layers.
2. **Deep Modules Over Shallow**: improve-codebase-architecture, design-an-interface both teach maximizing leverage (small interface, large hidden complexity).
3. **Behavior-Driven Testing**: tdd emphasizes integration-style tests through public APIs, not mocking internals.
4. **Explicit Language**: improve-codebase-architecture requires using consistent vocabulary (module, interface, implementation, depth, seam, adapter, leverage, locality) to avoid drift.
5. **Domain Awareness**: improve-codebase-architecture integrates CONTEXT.md (domain model) and docs/adr/ (architectural decisions) so refactoring respects project semantics.
6. **Parallel Sub-Agents for Exploration**: design-an-interface spawns 3+ sub-agents simultaneously with different constraints to generate radically different interface options.

---

## Technical Architecture

### Distribution and Activation

Skills are distributed via npm package `skills`:

```bash
npx skills@latest add mattpocock/skills/to-prd
npx skills@latest add mattpocock/skills/tdd
```

Installation downloads the skill from GitHub and registers it with Claude Code's local skill registry.

### Skill File Format

Each skill is a directory containing:

- **SKILL.md**: Main skill definition with frontmatter, philosophy, workflow, checklists
- **Reference files** (optional): Thematic guides (e.g., mocking.md, interface-design.md) providing deeper context
- **Support files** (optional): ADR templates, context format guides, agent briefs

Example (tdd skill):
```
tdd/
├── SKILL.md           # Core skill with philosophy and workflow
├── deep-modules.md    # Reference: how to identify and design deep modules
├── interface-design.md # Reference: designing testable interfaces
├── mocking.md         # Reference: when to mock vs. integration test
├── refactoring.md     # Reference: refactoring patterns
└── tests.md           # Reference: writing good tests
```

### Frontmatter Schema

```yaml
---
name: to-prd
description: Turn the current conversation context into a PRD and submit it as a GitHub issue. Use when user wants to create a PRD from the current context.
---
```

Fields:
- `name`: Lowercase, hyphenated, matches directory name
- `description`: Trigger keywords and activation conditions (used by Claude to decide when to load the skill)

### Content Discipline

Skills are **AI-facing instruction sets**, not user documentation. They encode:

1. **Philosophy**: Why this pattern matters (e.g., "tests should verify public behavior, not implementation")
2. **Workflow**: Step-by-step process with decision points
3. **Anti-Patterns**: Explicit warnings against common mistakes
4. **Checklists**: Verification points per cycle/iteration
5. **Evaluation Criteria**: How to recognize when the pattern is working
6. **References**: Embedded guides for deeper topics

This structure enables Claude (the orchestrator) to:
- Load the skill when activation conditions match
- Apply the workflow step-by-step
- Verify work against checklists
- Delegate sub-tasks to specialist agents with clear guidance

### Integration with GitHub

Many skills produce GitHub artifacts:
- `to-prd` files PRDs as GitHub issues
- `to-issues` breaks specifications into issues with vertical-slice structure
- `request-refactor-plan` files refactor plans as issues
- `triage-issue` files bug reports with TDD-based fix plans

Skills assume access to the git repository and GitHub API (via `gh` CLI).

### Integration with Domain-Driven Design

`improve-codebase-architecture` integrates with:
- **CONTEXT.md**: Domain-aware vocabulary (names concepts, defines seams)
- **docs/adr/**: Architectural decision records (avoid re-litigating settled choices)
- **LANGUAGE.md**: Consistent terminology (module, interface, implementation, depth, seam, adapter, leverage, locality)

This enables architectural discussions to ground in project semantics, not generic technology names.

---

## Installation & Usage

### Quick Start

```bash
# Install a skill
npx skills@latest add mattpocock/skills/tdd

# The skill is now registered with Claude Code
# Load it in a session using: /mattpocock-skills:tdd (or similar activation syntax)
```

### Usage Pattern

1. Activate the skill in a Claude Code session (e.g., asking for TDD help activates `tdd` skill)
2. Claude loads the skill file and follows the workflow
3. Skill provides checklists, anti-patterns, and decision points
4. Workflow produces artifacts (code, tests, GitHub issues, architectural plans)

Example TDD workflow:
```
Planning → Review requirements with user, list behaviors to test, get approval
Tracer Bullet → RED: one test, GREEN: minimal code, REFACTOR: improve
Loop → Repeat until all behaviors tested
Refactor → Extract duplication, deepen modules, apply SOLID where natural
```

### Newsletter and Community

Pocock maintains ~60,000 subscriber newsletter for skill updates: <https://www.aihero.dev/s/skills-newsletter>

---

## Limitations and Caveats

### Scope Limitations

Skills are domain-specific and workflow-oriented. They assume:

1. **Existing repository context**: Skills like `improve-codebase-architecture` and `triage-issue` require reading existing code; they do not generate projects from scratch.

2. **GitHub integration**: `to-prd`, `to-issues`, `triage-issue`, `request-refactor-plan` all file GitHub artifacts. They require GitHub authentication and repository access.

3. **JavaScript/TypeScript focus**: Multiple skills (`migrate-to-shoehorn`, `scaffold-exercises`) target JavaScript/TypeScript ecosystems. Python/Go/Rust support not evident from documentation.

4. **Manual verification requirement**: Skills like `tdd` require user confirmation and guidance; they do not operate fully autonomously. User must review designs, approve plans, and confirm test behavior before implementation proceeds.

5. **Incomplete implementation guidance**: `improve-codebase-architecture` surfaces candidates for deepening but defers actual interface design to separate `design-an-interface` skill. No single skill covers architecture → implementation end-to-end.

### Design Trade-Offs

1. **Vertical Slices Only**: `tdd` explicitly forbids horizontal slicing (all tests first, then all code). This is correct for behavior-driven development but conflicts with some test-framework conventions (snapshot testing, fixture preparation) where test structure itself is meaningful.

2. **Deep Modules as Universal Good**: `improve-codebase-architecture` treats depth (small interface, large complexity) as universally desirable. Real systems have legitimate shallow modules (adapters, pass-throughs); depth is leverage only when callers benefit from hidden complexity. This nuance is noted in reference material but not fully explored in skill body.

3. **Mocking Anti-Pattern**: `tdd` promotes integration testing over mocking. This is sound for behavior-driven testing but creates challenges in large systems where true integration tests are slow or have external dependencies. `mocking.md` reference provides nuance, but the skill body leads with integration-only messaging.

4. **Sequential Planning**: `to-prd`, `to-issues`, `request-refactor-plan` assume upfront planning in conversation. In iterative development, plans evolve as code reveals assumptions. These skills do not teach mid-project plan revision.

### Known Gaps (Not Documented)

1. **Async/Concurrency**: No skill for async programming patterns, concurrent testing, race condition debugging, or performance profiling.

2. **Documentation**: No skill for API documentation, README writing, changelog management, or architectural decision recording (ADR-aware, but ADR-authoring not present).

3. **Security**: No skill for security review, vulnerability auditing, threat modeling, or cryptographic pattern recognition.

4. **Performance Optimization**: No skill for profiling, optimization, load testing, or resource efficiency patterns.

5. **Integration Testing**: While `tdd` teaches integration testing, no skill covers multi-service integration, contract testing, API mocking, or distributed system testing.

6. **Cross-Language Support**: Skills are heavily JavaScript/TypeScript-centric. Multi-language codebases (monorepos with Python, Go, Rust) have limited support.

---

## Relevance to Claude Code Development

mattpocock/skills exemplifies a **reusable, modular approach to encoding engineering discipline as AI-loadable workflows**. Relevance to Claude Code:

1. **Workflow Encoding**: Each skill demonstrates how to translate a structured engineering practice (TDD, interface exploration, architectural refactoring) into prompt-like guidance that Claude can follow step-by-step.

2. **Anti-Pattern Guidance**: Skills explicitly teach what NOT to do (horizontal slicing, shallow modules, implementation-coupled tests). This guidance prevents common pitfalls in agent-driven development.

3. **Checklist-Driven Verification**: Skills use checklists (e.g., "Confirm with user which behaviors to test") to ensure Claude pauses for user alignment before proceeding. This pattern is applicable to any guided workflow.

4. **Reference Material Integration**: Embedding thematic deep-dives (mocking.md, interface-design.md) within skills allows Claude to load context without external tool calls. This model could apply to Claude Code's documentation system.

5. **Domain-Aware Architecture Guidance**: `improve-codebase-architecture`'s integration with CONTEXT.md and docs/adr/ shows how to make architectural guidance project-specific rather than generic.

6. **Parallel Sub-Agent Spawning**: `design-an-interface` demonstrates spawning 3+ parallel sub-agents with different constraints to explore a design space. This pattern could generalize to other exploration tasks (e.g., optimization approaches, testing strategies).

7. **GitHub Integration**: Multiple skills produce and manage GitHub artifacts (issues, PRs, milestones). This integration pattern is reusable for any workflow that needs to persist decisions in project management systems.

### Applicability to This Repository (claude_skills)

This repository (claude_skills) and mattpocock/skills address similar problems but at different scales:

- **mattpocock/skills**: Focused collection (21 skills) of deeply specialized engineering workflows. Each skill is battle-tested, well-documented, and designed for reuse.
- **claude_skills**: Larger ecosystem (60+ skills, agents, plugins) covering broader domains (skill generation, MCP integration, process improvement, code auditing, testing, etc.).

mattpocock/skills provides **reference implementations** for skill structure, activation triggers, progressive disclosure, and reference material organization. Patterns from mattpocock/skills could inform:
- Skill frontmatter consistency
- Anti-pattern documentation standards
- Checklist-driven verification workflows
- Domain-aware guidance (CONTEXT.md integration)
- Reference material organization (embedding deep-dives within skills)

---

## References

- GitHub Repository: <https://github.com/mattpocock/skills>
- License: MIT (2026 Matt Pocock)
- Last Verified: 2026-04-27
- API Data Access: 2026-04-27 via GitHub API with authentication
- Newsletter: <https://www.aihero.dev/s/skills-newsletter>

**Accessed Primary Sources**:
- Repository clone (shallow): /home/user/claude_skills/.worktrees/skills
- README.md (lines 1-116)
- LICENSE (lines 1-22)
- Skill files: tdd/SKILL.md, to-prd/SKILL.md, design-an-interface/SKILL.md, improve-codebase-architecture/SKILL.md
- Reference files: tdd/deep-modules.md, improve-codebase-architecture/LANGUAGE.md

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Anthropic Agent Skills Repository](./anthropics-skills.md) | skill-generation-tools | Official skill specification and template reference; foundation for SKILL.md format mattpocock/skills follows |
| [Claude Code Skills Library by Alireza Rezvani](./claude-code-skills-alirezarezvani.md) | skill-generation-tools | 170 modular skills with identical architecture (SKILL.md + references + CLI tools); shared emphasis on encoding expertise as reusable instruction bundles |
| [Everything Claude Code](./everything-claude-code.md) | skill-generation-tools | Comprehensive skill harness (65+ skills, 16 agents) implementing mattpocock patterns at scale with hook-based automation and persistent memory |
| [SkillKit — Universal Package Manager for AI Agent Skills](./skillkit.md) | skill-generation-tools | Skill format auto-translation and package discovery; complements mattpocock/skills distribution model with cross-platform support for 32 agents |
| [Claude Pilot](../developer-tools/claude-pilot.md) | developer-tools | Enforcement layer using hooks and checklist-driven verification similar to mattpocock/skills workflow discipline; model routing strategy complements skill-based approach |
| [mcpskills-cli](./mcpskills-cli.md) | skill-generation-tools | MCP-to-skill converter using Streamable HTTP discovery; extends mattpocock approach to integrate external tool ecosystems |
| [Skill Seekers](./skill-seekers.md) | skill-generation-tools | Documentation-to-skill automation; alternative generation path to mattpocock's manual curation model |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production-scale orchestration (37.5K stars) implementing multi-agent patterns that mattpocock skills coordinate; hash-anchored editing complements skill-based workflows |

---

## Freshness Tracking

**Entry Created**: 2026-04-27 (v1.0.0)

**Last Verified**: 2026-04-27

**Next Review Due**: 2026-07-27 (90 days)

### Confidence Assessment

| Section | Confidence | Notes |
|---------|-----------|-------|
| Overview | high | Official README and skill descriptions read in full; recent repository (created 2026-02-03) |
| Key Statistics | high | GitHub API data verified (stars, forks, dates) with authentication |
| Key Features | high | All skill descriptions and workflows extracted from primary source SKILL.md files; anti-patterns and examples verified verbatim |
| Technical Architecture | high | Skill file structure, frontmatter, and reference material organization observed directly from filesystem; distribution mechanism (npx skills) documented in README |
| Installation & Usage | medium | Installation commands verified from README; actual behavior not tested in live Claude Code environment; newsletter URL sourced from README |
| Limitations | medium | Limitations inferred from skill scope (no Python/Rust/Go skills present) and design choices (depth-is-good philosophy); not explicitly documented by author |
| Relevance to Claude Code | high | Applicability assessed by comparing skill structure to Claude Code skill conventions and architectural patterns used in this repository |

### Changes Since Last Review

N/A — this is the initial entry created 2026-04-27.

### Data Drift Monitoring

Monitor for:
1. Star count drift (refresh quarterly via GitHub API)
2. New skills added (README updates)
3. License changes
4. Newsletter subscriber count (if accessible)
5. Major refactors to skill philosophy or structure
