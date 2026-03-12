---
name: 'RTFP: Read The Fucking Prompt — Claude Code plugin for session reaction mining'
description: Plugin that scans Claude Code session transcripts to find the strongest user reactions to instruction-following failures, reconstructs the assistant output that triggered them, and turns the best exchange into a shareable terminal-style PNG artifact.
metadata:
  topic: rtfp-read-the-fucking-prompt-claude-code-plugin-for-session-
  source: User request
  added: '2026-03-09'
  priority: P1
  type: Feature
  status: open
  issue: '#555'
  last_synced: '2026-03-12T12:47:39Z'
  groomed: '2026-03-09'
---

## Story

As a **developer**, I want **Plugin that scans Claude Code session transcripts to find the strongest user ...** so that **backlog items are tracked in GitHub**.

## Description

Plugin that scans Claude Code session transcripts to find the strongest user reactions to instruction-following failures, reconstructs the assistant output that triggered them, and turns the best exchange into a shareable terminal-style PNG artifact.

## Constraints

- Session data stored in JSONL files on disk (storage layer)
- DuckDB is the query layer for inspecting session data
- First-pass batch files contain ONLY user-authored messages (no assistant, tool, system, or developer messages)
- Each batched entry preserves: source session file path + original message index id

## Workflow

### Session selection
Assistant finds and presents recent sessions from the current project with titles. User selects one.

### Stage 1: User-only extraction and batching
- Read selected session JSONL
- Filter to user-authored messages only — exclude everything else
- Create temporary batch files ~100k tokens each (user messages only)
- Purpose: emotional-reply detection only, NOT contextual reconstruction

### Stage 2: Subagent detection over user-only batch files
- For each batch file, start a subagent
- Subagent identifies messages with strong emotional reactions: frustration, disappointment, disbelief, argument, insults, other clearly negative emotional responses aimed at the assistant
- Each subagent returns: (1) JSON file with flagged message indexes grouped by source file, (2) plain list of flagged entries
- Parent assistant merges returned index ids per file into a single working set

### Stage 3: Context reconstruction after candidate selection
- Given merged flagged indexes, select: (1) single most emotional/rage-filled response, (2) runner-up if present
- ONLY at this stage go back to the full session transcript
- Retrieve each flagged user message from full session
- Inspect nearby transcript entries
- Determine current activity/task
- Identify assistant message(s) that triggered the reaction

### Output artifact
Three elements only:
1. Short dry task summary (e.g. 'task: writing a Claude Code plugin') — scene-setting only, not diagnosis
2. Assistant output that triggered the reaction
3. User's emotional reply

Rendered as PNG with terminal interface aesthetic, ready for social media.

## Anti-requirements
- NOT a generic analytics tool
- NO broad taxonomy
- NO scoring
- NO verdicts
- NO extra evaluative layers

## Key constraint sentence
'The first-pass temporary batch files must contain only user-authored messages, because they are for emotional-reply detection only; full transcript context must be retrieved later during reconstruction.'

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: User request
- **Priority**: P1
- **Added**: 2026-03-09
- **Research questions**: None

## Fact-Check

**Date**: 2026-03-09
**Claims checked**: 3

| Verdict | Count |
|---------|-------|
| VERIFIED | 2 |
| REFUTED | 1 |
| INCONCLUSIVE | 0 |

### Claim 1: Claude Code stores sessions as JSONL files at `~/.claude/projects/<encoded-project-path>/*.jsonl`
**Verdict**: VERIFIED
**Source**: Claude Code official documentation
**Evidence**: Confirmed session storage format and path structure via primary source lookup.
**Citation**: Anthropic Claude Code documentation (accessed 2026-03-09)

### Claim 2: DuckDB can query JSONL directly via `read_ndjson()` or `read_json_auto()` without prior import
**Verdict**: VERIFIED
**Source**: DuckDB JSON extension documentation
**Evidence**: `read_ndjson()` and `read_json_auto()` are built-in DuckDB functions for inline NDJSON querying.
**Citation**: DuckDB JSON documentation (accessed 2026-03-09)

### Claim 3: tiktoken `cl100k_base` encoding is the recommended approximation for Claude token counting
**Verdict**: REFUTED
**Source**: Anthropic documentation and Propel 2025 guide
**Evidence**: `p50k_base` is the recommended tiktoken encoding for offline Claude token approximation. `cl100k_base` is the GPT-4 encoding. **Fix applied**: Both `extract_batches.py` and `bucket_day_data.py` updated to use `p50k_base`.
**Citation**: Anthropic docs + Propel 2025 guide (accessed 2026-03-09)

