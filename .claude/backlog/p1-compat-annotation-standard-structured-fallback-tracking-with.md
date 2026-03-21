---
name: COMPAT annotation standard — structured fallback tracking with CI enforcement
description: 'Establish a COMPAT annotation standard for all compatibility shims, fallbacks, and temporary workarounds in the codebase. Every fallback must document why it exists, what condition allows removal, and when it was added. A pre-commit hook scans for COMPAT annotations and fails CI when removal conditions are met or annotations are malformed. Companion: ADR records in .claude/decisions/ for architectural decisions that motivated the fallback. Motivated by claim-task fix (2026-03-07) which added a silent field-name fallback with no removal condition documented.'
metadata:
  topic: compat-annotation-standard-structured-fallback-tracking-with
  source: Session observation — claim-task fix introduced silent compatibility shim with no removal tracking
  added: '2026-03-07'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#549'
  last_synced: '2026-03-21T03:45:33Z'
---

## Story

As a **developer using Claude Code skills**, I want to **compat annotation standard — structured fallback tracking with ci enforcement** so that **the tooling becomes more capable and complete**.

## Description

Establish a COMPAT annotation standard for all compatibility shims, fallbacks, and temporary workarounds in the codebase. Every fallback must document why it exists, what condition allows removal, and when it was added. A pre-commit hook scans for COMPAT annotations and fails CI when removal conditions are met or annotations are malformed. Companion: ADR records in .claude/decisions/ for architectural decisions that motivated the fallback. Motivated by claim-task fix (2026-03-07) which added a silent field-name fallback with no removal condition documented.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — claim-task fix introduced silent compatibility shim with no removal tracking
- **Priority**: P1
- **Added**: 2026-03-07
- **Research questions**: None
