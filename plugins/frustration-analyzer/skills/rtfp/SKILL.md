---
name: rtfp
description: Read The Fucking Prompt — finds the strongest user reaction to an AI instruction-following failure in a chosen session, reconstructs what the assistant did wrong, and renders a shareable terminal-style PNG. Use when asked to find rage moments, generate a rage receipt, or capture a frustration incident from a session.
argument-hint: "[session-path]"
allowed-tools: "mcp__frustration-analyzer__list_sessions, mcp__frustration-analyzer__extract_user_messages, mcp__frustration-analyzer__get_context_window, mcp__frustration-analyzer__get_scenario, mcp__frustration-analyzer__render_rage_receipt, Read, Write, Glob"
disable-model-invocation: true
---

# RTFP — Read The Fucking Prompt

Finds the single strongest user reaction to an AI instruction-following failure, reconstructs the assistant output that triggered it, and renders the exchange as a terminal-style PNG ready for social media.

## Argument

Optional: a session file path. If provided, skip Steps 1–2 and use it directly.

## Step 1 — List Recent Sessions

Call `mcp__frustration-analyzer__list_sessions` with the current project path or the default `~/.claude/projects/`.

Present sessions as a numbered list:

```text
Recent sessions:
1. [2026-03-09 14:32] writing a Claude Code plugin       (…/abc123.jsonl)
2. [2026-03-09 11:15] debugging a FastMCP server         (…/def456.jsonl)
3. [2026-03-08 18:44] refactoring auth middleware        (…/ghi789.jsonl)
```

## Step 2 — User Selects Session

Ask the user to choose a number. Wait for their response. Use the chosen file path for all subsequent steps.

## Step 3 — Stage 1: User-Only Extraction

Call:

```text
mcp__frustration-analyzer__extract_user_messages(
    file="{chosen_file}",
    output_path="/tmp/rtfp-batch-{session_stem}.jsonl"
)
```

This writes a JSONL file containing ONLY user-authored messages. Each entry:

```json
{"file": "...", "line_index": 42, "text": "..."}
```

No assistant messages, tool outputs, system messages, or context are included. The batch file is the input to Stage 2 detection only.

Report: "Extracted N user messages. Created batch file at {output_path}."

If the session has more than 200 user messages, split into multiple batch files by slicing the output. Name them `…-batch-1.jsonl`, `…-batch-2.jsonl`, etc. For most sessions, one batch file is sufficient.

## Step 4 — Stage 2: Parallel Subagent Detection

For each batch file, spawn a subagent of type `frustration-analyzer:batch-detector`. Pass the batch file path in the delegation prompt.

Spawn all batch subagents in a single message (parallel). Each subagent reads only its assigned user-only batch file and returns:

- `{batch_path}.flags.json` — structured flagged entry list
- `{batch_path}.flags.txt` — plain list of flagged entries

Wait for all subagents to complete. Collect the output file paths.

Report: "Detection complete. Found M flagged messages across K batches."

If no flags were found across all batches, render a "no rage" card. Call:

```text
mcp__frustration-analyzer__render_rage_receipt(
    task_summary="Session analysis complete",
    assistant_excerpt="No strong emotional reactions detected in this session.",
    user_reply="👍",
    output_path="/tmp/rtfp-{session_stem}-clean.png"
)
```

Then skip to Step 8 and present the result using the same format as a normal receipt. Do NOT return a plain text string.

## Step 5 — Merge Flags

Read all `*.flags.json` files. Merge the `flags` arrays into a single file at `/tmp/rtfp-merged-{session_stem}.json`:

```json
{
  "session_file": "{chosen_file}",
  "flags": [
    {"file": "...", "line_index": 42, "text": "..."},
    ...
  ],
  "total": N,
  "batch_count": K
}
```

## Step 6 — Stage 3: Context Reconstruction

Spawn a subagent of type `frustration-analyzer:context-reconstructor`. Pass the merged flags file path in the delegation prompt.

The reconstruction agent:

1. Reads the merged flags
2. Picks the single most emotional/specific reaction as the winner
3. Notes a runner-up if one exists
4. Calls `get_context_window` to read full transcript context for the winner
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

- Stage 1 batch files MUST contain ONLY user-authored messages — no assistant content, no tool outputs, no system messages
- Context reconstruction happens ONLY in Stage 3 — never pull full context in Stages 1 or 2
- Do NOT add scores, verdicts, categories, or evaluative commentary
- This is one session at a time — not a corpus-wide analytics tool
- The task_summary is a single dry background line only, present tense, lowercase
- The assistant_excerpt and user_reply must be verbatim transcript text
