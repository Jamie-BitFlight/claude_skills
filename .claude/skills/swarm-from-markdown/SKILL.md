---
name: swarm-from-markdown
description: Parse a markdown file's unchecked checkbox items (- [ ]) and generate a self-organizing Claude Code swarm task pool. Use when you have a todo.md, checklist.md, or any markdown file with checkbox items and want to dispatch them as parallel swarm tasks using TeamCreate + TaskCreate + worker agents. Skips checked items (- [x] / - [X]) automatically.
---

# Swarm from Markdown

Converts a markdown checklist file into a self-organizing Claude Code swarm. Each unchecked `- [ ]` item becomes a `TaskCreate` call and a spawned worker agent. Checked items (`- [x]`, `- [X]`) are skipped automatically.

## When to Use This Skill

Use when:

- You have a `todo.md`, `checklist.md`, or any markdown file with `- [ ]` checkbox items
- You want to dispatch independent checklist items as parallel swarm tasks
- You need to avoid hand-expanding long task lists into manual `TaskCreate` loops
- Your task list changes over time and you want stable worker IDs for resumption

## Quick Start (Worked Example)

Given `tasks.md`:

```markdown
- [ ] Implement the login endpoint
- [x] Already done — skip this
- [ ] Write unit tests for auth
- [ ] Update API documentation
```

Run the parser:

```bash
uv run scripts/markdown_to_task_pool.py tasks.md --json
```

Output:

```json
{
  "team_name": "swarm-tasks",
  "items": [
    {"index": 0, "worker_id": "worker-0", "text": "Implement the login endpoint"},
    {"index": 1, "worker_id": "worker-1", "text": "Write unit tests for auth"},
    {"index": 2, "worker_id": "worker-2", "text": "Update API documentation"}
  ],
  "worker_count": 3
}
```

Then orchestrate the swarm:

```javascript
// Step 1 — Create team
TeamCreate({ team_name: "swarm-tasks" })

// Step 2 — Create one task per unchecked item (checked item is excluded)
TaskCreate({ subject: "Implement the login endpoint", description: "Implement the login endpoint", activeForm: "Working on Implement the login endpoint..." })
TaskCreate({ subject: "Write unit tests for auth", description: "Write unit tests for auth", activeForm: "Working on Write unit tests for auth..." })
TaskCreate({ subject: "Update API documentation", description: "Update API documentation", activeForm: "Working on Update API documentation..." })

// Step 3 — Spawn one worker per task (or use --workers N to cap concurrency)
Agent({ team_name: "swarm-tasks", name: "worker-0", subagent_type: "general-purpose", prompt: "...", run_in_background: true })
Agent({ team_name: "swarm-tasks", name: "worker-1", subagent_type: "general-purpose", prompt: "...", run_in_background: true })
Agent({ team_name: "swarm-tasks", name: "worker-2", subagent_type: "general-purpose", prompt: "...", run_in_background: true })

// Step 4 — Observe pool state
TaskList()
```

The `[x]` checked item never appears in any `TaskCreate` call.

## How It Works

1. Parse the markdown file using the marko GFM AST (not regex).
2. Walk the AST: collect `ListItem` nodes whose child `Paragraph` has `checked is False`.
3. Assign each item a 0-based index — `worker-{index}` — over unchecked items only.
4. Derive team name from the filename stem: `swarm-{stem}`.
5. Emit JSON or human-readable output showing the `TaskCreate` sequence and worker count.

Worker IDs are stable when items are only appended: re-running on the same file with new items added at the end preserves existing IDs. Checking (completing) an earlier item shifts all subsequent unchecked items to lower indices — do not resume a partially-executed swarm after checking items mid-list.

## marko AST Walk (GFM Checkbox Detection)

The checkbox `checked` attribute lives on the `Paragraph` child of a `ListItem`, not on the `ListItem` itself. The guard `child.checked is not False` skips both checked items (`True`) and non-checkbox list items (`None`).

```python
from marko import Markdown
from marko.block import List, ListItem, Paragraph
from marko.inline import RawText

md = Markdown(extensions=["gfm"])
doc = md.parse(markdown_text)      # parse() returns AST — do NOT call md() which returns HTML

results = []
for node in doc.children:
    if not isinstance(node, List):
        continue
    for item in node.children:
        if not isinstance(item, ListItem):
            continue
        for child in item.children:
            if not isinstance(child, Paragraph) or not hasattr(child, "checked"):
                continue
            if child.checked is not False:   # True=checked, None=non-checkbox — both skip
                continue
            text_parts = [
                c.children.strip()
                for c in child.children
                if isinstance(c, RawText)
            ]
            text = " ".join(text_parts).strip()
            if text:
                results.append(text)
```

