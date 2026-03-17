---
name: MCP-based backlog scenario testing with backlog-mcp-validator and backlog-item-groomer
description: Build scenario-based integration tests for the backlog-mcp FastMCP server, organized by the skill/agent workflow that generates each call pattern. 20 scenarios covering create-backlog-item (1), work-backlog-item browse/plan/status/close/resolve (12), groom-backlog-item (4), group-items-to-milestone (1), backlog-item-groomer agent (1), sync+pull (2). Plus 4 error paths (close without checklist, view nonexistent, add duplicate, list empty) and 3 full lifecycle tests (create→close, create→resolve+cleanup, stale discovery). Tests use in-memory FastMCP Client through full operations layer (mocking only at github.py and filesystem boundary), verifying the exact response shapes that each skill reads from tool output. Design documented in session and migration map at .claude/skills/backlog/CLI_TO_MCP_MIGRATION.md.
metadata:
  topic: mcp-based-backlog-scenario-testing-with-backlog-mcp-validato
  source: Session observation
  added: '2026-03-01'
  priority: completed
  type: Feature
  status: done
  issue: '#328'
  groomed: '2026-03-01'
  last_synced: '2026-03-01T08:20:49Z'
  plan: plan/tasks-12-backlog-mcp-scenarios.md
---

## Story

As a **developer**, I want **Build scenario-based integration tests for the backlog-mcp FastMCP server, or...** so that **backlog items are tracked in GitHub**.

## Description

Build scenario-based integration tests for the backlog-mcp FastMCP server, organized by the skill/agent workflow that generates each call pattern. 20 scenarios covering create-backlog-item (1), work-backlog-item browse/plan/status/close/resolve (12), groom-backlog-item (4), group-items-to-milestone (1), backlog-item-groomer agent (1), sync+pull (2). Plus 4 error paths (close without checklist, view nonexistent, add duplicate, list empty) and 3 full lifecycle tests (create→close, create→resolve+cleanup, stale discovery). Tests use in-memory FastMCP Client through full operations layer (mocking only at github.py and filesystem boundary), verifying the exact response shapes that each skill reads from tool output. Design documented in session and migration map at .claude/skills/backlog/CLI_TO_MCP_MIGRATION.md.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation
- **Priority**: P1
- **Added**: 2026-03-01
- **Research questions**: None

## Fact-Check

**Date**: 2026-03-01 | **Claims checked**: 4

