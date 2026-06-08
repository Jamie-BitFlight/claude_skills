# DH Workflow Map — Coverage Manifest

The authoritative index of what has been collected, where it lives, and what is still a
gap. Consult this FIRST when asked any question about the workflow map. A question maps to
a layer: if COLLECTED, query its data; if a GAP, it is a named pending pass — never restart.

All files live in `plugins/development-harness/docs/workflow-layers/`.

Resolution: **medium-high**. Skeleton + connections + 8 annotation layers collected and
spot-checked. Graph/explorer not yet rebuilt from this data.

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
| Graph/explorer rebuild from L0+L1+G1-G8 | PENDING |
| Phases 3–6 in dh-system-model.html | PENDING |
| SAM backend routing (sam_plan/sam_task per-backend) | PENDING |
| Agent-file identity layer (model, tools, skills-loaded, STATUS contract) | PENDING |
| backlog #2619 — issue type routing downstream | LOGGED, needs groom |
| backlog #2620 — autonomy_mode setter | LOGGED, needs groom |

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
- Phase A/B/C/D collection protocol using `dh:workflow-extractor` (haiku, Read/Grep/Glob/Write/Edit/Bash)

## Source provenance

Every L0 fork carries `source_file` + `source_block`. Every L1 trace carries `source_file`.
G1-G8 entries carry `source_file` per item. The skeleton is faithful to the source's own
Mermaid graph structure — not an imposed schema.
