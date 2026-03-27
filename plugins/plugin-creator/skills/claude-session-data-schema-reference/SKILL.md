---
name: claude-session-data-schema-reference
description: Claude Code session log schema — JSONL record types, message structure, tool call/result pairing, subagent file locations, team session layout, task/plan/team configuration paths. Use when parsing ~/.claude/projects/**/*.jsonl files, writing PostToolUse hooks that measure response sizes, building session analyzers, or any agent that reads or queries Claude session transcripts.
user-invocable: false
allowed-tools: Read
---

# Claude Code Session Log Schema

Reference skill for the JSONL session log format written by Claude Code under `~/.claude/projects/`.

All claims in the reference are sourced from direct JSONL file inspection and verified against the
LM Assist TypeScript source. No fields are inferred.

## When to Load

Load `./references/schema.md` when you need:

- Directory structure and project-key encoding rules
- Complete record type discriminator (`system`, `user`, `assistant`, `result`, `progress`, `summary`, `file-history-snapshot`)
- Field-level schema for each record type
- Tool call / tool result pairing algorithm
- Subagent and team session file naming conventions
- Task, plan, and team configuration paths
- Hook integration — how `PostToolUse` `tool_response` maps to `tool_result.content`
- What is NOT in the logs (per-tool token costs, streaming events, hook records, per-tool timing)

## Source

Schema verified 2026-03-24. Source reference: `./references/schema.md`.
