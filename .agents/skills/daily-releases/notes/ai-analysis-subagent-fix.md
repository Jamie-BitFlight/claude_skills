# AI Analysis Subagent Fix Plan

## Findings

### Anti-Pattern Location

The AI analysis step runs in the orchestrator itself. The instructions are in:

- **File:** `.claude/skills/daily-releases/SKILL.md`
- **Lines:** 72–95 (Step 2b)

The relevant instruction text (lines 72–95):

```text
#### 2b. AI analysis

Read the extracted data and apply the primary analysis prompt from:

  .claude/skills/create-merge-request-changelog/references/analysis_prompts.md

Use the **Primary Analysis Prompt** section with the day's data substituted in:

- {commit_details} → contents of commits_detailed.txt
- {changes_diff}   → contents of changes.diff (truncate to ~4000 chars if very large; use changes_stat.txt instead)
- {changed_files}  → contents of changed_files.txt
- {commit_count}, {files_changed}, {lines_added}, {lines_deleted} → from summary.json

Produce the structured JSON analysis output defined in the prompt's <output_format> section.

Also generate a title using the Title Generation Prompt:
  Daily Release - <date>

Save the complete analysis JSON to ./daily-releases/<date>/analysis.json.
```

### What "Run in the Orchestrator" Means Here

The SKILL.md is consumed by the orchestrating Claude Code session (the AI session that activated `/daily-releases`). Step 2b instructs that session to:

1. Read `commits_detailed.txt`, `changes.diff`, `changed_files.txt`, `summary.json` into its own context window.
2. Execute the Primary Analysis Prompt inline — i.e., the orchestrator IS the LLM performing the analysis.
3. Write the resulting JSON to `analysis.json`.

There is no subprocess call, no SDK invocation, no `Agent()` delegation — the orchestrator consumes the raw git data directly and burns its context window doing the categorization work.

### Input Files Read by Step 2b

All paths are relative to the repository root:

| Variable | File Path |
|----------|-----------|
| `{commit_details}` | `./daily-releases/<date>/commits_detailed.txt` |
| `{changes_diff}` | `./daily-releases/<date>/changes.diff` |
| `{changed_files}` | `./daily-releases/<date>/changed_files.txt` |
| `{commit_count}` / `{files_changed}` / `{lines_added}` / `{lines_deleted}` | `./daily-releases/<date>/summary.json` |

These files are produced by Step 2a (`analyze_git_changes.py`). The orchestrator reads all of them before constructing the analysis prompt.

### Output File Written by Step 2b

```text
./daily-releases/<date>/analysis.json
```

This file is then consumed by Step 2c (`format_mr_description.py`), which is a Python script — not the orchestrator.

### Why This Is the Anti-Pattern

The orchestrator context window is shared across the entire session and across all days being processed. When processing N days, the orchestrator reads N sets of git data files and performs N AI analysis passes in its own context. Each pass consumes:

- The full `commits_detailed.txt` content
- Up to 4000 chars of `changes.diff`
- The `changed_files.txt` and `summary.json` contents
- The full Primary Analysis Prompt from `analysis_prompts.md`

For a backfill of many days, this exhausts the orchestrator context window and degrades output quality for later days.

The correct pattern: delegate each analysis to a fresh subagent that receives the file paths, performs the analysis in its own context window, and writes `analysis.json` without consuming any orchestrator context.

---

## Proposed Fix

### Pattern: Replace Step 2b with an Agent Delegation

The fix replaces the inline "Read data, apply prompt, write JSON" instruction in SKILL.md with an instruction to invoke an `Agent` subagent.

The subagent receives:
- The file paths (not the file contents)
- The path to the analysis prompts reference file
- The output path for `analysis.json`

The subagent reads the files, applies the Primary Analysis Prompt, and writes the output. The orchestrator never reads the git data files.

### Pseudocode for Updated Step 2b in SKILL.md

