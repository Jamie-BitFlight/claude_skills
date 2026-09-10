---
name: rtfp
description: Use when asked to find a rage moment, analyze a direct transcript path, or analyze a session time range. RTFP finds the strongest instruction-following failure in Claude or Codex sessions and renders a rage receipt.
argument-hint: '[session-path | session range]'
allowed-tools: mcp__frustration-analyzer__list_sessions, mcp__frustration-analyzer__extract_user_messages, mcp__frustration-analyzer__get_context_window, mcp__frustration-analyzer__get_scenario, mcp__frustration-analyzer__render_rage_receipt, Read, Write, Glob
---

# RTFP — Read The Fucking Prompt

Finds the single strongest user reaction to an AI instruction-following failure in a Claude or Codex session set, reconstructs the triggering assistant output, and renders it as a terminal-style PNG ready for social media.

## Argument

Optional: a Claude or Codex session file path, or a natural-language session range such as `this week`. A direct path analyzes that one file. A range analyzes every matched session only when `list_sessions` returns the complete requested set.

## Required MCP Tools

Before starting, confirm the plugin MCP tools needed for this run are available: `list_sessions` (unless a path was provided), `extract_user_messages`, `get_context_window` or `get_scenario`, and `render_rage_receipt`. If any are absent, stop and report that the RTFP plugin MCP tools are unavailable; do not manually read session or source-repository files as a substitute.

## Step 1 — Resolve the Session Set

For a direct path, use it as the one-item set and skip listing and selection.

For an explicit range such as `all this week`, resolve the dates in the user's timezone before the MCP call. Call `mcp__frustration-analyzer__list_sessions` with `provider`, `modified_after`, `modified_before`, and `limit=1000`. Report the resolved dates, matched count, and Claude/Codex split. “Progressed” means a file's modification time is inside the requested interval and the whole session is analyzed. If the result is truncated, ask the user for a narrower range or provider; only a complete result proceeds to analysis.

For an unqualified `/rtfp`, call `mcp__frustration-analyzer__list_sessions(provider="all", limit=10)`. Present the newest ten sessions with provider labels and let the user choose one, even when more sessions exist. This is a recent-session picker, not a complete-set request.

Present sessions as a numbered list:

```text
Matched sessions:
1. [Claude, 2026-03-09 14:32] writing a Claude Code plugin  (…/abc123.jsonl)
2. [Codex, 2026-03-09 11:15] debugging a FastMCP server      (…/def456.jsonl)
3. [Claude, 2026-03-08 18:44] refactoring auth middleware   (…/ghi789.jsonl)
```

## Step 2 — Select or Continue

For an unqualified request, ask the user to choose one numbered session. For a complete explicit multi-session request, skip this prompt and use every returned session. Use every selected file in the remaining stages.

## Step 3 — Stage 1: User-Only Extraction

For each selected file, in bounded parallel waves of at most four sessions, call:

```text
mcp__frustration-analyzer__extract_user_messages(
    file="{session_file}",
    output_path="/tmp/rtfp-batch-{session_key}.jsonl"
)
```

Use the returned `output_paths` as the Stage 2 inputs; it contains every batch for that session. Wait for each wave before starting the next. Report only each session's extracted message count, not internal batch paths or transcript line details.

## Step 4 — Stage 2: Parallel Subagent Detection

For each session's batches, delegate detection in the same bounded parallel waves. On Claude, use the named `frustration-analyzer:batch-detector` agent. On Codex, delegate a generic subagent with the batch path and this contract: read only that user-only batch; flag strong emotional reactions aimed at the assistant (not neutral corrections or frustration at something else); write the two artifacts below; and report its count.

Run at most four batch delegates per wave. The parent may handle one small batch directly; delegate every additional batch. Each detector returns:

- `{batch_path}.flags.json` — structured flagged entry list
- `{batch_path}.flags.txt` — plain list of flagged entries

Wait for all subagents to complete. Collect the output file paths.

Report: "Detection complete. Found M flagged messages across S sessions."

If no flags were found across all batches, always render a clean receipt. Call:

```text
mcp__frustration-analyzer__render_rage_receipt(
    task_summary="session-set analysis complete",
    assistant_excerpt="No strong emotional reactions detected in these sessions.",
    user_reply="👍",
    output_path="/tmp/rtfp-session-set-clean.png"
)
```

Then skip to Step 8 and present the receipt using the same format as a normal result.

## Step 5 — Merge Flags

Merge every returned `flags` array into `/tmp/rtfp-merged-session-set.json`. Preserve each flag's originating `file`, raw `line_index`, and text; never renumber lines across files. This artifact is internal: do not expose its path or raw line details in progress reports.

```json
{
  "session_files": ["{selected_file}", "..."],
  "flags": [
    {"file": "...", "line_index": 42, "text": "..."},
    ...
  ],
  "total": N,
  "session_count": S
}
```

## Step 6 — Stage 3: Context Reconstruction

Delegate reconstruction with the merged flags path. On Claude, use the named `frustration-analyzer:context-reconstructor` agent. On Codex, delegate a generic subagent to select the strongest specific reaction, retrieve context from the winner's originating file and raw line, identify the triggering verbatim assistant text, and write the same 3-field artifact.

The reconstruction agent:

1. Reads the merged flags
2. Picks the single most emotional/specific reaction as the winner
3. Notes a runner-up if one exists
4. Calls `get_context_window` against the winner's originating file to read full transcript context
5. Identifies the triggering assistant output
6. Produces the 3-field artifact: `task_summary`, `assistant_excerpt`, `user_reply`
7. Writes `{session_stem}.rtfp.json`

Wait for the reconstruction agent to complete. Read the `.rtfp.json` artifact it produced.

## Step 7 — Render PNG

Call:

```text
mcp__frustration-analyzer__render_rage_receipt(
    task_summary="{task_summary}",
    assistant_excerpt="{assistant_excerpt}",
    user_reply="{user_reply}",
    output_path="/tmp/rtfp-{session_stem}.png"
)
```

## Step 8 — Present Result

Display the 3 artifact fields clearly:

```text
task: {task_summary}

assistant said:
  {assistant_excerpt}

user replied:
  {user_reply}

PNG saved to: {output_path}
```

If a runner-up exists, offer:

> There's also a runner-up. Want to render that one?

## Constraints

- Stage 1 artifacts contain only user-authored messages.
- Stage 3 performs all context reconstruction.
- Each selection is bounded by its provider, interval, and limit.
- The final artifact contains exactly `task_summary`, `assistant_excerpt`, and `user_reply`; `task_summary` is a single dry lowercase present-tense line.
- `assistant_excerpt` and `user_reply` are verbatim transcript text.
