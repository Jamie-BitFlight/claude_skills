---
name: Fix $N corruption in bash-development and perl-development SKILL.md code examples
description: "bash-development and perl-development plugin SKILL.md files contain shell code examples with `$N` variable references (including `${N}` brace form). All forms are substituted by the skill engine at load time — there is no safe escape in SKILL.md body.\n\nAffected files confirmed via grep:\n- plugins/bash-development/skills/bash-portability/SKILL.md — ${1} × 5\n- plugins/bash-development/skills/bash-testing/SKILL.md — ${1}, ${2}\n- plugins/bash-development/skills/bash-logging/SKILL.md — ${1}, ${2}\n- plugins/bash-development/skills/bash-development/SKILL.md — ${1}, ${2}\n- plugins/bash-development/skills/bash-52-features/SKILL.md — many ${N} occurrences\n- plugins/bash-development/skills/bash-53-features/SKILL.md — many ${N} occurrences\n- plugins/perl-development/skills/perl-lint/SKILL.md — ${1}\n- plugins/perl-development/skills/perl-validate/SKILL.md — ${1}\n\nWhen invoked with arguments, `${1}` renders as the argument value, corrupting code examples. When invoked without arguments, `${1}` renders as empty string, also corrupting examples.\n\nFix: Move all shell code examples containing `$N` patterns from SKILL.md body into `references/*.md` files. Reference files are NOT subject to substitution. Link to them from SKILL.md.\n\nNote: These skills have no `argument-hint` frontmatter and are not argument-routing skills. Their code examples are reference material that should live in reference files regardless."
metadata:
  topic: fix-n-corruption-in-bash-development-and-perl-development-sk
  source: Session 2026-03-08 — canary testing of argument substitution
  added: '2026-03-08'
  priority: P1
  type: Bug
  status: needs-grooming
  issue: '#552'
  last_synced: '2026-03-10T06:55:34Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix $n corruption in bash-development and perl-development skill.md code examples** so that **the tool works correctly and reliably**.

## Description

bash-development and perl-development plugin SKILL.md files contain shell code examples with `$N` variable references (including `${N}` brace form). All forms are substituted by the skill engine at load time — there is no safe escape in SKILL.md body.

Affected files confirmed via grep:
- plugins/bash-development/skills/bash-portability/SKILL.md — ${1} × 5
- plugins/bash-development/skills/bash-testing/SKILL.md — ${1}, ${2}
- plugins/bash-development/skills/bash-logging/SKILL.md — ${1}, ${2}
- plugins/bash-development/skills/bash-development/SKILL.md — ${1}, ${2}
- plugins/bash-development/skills/bash-52-features/SKILL.md — many ${N} occurrences
- plugins/bash-development/skills/bash-53-features/SKILL.md — many ${N} occurrences
- plugins/perl-development/skills/perl-lint/SKILL.md — ${1}
- plugins/perl-development/skills/perl-validate/SKILL.md — ${1}

When invoked with arguments, `${1}` renders as the argument value, corrupting code examples. When invoked without arguments, `${1}` renders as empty string, also corrupting examples.

Fix: Move all shell code examples containing `$N` patterns from SKILL.md body into `references/*.md` files. Reference files are NOT subject to substitution. Link to them from SKILL.md.

Note: These skills have no `argument-hint` frontmatter and are not argument-routing skills. Their code examples are reference material that should live in reference files regardless.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session 2026-03-08 — canary testing of argument substitution
- **Priority**: P1
- **Added**: 2026-03-08
- **Research questions**: None
