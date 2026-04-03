# Compound Engineering Plugin

## Overview

The Compound Engineering Plugin is a comprehensive AI-powered development toolkit designed for Claude Code and other AI coding assistants (Cursor, OpenCode, Codex, GitHub Copilot, Gemini CLI, Windsurf, and others). It implements a philosophy where "each unit of engineering work should make subsequent units easier—not harder" by emphasizing planning, review, knowledge codification, and systematic execution.

Published as `@every-env/compound-plugin` on npm. Latest version: **2.61.0** (released 2026-04-01). License: MIT.

**Homepage**: <https://every.to/source-code/my-ai-had-already-fixed-the-code-before-i-saw-it>
**Repository**: <https://github.com/EveryInc/compound-engineering-plugin>
**Author**: Kieran Klaassen and Every Inc.

## Problem Addressed

Traditional software development accumulates technical debt incrementally — each feature adds complexity, making the codebase progressively harder to work with over time. The Compound Engineering Plugin inverts this dynamic by implementing a workflow philosophy where "80% is in planning and review, 20% is in execution."

The plugin surfaces specific problems it solves:

1. **Inadequate planning before code execution** — lack of structured requirements exploration
2. **Code review quality and consistency** — missing specialized review perspectives and coverage gaps
3. **Knowledge loss after solving problems** — learnings not codified for future reuse
4. **Fragmented multi-platform AI coding tool adoption** — developers must reinvest skill/agent setup per tool
5. **Difficulty extending agents and skills** — cross-platform conversion overhead

## Key Statistics

- **Agents**: 35+ specialized agents organized by discipline (review, document-review, research, design, workflow, docs)
- **Skills**: 40+ skills including 7 core workflow commands (`/ce:brainstorm`, `/ce:plan`, `/ce:review`, `/ce:work`, `/ce:compound`, `/ce:ideate`, `/ce:compound-refresh`)
- **Plugin version**: 2.61.0 (released 2026-04-01)
- **CLI version**: linked to plugin version via `linked-versions` release automation
- **Active development**: ~30 commits per version cycle across planning, review, and workflow refinement
- **Multi-platform support**: Claude Code (primary), Cursor, OpenCode, Codex, GitHub Copilot, Gemini CLI, Droid, Pi, Kiro, Windsurf, OpenClaw, Qwen

## Key Features

### Core Workflow (Slash Commands)

Extracted from `plugins/compound-engineering/README.md`:

| Command | Purpose |
|---------|---------|
| `/ce:ideate` | "Discover high-impact project improvements through divergent ideation and adversarial filtering" |
| `/ce:brainstorm` | "Explore requirements and approaches before planning" with interactive Q&A and automatic ceremony-shortcutting |
| `/ce:plan` | "Transform features into structured implementation plans grounded in repo patterns, with automatic confidence checking" |
| `/ce:review` | "Structured code review with tiered persona agents, confidence gating, and dedup pipeline" |
| `/ce:work` | "Execute work items systematically" with worktree and task tracking |
| `/ce:compound` | "Document solved problems to compound team knowledge" |
| `/ce:compound-refresh` | "Refresh stale or drifting learnings and decide whether to keep, update, replace, or archive them" |

**Design**: Each skill acts as a progressive refinement stage. `/ce:brainstorm` is the primary entry point that "refines ideas into a requirements plan through interactive Q&A, and short-circuits automatically when ceremony isn't needed." Plans inform subsequent work cycles.

### Agent Architecture

**Organization by discipline** (from `plugins/compound-engineering/README.md`):

**Review Agents** (code review specialists):
- `adversarial-reviewer` — "Construct failure scenarios to break implementations across component boundaries"
- `correctness-reviewer` — "Logic errors, edge cases, state bugs"
- `security-reviewer` — "Exploitable vulnerabilities with confidence calibration"
- `performance-reviewer` — "Runtime performance with confidence calibration"
- `testing-reviewer` — "Test coverage gaps, weak assertions"
- `data-migrations-reviewer` — "Migration safety with confidence calibration"
- `architecture-strategist` — "Analyze architectural decisions and compliance"
- Plus 20+ language-specific and domain-specific review personas (DHH Rails style, Kieran Python/TypeScript/Rails, frontend race conditions, etc.)

