# PRD: DH Workflow Extractor System

**Status:** Draft v4 amended — fact-checked 2026-06-16; five design decisions resolved 2026-06-19  
**Date:** 2026-06-15 (amended 2026-06-19)  
**Authority:** Historical design snapshot. Tool-call forms below are captured extraction patterns,
not current executable signatures. Use the live server schemas and maintained architecture docs.
**Sources read:** plugin.json, hooks.json, work-backlog-item SKILL.md, groom/swarm.md,
add-new-feature SKILL.md, impact-analyst.md, claude-plugins-reference-2026,
claude-skills-overview-2026, workflow-trace-methodology.md, COVERAGE.md,
graph-schema.md, plan_ensemble.py, reduce.py, ensemble-rule-review SKILL.md,
claude-code-workflows docs

---

## Problem Statement

The DH plugin needs a machine-readable, always-current graph of its own workflow serving two
consumers:

- **AI agents**: impact radius analysis and change propagation — "if I modify skill X, what
  actors, steps, MCP calls, and artifacts does that affect?"; and developing agent tests for
  the system by knowing what each component does and what it depends on.
- **Human developers**: responsibility mapping and comprehension — what does the system do,
  who does what, what can be simplified, how to debug the system as a whole.

The current graph captures decision forks (Mermaid diamonds) but not execution steps — the
wrong granularity for both use cases. It has no incremental update path, no quality-verified
data, and no mechanism to stay current with repo changes.

---

## Goals

1. Produce an actor-step graph with verified fidelity to source files.
2. Keep the graph consistent with the repo: post-commit hook triggers re-extraction for
   changed files automatically.
3. Make updates incremental: one changed source file triggers re-extraction of only that
   file's contribution to each affected layer.
4. Make quality observable and improvable: every node carries a verification status; haiku
   extraction misses are logged to drive extraction rule refinement.
5. Support both decision-flow and step-flow views in the same graph.
6. Enable AI agent test generation: an AI agent reading the graph should be able to identify
   what each component does, what it calls, and what it depends on — sufficient to write
   targeted tests for any part of the system.

## Non-Goals

- The extraction infrastructure (workflow-extractor agents, scripts) is not itself in scope
  for the graph.
- Real-time (sub-second) graph updates.
- Coverage of files outside the reachable set from the defined entry points.
- Hook script internals (`.cjs`, `.py` scripts) — hooks appear as actors but their
  implementation is not traced.

---

## Plugin Referencing Patterns (authoritative, read from source)

Understanding how the DH plugin's components reference each other is prerequisite to
defining extraction rules and scope enumeration. These patterns were read from actual source
files.

### How skills reference other skills

In Mermaid diagram node labels:
```
Load references/workflows/groom/start.md
→ groom/swarm.md
routes to work/start.md
```

In prose instructions to Claude:
```
/dh:add-new-feature          ← slash-command invocation
Skill(skill='find-cause')   ← explicit skill loading
```

### How agents are dispatched

In prose and Mermaid:
```
subagent_type="dh:impact-analyst"           ← Agent tool call
TeamCreate(team_name: "groom-{item-slug}")  ← team with named members
```

Agent files are in `agents/*.md`. Each agent's frontmatter declares `tools:`, `model:`,
`description:`. The body is the prompt that drives the agent.

### How MCP tools appear in source

Three forms appear in prose and Mermaid — two MCP call forms plus the provider-neutral CLI:

**Full form** (matches the actual tool name registered by MCP server):
```
mcp__plugin_dh_backlog__backlog_groom(selector='{item_ref}', section='Impact Radius', content='...')
mcp__plugin_dh_backlog__artifact_register(content=..., item_id=..., artifact_type=...)
mcp__plugin_dh_sam__sam_plan(action='status', plan=...)
```

**Short form** (human-readable shorthand used in prose):
```
backlog_groom(selector, section='Impact Radius', content='...')
backlog_view(selector, summary=False, section='RT-ICA')
artifact_read(item_id=..., artifact_type=...)
artifact_register(content=..., item_id=..., artifact_type=...)
sam_plan(action='create', ...)
sam_task(action='claim', plan=..., task=...)
```