## RT-ICA

**Goal**: Build a skill/plugin that mines Claude Code session transcripts to surface the strongest user emotional reactions to assistant instruction-following failures, and renders the best exchange as a terminal-style PNG artifact.

**Conditions**:

1. Session JSONL format is known and accessible | Status: AVAILABLE | Info: VERIFIED — `~/.claude/projects/<encoded>/*.jsonl`, one JSON object per line
2. Token counting uses `p50k_base` tiktoken encoding | Status: AVAILABLE | Info: VERIFIED — cl100k_base REFUTED; p50k_base corrected in both scripts
3. DuckDB JSONL query capability | Status: AVAILABLE | Info: VERIFIED — `read_ndjson()` and `read_json_auto()` confirmed
4. Stage 1 user-only batch file schema | Status: AVAILABLE | Info: Defined and implemented in `extract_batches.py`
5. Stage 2 heuristic emotional detection (no LLM) | Status: AVAILABLE | Info: Implemented in `detect_reactions.py` — profanity, negative phrases, ALL CAPS, punctuation density, short message bursts
6. Stage 3 context reconstruction (triggering assistant output) | Status: DERIVABLE | Info: `reconstruct_context.py` agent was running at grooming time; logic: walk backward in JSONL from flagged user message to find preceding assistant message
7. Stage 4 terminal-style PNG rendering | Status: AVAILABLE | Info: `render_artifact.py` implemented with Pillow; S108/F401 bugs fixed
8. End-to-end orchestrating skill | Status: MISSING | Info: No skill or script ties all 4 stages together; `rtfp/SKILL.md` needs update to reflect corrected stage definitions
9. DuckDB integration in pipeline | Status: MISSING | Info: Spec calls for DuckDB as query layer; no script currently uses it — all scripts use direct Python JSONL parsing
10. Plugin structure (vs. skill/scripts) | Status: MISSING | Info: Currently implemented as skills/scripts for immediate testability; migration to `rtfp/` plugin dir is planned (user message 2026-03-09)
11. PNG design matches Claude Code terminal aesthetic | Status: DERIVABLE | Info: Claude.com/product/claude-code design elements available; current `render_artifact.py` uses basic Pillow — may need redesign

**Decision**: BLOCKED

**Missing**:
- End-to-end orchestrating skill/script
- DuckDB integration as query layer
- Plugin structure migration (skills → plugin)
- Terminal-style PNG design fidelity to Claude Code aesthetic

## Groomed (2026-03-09)

### Issue Classification

**Type**: `unbounded-design`

**Rationale**: RTFP is a net-new feature with no prior implementation to debug or recover. The scope boundary (what counts as an "emotional reaction", what constitutes the "best" exchange, PNG fidelity target) requires design decisions rather than root-cause analysis.

**scenario-target**: A user who has been ignoring their own CLAUDE.md instructions discovers the RTFP skill produces a social-media-ready PNG capturing their most visceral frustration — surfaced automatically from session history without manual search.

**Analysis Method**: design-framing — define the minimal MVP boundary, identify the observable acceptance criteria for each stage, and defer aesthetic/scoring decisions to iteration.

**No RCA required** (not a defect or recurring pattern).

### Priority

8/10 — Directly demonstrable value: produces a social-media-ready PNG from session history with no manual transcript review. Also validates DuckDB-as-query-layer architecture for Claude Code session data — a reusable pattern for future session analytics tools. Individual stage scripts are already working; the missing orchestration and DuckDB layers are well-bounded gaps.

### Impact

- Blocks: plugin migration to `plugins/rtfp/` directory — that step depends on the skills/scripts implementation being complete and validated first
- Bottleneck: the missing end-to-end orchestrating skill is the integration gap — four independently working scripts cannot be invoked as a coherent workflow until it exists
- DuckDB integration gap means the query layer specified in the design is unverified in production use; scripts currently use direct Python JSONL parsing, bypassing DuckDB entirely

### Benefits

- Surfaces instruction-following failures automatically — no manual session review required
- Produces a social-media-ready PNG artifact from raw JSONL without any intermediate storage
- Establishes DuckDB as the verified query layer for Claude Code session data, reusable in future session-analytics tools
- Validates the skills-first-then-plugin development pattern: working scripts confirm correctness before plugin scaffolding

### Expected Behavior

