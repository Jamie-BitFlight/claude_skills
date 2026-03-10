---
name: 'SAM: Timeout/Stall Detection'
description: Define mechanism to detect when an agent is stuck or has stalled. Include timeout thresholds per stage, health check patterns, and recovery actions.
metadata:
  topic: sam-timeoutstall-detection
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#87'
  plan: ''
  last_synced: '2026-03-10T06:56:54Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: timeout/stall detection** so that **the tooling becomes more capable and complete**.

## Description

Define mechanism to detect when an agent is stuck or has stalled. Include timeout thresholds per stage, health check patterns, and recovery actions.

## Suggested Location

[`stateless-software-engineering-framework.md`](https://github.com/bitflight-devops/stateless-agent-methodology/blob/main/stateless-software-engineering-framework.md) (Orchestrator section 3.8)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P1
- **Added**: 2026-02-01
- **Research questions**: How do orchestration frameworks (Temporal, Prefect, Airflow) handle task timeouts? What heartbeat patterns exist? How does Gas Town handle session recycling?
