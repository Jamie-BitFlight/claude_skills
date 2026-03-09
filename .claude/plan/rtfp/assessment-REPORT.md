# Plugin Assessment Report: rtfp

**Date**: 2026-03-09
**Current Path**: `.claude/skills/rtfp/`
**Target Path**: `plugins/rtfp/`

## Executive Summary

- **Overall Score**: 62/100
- **Marketplace Ready**: No (pre-plugin structure)
- **Critical Issues**: 3
- **Warnings**: 5
- **Recommendations**: 9
- **Migration Complexity**: Medium

### Key Findings

1. SKILL.md is well-structured with a clear 7-step workflow, but the skill delegates heavily to subagents (Steps 3, 5) while the scripts only cover the non-LLM pipeline stages -- this split is undocumented in any architecture reference
2. No `plugins/rtfp/` directory exists yet -- full plugin scaffolding needed (`.claude-plugin/plugin.json`, `agents/`, `README.md`)
3. The SKILL.md workflow references scripts by hardcoded `.claude/skills/rtfp/scripts/` paths which will break after plugin migration to `plugins/rtfp/skills/rtfp/scripts/`
4. `reconstruct_context.py` is referenced nowhere in SKILL.md -- Steps 4-5 describe subagent work that duplicates this script's functionality

## Current Structure Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `SKILL.md` | 124 | Skill definition: 7-step RTFP workflow |
| `scripts/list_sessions.py` | 248 | Stage 1: List Claude Code sessions for project |
| `scripts/extract_batches.py` | 285 | Stage 2: Extract and batch user messages from JSONL |
| `scripts/detect_reactions.py` | 338 | Stage 2 (detection): Heuristic emotional reaction detection |
| `scripts/reconstruct_context.py` | 655 | Stage 3: Context reconstruction and winner selection |
| `scripts/render_artifact.py` | 480 | Stage 4: PNG rendering with terminal-style dark theme |

**Total**: 2,130 lines across 6 files. No `references/` directory. No agents. No hooks configuration. No tests.

### Pipeline Architecture

```text
Step 1: list_sessions.py         -- Script (user selects session)
Step 2: extract_batches.py       -- Script (produces batch files)
Step 3: Fan-out scan             -- Subagent per batch (LLM-based detection)
Step 4: Merge flagged indexes    -- Orchestrator logic (no script)
Step 5: Pick the winner          -- Subagent (LLM-based selection)
Step 6: render_artifact.py       -- Script (PNG output)
Step 7: Report                   -- Orchestrator output
```

**Orphaned script**: `detect_reactions.py` implements heuristic detection (Stage 2 per its docstring) but SKILL.md Step 3 delegates detection to subagents instead. `reconstruct_context.py` implements context reconstruction and winner selection (Stage 3 per its docstring) but SKILL.md Steps 4-5 delegate this to subagents. These scripts appear to be alternative implementations that the SKILL.md workflow does not invoke.

## SKILL.md Quality Analysis

### Frontmatter Assessment

| Field | Present | Valid | Value |
|-------|---------|-------|-------|
| `name` | Yes | Yes | `rtfp` |
| `description` | Yes | Yes | 330 chars, single-line (no multiline bug) |
| `argument-hint` | No | -- | Missing -- should hint `[session-id]` |
| `allowed-tools` | No | -- | Missing -- skill needs Read, Bash, Agent, Glob |
| `user-invocable` | No (default true) | Yes | Correct default for user-triggered skill |
| `model` | No | -- | OK, inherits |
| `context` | No | -- | OK, runs in main context (needs Agent tool for subagent delegation) |
| `disable-model-invocation` | No | -- | Should be `true` -- this skill has side effects (writes PNG, creates temp files) and should only fire when user explicitly requests it |

### Description Quality: 7/10

**Strengths**:
- Action verbs: "Scan", "find", "reconstruct", "render"
- Clear trigger phrases: "rtfp", "read the fucking prompt", "find my worst AI moment", "make a rage screenshot"
- Specific output description: "terminal-style PNG artifact"

**Gaps**:
- No mention of "session analysis" or "conversation review" -- broader trigger keywords missing
- No mention of "frustration", "rage", "emotional" as standalone triggers
- Missing: "share", "screenshot", "meme" as trigger keywords

### Content Structure: 8/10

**Strengths**:
- Clear numbered steps with exact CLI invocations
- Explicit constraints section ("Non-Negotiable") preventing scope creep
- Output format documented at Step 7
- Progressive workflow -- each step depends on prior output

**Gaps**:
- No `references/` directory for progressive disclosure -- all content is in SKILL.md (124 lines, ~4,800 chars, well within token budget)
- Subagent prompt templates are inline in SKILL.md (Steps 3, 5) -- these could be extracted to reference files for maintainability
- No error handling guidance (what if no reactions found, what if session is empty)

### Token Budget

At 124 lines / ~4,800 characters, this SKILL.md is well within the recommended limits. No SK006 or SK007 concerns.

## Scripts Audit

### `list_sessions.py` (Stage 1) -- Referenced in SKILL.md Step 1

