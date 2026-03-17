# Feature Context: Research Curator Code Analysis Pass

**Feature Slug**: research-curator-code-analysis
**Date**: 2026-03-15

---

## Problem Statement

The research-curator agent produces entries based on README files only. When a repo lacks comprehensive technical docs, the entry cannot answer engineering questions about internals (schemas, APIs, extension systems). Evidence: pi-mono session read 11 doc files, zero source files.

The agent already shallow-clones repositories to `.worktrees/{repo-name}/` and has full Read/Grep/Glob access to the clone. However, the Phase 1 Extract step has no instruction to read source files -- it gathers from "primary sources" which in practice means README, docs/, CHANGELOG, and config files. The Depth Requirements section demands architecture content include "core components and their relationships (with exact names from source)" and "extension or integration points," but provides no mechanism to discover these from code when documentation is silent.

The result: entries for doc-thin repos have Architecture sections that either parrot the README's high-level description or contain low-confidence inferences. The agent's own fidelity rules prohibit inference, so the section ends up shallow.

---

## Current System

### Agent: `@research-curator` (`.claude/agents/research-curator.md`)

Model: Haiku. Operates in three modes: default (new URL), `--rerun` (refresh), `--fix` (repair validation issues).

### Research Workflow Phases

**Phase 1 -- Extract Key Passages**: The agent fetches primary sources (README, docs site, gh API, package registry) and records exact quotes with source attribution and section relevance. The shallow clone is created before this phase, but the extraction instructions reference "primary sources" generically -- there is no explicit instruction to read `.py`, `.ts`, `.go`, or other source files from the worktree.

**Phase 2 -- Organize Extracts by Section Theme**: Extracted passages are grouped by which entry section they feed (Overview, Architecture, Features, etc.).

**Phase 3 -- Write Entry Grounded in Extracts**: Each section is composed from the organized extracts. Every factual claim must trace to an extract. The entry follows the 10-section template defined in `references/entry-template.md`.

**Phase 4 -- Assign Confidence Per Section**: Each section gets a confidence level (high/medium/low) based on source quality, completeness, and corroboration.

**Phase 5 -- Verify Every Claim Traces to an Extract**: Final validation pass confirming no ungrounded claims. If a claim lacks a source passage, it is removed.

### What the Agent Reads Today

From the worktree clone:
- README.md (and variants)
- docs/ directory contents
- CHANGELOG / CHANGES
- Config files (pyproject.toml, package.json, Cargo.toml) for metadata
- LICENSE

From external sources:
- Documentation site via `mcp__Ref__ref_read_url`
- GitHub API via `gh api` for stats (stars, contributors, releases)
- Web search via `mcp__exa__web_search_exa` for articles and comparisons
- Code examples via `mcp__exa__get_code_context_exa`

### What the Agent Does NOT Read Today

- Source code files (`.py`, `.ts`, `.go`, `.rs`, `.java`, etc.)
- Schema definitions, protobuf files, OpenAPI specs
- Plugin/extension registration code
- Test files that demonstrate API surface

### Entry Template Sections Affected

The entry template (`references/entry-template.md`) has 10 required sections. The sections most affected by doc-thin repos:

- **Technical Architecture**: Requires "core components and their relationships," "data flow or execution model," "extension or integration points." These are undiscoverable from README alone in many repos.
- **Key Features**: Requires "HOW it does it -- the mechanism, not just the outcome." Mechanisms live in source code.
- **Installation & Usage**: Requires "complete, working example." When docs lack examples, source test files often contain them.

### Orchestrator Skill: `/research-curator` (`.claude/skills/research-curator/SKILL.md`)

The orchestrator spawns `@research-curator` agents and handles coordination. It does not influence what the agent reads during Phase 1 -- that is entirely governed by the agent file's instructions. After the research agent completes, the orchestrator spawns three post-processing agents (insight-extractor, utilization-assessor, cross-referencer) and updates README.

### Validation (`references/validation-rules.md`)

The validator checks structural completeness (all 9 required sections exist, header fields present, no empty sections) but does not assess content depth. An Architecture section containing only README-derived surface descriptions passes validation.

---

## Desired Outcome

