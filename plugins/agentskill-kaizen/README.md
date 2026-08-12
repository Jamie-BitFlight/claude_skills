<p align="center">
  <img src="./assets/hero.png" alt="agentskill-kaizen" width="800" />
</p>

# agentskill-kaizen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-blueviolet.svg)](https://claude.ai/code)

You make the same mistakes across sessions and have no way to see them. Claude Code writes
session transcripts to `~/.claude/projects/` after every conversation. This plugin mines those
JSONL files with SQL and process-mining algorithms to find anti-patterns, then generates
concrete fixes — hook scripts, skill patches, CLAUDE.md updates — as reviewable draft
proposals.

## Quick Start

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install agentskill-kaizen@jamie-bitflight-skills
```

Run the full analysis:

```
/agentskill-kaizen:analyze
```

Review findings:

```
/agentskill-kaizen:report
```

Generate fixes for the top anti-patterns:

```
/agentskill-kaizen:generate-hooks
```

## Commands

### `/agentskill-kaizen:analyze` — Full autonomous pipeline

```
/agentskill-kaizen:analyze
/agentskill-kaizen:analyze --project -home-user-repos-myproject
/agentskill-kaizen:analyze --dimensions tool-misuse,errors,frustration
```

Runs the `transcript-analyst` agent across your session corpus. The agent queries JSONL files
with DuckDB SQL and applies process-mining algorithms (prefix span, clustering) across ten
anti-pattern dimensions. Output is written to `.planning/kaizen/analysis-{YYYY-MM-DD}.md`.

### `/agentskill-kaizen:explore` — Interactive investigation

```
/agentskill-kaizen:explore
/agentskill-kaizen:explore --project -home-user-repos-myproject
```

Starts an interactive session: the agent presents initial findings from the transcript corpus,
then lets you steer deeper investigation. Use when you have a specific hypothesis or want to
follow a thread that the automated analysis surfaced.

### `/agentskill-kaizen:report` — Summary from existing analysis

```
/agentskill-kaizen:report
/agentskill-kaizen:report --latest
/agentskill-kaizen:report --all
```

Reads existing analysis files in `.planning/kaizen/` and produces a structured summary.
Faster than re-running analysis — use this to review findings between analysis runs.

### `/agentskill-kaizen:generate-hooks` — Translate findings into fixes

```
/agentskill-kaizen:generate-hooks
/agentskill-kaizen:generate-hooks --from .planning/kaizen/analysis-2026-02-18.md
/agentskill-kaizen:generate-hooks --install
```

Runs the `improvement-generator` agent to produce draft fixes from analysis findings. Without
`--install`, all output is written to `.planning/kaizen/hooks/` as reviewable proposals.
With `--install`, approved proposals are applied immediately.

## What the Analysis Finds

Ten dimensions analyzed across your session history:

| Dimension | What it finds |
|-----------|---------------|
| Tool Misuse | Bash calls for file read/write/search instead of built-in tools |
| Repeated Errors | Edit-before-Read patterns, stale edits, denied tool calls |
| User Frustration | Corrections, denials, interrupts, "you keep doing this" signals |
| Tooling Gaps | Multi-step sequences that repeat identically and could be a single script |
| Delegation Patterns | Whether Claude uses specialist agents or defaults to general-purpose |
| Shortest Path | Wasted steps when the same goal was reached faster in other sessions |
| Red Herrings | Investigation branches abandoned without producing output |
| System Interruptions | Context compaction events or API errors that derailed work mid-task |
| Missing Hooks | Recurring manual corrections that a PreToolUse hook would prevent |
| Direct SQL Access | DuckDB queries against raw JSONL for custom ad-hoc investigation |

## Improvement Outputs

Findings translate into five types of draft improvements:

- **Hook scripts** — PreToolUse, SubagentStart, SubagentStop, and Stop hooks that enforce
  correct behavior automatically
- **Agent prompt refinements** — Delegation prompts for the subagent-refactorer to fix specific
  misbehavior
- **Skill patches** — Delegation prompts for plugin-creator to fill knowledge gaps in existing
  skills
- **CLAUDE.md updates** — Exact markdown additions with evidence and rationale
- **Script automation proposals** — Replacement scripts for multi-step manual workflows

All outputs are proposals by default. Nothing is modified until you review and approve.

## Typical Workflow

```bash
# 1. Run full analysis on the current project
/agentskill-kaizen:analyze

