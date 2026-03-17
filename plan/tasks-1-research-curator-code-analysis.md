---
feature: research-curator-code-analysis
description: Add code-analysis phase to research-curator agent for repository targets with thin documentation
issue: "#717"
created: 2026-03-15
acceptance-criteria-structured:
  - criterion_id: AC1
    description: "Entry Architecture section contains source file path reference for thin-docs repo"
    check_command: "grep -r 'Source:.*/' research/ | head -5; test $? -eq 0"
  - criterion_id: AC2
    description: "Code-analysis phase skipped for repos with comprehensive docs"
    check_command: "echo 'Manual verification required — run /research-curator on well-documented repo'"
  - criterion_id: AC3
    description: "Doc-sufficiency check result appears in agent working notes"
    check_command: "echo 'Manual verification required — check session transcript'"
  - criterion_id: AC4
    description: "Source files read does not exceed depth budget"
    check_command: "echo 'Manual verification required — count Read calls in session'"
  - criterion_id: AC5
    description: "validate passes on code-analysis entries"
    check_command: "uv run .claude/skills/research-curator/scripts/validate_research.py --all 2>&1 | tail -5"
  - criterion_id: AC6
    description: "rerun re-evaluates doc sufficiency"
    check_command: "echo 'Manual verification required — run --rerun on existing entry'"
---

# Task Plan: Research Curator Code Analysis Phase

**Feature**: research-curator-code-analysis
**Issue**: #717
**Plan artifacts**:

- [Feature context](./feature-context-research-curator-code-analysis.md) — problem statement and desired outcome
- [Architecture spec](./architect-research-curator-code-analysis.md) — design decisions D1-D4

---

## Task 1: Add Doc-Sufficiency Gate to Phase 1

**Status**: NOT STARTED
**Dependencies**: None
**Priority**: 1
**Complexity**: Medium
**Agent**: contextual-ai-documentation-optimizer
**Skills**: []

### Description

Modify `.claude/agents/research-curator.md` to add a doc-sufficiency check at the end of Phase 1 (Extract). The check evaluates three binary questions against extracted passages:

1. Do extracts name specific component/module names?
2. Do extracts describe data flow between named components?
3. Do extracts name extension points with interfaces?

If ANY is NO, flag for Phase 1b. Record the check result as a working note.

Reference: `plan/architect-research-curator-code-analysis.md` section D1.

### Acceptance Criteria

- [ ] Phase 1 instructions in the agent file include the three-question doc-sufficiency check
- [ ] Check result is recorded as a working note (not in the entry)
- [ ] Instructions are Haiku-compatible (binary yes/no, no qualitative judgment)

### Verification Steps

- [ ] Read `.claude/agents/research-curator.md` and confirm the check appears after Phase 1
- [ ] Verify the three questions match the architect spec D1
- [ ] Confirm instructions use imperative language appropriate for Haiku

---

## Task 2: Add Phase 1b Code Analysis Instructions

**Status**: NOT STARTED
**Dependencies**: Task 1
**Priority**: 1
**Complexity**: High
**Agent**: contextual-ai-documentation-optimizer
**Skills**: []

### Description

Add Phase 1b (Code Analysis) to `.claude/agents/research-curator.md` between Phase 1 and Phase 2. Phase 1b:

1. Triggers only when doc-sufficiency check fails
2. Uses three-tier file selection with explicit glob patterns (Tier 1: entrypoints, Tier 2: schema/types, Tier 3: index/barrel)
3. Reads up to 12 source files (depth budget)
4. Adds findings to the extracted passages pool with file-path citations
5. Notes how many files remain unread if budget exhausted

Reference: `plan/architect-research-curator-code-analysis.md` sections D2, D3, and "Phase 1b: Code Analysis".

### Acceptance Criteria

