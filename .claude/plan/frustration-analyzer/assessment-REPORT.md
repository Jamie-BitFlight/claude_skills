# Assessment Report: frustration-analyzer → RTFP Redesign

Date: 2026-03-09
Plugin path: plugins/frustration-analyzer
Validator: exit 0, warnings PD002 (no examples/) and PD003 (no scripts/)
Assessment type: Design delta — existing plugin vs new RTFP spec

---

## Current Plugin Design Map

### Components

| Component | File | Purpose |
|-----------|------|---------|
| MCP server | `mcp/server.py` | DuckDB+JSONL tools: scan_transcripts, list_insults, top_insults, get_scenario, generate_social_post |
| Agent | `agents/frustration-analyst.md` | Insult classification workflow with 9-category taxonomy |
| Skill | `skills/frustration-analysis/SKILL.md` | User-facing workflow guide + allowed-tools declaration |
| Reference | `skills/frustration-analysis/references/insult-categories.md` | Category definitions and example phrases |

### Current Workflow

```text
User → scan corpus-wide (~/.claude/projects/**/*.jsonl)
     → classify every user message against 9 insult categories
     → index matches (severity/creativity/humor/accuracy 1-5)
     → list_insults / top_insults / get_scenario
     → generate_social_post (raw text + hashtags)
```

### What Works (Keep)

- DuckDB `read_ndjson_auto()` over JSONL files — correct architecture
- `scan_transcripts` paginated extraction with context window
- `get_scenario` file+line_index lookup
- `generate_social_post` raw output + privacy_reminder
- FastMCP server structure
- `_resolve_glob()` and `_extract_user_text_from_value()` helpers
- Agent uses `model: opus` and `skills: frustration-analysis`

### What Must Change (Gap vs RTFP Spec)

---

## RTFP Target Spec

**Concept**: Read The Fucking Prompt — a plugin that finds the single strongest user reaction to an instruction-following failure, reconstructs the triggering assistant output, and renders the exchange as a terminal-style PNG ready for social media.

**Key constraints from spec:**
- Session-specific (user chooses one session, not corpus-wide)
- User-only extraction in batch stage (no assistant messages in batch files)
- 3-stage pipeline with subagents
- No taxonomy, no scoring, no verdicts, no analytics
- Final output = PNG terminal artifact

---

## Gap Analysis: Current vs RTFP

### Workflow Gap

| Stage | Current | RTFP Target |
|-------|---------|-------------|
| Entry | Corpus-wide glob | User selects from list of recent project sessions |
| Stage 1 | `scan_transcripts` (includes context) | Extract user-only messages → batch files (~100k tokens each) |
| Stage 2 | Single agent classifies all | One subagent per batch → returns flagged indexes JSON |
| Stage 3 | `get_scenario` on demand | Merge indexes → reconstruction agent picks winner + reads full transcript |
| Output | Text social post | PNG terminal-style artifact |

### MCP Tool Gap

| Current Tool | RTFP Replacement |
|---|---|
| `scan_transcripts` | `list_sessions` (show recent sessions for project) + `extract_user_messages` (user-only, no context) |
| `list_insults` | Remove — no persistent insult index |
| `top_insults` | Remove — no scoring |
| `get_scenario` | `get_context_window` (given file + line_index → returns N messages before+after including assistant) |
| `generate_social_post` | `render_rage_receipt` (given task_summary + assistant_excerpt + user_reply → returns PNG bytes or path) |

### Agent Gap

