---
name: 'Backlog system redesign: GitHub Issues as source of truth with local cache'
description: 'Current architecture has BACKLOG.md as primary source of truth with GitHub Issues as a secondary mirror. This is inverted — only works for one agent in one repo clone. A second session, different machine, or teammate sees stale markdown files. Redesign so GitHub Issues + Projects are the backend (available from anywhere) and local .claude/backlog/ files are a derived read cache rebuilt on demand. Key changes: (1) add creates GitHub Issue first, writes local cache from response, (2) list queries gh issue list with label filters, caches locally for speed, (3) update does gh issue edit first then updates cache, (4) close happens via Fixes #N in PR — GitHub auto-closes on merge, no manual skill workflow needed, (5) status lives in GitHub labels not markdown fields, (6) priority lives in GitHub labels not markdown section headers, (7) plan artifacts attached as issue comments or linked in body, (8) groomed content written into issue body expandable sections. Add pull/push commands: backlog.py pull fetches all open issues and rebuilds local cache, backlog.py push syncs local edits back to GitHub. The Fixes #N convention in commits/PRs handles closing automatically.'
metadata:
  topic: backlog-system-redesign-github-issues-as-source-of-truth-wit
  source: Session observation — identified during work-backlog-item close workflow for CI failures item
  added: '2026-02-26'
  priority: completed
  type: Feature
  status: done
  issue: '#282'
  groomed: '2026-02-27'
  last_synced: '2026-02-27T12:14:59Z'
  plan: plan/tasks-7-backlog-gh-first-phase1.md
---

## Story

As a **developer**, I want **Current architecture has BACKLOG** so that **backlog items are tracked in GitHub**.

## Description

Current architecture has BACKLOG.md as primary source of truth with GitHub Issues as a secondary mirror. This is inverted — only works for one agent in one repo clone. A second session, different machine, or teammate sees stale markdown files. Redesign so GitHub Issues + Projects are the backend (available from anywhere) and local .claude/backlog/ files are a derived read cache rebuilt on demand. Key changes: (1) add creates GitHub Issue first, writes local cache from response, (2) list queries gh issue list with label filters, caches locally for speed, (3) update does gh issue edit first then updates cache, (4) close happens via Fixes #N in PR — GitHub auto-closes on merge, no manual skill workflow needed, (5) status lives in GitHub labels not markdown fields, (6) priority lives in GitHub labels not markdown section headers, (7) plan artifacts attached as issue comments or linked in body, (8) groomed content written into issue body expandable sections. Add pull/push commands: backlog.py pull fetches all open issues and rebuilds local cache, backlog.py push syncs local edits back to GitHub. The Fixes #N convention in commits/PRs handles closing automatically.

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — identified during work-backlog-item close workflow for CI failures item
- **Priority**: P1
- **Added**: 2026-02-26
- **Research questions**: None

## Design Constraints

### Authorization gate: preventing untrusted issue injection

Agents must never auto-action issues from arbitrary contributors. The approved work queue requires an explicit gate:

1. **Project board membership** (coarse gate) — only issues added to the GitHub Project are visible to `backlog.py pull`. Issues opened by external contributors exist in the repo tracker but are invisible to agents until a maintainer adds them to the project.
2. **Label filter** (fine-grained) — within the project, only issues carrying an `agent:actionable` label (or equivalent) enter the agent's working set. This prevents half-triaged items from being picked up prematurely.
3. **Author allowlist** (optional hardening) — `.claude/config.json` or `pyproject.toml` can list approved GitHub logins. `backlog.py pull` skips issues from authors not on the list even if they're in the project. Useful for repos with many collaborators.

The combination means: random drive-by issues stay in the repo's issue tracker, never enter the agent's local cache, and never get worked. A maintainer explicitly approves work by adding the issue to the project board and labeling it.

### Cache-first reads: minimizing API pressure

Local `.claude/backlog/*.md` files are the **fast read path** for agents. GitHub API is reserved for writes and explicit syncs. This avoids rate-limiting, network latency, and unnecessary API pressure from agents querying backlog state during sessions.

**Cache hit (read local, skip GH API):**

1. **Recent local write** — frontmatter `last_synced` is within a freshness window (e.g., 10 min) and action is read-only (`list`, `find_item`, reading item details for grooming/planning). The local file is authoritative for the current session.
2. **Same branch, same session** — if the item was modified on the current git branch, local changes are the latest state. No reason to round-trip to GH.
3. **Read-after-write** — immediately after `add`, `update`, or `groom` writes locally, the local file reflects the latest state. Subsequent reads within the session use it directly.
4. **No issue number** — Ideas and un-synced items have no GH issue. Local is the only source.
5. **`list` without `--with-status`** — default `list` reads only local files. Status label lookup (which requires GH API) is opt-in via `--with-status`.
6. **Offline / no token** — `_try_get_github()` returns `None`. Fall back to local cache for all reads, warn once per session.

