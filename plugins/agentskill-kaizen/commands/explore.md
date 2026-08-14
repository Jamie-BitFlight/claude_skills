---
name: explore
description: Interactive transcript exploration — presents findings, user steers investigation
argument-hint: '[--project <name>]'
allowed-tools: Read,Write,Glob,Grep,Bash,Task
---

Start an interactive transcript exploration session. Present initial findings from the transcript corpus, then let the user steer deeper investigation.

## Arguments

- `--project <name>` — Scope to a specific project transcript directory. Default: current project.

## Execution Steps

1. **Resolve transcript path.** Same logic as `/agentskill-kaizen:analyze` — derive project key from `--project` flag or current working directory.

2. **Run initial survey.** Use DuckDB MCP to run a quick corpus overview:
   - Total session count and date range
   - Record type distribution
   - Top 10 most-used tools
   - Error rate summary
   - User interrupt count

3. **Present findings to user.** Display the survey results and suggest investigation directions:
   - "I found {N} sessions with {M} tool misuse violations. Want to dig into those?"
   - "I found {K} repeated workflow deviations. Want to compare those sessions?"
   - "The most common error is {type} ({count} times). Want to trace those sessions?"

4. **Follow user direction.** Based on user response, run targeted queries:
   - Use DuckDB SQL for structured data extraction
   - Use kaizen MCP tools for process mining and pattern detection
   - Present results incrementally
   - Ask clarifying questions to narrow investigation

5. **Save findings on request.** When the user wants to save findings, write to `.planning/kaizen/exploration-{date}.md`.

## Interaction Pattern

This command runs interactively — do NOT spawn an autonomous agent. Stay in the main conversation so the user can steer the investigation in real-time. Use MCP tools directly for queries.
