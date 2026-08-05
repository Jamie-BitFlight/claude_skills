# DH Workflow Graph — Data Schema

Used by the workflow mapper assembler to produce `dh-workflow-graph.json`,
consumed by `dh-workflow-explorer.html` via Cytoscape.js.

---

## Top-level shape

```json
{
  "meta": { ... },
  "nodes": [ ...Node ],
  "edges": [ ...Edge ],
  "overlays": { ...OverlayConfig },
  "routes": [ ...RouteManifest ]
}
```

Gap transitions are represented as `gap`-type edges within `edges` (see [gap](#gap) below) — there is no separate top-level `gaps` array.

---

## Node types

Seven node types. Every node carries `source_file` + `source_heading` so
the explorer can link to the evidence. Nodes without a traceable source must
set `verified: false`.

### step

A discrete action performed by an actor within a workflow reference file.

```json
{
  "id": "step.groom.wave1.impact-analyst.write-impact-radius",
  "type": "step",
  "label": "Write Impact Radius section",
  "actor": "agent.dh-impact-analyst",
  "source_file": "skills/work-backlog-item/references/workflows/groom/swarm.md",
  "source_heading": "## Wave 1 — impact-analyst",
  "verified": true,
  "conditional": false,
  "condition": null,
  "mcp_calls": [
    "mcp__plugin_dh_backlog__backlog_groom(selector, section='Impact Radius', content=...)"
  ],
  "reads_artifacts": [],
  "writes_artifacts": ["artifact.impact-radius-section"],
  "agents_dispatched": [],
  "metadata": {}
}
```

`conditional` and `condition` capture a guard on the step's execution — a step whose
execution depends on a guard sets `conditional: true` and records the guard text in
`condition`; unconditional steps set `conditional: false` and `condition: null`.

**Node ID convention:** `step.{route}.{reference-file-slug}.{actor-slug}.{action-slug}`
All slugs are lowercase, hyphens replaced with dots, special characters stripped.

**Verified-flag semantics:**

- `true` — the sonnet verifier confirmed the step: the source citation resolves to a
  real heading and the evidence quote matches the source text at ≥80%.
- `false` — extracted by a worker but not confirmed (verifier voted `PLAUSIBLE`), or a
  `weight=1` finding from `reduce.py` that no other worker corroborated.

### agent

An agent dispatched during the workflow.

```json
{
  "id": "agent.dh-impact-analyst",
  "type": "agent",
  "label": "dh:impact-analyst",
  "source_file": "agents/impact-analyst.md",
  "source_heading": "## Description",
  "verified": true,
  "metadata": {
    "model": "sonnet",
    "tools": ["Read", "Grep", "Glob", "Bash", "mcp__plugin_dh_backlog__backlog_groom"],
    "skills_loaded": [],
    "dispatch_mechanism": "TeamCreate"
  }
}
```

### skill

A skill loaded by an agent or invoked by a workflow step.

```json
{
  "id": "skill.dh-code-review-python",
  "type": "skill",
  "label": "dh:code-review-python",
  "source_file": "skills/code-review-python/SKILL.md",
  "source_heading": "## Activation",
  "verified": true,
  "metadata": {
    "trigger": "pyproject.toml or *.py file detected"
  }
}
```

### reference_file

An instruction or reference file loaded by an agent (the actual behavior,
not the SKILL.md router). These are the files that contain real behavior.

```json
{
  "id": "ref.groom-swarm-md",
  "type": "reference_file",
  "label": "groom/swarm.md",
  "source_file": "skills/work-backlog-item/references/workflows/groom/swarm.md",
  "source_heading": "# Swarm dispatch",
  "verified": true,
  "metadata": {
    "loaded_by": ["agent.dh-backlog-item-groomer"],
    "contains_steps": true
  }
}
```

### mcp_tool

A single tool exposed by an MCP server. Not a call — the capability itself.

```json
{
  "id": "mcp.backlog_groom",
  "type": "mcp_tool",
  "label": "backlog_groom()",
  "source_file": "backlog_core/server.py",
  "source_heading": "backlog_groom tool",
  "verified": true,
  "metadata": {
    "server": "dh-backlog",
    "mcp_name": "mcp__plugin_dh_backlog__backlog_groom",
    "params": ["selector", "section", "content", "sections", "mark_groomed"],
    "backend_aware": true
  }
}
```

### artifact

A document or data object produced and consumed across stages.
Includes backlog item sections, SAM plan YAML, registered artifacts, and ephemeral in-memory objects.

```json
{
  "id": "artifact.impact-radius-section",
  "type": "artifact",
  "label": "Impact Radius section",
  "source_file": "skills/work-backlog-item/references/workflows/groom/swarm.md",
  "source_heading": "## Wave 1 — impact-analyst",
  "verified": true,
  "metadata": {
    "artifact_type": "backlog_section",
    "section_name": "Impact Radius",
    "storage": "GitHub Issue body via backlog_groom()",
    "persistent": true,
    "consumed_by_phases": [3, 4]
  }
}
```

### backend

The configured storage layer. Not a node the workflow calls directly —
it's what the MCP server routes to. Shown on the MCP tools overlay.

```json
{
  "id": "backend.github",
  "type": "backend",
  "label": "GitHub (Issues + Gist)",
  "source_file": "backlog_core/backends/github_backend.py",
  "source_heading": "class GitHubBackend",
  "verified": true,
  "metadata": {
    "handles": ["backlog items", "artifact manifests", "gist content"],
    "config_key": "BACKLOG_BACKEND=github",
    "alternatives": ["beads", "sqlite", "memory"]
  }
}
```

---

## Edge types

Every edge carries `verified: true|false` and `gap: true|false`.
A gap edge is rendered differently in the explorer (dashed, amber).
An edge may additionally carry `status: "orphan"` — see [Orphan edges](#orphan-edges) below;
absent on every non-orphan edge.

```json
{
  "id": "e.work-rt-ica-gate.1-calls-mcp.backlog_view",
  "type": "calls",
  "source": "work.rt-ica-gate.1",
  "target": "mcp.backlog_view",
  "label": "backlog_view(selector, section='RT-ICA')",
  "verified": true,
  "gap": false,
  "source_file": "skills/work-backlog-item/references/workflows/work/rt-ica-gate.md",
  "source_heading": "## Step 1",
  "metadata": {
    "condition": null,
    "params": {"selector": "{item_ref}", "summary": false, "section": "RT-ICA"}
  }
}
```

### Edge type enum

| type | meaning |
|---|---|
| `calls` | step invokes a tool via MCP or the CLI (`sam_schema/cli.py`) |
| `dispatches` | orchestrator spawns an agent |
| `loads` | agent loads a skill or reference file |
| `reads` | step reads an artifact or section |
| `writes` | step writes an artifact or section |
| `defers_to` | step routes to another reference file |
| `routes_to` | conditional branch to a step |
| `stores_in` | MCP tool persists data to backend |
| `next` | sequential transition from one step to the next step |
| `gap` | transition exists but is unattested in source — see [gap](#gap) below |

### next

Sequential transition between two consecutive step nodes.

```json
{
  "id": "e.step.groom.wave1.impact-analyst.1-next-step.groom.wave1.impact-analyst.2",
  "type": "next",
  "source": "step.groom.wave1.impact-analyst.write-impact-radius",
  "target": "step.groom.wave1.impact-analyst.broadcast-result",
  "label": "",
  "verified": true,
  "gap": false,
  "source_file": "skills/work-backlog-item/references/workflows/groom/swarm.md",
  "source_heading": "## Wave 1 — impact-analyst"
}
```

### gap

An unattested transition — a workflow edge that must logically exist (for example,
between two adjacent steps) but has no direct evidence in the source file. Rendered as
a dashed, amber edge in the explorer. Required for correct blast-radius analysis: a
silent gap produces an incorrect impact assessment.

```json
{
  "id": "gap.work-prepare-to-feature-request",
  "type": "gap",
  "source": "step.work.prepare.orchestrator.last",
  "target": "step.work.feature-request.orchestrator.first",
  "label": "Transition from prepare.md terminal step to feature-request.md not explicitly attested in either file",
  "verified": false,
  "gap": true,
  "source_file": "skills/work-backlog-item/references/workflows/work/prepare.md",
  "source_heading": null
}
```

**Fields:**

| Field | Type | Semantics |
|---|---|---|
| `id` | string | Unique edge identifier. |
| `type` | string | Always `"gap"`. |
| `source` | string | Node ID the transition originates from. |
| `target` | string | Node ID the transition leads to. |
| `label` | string | Human-readable description of the missing transition. |
| `verified` | boolean | Always `false` for gap edges. |
| `gap` | boolean | Always `true` for gap edges. |
| `source_file` | string \| null | File where the gap was identified, if applicable. |
| `source_heading` | string \| null | Heading where the gap was identified, if applicable. |

### Orphan edges

An edge whose `source` or `target` node id is absent from the assembled node set. Node ids
are deterministic slugs of layer-file keys (see `assemble_graph.py`'s `slugify`/`_node_id`).
Renaming a key in any `docs/workflow-layers/*.json` layer file changes that slug on
re-extraction, orphaning every edge that still references the old id.

`self_check()` in `assemble_graph.py` **preserves** orphan edges — it never deletes them.
Each orphan edge is annotated in place with `status: "orphan"` and `verified: false`; a
non-orphan edge is returned unchanged (no `status` key added). This replaces the prior
behavior of silently dropping the edge and printing an `ORPHAN REMOVED` line to stderr, which
no consumer of the output JSON could observe. `meta.orphan_count` (assembled output, see
`_build_graph_dict`) is always computed from the actual edge set, never hardcoded, mirroring
`meta.gap_count`.

`status: "orphan"` is a distinct concept from `gap`: a `gap` edge marks a transition that is
real but unattested by source data; `status: "orphan"` marks a transition whose recorded
endpoint no longer exists in the current node set. An orphan edge never also sets `gap: true`.

```json
{
  "id": "e.work-backlog-item-q3-2.yes.branch",
  "type": "branch",
  "source": "fork.work_backlog_item_q3_2",
  "target": "fork.renamed_condition",
  "label": "YES",
  "status": "orphan",
  "verified": false,
  "gap": false,
  "source_file": "skills/work-backlog-item/references/workflows/work/prepare.md",
  "source_heading": "## Step 3"
}
```

**Explorer rendering:** Cytoscape.js requires every edge's `source`/`target` to reference an
id already present in the element set it is given — a dangling reference throws and aborts
the whole render, not just that one edge. `dh-workflow-explorer.html`'s `buildElements()`
therefore keeps orphan edges (`status === "orphan"`) out of the elements passed to Cytoscape
while every other edge (including `gap` edges) still renders as before. Orphan edges remain
fully present in the JSON — `meta.orphan_count` and any offline tooling can still see them —
they are just not drawn on the graph canvas.

---

## Overlay configuration

Defines the six toggleable views. Each overlay specifies how to color
nodes and which edge types to show/hide when active.

```json
{
  "overlays": {
    "workflow": {
      "label": "Workflow",
      "description": "Steps and routing only",
      "node_types_visible": ["step"],
      "edge_types_visible": ["defers_to", "routes_to", "gap"],
      "color_by": null
    },
    "agents": {
      "label": "Agents",
      "description": "Color each step by the agent that handles it",
      "node_types_visible": ["step", "agent"],
      "edge_types_visible": ["dispatches", "defers_to", "routes_to"],
      "color_by": "agent",
      "palette": {
        "agent.dh-impact-analyst": "#6c8ef5",
        "agent.dh-fact-checker": "#7dd3a8",
        "agent.dh-classifier": "#f5a623",
        "agent.dh-rtica-assessor": "#5bc0de",
        "agent.dh-backlog-item-groomer": "#e05c5c",
        "unassigned": "#c8ccd8"
      }
    },
    "skills": {
      "label": "Skills loaded",
      "description": "Show which skills each agent loads",
      "node_types_visible": ["step", "agent", "skill"],
      "edge_types_visible": ["dispatches", "loads"],
      "color_by": "skill_count"
    },
    "instructions": {
      "label": "Instructions",
      "description": "Show which reference files are loaded per agent",
      "node_types_visible": ["step", "agent", "reference_file"],
      "edge_types_visible": ["dispatches", "loads"],
      "color_by": "reference_file"
    },
    "tools": {
      "label": "MCP tools",
      "description": "Show exact MCP tool calls per step, grouped by server",
      "node_types_visible": ["step", "mcp_tool", "backend"],
      "edge_types_visible": ["calls", "stores_in"],
      "color_by": "mcp_server",
      "palette": {
        "dh-backlog": "#6c8ef5",
        "dh-sam": "#7dd3a8",
        "direct": "#c8ccd8"
      }
    },
    "artifacts": {
      "label": "Artifact flow",
      "description": "Show reads and writes as directional edges, colored by artifact type",
      "node_types_visible": ["step", "artifact"],
      "edge_types_visible": ["reads", "writes"],
      "color_by": "artifact_type",
      "palette": {
        "backlog_section": "#6c8ef5",
        "sam_plan": "#7dd3a8",
        "gist_artifact": "#f5a623",
        "ephemeral": "#c8ccd8"
      }
    }
  }
}
```

---

## Route manifest

One entry per workflow route. Used to filter the graph by route
and to wire inter-route connections.

```json
{
  "routes": [
    {
      "id": "create",
      "label": "Create",
      "entry_step": "create.start.1",
      "terminal_steps": ["create.start.6"],
      "exits_to": ["groom"],
      "flags": [],
      "phase": 1
    },
    {
      "id": "groom",
      "label": "Groom",
      "entry_step": "groom.intake.1",
      "terminal_steps": ["groom.finally.terminal-groomed", "groom.finally.terminal-blocked"],
      "exits_to": ["work"],
      "flags": ["--auto"],
      "phase": 2
    }
  ]
}
```

---

## Extraction Pipeline Files

Supporting files produced and consumed by the workflow extraction pipeline
(`enumerate_scope.py`, `dh-extract-file.js`, `merge_layer.py`). These are inputs to,
and byproducts of, building the layer JSON files consumed by the assembler — they are
not part of the assembled `dh-workflow-graph.json` shape itself.

### meta.json — staleness tracking

**Path:** `docs/workflow-layers/meta.json`

```json
{
  "last_analyzed_commit": "a8a9174f8c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
  "last_analyzed_at": "2026-06-19T15:30:00Z",
  "scope_version": "sha256:3a4b5c6d7e8f..."
}
```

| Field | Type | Semantics |
|---|---|---|
| `last_analyzed_commit` | string | Full 40-character SHA of the last commit for which extraction ran. Empty string when no extraction has run. |
| `last_analyzed_at` | string | ISO 8601 timestamp of the last extraction completion. |
| `scope_version` | string | `sha256:<hex>` of the `SCOPE.md` content at the time of the last extraction. When this changes, the scope set has changed and a full re-crawl is needed. |

The SessionStart staleness hook writes `meta.json` after successful extraction.
`merge_layer.py` does NOT write `meta.json` — that is the hook's responsibility.

### SCOPE.md — reachable file set

**Path:** `docs/workflow-layers/SCOPE.md`

Markdown table, one row per reachable file, produced by `enumerate_scope.py`.

```markdown
# DH Workflow Extraction Scope

Generated by enumerate_scope.py. Do not edit manually.
Last generated: 2026-06-19T15:00:00Z
Entry points: work-backlog-item, groom-milestone, work-milestone, complete-milestone, create-milestone, start-milestone, group-items-to-milestone

| file_path | entry_point | reference_type | depth |
|---|---|---|---|
| skills/work-backlog-item/SKILL.md | work-backlog-item | entry_point | 0 |
| skills/work-backlog-item/references/workflows/groom/swarm.md | work-backlog-item | mermaid_node | 1 |
| agents/impact-analyst.md | work-backlog-item | agent_dispatch | 2 |
```

`reference_type` values: `entry_point`, `mermaid_node`, `prose_skill`, `agent_dispatch`, `prose_file`.

`enumerate_scope.py` produces the same output given the same input files (deterministic
BFS). The SHA-256 of `SCOPE.md` content serves as `scope_version` in `meta.json`.

### Fragment — per-file ETL intermediate

**Path convention:** `.tmp/fragments/{slug}-{timestamp}.json` (ephemeral, not committed)

```json
{
  "meta": {
    "source_file": "skills/work-backlog-item/references/workflows/groom/swarm.md",
    "layer_type": "step",
    "extracted_at": "2026-06-19T15:00:00Z",
    "verified_count": 12,
    "unverified_count": 2
  },
  "items": [],
  "unverified_items": []
}
```

Fragment files are written by `dh-extract-file.js` after the sonnet verifier completes.
`merge_layer.py` reads them and removes them after a successful merge into the layer file.

### Miss log — extraction quality feedback

**Path convention:** `.tmp/extraction-misses/{YYYY-MM-DD}-{source-slug}.md`

```markdown
# Extraction Miss Log

Source file: skills/work-backlog-item/references/workflows/groom/swarm.md
Date: 2026-06-19
Commit: a8a9174f

## Weight-1 Findings (missed by all workers except one)

### Finding 1
- group: 5
- location: groom/swarm.md:wave_1_impact_analyst
- evidence: "Send result to team-lead via SendMessage"
- verifier_vote: CONFIRMED
- rule_slug: agent-dispatch-send-message

Pattern analysis: workers missed `SendMessage` as an agent dispatch because rule group 5 patterns
focus on `TeamCreate` and `subagent_type`. Add `SendMessage(to=...)` as an explicit dispatch pattern.
```

Miss logs are never committed. They are read periodically to refine
`docs/workflow-layers/extraction-rules.json`.

---

## Cytoscape.js consumption

The explorer loads this file and maps it as follows:

```javascript
// Node mapping
cy.add(graph.nodes.map(n => ({
  data: { id: n.id, label: n.label, type: n.type, ...n.metadata },
  classes: [n.type, n.verified ? 'verified' : 'unverified']
})))

// Edge mapping
cy.add(graph.edges.map(e => ({
  data: { id: e.id, source: e.source, target: e.target,
          type: e.type, label: e.label },
  classes: [e.type, e.gap ? 'gap' : 'attested']
})))

// Overlay toggle
function applyOverlay(overlayId) {
  const ov = graph.overlays[overlayId]
  cy.nodes().hide()
  cy.nodes(`[type]`).filter(n => ov.node_types_visible.includes(n.data('type'))).show()
  cy.edges().hide()
  cy.edges(`[type]`).filter(e => ov.edge_types_visible.includes(e.data('type'))).show()
  applyColorBy(ov.color_by, ov.palette)
}

// Upstream/downstream highlight on click
cy.on('tap', 'node', function(evt) {
  const node = evt.target
  const upstream = node.predecessors()
  const downstream = node.successors()
  cy.elements().addClass('dimmed')
  node.union(upstream).union(downstream).removeClass('dimmed').addClass('highlighted')
})
```

---

## What the workflow assembler must output

The assembler receives synthesized route flows and must produce this schema.
Key rules:

1. Every step node gets `source_file` + `source_heading` from the fragment it came from
2. Every edge of type `gap` sets `gap: true` and `verified: false`
3. Agents are extracted from `agents_dispatched[]` arrays in step nodes (edge type `dispatches`)
4. MCP tool nodes are extracted from `mcp_calls[]` strings starting with `mcp__`. Some workflow
   reference files document the CLI form (`uv run plugins/development-harness/sam_schema/cli.py
   <command>`) instead of the MCP call — those `mcp_calls[]` entries do not start with `mcp__`
   and are not extracted as `mcp_tool` nodes by this rule; a future assembler revision would need
   a second pattern for CLI-form entries to keep those edges represented.
5. Artifact nodes are extracted from `reads_artifacts[]` and `writes_artifacts[]` arrays in step nodes
6. Skills are extracted from agent frontmatter `tools:` field (requires a second pass over agent files)
7. Reference files are extracted from `enumerate_scope.py`'s scope enumeration (see SCOPE.md above), not from step node fields