**Document Review Agents** (plan and requirements review):
- `coherence-reviewer` — "Review documents for internal consistency, contradictions, and terminology drift"
- `feasibility-reviewer` — "Evaluate whether proposed technical approaches will survive contact with reality"
- `product-lens-reviewer` — "Challenge problem framing, evaluate scope decisions, surface goal misalignment"
- `security-lens-reviewer` — "Evaluate plans for security gaps at the plan level (auth, data, APIs)"
- `adversarial-document-reviewer` — "Challenge premises, surface unstated assumptions, and stress-test decisions"

**Research Agents** (knowledge gathering):
- `learnings-researcher` — "Search institutional learnings for relevant past solutions"
- `best-practices-researcher` — "Gather external best practices and examples"
- `framework-docs-researcher` — "Research framework documentation and best practices"
- `git-history-analyzer` — "Analyze git history and code evolution"
- `repo-research-analyst` — "Research repository structure and conventions"

**Design Agents**:
- `design-implementation-reviewer` — "Verify UI implementations match Figma designs"
- `design-iterator` — "Iteratively refine UI through systematic design iterations"
- `figma-design-sync` — "Synchronize web implementations with Figma designs"

**Workflow Agents** (execution support):
- `bug-reproduction-validator` — "Systematically reproduce and validate bug reports"
- `pr-comment-resolver` — "Address PR comments and implement fixes"
- `spec-flow-analyzer` — "Analyze user flows and identify gaps in specifications"
- `lint` — "Run linting and code quality checks on Ruby and ERB files"

**Data flow**: Skills invoke agents via tool dispatch. Skills orchestrate multi-agent review pipelines (e.g., `/ce:review` routes to tiered review agents with confidence gating and dedup). Agents operate independently but follow structured schemas — review agents emit structured JSON with confidence scores, document-review agents return role-specific feedback, research agents return findings with sources.

### Extensibility Mechanisms

**Multi-platform conversion** — The plugin ships a Bun/TypeScript CLI that converts Claude Code plugins to other agent platforms:

```
bunx @every-env/compound-plugin install compound-engineering --to <target>
```

**Supported targets** (extracted from README):
- `opencode` — Commands as `.md` files, `opencode.json` deep-merged
- `codex` — Claude commands become prompt + skill pairs
- `droid` — Tool names mapped (`Bash`→`Execute`, `Write`→`Create`)
- `pi` — Prompts, skills, extensions, and `mcporter.json` for interop
- `gemini` — Skills from agents, commands as `.toml`
- `copilot` — Agents as `.agent.md` with Copilot frontmatter, MCP env vars prefixed
- `kiro` — Agents as JSON configs, only stdio MCP servers supported
- `windsurf` — Skills, commands as workflows, `mcp_config.json` merged
- `qwen` — Agents as `.yaml`, env vars with placeholders extracted as settings
- `openclaw` — TypeScript skill files, `openclaw-extension.json` for MCP

**Personal config sync**:

```
bunx @every-env/compound-plugin sync --target <provider>
```

Syncs `~/.claude/skills/`, `~/.claude/commands/`, and MCP servers from `~/.claude/settings.json` to other tools.

**Skill authoring patterns** — Skills organize as:
- Core workflow skills with `/ce:*` slash commands
- Domain-specific skills (git, testing, frontend, Ruby gems, DSPy)
- Utility skills (todos, testing, automation)
- Beta/experimental skills with `-beta` suffix

Reference files are split into `references/` (large, optional) and inlined via `@` syntax when <150 lines and unconditionally needed.

### Representative Skill: `/ce:review`

Extracted from plugin code and README:

- **Phases**: Invokes tiered review agents (rule-based, persona-based, deepening) with confidence scoring
- **Confidence gating**: Suppresses false positives, requires high confidence for blocking issues
- **Dedup pipeline**: Consolidates duplicate findings across agent instances
- **Table format requirement**: Enforces structured table output for readability
- **Question tool integration**: Requires native question tool for user interaction (platform-agnostic fallback: numbered options)
- **Output**: Structured markdown review with: issues by severity, confidence scores, previous comments integration, next steps menu

### Representative Skill: `/ce:plan`

