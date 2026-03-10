---
name: 'SAM: Scope Creep Detection'
description: Define mechanism to detect when execution diverges from plan. How does Forensic Review detect that the execution agent solved a different problem than planned?
metadata:
  topic: sam-scope-creep-detection
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#89'
  plan: ''
  last_synced: '2026-03-10T06:56:53Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: scope creep detection** so that **the tooling becomes more capable and complete**.

## Description

Define mechanism to detect when execution diverges from plan. How does Forensic Review detect that the execution agent solved a different problem than planned?

## Suggested Location

[`stateless-software-engineering-framework.md`](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/stateless-software-engineering-framework.md) (section 3.6 Forensic Review)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P1
- **Added**: 2026-02-01
- **Research questions**: How does GSD plan-checker detect deviation? What diff/comparison techniques exist? How do code review tools detect scope creep in PRs?