**Cache miss (must hit GH API):**

- `list --with-status` — needs label state from GH
- `close` / `resolve` — mutates GH state
- `pull` — explicit cache refresh from GH
- `sync` / `push` — writes local state to GH
- Fresh clone or new branch with no local files — must `pull` first

**Design principle:** Agents working locally against `backlog.py list` and `backlog.py groom` should never trigger API calls as a side effect of reading. Network operations are explicit (`pull`, `push`, `sync`, `--with-status`).

## Fact-Check

**Date**: 2026-02-27
**Claims checked**: 8 | VERIFIED: 5 | REFUTED: 1 | PARTIALLY VERIFIED: 2

### Claim 1: "Current architecture has BACKLOG.md as primary source of truth"
**Verdict**: REFUTED
**Evidence**: BACKLOG.md does not exist (glob search returned empty). Code reads from `.claude/backlog/` per-item files via `_parse_backlog_from_directory()` (backlog.py:178-222).
**Impact**: Issue description overstates the problem — BACKLOG.md is already eliminated. The real issue is local-first vs GH-first flow.

### Claim 2: "GitHub Issues as a secondary mirror"
**Verdict**: PARTIALLY VERIFIED
**Evidence**: `add` creates local file first, then GH issue (backlog.py:760-794). `list` reads only local files (backlog.py:872). `sync` creates GH issues for items missing them. Flow is local-first despite docstring (line 17) claiming "GitHub Issues are the source of truth."
**Citation**: Codebase analysis (backlog.py lines 760-794, 866-877)

### Claim 3: "A second session sees stale markdown files"
**Verdict**: VERIFIED
**Evidence**: `list` calls `parse_backlog()` which reads only the local directory. No automatic GH sync on read. `pull` exists but must be invoked manually.
**Citation**: Codebase analysis (backlog.py:225-231, 1912-1943)

### Claim 4: "close happens via Fixes #N — GitHub auto-closes on merge"
**Verdict**: VERIFIED
**Evidence**: GitHub docs confirm supported keywords (close, closes, fix, fixes, resolve, resolves) auto-close linked issues when PR merges to default branch. Enabled by default, configurable since Apr 2025.
**Citation**: [Linking a PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue) (accessed 2026-02-27)

### Claim 5: "status lives in GitHub labels"
**Verdict**: VERIFIED
**Evidence**: Labels `status:needs-grooming`, `status:in-progress` used at issue creation (backlog.py:465) and fetched for display (backlog.py:809, 834).
**Citation**: Codebase analysis (backlog.py:465, 798-812, 1492-1502)

### Claim 6: "priority lives in GitHub labels"
**Verdict**: VERIFIED
**Evidence**: Priority labels (`priority:p1` etc.) created on issue creation (backlog.py:461-465).
**Citation**: Codebase analysis (backlog.py:461-465)

### Claim 7: "Add pull/push commands: backlog.py pull"
**Verdict**: PARTIALLY VERIFIED
**Evidence**: `pull` already implemented (backlog.py:1912-1943). No `push` command exists — `sync` pushes groomed content but is not a full bidirectional push.
**Citation**: Codebase analysis (backlog.py:1912-1943; grep for "def push" returned no matches)

### Claim 8: "Fixes #N convention handles closing automatically"
**Verdict**: VERIFIED
**Evidence**: Same as Claim 4. Default branch only. Configurable since Apr 2025.
**Citation**: [Linking a PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue) (accessed 2026-02-27)

### Summary of Impact on Scope
The issue description is **partially stale** — it describes a problem state (BACKLOG.md as primary) that no longer exists. The current architecture already uses per-item `.claude/backlog/*.md` files with GH Issue sync, labels for status/priority, and a `pull` command. The remaining work is narrower than described: flipping `add` and `list` to be GH-first, adding `push`, and removing local-file-as-primary dependency.

## RT-ICA

**Goal**: Flip the backlog system from local-file-primary to GitHub-Issues-primary, with local .claude/backlog/ files as a derived read cache.

**Decision**: APPROVED (with reduced scope — fact-check found 1 REFUTED claim and 2 partially verified)

| # | Condition | Status | Info needed |
|---|-----------|--------|-------------|
| 1 | Current architecture understood | AVAILABLE | Verified via codebase analysis |
| 2 | BACKLOG.md is primary source of truth | MISSING | REFUTED — BACKLOG.md doesn't exist. Issue description is stale. |
| 3 | GitHub Issues API access | AVAILABLE | PyGithub + GITHUB_TOKEN already in use |
| 4 | Label taxonomy (status/priority) | AVAILABLE | Already implemented |
| 5 | pull command (GH→local) | AVAILABLE | Already implemented (backlog.py:1912) |
| 6 | push command (local→GH) | DERIVABLE | sync does partial push; full push derivable |
| 7 | Authorization gate design | AVAILABLE | Described in local file |
| 8 | Migration path (local-first → GH-first) | MISSING | No migration plan |
| 9 | Offline/degraded-network fallback | MISSING | GH-first needs fallback strategy |
| 10 | Impact on dependent skills | DERIVABLE | create-backlog-item, work-backlog-item, groom-backlog-item |
| 11 | Fixes #N convention | AVAILABLE | Verified against GitHub docs |
| 12 | Revised scope statement | MISSING | Issue overstates current problems |