A Phase 1b code-analysis pass that triggers when a doc-sufficiency check fails. The doc-sufficiency check evaluates whether Phase 1 extracts contain enough material to write the Architecture and Key Features sections at the required depth. When insufficient, Phase 1b reads a bounded set of source files from the worktree clone to extract architectural evidence: module structure, class/function signatures, schema definitions, plugin registration patterns, and data flow.

Entry Architecture and Key Features sections cite source-file evidence (file path + line reference) when docs are thin, with confidence annotated appropriately. The existing extractive methodology (quote-then-write) applies identically to code extracts.

---

## Acceptance Criteria

1. When a cloned repo's README+docs provide fewer than 3 extractable architectural claims, the agent automatically enters a code-analysis pass before writing the entry.
2. The code-analysis pass reads at most 15 source files per invocation, selected by a tiered priority system (entry points, schema files, plugin registries, core modules, tests).
3. Code-derived architectural findings appear in the entry's Technical Architecture section with source file attribution (e.g., "Source: `src/core/engine.py:45-62`").
4. The entry's Freshness Tracking confidence map distinguishes doc-sourced claims (existing confidence rules) from code-sourced claims (new: `code-read` confidence qualifier).
5. No new scripts or validators are required -- changes are confined to the agent prompt file and entry template reference file.
6. The doc-sufficiency check and file-selection tiers are expressed as explicit enumerated rules (not prose reasoning), suitable for a Haiku-level model.

---

## Key Design Questions (for architect)

1. **How should the doc-sufficiency check be expressed for Haiku-level reasoning?** The check must be a concrete, countable threshold (e.g., "count extractable architectural claims from Phase 1") rather than a qualitative judgment. Haiku cannot reliably evaluate "is this sufficient?" but can count items against a threshold.

2. **What is the right depth budget (max source files per analysis pass)?** The 15-file cap in AC#2 needs architectural justification. Too few files miss critical modules; too many exhaust context window and slow execution. The architect should consider: average module count in target repos, Haiku's context limits, and diminishing returns curve.

3. **How should file-selection tiers be ordered and prioritized?** Candidate tiers include: (a) entry point files (`main.py`, `cli.py`, `app.py`), (b) schema/model files (`models.py`, `schema.py`, `*.proto`, `openapi.yaml`), (c) plugin/extension registries (`plugins/`, `extensions/`, files containing `register`), (d) core module `__init__.py` files for export surface, (e) test files for API usage examples. The ordering determines which files get read when the budget is exhausted before all tiers are covered.

4. **How should code-level findings be cited in the entry template?** Options include: inline source references within prose (`Source: path:lines`), a dedicated "Code Evidence" subsection under Technical Architecture, or footnote-style references linking to the worktree path. The citation format must work within the existing entry template structure without adding new required sections.

---

## Files to Modify

- **`.claude/agents/research-curator.md`**: Add Phase 1b code-analysis pass between Phase 1 (Extract) and Phase 2 (Organize). Add doc-sufficiency check logic. Add file-selection tier definitions. Add code-extract citation format instructions.

- **`.claude/skills/research-curator/references/entry-template.md`**: Add guidance for code-sourced citations in the Technical Architecture section. Add `code-read` confidence qualifier to the Freshness Tracking documentation.

---

## Constraints

- **Haiku model**: All instructions added to the agent file must be unambiguous enumerated rules, not prose requiring interpretation. Decision points must be concrete thresholds, not qualitative judgments. Mermaid flowcharts are the preferred format for branching logic.
- **Shallow clone already on disk**: The worktree clone is created before Phase 1 in the existing workflow. No new cloning, tooling, or setup is needed -- Phase 1b reads from the same `.worktrees/{repo-name}/` path.
- **No new scripts or validators required**: All changes are prompt-level modifications to the agent file and template reference file. The existing validation rules (`validate_research.py`) do not need modification since they check structural completeness, not content depth.
- **Extractive methodology preserved**: Code-derived findings follow the same extract-then-write discipline as doc-derived findings. Exact code passages are recorded with file:line attribution before any abstraction is written.
- **Bounded execution**: The file-selection budget prevents unbounded source reading that could exhaust Haiku's context window or cause excessive latency.
