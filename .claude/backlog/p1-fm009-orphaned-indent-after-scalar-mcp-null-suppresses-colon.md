---
name: 'FM009 orphaned-indent after scalar mcp: null suppresses colon fix'
description: "The FM009 state machine in plugin_validator.py:_fix_unquoted_colons does not differentiate between scalar top-level lines (mcp: null) and block-introducer lines (mcp:). When a scalar line like `mcp: null` is encountered, current_top_level_key is set to 'mcp'. Any subsequent indented line (orphaned indent — impossible in valid YAML but possible in malformed frontmatter) is then incorrectly treated as inside the mcp: block and skipped by the ecosystem guard, leaving an unquoted colon unfixed and invalid YAML in production SKILL.md files. The fix requires detecting scalar vs block top-level lines and resetting current_top_level_key after a scalar so subsequent indented lines are not suppressed."
metadata:
  topic: fm009-orphaned-indent-after-scalar-mcp-null-suppresses-colon
  source: Code review — tasks-26 followup analysis (2026-03-06)
  added: '2026-03-06'
  priority: P1
  type: Bug
  status: needs-grooming
  plan: plan/tasks-28-multi-ecosystem-plugin-creator-followup-3.md
  issue: '#518'
  last_synced: '2026-03-12T12:48:05Z'
---

## Story

As a **developer using Claude Code skills**, I want to **fm009 orphaned-indent after scalar mcp: null suppresses colon fix** so that **the tooling becomes more capable and complete**.

## Description

The FM009 state machine in plugin_validator.py:_fix_unquoted_colons does not differentiate between scalar top-level lines (mcp: null) and block-introducer lines (mcp:). When a scalar line like `mcp: null` is encountered, current_top_level_key is set to 'mcp'. Any subsequent indented line (orphaned indent — impossible in valid YAML but possible in malformed frontmatter) is then incorrectly treated as inside the mcp: block and skipped by the ecosystem guard, leaving an unquoted colon unfixed and invalid YAML in production SKILL.md files. The fix requires detecting scalar vs block top-level lines and resetting current_top_level_key after a scalar so subsequent indented lines are not suppressed.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review — tasks-26 followup analysis (2026-03-06)
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None
