---
name: 'SAM: Partial Success Handling'
description: Define how to represent and handle partial task success. Task completes some DoD items but not all. How is this state represented in artifacts?
metadata:
  topic: sam-partial-success-handling
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#110'
  last_synced: '2026-03-12T12:48:50Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: partial success handling** so that **the tooling becomes more capable and complete**.

## Description

Define how to represent and handle partial task success. Task completes some DoD items but not all. How is this state represented in artifacts?

## Suggested Location

[`stateless-software-engineering-framework.md`](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/stateless-software-engineering-framework.md) (section 3.5 Execution Agent output)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P2
- **Added**: 2026-02-01
- **Research questions**: How do GSD checkpoints represent partial progress? How do CI/CD systems handle partial test passes? What state machine patterns exist?
