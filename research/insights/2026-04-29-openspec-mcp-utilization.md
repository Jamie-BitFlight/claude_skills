# Utilization Proposals: OpenSpec MCP

**Research entry**: ./research/mcp-ecosystem/openspec-mcp.md
**Generated**: 2026-04-29
**Integration surfaces found**: 3 (MCP server | npm package | CLI)
**Proposals written**: 2
**Skipped**: 3 — existing task tracking via backlog MCP server, dashboard rendering not applicable to CLI-only agents, approval workflows already implemented in GitHub issues

---

## Utilization 1: `/dh:implement-feature` → OpenSpec MCP

**Research entry**: ./research/mcp-ecosystem/openspec-mcp.md
**Caller**: `./.claude/skills/dh/SKILL.md` (implement-feature workflow step, task progress loop)
**Integration mechanism**: MCP server integration (stdio transport)
**Replaces or adds**: Adds real-time task progress tracking and human review coordination during feature implementation
**Setup cost**: Medium (MCP server startup + OpenSpec CLI prerequisite + config)
**Integration surface**: `openspec_get_progress_summary`, `openspec_get_tasks`, `openspec_update_task`, `openspec_list_reviews`

### Why this caller

The `/dh:implement-feature` skill (research entry Section "Integration Opportunities") runs an execution loop where agents implement tasks from a feature plan. Currently, task progress is tracked by reading and parsing local plan files in `.dh/projects/{slug}/`. OpenSpec MCP exposes `openspec_get_progress_summary` and `openspec_get_tasks` tools that surface task state through MCP, eliminating file parsing and enabling agents to update task status semantically via `openspec_update_task` during implementation.

The research entry documents (Section "Relevance to Claude Code Development → Integration Opportunities"): *"openspec_get_progress_summary replaces the need for manual inspection of task files during the /implement-feature execution loop."* This directly maps to the progress polling pattern used during feature execution.

### Integration sketch

During the `/dh:implement-feature` execution loop, after agents complete subtasks:

```python
# Current pattern (file-based): agent reads task file, parses YAML, updates locally
with open(f"plan/tasks/{task_id}.yaml") as f:
    task_data = yaml.safe_load(f)
    task_data["status"] = "complete"
    # write back

# OpenSpec MCP pattern: agent calls MCP tool directly
mcp_client.call_tool("openspec_update_task", {
    "task_id": task_id,
    "status": "complete",
    "output": "implementation details"
})

# Get progress for status report
progress = mcp_client.call_tool("openspec_get_progress_summary", {})
# Output: { "total": 5, "completed": 3, "in_progress": 1, "blocked": 1 }
```

**Prerequisite**: OpenSpec project directory initialized with `npm install -g @fission-ai/openspec && npx openspec-mcp /path/to/feature/project`. Task definitions stored in `openspec/tasks/` or equivalent per OpenSpec schema.

---

## Utilization 2: `/dh:work-milestone` → OpenSpec MCP Approval Pipeline

**Research entry**: ./research/mcp-ecosystem/openspec-mcp.md
**Caller**: `./.claude/skills/complete-milestone/SKILL.md` (milestone completion workflow, approval gates)
**Integration mechanism**: MCP server integration (stdio transport)
**Replaces or adds**: Adds structured change approval workflow during milestone close — agents request human approval before marking items complete
**Setup cost**: Medium (MCP server startup, OpenSpec CLI prerequisite, approval process configuration)
**Integration surface**: `openspec_request_approval`, `openspec_list_pending_approvals`, `openspec_approve_change`, `openspec_add_review`

### Why this caller

The `/complete-milestone` skill audits open and closed issues, then closes the milestone. Currently, closure is direct. The research entry (Section "Key Features → Approval Workflow State Machine") documents: *"State progression: draft → pending_approval → approved → implementing → completed → archived."* This state machine maps directly to the milestone completion gate: before marking issues as complete, agents can request human approval via `openspec_request_approval`, poll pending approvals with `openspec_list_pending_approvals`, and record reviewer feedback via `openspec_add_review`.

The research entry (Section "Relevance to Claude Code Development → Integration Opportunities") explicitly states: *"The review system (add_review, reply_review, resolve_review) maps well to the code-reviewer agent output model where findings need human acknowledgment before closure."* Milestone completion is a natural point for this workflow — agents ensure all closed issues have been reviewed before milestone state transitions to archived.

### Integration sketch

In the `/complete-milestone` workflow, after auditing closed issues:

```python
# Current pattern: report closed issues, close milestone
for issue in closed_issues:
    # GitHub issue is already closed, just report it

# OpenSpec MCP pattern: request approval before marking complete
for change_id in milestone_changes:
    mcp_client.call_tool("openspec_request_approval", {
        "change_id": change_id,
        "from": "agent",
        "to": "@reviewer"
    })

# Poll pending approvals (user sees this via OpenSpec dashboard)
pending = mcp_client.call_tool("openspec_list_pending_approvals", {})
# If pending approvals exist: ask user to review
# Once approved, transition change state
mcp_client.call_tool("openspec_approve_change", {
    "change_id": change_id
})

# Then close the milestone
close_milestone(milestone_number)
```

**Prerequisite**: Feature or milestone changes tracked in OpenSpec format (Markdown files with YAML frontmatter in `openspec/changes/`). Approval workflow configured in OpenSpec project.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `/dh:add-new-feature` (feature proposal workflow) | OpenSpec `openspec_create_change`, `openspec_validate_change` could capture feature specs as OpenSpec changes, but the current backlog item + GitHub issue flow is semantically equivalent and already integrated. Adding OpenSpec layer would duplicate state without clear advantage. |
| `code-reviewer` agent (Python/TypeScript reviewers) | Review comment threads (`openspec_add_review`, `openspec_reply_review`) are generic to OpenSpec; code reviews are language-specific. OpenSpec integration would be more suitable for design/spec review agents (which don't currently exist in the repo) than for language-specific code reviewers. |
| Dashboard/web UI skills | OpenSpec MCP exposes a Fastify-based web dashboard, but this repo is CLI-only. No local agents depend on rendered HTML UI — all output is CLI text. The dashboard is not a utilization surface for this agent ecosystem. |

---

## Integration Readiness

Both proposals are **viable if and only if**:

1. A feature or milestone adopts OpenSpec as its specification format (currently not the case)
2. The `.dh` project backend switches from file-based task tracking to OpenSpec MCP tools
3. OpenSpec CLI (`@fission-ai/openspec`) is available in the CI/deployment environment

**No breaking changes** to existing workflows are required — these are purely *additive* integrations that could be enabled per-project or per-milestone via configuration.

**Configuration vector**: Add a feature flag or env var `ENABLE_OPENSPEC_MCP=true` to `/dh:implement-feature` and `/complete-milestone` workflows. When enabled, delegate task tracking to OpenSpec MCP instead of local file parsing. When disabled (default), use existing backlog system.