- [ ] Phase 1b appears in the agent file between Phase 1 and Phase 2
- [ ] Three-tier file selection with glob patterns for Python, Node/TS, Go, Rust ecosystems
- [ ] Depth budget of 12 files is enforced with explicit stop instruction
- [ ] Findings cite source files using the format from D4
- [ ] Phase 1b is conditional — only runs when doc-sufficiency check fails

### Verification Steps

- [ ] Read agent file and confirm Phase 1b appears in correct position
- [ ] Verify glob patterns match architect spec D3
- [ ] Confirm depth budget and stop condition are explicit
- [ ] Verify citation format matches D4

---

## Task 3: Update Entry Template for Code-Level Citations

**Status**: NOT STARTED
**Dependencies**: None
**Priority**: 2
**Complexity**: Low
**Agent**: contextual-ai-documentation-optimizer
**Skills**: []

### Description

Review and update `.claude/skills/research-curator/references/entry-template.md` to support code-level citations in the Architecture section. If the template already supports this (Source: lines are generic enough), document that no change is needed. If it needs a note about worktree file paths as valid sources, add it.

Specific additions from the architect spec:

1. Add `Confidence Map` field to the Freshness Tracking table (`section: level (qualifier)`)
2. Add note explaining the `code-read` confidence qualifier and mixed-source annotation (`doc + code-read`)

Reference: `plan/architect-research-curator-code-analysis.md` section D4 and "Entry Template Changes".

### Acceptance Criteria

- [ ] Entry template Architecture section explicitly supports source-file citations
- [ ] Citation format is documented (`Source: {path} — {name}`)
- [ ] `code-read` confidence qualifier is documented in Freshness Tracking guidance
- [ ] No breaking changes to existing entry validation

### Verification Steps

- [ ] Read updated template and confirm citation guidance exists
- [ ] Run `uv run .claude/skills/research-curator/scripts/validate_research.py --all` to confirm no validation regressions

---

## Task 4: Verify Downstream Agent Compatibility

**Status**: NOT STARTED
**Dependencies**: Task 2, Task 3
**Priority**: 3
**Complexity**: Low
**Agent**: general-purpose
**Skills**: []

### Description

Verify that `.claude/agents/research-insight-extractor.md` and `.claude/agents/research-utilization-assessor.md` can handle entries with code-level Architecture content. Read both agent files and confirm their instructions do not filter out or break on source-file citations. If no changes needed, document that in a brief note.

### Acceptance Criteria

- [ ] research-insight-extractor handles code-level architecture content (confirmed or fixed)
- [ ] research-utilization-assessor handles code-level architecture content (confirmed or fixed)
- [ ] Compatibility check documented

### Verification Steps

- [ ] Read both downstream agent files
- [ ] Confirm no instructions that would reject worktree file paths in Architecture sections
- [ ] Document findings

---

## Task 5: Integration Verification

**Status**: NOT STARTED
**Dependencies**: Task 1, Task 2, Task 3, Task 4
**Priority**: 4
**Complexity**: Medium
**Agent**: general-purpose
**Skills**: []

### Description

Run validation to ensure the modified agent file and entry template pass all existing checks:

1. Run `uv run prek run --files .claude/agents/research-curator.md`
2. Run `uv run .claude/skills/research-curator/scripts/validate_research.py --all`
3. Review the modified agent file for instruction coherence — Phase 1 → doc-sufficiency check → Phase 1b (conditional) → Phase 2 flow is unbroken

### Acceptance Criteria

- [ ] prek passes on modified agent file
- [ ] `validate_research.py --all` passes with no new errors
- [ ] Phase flow is coherent when read sequentially

### Verification Steps

- [ ] Run prek and capture output
- [ ] Run validator and capture output
- [ ] Read agent file sequentially and confirm flow

---

## Context Manifest

### How the Research Curator Agent Currently Works

When a user invokes `/research-curator <URL>`, the orchestrator skill at `.claude/skills/research-curator/SKILL.md` parses the arguments through a mode router (default, `--batch`, `--rerun`, `--validate`) and spawns the `@research-curator` agent defined in `.claude/agents/research-curator.md`. The agent runs on the Haiku model, which is a critical constraint -- all instructions must be binary/enumerated rules, not qualitative prose.

