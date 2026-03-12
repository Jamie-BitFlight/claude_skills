---
name: 'SAM: Error Recovery / Rollback Procedures'
description: Define explicit procedure when a task fails irrecoverably. How to undo artifact changes? How to restore artifact plane to consistent state after failure?
metadata:
  topic: sam-error-recovery-rollback-procedures
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#85'
  plan: ''
  last_synced: '2026-03-12T12:49:04Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: error recovery / rollback procedures** so that **the tooling becomes more capable and complete**.

## Description

Define explicit procedure when a task fails irrecoverably. How to undo artifact changes? How to restore artifact plane to consistent state after failure?

## Suggested Location

[`stateless-software-engineering-framework.md`](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/stateless-software-engineering-framework.md) (new Appendix or Part 6 addition)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P1
- **Added**: 2026-02-01
- **Research questions**: How do GSD, BMAD-METHOD, AutoGPT, and traditional CI/CD handle rollback? What patterns exist for transactional artifact updates?

## Plan

plan/tasks-5-sam-error-recovery.md