Marko normalizes `[x]` and `[X]` to `checked=True` at parse time — no separate patterns needed.

## CLI Script Reference

```bash
uv run scripts/markdown_to_task_pool.py <markdown_file> [--workers N] [--json] [-h]
```

| Argument | Description |
|---|---|
| `markdown_file` | Path to markdown file with checkbox items |
| `--workers N` | Number of worker agents to spawn (default: number of unchecked items) |
| `--json` | Emit JSON instead of human-readable output |
| `-h` | Show help |

Examples:

```bash
# Human-readable output
uv run scripts/markdown_to_task_pool.py todo.md

# JSON output (pipe to orchestration script)
uv run scripts/markdown_to_task_pool.py tasks.md --json

# Cap workers at 3 regardless of item count
uv run scripts/markdown_to_task_pool.py tasks.md --json --workers 3
```

`--workers N` overrides the worker count while item count stays unchanged. Use it to cap concurrency when you have many items but want fewer parallel agents.

## TeamCreate + TaskCreate Call Flow

Full orchestration for a file with N unchecked items:

```javascript
// 1. Parse the file
// uv run scripts/markdown_to_task_pool.py <file> --json
// → { "team_name": "swarm-{stem}", "items": [...], "worker_count": N }

// 2. Create team
TeamCreate({ team_name: "swarm-{stem}" })

// 3. Create tasks — one per unchecked item (loop over items array from script output)
// Each unchecked item becomes one task; checked items are absent from items array
// See the worked example above for concrete TaskCreate calls

// 4. Spawn workers — one per item (or --workers N if capped)
Agent({ team_name: "swarm-{stem}", name: "{item.worker_id}", subagent_type: "general-purpose", prompt: WORKER_PROMPT, run_in_background: true })
// ... repeated for each worker

// 5. Observe and synthesize
TaskList()
// Collect findings via SendMessage team-lead channel
```

## Worker Prompt Template

Each worker receives this 8-step self-organizing prompt, parameterized by `{team_name}` and `{worker_id}`:

```text
You are swarm worker {worker_id} in team {team_name}.

Your job loop:
1. Call TaskList() to see all tasks in the pool.
2. Find a task with status 'pending' and no owner field set.
3. Claim it: call TaskUpdate with owner={worker_id} and status='in-progress'.
4. Re-read the task description and do the actual work.
5. Mark it done: call TaskUpdate with status='complete' and add a result summary.
6. Send your findings to the team-lead: SendMessage({ type: "direct_message", recipient: "team-lead", content: "Completed: {task subject} — {summary}" }).
7. Repeat from step 1 until TaskList() shows no pending tasks with no owner.
8. Send shutdown acknowledgment: SendMessage({ type: "shutdown_acknowledgment", recipient: "team-lead", content: "No tasks remain. Shutting down." }).
```

All workers run the same prompt. They race to claim tasks and naturally load-balance — no central coordinator needed.

## Output Contract

JSON schema emitted by `--json`:

```json
{
  "team_name": "swarm-{stem}",
  "items": [
    {"index": 0, "worker_id": "worker-0", "text": "First unchecked item text"},
    {"index": 1, "worker_id": "worker-1", "text": "Second unchecked item text"}
  ],
  "worker_count": 2
}
```

- `team_name`: `swarm-` prefix + markdown filename stem (no extension)
- `items`: only unchecked items — checked items are absent
- `index`: 0-based over unchecked items only
- `worker_id`: `worker-{index}`
- `worker_count`: defaults to `len(items)`; overridden by `--workers N`

Exit codes: 0 on success (including zero-item case), 1 on file-not-found or parse failure.

## Source Pattern

This skill automates the manual `TaskCreate` loop at lines 109-114 of [../swarm-patterns/SKILL.md](../swarm-patterns/SKILL.md) (Pattern 3: Self-Organizing Swarm).

The "Todo-Driven Delegation" pattern — parsing `todo.md` checkbox items and generating worker assignments from item indices — originates in the Octogent agent framework:

SOURCE: [../../../research/agent-frameworks/octogent.md](../../../research/agent-frameworks/octogent.md) lines 51-53 (accessed 2026-05-19): "todo.md contains markdown checkbox items. The runtime parses these items and generates worker prompts from them. Incomplete items automatically become worker assignments in swarm runs, and terminal IDs like `<tentacle-id>-swarm-0` are derived from parsed item indices."
