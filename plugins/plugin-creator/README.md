<p align="center">
  <img src="./assets/hero.png" alt="Plugin Creator & Refactoring Toolkit" width="800" />
</p>

# Plugin Creator & Refactoring Toolkit

Complete toolkit for creating, refactoring, validating, and auditing Claude Code plugins, skills, agents, and hooks.

## Why Install This?

Building a Claude Code plugin involves a lot of moving parts: `plugin.json` schema rules, skill frontmatter constraints, agent configuration requirements, hook event wiring, and validation tooling. Without guidance, common mistakes include:

- Frontmatter that silently fails YAML parsing (multiline descriptions, unquoted colons, array fields that must be comma-separated strings)
- Skills that grow too large and get truncated from Claude's context budget
- Agents with weak description triggers that cause misrouting
- Hooks connected to the wrong events or written in the wrong language

This plugin gives Claude a complete reference for all of those systems plus agentic workflows to handle creation, validation, and refactoring.

## What You Get

### Commands

#### `/plugin-lifecycle`

Orchestrates the full plugin development lifecycle from a blank canvas to a marketplace-ready plugin.

```text
/plugin-lifecycle new <concept>
/plugin-lifecycle existing <plugin-path>
```

- `new <concept>` — Creates a plugin from scratch. Runs a prerequisite check (RT-ICA), user discussion, parallel research, design, atomic implementation, multi-layer validation, documentation, and final verification.
- `existing <plugin-path>` — Improves an existing plugin. Enters at the assessment phase, then proceeds through design, planning, and execution.

#### `/plugin-creator`

Focused new-plugin creation workflow. Runs discussion capture, parallel research, design with verification, and atomic implementation. Use this when creating a new plugin from scratch without the full lifecycle orchestration.

```text
/plugin-creator <plugin-concept>
```

#### `/skill-creator`

Guides through creating a new skill at any scope: plugin, project, or user level. Covers frontmatter schema, invocation control, progressive disclosure with `references/` directories, and validation.

```text
/skill-creator
```

After invoking, Claude will ask about the skill's purpose and guide through the creation process step by step. Scope choices: plugin (`plugins/{name}/skills/{skill-name}/`), project (`.claude/skills/{skill-name}/`), or user (`~/.claude/skills/{skill-name}/`).

#### `/agent-creator`

Creates Claude Code agent files from requirements. Handles discovery of existing agents, template selection, frontmatter generation, scope determination, and `plugin.json` updates.

```text
/agent-creator
```

Trigger phrases that activate this automatically: "create an agent", "add an agent to my plugin", "I need an agent for...".

#### `/hook-creator`

Creates hook scripts for Claude Code plugins. Enforces the mandatory constraints for production hooks: explicit `.cjs` or `.mjs` extension (never plain `.js`), `execFileSync` over `execSync`, `${CLAUDE_PLUGIN_ROOT}` path anchoring, correct `hookSpecificOutput` schema, and explicit timeouts.

```text
/hook-creator
```

Trigger phrases: "create a hook", "add a hook to my plugin", "build a PostToolUse hook", "I need a hook that...".

#### `/lint`

Runs the `skilllint` validator on a skill, agent, or plugin directory. Reports token complexity, broken links, frontmatter issues, and structural problems.

```text
/lint <path-to-skill-or-plugin>
```

#### `/refactor-plugin`

Starts a complete plugin refactoring workflow: assessment, design, task planning, and parallel agent execution.

```text
/refactor-plugin <plugin-path>
```

#### `/refactor-skill`

Assesses and refactors oversized or multi-domain skills. First determines whether splitting or `references/` extraction is appropriate — then executes the correct action. Preserves 100% of content and maintains backwards compatibility.

```text
/refactor-skill <path-to-skill-directory>
```

Use when `skilllint` reports SK006 (warning threshold) or SK007 (error threshold) on a skill.

#### `/assessor`

Analyzes a plugin's structure, scores its quality, and generates a phased refactoring plan with design map and task files.

```text
/assessor <plugin-name>
```

#### `/implement-refactor`