- **Phases**: Requirements research, plan generation, document review, confidence gating, deepening on demand
- **Confidence checking**: Auto-detects gaps (scope, metrics, success criteria, testing) and enforces review gate
- **Interactive deepening**: Users request deepening on specific sections without full re-planning
- **Document review**: Routes passing confidence checks to document-review agent for role-specific feedback
- **Output**: Markdown implementation plan with: phase breakdown, success metrics, testing strategy, known limitations, task decomposition

## Technical Architecture

### CLI Entry Point and Conversion Pipeline

**Location**: `src/index.ts` (Bun/TypeScript)

**Command structure**:
```bash
bunx @every-env/compound-plugin <command> [args]
```

**Commands** (extracted from package.json scripts):
- `dev` — Local development (run CLI directly)
- `convert` — Convert plugin between formats
- `list` — List available plugins/targets
- `cli:install` — Install plugin to specified target
- `release:preview` — Preview release changes
- `release:validate` — Validate plugin/marketplace consistency

**Conversion architecture**:
- `src/parsers/` — Parse Claude Code plugin structure (`claude.ts`, `claude-home.ts`)
- `src/types/` — Target-specific type definitions (one per platform: `opencode.ts`, `codex.ts`, `copilot.ts`, etc.)
- `src/converters/` — Transform Claude types to target types
- `src/targets/` — Writer modules for each platform (generate platform-specific output)

**Data flow**: Parse plugin → detect target → convert types → write target-specific structure → merge MCP/config files

### Plugin Structure

**Directory layout** (from `plugins/compound-engineering/`):
```
agents/
├── review/              # Code review agents (20+ files)
├── document-review/     # Plan/requirements review (7 files)
├── research/            # Knowledge gathering (5 files)
├── design/              # UI/design agents (3 files)
├── workflow/            # Execution support (4 files)
└── docs/                # Documentation (1 file)

skills/
├── ce-brainstorm/       # Core workflow
├── ce-compound/
├── ce-ideate/
├── ce-plan/
├── ce-review/
├── ce-work/
├── ce-compound-refresh/
├── git-clean-gone-branches/
├── git-commit/
├── ... (40+ skills)
└── (each has SKILL.md, references/, assets/, scripts/)
```

**Agent dispatch** — Skills invoke agents via named agent references: `compound-engineering:<category>:<agent-name>` (fully-qualified namespace to prevent resolution conflicts when multiple plugins are installed).

### Plugin Manifest

**File**: `.claude-plugin/plugin.json` (for compound-engineering plugin)

```json
{
  "name": "compound-engineering",
  "version": "2.61.0",
  "description": "AI-powered development tools for code review, research, design, and workflow automation.",
  "author": { "name": "Kieran Klaassen", "email": "kieran@every.to", "url": "https://github.com/kieranklaassen" },
  "license": "MIT",
  "homepage": "https://every.to/source-code/my-ai-had-already-fixed-the-code-before-i-saw-it",
  "repository": "https://github.com/EveryInc/compound-engineering-plugin",
  "keywords": [...]
}
```

**Version synchronization**: CLI and plugin versions are **linked** via `linked-versions` release-please plugin. A release with only plugin changes still bumps CLI version (and vice versa) to keep them in sync.

### Conversion Architecture Details

**Mapping strategies** (extracted from code structure):

1. **Agent conversion**: Claude agents (Markdown frontmatter + prompt) → target format
   - Codex: `prompt + skill pair`
   - Copilot: `.agent.md` with Copilot frontmatter
   - Gemini: agent name + description → skill
   - Kiro: JSON config + prompt `.md`
   - Windsurf: agent → skill + workflow

2. **Skill conversion**: Claude SKILL.md (YAML frontmatter + content) → target format
   - OpenCode: `.md` files in config directories
   - Droid: Tool names remapped (`Bash`→`Execute`)
   - Qwen: Content extracted as `.yaml` with env var placeholders

3. **Tool name normalization** — Centralizes platform-specific tool naming across converters (e.g., Claude's `Bash` tool ↔ Droid's `Execute` tool)

4. **MCP server merging** — Reads user's existing MCP config, preserves non-managed entries, deep-merges plugin servers, writes back