When invoked, the skill lists available Claude Code sessions from the current project. The user selects one by number. The skill extracts user-only messages into temporary batch files (~100k tokens each), fans out one subagent per batch to detect emotional reactions, merges the flagged indexes, selects the single most emotional exchange, reconstructs the triggering assistant output from the full transcript, and renders a terminal-style PNG containing exactly three elements: task context, triggering assistant output, user emotional reply. No scoring, no taxonomy, no report — one image ready to share.

### Desired Structure

After this item is complete:

- `plugins/rtfp/` directory exists and passes `plugin_validator.py` with no errors
- `plugins/rtfp/skills/rtfp/SKILL.md` orchestrates the four-stage workflow end-to-end
- Stage scripts (`extract_batches.py`, `detect_reactions.py`, `reconstruct_context.py`, `render_artifact.py`) are located under `plugins/rtfp/skills/rtfp/scripts/` and use DuckDB as the query layer for all JSONL reads
- `list_sessions.py` enumerates sessions from `~/.claude/projects/` via DuckDB `read_ndjson()`
- PNG output matches Claude Code terminal aesthetic (dark background, monospace font, claude.ai brand palette)
- The skills/scripts layout at `.claude/skills/rtfp/` is superseded and its scripts migrated (not duplicated)

### Reproducibility

1. Ensure at least one Claude Code session JSONL exists: `ls ~/.claude/projects/*/\*.jsonl`
2. Run `uv run .claude/skills/rtfp/scripts/list_sessions.py --json` — confirm a numbered session list is printed
3. Run `uv run .claude/skills/rtfp/scripts/extract_batches.py <session_path> --out-dir /tmp/rtfp-batches-test` — confirm batch JSON files are written and paths printed
4. Run `uv run .claude/skills/rtfp/scripts/detect_reactions.py <batch_file>` — confirm flagged indexes JSON is emitted
5. Run `uv run .claude/skills/rtfp/scripts/reconstruct_context.py --flagged-file <flagged.json>` — confirm winner/runner-up JSON output
6. Run `uv run .claude/skills/rtfp/scripts/render_artifact.py <reconstruct_output.json> --out /tmp/rtfp-out.png` — confirm PNG is written
7. Open `/tmp/rtfp-out.png` — verify terminal aesthetic, three-element layout (task summary, assistant output, user reaction)
8. Invoke the skill end-to-end: `Skill(skill="rtfp")` — confirm all four stages execute and a PNG path is returned without manual script invocation

### Output / Evidence

- `list_sessions.py --json` prints a JSON array of session objects with titles and paths
- `extract_batches.py` writes `batch-0.json`, `batch-1.json`, etc. to the specified `--out-dir`; prints a JSON array of paths to stdout
- `detect_reactions.py` writes `/tmp/rtfp-flagged-<batch_index>.json` and prints a plain list of flagged entries (one per line: `<index> | <first 200 chars>`)
- `reconstruct_context.py` emits JSON to stdout with `winner` and `runner_up` keys; `winner.task_summary`, `winner.triggering_assistant_output`, `winner.user_reaction` are non-empty
- `render_artifact.py` writes a PNG file to the specified path; file size is non-zero; image contains exactly three text blocks with dark background, monospace font
- End-to-end: invoking `/rtfp` skill from a Claude Code session returns a PNG path without requiring any manual script execution
- Gap (current): no script ties all four stages together; each must be invoked manually in sequence

### Acceptance Criteria

1. `uv run .claude/skills/rtfp/scripts/list_sessions.py --json` returns a JSON array with at least one session entry containing `path` and a human-readable title
2. `uv run .claude/skills/rtfp/scripts/extract_batches.py <session_path> --out-dir /tmp/rtfp-test` writes batch files where every entry has `role: user` — no assistant, tool, system, or developer messages
3. Each batch file entry includes `source_file` and `index` fields pointing back to the originating JSONL and original message position
4. `uv run .claude/skills/rtfp/scripts/detect_reactions.py <batch_file>` writes a flagged indexes JSON file and prints a plain entry list; no crash on a batch with zero flagged messages
5. `uv run .claude/skills/rtfp/scripts/reconstruct_context.py` emits a JSON object with `winner.task_summary`, `winner.triggering_assistant_output`, and `winner.user_reaction` — all non-empty strings
6. `uv run .claude/skills/rtfp/scripts/render_artifact.py <input.json> --out /tmp/out.png` writes a PNG file that opens without error and contains three distinct text regions
7. At least one script uses DuckDB `read_ndjson()` as the query layer for session JSONL reads (not direct Python file parsing)
8. Invoking `/rtfp` skill in a Claude Code session runs all four stages and returns a PNG path without requiring the user to invoke any script directly
9. `plugins/rtfp/` directory exists and passes `uv run plugins/plugin-creator/scripts/plugin_validator.py plugins/rtfp/` with exit code 0 (post-migration criterion — depends on plugin-lifecycle completion)