Executes refactoring tasks from a task file created by `/assessor`. Reads task files, resolves dependencies, delegates to specialist agents, and tracks completion with parallel orchestration.

```text
/implement-refactor <plugin-slug or task-file-path>
```

#### `/ensure-complete`

Validates that a completed refactoring achieved its goals. Checks improvement against the original assessment score, looks for documentation drift, and creates follow-up task files if issues remain.

```text
/ensure-complete <task-file-path>
```

#### `/start-refactor-task`

Picks up a specific refactoring task from a task file, updates its status, implements acceptance criteria, and runs verification steps. Used by sub-agents during parallel refactoring execution.

```text
/start-refactor-task <task-file-path> [--task <task-id>] [--complete <task-id>]
```

#### `/add-doc-updater`

Adds an automated documentation sync pipeline to any skill that wraps external documentation (API references, CLI docs, framework docs). Creates a Python script that downloads upstream docs, processes markdown for AI consumption, and enforces a configurable refresh cooldown.

```text
/add-doc-updater <target-plugin-or-skill-path>
```

#### `/skill-sync`

Updates a skill's content against its cited upstream sources. Use this when a skill references live documentation via `SOURCE:` URLs and that documentation has changed — new API methods added, configuration options renamed, behaviour changed — and you want to bring the skill current without touching its structure or rewriting things that are still accurate.

```text
/skill-sync <skill-path>
/skill-sync <plugin-directory-path>
```

When given a plugin directory, runs on every skill within it. The pipeline:

1. **Token profile** — runs `uvx skilllint` on the existing file and surfaces which 2–3 sections consume the most tokens, so the write step knows its budget before touching anything. If the file is already over the SK007 threshold, applies progressive-disclosure extraction (`references/` split) before proceeding.
2. **Three parallel read agents** — completeness auditor (scores quality, checks token budget), upstream drift researcher (fetches every `SOURCE:` URL in the skill and classifies each claim as NEW, STALE, VERIFIED, or UNVERIFIABLE), structure validator (checks YAML syntax, citations, code fence specifiers, derived counts).
3. **Change plan** — synthesizes all three reports into a change plan file written to `.tmp/scratch/plans/`. The write step receives only this file — it invents nothing.
4. **Write + verify** — a schema-aware write agent executes the change plan exactly, then runs `uvx skilllint` after each file touch. If SK007 fires during writing, the agent extracts the heaviest section to `references/` and retries until the skill is clean.

The pipeline does not pause for review and does not manage commits — it exits after `uvx skilllint` passes on all modified files.

#### `/audit-agent-lifecycle`

Validates that agents can actually accomplish what they claim to do. Runs 8 semantic audits: capability vs configuration alignment, skill loading correctness, inter-agent contracts, prompt contradictions, tool sufficiency, dead agents, scriptable patterns, and pattern learning. Writes reports to `.claude/audits/`.

```text
/audit-agent-lifecycle <plugin-path>
```

#### `/audit-skill-lifecycle`

Deep semantic validation of how skills interconnect. Traces call chains, detects circular dependencies, finds instruction contradictions, identifies duplicated datasets, and discovers scriptable sequences. Generates audit reports to `.claude/audits/`.

```text
/audit-skill-lifecycle <plugin-path>
```

#### `/audit-skill-completeness`

Evaluates a single skill's quality against 8 completeness categories derived from Anthropic's official skills repository. Scores preparation, progression, verification, scripts, examples, anti-patterns, references, and assets (0-3 per category). Generates a scored report.

```text
/audit-skill-completeness <skill-path>
```

#### `/agent-capability-analyzer`

Runs the description-drift experiment: spawns all Claude Code agents simultaneously to collect self-reported capabilities, then compares them against static frontmatter descriptions. Use to measure how reliable orchestrator routing based on descriptions actually is.

#### `/optimize-claude-md`

Optimizes CLAUDE.md files, SKILL.md files, agent definitions, and other AI-facing files for Claude comprehension. Measures baseline metrics, runs optimization via the `ai-doc-optimizer` agent, verifies with a second agent, then presents a before/after report.

