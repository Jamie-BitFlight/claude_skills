---
name: hooks-guide
description: Cross-platform hooks reference for AI coding assistants — Claude Code, GitHub Copilot, Cursor, Windsurf, Amp. Covers hook authoring in Node.js CJS and Python, per-platform event schemas, inline-agent hooks and MCP in agent frontmatter, common JSON I/O, exit codes, best practices, and a fetch script to refresh docs from official sources. Use when writing, reviewing, or debugging hooks for any AI assistant.
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

## Route to Reference

```mermaid
flowchart TD
    Start([What do you need?]) --> Q1{Which platform?}
    Q1 -->|Claude Code| Q2{Inline agent hooks<br>hooks/mcpServers/skills/memory?}
    Q1 -->|GitHub Copilot| Copilot["Read references/github-copilot.md"]
    Q1 -->|Cursor, Windsurf, Amp<br>or coverage gaps| Coverage["Read references/platform-coverage.md"]

    Q2 -->|Yes — agent frontmatter| Agent["Read references/inline-agent-hooks.md"]
    Q2 -->|No — project or global hooks| Q3{Interacts with session data?<br>costs, workloads, duration, tracking}

    Q3 -->|Yes — reading or writing<br>session logs or token data| SessionSchema["Load references/claude-session-log-schema-reference.md<br>before writing any code"]
    Q3 -->|No| Q4{Which language?}

    SessionSchema --> Q4

    Q4 -->|Node.js CJS| CJS["Read references/hooks-cjs.md"]
    Q4 -->|Python| Py["Read references/hooks-python.md"]
    Q4 -->|Not sure / both| Both["Read references/hooks-cjs.md<br>then references/hooks-python.md"]

    Agent --> CC["Also read references/claude-code.md<br>for full event schema"]
    Q4 --> Schema["Cross-platform concepts:<br>references/common-schema.md"]
    Copilot --> Schema
    Coverage --> Schema
```

## Specialist Skills

For deeper Claude Code coverage, these focused skills are available:

- **hooks-core-reference** — Hook system fundamentals: events, configuration, matchers, environment variables, execution, security, debugging. Use `Skill(skill: "plugin-creator:hooks-core-reference")` for configuration and troubleshooting.
- **hooks-io-api** — JSON input/output API: what data hooks receive via stdin and what JSON they return to control Claude. Use `Skill(skill: "plugin-creator:hooks-io-api")` for writing hook scripts that process input or produce JSON output.
- **hooks-patterns** — Recipes and working examples: plugin hooks, frontmatter hooks, prompt-based hooks, complete code examples in Python/Node.js. Use `Skill(skill: "plugin-creator:hooks-patterns")` for implementation patterns and examples.

## Reference Files

- `references/common-schema.md` — shared concepts, cross-platform comparison, JSON I/O, exit codes
- `references/claude-code.md` — Claude Code hooks full reference (events, matchers, configuration)
- `references/inline-agent-hooks.md` — hooks, mcpServers, skills, and memory in agent frontmatter
- `references/github-copilot.md` — GitHub Copilot coding agent hooks
- `references/hooks-cjs.md` — Node.js CJS authoring guide and templates
- `references/hooks-python.md` — Python authoring guide and templates
- `references/best-practices.md` — cross-platform conventions and anti-patterns
- `references/platform-coverage.md` — known platforms, fetch URLs, coverage status
- `references/hooks-lifecycle.png` — visual diagram of the full hook event sequence
- `references/claude-session-log-schema-reference.md` — verified schema for Claude Code session JSONL logs: file locations, record structure, tool_use/tool_result pairing, usage fields, observed response sizes. Load when creating or modifying hooks that interact with session data for costs, workloads, duration, or tracking.

## Refresh Docs

Re-fetch all platform docs and re-run the rwr:doc-to-skill transform on each:

```bash
bash plugins/plugin-creator/skills/hooks-guide/scripts/fetch-and-transform-hooks-docs.sh
```

This updates reference files from official sources. Run when upstream docs change.

## Sources

- Claude Code hooks: `https://docs.anthropic.com/en/docs/claude-code/hooks.md` (accessed 2026-02-27)
- Claude Code agent frontmatter: `https://docs.anthropic.com/en/docs/claude-code/sub-agents.md` (accessed 2026-02-27)
- GitHub Copilot coding agent: `https://docs.github.com/en/copilot/using-github-copilot/using-claude-as-your-copilot-llm` (accessed 2026-02-27)
