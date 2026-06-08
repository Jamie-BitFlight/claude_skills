# DH Workflow Trace — Collection Methodology

Defines how to systematically collect, store, and query the DH workflow execution model.
Written after two failed collection passes (pass 1: 67 agents; pass 2: 120 agents) to
record the root causes and the corrected approach.

See `docs/workflow-layers/COVERAGE.md` for what has been collected and how to answer
follow-up questions without restarting.

---

## Root cause of the failed passes

Both failed passes shared the same ordering error:

1. Invented a schema
2. Sent agents to read files and populate it
3. The schema predetermined what agents looked for
4. Anything not in the schema was never collected

Specifically:
- Pass 1 schema had no field for actor identity or concurrency — so no agent looked for them
- "SKILL.md is routing-only" was an unverified belief that caused the load-bearing files (`implement-feature/SKILL.md`, `complete-implementation/SKILL.md`) to be skipped — these contain the decision trees, not the reference files
- Flat step extraction destroyed the graph-of-graphs structure: a Mermaid node that says "Load X.md" was recorded as a step, discarding the expansion link. 101 "gaps" were artifacts of this flattening — they were always file-reference links, not missing connections.

**The fix:** read first, extract the source's own structure faithfully, choose shapes after.

---

## The source's own structure: graph-of-graphs

DH workflow files are not step sequences. They are a **graph of graphs**:

- A SKILL.md contains Mermaid flowcharts whose nodes may reference other files
- Each referenced file may contain its own Mermaid flowcharts
- The recursion bottoms out at prose leaves

A Mermaid diamond `Q{...}` is a decision node. Each outgoing labeled edge is a branch.
A branch target that says "Load X.md" or names another skill is an **expansion link** — it
means follow that file and continue reading. The 101 "gaps" in pass 1 were these expansion
links that the flat extractor didn't follow.

**Extraction rule:** follow file references into the referenced file and continue reading.
Record the path in `crosses_into_files` or `target_file`. Stopping at the reference
instead of following it is the most common extraction failure.

---

## Execution model: spans, not steps

The system is a tree of **execution spans**. One span = one actor running once: receives
instructions, loads skills, calls tools in order, produces outputs, hands control back.

### Actor topology (the field pass 1 lacked entirely)

| topology | dispatch mechanism | concurrency | cite from |
|---|---|---|---|
| `orchestrator` | none — session runs the step directly | n/a | step text in skill/reference file |
| `subagent` | `Agent(subagent_type=...)` | sequential, isolated context | the step that calls Agent |
| `team-member` | `TeamCreate(...)` | parallel with siblings | the step that calls TeamCreate + wave definition |
| `hook` | lifecycle trigger (`SubagentStop`, `PostToolUse`) | fires on event | `hooks/hooks.json` matcher |

**Never default topology to `orchestrator`.** Absence is `unverified: true`.

### Two-hop dispatch (profile-load-mediated)

implement-feature dispatches `subagent_type="dh:task-worker"` always. task-worker reads
the SAM task `agent:` field and calls `profile_load(agent_name=...)` to specialize itself.
The span tree is:

```
orchestrator-span
  └─ dispatches → task-worker-span  (subagent_type="dh:task-worker")
        └─ profile_load(agent:) → specialist behavior loaded INTO same span
```

This is distinct from groom swarm TeamCreate, which names specialists directly. The join
must distinguish these two shapes or every task-worker span resolves to the wrong actor.

SOURCE: `plugins/development-harness/CLAUDE.md` → "Dispatch Pattern"

### Conditional topology

`implement-feature` branches on `autonomy_mode`: `per_task` → single `Agent`; `full_auto`
/ `checkpoint` → `TeamCreate`. Record as:

```json
"topology": {
  "conditional_on": "plan.autonomy",
  "cases": {"per_task": "subagent", "full_auto": "team-member", "checkpoint": "team-member"},
  "source": "skills/implement-feature/SKILL.md:step 3"
}
```