```text
#### 2b. AI analysis (subagent delegation)

Delegate the analysis to a subagent. Do NOT read the git data files yourself.

Invoke Agent with:
  subagent_type: "general-purpose"
  model: "claude-haiku-4-5"
  prompt: |
    You are analyzing git changes to produce a structured JSON categorization.

    Read these files from the repository root:
      - ./daily-releases/<date>/commits_detailed.txt   → {commit_details}
      - ./daily-releases/<date>/changes.diff           → {changes_diff}
      - ./daily-releases/<date>/changed_files.txt      → {changed_files}
      - ./daily-releases/<date>/summary.json           → stats fields

    Apply the Primary Analysis Prompt from:
      .claude/skills/create-merge-request-changelog/references/analysis_prompts.md

    Substitute the file contents into the prompt variables exactly as documented.
    If changes.diff exceeds 4000 chars, use changes_stat.txt instead for {changes_diff}.

    Write the complete JSON output (matching the <output_format> schema in the prompt)
    to: ./daily-releases/<date>/analysis.json

    Do not print the JSON to stdout. Write only to the output file.
    Report "analysis.json written" when done.

Wait for the subagent to complete, then verify ./daily-releases/<date>/analysis.json exists
before proceeding to Step 2c.
```

### Why Haiku

- The analysis task is mechanical pattern-matching against a well-defined prompt schema
- The Primary Analysis Prompt in `analysis_prompts.md` fully specifies categories, indicators, and output format
- Haiku is cost-effective for high-volume per-day processing
- Each subagent invocation gets a fresh context window — no degradation across N days
- The reasoning required is bounded and structured — not open-ended design work

### Precedent

This mirrors the KB descriptions fix referenced in the backlog entry that prompted this investigation: replace inline orchestrator LLM work with `Agent(subagent_type="general-purpose", model="haiku")` delegation where the subagent receives file paths and writes output files.

---

## Blockers and Open Questions

### 1. Does the SKILL.md `Agent()` syntax support model selection?

The SKILL.md currently instructs the orchestrator to use prose commands ("Read...", "Apply the prompt..."). The fix requires the orchestrator to emit an `Agent()` tool call with `model="claude-haiku-4-5"`. This depends on whether the Claude Code session running this skill supports the `Agent` tool directly.

- If the skill runs in a session with `Agent` available: the fix works as described.
- If the skill runs in a context where `Agent` is unavailable (e.g., a non-agentic slash command context): the fix requires a different mechanism — possibly a standalone Python script that invokes the Anthropic SDK with Haiku and writes `analysis.json`.

**Resolution needed:** Confirm whether `/daily-releases` skill activations run in a context where `Agent()` tool is available to the orchestrator.

### 2. Draft release duplication (noted in backlog)

The backlog entry that prompted this investigation (`6d53c9c`) also references "fixing draft release duplication." This is a separate concern in `publish_daily_release.py` and is not addressed by the Step 2b subagent fix. The two issues should be tracked independently.

### 3. Haiku hallucination rate on structured output

CLAUDE.md documents Haiku at ~50% hallucination rate for reasoning tasks. The Primary Analysis Prompt requires classification reasoning (choosing between Bug Fix / Enhancement / Tech Debt / etc.). This is borderline — it is structured but requires judgment.

**Mitigation:** The analysis prompt is highly prescriptive with explicit indicators and diff patterns for each category. The output schema is strict JSON. These constraints reduce the reasoning surface significantly. Haiku is still the recommended choice for cost/volume reasons, but this risk should be noted in the SKILL.md update.

**Alternative:** Use `claude-sonnet-4-5` if analysis quality from Haiku proves insufficient after testing.

---

## Source References

- Anti-pattern location: `.claude/skills/daily-releases/SKILL.md`, lines 72–95
- Analysis prompt source: `.claude/skills/create-merge-request-changelog/references/analysis_prompts.md` (Primary Analysis Prompt section, lines 9–181)
- Output consumer: Step 2c uses `format_mr_description.py` at `.claude/skills/create-merge-request-changelog/scripts/format_mr_description.py`
- Haiku hallucination rate: CLAUDE.md, Model Selection section, Haiku 4.5 entry
- Precedent (KB descriptions fix): commit `6d53c9c` message

SOURCE: Direct file inspection of `.claude/skills/daily-releases/SKILL.md` and `.claude/skills/create-merge-request-changelog/references/analysis_prompts.md` (accessed 2026-02-24)