**CLI form** (`sam_schema/cli.py`, a Typer app — used where a workflow step documents the
provider-neutral CLI instead of, or alongside, an MCP call; see
[TASK_FILE_FORMAT.md](../TASK_FILE_FORMAT.md) "DH CLI Usage Guide" and
[backend-providers.md](../backend-providers.md) "CLI vs MCP Capability Surface" for the full
mapping):
```
 backlog groom --selector "{item_ref}" --section "Impact Radius" --content "..."
 plan status --plan-address {plan}
```

The full and short MCP forms are semantically identical; the CLI form is a distinct transport
that reaches the same `backlog_core.operations`/`sam_schema.core` code paths (no parallel
implementation) but is not itself an MCP call. Extraction rules must recognise all three —
a `mcp_calls[]` entry that does not start with `mcp__` may be a CLI invocation rather than the
short MCP form; see [graph-schema.md](../graph-schema.md) "What the workflow assembler must
output" rule 4 for the current gap in automated recognition of CLI-form entries. Not every MCP
tool has a CLI equivalent — see the capability-surface tables cited above before assuming a CLI
form exists for a given tool.

**Server routing** (from plugin.json):
- `mcp__plugin_dh_backlog__*` → `scripts/run_backlog_server.py`
- `mcp__plugin_dh_sam__*` → `scripts/run_sam_server.py`
- CLI form → `sam_schema/cli.py` (single entry point; not routed per-tool)

### How reference files are loaded

Reference files (`references/workflows/*/start.md`, `references/workflows/groom/swarm.md`
etc.) are loaded when a Mermaid node label or prose instruction names them. Claude follows
the reference and executes the named file's instructions. This is the graph-of-graphs
expansion mechanism.

They are NOT imported at parse time. They are followed at runtime when the node is reached.

### How scripts are used

Scripts (`scripts/parser/parse.mjs`, hook scripts in `hooks/`) are invoked via Bash tool
calls using `${CLAUDE_SKILL_DIR}/scripts/...` or `${CLAUDE_PLUGIN_ROOT}/scripts/...`.

Scripts are infrastructure — they are NOT workflow actors and are NOT nodes in the graph.
Their inputs and outputs may appear as step details but the scripts themselves are not traced.

### How assets are used

Assets (`assets/*.md`, worker prompt templates, delegation preambles) are read by Claude
during skill execution. They contribute to step content but are not graph nodes.

### How hooks work

`hooks/hooks.json` declares event handlers:
- `SessionStart` — fires at session open
- `PostToolUse` — fires after Write, Edit, Bash
- `SubagentStop` — fires when a subagent completes
- `TaskCompleted` — fires on task completion

Hook actors appear in the graph as `hook` type nodes. They have steps (the script they run
and what they do). Hook scripts themselves are not traced.

---

## Scope Definition

### Entry points

The reachable file set is computed from two entry point families:

- `*-milestone` skills: `groom-milestone`, `work-milestone`, `complete-milestone`,
  `create-milestone`, `start-milestone`, `group-items-to-milestone`
- `work-backlog-item` skill and its full reference tree (40+ files in `references/workflows/`)

### Reachability rules

A file is in scope if it is reachable from an entry point via any of these reference types:

| Reference type | Pattern to detect |
|---|---|
| Mermaid node → reference file | Node label contains a `.md` path: `Load references/...`, `→ groom/swarm.md` |
| Prose → skill | `/dh:skill-name`, `Skill(skill='dh:skill-name')` |
| Agent dispatch | `subagent_type="dh:agent-name"`, `TeamCreate()` member list |
| Prose → reference file | "Read `references/workflows/X/start.md`", "Load `X.md`" |

Recursion stops when no new files are discovered. Max depth: 15 (prevents infinite loops on
circular references).

### Stub skills — not entry points

`groom-backlog-item` and `create-backlog-item` are one-line stubs that invoke
`work-backlog-item` with a mode argument. Confirmed from source:

```
# groom-backlog-item/SKILL.md body:
Invoke `/dh:work-backlog-item groom $ARGUMENTS` and follow its instructions.

# create-backlog-item/SKILL.md body:
Invoke `/dh:work-backlog-item create $ARGUMENTS` and follow its instructions.
```

Do NOT trace them as independent execution entry points. They have no execution logic.
Tracing them would produce duplicate graph structure referencing what `work-backlog-item`
already covers. Canonical entry points:

```
create-backlog-item  →  /dh:work-backlog-item create
groom-backlog-item   →  /dh:work-backlog-item groom
```

### What enumerate_scope.py produces

A flat file list: `docs/workflow-layers/SCOPE.md`. Each entry: file path, entry point it was
reached from, reference type that included it.

---

## Graph Data Model

### Node types

**decision** — an explicit conditional fork with named branches. Extracted from Mermaid
diamond nodes (`Q{...}`, `D{...}`). The condition IS the structure.

```json
{
  "id": "fork.rt-ica-verdict",
  "type": "decision",
  "label": "RT-ICA verdict?",
  "actor": null,
  "source_file": "plugins/development-harness/skills/work-backlog-item/references/workflows/groom/swarm.md",
  "source_heading": "## Gate check",
  "verified": true,
  "branches": [
    {"condition": "BLOCKED", "target": "terminal.stop"},
    {"condition": "APPROVED", "target": "step.groom.wave1.1"}
  ]
}
```

**step** — a discrete action performed by an actor. May carry an optional guard condition.
Extracted from numbered/bulleted procedures in reference files.

```json
{
  "id": "step.groom.wave1.impact-analyst.write-impact-radius",
  "type": "step",
  "label": "Write Impact Radius section",
  "actor": "agent.dh-impact-analyst",
  "source_file": "plugins/development-harness/skills/work-backlog-item/references/workflows/groom/swarm.md",
  "source_heading": "## Wave 1 — impact-analyst",
  "verified": true,
  "conditional": false,
  "condition": null,
  "mcp_calls": [
    "mcp__plugin_dh_backlog__backlog_groom(selector, section='Impact Radius', content=...)"
  ],
  "reads_artifacts": [],
  "writes_artifacts": ["artifact.impact-radius-section"],
  "dispatches": [],
  "metadata": {}
}
```

**agent** — an actor defined in `agents/*.md`. Carries model, tools, skills loaded.

**skill** — a skill loaded by a step or agent (`/dh:rt-ica`, `Skill(skill='...')`).

**reference_file** — a workflow reference file loaded via expansion link.

**mcp_tool** — a single MCP tool capability (not a call — the tool itself).

**artifact** — a document or data object produced and consumed across steps.

**backend** — the storage layer an MCP tool routes to (GitHub, beads, sqlite, memory).

**hook** — a hook actor triggered by a lifecycle event (SessionStart, PostToolUse, etc.).

### Edge types

| type | meaning |
|---|---|
| `branch` | decision → next node (labelled with condition) |
| `next` | step → next step (sequential within a reference file) |
| `defers_to` | step or skill → reference file (expansion link) |
| `dispatches` | step → agent (via Agent tool or TeamCreate) |
| `calls` | step → mcp_tool |
| `reads` | step → artifact |
| `writes` | step → artifact |
| `loads` | agent → skill or reference_file |
| `stores_in` | mcp_tool → backend |
| `triggered_by` | hook → event type |
| `gap` | transition exists but is unattested — REQUIRED, rendered as dashed amber |

Gap edges are required. An AI agent doing impact analysis must know which transitions are
uncertain. Silent gaps produce incorrect blast-radius assessments.

### Existing L0–G8 data: enrichment role

G4 (dispatch topology), G8 (MCP backend routing), G2 (artifact producer/consumer) are
retained as enrichment to annotate step and mcp_tool nodes. They are not the primary
extraction target; steps are.

---

## Extraction Architecture

### Evidence sources: body content only

The `description:` frontmatter field and all other frontmatter fields are NOT valid evidence
sources for extraction. The description is a routing hint that tells Claude when to use the
skill or agent — it does not describe what the skill or agent actually does. Only body content
(the markdown below the frontmatter block) contains execution specifications.

This was established when it was confirmed: "The description of an agent or skill doesn't
direct what that skill or agent does right? It just the hook for when to use it."

Consequence: the graphify semantic extraction run produced INFERRED edges sourced from
description fields. Those edges were rejected as noise. Any extraction worker that cites
frontmatter text as evidence for an execution relationship is producing a wrong finding.

### KNOWN_ENTITIES.md — vocabulary oracle

Before reading any source file, extraction workers must load
`docs/workflow-layers/KNOWN_ENTITIES.md`. This file is the canonical reference for:
- All agent names (canonical `subagent_type` values)
- All skill names (canonical invocation names)
- All MCP tool names (full form and short-form aliases)
- All CLI subcommand names (`sam_schema/cli.py` groups and leaves)
- All registered artifact type keys
- All named backlog item section names

