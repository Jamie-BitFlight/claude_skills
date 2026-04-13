---
name: create-artifact
description: Register a plan artifact via the MCP backlog server. Use when you produce a document or report that downstream agents or worktree-isolated environments need to retrieve — feature-context, codebase-analysis, architect, task-plan, T0-baseline, TN-verification, or research artifacts. Triggers include "store an artifact", "register a plan artifact", "write a report to the backlog", "upload artifact content".
---

# Create Artifact (MCP-native storage)

Register your deliverable using `mcp__plugin_dh_backlog__artifact_register`. This is the ONLY
correct storage path for plan artifacts. Do NOT use `Write` to disk and do NOT return content
inline.

## Why disk writes and inline returns are wrong

- **Disk writes** produce a file only accessible from the root worktree. Worktree-isolated agents
  and CI environments cannot reach `~/.dh/...` paths via filesystem — they must use
  `artifact_read(issue_number, artifact_type)` over MCP.
- **Inline returns** are truncated by the task-notification summary when the agent runs as a
  background-dispatched task. The orchestrator receives a partial summary, not the full document.

MCP-native storage uploads content to a GitHub issue comment where any agent — regardless of
worktree or environment — can retrieve it via `artifact_read`.

## Correct invocation (verified against `backlog_core/server.py:2385`)

```python
mcp__plugin_dh_backlog__artifact_register(
    issue_number=<int>,           # GitHub issue number — REQUIRED
    artifact_type=<str>,          # Artifact type string — REQUIRED (see table below)
    artifact_id=<str>,            # Logical identifier — REQUIRED (see path format below)
    status="current",             # Lifecycle status: draft | current | superseded | archived
    agent=<str>,                  # Name of the producing agent (default: "")
    content=<str | None>,         # Full artifact content — include this to store in GitHub
)
```

**Return value**: dict with keys `registered` (bool), `artifact_count` (int), `action`
("added" or "updated"), `content_stored` (bool), `messages`, `warnings`. Check `action`
in your STATUS: DONE report — do NOT paste the full content.

## Parameters

### `artifact_type`

One of the recognized type strings:

| artifact_type | Producing agent | When to use |
|---|---|---|
| `feature-context` | feature-researcher | Discovery document: WHO/WHAT/WHEN/WHY analysis |
| `codebase-analysis` | codebase-analyzer | Codebase pattern/architecture/testing documents |
| `architect` | python-cli-design-spec | Architecture spec with interfaces and contracts |
| `task-plan` | swarm-task-planner | SAM task plan — auto-registered by `sam_plan(action='create', issue=N)`, do NOT register manually |
| `T0-baseline` | t0-baseline-capture | Pre-implementation baseline of acceptance criteria |
| `TN-verification` | tn-verification-gate | Post-implementation verification results |
| `research` | any research agent | Investigation findings, coverage analysis, rationale |

### `artifact_id`

Logical identifier for the artifact. Two valid formats:

- **Repo-relative path** for file artifacts that exist on disk in the root worktree:
  `plan/feature-context-{slug}.md`, `plan/architect-{slug}.md`
- **Logical id** for artifacts that do NOT write a repo file: `codebase-patterns-{slug}`,
  `codebase-architecture-{slug}`, `T0-baseline-{slug}`, `TN-verification-{slug}`

Use a logical id (not a path) when the agent stores content via `content=` without writing
a file to disk. Using a path that doesn't exist on disk causes a warning when `content=None`
and is misleading to artifact consumers.

Do NOT use `~/.dh/...` paths — these are MCP-server internals, not stable agent interfaces.

### `content`

Pass the full markdown string. When `content` is provided, it is stored as a structured GitHub
issue comment retrievable via `artifact_read(issue_number, artifact_type)` from any environment.

When `content` is `None`: the server attempts to read a local file at `artifact_id` (resolved
against the root worktree). If no file exists, a manifest-only entry is registered and a warning
is emitted. For background-dispatched agents, always pass `content=` explicitly.

## Examples by artifact type

### feature-context

```python
mcp__plugin_dh_backlog__artifact_register(
    issue_number=1770,
    artifact_type="feature-context",
    artifact_id="plan/feature-context-my-feature.md",
    content=feature_context_markdown,
    agent="feature-researcher",
)
```

### codebase-analysis (one call per focus area, logical id — no filesystem path)

```python
mcp__plugin_dh_backlog__artifact_register(
    issue_number=1770,
    artifact_type="codebase-analysis",
    artifact_id="codebase-patterns-my-feature",  # logical id: codebase-{focus}-{slug}
    content=patterns_markdown,
    agent="codebase-analyzer",
)

mcp__plugin_dh_backlog__artifact_register(
    issue_number=1770,
    artifact_type="codebase-analysis",
    artifact_id="codebase-architecture-my-feature",  # logical id: codebase-{focus}-{slug}
    content=architecture_markdown,
    agent="codebase-analyzer",
)
```

### architect

```python
mcp__plugin_dh_backlog__artifact_register(
    issue_number=1770,
    artifact_type="architect",
    artifact_id="plan/architect-my-feature.md",
    content=architect_markdown,
    agent="python-cli-design-spec",
)
```

### task-plan

`sam_plan(action='create', issue=N)` auto-registers this artifact. Do NOT call
`artifact_register` for `task-plan` — it creates a duplicate entry.

### research (secondary documents, rationale, coverage analysis)

```python
mcp__plugin_dh_backlog__artifact_register(
    issue_number=1770,
    artifact_type="research",
    artifact_id="plan/swarm-rationale-my-feature.md",
    content=rationale_markdown,
    agent="swarm-task-planner",
)
```

## STATUS: DONE report format

Do NOT paste the full document content. Report only:

```text
STATUS: DONE
ARTIFACT: type={artifact_type}, action={action}, content_stored={content_stored}, chars={len(content)}
```

Include a `<concerns>` block if quality issues were found during the work.
