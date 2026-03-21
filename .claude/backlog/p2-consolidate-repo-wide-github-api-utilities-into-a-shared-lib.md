---
name: Consolidate repo-wide GitHub API utilities into a shared library
description: 'The repo has shared GitHub API interaction scattered across multiple scripts and plugins (backlog.py, daily-releases scripts, etc.), each with its own inline GitHub client construction, SSL handling, and token management. Success: a single shared github_utils library installable by any script or plugin in the repo via PEP 723 [tool.uv.sources] or a proper package dependency, so all GitHub API work goes through one place. Done when all existing inline GitHub client code is replaced with imports from the shared library and CI stays green.'
metadata:
  topic: consolidate-repo-wide-github-api-utilities-into-a-shared-lib
  source: Session observation
  added: '2026-03-06'
  priority: P2
  type: Refactor
  status: needs-grooming
  issue: '#519'
  last_synced: '2026-03-21T03:45:56Z'
---

## Story

As a **developer using Claude Code skills**, I want to **consolidate repo-wide github api utilities into a shared library** so that **the tooling becomes more capable and complete**.

## Description

The repo has shared GitHub API interaction scattered across multiple scripts and plugins (backlog.py, daily-releases scripts, etc.), each with its own inline GitHub client construction, SSL handling, and token management. Success: a single shared github_utils library installable by any script or plugin in the repo via PEP 723 [tool.uv.sources] or a proper package dependency, so all GitHub API work goes through one place. Done when all existing inline GitHub client code is replaced with imports from the shared library and CI stays green.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation
- **Priority**: P2
- **Added**: 2026-03-06
- **Research questions**: None
