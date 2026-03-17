---
name: Fix pre-existing CI check failures on main
description: "6 CI checks fail on main (and all PRs) due to pre-existing issues:\n\n1. Python/Ruff: DOC201/ANN401/S202/PLR0911 in gh/, research-curator/, session-historian/, agentskill-kaizen/, plugin-creator/, uv/ scripts\n2. Python/ty: unresolved gitlab imports + mix_stderr arg removed in newer click (gh tests, plugin-creator conftest)\n3. Python/Tests: CliRunner mix_stderr (~30 ERRORs in plugin-creator) + panel.extension missing in agentskill-kaizen\n4. JSON/Prettier: plugins/agentskill-kaizen/.mcp.json and plu"
metadata:
  topic: fix-pre-existing-ci-check-failures-on-main
  source: Not specified
  added: '2026-02-26'
  priority: completed
  type: Bug
  status: done
  issue: '#281'
  groomed: '2026-02-28'
  last_synced: '2026-02-28T05:33:17Z'
---

## Story

As a **developer**, I want **6 CI checks fail on main (and all PRs) due to pre-existing issues:

1** so that **backlog items are tracked in GitHub**.

## Description

6 CI checks fail on main (and all PRs) due to pre-existing issues:

1. Python/Ruff: DOC201/ANN401/S202/PLR0911 in gh/, research-curator/, session-historian/, agentskill-kaizen/, plugin-creator/, uv/ scripts
2. Python/ty: unresolved gitlab imports + mix_stderr arg removed in newer click (gh tests, plugin-creator conftest)
3. Python/Tests: CliRunner mix_stderr (~30 ERRORs in plugin-creator) + panel.extension missing in agentskill-kaizen
4. JSON/Prettier: plugins/agentskill-kaizen/.mcp.json and plu

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Not specified
- **Priority**: medium
- **Added**: 2026-02-26
- **Research questions**: None

## Fact-Check

Fact-Check Summary: Fix pre-existing CI check failures on main
Checked against: CI run 22514177691 (2026-02-28T05:20, main branch, commit 344d2ffc)
Claims checked: 4

REFUTED (3):
- Python/Ruff DOC201/ANN401/S202/PLR0911 failures: Ruff job passes on main as of 2026-02-28
- Python/ty unresolved gitlab imports + mix_stderr: ty job passes on main as of 2026-02-28
- JSON/Prettier formatting failures: Prettier job passes on main as of 2026-02-28

PARTIALLY VERIFIED (1):
- Python/Tests failures: Issue claims ~30 ERRORs from CliRunner mix_stderr + panel.extension.
  Actual: 1 test fails (test_update_plugin_json_writes_prettier_compatible_format) due to
  npm/prettier ENOTEMPTY race condition in CI causing fallback to non-prettier JSON format.

NEW FINDING (not in original issue):
- Local/Manifest sync: Drift detected — stale command ./commands/rwr/cite.md (the-rewrite-room)
  and stale plugin hallucination-detector in marketplace manifest.

CURRENT SCOPE (reduced from 6 to 2 failing jobs):
1. Python/Tests: 1 test failure — prettier format assertion
2. Local/Manifest sync: manifest drift — stale entries need removal

## RT-ICA

RT-ICA: Fix pre-existing CI check failures on main
Goal: Make all CI jobs pass on main so PRs are not blocked by pre-existing failures
Decision: APPROVED

Conditions:
1. Access to CI workflow files (.github/workflows/) | AVAILABLE | Files in repo
2. Access to failing test source code | AVAILABLE | plugins/plugin-creator/tests/test_auto_sync_manifests.py
3. Understanding of prettier formatting assertion | AVAILABLE | Test expects single-line JSON but prettier produces multi-line
4. Access to manifest sync script | AVAILABLE | Scripts in repo
5. Knowledge of stale manifest entries | AVAILABLE | CI output names: commands/rwr/cite.md (the-rewrite-room), hallucination-detector plugin
6. Ability to run tests locally | AVAILABLE | uv run pytest
7. Ability to run manifest sync locally | AVAILABLE | uv run manifest_sync script

Missing: None
Assumptions to confirm: None — all conditions directly observable from CI output and codebase

## Groomed (2026-02-28)

### Priority

7/10 — Reduced from 6 failures to 2 on main. Blocks all PR merges and branch protection enforcement.

### Impact

- Blocks: All PRs show 2 failed CI jobs (Python/Tests, Local/Manifest sync)
- Bottleneck: Main branch cannot achieve clean CI; blocks branch protection rules

### Benefits

- All CI jobs pass on main — unblocks PRs and merges
- Enables required status checks for branch protection
- Removes pre-existing failure confusion for contributors

### Acceptance Criteria

1. Python/Tests: test_update_plugin_json_writes_prettier_compatible_format passes
2. Local/Manifest sync: zero drift reported by auto_sync_manifests.py --reconcile --dry-run
3. Both jobs consistently pass on main and new PRs
4. No regression in other CI jobs (Ruff, ty, Prettier, validation)

### Resources

| Type | Item |
|------|------|
| Script | plugins/plugin-creator/scripts/auto_sync_manifests.py |
| Test | plugins/plugin-creator/tests/test_auto_sync_manifests.py |
| Workflow | .github/workflows/code-quality.yml |
| Prior work | completed-resolve-manifest-drift-to-make-ci-sync-check-blocking.md |

### Dependencies

- Depends on: None
- Blocks: PR merges, branch protection, clean CI

### Blockers

None — RT-ICA APPROVED. All conditions available.

### Effort

Medium — Two distinct failures (test assertion format mismatch + manifest drift cleanup), both isolated to known files. Estimated 2-4 hours.