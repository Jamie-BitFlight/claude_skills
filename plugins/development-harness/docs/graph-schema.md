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
  "routes": [ ...RouteManifest ],
  "gaps": [ ...Gap ]
}
```

---

## Node types

Seven node types. Every node carries `source_file` + `source_heading` so
the explorer can link to the evidence. Nodes without a traceable source must
set `verified: false`.

### step

One discrete action in a workflow reference file.

```json
{
  "id": "work.rt-ica-gate.1",
  "type": "step",
  "label": "Read RT-ICA section",
  "route": "work",
  "phase": 3,
  "source_file": "skills/work-backlog-item/references/workflows/work/rt-ica-gate.md",
  "source_heading": "## Step 1",
  "verified": true,
  "metadata": {
    "action": "backlog_view(selector, summary=false, section='RT-ICA')",
    "gate": true,
    "gate_condition": "Date > 7 days OR metadata.updated_at > Date",
    "gate_outcome_pass": "proceed",
    "gate_outcome_fail": "re-run dh:rt-ica"
  }
}
```

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
| `calls` | step invokes a tool or MCP call |
| `dispatches` | orchestrator spawns an agent |
| `loads` | agent loads a skill or reference file |
| `reads` | step reads an artifact or section |
| `writes` | step writes an artifact or section |
| `defers_to` | step routes to another reference file |
| `routes_to` | conditional branch to a step |
| `stores_in` | MCP tool persists data to backend |
| `gap` | transition exists but is unattested in source |

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

## Gap list

Every unattested transition collected across all routes.
Rendered as dashed amber edges in the explorer.

```json
{
  "gaps": [
    {
      "id": "gap.work-prepare-to-feature-request",
      "between": "work.prepare.LAST → work.feature-request.1",
      "description": "Transition from prepare.md terminal step to feature-request.md not explicitly attested in either file",
      "route": "work",
      "phase": 3,
      "severity": "medium"
    }
  ]
}
```

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
3. Agents are extracted from `agents_dispatched[]` arrays in step fragments
4. MCP tool nodes are extracted from `tool_or_agent` strings starting with `mcp__`
5. Artifact nodes are extracted from `reads[]` and `writes[]` arrays in step fragments
6. Skills are extracted from agent frontmatter `tools:` field (requires a second pass over agent files)
7. Reference files are extracted from `defers_to[]` arrays in step fragments
