---
name: Simplify review fixes for milestone orchestration tooling
description: '21 findings from code reuse, quality, and efficiency reviews of the milestone orchestration tooling (commits 5d3737f7 through 3b747046). HIGH items: (1) gates.py subprocess.run has no timeout — hung command blocks indefinitely, (2) batch_fetch_statuses drops closed-but-milestoned issues with state=open, (3) duplicate test file tests/test_gates.py vs test_dispatch_schema/test_gates.py, (4) _MIN_CONFLICT_GROUP_SIZE duplicated in operations.py and validator.py, (5) _validate_milestone_number only called in create not other functions. MEDIUM items: CommandResult.passed redundant state, dependency inversion backlog_core importing dispatch_schema, union-find missing rank, yaml_reader unnecessary deep copy, cached GitHub repo handle. LOW: regex pattern repeated, base model extraction, _keys_to_kebab double traversal, shutil.which not cached, _parse_impact_radius_paths belongs in parsing.py.'
metadata:
  topic: simplify-review-fixes-for-milestone-orchestration-tooling
  source: 'GitHub Issue #938'
  added: '2026-03-21'
  priority: P1
  type: Refactor
  status: in-progress
  issue: '#938'
  last_synced: '2026-03-21T03:45:00Z'
  groomed: '2026-03-21'
  plan: plan/tasks-4-simplify-review-fixes.md
---

## Story

As a **maintainer of the codebase**, I want to **simplify review fixes for milestone orchestration tooling** so that **the code is cleaner and more maintainable**.

## Description

21 findings from code reuse, quality, and efficiency reviews of the milestone orchestration tooling (commits 5d3737f7 through 3b747046). HIGH items: (1) gates.py subprocess.run has no timeout — hung command blocks indefinitely, (2) batch_fetch_statuses drops closed-but-milestoned issues with state=open, (3) duplicate test file tests/test_gates.py vs test_dispatch_schema/test_gates.py, (4) _MIN_CONFLICT_GROUP_SIZE duplicated in operations.py and validator.py, (5) _validate_milestone_number only called in create not other functions. MEDIUM items: CommandResult.passed redundant state, dependency inversion backlog_core importing dispatch_schema, union-find missing rank, yaml_reader unnecessary deep copy, cached GitHub repo handle. LOW: regex pattern repeated, base model extraction, _keys_to_kebab double traversal, shutil.which not cached, _parse_impact_radius_paths belongs in parsing.py.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Simplify review of milestone orchestration session 2026-03-21
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None

## RT-ICA

<div><sub>2026-03-21T02:37:53Z</sub>

APPROVED — 21 findings with file locations documented. Target files exist. Test infrastructure in place.
</div>
