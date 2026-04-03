<p align="center">
  <img src="./assets/hero.png" alt="agentskill-kaizen" width="800" />
</p>

# agentskill-kaizen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-blueviolet.svg)](https://claude.ai/code)

Analyze Claude Code session transcripts to find inefficiencies, anti-patterns, and repeated
mistakes, then generate fixes automatically.

## Quick Start

Invoke the commands with a task on the same line:

```
/agentskill-kaizen:analyze find tool misuse patterns
/agentskill-kaizen:explore show me where I keep repeating the same mistakes
/agentskill-kaizen:report summarize findings from the most recent analysis
/agentskill-kaizen:generate-hooks create hooks for the top three anti-patterns
```

## Features

- Analyzes JSONL session transcripts with SQL (DuckDB) and process-mining algorithms
- Detects ten anti-pattern dimensions: tool misuse, repeated errors, user frustration, delegation
  gaps, and more
- Generates actionable outputs: hook scripts, skill patches, CLAUDE.md updates, and automation
  proposals
- All outputs are draft proposals by default — nothing is modified until you review and approve

## Installation

### From Marketplace

Add the marketplace (one-time setup):

```bash
claude plugin marketplace add jamie-bitflight-skills/claude_skills
```

Install the plugin:

```bash
claude plugin install agentskill-kaizen@jamie-bitflight-skills
```

### Local Development

```bash
claude --plugin-dir ./plugins/agentskill-kaizen
```

## Prerequisites

- Claude Code CLI v2.0+
- `uv` installed (runs the process-mining MCP server and its dependencies)
- `uvx` installed (runs the DuckDB MCP server)
- Session transcripts in `~/.claude/projects/` — generated automatically by Claude Code during
  normal use

The first run downloads Python dependencies for the analysis server (fastmcp, pm4py, pandas,
prefixspan, scikit-learn). Subsequent runs use the cached environment.

## Components

| Component | Name | Purpose |
|-----------|------|---------|
| Command | `/agentskill-kaizen:analyze` | Full autonomous transcript analysis pipeline |
| Command | `/agentskill-kaizen:explore` | Interactive exploration with user steering |
| Command | `/agentskill-kaizen:report` | Summary from existing analysis files |
| Command | `/agentskill-kaizen:generate-hooks` | Translate findings into hook configurations |
| Agent | `transcript-analyst` | Deep SQL/process-mining analysis of JSONL transcripts |
| Agent | `improvement-generator` | Generates hooks, skill patches, CLAUDE.md updates |
| Skill | `transcript-analysis` | DuckDB query patterns, JSONL schema, PM4Py methodology |
| Skill | `kaizen-improvement` | Templates for improvement output generation |
| MCP Server | `kaizen-analysis` | FastMCP server: `get_transcript_jsonl_schema`, resource `kaizen://session-log/schema`, process mining, pattern detection, clustering |
| Dashboard | Panel/Bokeh dashboard | Live sentiment visualization served at OS-assigned port; access via `open_dashboard` MCP tool |

## Usage

### Slash Commands

```
/agentskill-kaizen:analyze
/agentskill-kaizen:analyze --project -home-user-repos-myproject
/agentskill-kaizen:analyze --dimensions tool-misuse,errors,frustration

/agentskill-kaizen:explore
/agentskill-kaizen:explore --project -home-user-repos-myproject

/agentskill-kaizen:report
/agentskill-kaizen:report --latest
/agentskill-kaizen:report --all

/agentskill-kaizen:generate-hooks
/agentskill-kaizen:generate-hooks --install
/agentskill-kaizen:generate-hooks --from .planning/kaizen/analysis-2026-02-18.md
```

### Agent Triggering

The plugin's agents can be addressed directly during an orchestrated task:

```
Delegate to transcript-analyst to analyze session transcripts for tool misuse patterns.
Delegate to improvement-generator to produce hook configurations from the analysis report.
```

### Skill Activation

```
/agentskill-kaizen:transcript-analysis
/agentskill-kaizen:kaizen-improvement
```

## What the Analysis Covers

Ten dimensions are analyzed across your session history:

| Dimension | What it finds |
|-----------|---------------|
| Tool Misuse | Bash calls used for file read/write/search instead of built-in tools |
| Repeated Errors | Edit-before-Read patterns, stale edits, denied tool calls |
| User Frustration | Corrections, denials, interrupts, "you keep doing this" signals |
| Tooling Gaps | Multi-step sequences that repeat identically and could be a single script |
| Delegation Patterns | Whether Claude uses specialist agents or defaults to general-purpose |
| Shortest Path | Wasted steps when the same goal was reached faster in other sessions |
| Red Herrings | Investigation branches that were abandoned without producing output |
| System Interruptions | Context compaction events or API errors that derailed work mid-task |
| Missing Hooks | Recurring manual corrections that a PreToolUse hook would prevent |
| Direct SQL Access | DuckDB queries against raw JSONL for custom ad-hoc investigation |

## Improvement Outputs

Findings translate into five types of improvements:

- **Hook scripts** — PreToolUse, SubagentStart, SubagentStop, and Stop hooks that enforce correct
  behavior automatically
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

You run `/agentskill-kaizen:generate-hooks` and get a draft hook at
`.planning/kaizen/hooks/tool-misuse-prevention.md` containing a complete hook JSON configuration
and a JavaScript check script that blocks `cat`, `grep`, `find`, and `sed` from running via
Bash. After reviewing it, you run `--install` and the hook is active from the next session.

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
- `uv` installed (process-mining MCP server dependencies)
- `uvx` installed (DuckDB MCP server)
- Session transcripts in `~/.claude/projects/`

## License

MIT

---

> **The Ancient Woe**
>
> *The stubborn general who loses the exact same battle in the exact same valley for three years running, learning nothing from the ghosts of his fallen cavalry.*

> **The Bard's Decree**
>
> *"Summon the seers to read the ashes of our past follies! Let us divine our blunders from the ledger, that we cease stepping upon the exact same rake in the orchard!"*
