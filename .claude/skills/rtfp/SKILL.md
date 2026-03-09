---
name: rtfp
description: "SUPERSEDED — use the plugin version at plugins/rtfp/skills/rtfp/SKILL.md instead. This skill and its scripts have been migrated to the plugins/rtfp/ plugin directory."
allowed-tools: "Read, Bash, Glob, Write"
deprecated: true
---

> **SUPERSEDED**: This skill has been migrated to `plugins/rtfp/`. Use the plugin version instead.
> The canonical location is `plugins/rtfp/skills/rtfp/SKILL.md` with scripts at `plugins/rtfp/skills/rtfp/scripts/`.
> Scripts in `.claude/skills/rtfp/scripts/` are the originals preserved for reference only.

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

## Fast Mode (Heuristic Pipeline — No Subagents)

For quick results without LLM subagent delegation, use the heuristic scripts directly:

```bash
# Step 1: List sessions (same as default)
uv run .claude/skills/rtfp/scripts/list_sessions.py --json

# Step 2: Detect reactions heuristically (replaces Steps 3-4)
uv run .claude/skills/rtfp/scripts/detect_reactions.py <session_jsonl_path>

# Step 3: Reconstruct context and pick winner (replaces Step 5)
uv run .claude/skills/rtfp/scripts/reconstruct_context.py <session_jsonl_path> --flagged-indexes <indexes>

# Step 4: Render PNG (same as Step 6)
uv run .claude/skills/rtfp/scripts/render_artifact.py --input-file /tmp/rtfp-result.json --output rtfp_artifact.png
```

Fast mode trades accuracy for speed — the heuristic detection may miss subtle reactions that the LLM scan catches. Use the default workflow below for best results.

---

## Workflow (Default — LLM-Based)

### Step 1 — List Sessions

```bash
uv run .claude/skills/rtfp/scripts/list_sessions.py --json
```

Present the numbered list to the user. Ask which session to inspect. Wait for the user's selection (by number or session ID) before proceeding.

### Step 2 — Extract Batches

```bash
uv run .claude/skills/rtfp/scripts/extract_batches.py <session_jsonl_path> --out-dir /tmp/rtfp-batches-<sessionid>
```

The script outputs a JSON object with keys including `session_id`, `out_dir`, and `batch_files`. Read the `batch_files` array from this object — each path in that array is one batch to scan in Step 3.

### Step 3 — Fan-Out Scan (one subagent per batch)

Spawn one general-purpose subagent per batch file. Each subagent receives its assigned batch file path and these instructions:

```text
Read the batch JSON file at <batch_file_path>.
Scan all user messages for strong emotional reactions targeted at the assistant:
frustration, disbelief, insults, argument, rage, or clearly negative emotional
responses aimed at the AI's behavior.

Produce TWO outputs:

1. Write a JSON file to /tmp/rtfp-flagged-<batch_index>.json with this format:
   {"source_file": "<batch_file_path>", "flagged_indexes": [N, ...]}
   Write an empty flagged_indexes array if no reactions are found.

2. Print a plain list of flagged entries to your output:
   each line: <message_index> | <first 200 chars of content>
```

Wait for all subagents to finish before proceeding.

### Step 4 — Merge Flagged Indexes

Read each `/tmp/rtfp-flagged-<batch_index>.json` file produced in Step 3. Merge all `flagged_indexes` arrays into a single working set keyed by source file. If no indexes were flagged across all batches, report that to the user and stop.

### Step 5 — Pick the Winner (final subagent)

Spawn one general-purpose subagent with the merged working set and the original session JSONL path. Instructions to that subagent:

```text
You have a merged set of flagged message indexes from a Claude Code session transcript.
Session JSONL file: <session_jsonl_path>
Flagged indexes: <merged_working_set_as_json>

The indexes in flagged_indexes are jsonl_line_index values — 1-based line numbers in the
source JSONL file (line 1 = first line). Use these to locate records by counting lines
from the top of the file, not by position among filtered messages.

1. Read the full session JSONL file.
2. Read every flagged user message at the given jsonl_line_index positions (1-based line numbers).
3. Choose the single most emotional, rage-filled response as the winner.
   Optionally identify one runner-up.
4. Determine what the user was currently doing when the reaction occurred —
   write one dry background line describing the activity, not the incident.
   CORRECT:   "writing a Claude Code plugin"
   CORRECT:   "refactoring test fixtures"
   INCORRECT: "the assistant ignored the constraint about scoring"
   INCORRECT: "failure to follow the instruction to omit scoring"
5. Identify the assistant message(s) immediately preceding the winning reaction.
6. Write /tmp/rtfp-result.json with exactly these fields:
   {
     "task_summary": "<dry one-line activity description>",
     "triggering_assistant_output": "<triggering assistant output>",
     "user_reaction": "<winning emotional user reply>"
   }
```

Wait for the subagent to finish. Verify `/tmp/rtfp-result.json` exists before proceeding.

### Step 6 — Render PNG

```bash
uv run .claude/skills/rtfp/scripts/render_artifact.py --input-file /tmp/rtfp-result.json --output rtfp_artifact.png
```

The script produces a terminal-style dark PNG with:

- Title bar: "Claude Code" with red/yellow/green dots
- `task:` + dry activity line
- Divider
- `assistant:` + triggering assistant output (wrapped to fit)
- Divider
- `user:` + emotional user reply in vivid/bright color

### Step 7 — Report

Report the output PNG path to the user. Display the three fields as text in the response:

```text
task:      <dry activity line>
assistant: <assistant excerpt>
user:      <emotional reply>

PNG: rtfp_artifact.png
```