SOURCE: `workflow-result.json` → `implement-feature.progress-loop-step-3-dispatch`

---

## Collection protocol (correct order)

### Phase 0 — Validation gate (mandatory before any fan-out)

Two gates. Neither Phase A nor B launches until both pass.

**Gate 1:** Prove the schema on ONE route by hand (~10 reads, no fan-out). Build the
complete `groom` span tree from `groom/swarm.md` + 5 Wave-1 agent files + their tools.
Pass criterion: every schema field fills with a real citation, zero forced or null fields.

**Gate 2:** Scope and cost approved by the user. State exact file count and estimated
agent count before launching. Cost has surprised the user; a third surprise is the failure
to avoid.

### Phase A — Enumerate (deterministic script, no agent)

Glob the source set into a coverage checklist:
- `skills/*/SKILL.md` — orchestrator entry points
- `skills/*/references/**/*.md` — sub-procedures, dispatch points
- `agents/*.md` — actor identities
- `@mcp.tool` in server code — tool behavior
- `hooks/hooks.json` — hook actors

### Phase B — Extract per file (parallel, one `dh:workflow-extractor` per file)

Each agent reads ONE file and extracts into fragments. The agent file is
`agents/workflow-extractor.md` — haiku model, `Read, Grep, Glob, Write, Edit, Bash` only.

**Hard rule in every extraction prompt:** fill only what the file literally attests.
Uncited fields → `null` + `unverified: true`. Never default topology.

Three extraction families (different target fields per source type):
- B1 skill/reference files: steps, dispatch points, topology, waves, barriers, prompt templates
- B2 agent files: actor identity, model, tools, skills-loaded, STATUS contract, responds-to
- B3 MCP server code: tool name, params, backend routing (reuse existing verified traces)

### Phase C — Join (one agent per route)

For each route, join B1+B2+B3 on agent name + tool name:
1. Dispatch point (B1) names agent + topology
2. Resolve agent name → agent file identity (B2)
3. Resolve tool → backend behavior (B3)
4. Apply two-hop resolution where dispatch names `task-worker`
5. GAP RULE: unresolvable → `unverified: true` span, never silently completed

### Phase D — Assemble + verify

1. Build span tree from `parent_span` links
2. Verify every `source` citation resolves to a real file+heading
3. Re-open 3–4 synthesized spans against their cited source (catch smoothing)
4. Project spans → graph

---

## How this maps to overlays

| Overlay | Span fields used | Answers |
|---|---|---|
| **Actor** | `actor.topology` + `triggered_by.mechanism` | Who runs this — orchestrator, one agent, or team? |
| **Instructions** | `instructions.skills_loaded` + `instructions.agent_file` | What guides this actor? |
| **Tools** | `tool_calls[]` + backend routing | What does this call, and where does it land? |
| **Artifacts** | `outputs[]` + `consumed_by_spans` | What is produced and who consumes it? |
| **Handoff** | `responds_to` + STATUS contract | Who does this actor report back to? |
| **Concurrency** | `triggered_by.concurrency` + wave + siblings | What runs simultaneously, where is the barrier? |

---

## What the graph-of-graphs means for the explorer

The explorer should be hierarchical, not flat:
- Top-level nodes: the major lifecycle phases (create/groom/work/add-new-feature/implement-feature/complete-implementation)
- Click a phase node: expands into the Mermaid decision graph for that skill
- Click a decision node that has an expansion link: expands into the referenced file's graph
- Collapse back: returns to parent view

This mirrors how the orchestrator actually loads the files at runtime.

---

## Ordering rule (enforced)

```
WRONG: schema → agents read files → graph
RIGHT: read files → data exists → schema derived from data → extract → graph
```

A schema written before reading source encodes the author's beliefs, not the system's
structure. Both failed passes made this mistake. The methodology does not — Phase 0
validates the schema on one route before any fan-out.
