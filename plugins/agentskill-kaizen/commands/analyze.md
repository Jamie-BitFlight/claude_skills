---
name: analyze
description: Run autonomous transcript analysis pipeline across sessions
argument-hint: '[--project <name>] [--dimensions <list>]'
allowed-tools: Read,Write,Glob,Grep,Bash,Task
---

Run the autonomous transcript analysis pipeline. Spawn the @transcript-analyst agent to query JSONL session data, detect anti-patterns, and write structured findings.

## Arguments
<user_arguments>$ARGUMENTS</user_arguments>

- `--project {project}` — Scope analysis to a specific project. The project key is the path with hyphens replacing slashes. Default: current project (derived from cwd).
- `--dimensions {dimensions}` — Comma-separated list of dimensions to analyze. Options: tool-misuse, errors, frustration, tooling-gaps, delegation, shortest-path, red-herrings, interruptions, missing-hooks, all. Default: all.

## Execution Steps

1. **Resolve transcript path.** Determine the project transcript directory:

   ```text
   ~/.claude/projects/{project}/
   ```

   If `--project` is provided, use it as the project key. Otherwise, derive from the current working directory by replacing `/` with `-` and prepending `-`.

2. **Create output directory.** Ensure `.planning/kaizen/` exists in the current project root.

3. Delegate the analysis via Agent tool:

   ```text
   subagent_type: agentskill-kaizen:transcript-analyst
   prompt: "Analyze transcripts at {path}. Dimensions: {dimensions}. Write findings to .planning/kaizen/analysis-{date}.md"
   ```

   The agent has access to DuckDB MCP for SQL queries and the custom kaizen MCP for process mining. Let it choose its own analysis approach.

4. **Report results.** After the agent completes, summarize:
   - Number of sessions analyzed
   - Number of findings by severity
   - Path to the analysis report file

## Output

Analysis report written to `.planning/kaizen/analysis-{YYYY-MM-DD}.md` with structured findings including session IDs, severity, evidence, and improvement recommendations.
