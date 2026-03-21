---
name: Migrate milestone skills from gh CLI to project tooling
description: <div><sub>2026-03-20T23:38:51Z</sub>
metadata:
  topic: migrate-milestone-skills-from-gh-cli-to-project-tooling
  source: Milestone orchestration design — .claude/reports/milestone-orchestration-design-20260320.md
  added: '2026-03-20'
  priority: P1
  type: Refactor
  status: open
  issue: '#923'
  last_synced: '2026-03-21T03:45:07Z'
  groomed: '2026-03-20'
---

## Groomed (2026-03-20)

### Fact-Check Update

<div><sub>2026-03-20T23:38:51Z</sub>

Fact-checker (2026-03-20) found that existing milestone skills (/create-milestone, /group-items-to-milestone, /start-milestone, /complete-milestone) already use PyGithub scripts as their primary path via github_project_setup.py. The gh CLI is used only as fallback. This item needs re-scoping — the migration claimed in the description is already partially done. Verify each skill individually to determine what remains.
</div>
