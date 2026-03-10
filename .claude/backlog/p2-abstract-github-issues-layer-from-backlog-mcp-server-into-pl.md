---
name: Abstract GitHub Issues layer from backlog MCP server into pluggable backend
description: 'The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Issues as its issue-tracking backend. Every operation — add, list, sync, close, resolve, groom — assumes GitHub Issues API. This prevents using the backlog system with GitLab, Jira, databases, or alternative agent task systems like GSD (get-shit-done), Superpowers, or Beads. Success: a clean backend protocol/interface with 2+ working backends shipped (GitHub Issues as default + at least one alternative like Beads graph tracker or SQLite) proving the abstraction works. You know it works when the same 10 MCP tools produce equivalent behavior against a different backend with zero changes to skill workflows or MCP tool signatures. Research refs: research/agent-frameworks/get-shit-done.md, research/agent-frameworks/superpowers.md, research/task-management/beads.md.'
metadata:
  topic: abstract-github-issues-layer-from-backlog-mcp-server-into-pl
  source: User request
  added: '2026-03-02'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#389'
  last_synced: '2026-03-10T06:56:22Z'
  groomed: '2026-03-02'
---

## Story

As a **developer**, I want **The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Is...** so that **backlog items are tracked in GitHub**.

## Description

The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Issues as its issue-tracking backend. Every operation — add, list, sync, close, resolve, groom — assumes GitHub Issues API. This prevents using the backlog system with GitLab, Jira, databases, or alternative agent task systems like GSD (get-shit-done), Superpowers, or Beads. Success: a clean backend protocol/interface with 2+ working backends shipped (GitHub Issues as default + at least one alternative like Beads graph tracker or SQLite) proving the abstraction works. You know it works when the same 10 MCP tools produce equivalent behavior against a different backend with zero changes to skill workflows or MCP tool signatures. Research refs: research/agent-frameworks/get-shit-done.md, research/agent-frameworks/superpowers.md, research/task-management/beads.md.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P2
- **Added**: 2026-03-02
- **Research questions**: None

## Story

As a **developer**, I want **The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Is...** so that **backlog items are tracked in GitHub**.

## Description

The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Issues as its issue-tracking backend. Every operation — add, list, sync, close, resolve, groom — assumes GitHub Issues API. This prevents using the backlog system with GitLab, Jira, databases, or alternative agent task systems like GSD (get-shit-done), Superpowers, or Beads. Success: a clean backend protocol/interface with 2+ working backends shipped (GitHub Issues as default + at least one alternative like Beads graph tracker or SQLite) proving the abstraction works. You know it works when the same 10 MCP tools produce equivalent behavior against a different backend with zero changes to skill workflows or MCP tool signatures. Research refs: research/agent-frameworks/get-shit-done.md, research/agent-frameworks/superpowers.md, research/task-management/beads.md.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P2
- **Added**: 2026-03-02
- **Research questions**: None

## Story

As a **developer**, I want **The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Is...** so that **backlog items are tracked in GitHub**.

## Description

The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Issues as its issue-tracking backend. Every operation — add, list, sync, close, resolve, groom — assumes GitHub Issues API. This prevents using the backlog system with GitLab, Jira, databases, or alternative agent task systems like GSD (get-shit-done), Superpowers, or Beads. Success: a clean backend protocol/interface with 2+ working backends shipped (GitHub Issues as default + at least one alternative like Beads graph tracker or SQLite) proving the abstraction works. You know it works when the same 10 MCP tools produce equivalent behavior against a different backend with zero changes to skill workflows or MCP tool signatures. Research refs: research/agent-frameworks/get-shit-done.md, research/agent-frameworks/superpowers.md, research/task-management/beads.md.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P2
- **Added**: 2026-03-02
- **Research questions**: None

## Story

As a **developer using Claude Code skills**, I want to **abstract github issues layer from backlog mcp server into pluggable backend** so that **the tooling becomes more capable and complete**.

## Description