**Release automation** — `semantic-release` generates changelogs automatically from conventional commit prefixes (`feat:`, `fix:`, `docs:`, etc.). Release PRs and GitHub Releases are canonical release-notes sources (not root CHANGELOG.md).

## Installation & Usage

### Install to Claude Code

```bash
/plugin marketplace add EveryInc/compound-engineering-plugin
/plugin install compound-engineering
```

### Install to Cursor

```
/add-plugin compound-engineering
```

### Install to Other Platforms

**OpenCode**:
```bash
bunx @every-env/compound-plugin install compound-engineering --to opencode
```

**Codex**:
```bash
bunx @every-env/compound-plugin install compound-engineering --to codex
```

**GitHub Copilot**:
```bash
bunx @every-env/compound-plugin install compound-engineering --to copilot
```

(Similar pattern for Droid, Pi, Gemini, Kiro, Windsurf, OpenClaw, Qwen)

### Multi-target Installation

```bash
bunx @every-env/compound-plugin install compound-engineering --to codex --also opencode --also copilot
```

### Sync Personal Config Across Tools

```bash
# Sync to all detected tools
bunx @every-env/compound-plugin sync

# Sync to specific target
bunx @every-env/compound-plugin sync --target codex
```

Syncs:
- Personal skills from `~/.claude/skills/` (as symlinks)
- Personal slash commands from `~/.claude/commands/` (as provider-native prompts, workflows, or converted skills)
- MCP servers from `~/.claude/settings.json`

### Local Development

**From local checkout** (active development — edits reflected immediately):

```bash
alias cce='claude --plugin-dir ~/code/compound-engineering-plugin/plugins/compound-engineering'
cce  # Run with local plugin
```

**From pushed branch**:

```bash
bun run src/index.ts plugin-path compound-engineering --branch feat/new-agents
# Output: claude --plugin-dir ~/.cache/compound-engineering/branches/compound-engineering-feat~new-agents/plugins/compound-engineering
```

Branch cache path is deterministic and auto-updates on re-run.

### Testing and Validation

```bash
bun install                     # Install dependencies
bun test                        # Run full test suite
bun run release:validate        # Check plugin/marketplace consistency
```

## Relevance to Claude Code Development

This plugin directly addresses multi-agent orchestration patterns and skill design best practices for Claude Code:

1. **Skill design patterns** — 40+ production skills demonstrating:
   - Reference file inclusion (backtick paths vs. `@` inline syntax)
   - Cross-platform content compatibility (works on Claude Code, Cursor, Codex, etc.)
   - Conditional and late-sequence extraction
   - Proper use of native tools (Glob, Grep, Read) instead of shell (`find`, `grep`, `cat`)

2. **Multi-agent orchestration** — The `/ce:review`, `/ce:compound`, and `/ce:plan` skills exemplify:
   - Parallel agent dispatch with confidence scoring
   - Deduplication pipelines to suppress duplicate findings
   - Gating logic (confidence thresholds, question tools)
   - Progressive refinement workflows

3. **Agent namespacing** — Demonstrates fully-qualified agent references (`compound-engineering:<category>:<name>`) to prevent conflicts when multiple plugins are loaded

4. **Plugin versioning and release** — Shows how to use `semantic-release` with `linked-versions` for synchronized CLI + plugin releases and automated changelog generation

5. **Cross-platform conversion** — The CLI is a reference implementation for converting Claude Code plugins to other agent platforms, with test fixtures and writer modules for 10+ targets

6. **Workflow philosophy** — Implements the planning-first, review-heavy, knowledge-compounding approach that aligns with Claude Code's emphasis on structured reasoning before code execution

## Limitations and Caveats

