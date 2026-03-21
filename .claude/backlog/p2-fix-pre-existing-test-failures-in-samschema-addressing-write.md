---
name: Fix pre-existing test failures in sam_schema (addressing + writer)
description: "5 pre-existing test failures confirmed on baseline commit 699a66b6 before any changes in this session.\n\nFailures:\n1. `tests/test_addressing_pnnn.py::TestParseAddressPNNN::test_parse_address_rejects_invalid[empty]` — regex `'Invalid'` does not match actual error `\"Address cannot be empty: ''\"` (4 parametrized cases: empty, trailing-slash, traversal, absolute)\n2. `tests/test_writers_new.py::TestAtomicWriteSafety::test_atomic_write_cleans_up_temp_file_on_failure` — assertion failure in atomic write cleanup path\n\nRoot cause not investigated. Addressing failures are a regex mismatch between the test expectation and the actual error message in `resolve_plan_address`. Writer failure requires inspection of the atomic write path.\n\nFiles to investigate:\n- `packages/sam_schema/sam_schema/core/addressing.py`\n- `packages/sam_schema/tests/test_addressing_pnnn.py`\n- `packages/sam_schema/sam_schema/writers/yaml_writer.py`\n- `packages/sam_schema/tests/test_writers_new.py`"
metadata:
  topic: fix-pre-existing-test-failures-in-samschema-addressing-write
  source: fastmcp-audit session 2026-03-15 — found during full test suite run
  added: '2026-03-16'
  priority: P2
  type: Bug
  status: needs-grooming
  issue: '#744'
  last_synced: '2026-03-21T03:45:22Z'
---

## Story

As a **developer relying on this plugin**, I want to **fix pre-existing test failures in sam_schema (addressing + writer)** so that **the tool works correctly and reliably**.

## Description

5 pre-existing test failures confirmed on baseline commit 699a66b6 before any changes in this session.

Failures:
1. `tests/test_addressing_pnnn.py::TestParseAddressPNNN::test_parse_address_rejects_invalid[empty]` — regex `'Invalid'` does not match actual error `"Address cannot be empty: ''"` (4 parametrized cases: empty, trailing-slash, traversal, absolute)
2. `tests/test_writers_new.py::TestAtomicWriteSafety::test_atomic_write_cleans_up_temp_file_on_failure` — assertion failure in atomic write cleanup path

Root cause not investigated. Addressing failures are a regex mismatch between the test expectation and the actual error message in `resolve_plan_address`. Writer failure requires inspection of the atomic write path.

Files to investigate:
- `packages/sam_schema/sam_schema/core/addressing.py`
- `packages/sam_schema/tests/test_addressing_pnnn.py`
- `packages/sam_schema/sam_schema/writers/yaml_writer.py`
- `packages/sam_schema/tests/test_writers_new.py`

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: fastmcp-audit session 2026-03-15 — found during full test suite run
- **Priority**: P2
- **Added**: 2026-03-16
- **Research questions**: None
