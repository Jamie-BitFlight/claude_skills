---
name: 'SAM: Parallel Execution Details'
description: Detail safe parallelization within SAM pipeline. When can tasks run in parallel? How to handle merge conflicts? Reference GSD wave execution pattern.
metadata:
  topic: sam-parallel-execution-details
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#107'
  last_synced: '2026-03-14T16:01:07Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: parallel execution details** so that **the tooling becomes more capable and complete**.

## Description

Detail safe parallelization within SAM pipeline. When can tasks run in parallel? How to handle merge conflicts? Reference GSD wave execution pattern.

## Suggested Location

[`stateless-software-engineering-framework.md`](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/stateless-software-engineering-framework.md) (new section 2.4 or Appendix)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P2
- **Added**: 2026-02-01
- **Research questions**: How does GSD wave execution work in detail? How do task orchestrators (Temporal, Prefect) handle parallel dependencies? What conflict resolution patterns exist?
