# Improvement Proposals: Beads (bd)

**Research entry**: ./research/task-management/beads.md
**Generated**: 2026-03-28
**Patterns assessed**: 7
**Backlog items created**: 1 (issues: #1089)
**Deferred (low confidence)**: 0
**Deferred (medium confidence)**: 3
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Semantic compaction for completed SAM tasks

**Source pattern**: "Semantic compaction: summarizing completed work rather than deleting it preserves audit trail while managing context window size" (Patterns Worth Adopting section); "`bd compact` summarizes closed tasks using semantic compression" (Key Features > Compaction and Memory Management)
**Local system**: `plugins/development-harness/sam_schema/core/query.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1089 created

### Current state

Completed SAM tasks remain in plan files with full detail (requirements, constraints, acceptance criteria, verification steps). When an orchestrator runs `sam_status` or `sam_read` on a long-running plan with many completed tasks, the full task bodies consume context window tokens unnecessarily. No mechanism exists to summarize or compact completed work. All query functions in `plugins/development-harness/sam_schema/core/query.py` return full task content regardless of completion status.

### Target state

A `sam_compact` CLI command and MCP tool that summarizes completed tasks in a plan file. For each COMPLETE task, the full body is replaced with a one-line summary preserving: task title, completion timestamp, key outcomes (files modified, tests added). The original full body is preserved in a `_compacted` metadata field or separate archive file for audit trail. `sam_status` output includes a `compacted_count` field showing how many tasks were compacted.

### Measurable signal

Run `uv run sam compact P{N}` on a plan with 5+ COMPLETE tasks. Before: `sam_status` output includes full task bodies for all tasks. After: completed tasks show summary-only in `sam_read` output, `compacted_count: N` appears in `sam_status`, and `sam_read --full` (or `--no-compact`) flag retrieves the original uncompacted body. Context token count for the plan drops measurably (verify by comparing character count of `sam_status` output before and after).

---

## Improvement 2: Hash-based IDs for multi-branch plan creation

**Source pattern**: "Hash-based IDs for any distributed state where sequential IDs would collide (applicable to agent coordination systems beyond task tracking)" (Patterns Worth Adopting section); "IDs derived from random UUIDs (`bd-a1b2`) scaled from 4 to 6 chars as database grows" (Key Features > Hash-Based Collision Prevention)
**Local system**: `plugins/development-harness/sam_schema/core/addressing.py`, `plugins/development-harness/sam_schema/core/query.py`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: The local system uses sequential `P{N}/T{M}` addressing with collision detection via `_find_collision()` in `query.py` (line 65). Kage-bunshin sessions use UUID-based session IDs to isolate concurrent work. The collision scenario (two branches creating `P10` simultaneously) is plausible but has not been observed in practice. Would need evidence of actual collision incidents or a multi-branch concurrent planning workflow to raise confidence.

### Current state

SAM plan addresses use sequential numbering: `P{N}` for plans, `T{M}` for tasks within plans. The `_find_collision()` function in `sam_schema/core/query.py` (line 65) detects same-number files at creation time within a single branch. Kage-bunshin uses UUID session IDs (`spawn.py` line 178) for process isolation. However, if two branches independently create plans, both could generate `P10-feature-a.yaml` and `P10-feature-b.yaml`, requiring manual resolution on merge.

### Target state

Plan addresses incorporate a short hash prefix (e.g., `P10a3f8-feature-slug.yaml`) derived from a UUID, preventing merge conflicts when multiple branches create plans concurrently. The addressing module resolves both hash-prefixed and legacy sequential addresses for backward compatibility.

### Measurable signal

Create two plans on separate branches with the same sequence number. Merge the branches. Before: git merge conflict on plan file numbering. After: no conflict, both plans coexist with distinct hash-prefixed addresses.

---

## Improvement 3: Single-command context briefing for agent session bootstrap

**Source pattern**: "The `bd prime` pattern: a single command that generates a compact, structured context briefing -- applicable to any stateful tool that needs to inject context into an agent session" (Patterns Worth Adopting section); "`bd prime` command generates ~1-2k token workflow context summary for injection into agent sessions" (Key Features > Agent-Optimized Task Graph)
**Local system**: `.claude/CLAUDE.md`, `.claude/hooks/`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: The local system uses CLAUDE.md (~3k+ tokens) plus SessionStart hooks for context injection. These serve a similar purpose to `bd prime` but are not a single compact command that generates a dynamic workflow briefing. The gap is real (no `sam prime` or equivalent exists), but the practical impact depends on whether agents are actually context-starved at session start. Would need measurement of context window consumption at session start to raise confidence.

### Current state

Agent session context comes from CLAUDE.md (static, ~3k+ tokens of project instructions) and SessionStart hooks (dynamic, but focused on backlog sync and tool setup). No single command generates a compact, dynamic workflow briefing that summarizes: current plan status, ready tasks, recent completions, and active blockers. Agents must call multiple MCP tools (`sam_status`, `sam_ready`, `backlog_list`) to build equivalent context.

### Target state

A `sam prime` CLI command and MCP tool that generates a compact (~1-2k token) workflow briefing containing: active plan summary, ready task count and IDs, recently completed tasks, active blockers, and relevant context from the plan's context manifest. Output is structured text suitable for injection into CLAUDE.md or agent prompts.

### Measurable signal

Run `uv run sam prime` in a project with an active plan. Output is a single text block under 2000 tokens containing: plan name, task status summary, list of ready tasks, and any blockers. The output can be piped to a SessionStart hook or injected into an agent prompt.

---

## Improvement 4: Typed `discovered-from` dependency links in SAM task schema

**Source pattern**: "Adopt `bd create --deps discovered-from:<parent>` pattern to track emergent work found during implementation, keeping discovered tasks linked to their origin" (Integration Opportunities section); "`discovered-from` -- tracks tasks surfaced during implementation" (Key Features > Dependency and Link Types)
**Local system**: `plugins/development-harness/sam_schema/core/models.py`, `plugins/development-harness/skills/dispatch/SKILL.md`
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred -- confidence medium: The local system captures discoveries during implementation via prose (context-refinement agent collects "divergence notes and discovered-during-implementation sections" per `plan-artifact-lifecycle.md` line 106) and the dispatch skill collects discoveries between waves (`dispatch/SKILL.md` line 63). However, these are unstructured text, not typed dependency links in the task graph. The gap is real but the practical benefit of structured `discovered-from` links vs. prose notes needs validation -- current workflows may not query this relationship programmatically.

### Current state

Discoveries during implementation are captured as unstructured prose in context-refinement agent output and dispatch wave collection. The SAM task schema (`sam_schema/core/models.py`) supports `dependencies` as a list of task IDs (line 594 area), but dependency links have no type field -- all dependencies are treated as `blocks` semantics. There is no way to distinguish "blocks" from "discovered-from" or "relates-to" relationships.

### Target state

The SAM `Task` model in `models.py` supports typed dependency links: `blocks`, `discovered-from`, `relates-to`. The `sam_create` and `sam_update` tools accept a `--dep-type` parameter. `sam_ready` only respects `blocks` dependencies for readiness calculation; `discovered-from` and `relates-to` are informational. Queries can filter by dependency type.

### Measurable signal

Run `uv run sam update P{N}/T{M} --add-dep T{K} --dep-type discovered-from`. Then `uv run sam read P{N}/T{M} --format json` shows the dependency with `type: discovered-from`. `sam_ready` still considers T{M} ready (discovered-from does not block).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Hash-based IDs for multi-branch plan creation | Medium | No observed collision incidents; local system has `_find_collision()` mitigation; would need evidence of actual multi-branch concurrent planning failures |
| Single-command context briefing (`sam prime`) | Medium | Local system uses CLAUDE.md + hooks for similar purpose; would need measurement of context window consumption to confirm practical impact |
| Typed `discovered-from` dependency links | Medium | Local system captures discoveries as prose; would need evidence that structured links provide queryable value beyond what prose notes offer |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Atomic claim semantics (`--claim` flag) | Already covered: `sam_claim` MCP tool and CLI command implement atomic claim with `claimed: true/false` response. Documented in `start-task/SKILL.md` lines 86-99 and `sam_schema/server.py` line 557. |
| CLI-first, MCP-optional design philosophy | Already covered: SAM has both CLI (`sam_schema/cli.py`) and MCP server (`sam_schema/server.py`). Backlog system has both CLI and MCP tools. |
| Install `bd` / `bd setup claude` / beads plugin adoption | Not a local system improvement pattern -- these are about adopting an external tool, not extending local systems. |
