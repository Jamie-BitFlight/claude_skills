---
name: create-artifact
description: Register a plan artifact via the MCP backlog server. Use when you produce a document or report that downstream agents or worktree-isolated environments need to retrieve — feature-context, codebase-analysis, architect, T0-baseline, TN-verification, or research artifacts. Triggers include "store an artifact", "register a plan artifact", "write a report to the backlog", "upload artifact content".
---

# Create Artifact

Register your deliverable through the configured content provider with
`mcp__plugin_dh_backlog__artifact_register`, or use the `artifact register` CLI subcommand in
scripting contexts. Pass the content in the registration call and return only its logical ID.

## Storage boundary

- `artifact_register` writes through the selected provider; agents do not choose or access its
  storage layer.
- `artifact_read(item_id, artifact_type)` retrieves the current artifact through the same boundary.
- Background agents return the logical ID instead of repeating the document in their completion
  message.

## Invocation

**MCP:**

```python
mcp__plugin_dh_backlog__artifact_register(
    item_id=<int | str>,          # Backlog item identifier — REQUIRED
    artifact_type=<str>,          # Artifact type string — REQUIRED (see table below)
    artifact_id=<str>,            # Logical identifier — REQUIRED
    status="current",             # Lifecycle status: draft | current | superseded | archived
    agent=<str>,                  # Name of the producing agent (default: "")
    content=<str>,                # Non-empty full artifact content — REQUIRED
)
```

**CLI equivalent** (scripting/dispatch contexts):

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact register \
  --item-id <identifier> \
  --artifact-type <str> \
  --artifact-id <str> \
  --status "current" \
  --agent <str> \
  --content <str>
```

`--status` and `--agent` are optional (same defaults as the MCP form). The examples below use the
MCP form; substitute the same values into the CLI flags above for a scripting context.

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
| `T0-baseline` | t0-baseline-capture | Pre-implementation baseline of acceptance criteria |
| `TN-verification` | tn-verification-gate | Post-implementation verification results |
| `research` | any research agent | Investigation findings, coverage analysis, rationale |

### `artifact_id`

Use a stable logical identifier, such as `feature-context-{slug}`, `architect-{slug}`,
`codebase-patterns-{slug}`, `T0-baseline-{slug}`, or `TN-verification-{slug}`. Consumers use the
owner and artifact type to discover content; the identifier distinguishes multiple artifacts of
the same type.

### `content`

Pass a non-empty full markdown string. The current registration contract requires `content=`;
without it, the call is invalid and `artifact_read(item_id, artifact_type)` cannot return the document.

## Examples by artifact type

### feature-context

```python
mcp__plugin_dh_backlog__artifact_register(
    item_id=1770,
    artifact_type="feature-context",
    artifact_id="feature-context-my-feature",
    content=feature_context_markdown,
    agent="feature-researcher",
)
```

### codebase-analysis (one call per focus area)

```python
mcp__plugin_dh_backlog__artifact_register(
    item_id=1770,
    artifact_type="codebase-analysis",
    artifact_id="codebase-patterns-my-feature",
    content=patterns_markdown,
    agent="codebase-analyzer",
)

mcp__plugin_dh_backlog__artifact_register(
    item_id=1770,
    artifact_type="codebase-analysis",
    artifact_id="codebase-architecture-my-feature",
    content=architecture_markdown,
    agent="codebase-analyzer",
)
```

### architect

```python
mcp__plugin_dh_backlog__artifact_register(
    item_id=1770,
    artifact_type="architect",
    artifact_id="architect-my-feature",
    content=architect_markdown,
    agent="python-cli-design-spec",
)
```

### task-plan

Task plans live exclusively in SAM plan storage. Create them with
`mcp__plugin_dh_sam__sam_plan(config={"action": "create", ...})` and retrieve them with
`mcp__plugin_dh_sam__sam_plan(plan="{plan_ref}", config={"action": "read"})`.

### research (secondary documents, rationale, coverage analysis)

```python
mcp__plugin_dh_backlog__artifact_register(
    item_id=1770,
    artifact_type="research",
    artifact_id="swarm-rationale-my-feature",
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