The backlog MCP server (10 tools, 382+ tests) is tightly coupled to GitHub Issues as its issue-tracking backend. Every operation — add, list, sync, close, resolve, groom — assumes GitHub Issues API. This prevents using the backlog system with GitLab, Jira, databases, or alternative agent task systems like GSD (get-shit-done), Superpowers, or Beads. Success: a clean backend protocol/interface with 2+ working backends shipped (GitHub Issues as default + at least one alternative like Beads graph tracker or SQLite) proving the abstraction works. You know it works when the same 10 MCP tools produce equivalent behavior against a different backend with zero changes to skill workflows or MCP tool signatures. Research refs: research/agent-frameworks/get-shit-done.md, research/agent-frameworks/superpowers.md, research/task-management/beads.md.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P2
- **Added**: 2026-03-02
- **Research questions**: None

## Fact-Check

**Date**: 2026-03-02
**Claims checked**: 5

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | 10 MCP tools in backlog server | VERIFIED | 10 @mcp.tool() decorators in backlog_core/server.py |
| 2 | 382+ tests | REFUTED (minor) | 380 test functions found across test suite — 2 short of claim |
| 3 | Every operation assumes GitHub Issues API | VERIFIED | operations.py imports/calls GitHub client in add, list, sync, close, resolve, groom |
| 4 | GSD (get-shit-done) is a real system | VERIFIED | npm get-shit-done-cc@1.22.0, GitHub glittercowboy/get-shit-done (accessed 2026-03-02) |
| 5 | Beads is distributed git-backed graph tracker using Dolt | VERIFIED | GitHub steveyegge/beads, ARCHITECTURE.md confirms Dolt storage (accessed 2026-03-02) |

**VERIFIED**: 4 | **REFUTED**: 1 (minor — 380 tests not 382+) | **INCONCLUSIVE**: 0

## RT-ICA

**Goal**: Define a backend protocol/interface so any issue tracker can be plugged into the backlog MCP server, and ship with 2+ working backends proving the abstraction.

**Conditions**:

| # | Condition | Status | Info Needed |
|---|-----------|--------|-------------|
| 1 | Current GitHub coupling surface area mapped | AVAILABLE | github.py (268 lines), operations.py imports 12+ GitHub functions |
| 2 | MCP tool signatures documented (10 tools) | AVAILABLE | server.py: add, list, view, sync, close, resolve, update, groom, normalize, pull |
| 3 | Test suite exists (380 tests) | AVAILABLE | 7 test files; count verified (380, not 382+ as claimed) |
| 4 | Backend protocol/interface design | MISSING | No protocol exists yet — this IS the deliverable |
| 5 | Alternative backend candidates identified | AVAILABLE | Beads (Dolt), SQLite, GitLab, Jira — research refs verified |
| 6 | Beads API/integration surface documented | DERIVABLE | research/task-management/beads.md exists; full API not mapped |
| 7 | SQLite schema for equivalent operations | MISSING | No schema exists |
| 8 | Migration path from current monolith | MISSING | No refactoring strategy defined |
| 9 | Test strategy for multi-backend verification | MISSING | No test harness for backend-agnostic testing |
| 10 | GSD/Superpowers integration surface | DERIVABLE | Research files exist; integration mapping not done |

**Decision**: APPROVED (4 MISSING conditions are deliverables, not blockers)
**Missing as blockers**: None
**Missing as deliverables**: Backend protocol design, SQLite schema, migration path, test strategy

## Groomed (2026-03-02)

### Issue Classification

**Type**: unbounded-design
**Rationale**: The backlog system works correctly for GitHub Issues but was designed without a backend abstraction layer. No failure triggered this — it is a design limitation that prevents multi-platform support.
**Analysis Method**: design-framing
**Scenario Target**: User wants to use backlog system with a non-GitHub backend (GitLab, Jira, Beads, SQLite) -> All 10 MCP tools work identically against any conforming backend without code changes to server.py or skill workflows

### Priority

8/10 — P2 system design work. Unblocks 5+ downstream features (GitLab/Jira integration, alternative task systems like Beads, GSD compatibility). Enables distributed backlog architecture for multi-machine/multi-agent workflows.