- **PEP 723 shebang**: Correct (`#!/usr/bin/env -S uv --quiet run --active --script`)
- **Dependencies**: None (stdlib only)
- **Purpose**: Discovers JSONL session files under `~/.claude/projects/`, outputs JSON metadata
- **Quality**: Well-structured with proper argparse, error handling, progress reporting to stderr
- **Issue**: `_TITLE_MAX_LEN = 80` truncation constant -- violates "No Invented Limits" repo policy. The consumer should control truncation, not the script.

### `extract_batches.py` (Stage 2) -- Referenced in SKILL.md Step 2

- **PEP 723 shebang**: Correct
- **Dependencies**: `tiktoken>=0.7.0`
- **Purpose**: Extracts user-authored messages from JSONL, splits into token-bounded batch files
- **Quality**: Clean implementation with proper batching logic
- **Issue**: Help text says "tiktoken cl100k_base" but code uses `p50k_base` encoding -- documentation/code mismatch at line 54 vs line 254
- **Issue**: `_DEFAULT_OUT_DIR` uses `tempfile.gettempdir()` -- non-deterministic across platforms

### `detect_reactions.py` (Stage 2 detection) -- NOT referenced in SKILL.md

- **PEP 723 shebang**: Correct
- **Dependencies**: None (stdlib only)
- **Purpose**: Heuristic-based emotional reaction detection using regex patterns and signal scoring
- **Quality**: Well-designed signal detection with configurable thresholds, benign acronym exclusion
- **Status**: ORPHANED -- SKILL.md Step 3 uses subagent-based LLM detection instead of this script. This script is either a pre-LLM fallback or an alternative implementation that was superseded.

### `reconstruct_context.py` (Stage 3) -- NOT referenced in SKILL.md

- **PEP 723 shebang**: Correct
- **Dependencies**: None (stdlib only)
- **Purpose**: Full pipeline for context reconstruction, task inference, candidate scoring, and winner selection
- **Quality**: Most sophisticated script (655 lines). Implements task summary inference from file extensions, signal density scoring with profanity/caps/punctuation weighting, and runner-up selection.
- **Status**: ORPHANED -- SKILL.md Steps 4-5 delegate this to subagents. This script implements the same logic deterministically (no LLM calls). Contains duplicated constants with `detect_reactions.py` (acronym lists, punctuation patterns).
- **Notable**: This script produces the exact JSON format (`task_summary`, `triggering_assistant_output`, `user_reaction`) that `render_artifact.py` consumes.

### `render_artifact.py` (Stage 4) -- Referenced in SKILL.md Step 6

- **PEP 723 shebang**: Correct
- **Dependencies**: `pillow>=10.0.0`
- **Purpose**: Renders terminal-style dark PNG with macOS window chrome
- **Quality**: Production-quality rendering with font fallback chains, text wrapping, rounded corners
- **Issue**: SKILL.md Step 6 invokes with positional arg (`render_artifact.py /tmp/rtfp-result.json --out rtfp_artifact.png`) but the script expects `--input-file` flag -- the invocation in SKILL.md will fail
- **Issue**: SKILL.md Step 5 writes `task`/`assistant`/`user` keys but `render_artifact.py` reads `task_summary`/`triggering_assistant_output`/`user_reaction` keys -- JSON field name mismatch between SKILL.md subagent instructions and script expectations

## Plugin Migration Gap Analysis

### Missing Components

| Component | Status | Required Action |
|-----------|--------|-----------------|
| `plugins/rtfp/.claude-plugin/plugin.json` | Missing | Create with name, version, description, author, keywords |
| `plugins/rtfp/skills/rtfp/SKILL.md` | Missing | Move and update script paths |
| `plugins/rtfp/skills/rtfp/scripts/` | Missing | Move all 5 scripts |
| `plugins/rtfp/agents/` | Missing | Extract subagent prompts from SKILL.md Steps 3, 5 |
| `plugins/rtfp/README.md` | Missing | Create user-facing documentation |
| `plugins/rtfp/skills/rtfp/references/` | Not needed yet | Optional: extract subagent prompt templates |

### Path Migration Required

All script references in SKILL.md use `.claude/skills/rtfp/scripts/` paths. After migration to `plugins/rtfp/`, these must change to relative paths from the skill directory:

```text
BEFORE: uv run .claude/skills/rtfp/scripts/list_sessions.py
AFTER:  uv run ./scripts/list_sessions.py
```

This works because `uv run` resolves relative to CWD, and plugin scripts should use `${CLAUDE_PLUGIN_ROOT}` or relative paths from the skill directory.

### Subagent Extraction Decision

SKILL.md Steps 3 and 5 contain inline subagent prompts (multi-line text blocks). Two options:

