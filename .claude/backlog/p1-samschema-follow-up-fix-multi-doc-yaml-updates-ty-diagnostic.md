---
name: sam_schema follow-up — fix multi-doc YAML updates, ty diagnostics, compound task IDs, and unrecognized plan formats
description: "Feature verification for #715 (unified SAM task schema) found 4 gaps after implementation:\n\n1. update_fields() fails on yaml_frontmatter format files (multi-document YAML) — ruamel.yaml raises ComposerError on files with --- separators. This means sam state P1/T3 in_progress fails on the dominant file format in the repo.\n2. ty check has 2 diagnostics: type annotation mismatch at query.py:130 and stale type-ignore at yaml_writer.py:437.\n3. TASK_ID_PATTERN regex rejects compound IDs like T10a/T10b — causes 2 of 11 tasks to be silently dropped during parsing of the feature's own task file.\n4. ~20 plan files in plan/ use a format variant (task summary list in frontmatter) not covered by any reader.\n\nCode review also found: silent status normalization fallback (unrecognized values default to not-started), MCP server has 0% test coverage, path traversal prevention only in writer not readers.\n\nWhat success looks like: all 10 acceptance criteria from #715 pass. sam state works on yaml_frontmatter files. ty check returns zero diagnostics. T10a/T10b task IDs parse correctly.\n\nFollow-up task file: plan/tasks-3-unified-sam-task-schema-followup-1.md\nReview report: .claude/reports/review-unified-sam-task-schema-2026-03-14.md"
metadata:
  topic: samschema-follow-up-fix-multi-doc-yaml-updates-ty-diagnostic
  source: 'Feature verification gaps — #715 complete-implementation Phase 2 (2026-03-15)'
  added: '2026-03-15'
  priority: completed
  type: Bug
  status: done
  issue: '#716'
  last_synced: '2026-03-15T15:15:50Z'
  plan: plan/tasks-3-unified-sam-task-schema-followup-1.md
  groomed: '2026-03-15'
---

## Groomed (2026-03-15)

### Acceptance Criteria

<div><sub>2026-03-15T15:15:50Z</sub>

**Additional criteria (added 2026-03-15):**

11. Single-task follow-up files (e.g., `plan/tasks-696-sam-bookend-validation-followup-1.md`) parse correctly — reader handles degenerate case of one task in frontmatter list with body as description. `status: pending` normalized to `not-started`.
12. code-reviewer agent produces follow-up task files via `sam create` — not via `Write` tool with ad-hoc format. Follow-up files are valid pure YAML that `sam read` can parse without a new reader variant.
13. All existing follow-up files in `plan/tasks-*-followup-*.md` parse via `sam status` with non-zero task count.
</div>