### Impact

- Blocks: Alternative backend support; GitLab, Jira, Beads integration; distributed team workflows
- Bottleneck: Current GitHub coupling prevents adoption by teams using non-GitHub platforms; blocks GSD/Superpowers framework compatibility

### Scope

### Benefits

- Same 10 MCP tools work against any conforming backend (GitHub Issues, Beads, SQLite, GitLab, Jira)
- Enables backlog system to support alternative agent task systems (GSD, Superpowers)
- Establishes pluggable architecture pattern for future backend additions
- Reduces lock-in to GitHub Issues API
- Proves the abstraction works with 2+ reference implementations

### Expected Behavior

Backend protocol exists and is documented. Two working implementations (GitHub Issues + one alternative like Beads or SQLite) can be swapped by changing a configuration value. Skill workflows (create-backlog-item, work-backlog-item, groom-backlog-item) require zero code changes when backend changes.

### Acceptance Criteria

1. Backend protocol documented (interface, method signatures, return types, error contracts) with clear contract for each of 10 MCP tool operations
2. GitHub Issues backend extracted from current github.py into dedicated backend module, passing all 380 existing tests
3. At least one alternative backend implemented (Beads or SQLite) with equivalent functionality for all 10 operations
4. Backend factory selects implementation by environment variable or config file
5. Cross-backend test suite verifies identical behavior across all backends
6. All 10 MCP tools callable from server.py with zero changes to tool signatures
7. Skill workflows unchanged: create-backlog-item, work-backlog-item, groom-backlog-item invoke same MCP tools regardless of backend
8. 380+ existing tests still passing after refactoring
9. Documentation updated: describes backend protocol, configuration, adding new backends

### Dependencies

- **Depends on**: #329 (migrate backlog to MCP server) should be completed first so MCP layer is stable
- **Blocks**: Any future backends (GitLab, Jira, Beads integration items)
- **Related**: #282 (GitHub-first backlog redesign) and #255 (backlog MCP server conversion, resolved) provide architectural context

### Research

| Source | Path | Key Insight |
|--------|------|-------------|
| Beads | research/task-management/beads.md | Distributed git-backed graph tracker using Dolt (versioned SQL); bd ready for agent work queues; 17,269 stars |
| GSD | research/agent-frameworks/get-shit-done.md | Meta-prompting system; 11 agents, XML task format, file-based state (STATE.md, ROADMAP.md); 10,193 stars |
| Superpowers | research/agent-frameworks/superpowers.md | 14-skill dev workflow framework with spec-driven execution; 40,911 stars |

### Files

| File | Role | Lines |
|------|------|-------|
| .claude/skills/backlog/backlog_core/github.py | GitHub-specific client wrapper | ~268 |
| .claude/skills/backlog/backlog_core/operations.py | All backlog operations (tightly coupled to GitHub) | ~1400+ |
| .claude/skills/backlog/backlog_core/server.py | MCP tool definitions (10 tools) | ~340 |
| .claude/skills/backlog/backlog_core/models.py | Data models (BacklogItem, etc.) | — |
| .claude/skills/backlog/backlog_core/parsing.py | Markdown/frontmatter parsing | — |
| .claude/skills/backlog/tests/ | 380 tests across 7 test files | — |

### Skills

- /backlog — main backlog interface (skill under refactoring)
- /python3-development — Python architecture and testing
- /fastmcp-creator — MCP server patterns

### Agents

- @python3-development:python-cli-architect — for protocol design and implementation
- @python3-development:python-pytest-architect — for cross-backend test harness
- @python3-development:codebase-analyzer — for coupling surface area analysis

### Decision

RT-ICA APPROVED. No blockers — all MISSING conditions are deliverables. Effort: High (protocol design + GitHub extraction + 2 new backends + cross-backend test harness). Recommended phasing: (1) protocol design + validation, (2) GitHub backend extraction, (3) alternative backend implementation, (4) cross-backend test suite, (5) documentation.