```text
/optimize-claude-md <file-or-directory-path>
```

Only runs when you invoke it directly — Claude will not trigger this automatically.

#### `/optimize`

Guides writing lean AI-facing instructions. Flags content that Claude does not need: discoverable data, over-explained concepts, invented constraints, duplicated content, and stale cached facts.

#### `/write-frontmatter-description`

Writes or rewrites frontmatter `description` fields for skills and agents. Enforces single-line format, no YAML multiline indicators, no bare colons, front-loaded critical information, and trigger keywords for tool selection. Use when a description exceeds 1024 characters or fails validation.

#### `/mission-statement`

Defines a plugin mission statement — purpose, values, anti-patterns, and trade-offs. Produces `mission.json` with `[draft]` status and creates a backlog interview task for refinement. Use when creating a new plugin or auditing alignment.

```text
/mission-statement <plugin-path>
```

#### `/rt-ica` (moved to development-harness)

This skill has moved to the `development-harness` plugin. Use `/dh:rt-ica` instead.

Mandatory pre-planning checkpoint (Reverse Thinking — Information Completeness Assessment). Blocks planning until all prerequisites are verified. Use before creating plans, delegating to agents, or defining acceptance criteria.

#### `/memory-and-rules`

Reference for configuring Claude Code persistent memory: `CLAUDE.md` files, auto memory, `.claude/rules/` directories, memory hierarchy, and best practices for each scope level.

#### `/review-permissions`

Reference for configuring Claude Code permissions: tool approval rules, permission modes, managed policies, and sandboxing. Covers allow/deny/ask policies for Bash, Read, Edit, WebFetch, MCP, and Agent tools.

### Reference Skills

These load automatically when Claude needs them, or you can invoke them directly for reference.

| Skill | What it provides |
|---|---|
| `/claude-skills-overview-2026` | Complete Claude Code skills system reference — frontmatter schema, invocation control, context fork, hooks in skills, token budget |
| `/claude-plugins-reference-2026` | Complete Claude Code plugins system reference — `plugin.json` schema, all component types, marketplace format, CLI commands |
| `/hooks-guide` | Cross-platform hooks reference for Claude Code, GitHub Copilot, Cursor, Windsurf, and Amp |
| `/hooks-core-reference` | Claude Code hook system fundamentals — all events, matchers, environment variables, execution behavior, debugging |
| `/hooks-io-api` | Hook JSON input/output API — what data hooks receive via stdin, what JSON they return to control Claude Code behavior |
| `/hooks-patterns` | Hook recipes and working examples in Python and Node.js |
| `/agentskills` | Agent Skills Open Standard (agentskills.io) — portable skill format for Claude Code, Cursor, Gemini CLI, and 20+ other agents |
| `/prompt-optimization` | Principles for optimizing CLAUDE.md files and skills for Claude Code |
| `/command-development` | Legacy `.claude/commands/` format — frontmatter fields, argument syntax, bash execution, AskUserQuestion patterns, workflow locking |
| `/mcp-integration` | MCP server configuration within plugins — stdio/SSE/HTTP/WebSocket types, authentication, tool naming, lifecycle, security |
| `/plugin-settings` | Per-project plugin configuration via `.local.md` — YAML frontmatter parsing from hooks, configuration-driven behavior patterns |
| `/component-patterns` | Component lifecycle and decision framework — when to use commands vs skills vs agents vs hooks vs MCP servers |

### Claude Improvements

With this plugin installed, Claude will:

- Recognize when you describe a plugin, skill, agent, or hook and activate the appropriate creation workflow automatically
- Validate frontmatter before writing it, catching YAML syntax errors, forbidden multiline indicators, and incorrect field types
- Use the correct tool format for agent and skill `tools` fields (comma-separated strings, not arrays)
- Write hook scripts in the language that matches the project runtime (Node.js by default; Python when `pyproject.toml` is present); for Node.js always use `.mjs` or `.cjs` — never plain `.js` (see [hooks-nodejs-extension.md](./skills/hooks-guide/references/hooks-nodejs-extension.md))
- Apply the `${CLAUDE_PLUGIN_ROOT}` environment variable in hook paths rather than hardcoding absolute paths
- Check skill complexity with token-based thresholds and recommend `references/` extraction or splitting before a skill exceeds Claude's context budget
- Route refactoring task types to the correct specialist: `SKILL_SPLIT` tasks to `/refactor-skill`, `AGENT_OPTIMIZE` tasks to the `subagent-refactorer` agent, `DOC_IMPROVE` tasks to the `ai-doc-optimizer` agent
- Require `name:` in all skill and agent frontmatter per the agentskills.io specification