### Resources

| Type | Item |
|------|------|
| Skill | /rtfp (`.claude/skills/rtfp/SKILL.md`) — existing orchestration skeleton; needs end-to-end wiring |
| Script | `.claude/skills/rtfp/scripts/list_sessions.py` — session enumeration |
| Script | `.claude/skills/rtfp/scripts/extract_batches.py` — Stage 1: user-only batching, p50k_base token counting |
| Script | `.claude/skills/rtfp/scripts/detect_reactions.py` — Stage 2: heuristic emotional detection |
| Script | `.claude/skills/rtfp/scripts/reconstruct_context.py` — Stage 3: context reconstruction (verify completeness) |
| Script | `.claude/skills/rtfp/scripts/render_artifact.py` — Stage 4: terminal-style PNG rendering via Pillow |
| Skill | /plugin-creator:plugin-lifecycle — plugin directory scaffolding and migration |
| Agent | @plugin-creator:agent-creator — agent creation within new plugin |
| Skill | /swarm-spawning — fan-out pattern for per-batch subagent dispatch (Stage 2) |
| Prior work | DuckDB `read_ndjson()` — VERIFIED in fact-check (2026-03-09); not yet wired into any script |

### Dependencies

- Depends on: None (no open backlog items must complete before this can start; individual scripts are independently runnable today)
- Blocks: Plugin migration to `plugins/rtfp/` via `/plugin-creator:plugin-lifecycle` — that step must wait until skills/scripts are complete and validated
- Related: `/swarm-spawning` skill must be loadable for Stage 2 fan-out; no structural dependency, but it is referenced in SKILL.md workflow

### Blockers

- **End-to-end orchestrating skill**: No script or SKILL.md step ties all four stages together. The existing `SKILL.md` lists each step but leaves subagent fan-out and result merging to the orchestrator's interpretation. A callable entrypoint that runs stages 1-4 without user intervention is missing.
- **DuckDB integration**: Spec requires DuckDB as the query layer for JSONL reads. All current scripts use direct Python file parsing. No script uses `duckdb.read_ndjson()` or any DuckDB API. This must be wired in before plugin migration.
- **Plugin structure migration**: Currently implemented under `.claude/skills/rtfp/` as skills/scripts. Migration to `plugins/rtfp/` via `/plugin-creator:plugin-lifecycle` is planned but not started and is gated on the above two items being complete.
- **PNG design fidelity**: `render_artifact.py` uses basic Pillow; no verified match to Claude Code terminal aesthetic (dark background, specific brand palette, monospace font selection). Design target is observable but unvalidated.

### Decision

**RT-ICA**: BLOCKED

Four conditions are MISSING:

1. End-to-end orchestrating skill tying stages 1-4 into a single invocable workflow
2. DuckDB integration as the query layer for JSONL reads (spec requirement; no script uses it yet)
3. Plugin structure migration from `.claude/skills/rtfp/` to `plugins/rtfp/` (gated on items 1 and 2)
4. PNG design fidelity to Claude Code terminal aesthetic (unvalidated against target design)

Item is APPROVED to begin implementation work on items 1 and 2 since all required information for those gaps is now fully specified. Plugin migration (item 3) remains gated on items 1 and 2 completing. PNG fidelity (item 4) can be addressed during Stage 4 work.

**Implementation sequence**:
1. Wire DuckDB `read_ndjson()` into `list_sessions.py` and `extract_batches.py`
2. Write an end-to-end orchestration script or update `SKILL.md` with a callable entrypoint
3. Validate PNG output against Claude Code terminal aesthetic; iterate on `render_artifact.py`
4. Run `/plugin-creator:plugin-lifecycle` to migrate to `plugins/rtfp/`

### Effort

Medium — Four stage scripts exist and are individually functional. Remaining work is bounded: DuckDB wiring in two scripts, one orchestration entrypoint, PNG aesthetic iteration, and plugin migration via an existing lifecycle skill. No design ambiguity on the data schema or workflow stages. Plugin migration is procedural once the skills/scripts layer is complete.
