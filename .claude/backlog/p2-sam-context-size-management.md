---
name: 'SAM: Context Size Management'
description: Define explicit guidance for measuring and managing context size per agent. What's the target token budget? How to detect context pressure?
metadata:
  topic: sam-context-size-management
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#111'
  last_synced: '2026-03-21T03:46:39Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: context size management** so that **the tooling becomes more capable and complete**.

## Description

Define explicit guidance for measuring and managing context size per agent. What's the target token budget? How to detect context pressure?

## Suggested Location

[`stateless-software-engineering-framework.md`](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/stateless-software-engineering-framework.md) (section 2.1 or Appendix C)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P2
- **Added**: 2026-02-01
- **Research questions**: How do agent frameworks measure context usage? What token counting approaches exist? How does Claude Code handle context limits internally?
