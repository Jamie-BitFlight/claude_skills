---
name: Enhance skill-research-process for CLI tool skills
description: 'The skill-research-process skill has sound research orchestration but lacks output specification for producing complete CLI tool skills. Three gaps identified via assessment against the uv skill: (1) No local directory input — passing a path like .claude/worktrees/ty/docs/ is treated as a tool name, triggering web searches instead of reading local docs. (2) No CLI reference file templates — no structural anchor ensuring standard reference types (cli_reference.md, configuration.md, migration-guid'
metadata:
  topic: enhance-skill-research-process-for-cli-tool-skills
  source: Session observation
  added: '2026-02-25'
  priority: completed
  type: Feature
  status: done
  groomed: '2026-02-25'
  issue: '#197'
  plan: plan/tasks-6-enhance-skill-research-process.md
---

## Story

As a **developer**, I want **The skill-research-process skill has sound research orchestration but lacks o...** so that **backlog items are tracked in GitHub**.

## Description

The skill-research-process skill has sound research orchestration but lacks output specification for producing complete CLI tool skills. Three gaps identified via assessment against the uv skill: (1) No local directory input — passing a path like .claude/worktrees/ty/docs/ is treated as a tool name, triggering web searches instead of reading local docs. (2) No CLI reference file templates — no structural anchor ensuring standard reference types (cli_reference.md, configuration.md, migration-guid

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation
- **Priority**: P1
- **Added**: 2026-02-25
- **Research questions**: None

## Fact-Check

Claims checked: 5
VERIFIED: 5 | REFUTED: 0 | INCONCLUSIVE: 0

All claims confirmed against file content (filesystem check — no web verification needed, these are structural claims about repo files):

1. CONFIRMED — No local path input handling. Evidence: SKILL.md:4 argument-hint is tool-or-library-name; agent-prompts.md:34-39 lists only web-based sources; no Read/Glob tools used anywhere.
2. CONFIRMED — No named reference file templates. Evidence: agent-prompts.md:63-69 prescribes only category/index.md structure with no named standard files.
3. CONFIRMED — No assets/ directory production. Evidence: absent from SKILL.md and agent-prompts.md entirely; gaps-analysis.md does not mention it either.
4. CONFIRMED — No sync/release-tracking script. Evidence: absent from SKILL.md and agent-prompts.md; gaps-analysis.md:29 explicitly documents this gap.
5. CONFIRMED — Output uses references/{category}/index.md (subdirectory). Evidence: SKILL.md:22,75,112-113 and agent-prompts.md:63-68,135 consistently use this pattern.

## RT-ICA

Goal: Fix skill-research-process so it produces CLI tool skills matching the structural quality of the uv skill — with local path input, named reference file templates, assets/ output, a sync script, and flat reference file layout.

Decision: APPROVED

Conditions:
1. Local directory path input handling | AVAILABLE | Fix: update agent-prompts.md with local-path detection variant
2. Named CLI reference file templates | AVAILABLE | Fix: new references/cli-tool-reference-templates.md defining standard files (cli_reference.md, configuration.md, migration-guide.md, quick-reference.md, troubleshooting.md); update categorization agent prompt to reference it
3. Assets/ directory production step | AVAILABLE | Fix: add to Stage 3 in agent-prompts.md
4. Sync/release-tracking script production | AVAILABLE | Fix: add Stage 4 Post-Integration to agent-prompts.md delegating to @python3-development:python-cli-architect
5. Flat reference file layout | AVAILABLE | Fix: update Stage 2, Stage 3, Quality Gate 2 across SKILL.md and agent-prompts.md
6. Embed vs separate skill | RESOLVED | False dilemma — references/ directory handles this. New content goes in references/cli-tool-reference-templates.md and updates to agent-prompts.md. No new skill, no embedding into SKILL.md body.

## Groomed (2026-02-25)

### Priority

9/10 — Blocks CLI tool skill creation at production quality. Without these fixes, `/skill-research-process` produces structurally different output than the reference `uv` skill, missing 5 critical components (local paths, named reference files, assets, sync scripts, flat layout). Affects any skill targeting tools like `ty`, `ripgrep`, `fd`, where comprehensive documentation is essential.

### Impact

- Blocks: New CLI tool skills cannot match existing quality standards; users get incomplete documentation
- Bottleneck: Reference `uv` skill demonstrates the target structure, but skill-research-process cannot produce it

### Benefits

- Enables local documentation ingestion (e.g., `.claude/worktrees/ty/docs/`) as input
- Produces standard CLI reference files (cli_reference.md, configuration.md, migration-guide.md, quick-reference.md, troubleshooting.md) instead of arbitrary categories
- Generates assets/ directories for templates, examples, and reusable resources
- Produces sync/release-tracking scripts for keeping skills current (GitHub Releases API integration)
- Aligns output to flat references/ structure (agentskills spec standard), avoiding subdirectory navigation overhead

### Expected Behavior

When invoking `/skill-research-process .claude/worktrees/ty/docs/`:

1. Skill detects argument is local path (starts with `./`, `/`, `~`, or contains `/`)
2. Reads directory structure and file index from local path
3. Passes local documentation as primary source to categorization agent
4. Categorization agent maps findings to 5 named reference file types (CLI tools)
5. Research agents populate `references/{category-slug}.md` (flat, not subdirectories)
6. Stage 3 creates `assets/` directory with example configs, Dockerfiles, or templates
7. Stage 4 creates `scripts/sync_{tool-name}_releases.py` for GitHub Releases tracking
8. Output skill matches `uv` structural quality and completeness

### Acceptance Criteria

1. **Local input detection** — Stage 0 reads local directory paths; categorization agent prompt template includes path-detection variant
2. **Named reference file templates** — New `references/cli-tool-reference-templates.md` defines standard file types; categorization agent maps to them
3. **Assets directory production** — Stage 3 Integration step creates assets/ with reusable templates or examples
4. **Sync script production** — Stage 4 Post-Integration creates sync script delegating to @python3-development:python-cli-architect
5. **Flat reference layout** — All updates to SKILL.md, agent-prompts.md, Stage 2 and Stage 3 use `references/{slug}.md` instead of `references/{category}/index.md`
6. **Verified against uv skill structure** — New flow produces output structurally identical to `plugins/python3-development/skills/uv/` (verified by file diff)

### Resources

- Skill: `/skill-research-process` (skill being enhanced)
- Skill: `/plugin-creator:skill-creator` (skill structure, frontmatter format, and validation requirements — load before modifying any SKILL.md)
- Skill: `/plugin-creator:agentskills` (references/ structure standard)
- Skill: `/python3-development:python3-development` (orchestration guide for sync script delegation)
- Agent: `@python3-development:python-cli-architect` (sync script production)
- Reference: `.claude/skills/skill-research-process/references/agent-prompts.md` (will be updated)
- Reference: `.claude/skills/skill-research-process/references/cli-tool-reference-templates.md` (NEW)
- Reference: `plugins/python3-development/skills/uv/` (quality benchmark)
- Prior work: `.claude/plan/skill-research-process-assessment.md` (gap analysis)
- Prior work: `.claude/skills/skill-research-process/references/gaps-analysis.md`

### Dependencies

- Blocks: CLI tool skill creation for `ty`, `ripgrep`, `fd` etc. until complete
- Depends on: None

### Effort

High — 5 interdependent fixes across SKILL.md, agent-prompts.md, new reference file, new stage, and verification against uv skill structure.

### Reproducibility

The gaps are reproducible and currently present:

1. **Local directory input** — Attempt `/skill-research-process .claude/worktrees/ty/docs/` and observe that the skill treats the path as a tool name rather than reading the local directory
2. **Reference file structure** — Generated output uses `references/{category}/index.md` structure instead of named files like `references/cli_reference.md`
3. **Missing assets/** — Generated skill will lack an `assets/` directory for templates and examples
4. **Missing sync script** — Generated skill will lack `scripts/sync_{tool-name}_releases.py` for release tracking
5. **Flat layout absence** — References use subdirectory structure, not flat named files

Evidence files: `.claude/skills/skill-research-process/SKILL.md` (line 4: argument-hint is tool-or-library-name), `agent-prompts.md` (lines 34-39: only web-based sources; lines 63-69: only category/index.md structure)