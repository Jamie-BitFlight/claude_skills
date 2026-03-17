---
name: Create ty skill for python3-development plugin
description: New skill documenting Astral's ty type checker, to live at plugins/python3-development/skills/ty/. Should be modeled on the uv skill structure (SKILL.md, references/cli_reference.md, references/configuration.md, references/migration-guide.md, references/quick-reference.md, references/troubleshooting.md, scripts/sync_ty_releases.py). Source docs are cloned at .claude/worktrees/ty/docs/. One reference already exists in python-cli-architect.md line 280 documenting ty as the primary type checker. Th
metadata:
  topic: create-ty-skill-for-python3-development-plugin
  source: Session observation
  added: '2026-02-25'
  priority: completed
  type: Feature
  status: done
  issue: '#210'
  groomed: '2026-02-28'
  last_synced: '2026-02-28T05:43:01Z'
  plan: plan/tasks-2-complete-ty-skill.md
---

## Story

As a **developer**, I want **New skill documenting Astral's ty type checker, to live at plugins/python3-de...** so that **backlog items are tracked in GitHub**.

## Description

New skill documenting Astral's ty type checker, to live at plugins/python3-development/skills/ty/. Should be modeled on the uv skill structure (SKILL.md, references/cli_reference.md, references/configuration.md, references/migration-guide.md, references/quick-reference.md, references/troubleshooting.md, scripts/sync_ty_releases.py). Source docs are cloned at .claude/worktrees/ty/docs/. One reference already exists in python-cli-architect.md line 280 documenting ty as the primary type checker. Th

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation
- **Priority**: P1
- **Added**: 2026-02-25
- **Research questions**: None

**Research first**: Read .claude/worktrees/ty/docs/ for source material. Read plugins/python3-development/skills/uv/ for structural template. Read plugins/python3-development/agents/python-cli-architect.md line 280 for existing ty reference to preserve and expand.

## Fact-Check

Fact-Check Summary: Create ty skill for python3-development plugin
Checked against: codebase state 2026-02-28, commit a22104c (2026-02-27)
Claims checked: 5

VERIFIED (3):
1. ty skill directory exists at plugins/python3-development/skills/ty/ — confirmed
2. SKILL.md created (123 lines, commit a22104c, 2026-02-27) — confirmed
3. References directory with 6 files (1,236 lines total) — confirmed:
   cli-reference.md (177), configuration-schema.md (338), environment-and-modules.md (127),
   file-selection.md (147), installation.md (254), rules-and-diagnostics.md (193)

PARTIAL (1):
4. Structure modeled on uv skill — PARTIALLY DONE. Created 9 files (1,372 lines) but
   diverges from uv skill template in file naming and organization

MISSING (1):
5. Components specified in backlog item but not created:
   - scripts/sync_ty_releases.py — NOT CREATED
   - references/migration-guide.md — NOT CREATED
   - references/quick-reference.md — NOT CREATED (content embedded in SKILL.md instead)
   - references/troubleshooting.md — NOT CREATED
   - .claude/worktrees/ty/docs/ source material — NOT PRESENT

CREATED BUT NOT IN SPEC:
- resources/workflows/environment-discovery.md (16 lines)
- resources/workflows/python-version-resolution.md (12 lines)

## RT-ICA

RT-ICA: Create ty skill for python3-development plugin
Goal: Complete the ty type checker skill to match uv skill structure template
Decision: APPROVED — remaining work is clearly scoped

Conditions:
1. Existing ty skill foundation (SKILL.md + 6 references) | AVAILABLE
2. uv skill template for structural reference | AVAILABLE (plugins/python3-development/skills/uv/)
3. ty documentation source material | DERIVABLE (ty docs available via web/repo)
4. Missing files clearly identified | AVAILABLE (4 files: sync script, migration, quick-ref, troubleshooting)

Missing: None — all remaining work is well-defined
Assumptions: Quick-reference and troubleshooting content may already exist within SKILL.md
and just needs extraction into separate reference files

## Groomed (2026-02-28)

### Priority

P1 — Substantial work complete (1,372 lines, 9 files). Remaining work is gap-filling, not greenfield.

### Impact

- Blocks: ty skill cannot be considered complete per original specification
- Existing: Functional skill already usable with SKILL.md and 6 reference files

### Progress (as of 2026-02-28)

**Created (commit a22104c, 2026-02-27):**
- plugins/python3-development/skills/ty/SKILL.md (123 lines)
- references/cli-reference.md (177 lines)
- references/configuration-schema.md (338 lines)
- references/environment-and-modules.md (127 lines)
- references/file-selection.md (147 lines)
- references/installation.md (254 lines)
- references/rules-and-diagnostics.md (193 lines)
- resources/workflows/environment-discovery.md (16 lines)
- resources/workflows/python-version-resolution.md (12 lines)

**Missing (per original spec modeled on uv skill):**
- scripts/sync_ty_releases.py
- references/migration-guide.md
- references/quick-reference.md (content may be in SKILL.md, needs extraction)
- references/troubleshooting.md

### Acceptance Criteria

1. All 4 missing files created
2. Structure aligns with uv skill template
3. No regression in existing skill content
4. Passes prek validation

### Resources

| Type | Item |
|------|------|
| Existing skill | plugins/python3-development/skills/ty/ (9 files, 1,372 lines) |
| Template | plugins/python3-development/skills/uv/ (structural reference) |

### Dependencies

- Depends on: None
- Blocks: Skill completeness per original specification

### Blockers

None — RT-ICA APPROVED. Remaining work is clearly scoped.

### Effort

Small — 4 files to create, pattern available from uv skill. Content may partially exist in SKILL.md needing extraction.