The agent's research workflow proceeds through five sequential phases. Phase 1 (Extract Key Passages) fetches primary sources -- README, docs site, GitHub API, package registries -- and records exact quotes with source attribution and a `Relevance` field indicating which entry section each extract feeds. The extract format is:

```text
N. "{exact quote or data point}"
   Source: {URL or tool + section}
   Relevance: {which entry section this feeds}
```

Before Phase 1 begins, the agent checks whether the target has an associated repository. If yes, it shallow-clones it to `.worktrees/{repo-name}/` via `git clone --depth 1` or `gh repo clone`. This clone is already on disk by the time Phase 1 completes -- the code analysis feature does not need to add any cloning logic. However, the current Phase 1 instructions never direct the agent to read source code files (`.py`, `.ts`, `.go`, etc.) from the worktree. It reads only README, docs/, CHANGELOG, config files, and LICENSE from the clone.

Phase 2 (Organize Extracts by Section Theme) groups passages by entry section. Phase 3 (Write Entry Grounded in Extracts) composes the 10-section entry from those extracts, with every factual claim tracing to a passage. Phase 4 assigns confidence levels (high/medium/low) per section. Phase 5 verifies no ungrounded claims remain. The agent then selects a category from a fixed list, writes the entry to `./research/{category}/{resource-name}.md`, and returns a structured result block.

After the research agent completes, the orchestrator spawns three concurrent post-processing agents: `@research-insight-extractor` (Opus model, maps patterns to local systems and creates backlog items), `@research-utilization-assessor` (Haiku model, checks if the tool has a callable API/SDK the repo could use), and `@research-cross-referencer` (adds cross-reference tables). The orchestrator then updates `./research/README.md`, lints, commits, and pushes.

### The Entry Template and Validation System

The entry template at `.claude/skills/research-curator/references/entry-template.md` defines 10 required sections: Overview, Problem Addressed, Key Statistics, Key Features, Technical Architecture, Installation & Usage, Relevance to Claude Code Development, References, Cross-References, and Freshness Tracking. The Freshness Tracking section currently contains a table with three fields: Last Verified, Version at Verification, and Next Review Recommended. There is no Confidence Map field in the current template -- this is one of the additions Task 3 must make.

The validation script at `.claude/skills/research-curator/scripts/validate_research.py` checks structural completeness only. It verifies: (1) all 9 required `##`-level sections exist (section_completeness, error severity), (2) header fields Research Date/Source URL/Version at Research/License are present (header_fields, error), (3) no sections are empty (empty_sections, error), (4) References URLs have access dates (access_dates, warning), (5) Freshness Tracking has its three required fields (freshness_tracking, warning), (6) Key Statistics dates are not older than 6 months (statistics_currency, warning), (7) URL format validity (url_format, warning), and (8) markdown formatting (formatting_suggestions, info).

The validator does NOT check content depth -- an Architecture section with only "uses a plugin system" passes validation. The validator also does NOT currently check for or require a Confidence Map field. This means adding the Confidence Map field to the template (Task 3) will not break validation, because the validator checks for the three existing Freshness Tracking fields by substring match (`field in section_text`), and adding a new row to the table does not remove any existing fields. The `_check_freshness_tracking` function in `validate_research.py` only checks for `FRESHNESS_REQUIRED_FIELDS = ["Last Verified", "Version at Verification", "Next Review Recommended"]` and their aliases -- it will not reject entries missing "Confidence Map" because that field is not in the required list.

The validation rules are documented in `.claude/skills/research-curator/references/validation-rules.md`, which maps directly to what the script checks. The rules file defines the Script vs Agent responsibility boundary: the script detects issues, the agent fixes content issues via `--fix` mode, and the orchestrator decides which to auto-fix based on severity.

