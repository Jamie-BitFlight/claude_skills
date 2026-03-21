---
name: Extract shared _get_table_width() utility from 6 duplicate copies
description: 'The `_get_table_width(table: Table) -> int` function is identically defined in 6 scripts:\n- .claude/skills/session-historian/scripts/session_query.py\n- .claude/skills/backlog/scripts/backlog.py\n- .claude/utilities/find-temp-documentation.py\n- plugins/plugin-creator/scripts/normalize_frontmatter.py\n- plugins/plugin-creator/scripts/create_plugin.py\n- plugins/python3-development/scripts/validate_pep723.py\n\nExtract to a shared utility module and import from all 6.\n\nDiscovered during code review session 2026-03-11.'
metadata:
  topic: extract-shared-gettablewidth-utility-from-6-duplicate-copies
  source: Code review 2026-03-11
  added: '2026-03-11'
  priority: P2
  type: Refactor
  status: needs-grooming
  issue: '#613'
  last_synced: '2026-03-21T08:07:45Z'
---

## Story

As a **maintainer of the codebase**, I want to **extract shared _get_table_width() utility from 6 duplicate copies** so that **the code is cleaner and more maintainable**.

## Description

The `_get_table_width(table: Table) -> int` function is identically defined in 6 scripts:\n- .claude/skills/session-historian/scripts/session_query.py\n- .claude/skills/backlog/scripts/backlog.py\n- .claude/utilities/find-temp-documentation.py\n- plugins/plugin-creator/scripts/normalize_frontmatter.py\n- plugins/plugin-creator/scripts/create_plugin.py\n- plugins/python3-development/scripts/validate_pep723.py\n\nExtract to a shared utility module and import from all 6.\n\nDiscovered during code review session 2026-03-11.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Code review 2026-03-11
- **Priority**: P2
- **Added**: 2026-03-11
- **Research questions**: None