Workers validate every extracted entity name against this list. Short-form aliases are
resolved to canonical names before emitting a finding. When a worker finds a body-content
entity that is NOT in the list, it adds it to KNOWN_ENTITIES.md following the Living Document
Protocol before emitting the finding — so the file stays current as the plugin grows.

The file exists at:
`plugins/development-harness/docs/workflow-layers/KNOWN_ENTITIES.md`

### Extraction design (resolved 2026-06-19)

**Decision**: `enumerate_scope.py` (deterministic) is the outer loop. It follows all four
reference types to max depth 15 and produces SCOPE.md — the reachable file set. This IS the
"crawl." The per-file ensemble pipeline (haiku workers → `reduce.py` → sonnet verifier)
then runs against each file in SCOPE.md independently.

Rationale: deterministic outer loop gives idempotent scope, reproducible file sets, and
incremental update via merge_layer.py. Full ensemble per file is retained for the verified
fidelity that goal #1 requires. Group-6 ensemble workers also extract file references,
enabling self-correcting scope across cycles with gap edges marking uncertainty.

### Primitive: Dynamic Workflow

The orchestrator is a saved dynamic workflow script (`workflows/dh-extract-file.js`), not a
Claude agent. The workflow runtime keeps intermediate results in script variables (not
context), runs in the background, is resumable, and rerunnable with `args`.

```
args: { source_file, layer_type, report_dir? }

1. plan_ensemble.py  →  worker_assignments (deterministic)
2. spawn N haiku workers in parallel  →  N output files in report_dir
3. reduce.py --glob 'worker-*.md' --keep-threshold 4  →  ranked report (deterministic)
4. spawn sonnet verifier  →  CONFIRMED / PLAUSIBLE / REFUTED per finding
5. merge_layer.py  →  updated layer JSON (deterministic)
return: { layer_path, verified_count, unverified_count, miss_log_path }
```

Steps 1, 3, 5 are deterministic Python scripts. Only steps 2 and 4 use LLM.

### Worker fleet

**Workers:** Haiku homogeneous fleet. Cheap and 3–5× faster than sonnet. Reliable at
mechanical pattern matching when the rule slice is kept rigid and thin.

**Verifier:** One sonnet agent after reduce.py. For each surviving finding, it:
1. Reads the source file at the cited heading
2. Searches for the evidence quote (≥80% match acceptable)
3. Votes: CONFIRMED / PLAUSIBLE / REFUTED

REFUTED → `unverified_items`. PLAUSIBLE → main array with `verified: false`. CONFIRMED →
main array with `verified: true`.

**Miss log:** When the verifier CONFIRMS a weight=1 finding (haiku found it but only once),
logs to `.tmp/extraction-misses/{date}-{slug}.md`. This feeds extraction rule refinement —
patterns haiku missed can be made explicit in the next rule revision.

### Corroboration reform (reduce.py changes)

**Change 1 — Slug-normalised heading keys**

When location has no line number, normalise the heading before keying:
```
"groom/swarm.md:## Wave 1 — impact-analyst"
→ "groom/swarm.md:wave_1_impact_analyst"
```
Minor heading-text differences no longer break corroboration.

**Change 2 — Cross-group location signal**

A location found by workers from ≥2 different rule groups gets `cross_group: true` and
elevated priority in the ranked output. A step found by both a dispatch-pattern worker (group
5) and an artifact-flow worker (group 4) is more credible than one found by a single group.

### Fragment ETL (incremental update)

Each extraction run produces a source-scoped fragment file, not a direct layer JSON write:

```json
{
  "meta": {
    "source_file": "skills/work-backlog-item/references/workflows/groom/swarm.md",
    "layer_type": "step",
    "extracted_at": "2026-06-10T15:00:00Z",
    "verified_count": 12,
    "unverified_count": 2
  },
  "items": [...],
  "unverified_items": [...]
}
```

`merge_layer.py` (new deterministic script):
```
1. Read existing layer JSON
2. Remove all items where item.source_file == fragment.meta.source_file
3. Append fragment.items
4. Write back layer JSON
5. Print: removed N, added M, total T
```