### What Needs to Change for Each Task

**Task 1 (Doc-Sufficiency Gate)**: The agent file `.claude/agents/research-curator.md` must be modified to add a doc-sufficiency check immediately after Phase 1 completes. The check evaluates three binary yes/no questions against Phase 1 extracts tagged with `Relevance: Architecture` or `Relevance: Features`. The current Phase 1 extract format already has a `Relevance` field, but it uses free-form values like "which entry section this feeds." Task 1 must also add guidance to Phase 1 to use exact section names from the template (Overview, Technical Architecture, Key Features, etc.) as Relevance values, so the doc-sufficiency check can filter by section. The three questions from architect spec D1 are: (Q1) Do extracts name at least 2 specific component/module/class names? (Q2) Do extracts describe data flow between at least 2 named components? (Q3) Do extracts name an extension point with its concrete API? If ANY is NO, Phase 1b triggers. The check result must be recorded as a working note (internal to the agent's reasoning), not written to the entry file.

**Task 2 (Phase 1b Code Analysis)**: A new Phase 1b section must be inserted into the agent file between Phase 1 and Phase 2, inside the `<methodology>` XML tags (lines 110-155 of the current agent file). The `<methodology>` section currently contains Phase 1 (Extract Key Passages) and Phase 2 (Write From Extracts). Phase 1b must be conditional -- only runs when the doc-sufficiency check fails. It uses a three-tier file selection system with explicit glob patterns per ecosystem (Python, Node/TS, Go, Rust, Java/Kotlin, Ruby). The tiers are: Tier 1 (entrypoints like `**/main.py`, `**/cli.py`), Tier 2 (schema/type files like `**/models.py`, `**/types.ts`), Tier 3 (index/barrel files like `**/__init__.py`, `**/api.py`). The depth budget is 12 source files maximum. Files over 500 lines are skipped with a note. Test files, dependency directories, and build artifacts are excluded. Code extracts use the same format as Phase 1 but add `Confidence: code-read` and use `Source: {relative-path}:{line-range} -- {name}` instead of a URL. The full Phase 1b prompt text is provided verbatim in the architect spec under "Phase 1b: Code Analysis (new)" -- Task 2's implementor should use that as the primary reference.

**Task 3 (Entry Template Update)**: The entry template at `.claude/skills/research-curator/references/entry-template.md` needs two additions. First, a new row in the Freshness Tracking table: `| Confidence Map | \`section: level (qualifier)\` |`. Second, a note below the template explaining the `code-read` confidence qualifier: when Architecture claims derive from code analysis, append `(code-read)` to the confidence level (e.g., `Architecture: medium (code-read)`). Mixed-source sections use the lower confidence and note both qualifiers: `Architecture: medium (doc + code-read)`. The Freshness Tracking table in the template is a standard markdown table inside the fenced code block (lines 177-183 of the template file). The new row goes after the existing three rows. The explanatory note goes after the closing ```` ```` of the template block, near the existing `> **Note**:` blocks.

**Task 4 (Downstream Agent Compatibility)**: The two downstream agents that consume research entries need compatibility verification. The `@research-insight-extractor` (`.claude/agents/research-insight-extractor.md`, Opus model) reads the Relevance to Claude Code Development section and maps patterns to local systems using a `<system_map>` table. It does not filter or parse the Technical Architecture section's content format -- it reads research entries holistically and looks for patterns. The `@research-utilization-assessor` (`.claude/agents/research-utilization-assessor.md`, Haiku model) checks whether the entry documents a callable API/SDK/CLI/webhook. It reads the full entry and checks for integration surfaces. Neither agent has instructions that would reject or break on `Source: path -- name` citations within Architecture sections. Neither agent parses the Freshness Tracking Confidence Map field. The compatibility check should confirm this by reading both files and documenting that no changes are needed (or making changes if something is found).

**Task 5 (Integration Verification)**: Runs `uv run prek run --files .claude/agents/research-curator.md` for linting and `uv run .claude/skills/research-curator/scripts/validate_research.py --all` for validation. The `prek` command is the repo's Rust-based pre-commit replacement. The validator will pass because the changes are to the agent prompt file and template reference file, not to research entry files themselves.

### Technical Reference Details

#### Key File Locations and Their Roles

- `.claude/agents/research-curator.md` -- PRIMARY file being modified (Tasks 1, 2). Contains the full agent prompt with research workflow phases inside `<methodology>` tags. The agent runs on Haiku model. Line 110 starts the `<methodology>` section. Phase 1 extract format is at lines 120-132. Phase 2 starts at line 137.
- `.claude/skills/research-curator/SKILL.md` -- Orchestrator skill. NOT modified by any task. Spawns `@research-curator` agents and handles post-processing. Relevant for understanding how the agent is invoked but no changes needed.
- `.claude/skills/research-curator/references/entry-template.md` -- Entry template (Task 3). The Freshness Tracking table is at lines 177-183 inside the fenced template block. Existing `> **Note**:` blocks are at lines 185-194.
- `.claude/skills/research-curator/references/validation-rules.md` -- Validation rules documentation. NOT modified. Defines the 9 required sections, severity levels, and JSON output schema. The validator checks structure, not content depth.
- `.claude/skills/research-curator/scripts/validate_research.py` -- Validation script. NOT modified. Checks `REQUIRED_SECTIONS` (9 sections), `REQUIRED_HEADER_FIELDS` (4 fields), `FRESHNESS_REQUIRED_FIELDS` (3 fields). Does not check for Confidence Map. Adding Confidence Map to the template will not cause validation failures.
- `.claude/agents/research-insight-extractor.md` -- Downstream consumer (Task 4). Opus model. Reads entry's Relevance section. Has a `<system_map>` for mapping patterns to local files. Does not parse Architecture section format.
- `.claude/agents/research-utilization-assessor.md` -- Downstream consumer (Task 4). Haiku model. Checks for callable integration surfaces (API/SDK/CLI/webhook). Does not parse Architecture section format.
- `plan/architect-research-curator-code-analysis.md` -- Architecture spec with design decisions D1-D4, full Phase 1b prompt text, file selection tiers, citation format, and entry template changes.
- `plan/feature-context-research-curator-code-analysis.md` -- Problem statement, current system description, desired outcome, and acceptance criteria.

#### Agent File Structure (research-curator.md)

The agent file uses XML-style tags to organize sections: `<research_tools>`, `<methodology>`, `<fidelity_rules>`, `<depth_requirements>`, `<categories>`, `<modes>`, `<inaccessibility_handling>`, `<return_format>`, `<boundaries>`. Tasks 1 and 2 modify content inside `<methodology>`. The Phase 1 instructions are inside `<methodology>` and the doc-sufficiency check + Phase 1b must be inserted between the existing Phase 1 and Phase 2 subsections within that same tag.

#### Mermaid Workflow Diagram in Agent File

The agent file contains a Mermaid flowchart (lines 21-60) showing the research workflow. The current flow goes: Extract -> Organize -> Write -> Confidence -> Validate -> SelectCat -> WriteFile -> Return. After Task 1 and Task 2, the flow should conceptually become: Extract -> DocSufficiencyCheck -> (conditional) Phase1b -> Organize -> Write -> Confidence -> Validate -> SelectCat -> WriteFile -> Return. The Mermaid diagram should be updated to reflect the new Phase 1b branch.

#### Citation Format from Architect Spec D4

Code-derived findings use inline `Source:` attribution within existing prose sections:

```text
Source: `{relative-path}` -- {exported-name or description}
```

Code extracts during Phase 1b use:

```text
N. "{exact code passage}"
   Source: {relative-path}:{line-range} -- {name}
   Relevance: Architecture | Features
   Confidence: code-read
```

#### Confidence Qualifier System

The existing confidence system in the agent file (Fidelity Rules, Rule 4) uses three levels: high, medium, low. The new `code-read` qualifier is an annotation appended in parentheses to the existing level, not a new level. It indicates the source type, not the confidence grade. Mixed sources use the lower of the two confidence levels with both qualifiers noted.

#### Existing Relevance Field Values

The current Phase 1 instructions say `Relevance: {which entry section this feeds}` with no constraint on values. Task 1 must add explicit guidance to use exact section names from the template: Overview, Problem Addressed, Key Statistics, Key Features, Technical Architecture, Installation & Usage, Relevance to Claude Code Development, References, Freshness Tracking. This enables the doc-sufficiency check to filter extracts by `Technical Architecture` and `Key Features` tags.

#### Validation Script Internals

The `validate_research.py` script uses these constants that are relevant for understanding what will and will not break:

- `REQUIRED_SECTIONS`: 9 sections (does not include Cross-References)
- `SECTION_ALIASES`: `{"Installation & Usage": ["Installation and Usage"]}`
- `REQUIRED_HEADER_FIELDS`: `["Research Date", "Source URL", "Version at Research", "License"]`
- `FRESHNESS_REQUIRED_FIELDS`: `["Last Verified", "Version at Verification", "Next Review Recommended"]`
- `FRESHNESS_ALIASES`: `{"Last Verified": ["Research Date"], "Next Review Recommended": ["Next Review"]}`

The `_check_freshness_tracking` function does substring matching (`field in section_text`), so adding new rows to the Freshness Tracking table will not interfere with existing field detection.

### Discovered During Implementation

[Date: 2026-03-15]

#### Plan Artifact Freshness Check

All plan artifacts (feature context and architect spec) remain aligned with the implementation. No intent divergences were found. The following design refinements occurred during implementation -- all are acceptable evolutions that stay within original intent:

1. **`--rerun` mode gained doc-sufficiency and Phase 1b support**: The feature context and architect spec focused on the default (new URL) workflow. During implementation, the `--rerun` mode was also updated to run the doc-sufficiency check on re-extracted passages and conditionally trigger Phase 1b before updating sections. This is a logical extension -- `--rerun` re-gathers data and should re-evaluate whether code analysis is needed for entries that may have been created before this feature existed.

2. **Mermaid workflow diagram updated**: The main workflow flowchart in the agent file was updated to include the DocCheck decision node and Phase 1b branch, plus the `--rerun` path routing through DocCheck. Neither plan artifact discussed diagram updates, but the diagram is the authoritative workflow visualization and must reflect the actual phase flow.

3. **Exclusion list expanded**: The implementation added `**/__pycache__/**`, `**/dist/**`, `**/build/**`, `**/target/**` to the Phase 1b exclusion list beyond what the architect spec listed. These are standard build/cache directories that should always be excluded from code analysis.

4. **Test exclusion patterns broadened**: The architect spec had four specific test patterns. The implementation added `**/*_test.*` and `**/*.test.*` as catch-all patterns to cover ecosystems not explicitly listed (e.g., Dart, Elixir).

5. **Relevance field values use exact template section names**: The architect spec used shorthand (`Architecture | Features`) for Phase 1b extract Relevance values. The implementation uses `Technical Architecture | Key Features` -- the exact section names from the entry template. This is consistent with the Relevance values guidance added to Phase 1, which tells the agent to use exact template section names so the doc-sufficiency check can filter by section.

6. **Citation format guidance added to entry template**: The architect spec placed the `Source: {path} -- {name}` citation format only in the agent instructions (D4). The implementation also added an `> **Architecture section citations**` guidance block directly in `entry-template.md` with format examples. This improves discoverability for future template consumers and downstream agents that read the template but not the agent file.

#### Divergence Classification Summary

All 6 items above are classified as **design-refinement** (acceptable evolution during implementation). Zero items classified as intent-divergence. No `DIVERGENCE_REQUIRING_REVIEW` blocks needed.
