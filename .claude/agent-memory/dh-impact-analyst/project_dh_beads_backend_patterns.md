---
name: project_dh_beads_backend_patterns
description: Key architectural patterns and risk hotspots discovered during beads backend impact analysis for DH plugin (issue #2279)
metadata:
  type: project
---

## Beads Backend Integration — Key Patterns (Issue #2279, 2026-05-14)

**Why:** Impact analysis for adding beads (`bd` CLI) as a new backend to the DH plugin.
**How to apply:** Use as orientation for any future backend addition or modification work in the DH plugin.

### Factory Pattern — Two Entry Points

Backend selection has TWO independent factory functions:
- `backlog_core/backend_protocol.py::create_backend()` — controls `BacklogBackend`; `_VALID_BACKENDS = ("github", "memory", "sqlite")`
- `sam_schema/core/task_config.py::create_task_backend()` — controls `TaskBackend`; `_VALID_BACKENDS = ("local", "github", "memory")`

And a THIRD factory for artifact storage:
- `backlog_core/artifact_provider.py::create_artifact_provider()` — controls `ArtifactBackend`; uses `BackendName` StrEnum (no beads member)

Adding any new backend requires updating all three. Missing one causes silent fallthrough to `raise ValueError`/`raise BacklogError`.

### Hook Type Risk

`skills/implementation-manager/scripts/task_status_hook.py` line 807:
```python
parent_issue = int(data["parent_issue_number"])
```
This cast fails with `ValueError` for non-integer IDs (e.g., nanoid beads IDs). The failure is swallowed by `contextlib.suppress` on the MCP-call path but NOT on the file-read path. Fix: widen type to `str | int | None`, skip the cast.

### Prior Beads Removal Constraint

`backlog_core/server.py` lines 107-111 document that beads was previously removed because a lifespan hook auto-installed `@beads/bd` via npm and blocked MCP startup for 20+ seconds when the download hung. Any new beads integration MUST validate `bd` presence lazily, never at server startup.

### High-Traffic Consumer Chain for BacklogBackend

`create_backend()` → `get_config()` (module singleton) → `BacklogConfig(backend=...)` → injected into `operations.py` and `server.py`. Cache invalidated by `reset_config()`. Tests that add a new backend must call `reset_config()` between runs.

### GitHub-Only MCP Tools (No Beads Equivalent)

These MCP tools cannot be implemented behind a BeadsBackend — no beads primitive exists:
- `backlog_list_merged_prs` (no PR concept in beads)
- `backlog_list_labels` (no label system)
- `backlog_create_project`, `backlog_list_projects` (GitHub Projects V2 specific)
- `backlog_comment_issue`, `backlog_list_comments`, `backlog_read_comment` (GitHub comments)
- `backlog_sync`, `backlog_pull`, `backlog_normalize` (GitHub sync operations)
- `github_branches` MCP tool used by `work-milestone`

### BEHAVIOUR_CHANGE Skills/Agents (Substantive Rewrites Needed)

12 files require behavioral changes (not just wording updates):
- Agents: `alignment-analyst`, `impact-analyst`, `plan-validator`, `swarm-task-planner`
- Skills: `add-new-feature`, `complete-implementation`, `gate-push`, `groom-milestone`, `implement-feature`, `start-task`, `work-backlog-item`, `work-milestone`

Full per-file evidence: `docs/dh-backend-beads/comparison-research/06-agents-beads-integration.md` and `07-skills-hooks-beads-integration.md`

### ActiveTaskContext Type Propagation

`parent_issue_number` field flows through:
1. `start-task` skill writes it to active-task JSON (integer GitHub issue number)
2. `sam_schema/server.py` reads it via `sam_active_task(set)` — typed `int | None`
3. `context_backend.py` stores it — typed `int | None`
4. `task_status_hook.py` reads it from filesystem context file — casts to `int`

Widening to `str | int | None` must happen at all 4 points simultaneously to be effective.