### Automatic Behaviors

- **On every git commit**: The `auto-sync-manifests` pre-commit hook detects component changes (skills, agents, commands), updates `plugin.json` component arrays, bumps the plugin version (major for deletion, minor for addition, patch for modification), and updates `marketplace.json`. No manual version management required.

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install plugin-creator@jamie-bitflight-skills
```

## Usage

### Create a new plugin from scratch

```bash
/plugin-lifecycle new "a plugin that helps with Terraform infrastructure reviews"
```

Claude will run prerequisite checks, discuss requirements with you, conduct parallel research, design the plugin structure, implement components, validate everything, and produce a marketplace-ready plugin.

### Create a new agent

```bash
/agent-creator
```

Or just say "create an agent that reviews pull requests for security issues" and Claude will activate the workflow automatically.

### Validate a plugin before committing

```bash
/lint ./plugins/my-plugin
```

Or use the CLI directly:

```bash
uvx skilllint@latest check ./plugins/my-plugin
uvx skilllint@latest check --fix ./plugins/my-plugin
```

Auto-fix handles: YAML arrays converted to comma-separated strings, multiline descriptions collapsed to single lines, and unquoted colons in description values.

### Refactor an oversized skill

```bash
/refactor-skill ./plugins/my-plugin/skills/my-large-skill
```

Claude will assess whether the skill needs splitting (multiple independent domains) or `references/` extraction (single domain, oversized). If splitting is warranted, it produces new focused SKILL.md files and converts the original to a facade skill for backwards compatibility.

### Full plugin refactoring workflow

```bash
/assessor my-plugin
# Review the assessment report and task plan
/implement-refactor my-plugin
# After all tasks complete:
/ensure-complete .claude/plan/tasks-refactor-my-plugin.md
```

## Validation Reference

### What `skilllint` checks

- YAML syntax validity
- No forbidden multiline indicators (`>-`, `|-`)
- Required fields present (`name` and `description` for agents; `name` for plugin skills)
- Field types match schema (string, bool, object)
- `tools` and `skills` fields are comma-separated strings, not arrays
- Token-based skill complexity (SK006: warning, SK007: must split)
- Internal markdown link validity

### What `claude plugin validate` checks

- `plugin.json` exists in `.claude-plugin/`
- JSON syntax is valid
- Required field `name` is present and kebab-case
- All paths start with `./`
- `agents` field is an array of individual file paths, not a directory string
- Referenced files exist

### Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| Skill not appearing as slash command | Missing `name:` field | `skilllint --fix` adds it from directory name |
| `agents: Invalid input` | Used directory string instead of array | Change `"agents": "./agents/"` to `["./agents/file.md"]` |
| Description shows as `>-` | YAML multiline indicator | `skilllint --fix` collapses to single line |
| Hook not firing | Script not executable | `chmod +x scripts/my-hook.mjs` (or `.cjs`/`.py`) |
| Path errors after install | Used `../` traversal | Use `${CLAUDE_PLUGIN_ROOT}` or symlinks |

## Agents

These agents run internally to implement the skills above. They are not invoked directly.

| Agent | Purpose |
|---|---|
| `refactor-planner` | Analyzes plugin structure and creates refactoring plans |
| `refactor-executor` | Executes refactoring tasks from plans with parallel orchestration |
| `refactor-validator` | Validates refactoring completeness and quality against original assessment |
| `subagent-refactorer` | Rewrites agent prompt files using Anthropic prompt engineering methodology — strategic XML tagging, strong imperative instructions, model-tier selection |
| `skill-auditor` | Read-only quality audit and completeness scoring for agents, skills, and CLAUDE.md files |
| `skill-content-updater` | Sync skill content against upstream sources — fetch live docs, classify drift (NEW/STALE/VERIFIED), apply updates |
| `ai-doc-optimizer` | Content optimization and frontmatter description writing for prompts, SKILL.md, and CLAUDE.md files |
| `plugin-assessor` | Analyzes plugins for structure, frontmatter compliance, orphaned files, and cross-reference validity |
| `hook-creator` | Generates hook scripts (Node.js `.mjs`/`.cjs` by default, Python or other language when matching project runtime), wires `hooks.json` |
| `agent-creator` | Creates agent files from requirements with template selection and plugin.json updates |

### The three documentation-work agents

These three agents replaced `contextual-ai-documentation-optimizer`, which bundled all documentation concerns under a single agent that was easy to misroute. Each agent now has a single scope so orchestrators and skill authors can route precisely.

**`skill-auditor`** — Use when you want to know how complete or well-structured a skill is, without changing anything. The agent runs entirely read-only: it scores the skill against 8 completeness categories, checks whether the file is approaching the SK006/SK007 token thresholds, checks progressive-disclosure structure, and reports all gaps in a structured audit report at `.tmp/scratch/reports/skill-sync-{slug}-completeness-YYYYMMDD.md`. Nothing is written to the skill itself. Route here when a human or orchestrator asks "how good is this skill?" or "what's missing from this skill?" — not when the goal is to fix something.

**`skill-content-updater`** — Use when a skill's cited sources have drifted and you need to bring content current. The agent has two roles in the `/skill-sync` pipeline: in Stage 2 it fetches every `SOURCE:` URL cited in the skill and classifies each claim as NEW (exists upstream, absent from skill), STALE (changed or removed upstream), VERIFIED (matches), or UNVERIFIABLE (URL unreachable); in Stage 5 it receives a change plan file path and executes it exactly — no interpretation, no content invention. Route here when the goal is "sync this skill against what the upstream docs actually say today", not when the goal is "make this skill's prose clearer".

**`ai-doc-optimizer`** — Use when the skill's content is current but needs to be clearer, better structured, or more useful for Claude to follow. The agent rewrites for comprehension: tightens instruction language, applies RT-ICA and CoVe patterns, improves structure and progressive disclosure, and rewrites `description` frontmatter fields to front-load trigger keywords. Route here when the goal is "make this skill work better as AI-facing instruction", not when the goal is "add what's missing from the upstream docs".

Routing by concern:

- Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `ai-doc-optimizer` agent (`plugin-creator:ai-doc-optimizer`)
- Audit quality (read-only, no writes, score against completeness categories) → `skill-auditor` agent (`plugin-creator:skill-auditor`)
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `skill-content-updater` agent (`plugin-creator:skill-content-updater`)
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly

## Scripts

| Script | Purpose | Usage |
|---|---|---|
| `create_plugin.py` | Interactive plugin scaffolding | `uv run plugins/plugin-creator/scripts/create_plugin.py` |
| `fix_tool_formats.py` | Fix invalid tool field formats across the codebase | `uv run plugins/plugin-creator/scripts/fix_tool_formats.py` |
| `auto_sync_manifests.py` | Pre-commit hook — syncs plugin.json and bumps versions | Runs automatically on `git commit` |
| `validate-task-file.sh` | Validate refactoring task file format | `./plugins/plugin-creator/scripts/validate-task-file.sh <path>` |

## Requirements

- Claude Code v2.0+
- `uvx` available (for running `skilllint`)
- `uv` available (for running Python scripts)
- Node.js available (for hook scripts at runtime)

## License

MIT License, with the exception of the `skill-creator` skill which retains its original Apache License 2.0 (sourced from [anthropics/skills](https://github.com/anthropics/skills)). See `skills/skill-creator/LICENSE.txt`.

---

**Author**: Jamie Nelson — [github.com/bitflight-devops](https://github.com/bitflight-devops)