| Claim | Verdict | Evidence |
|-------|---------|----------|
| FastMCP Client supports in-memory transport via `Client(mcp)` | VERIFIED | Existing tests at `tests/test_backlog_core_server.py` + [FastMCP docs](https://gofastmcp.com/clients/client) |
| `github.py` serves as boundary layer for GitHub API mocking | VERIFIED | 18 functions centralized in `backlog_core/github.py`; `operations.py` imports only from this module |
| Test design documented in `CLI_TO_MCP_MIGRATION.md` | REFUTED | File is a CLI→MCP migration map (tool mapping + file inventory). Contains no test scenarios, error paths, or lifecycle tests. Test design exists only in the issue description itself. |
| Server exposes 10 MCP tools | VERIFIED | Confirmed 10 `@mcp.tool()` decorators in `server.py`. Issue description lists only 8 — missing `backlog_normalize` and `backlog_pull`. |

**Action items from fact-check**:
- REFUTED claim: Remove reference to CLI_TO_MCP_MIGRATION.md as test design doc. The test scenario design must be created as part of this work.
- Issue description lists only 8 tools but 10 exist — tests must cover all 10.

## RT-ICA

**Goal**: Build scenario-based integration tests that verify the backlog MCP server works correctly through the full operations layer, ensuring skills and agents get the response shapes they depend on.

**Conditions**:

1. FastMCP 3.x in-memory Client transport available | AVAILABLE | Verified in existing tests and official docs
2. backlog_core package with server.py, operations.py, github.py, models.py, parsing.py | AVAILABLE | All modules exist and are tested
3. github.py boundary layer suitable for mocking | AVAILABLE | 18 functions centralized, operations.py imports only from github.py
4. Existing test infrastructure (conftest.py, pytest-asyncio) | AVAILABLE | tests/ directory with conftest.py, asyncio_mode=auto
5. Test design document with 20 scenarios + 4 error paths + 3 lifecycle tests | MISSING | Issue description has the design intent but no formal test scenario spec exists (CLI_TO_MCP_MIGRATION.md claim REFUTED). Must be created as part of this work.
6. Knowledge of exact response shapes each skill reads from tool output | DERIVABLE | Can be derived by reading skill files (work-backlog-item, create-backlog-item, groom-backlog-item, group-items-to-milestone) and agent files (backlog-item-groomer)
7. Filesystem mock strategy (tmp_path or similar) | DERIVABLE | pytest tmp_path fixture is standard; conftest.py may already have patterns
8. All 10 MCP tools documented with expected params and return shapes | AVAILABLE | server.py has full type annotations and docstrings
9. fastmcp-python-tests skill available for test writing guidance | AVAILABLE | User confirmed this skill should be loaded by test writers

**Decision**: APPROVED
**Missing**: None (condition 5 will be created as part of the work; conditions 6-7 are DERIVABLE from codebase)
**Assumptions to confirm**: Response shapes read by each skill (condition 6) — verify during architecture phase

## Groomed (2026-03-01)

### Reproducibility

Tests are written in pytest with async support. Each scenario invokes the in-memory FastMCP Client:

1. Launch the backlog MCP server via in-memory transport (`Client(mcp)`)
2. Call specific tools with documented parameters
3. Parse response dictionary containing data + messages/warnings/errors
4. Compare against expected shapes

Mocking strategy: github.py boundary (18 functions) + tmp_path filesystem. Operations layer NOT mocked.

### Output / Evidence

- Test file: `.claude/skills/backlog/tests/test_backlog_mcp_scenarios.py`
- Response shapes documented in `backlog_core/server.py` (tool docstrings + type annotations)
- Existing test file: `test_backlog_core_server.py` mocks operations layer; new tests mock at github.py and filesystem boundary

### Priority

9/10 — Validates the MCP server implementation before skills migrate to it. Blocks: `p1-migrate-backlog-to-mcp-server-system.md`.

### Impact

- Blocks MCP skill migration — cannot proceed confidently without integration test coverage
- Current test suite (55 tests) mocks operations; new tests verify through full stack
- Catches integration bugs across operations layer + github.py boundary + filesystem interactions

### Scope

- 20 skill/workflow scenarios (create-backlog-item: 1, work-backlog-item browse/plan/status/close/resolve: 12, groom-backlog-item: 4, group-items-to-milestone: 1, backlog-item-groomer agent: 1, sync+pull: 2)
- 4 error paths (close without checklist, view nonexistent, add duplicate, list empty)
- 3 full lifecycle tests (create→close, create→resolve+cleanup, stale discovery)
- All 10 MCP tools covered (add, list, view, sync, close, resolve, update, groom, normalize, pull)

### Acceptance Criteria

1. Test file created at `.claude/skills/backlog/tests/test_backlog_mcp_scenarios.py`
2. 20 scenario tests pass (1 per skill workflow pattern)
3. 4 error path tests pass
4. 3 lifecycle tests pass
5. All 10 MCP tools exercised
6. Operations layer NOT mocked — github.py + filesystem boundary only
7. Each test verifies response shape against what skills/agents expect
8. pytest asyncio_mode=auto; no @pytest.mark.asyncio decorators
9. All existing tests still pass (backward compatibility)

### Dependencies

- Depends on: MCP server implementation (DONE — merged PR #332, 382 tests passing)
- Blocks: p1-migrate-backlog-to-mcp-server-system.md

### Resources

| Type | Item |
|------|------|
| Skill | /fastmcp-python-tests (test design guidance — MUST be loaded by test writers) |
| Agent | @backlog-mcp-validator (tool reference, validation patterns) |
| MCP Server | .claude/skills/backlog/backlog_core/server.py (10 tools) |
| Operations | .claude/skills/backlog/backlog_core/operations.py |
| GitHub Boundary | .claude/skills/backlog/backlog_core/github.py (18 functions, mocking point) |
| Existing Tests | .claude/skills/backlog/tests/test_backlog_core_server.py (55 tests, pattern reference) |
| Skill Files | work-backlog-item, create-backlog-item, groom-backlog-item, group-items-to-milestone |
| Agent File | .claude/agents/backlog-item-groomer.md |
| Migration Map | .claude/skills/backlog/CLI_TO_MCP_MIGRATION.md (tool signatures) |

### Effort

High (estimated complexity). Test design + fixtures + 27 scenario implementations + debugging.

### Blockers

None — RT-ICA APPROVED. All prerequisites available or derivable.