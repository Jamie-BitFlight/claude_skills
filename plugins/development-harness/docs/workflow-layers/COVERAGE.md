# DH Workflow Map — Coverage Manifest

The authoritative index of what has been collected, where it lives, and what is still a
gap. Consult this FIRST when asked any question about the workflow map. A question maps to
a layer: if COLLECTED, query its data; if a GAP, it is a named pending pass — never restart.

All files live in `plugins/development-harness/docs/workflow-layers/`.

Resolution: **medium-high**. Skeleton + connections + 8 annotation layers collected and
spot-checked. Graph rebuilt from layer data (224 nodes, 411 edges). Explorer renders all 6 overlays.

---

## Collected layers

| Layer | What it captures | File | Status | Verification |
|---|---|---|---|---|
| L0 — forks | Every forking decision across 5 lifecycle skills: diamond/prose condition, branches, `evaluated_by`, file-ref expansion links | `L0-forks.json` | COLLECTED | 111 forks, 5 skills, 23 file-ref links. Spot-checked verbatim. 103 orchestrator / 5 parser / 3 agent |
| L1 — traces | Each fork branch followed to terminal; cross-file/skill connections; loop-backs | `L1-trace-*.json` (4 files) | COLLECTED | 273 traces, 105 cross-file connections, 0 UNRESOLVED. 3 skill-handoffs falsified against source |
| G1 — failure modes | Every failure point per skill + where each bounces to | `G1-failure-modes.json` | COLLECTED | 48 failure modes: 29 pure STOP, 9 bounce, 5 escalate, 5 create_backlog_item |
| G2 — artifacts | Full artifact set per step + producer/consumer/storage | `G2-artifacts.json` | COLLECTED | 14 artifacts, 0 orphan consumers |
| G3 — actor types | Per-action: orchestrator-raw / agent-structured-task / agent-raw-prompt | `G3-actor-types.json` | COLLECTED | 68 actions: 51 orchestrator-raw, 12 agent-raw-prompt, 5 agent-structured-task |
| G4 — concurrency | Dispatch topology: TeamCreate vs Agent, waves, barriers, siblings | `G4-concurrency.json` | COLLECTED | 15 dispatch points, 5 conditional dispatches |
| G5 — optionality | Per-step: mandatory / conditional / skippable-by-flag | `G5-optionality.json` | COLLECTED | 49 steps: 8 mandatory, 30 conditional, 11 skippable-by-flag |
| G6 — task types | Which paths apply per issue type + --quick/--auto variants | `G6-task-types.json` | COLLECTED | 7 types. Key finding: classifier output does not route downstream of grooming |
| G7 — complexity routing | Each orchestrator decision signal: enforced vs designed-only | `G7-complexity-routing.json` | COLLECTED | 8 signals: 3 enforced, 1 designed-only, 4 partially-enforced |
| G8 — backend routing | Per MCP tool call: which backend protocol method + per-backend behavior | `G8-backend-routing.json` | COLLECTED | 55 calls mapped; SAM tools marked pending |

---

## Key findings from collected layers (optimization-relevant)

**G6 — Issue type does not route downstream** (backlog #2619): The classifier's five types
only change behavior within grooming. No source attests that add-new-feature,
implement-feature, or complete-implementation branch by type.

**G7 — `autonomy_mode` consumed but never set** (backlog #2620): implement-feature fully
enforces the field; nothing sets it from item signals. Defaults silently to `full_auto`.

**G7 — complexity-fit formula is designed-only**: Zero grep hits in any skill file. Lives
only in `docs/complexity-fit-and-economics-of-agents.md`.

**G7 — ARL human touchpoints are partially enforced**: Documented in design files; no
skill flowchart reads escalation criteria to trigger them.

**G5 — Only 8 mandatory steps across all 5 skills**: Everything else is conditional or
flag-skippable. `--quick` is the largest single shortcut.

**G3 — 5 structured-task dispatches vs 12 raw-prompt dispatches**: Raw-prompt pattern
means the orchestrator writes instructions inline — fragile to prompt drift.

---

## Remaining gaps

| Gap | Status |
|---|---|
| Graph/explorer rebuild from L0+L1+G1-G8 | COMPLETE — `assemble_graph.py` + `dh-workflow-graph.json` |
| Phases 3–6 in dh-system-model.html | PENDING |
| SAM backend routing (sam_plan/sam_task per-backend) | PENDING |
| Agent-file identity layer (model, tools, skills-loaded, STATUS contract) | PENDING |
| routes_to edge type — no instances (L1 terminal_targets are intra-skill headings, not cross-skill) | PENDING |
| 5 skill nodes have unverified source_file (skill names not in SKILL_FILE_MAP in assemble_graph.py) | PENDING |
| backlog #2619 — issue type routing downstream | LOGGED, needs groom |
| backlog #2620 — autonomy_mode setter | LOGGED, needs groom |

---

## Update process

Two tiers depending on what changed.

### Tier 1 — Only the assembler output needs refreshing (layer data unchanged)

Run from repo root:

```bash
uv run plugins/development-harness/docs/assemble_graph.py
```

That rebuilds `dh-workflow-graph.json` and updates the embedded data in
`dh-workflow-explorer.html`. Use when you've edited `assemble_graph.py` itself,
or when you want a clean rebuild without changing source data.

### Tier 2 — Source skill/agent files changed (SKILL.md, reference files, hooks.json)

The layer JSON files are the source of truth for the assembler. They must be
re-extracted before re-assembling.

1. **Identify which layers are affected** by the change:

   | Change type | Layers to re-extract |
   |---|---|
   | Mermaid forks added/changed in a SKILL.md | L0, L1 for that skill |
   | New agent dispatched or dispatch changed | G4 |
   | Artifact produced/consumed changed | G2 |
   | MCP tool call changed | G8 |
   | New failure mode | G1 |
   | Optionality changed (--quick, --auto) | G5, G6 |

2. **Re-extract the affected layer.** The single-agent `dh:workflow-extractor` has been
   retired; re-extraction is pending redesign (see the PRD at
   `../plans/prd-workflow-extractor.md`). See `../workflow-trace-methodology.md` for
   the extraction protocol and field definitions per layer type.

3. **Run the assembler** (Tier 1 step above).

### What NOT to do

- Do not edit the layer JSON files by hand — extract from source and let the
  assembler build the graph.
- Do not edit `dh-workflow-graph.json` directly — it is an assembler output.
- Do not restart collection from scratch unless more than 3 layers are affected.
  The follow-up protocol below applies to targeted gaps.

---

## Follow-up protocol

```
Question asked
  → match to a layer in this manifest
  → COLLECTED  : query that layer's JSON file, answer with citations
  → GAP        : name the pending pass + its unit; scope and cost it
  → NEVER      : restart the whole collection from scratch
```

## Collection methodology

See `../workflow-trace-methodology.md` for the full methodology:
- Schema must come AFTER data collection, not before
- The graph-of-graphs structure (Mermaid nodes expand to referenced files)
- Two-hop dispatch resolution (orchestrator → task-worker → profile_load → specialist)
- Phase A/B/C/D collection protocol (single-agent `dh:workflow-extractor` retired; pending redesign — see `../plans/prd-workflow-extractor.md`)

## Source provenance

Every L0 fork carries `source_file` + `source_block`. Every L1 trace carries `source_file`.
G1-G8 entries carry `source_file` per item. The skeleton is faithful to the source's own
Mermaid graph structure — not an imposed schema.
