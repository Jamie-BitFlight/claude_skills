---
name: rtfp
description: 'Scan Claude Code session transcripts to find the strongest user reactions to assistant instruction-following failures, reconstruct the triggering assistant output, and render a shareable terminal-style PNG artifact. Use when you want to surface and share a moment where the assistant completely missed what was asked — captures what they were doing, what Claude said, and how the user reacted. Triggers on: "rtfp", "read the fucking prompt", "find my worst AI moment", "make a rage screenshot from this session".'
---

# RTFP — Read The Fucking Prompt

Scan a Claude Code session transcript for the single strongest user reaction to an assistant instruction-following failure. Render it as a terminal-style PNG for sharing.

Output is exactly three things: what they were doing, what Claude said, how the user reacted.

---

## Constraints (Non-Negotiable)

- One clean moment — not a report
- Do NOT build a taxonomy of failure types
- Do NOT add scoring or severity ratings
- Do NOT add verdicts or evaluative summaries
- Do NOT analyze why the misunderstanding occurred
- Do NOT produce session-wide analytics

---

## Workflow

### Step 1 — List Sessions

```bash
uv run ./scripts/list_sessions.py --json
```

Present the numbered list to the user. Ask which session to inspect. Wait for the user's selection (by number or session ID) before proceeding.

### Step 2 — Extract Batches

```bash
TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")
uv run ./scripts/extract_batches.py <session_jsonl_path> --out-dir "$TMPDIR/rtfp-batches-<sessionid>"
```

The script outputs a JSON object. Read the `batch_files` array from this object — each path in that array is one batch to scan in Step 3.

### Step 3 — Fan-Out Scan (one subagent per batch)

Spawn one general-purpose subagent per batch file. Each subagent receives its assigned batch file path and these instructions:

```text
Read the batch JSON file at <batch_file_path>.
Scan all user messages for strong emotional reactions targeted at the assistant:
frustration, disbelief, insults, argument, rage, or clearly negative emotional
responses aimed at the AI's behavior.

Determine the platform temp directory first:
TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")

Produce TWO outputs:

1. Write a JSON file to $TMPDIR/rtfp-flagged-<batch_index>.json with this format:
   {"source_file": "<original_session_jsonl_path>", "flagged_indexes": [N, ...]}
   Use the source_file field from the batch JSON header (the original session JSONL path, not the batch file path).
   Write an empty flagged_indexes array if no reactions are found.

2. Print a plain list of flagged entries to your output:
   each line: <message_index> | <full content> (no truncation)
```

Wait for all subagents to finish before proceeding.

### Step 4 — Merge Flagged Indexes

Read each `$TMPDIR/rtfp-flagged-<batch_index>.json` file produced in Step 3 (where `TMPDIR` was determined via `python3 -c "import tempfile; print(tempfile.gettempdir())"`). Merge all `flagged_indexes` arrays into a single working set keyed by source file. If no indexes were flagged across all batches, report that to the user and stop.

### Step 5 — Pick the Winner (final subagent)

Spawn one general-purpose subagent with the merged working set and the original session JSONL path. Instructions to that subagent:

```text
You have a merged set of flagged message indexes from a Claude Code session transcript.
Session JSONL file: <session_jsonl_path>
Flagged indexes: <merged_working_set_as_json>

1. Read the full session JSONL file.
2. Read every flagged user message at the given indexes.
3. Choose the single most emotional, rage-filled response as the winner.
   Optionally identify one runner-up.
4. Determine what the user was currently doing when the reaction occurred —
   write one dry background line describing the activity, not the incident.
   CORRECT:   "writing a Claude Code plugin"
   CORRECT:   "refactoring test fixtures"
   INCORRECT: "the assistant ignored the constraint about scoring"
   INCORRECT: "failure to follow the instruction to omit scoring"
5. Inspect nearby transcript entries and identify the assistant message(s) that triggered the winning reaction. Do not assume it is always the single immediately preceding message — look at the surrounding context window.
6. Determine the platform temp directory:
   TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")
   Write $TMPDIR/rtfp-result.json with exactly these fields:
   {
     "task_summary": "<dry one-line activity description>",
     "triggering_assistant_output": "<triggering assistant output>",
     "user_reaction": "<winning emotional user reply>"
   }
```

Wait for the subagent to finish. Verify `$TMPDIR/rtfp-result.json` exists before proceeding (use the same `TMPDIR` value).

### Step 6 — Render PNG

```bash
TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")
uv run ./scripts/render_artifact.py --input-file "$TMPDIR/rtfp-result.json" --output rtfp_artifact.png
```

The script produces a terminal-style dark PNG with:

- Title bar: "rtfp — Read The Fucking Prompt" with red/yellow/green dots
- `task:` + dry activity line
- Divider
- `claude:` + triggering assistant output (truncated to fit if needed)
- Divider
- `user:` + emotional user reply in vivid/bright color

### Step 7 — Report

Report the output PNG path to the user. Display the three fields as text in the response:

```text
task:      <dry activity line>
claude:    <assistant excerpt>
user:      <emotional reply>

PNG: rtfp_artifact.png
```