1. **Skill file isolation** — Skills cannot reference files outside their directory tree. If two skills need the same supporting file, it must be duplicated. This reflects current Claude Code skill resolution behavior and known path-resolution bugs (#11011, #17741, #12541).

2. **Cross-platform variable handling** — Platform-specific environment variables (e.g., `${CLAUDE_PLUGIN_ROOT}`, `CODEX_SESSION_ID`) are not universally available. Skills using them must include graceful fallbacks or use relative paths from the skill directory.

3. **MCP server coverage** — Kiro supports only stdio MCP servers (not HTTP). OpenClaw currently syncs skills only (no personal command sync or MCP sync yet).

4. **Agent naming conflicts** — When multiple plugins define agents with the same short name, unqualified references fail. Requires fully-qualified namespace (`plugin:category:name`).

5. **Release workflow constraint** — CLI and plugin versions are locked together via `linked-versions`. A plugin-only change still bumps CLI version. This is intentional but means version numbers don't strictly reflect per-component release cycles.

6. **Learning curve** — The compound engineering workflow philosophy (80% planning, 20% execution) requires discipline to maintain. Teams must commit to review-gate practices and knowledge codification to realize benefits.

7. **Browser automation optional** — The `agent-browser` skill requires separate installation: `npm install -g agent-browser && agent-browser install`. Not bundled with the plugin.

## References

- **GitHub Repository**: <https://github.com/EveryInc/compound-engineering-plugin> (accessed 2026-04-03)
- **NPM Package**: `@every-env/compound-plugin` v2.61.0 (accessed 2026-04-03)
- **Plugin Manifest**: `.claude-plugin/plugin.json` in repo (accessed 2026-04-03)
- **README**: `plugins/compound-engineering/README.md` — agent inventory, skill descriptions, installation instructions (accessed 2026-04-03)
- **AGENTS.md** (plugin instructions): `.claude-plugin/AGENTS.md` — versioning, compliance checklist, skill patterns (accessed 2026-04-03)
- **CHANGELOG**: Root `CHANGELOG.md` — release history, v2.61.0 (2026-04-01), v2.60.0 (2026-03-31), linked-versions policy (accessed 2026-04-03)
- **Package.json**: Scripts (dev, convert, cli:install, release:validate), dependencies (citty, js-yaml), devDependencies (semantic-release) (accessed 2026-04-03)
- **Article**: "My AI had already fixed the code before I saw it" — <https://every.to/source-code/my-ai-had-already-fixed-the-code-before-i-saw-it> (accessed 2026-04-03, homepage link from plugin manifest)
- **Every's Article**: "Compound Engineering: How Every codes with agents" — <https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents> (linked in README, accessed 2026-04-03)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | shares comprehensive multi-agent orchestration with 65+ skills and cross-platform support |
| [Claude Code Skills Library by Alireza Rezvani](./claude-code-skills-alirezarezvani.md) | skill-generation-tools | parallel skill library providing 170 modular packages for Claude Code with cross-platform deployment |
| [Gas Town](../research-agent-patterns/gastown.md) | research-agent-patterns | implements physical tmux+git-worktree infrastructure for multi-agent orchestration patterns |
| [Superpowers](../agent-frameworks/superpowers.md) | agent-frameworks | shares planning-first development philosophy with tiered review agents and skill-driven execution |
| [Orchestrator Agent Creation Guide](../research-agent-patterns/orchestrator-agent-creation-guide.md) | research-agent-patterns | demonstrates agent routing and delegation patterns for multi-agent coordination |
| [pi-mono](../agent-frameworks/pi-mono.md) | agent-frameworks | provides multi-agent runtime with unified LLM API and agent coordination infrastructure |

---

## Freshness Tracking

**Last reviewed**: 2026-04-03
**Next review**: 2026-07-03

### Confidence Summary

- **Identity/Metadata**: high — official plugin manifest, npm package, GitHub repo
- **Features**: high — extracted from official README, AGENTS.md, plugin structure
- **Architecture**: high — full plugin source read (CLI entry, conversion pipeline, agent dispatch, manifest format)
- **Usage Examples**: high — installation commands extracted from README with version verification
- **Limitations**: medium — some limitations documented in AGENTS.md, others inferred from code structure; learning curve limitations noted in articles but not systematically documented in official sources

### Notes

- Version 2.61.0 released 2026-04-01 with linked-versions release automation and skill file isolation guidelines
- CLI and plugin maintain synchronized versions via `linked-versions` release-please plugin
- Multi-platform conversion architecture supports 10 target agent platforms with dedicated writer modules and type definitions
- 35+ agents organized by discipline (review, document-review, research, design, workflow, docs); 40+ skills with consistent reference file patterns and cross-platform compatibility