# 2. Review the summary of findings
/agentskill-kaizen:report

# 3. Generate hooks for the top anti-patterns
/agentskill-kaizen:generate-hooks

# 4. Review drafts in .planning/kaizen/hooks/, then install when ready
/agentskill-kaizen:generate-hooks --install

# 5. Deep-dive on anything that needs more investigation
/agentskill-kaizen:explore
```

## Example

You run `/agentskill-kaizen:analyze` and the report shows:

```
Tool Misuse: 593 occurrences across 45 sessions — CRITICAL
  Finding: Bash used for file read operations (cat, grep, find)
  Evidence: Session abc123 line 456, Session def789 line 123
  Recommendation: PreToolUse hook to deny Bash file-op patterns
```

You run `/agentskill-kaizen:generate-hooks` and get a draft at
`.planning/kaizen/hooks/tool-misuse-prevention.md` containing a complete hook JSON
configuration and a JavaScript check script that blocks `cat`, `grep`, `find`, and `sed` from
running via Bash. After reviewing it, you run `--install` and the hook is active from the
next session.

## Components

| Component | Name | Purpose |
|-----------|------|---------|
| Command | `/agentskill-kaizen:analyze` | Full autonomous transcript analysis pipeline |
| Command | `/agentskill-kaizen:explore` | Interactive exploration with user steering |
| Command | `/agentskill-kaizen:report` | Summary from existing analysis files |
| Command | `/agentskill-kaizen:generate-hooks` | Translate findings into hook configurations |
| Agent | `transcript-analyst` | Deep SQL/process-mining analysis of JSONL transcripts — emits explicit `STATUS: DONE` block and `SendMessage` to team lead on completion |
| Agent | `improvement-generator` | Generates hooks, skill patches, CLAUDE.md updates — emits explicit `STATUS: DONE` block and `SendMessage` to team lead on completion |
| Skill | `transcript-analysis` | DuckDB query patterns, JSONL schema, process mining methodology |
| Skill | `kaizen-improvement` | Templates for improvement output generation |
| Skill | `meta-inspector` | Extracts specific data points from large transcripts and analysis reports without loading raw data into orchestrator context — orchestrator-invoked only |
| MCP Server | `kaizen-analysis` | FastMCP server: process mining, pattern detection, clustering, DuckDB queries |
| Dashboard | Panel/Bokeh | Live sentiment visualization; access via `open_dashboard` MCP tool |

## Structure

```text
plugins/agentskill-kaizen/
├── README.md
├── agents/
│   ├── improvement-generator.md
│   └── transcript-analyst.md
├── commands/
│   ├── analyze.md
│   ├── explore.md
│   ├── generate-hooks.md
│   └── report.md
├── mcp/
│   ├── dashboard.py          # Panel/Bokeh sentiment dashboard (daemon thread)
│   └── server.py             # FastMCP server: process mining, clustering, DuckDB
├── skills/
│   ├── agentskill-kaizen-meta-docs/
│   │   └── SKILL.md
│   ├── kaizen-improvement/
│   │   └── SKILL.md
│   ├── meta-inspector/
│   │   └── SKILL.md
│   └── transcript-analysis/
│       └── SKILL.md
└── tests/
    ├── conftest.py
    ├── test_dashboard.py
    └── test_server.py
```

## Requirements

- Claude Code CLI v2.0+
- `uv` — runs the process-mining MCP server and its dependencies
- `uvx` — runs the DuckDB MCP server
- Session transcripts in `~/.claude/projects/` — generated automatically by Claude Code

The first run downloads Python dependencies for the analysis server (fastmcp, pandas,
prefixspan). Subsequent runs use the cached environment.

## License

MIT

---

> **The Ancient Woe**
>
> *The stubborn general who loses the exact same battle in the exact same valley for three years running, learning nothing from the ghosts of his fallen cavalry.*

> **The Bard's Decree**
>
> *"Summon the seers to read the ashes of our past follies! Let us divine our blunders from the ledger, that we cease stepping upon the exact same rake in the orchard!"*