Idempotent. Running twice with the same fragment produces the same result.

---

## Extraction Rules

9 rule groups. Window=4 → 9 workers with 4× uniform coverage.

Workers extract from a single source file. Every worker reads the SAME file; only the rule
slice differs. The denoising comes from overlapping rule coverage on shared input.

| Group | What to find | Source evidence patterns |
|---|---|---|
| 1 | Numbered/bulleted steps: actor + action text | "1. Call...", "- Agent reads...", wave headers with step lists |
| 2 | Conditional guards on steps | "If --quick", "When BACKLOG_BACKEND=", "Skip when:", "Only if:" |
| 3 | Artifact reads per step | `artifact_read(...)`, `backlog_view(..., section='...')`, `sam_plan(action='status')` |
| 4 | Artifact writes per step | `artifact_register(content=...)`, `backlog_groom(section=..., content=...)`, `sam_plan(action='create')` |
| 5 | Agent dispatch per step | `subagent_type="dh:..."`, `TeamCreate(team_name=...)`, named wave members |
| 6 | File-reference expansion links | Mermaid node: `Load X.md`, `→ groom/swarm.md`; prose: "Read `references/...`" |
| 7 | Skill invocations | `/dh:skill-name`, `Skill(skill='dh:...')` |
| 8 | MCP tool calls (full and short form) and CLI-form invocations | `mcp__plugin_dh_backlog__*`, `backlog_groom(...)`, `sam_task(...)`, `artifact_list(...)` |
| 9 | Actor topology per dispatch | `orchestrator` (inline), `subagent` (Agent tool), `team-member` (TeamCreate), `hook` (lifecycle event) |

**Output schema per finding (fixed — all workers emit this shape):**
```yaml
- group: <1-9>
  rule: <free-form slug — not the corroboration key>
  location: <relative/path/from/plugin/root.md:## Exact Section Heading>
  verdict: VIOLATION   # means "found an instance"
  severity: high
  evidence: "<verbatim quote from source, max 200 chars>"
```

`location` uses plugin-relative paths (not absolute, not CLAUDE_SKILL_DIR-relative) so the
key is stable across environments.

---

## Understand-Anything (UA) Integration

### Infrastructure to adopt

UA (`~/repos/understand-anything`) provides mature, tested implementations of mechanisms this
PRD designs from scratch. The Opus advisor confirmed: "UA's infrastructure — fingerprinting,
change-classifier, post-commit hook pattern — are mature and tested. Your PRD reinvents all
of these."

Components to port or adopt:

| UA component | File | What it provides |
|---|---|---|
| Fingerprinting | `packages/core/src/fingerprint.ts` | SHA-256 per file, change detection |
| Change classifier | `packages/core/src/change-classifier.ts` | SKIP/PARTIAL/ARCHITECTURE/FULL scope |
| Post-commit hook | `hooks/hooks.json` | HEAD vs `meta.json` staleness detection |
| Merge + reviewer pattern | `file-analyzer` → `merge-batch-graphs.py` → `assemble-reviewer` | Batch merge with gap recovery |

The post-commit hook in UA already fires on git commits, reads the last-analyzed commit hash
from `meta.json`, detects changed files, and triggers incremental re-analysis. This is the
exact pattern this PRD needs.

### UA extraction is not suitable for workflow graph extraction

UA's `article-analyzer` agent extracts implicit knowledge (entities, claims, implicit
relationships) from markdown. It was evaluated by reading its output schema directly.
Finding: edges carry a `weight` and `description` (LLM reasoning) but no verbatim source
quote. Rule 2 says "only create edges with clear textual evidence" — but this is left to LLM
judgment, not verified by a locatable quote.

This is the same failure mode as the INFERRED edges rejected from the graphify extraction
run. UA extraction cannot serve as the extraction engine for the workflow graph because it
does not meet the evidence-quote grounding requirement.

### UA graph already exists

UA has already been run against the DH plugin and produced a graph at
`.understand-anything/knowledge-graph.json` (224 nodes, 411 edges). The dashboard renders
DH plugin entities correctly: agents appear as `service` nodes, MCP tools as `endpoint`
nodes with full canonical names, and the 6 overlays match the workflow graph's overlay design
(Workflow, Agents, Instructions, MCP Tools, Artifact Flow, Concurrency).

