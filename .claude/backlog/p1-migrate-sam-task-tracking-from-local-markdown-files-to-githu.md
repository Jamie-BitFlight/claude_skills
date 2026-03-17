---
name: Migrate SAM task tracking from local markdown files to GitHub sub-issues via backlog MCP
description: "Currently the SAM workflow splits task tracking across two systems:\n- GitHub Issues (via backlog MCP) for stories/backlog items\n- Local `plan/tasks-*.md` files for task status, with `implementation_manager.py` and `task_status_hook.py` managing state\n\n**Proposed architecture:** Unify everything in GitHub Issues using sub-issues.\n- Stories = GitHub Issues (existing)\n- Tasks within a story = GitHub sub-issues of the story issue\n- Research artifacts = tracked as linked issues or issue comments\n- Backlog MCP = extended to handle sub-issue CRUD, status transitions, and readiness queries\n\n**What needs to change:**\n1. Extend backlog MCP server to support sub-issue creation, status query, and dependency-based readiness logic\n2. Replace `implementation_manager.py` task status queries with MCP calls to GitHub sub-issues\n3. Replace `task_status_hook.py` file edits with GitHub API calls (via MCP or CLI) on `PostToolUse`/`SubagentStop` events\n4. Add research artifact tracking (currently absent) as linked issues on the story\n5. Decide offline/network dependency tradeoff — current system works without GitHub; sub-issues require network on every status check\n\n**Benefits:**\n- Single source of truth — no drift between local files and GitHub state\n- Removes accidental complexity (local markdown task files existed because sub-issues weren't prioritized)\n- Better visibility for collaborators\n- Backlog MCP already does CRUD on issues — extending to sub-issues is natural\n\n**Key risk:** Hook scripts fire frequently (every Write/Edit/Bash in a task session); each hook becoming a GitHub API call adds latency and network dependency."
metadata:
  topic: migrate-sam-task-tracking-from-local-markdown-files-to-githu
  source: Architecture discussion — session 2026-03-06
  added: '2026-03-06'
  priority: completed
  type: Refactor
  status: done
  issue: '#480'
  last_synced: '2026-03-06T21:54:09Z'
  groomed: '2026-03-06'
  plan: plan/tasks-2-migrate-sam-task-github-subissues.md
---

## Story

As a **maintainer of the codebase**, I want to **migrate sam task tracking from local markdown files to github sub-issues via backlog mcp** so that **the code is cleaner and more maintainable**.

## Description

Currently the SAM workflow splits task tracking across two systems:
- GitHub Issues (via backlog MCP) for stories/backlog items
- Local `plan/tasks-*.md` files for task status, with `implementation_manager.py` and `task_status_hook.py` managing state

**Proposed architecture:** Unify everything in GitHub Issues using sub-issues.
- Stories = GitHub Issues (existing)
- Tasks within a story = GitHub sub-issues of the story issue
- Research artifacts = tracked as linked issues or issue comments
- Backlog MCP = extended to handle sub-issue CRUD, status transitions, and readiness queries

**What needs to change:**
1. Extend backlog MCP server to support sub-issue creation, status query, and dependency-based readiness logic
2. Replace `implementation_manager.py` task status queries with MCP calls to GitHub sub-issues
3. Replace `task_status_hook.py` file edits with GitHub API calls (via MCP or CLI) on `PostToolUse`/`SubagentStop` events
4. Add research artifact tracking (currently absent) as linked issues on the story
5. Decide offline/network dependency tradeoff — current system works without GitHub; sub-issues require network on every status check

