# Backlog Process Domain Registry

All files that compose the backlog tooling ecosystem. This is the scope of the backlog-tools-administrator skill — changes outside this registry are out of scope.

Last updated: 2026-03-01

## Table of Contents

- [Primary Script](#primary-script)
- [Skills](#skills)
- [Agents](#agents)
- [Skill References](#skill-references)
- [Skill Templates](#skill-templates)
- [Tests](#tests)
- [Documentation and Schema](#documentation-and-schema)
- [Rules](#rules)
- [Hooks](#hooks)
- [Helper Scripts](#helper-scripts)

## Primary Script

The sole interface for all backlog and GitHub Issue CRUD:

- `.claude/skills/backlog/scripts/backlog.py` — Typer CLI with subcommands: add, list, sync, close, resolve, update, groom, view

## Skills

| Skill | Path | Purpose |
|-------|------|---------|
| `backlog` | `.claude/skills/backlog/SKILL.md` | Script documentation and integration guide |
| `create-backlog-item` | `.claude/skills/create-backlog-item/SKILL.md` | Guided/quick/auto intake for new items |
| `work-backlog-item` | `.claude/skills/work-backlog-item/SKILL.md` | Browse, plan, execute, close items |
| `groom-backlog-item` | `.claude/skills/groom-backlog-item/SKILL.md` | Fact-check, RT-ICA, groomer delegation |

## Agents

| Agent | Path | Purpose |
|-------|------|---------|
| `backlog-item-groomer` | `.claude/agents/backlog-item-groomer.md` | Autonomous grooming: resource/dependency mapping |

## Skill References

### backlog/

- `.claude/skills/backlog/references/item-schema.md` — Per-item file frontmatter schema
- `.claude/skills/backlog/references/known-patterns.md` — Known patterns and anti-patterns
- `.claude/skills/backlog/references/state-machine.md` — Item lifecycle state machine

### work-backlog-item/

- `.claude/skills/work-backlog-item/references/auto-mode.md`
- `.claude/skills/work-backlog-item/references/close-resolve-procedure.md`
- `.claude/skills/work-backlog-item/references/error-handling.md`
- `.claude/skills/work-backlog-item/references/example-sessions.md`
- `.claude/skills/work-backlog-item/references/github-integration.md`
- `.claude/skills/work-backlog-item/references/sam-definition.md`
- `.claude/skills/work-backlog-item/references/step-procedures.md`
- `.claude/skills/work-backlog-item/references/validation-plan.md`

## Skill Templates

- `.claude/skills/backlog/templates/item.md` — Per-item file template
- `.claude/skills/backlog/templates/milestone-archive.md` — Milestone archive template

## Tests

- `.claude/skills/backlog/tests/test_backlog_gh_first.py` — GitHub-first backlog tests
- `plugins/development-harness/tests/test_comment_operations.py` — Comment list/read operations (19 tests)

## Documentation and Schema

- `.claude/docs/backlog-item-groomed-schema.md` — Groomed item content schema
- `.claude/docs/backlog-lifecycle.draft.md` — Lifecycle documentation (draft)

## Rules

- `.claude/CLAUDE.md` — Section: `## Backlog Operations`

## Hooks

- `.claude/hooks/session-start-backlog.cjs` — Session start backlog prompt
- `.claude/hooks/stop-backlog-reminder.cjs` — Session end reminder

## Helper Scripts

- `.claude/scripts/rebuild_issue_bodies.py` — Rebuild GitHub issue bodies from local files
- `.claude/scripts/repair_from_original_register.py` — Repair items from original register
- `.claude/skills/gh/scripts/github_project_setup.py` — GitHub labels, project, milestone setup

## Architectural Relationships

```text
backlog.py (primary CLI — sole CRUD interface)
  |-- invoked by: create-backlog-item, work-backlog-item, groom-backlog-item skills
  |-- reads/writes: .claude/backlog/*.md (per-item files — local cache)
  |-- syncs with: GitHub Issues (source of truth)
  '-- schema: item-schema.md, state-machine.md

backlog-item-groomer agent
  |-- invoked by: groom-backlog-item skill
  '-- writes via: backlog.py groom subcommand

hooks/
  |-- session-start-backlog.cjs -> prompts user on session start
  '-- stop-backlog-reminder.cjs -> reminder on session end

CLAUDE.md ## Backlog Operations
  '-- rule: "Use backlog.py for all CRUD — no direct edits"
```