Current `frustration-analyst` agent:
- Has 9-category insult taxonomy → **delete**
- Has scoring dimensions → **delete**
- Has `index_insults` (batch) call → **remove** (tool doesn't exist in server.py anyway — stale ref)
- Has corpus-wide scan workflow → **replace**

RTFP needs:
1. **Orchestrator skill** — presents session list, triggers Stage 1, spawns Stage 2 subagents, triggers Stage 3
2. **Detector subagent** — reads user-only batch file, returns flagged indexes + plain list
3. **Reconstruction agent** — reads merged index, picks winner/runner-up, reads full transcript context, produces task_summary + assistant_excerpt + user_reply
4. **Renderer** — takes the 3-field artifact, produces terminal-style PNG

### Schema Gap

Current fields per insult: `file, line_index, text, category, severity, creativity, humor, accuracy, had_prior_correction, matched_text, reasoning`

RTFP incident fields (minimal):
```json
{
  "file": "path/to/session.jsonl",
  "user_line_index": 42,
  "task_summary": "writing a Claude Code plugin",
  "assistant_excerpt": "Here is a bulleted list of...",
  "user_reply": "I said no bullets. How are you still doing bullets.",
  "runner_up": { "user_line_index": 17, ... }
}
```

### Output Gap

Current: Text social post via `generate_social_post` MCP tool.

RTFP: PNG rendered to look like a terminal window. Content:
```
┌─ RTFP ──────────────────────────────────────┐
│ task: writing a Claude Code plugin           │
│                                              │
│ assistant:                                   │
│   Here is a bulleted list of...              │
│                                              │
│ user:                                        │
│   I said no bullets. How are you still       │
│   doing bullets.                             │
└──────────────────────────────────────────────┘
```

---

## Stale Reference Bugs (Fix Required)

1. `SKILL.md` line 22: calls `mcp__frustration-analyzer__index_insult(...)` — tool does not exist in server.py
2. `SKILL.md` line 40: `DuckDB is not involved at this stage` — incorrect, DuckDB IS involved in scan
3. `agents/frustration-analyst.md` line 26: calls `index_insults` (batch) — tool does not exist
4. `README.md`: says "8 insult categories" but server and SKILL define 9
5. `plugin.json` description still says "sanitized social media content" — outdated

---

## Refactoring Tasks

### Task 1: Replace MCP server tools

Replace current tools with RTFP-oriented tools:

- `list_sessions(project_path)` → returns recent sessions with titles/timestamps
- `extract_user_messages(file, output_path)` → writes user-only batch JSONL (no context, no assistant messages)
- `get_context_window(file, line_index, context_window=10)` → returns preceding + following turns from full transcript
- `render_rage_receipt(task_summary, assistant_excerpt, user_reply, output_path)` → renders PNG

Remove: `list_insults`, `top_insults` (scoring/taxonomy tools)
Keep (modified): `scan_transcripts` (rename to `extract_user_messages`), `get_scenario` (rename to `get_context_window`), `generate_social_post` (replace with `render_rage_receipt`)

### Task 2: Create RTFP orchestrator skill

New `skills/rtfp/SKILL.md`:
- `user-invocable: true`
- `disable-model-invocation: true` (user-triggered only)
- Workflow: session list → user selects → Stage 1 extract → Stage 2 detect (parallel subagents) → Stage 3 reconstruct → render PNG

### Task 3: Create detector subagent

New `agents/batch-detector.md`:
- Reads one user-only batch file
- Identifies emotional reactions (frustration, disbelief, argument, insults)
- Returns: `{ "flags": [{"file": "...", "line_index": N, "text": "..."}], "source_batch": "..." }`
- No taxonomy, no scoring

### Task 4: Create reconstruction agent

New `agents/context-reconstructor.md`:
- Receives merged flagged indexes
- Picks winner (most emotional/specific) + optional runner-up
- Reads full transcript context for each via `get_context_window`
- Outputs: task_summary + assistant_excerpt + user_reply (3 fields only)

### Task 5: Add PNG render capability

Add `pillow` to server.py dependencies.
Implement `render_rage_receipt` tool in server.py.
Terminal-style layout: dark background, monospace font, bordered card.

### Task 6: Update agent, skill, README, plugin.json

- Replace `agents/frustration-analyst.md` with orchestration-aware agent
- Replace `skills/frustration-analysis/SKILL.md` with RTFP skill
- Rewrite `README.md` for RTFP
- Update `plugin.json` description and keywords
- Remove `skills/frustration-analysis/references/insult-categories.md` (taxonomy gone)

---

## Priority Order

1. Task 1 — MCP server (new tools, remove scoring tools)
2. Task 5 — PNG render (depends on server being updated)
3. Task 3 — Detector subagent
4. Task 4 — Reconstruction agent
5. Task 2 — RTFP orchestrator skill
6. Task 6 — Docs and metadata cleanup

---

## Validator Notes

Current score: PASS (exit 0), warnings only:
- PD002: No examples/ directory
- PD003: No scripts/ directory

Post-refactor: `mcp/server.py` scripts dir should be added; examples not needed for this plugin type.