**Missing inputs**: Migration path, offline behavior strategy, revised scope reflecting already-implemented features.

## Groomed (2026-02-27)

### Reproducibility

Issue description is partially stale — BACKLOG.md no longer exists. Current architecture uses per-item `.claude/backlog/*.md` files with GitHub Issue sync. The core problem (local-first flow) is reproducible: `list` reads only local files, `add` creates local file before GH issue.

### Priority

9/10 — P1 backlog system architecture issue. Blocks distributed team workflows; every teammate on different machine sees stale cache. Core infrastructure work that unblocks dependent skills (create-backlog-item, work-backlog-item, groom-backlog-item).

### Impact

- Blocks: Distributed team workflows; multi-session consistency; agents working on same items across machines
- Bottleneck: Local files as primary truth; second session always sees stale data; no automatic sync
- Benefits: GitHub Issues as universal source of truth, multi-session collaboration, offline-first design possible

### Scope

**Current state** (partially implemented):
- Per-item `.claude/backlog/*.md` files exist (BACKLOG.md already eliminated)
- Labels for status/priority already in use
- `pull` command exists (backlog.py:1912-1943)
- `sync` pushes groomed content but is not a full `push`

**Remaining work** (narrower than issue describes):
1. Flip `add` to create GitHub Issue first, write local cache from response
2. Flip `list` to query `gh issue list` with label filters, cache locally
3. Add `push` command for full local→GitHub sync
4. Define offline/degraded-network fallback behavior
5. Create migration plan for existing items
6. Update dependent skills (create-backlog-item, work-backlog-item, groom-backlog-item)

**Already done** (should be removed from scope):
- BACKLOG.md elimination
- Status in GitHub labels (status:needs-grooming, status:in-progress)
- Priority in GitHub labels (priority:p1, etc.)
- `pull` command
- Authorization gate design (documented in item file)

### Output / Evidence

- `add` creates GitHub Issue first, writes issue number to local cache
- `list` queries `gh issue list` with status/priority label filters, caches results locally
- `push` command syncs local edits → GitHub Issues
- Offline fallback behavior defined and tested
- Migration plan documented and executed for existing P0/P1 items
- Dependent skills updated to call new add/list/push flows

### Dependencies

- **Depends on**: Issue #283 (unify issue body template) — should be completed first to ensure issue body structure is stable
- **Blocks**: create-backlog-item, work-backlog-item, groom-backlog-item skills
- **Related**: Authorization gate design (documented in item file Design Constraints section)

### Research

- GitHub auto-close via Fixes #N: VERIFIED — [Linking a PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue) (accessed 2026-02-27)
- Auto-close configurable since Apr 2025: [GitHub Changelog](https://github.blog/changelog/2025-04-23-users-can-now-choose-whether-merging-linked-pull-requests-automatically-closes-the-issue/) (accessed 2026-02-27)

### Skills

- /backlog — main backlog CRUD interface
- /create-backlog-item — invokes backlog add
- /work-backlog-item — invokes backlog list, close, resolve, update
- /groom-backlog-item — invokes backlog groom

### Agents

- @backlog-item-groomer — spawned by groom-backlog-item

### Prior Work

- .claude/backlog/p1-backlog-system-redesign-github-issues-as-source-of-truth-wit.md (design constraints, authorization gate)
- .claude/backlog/p1-backlogpy-unify-issue-body-template-and-add-missing-structur.md (related issue #283)
- .claude/skills/backlog/scripts/backlog.py (1946 lines — primary implementation file)

### Files

- .claude/skills/backlog/scripts/backlog.py (add:760, list:866, pull:1912, sync:979)
- .claude/skills/backlog/SKILL.md
- .claude/skills/create-backlog-item/SKILL.md
- .claude/skills/work-backlog-item/SKILL.md
- .claude/skills/groom-backlog-item/SKILL.md

### Decision

APPROVED for grooming. Scope is narrower than original description. Three open questions for human input before planning:
1. Offline/network fallback strategy (fail fast / read-only cache / queue for sync)
2. Migration approach (auto-migrate on first run / manual / dual-write transition)
3. Phased implementation preferred (add/list first → push → offline) or all-at-once

Note: GitHub label `type:bug` should be changed to `type:feature` — this is a redesign, not a bug fix.