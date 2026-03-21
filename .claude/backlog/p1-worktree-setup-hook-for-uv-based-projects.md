---
name: Worktree setup hook for uv-based projects
description: Add a WorktreeCreate hook that auto-runs uv sync and uv run prek install when worktrees are created for parallel agent work. Workers in /work-milestone need dependencies installed in their worktrees. Pattern sourced from Citadel worktree-setup.js — adapted for our uv-based toolchain.
metadata:
  topic: worktree-setup-hook-for-uv-based-projects
  source: Citadel assessment .claude/reports/citadel-assessment-20260320.md
  added: '2026-03-21'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#928'
  last_synced: '2026-03-21T03:45:06Z'
---

## Story

As a **developer using Claude Code skills**, I want to **worktree setup hook for uv-based projects** so that **the tooling becomes more capable and complete**.

## Description

Add a WorktreeCreate hook that auto-runs uv sync and uv run prek install when worktrees are created for parallel agent work. Workers in /work-milestone need dependencies installed in their worktrees. Pattern sourced from Citadel worktree-setup.js — adapted for our uv-based toolchain.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Citadel assessment .claude/reports/citadel-assessment-20260320.md
- **Priority**: P1
- **Added**: 2026-03-21
- **Research questions**: None
