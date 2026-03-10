---
name: SubagentStop hook should capture structured summary of subagent work
description: "## Current state\n\n`task_status_hook.py` handles `SubagentStop` by marking the task COMPLETE, adding a `completed` timestamp, deleting the context file, and syncing completion to GitHub. It does NOT capture any summary of what the subagent accomplished — no record of files changed, tests written, errors encountered, or decisions made. The parent orchestrator (`implement-feature`) receives only the raw sub-agent output in its context window (which is lost on compaction) and has no structured artifact to reference when making routing decisions for subsequent tasks.\n\n## Target state\n\n`task_status_hook.py` SubagentStop handler writes a `summary` field to the task YAML frontmatter (or a separate `.claude/context/summaries/{session_id}-{task_id}.json` file) containing: files_modified (list), tests_added (count), key_decisions (list of strings), errors_encountered (list), and duration_seconds (int, computed from Started to Completed). The `implement-feature` orchestrator can read these summaries when deciding routing for dependent tasks.\n\n## Measurable signal\n\nAfter SubagentStop fires for a task, the task file's YAML frontmatter contains a `summary:` block with at least `files_modified` and `duration_seconds` fields populated. Verify by reading the task file after a task completes: `uv run implementation_manager.py status . {slug}` output includes a `summary` key for completed tasks."
metadata:
  topic: subagentstop-hook-should-capture-structured-summary-of-subag
  source: 'Research entry: ./research/agent-frameworks/everything-claude-code.md — pattern: Session Summaries in Hook SubagentStop Phase'
  added: '2026-03-10'
  priority: P1
  type: Feature
  status: open
  issue: '#576'
  last_synced: '2026-03-10T08:44:08Z'
---