1. **Keep inline** (simpler): Subagent prompts stay in SKILL.md. This works but makes the skill harder to maintain.
2. **Extract to agents/** (better): Create `agents/batch-scanner.md` and `agents/winner-picker.md` with proper frontmatter. SKILL.md references them by name. This enables independent testing and model selection per agent.

### Orphaned Script Resolution

| Script | Decision | Rationale |
|--------|----------|-----------|
| `detect_reactions.py` | Keep and integrate | Provides deterministic fallback when subagent-based detection is unavailable or for pre-filtering before LLM scan |
| `reconstruct_context.py` | Keep and integrate | Implements the full reconstruction pipeline without LLM calls -- valuable as a fast-path or fallback. SKILL.md should offer a `--fast` mode using scripts only vs `--deep` mode using subagents |

## Refactoring Recommendations

### CRITICAL (must fix before plugin release)

1. **STRUCTURE_FIX**: Create `plugins/rtfp/.claude-plugin/plugin.json` with proper manifest
   - Severity: Critical
   - Effort: Low

2. **DOC_IMPROVE**: Fix JSON field name mismatch between SKILL.md Step 5 subagent output (`task`/`assistant`/`user`) and `render_artifact.py` expected input (`task_summary`/`triggering_assistant_output`/`user_reaction`)
   - File: `.claude/skills/rtfp/SKILL.md` line 90-94
   - File: `.claude/skills/rtfp/scripts/render_artifact.py` line 461-463
   - Severity: Critical -- the workflow will fail at Step 6

3. **DOC_IMPROVE**: Fix `render_artifact.py` CLI invocation in SKILL.md Step 6 -- uses positional arg but script expects `--input-file` flag
   - File: `.claude/skills/rtfp/SKILL.md` line 102
   - Severity: Critical -- the workflow will fail at Step 6

### HIGH (should fix)

4. **DOC_IMPROVE**: Add `argument-hint: "[session-id]"` to frontmatter
   - Severity: High
   - Effort: Trivial

5. **DOC_IMPROVE**: Add `disable-model-invocation: true` to frontmatter -- this skill has side effects (temp files, PNG creation) and should only run when explicitly requested
   - Severity: High
   - Effort: Trivial

6. **DOC_IMPROVE**: Fix tiktoken encoding documentation mismatch in `extract_batches.py` -- docstring/help says `cl100k_base` but code uses `p50k_base`
   - File: `.claude/skills/rtfp/scripts/extract_batches.py` lines 54, 254
   - Severity: High -- misleading documentation

7. **SKILL_SPLIT**: Extract subagent prompts (Steps 3, 5) into `agents/batch-scanner.md` and `agents/winner-picker.md` during plugin migration
   - Severity: High
   - Effort: Medium

### MEDIUM (recommended)

8. **AGENT_OPTIMIZE**: Integrate orphaned scripts (`detect_reactions.py`, `reconstruct_context.py`) as a `--fast` pipeline mode that skips subagent delegation for quick results
   - Severity: Medium
   - Effort: Medium

9. **DOC_IMPROVE**: Add error handling guidance to SKILL.md -- what happens when no reactions are found (Step 4 mentions it briefly but Steps 3, 5 don't handle it)
   - Severity: Medium
   - Effort: Low

### LOW (optional)

10. **DOC_IMPROVE**: Add broader trigger keywords to description: "session analysis", "conversation review", "frustration", "share", "screenshot"
    - Severity: Low
    - Effort: Trivial

11. **STRUCTURE_FIX**: Deduplicate shared constants between `detect_reactions.py` and `reconstruct_context.py` (benign acronyms list, punctuation patterns) into a shared module
    - Severity: Low
    - Effort: Low

## Parallelization Opportunities

These migration tasks can execute in parallel:

| Track | Tasks | Dependencies |
|-------|-------|--------------|
| **A: Scaffold** | Create `plugin.json`, directory structure, `README.md` | None |
| **B: Fix SKILL.md** | Fix CLI invocation (Step 6), fix JSON field names (Step 5), add frontmatter fields | None |
| **C: Extract agents** | Create `agents/batch-scanner.md`, `agents/winner-picker.md` from inline prompts | None |
| **D: Fix scripts** | Fix tiktoken docs, deduplicate constants | None |
| **E: Integration** | Move files to plugin structure, update all paths | Depends on A, B, C, D |

Tracks A through D are fully independent and can run simultaneously. Track E is the final assembly step.

## Scoring Breakdown

| Component | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Structural validity | 20% | 40/100 | 8.0 |
| Manifest completeness | 15% | 0/100 | 0.0 |
| Frontmatter correctness | 20% | 60/100 | 12.0 |
| Description quality | 15% | 70/100 | 10.5 |
| Reference organization | 15% | 50/100 | 7.5 |
| Documentation quality | 10% | 75/100 | 7.5 |
| Enhancement potential | 5% | 90/100 | 4.5 |
| **Total** | **100%** | -- | **50/100** |

**Note**: Score reflects current state as a standalone skill directory, not as a plugin. The 0/100 on manifest completeness is because no `plugin.json` exists yet. Structural validity is low because 2 of 5 scripts are orphaned from the workflow. The skill content itself (description, workflow clarity, script quality) is solid.

**Adjusted score accounting for "skill-only" context** (removing manifest weight, redistributing): **62/100** -- this is the score used in the Executive Summary, reflecting quality of the skill itself before plugin migration.
