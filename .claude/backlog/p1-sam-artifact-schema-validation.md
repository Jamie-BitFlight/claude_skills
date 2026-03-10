---
name: 'SAM: Artifact Schema Validation'
description: Define formal validation rules or JSON schemas for artifact formats. Currently only templates provided. Enable automated validation at stage boundaries.
metadata:
  topic: sam-artifact-schema-validation
  source: Gap analysis of SAM framework
  added: '2026-02-01'
  priority: P1
  type: Feature
  status: needs-grooming
  issue: '#88'
  plan: ''
  last_synced: '2026-03-10T06:56:54Z'
---

## Story

As a **developer using Claude Code skills**, I want to **sam: artifact schema validation** so that **the tooling becomes more capable and complete**.

## Description

Define formal validation rules or JSON schemas for artifact formats. Currently only templates provided. Enable automated validation at stage boundaries.

## Suggested Location

[`sam-artifact-schemas/`](https://github.com/bitflight-devops/stateless-agent-methodology) (new directory with schema files)

## Context

- **Source**: Gap analysis of SAM framework
- **Priority**: P1
- **Added**: 2026-02-01
- **Research questions**: How do GSD artifacts (STATE.md, ROADMAP.md) enforce structure? What validation approaches exist in BMAD-METHOD? JSON Schema vs YAML validation vs custom parsers?