**Benefits:**
- Single source of truth — no drift between local files and GitHub state
- Removes accidental complexity (local markdown task files existed because sub-issues weren't prioritized)
- Better visibility for collaborators
- Backlog MCP already does CRUD on issues — extending to sub-issues is natural

**Key risk:** Hook scripts fire frequently (every Write/Edit/Bash in a task session); each hook becoming a GitHub API call adds latency and network dependency.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Architecture discussion — session 2026-03-06
- **Priority**: P1
- **Added**: 2026-03-06
- **Research questions**: None

## Fact-Check

**Date**: 2026-03-06
**Claims checked**: 5

| Verdict | Count |
|---------|-------|
| VERIFIED | 4 |
| REFUTED | 1 |
| INCONCLUSIVE | 0 |

### Claim 1: GitHub sub-issues REST API is generally available

**VERDICT**: REFUTED
**Source**: GitHub Changelog Dec 2024, Sep 2025; docs.github.com/en/rest/issues/sub-issues (accessed 2026-03-06)
**Evidence**: Dec 2024 announcement explicitly states "available in public preview". No GA announcement found through Mar 2026.
**Citation**: [GitHub Changelog - REST API for sub-issues (Dec 2024)](https://github.blog/changelog/2024-12-12-github-issues-projects-close-issue-as-a-duplicate-rest-api-for-sub-issues-and-more/)

### Claim 2: PyGitHub venv has `get_sub_issues()` / `add_sub_issue()` methods

**VERDICT**: VERIFIED
**Source**: `.venv/lib/python3.11/site-packages/github/Issue.py` lines 572–602 (accessed 2026-03-06)
**Evidence**: Both methods present; `add_sub_issue()` uses `sub_issue.id` (not `.number`).

### Claim 3: `implementation_manager.py` uses local files only (no GitHub API calls)

**VERDICT**: VERIFIED
**Source**: `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` (accessed 2026-03-06)
**Evidence**: No GitHub imports; all status operations parse local `plan/tasks-*.md` files via `Path`.

### Claim 4: `task_status_hook.py` edits local markdown files only (no GitHub calls)

**VERDICT**: VERIFIED
**Source**: `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` (accessed 2026-03-06)
**Evidence**: No GitHub imports; all mutations via `Path.write_text()` on local files.

### Claim 5: Backlog MCP `github.py` has CRUD but zero sub-issue methods

**VERDICT**: VERIFIED
**Source**: `.claude/skills/backlog/backlog_core/github.py` (accessed 2026-03-06)
**Evidence**: PyGitHub CRUD confirmed (create, close, resolve, labels). No `sub_issue` methods present.

## RT-ICA

**Decision**: BLOCKED

**Goal**: Eliminate local `plan/tasks-*.md` files by making GitHub sub-issues the single source of truth for SAM task state, managed through the backlog MCP.

| # | Condition | Status | Notes |
|---|-----------|--------|-------|
| 1 | GitHub sub-issues REST API is production-stable | MISSING | REFUTED by fact-check — still public preview as of 2026-03-06. Preview APIs can break without deprecation notice. |
| 2 | PyGitHub library supports sub-issue methods | AVAILABLE | VERIFIED — `get_sub_issues()`, `add_sub_issue()` present in installed venv |
| 3 | Backlog MCP has PyGitHub integration to extend | AVAILABLE | VERIFIED — `github.py` uses PyGitHub, ready to add new methods |
| 4 | `implementation_manager.py` is the only task-status query layer | AVAILABLE | VERIFIED — isolated, no GitHub calls, clean replacement target |
| 5 | `task_status_hook.py` is the only status-write layer | AVAILABLE | VERIFIED — isolated, no GitHub calls, clean replacement target |
| 6 | Hook latency budget for GitHub API calls | DERIVABLE | Hooks fire on every Write/Edit/Bash. API round-trip adds ~100–500ms per hook event. Impact unknown without measurement. |
| 7 | Offline/network-degraded operation strategy | MISSING | No fallback design exists. Current system works without network; replacement would not. |
| 8 | Sub-issue dependency graph maps to current task dependency model | DERIVABLE | GitHub sub-issues express parent-child but not arbitrary task→task dependency. Current model allows `Task 1.1, Task 2.3` as deps. Needs design. |

**Missing inputs that prevent full planning**:
1. Preview API risk decision — choose: (a) accept preview risk and build now, (b) wait for GA, (c) hybrid approach (GitHub Issues as display layer, local files as execution state)
2. Offline strategy — define behavior when GitHub is unreachable during hook execution
3. Dependency model mapping — define how `Task A depends on Task B, C` maps to GitHub sub-issue structure

## Groomed (2026-03-06)

### Issue Classification

**Type**: unbounded-design
**Scenario-target**: Architectural migration — two valid designs (full GitHub-native vs hybrid) with unresolved tradeoffs on API stability, latency, and offline behavior.
**Analysis method**: design-framing (no RCA needed — not a defect or recurring pattern)

### Reproducibility

**Current state — observable by running these commands:**

1. Run `uv run plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py status . <slug>` — returns JSON parsed from `plan/tasks-*.md` files using `Path.read_text()`. Zero GitHub API calls. All task state lives in YAML frontmatter on disk.
2. Trigger a `SubagentStop` hook event — `task_status_hook.py` `handle_subagent_stop()` writes `status: complete` and a `completed:` timestamp into the local task file via `Path.write_text()`. No GitHub API calls.
3. Trigger a `PostToolUse` (Write/Edit/Bash) hook event — `task_status_hook.py` `handle_activity_update()` reads `.claude/context/active-task-{session_id}.json`, then writes `last_activity:` to the local task file. No GitHub API calls.
4. Inspect `.claude/skills/backlog/backlog_core/github.py` — PyGitHub CRUD present for issue-level operations (`create_issue_for_item`, `close_github_issue`, etc.). No `sub_issue` methods.
5. Inspect `.venv/lib/python3.11/site-packages/github/Issue.py` lines 572–599 — `get_sub_issues()` calls `GET /repos/{owner}/{repo}/issues/{number}/sub_issues`; `add_sub_issue()` calls `POST` to same endpoint; accepts `int` (sub_issue.id — the node ID, NOT .number) or Issue object. Both methods confirmed present in installed PyGitHub.

**Proposed state — what done looks like, observable from outside:**

- `implementation_manager.py status . <slug>` (or replacement MCP tool) returns task counts derived from GitHub sub-issues on the parent story issue, not from local task files.
- `task_status_hook.py` SubagentStop and PostToolUse events update sub-issue state via GitHub API rather than writing local YAML files.
- `backlog_core/github.py` exposes `list_sub_issues()`, `add_sub_issue()`, `update_sub_issue_status()` returning structured dicts.
- `plan/tasks-*.md` files are absent or demoted to read-only human-readable copies; they are no longer the execution source of truth.

### Priority

5/10 — Architecturally valuable but blocked on unresolved design decisions (preview API risk, offline behavior, dependency model). Current system works; this is a quality-of-life and single-source-of-truth improvement, not a defect fix. Cannot begin planning until the three MISSING RT-ICA conditions are resolved by human decision.

### Impact

- Blocks: Nothing is blocked on this today — existing system functions.
- Bottleneck: The split-system problem causes drift: task status in local markdown can diverge from the GitHub story issue, making it impossible to know task progress from GitHub alone. Collaborators (and future agents) who see only GitHub Issues see no task-level state.
- Hook latency risk: `task_status_hook.py` fires on every Write/Edit/Bash in a task session. Replacing file writes with GitHub API calls adds ~100–500ms per hook event and creates a hard network dependency in the hot path of every agent operation.

### Benefits

- GitHub becomes the single source of truth for both story and task state — no drift possible.
- Task progress visible to collaborators without access to local `plan/` files.
- Backlog MCP already manages issues — sub-issue support is a natural extension of existing PyGitHub integration.
- Eliminates the `plan/tasks-*.md` file format as an operational concern — agents no longer need to parse YAML frontmatter to query task state.
- Enables future task querying by any MCP client, not just the local orchestrator.

### Dependencies

**Depends on (must be resolved/decided before SAM planning):**

- Human decision on the three BLOCKED RT-ICA conditions (see Questions for Human below) — no planning can proceed without these
- `#365` Implementation Manager MCP Server — that item proposes wrapping `implementation_manager.py` as MCP tools over local files; this item supersedes or subsumes part of that scope. The relationship must be resolved before either is planned: if #365 is implemented first over local files, #480 becomes a migration of the MCP layer rather than a replacement of the CLI
- `#282` Backlog system redesign: GitHub Issues as source of truth — establishes the backlog layer that this item would extend with sub-issue support; must be complete or at minimum have stable GitHub CRUD in `github.py`
- `#257` development-harness: Task Status MCP — overlapping scope (MCP wrapper for `implementation_manager.py`); should be closed as superseded or scoped to non-GitHub variant before #480 planning begins

**Blocks (items waiting on this one):**

- None directly. The existing system is functional. This item unblocks a future state where SAM task state is visible on GitHub without local file access.

**RT-ICA BLOCKED on (must be resolved before planning):**

1. Preview API risk decision — GitHub sub-issues REST API remains in public preview as of 2026-03-06 with no announced GA date. Decision required: (a) accept preview risk and build now, (b) wait for GA, (c) hybrid approach where GitHub sub-issues are display-only and local files remain execution state
2. Offline/network-degraded operation strategy — `task_status_hook.py` fires on every Write/Edit/Bash in a task session; current file writes succeed with no network; replacement GitHub API calls would fail on network timeout. No fallback design exists
3. Dependency graph mapping — current `dependencies:` field allows arbitrary task-to-task references (e.g., `Task T3 depends on T1, T2`); GitHub sub-issues express only parent-child hierarchy, not peer-to-peer task dependencies. Mapping strategy required before implementation scope can be defined

### Questions for Human

These three unresolved decisions block SAM planning. Each requires a choice:

**1. GitHub sub-issues API stability risk (blocking)**

The sub-issues REST API is confirmed public preview as of 2026-03-06 (no GA announcement found). Preview APIs can break or change without deprecation notice.

Choose one:
- (a) Accept preview risk — build now, own the upgrade cost if API changes
- (b) Wait for GA — defer this item until GitHub announces GA
- (c) Hybrid — use GitHub sub-issues as a read/display layer only; keep local YAML files as execution state and sync periodically. This limits the single-source-of-truth benefit but eliminates preview API risk in the hot path.

**2. Hook latency and offline behavior (blocking)**

`task_status_hook.py` fires on every Write/Edit/Bash operation during a task session (potentially dozens of calls per minute). Each hook firing currently completes in <10ms (local file write). A GitHub API call adds ~100–500ms per event and fails completely when the network is degraded.

Choose one:
- (a) Accept latency — GitHub API call on every hook event; task sessions become network-dependent
- (b) Local write + async sync — hook writes locally and queues a background sync to GitHub; requires a sync daemon or periodic sync trigger
- (c) Reduce hook frequency — only SubagentStop calls GitHub (completion event); PostToolUse LastActivity updates stay local
- (d) Drop LastActivity tracking — remove the PostToolUse hook entirely; only track Started/Completed via GitHub

**3. Task dependency model (blocking)**

Current task files store arbitrary peer-to-peer dependencies: `Task T3 depends on T1, T2`. GitHub sub-issues express only parent-child relationships (a sub-issue belongs to a parent issue). There is no native GitHub concept for "sub-issue A must complete before sub-issue B can start."

Choose one:
- (a) Store dependency graph as issue body metadata — parse a structured section in each sub-issue's body as the dependency source of truth
- (b) Keep dependency graph in a local manifest file — sub-issues track state only; local YAML tracks dependencies; `get_ready_tasks()` logic stays in `implementation_manager.py`
- (c) Use GitHub milestone ordering or Projects board ordering as a proxy for dependency sequencing

### Resources

| Type | Item |
|------|------|
| Prior work — task query CLI | `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` |
| Prior work — hook script | `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` |
| Prior work — task format utilities | `plugins/python3-development/skills/implementation-manager/scripts/task_format.py` |
| Prior work — GitHub CRUD layer | `.claude/skills/backlog/backlog_core/github.py` |
| Prior work — MCP server | `.claude/skills/backlog/backlog_core/server.py` |
| Prior work — PyGitHub sub-issue methods | `.venv/lib/python3.11/site-packages/github/Issue.py` lines 572–599 |
| Skill | `/backlog` — backlog MCP skill, contains `backlog_core/github.py` patterns to follow |
| Skill | `/implement-feature` — orchestrator skill that calls `implementation_manager.py`; the consumer of whatever replaces it |
| Skill | `/start-task` — sub-agent skill that writes context file and is the producer of hook-triggering events |
| Related backlog item | `#365` Implementation Manager MCP Server — overlapping scope (local-file MCP wrapper); must be reconciled |
| Related backlog item | `#257` development-harness: Task Status MCP — overlapping scope; candidate for closure as superseded |
| External API reference | [GitHub REST API sub-issues (preview)](https://docs.github.com/en/rest/issues/sub-issues) — confirmed public preview as of 2026-03-06 |
| Agent | `@python3-development:python-cli-architect` — for redesigning `implementation_manager.py` interface |
| Agent | `@python3-development:context-gathering` — for codebase analysis before planning |

### Acceptance Criteria

These criteria are conditional on the human decisions in Questions for Human. They describe what done looks like for the full-migration option (choice (a) for each question). Criteria will need revision after design decisions are made.

**If full GitHub-native migration is chosen:**

1. `uv run implementation_manager.py status . <slug>` (or replacement MCP tool call) returns task state sourced from GitHub sub-issues on the parent story issue — verifiable by checking that local `plan/tasks-*.md` files are absent and the JSON output matches sub-issue labels/state on GitHub
2. Completing a task via SubagentStop hook results in the corresponding GitHub sub-issue transitioning to closed state — verifiable by checking `gh issue view <sub-issue-number> -R Jamie-BitFlight/claude_skills` shows state: closed
3. `backlog_core/github.py` contains `list_sub_issues(parent_issue_number)`, `add_sub_issue(parent_issue_number, sub_issue_id)`, and `update_sub_issue_status(issue_number, status)` functions — verifiable by running `uv run python -c "from backlog_core.github import list_sub_issues; print('ok')`
4. `get_ready_tasks()` logic produces the same output when given a parent GitHub issue with sub-issues as it currently does when given a local YAML task file — verifiable by running the existing test suite against a fixture GitHub issue
5. The hook script `task_status_hook.py` completes SubagentStop processing within an observable time budget (decision needed: what is acceptable latency) — verifiable by timing hook execution in a test session

**If hybrid approach is chosen (option (c)):**

1. GitHub sub-issues exist for each task in the story and reflect correct current status — verifiable via `gh issue list` showing sub-issues with matching labels
2. Local YAML files remain the execution source of truth and all existing tests pass unchanged
3. A sync command exists that pushes local task status to GitHub sub-issue labels — verifiable by running the sync command and checking GitHub issue labels match local YAML status

### Scope

**Files that need to change (for full GitHub-native migration):**

| File | Change |
|------|--------|
| `plugins/python3-development/skills/implementation-manager/scripts/implementation_manager.py` | Replace `parse_task_file()` and `get_ready_tasks()` with GitHub sub-issue queries; remove or demote local file parsing |
| `plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py` | Replace `Path.write_text()` calls with GitHub API calls for status and timestamp updates |
| `plugins/python3-development/skills/implementation-manager/scripts/task_format.py` | Demote or remove — YAML frontmatter format no longer needed if GitHub is source of truth |
| `.claude/skills/backlog/backlog_core/github.py` | Add `list_sub_issues()`, `add_sub_issue()`, `update_sub_issue_status()`, `get_ready_sub_issues()` |
| `.claude/skills/backlog/backlog_core/server.py` | Add MCP tools wrapping new sub-issue methods |
| `.claude/skills/implement-feature/SKILL.md` | Update CLI invocation steps to use MCP sub-issue tools instead of `implementation_manager.py` |
| `.claude/skills/start-task/SKILL.md` | Update context file and status-write steps to reference GitHub API |
| `plan/tasks-*.md` files (any existing) | Status: demoted to read-only reference artifacts or removed |

**Effort estimate**: High

Rationale: Three distinct systems must change in coordination (query layer, hook layer, MCP server), all gated on three unresolved design decisions. Each design option (full migration vs hybrid vs deferred) produces a different scope. The PyGitHub sub-issue methods are present but the REST API is in preview, adding risk. No prior migration path exists. Recommend splitting into phases after design decisions are made:

- Phase 1: Extend `backlog_core/github.py` with sub-issue CRUD and write integration tests against a real story issue
- Phase 2: Replace `implementation_manager.py` query path with GitHub sub-issue queries (read path only)
- Phase 3: Replace `task_status_hook.py` write path with GitHub API calls (or implement local+sync hybrid)
- Phase 4: Update skill documentation and remove local task file format dependencies

### Decision

**Date**: 2026-03-06

**1. Preview API risk**: ACCEPTED — build now using sub-issues REST API despite public preview status.

**2. Offline/cache strategy**: Same as current backlog MCP — local files are the cache/interface layer. All GitHub state is mirrored to local files; hooks read/write local cache and sync to GitHub when available. No degraded-mode logic needed beyond what backlog MCP already implements.

**3. Dependency model**: Under investigation. User direction: GitHub Projects v2 may offer relationship fields beyond parent-child. Fallback: named list in issue body referencing other issues by number. Sub-agent researching options — decision pending research output.

### Research

Full comparison analysis written to `plan/research/comparison-github-task-dependency-options.md`.

**Recommendation: Option B** — Sub-issues + issue body dep list.

Key findings:
- All 3 options require text-convention dep parsing; no option provides native GitHub dep enforcement
- `get_ready_tasks()` is unchanged in all options — dep resolution is always local
- Option B aligns with existing backlog MCP caching pattern
- Option C (Projects v2) is GraphQL-only, complex, and overkill for this use case

**Critical implementation guard**: Always pass the `Issue` object to `add_sub_issue()`, never `.id` or `.number` manually — both are integers, confusing them produces no type error.

**Fallback**: If sub-issues unavailable on repo plan, use Option A (body text deps only). Logic is identical.