Whether the workflow extraction graph supplements the UA graph, replaces it, or is stored
separately is an open decision (see Open Implementation Decisions).

---

## Phase A: Scope Enumeration (deterministic, no LLM)

Before any extraction, enumerate the full reachable file set.

**Script:** `scripts/enumerate_scope.py`

```
Input:  entry point skill names
Output: docs/workflow-layers/SCOPE.md

Algorithm:
  queue = [entry point SKILL.md files]
  visited = {}
  while queue not empty:
    file = queue.pop()
    if file in visited: continue
    visited[file] = True
    refs = extract_references(file)  # all 4 reference types
    queue.extend(refs not in visited)
  write SCOPE.md
```

`extract_references(file)` detects:
1. Mermaid node labels containing `.md` paths
2. `/dh:skill-name` → resolves to `skills/skill-name/SKILL.md`
3. `subagent_type="dh:agent-name"` → resolves to `agents/agent-name.md`
4. Prose file references: `"Load X.md"`, `"Read references/workflows/Y"`

---

## Update Lifecycle

### Trigger: SessionStart staleness check (replaces post-commit hook)

**Decision (2026-06-19):** Post-commit git hooks are not the foundation. `hooks/hooks.json`
handles Claude Code lifecycle events only (SessionStart, PostToolUse, SubagentStop) — not git
commit events. Git `.git/hooks/` are not tracked across clones and require `claude -p` which
cannot use skills. SessionStart approach adopted instead.

At SessionStart the hook:
1. Read `meta.json` → `last_analyzed_commit`
2. `git diff {last_analyzed_commit} HEAD --name-only` → changed files
3. Filter: files in `SCOPE.md`
4. For each changed file in scope: run extraction workflow (skills available in-session)
5. When complete: update `meta.json` with current HEAD commit hash
6. Update `COVERAGE.md`

Optional later optimization: prek post-commit hook writes a pending-refresh marker (faster
detection on commit; SessionStart reads marker instead of diffing). Not required for correctness.

### Tier 1 — Assembler-only rebuild

```bash
uv run plugins/development-harness/docs/assemble_graph.py
```

### Tier 2 — Single file changed (normal case via SessionStart)

Staleness detected automatically at next SessionStart. No manual step required.

### Tier 3 — Scope changed (new skill or agent added)

1. Re-run `enumerate_scope.py` to update `SCOPE.md`
2. SessionStart picks up new file on next session

### Manual entry point

`/dh:meta-workflow-graph-refresh` — reads COVERAGE.md and SCOPE.md, identifies stale files,
delegates to the workflow. No process steps in the skill itself.

---

## Component Inventory

| Component | Status | Action |
|---|---|---|
| `plan_ensemble.py` | **⚠️ CORRECTED**: In `plugins/plugin-creator/skills/ensemble-rule-review/scripts/` — not DH | Contribute 2 changes upstream to plugin-creator (verify backward-compat first; fallback: thin DH wrapper) |
| `reduce.py` | **⚠️ CORRECTED**: In `plugins/plugin-creator/skills/ensemble-rule-review/scripts/` — not DH | Same — contribute changes upstream |
| `scripts/enumerate_scope.py` | Does not exist | Create |
| `scripts/merge_layer.py` | Does not exist | Create |
| `workflows/dh-extract-file.js` | Does not exist | Create |
| `workflow-extractor-worker.md` | **⚠️ CORRECTED**: Does not exist | Create new from scratch with 9 step-centric rule groups |
| `workflow-extractor-reducer.md` | **⚠️ CORRECTED**: Does not exist | Create new from scratch with active evidence check + miss log |
| `workflow-extractor.md` (orchestrator agent) | **⚠️ CORRECTED**: Does not exist — nothing to retire | Create workflow-extractor-worker and -reducer instead |
| `assemble_graph.py` | Exists, role unclear under new design | Likely legacy — role TBD at planning |
| `graph-schema.md` | Aspirational, diverged | Rewrite to match this PRD's data model |
| `extraction-rules.json` | 6 fork rules | Replace with 9 step-centric rules |
| `docs/workflow-layers/SCOPE.md` | Does not exist | Created by enumerate_scope.py |
| `COVERAGE.md` | Has model error | Fix haiku→sonnet for dh:workflow-extractor |
| `.claude/rules/workflow-extraction.md` | References wrong dispatch | Update |
| `meta-workflow-graph-refresh/SKILL.md` | Points to right docs | No change needed |
| `hooks/post-commit` | **⚠️ SUPERSEDED**: Post-commit hook not adopted | SessionStart staleness check used instead — see Update Lifecycle |

---

## Quality Feedback Loop

1. Sonnet verifier confirms a weight=1 finding → logged to `.tmp/extraction-misses/`
2. Periodically: review miss log, identify patterns haiku consistently misses
3. Add explicit detection pattern to the relevant rule group in `extraction-rules.json`
4. Re-extract affected files — verify miss rate drops on those files

This is the mechanism for iterative quality improvement without increasing per-run cost.

---

## Design Decisions (Resolved 2026-06-19)

All five design decisions resolved before implementation begins.

1. **Crawl + ensemble composition** → **Deterministic enumeration outer loop + full ensemble per file.**
   `enumerate_scope.py` performs the crawl (deterministic file-set computation via all four
   reference types). Per-file ensemble (haiku workers → reduce.py → sonnet verifier) runs
   against each file in SCOPE.md. Full ensemble retained to produce the verified fidelity that
   goal #1 requires. Group-6 workers also extract references, enabling self-correcting scope
   across cycles, with gap edges marking uncertainty.

2. **Storage architecture** → **DH-owned JSON as source of truth; optional one-way export to UA.**
   DH workflow layer JSON files in `docs/workflow-layers/*.json`. UA dashboard fed via optional
   export adapter if desired. DH self-knowledge must not depend on `~/repos/understand-anything`
   being present. Coupling to UA's schema rejected.

3. **Consumer interface** → **Query skill for agents; existing `dh-workflow-explorer.html` for humans.**
   New `/dh:workflow-query` skill for programmatic agent access (blast-radius queries, test
   generation, what-does-file-X-affect). Existing explorer reused for human visualization — it
   reads the decision-2 JSON and falls out cleanly. No session-start injection (token bloat,
   contradicts DH anti-instruction-bloat principle).

4. **`dh:interop` — no impact.** Confirmed: one-way adapter only, no connection to workflow graph.

5. **`reduce.py` change strategy** → **Contribute upstream to plugin-creator.**
   Both changes (slug-normalised heading keys, cross-group signal) are general corroboration
   improvements benefiting all ensemble consumers. Verify backward-compatibility before merging.
   Fallback if backward-compat breaks: thin DH wrapper; never fork.

---

## Open Implementation Decisions

1. **SessionStart staleness detection detail:** SessionStart hook reads `meta.json` vs HEAD.
   Optional: prek post-commit hook writes pending-refresh marker (faster detection) — verify
   prek supports `post-commit` hook type before adding. Not required for correctness.

2. **assemble_graph.py scope:** Step nodes require reading reference files during assembly
   (not just layer JSON). Decide whether to extend the existing assembler or replace it.
   The current assembler reads only JSON; step assembly also needs markdown parsing.

3. **Explorer HTML updates:** `dh-workflow-explorer.html` renders current node types. Step
   nodes, hook nodes, and new edge types require UI changes. Scoped separately.

4. **Existing L0–G8 data migration:** Decision-fork data is kept as enrichment. Where does
   it live in the new layer structure — same files with a `type: "enrichment"` flag, or a
   separate `enrichment/` directory?

5. **`-p` mode skills:** With SessionStart approach extraction runs in-session with full skill
   access. If any path later requires headless execution, `Skill()` calls are unavailable in
   `-p` mode — all agent dispatch must use `agentType` parameter instead.

---

## Success Criteria

1. Every step node in the graph has `verified: true` and a source citation that resolves to a
   real file, real heading, and real evidence quote in the current repo HEAD.
2. Re-extracting one source file does not alter step nodes from other source files in the
   same layer.
3. Running the extraction workflow twice with identical inputs produces identical layer JSON.
4. SessionStart staleness check fires when in-scope files have changed since `last_analyzed_commit`
   and extraction completes within the session without blocking work.
5. An AI agent can traverse the graph from any node and enumerate all downstream actors,
   MCP calls, and artifacts affected — with gap edges clearly marked as unverified.
6. COVERAGE.md accurately reflects what has been extracted, at what verification level, and
   when each file was last processed.
