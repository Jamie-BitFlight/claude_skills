---
name: claude-skills-overview-2026
description: Reference guide for Claude Code skills system (March 2026). Use when creating, modifying, or understanding skills, SKILL.md format, frontmatter fields, hooks, context fork, or skill best practices.
user-invocable: true
---

# Claude Code Skills System - Complete Reference (March 2026)

Skills extend what Claude can do. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit. Claude uses skills when relevant, or you can invoke one directly with `/skill-name`.

> To create or improve skills using a guided workflow, load the `/plugin-creator:skill-creator` skill.

**Skills and slash commands are now unified** - they are the same system. A file at `.claude/commands/review.md` and a skill at `.claude/skills/review/SKILL.md` both create `/review` and work identically. If a skill and a command share the same name, the skill takes precedence. Skills are the recommended approach as they support additional features like supporting files and advanced frontmatter options.

> **Portable skills?** This reference covers **Claude Code-specific** features (hooks, context fork, model selection, invocation control). If you need to create skills that work across Claude Code, Cursor, Gemini CLI, OpenAI Codex, VS Code, and 20+ other agents, see the `../agentskills/SKILL.md` skill instead — it covers the portable subset of the format defined at [agentskills.io](https://agentskills.io).

---

## Bundled Skills

Bundled skills ship with Claude Code and are available in every session. Unlike built-in commands (which execute fixed logic), bundled skills are prompt-based: they give Claude a detailed playbook and let it orchestrate work using its tools (spawn parallel agents, read files, adapt to your codebase).

- **`/simplify`**: Reviews recently changed files for code reuse, quality, and efficiency issues, then fixes them. Spawns three review agents in parallel (code reuse, code quality, efficiency), aggregates findings, and applies fixes. Pass optional text to focus: `/simplify focus on memory efficiency`.

- **`/batch <instruction>`**: Orchestrates large-scale changes across a codebase in parallel. Researches the codebase, decomposes work into 5–30 independent units, presents a plan for approval. Once approved, spawns one background agent per unit in an isolated git worktree, each implementing its unit, running tests, and opening a pull request. Requires a git repository.

- **`/debug [description]`**: Troubleshoots your current Claude Code session by reading the session debug log. Optionally describe the issue to focus the analysis.

- **`/loop [interval] <prompt>`**: Schedules a recurring prompt at an interval. See `resources/scheduled-tasks.md`.

- **`/claude-api`**: Loads Claude API reference material for your project's language (Python, TypeScript, Java, Go, Ruby, C#, PHP, or cURL) and Agent SDK reference. Covers tool use, streaming, batches, structured outputs, and common pitfalls. Also activates automatically when your code imports `anthropic`, `@anthropic-ai/sdk`, or `claude_agent_sdk`.

**Source**: Official documentation at <https://code.claude.com/docs/en/skills.md> (section: "Bundled skills", accessed 2026-03-17)

---

## SKILL.md Complete Format

```yaml
---
name: my-skill
description: What this Skill does and when to use it
argument-hint: "[optional-arg]"
allowed-tools: Read, Grep, Glob
model: claude-sonnet-4-20250514
context: fork
agent: general-purpose
user-invocable: true
disable-model-invocation: false
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
          once: true
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "./scripts/lint.sh"
  Stop:
    - hooks:
        - type: command
          command: "./scripts/cleanup.sh"
---

# Skill Title

Your instructions here...
```

**Validation**: Use `claude plugin validate` to validate plugin structure. For skills bundled in plugins, see `../claude-plugins-reference-2026/SKILL.md` for plugin.json schema requirements.

---

## All Frontmatter Fields

All fields are optional. Only `description` is recommended so Claude knows when to use the skill.

The fields `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools` are part of the `../agentskills/SKILL.md` and are portable across all compatible agents. The remaining fields below are Claude Code extensions.

| Field                      | Required    | Type    | Max Length | Description                                                                                                                                           |
| -------------------------- | ----------- | ------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                     | Recommended | string  | 64 chars   | Display name for the skill. If omitted, uses directory name. Lowercase letters, numbers, hyphens only. Required per agentskills.io spec; optional in Claude Code. |
| `description`              | Recommended | string  | 1024 chars | What the skill does and when to use it. Claude uses this to decide when to apply the skill. If omitted, uses the first paragraph of markdown content. |
| `argument-hint`            | No          | string  | —          | Hint shown during autocomplete to indicate expected arguments. Example: `[issue-number]` or `[filename] [format]`.                                    |
| `allowed-tools`            | No          | string  | —          | Tools Claude can use without asking permission when this skill is active (comma-separated). Example: `Read, Grep, Glob, Bash(npm run:*)`              |
| `model`                    | No          | string  | —          | Model to use when this skill is active. Use aliases `opus`, `sonnet`, `haiku` (preferred) or full model IDs like `claude-opus-4-6`, `claude-sonnet-4-6`. |
| `context`                  | No          | string  | —          | Set to `fork` to run in a forked subagent context. See [Context Fork Behavior](#context-fork-behavior) for tool restrictions.                         |
| `agent`                    | No          | string  | —          | Which subagent type to use when `context: fork` is set. Options: `Explore`, `Plan`, `general-purpose`, or custom agent. Default: `general-purpose`    |
| `user-invocable`           | No          | boolean | —          | Set to `false` to hide from the `/` menu. Use for background knowledge users shouldn't invoke directly. Default: `true`.                              |
| `disable-model-invocation` | No          | boolean | —          | Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`. Default: `false`. |
| `hooks`                    | No          | object  | —          | Hooks scoped to this skill's lifecycle. See [Hooks](/en/hooks) for configuration format. Events: `PreToolUse`, `PostToolUse`, `Stop`                  |

> [!IMPORTANT]
>
> When an `allowed-tools` field is not specified, the skill inherits the tool capabilities of the parent agent. This is a common pattern for skills that need to use tools from the parent agent. Such as when a skill is used by the orchestrator agent for knowledge or task information, no `allowed-tools` field is needed.
>
> The `allowed-tools` field is both a pre-approval mechanism and a capability scoping mechanism.
> Listed tools are granted to Claude without per-use permission prompts when the skill is active, and Claude is restricted to only those tools.
> This also reduces context size by limiting included tool definitions to only those the skill may need.

> [!NOTE]
> **`name:` is required** per the [Agent Skills open standard](https://agentskills.io/specification). A bug in Claude Code v2.1.23 caused plugin skills with `name:` to not appear as slash commands; that bug was resolved 2026-02-20. Include `name:` in all SKILL.md files. The value must match the directory name.

---

## Skill Tokenomics

Skills use progressive disclosure - only frontmatter loads initially (~100 tokens), full content loads on activation.

The context window is a public good shared with everything else Claude needs to know. Only add context Claude does not already have. Before writing each section, challenge it:

- Does Claude really need this information to complete the task?
- Can I assume Claude already knows this from training?
- Does this paragraph justify its token cost?

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

### Budget Constraints

| Resource                   | Limit                                      | Notes                               |
| -------------------------- | ------------------------------------------ | ----------------------------------- |
| `name` field               | 64 chars                                   | Lowercase, numbers, hyphens only    |
| `description` field        | 1024 chars                                  | Critical for skill selection        |
| `<available_skills>` block | 2% of context window (fallback 16,000 chars) | Scales dynamically; separate from global context |
| Skills before truncation   | ~34-36                                     | Varies by description complexity    |

### YAML Multiline Bug

**Use single-line strings for descriptions** — Claude Code's skill indexer does not parse YAML multiline indicators (`>-`, `|`, `|-`) correctly; the description may appear as ">-" instead of actual content. Quote the value only when YAML syntax requires it (colons, leading special characters, boolean literals).

```yaml
# Correct — single quoted string
description: 'Extract text from PDFs. Use when the user mentions PDFs or document extraction.'

# Wrong — multiline indicators break the indexer
description: >-
  This appears as ">-" in the index
```

### Truncation Behavior

When total skill metadata exceeds the budget (2% of context window, fallback 16,000 characters):

1. Skills are truncated from the `<available_skills>` block
2. Truncated skills cannot be auto-invoked by Claude
3. User can still invoke truncated skills explicitly with `/skill-name`
4. Run `/context` to check for a warning about excluded skills

To override the limit, set the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable.

**Source**: Official documentation at <https://code.claude.com/docs/en/skills.md> (section: "Troubleshooting")

### Fallback Strategy

If you have many skills, embed pointers in CLAUDE.md as a safeguard:

```markdown
## Skills Available
- For debugging: use `/scientific-method:scientific-thinking` skill
- For delegation: use `/delegate` skill
```

This ensures Claude can find skills even if truncated from `<available_skills>`.

---

## String Substitutions

Skills support string substitution for dynamic values in the skill content:

| Variable               | Description                                                                                                                                  |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `$ARGUMENTS`           | All arguments passed when invoking the skill. If `$ARGUMENTS` is not present in the content, arguments are appended as `ARGUMENTS: <value>`. |
| `$ARGUMENTS[N]`        | Access a specific argument by 0-based index, such as `$ARGUMENTS[0]` for the first argument.                                                 |
| `$N`                   | Shorthand for `$ARGUMENTS[N]`, such as `$0` for the first argument or `$1` for the second.                                                   |
| `${CLAUDE_SESSION_ID}` | The current session ID. Useful for logging, creating session-specific files, or correlating skill output with sessions.                      |
| `${CLAUDE_SKILL_DIR}`  | Absolute path to the directory containing the current SKILL.md file. For plugin skills, this is the skill's subdirectory within the plugin, not the plugin root. Use in bash injection commands to reference scripts or files bundled with the skill, regardless of the current working directory. |

**Example with positional arguments:**

```yaml
---
description: Migrate a component from one framework to another
---

Migrate the $0 component from $1 to $2.
Preserve all existing behavior and tests.
```

Running `/migrate-component SearchBar React Vue` replaces `$0` with `SearchBar`, `$1` with `React`, and `$2` with `Vue`.

---

## Dynamic Context Injection

The exclamation then backtick syntax runs shell commands before the skill content is sent to Claude. The command output replaces the placeholder, so Claude receives actual data, not the command itself.

**Example**: This skill summarizes a pull request by fetching live PR data with the GitHub CLI: @resources/pr-summary-example.md

**How it works**:

1. Each \`\!\`command\`\` executes immediately (before Claude sees anything)
2. The output replaces the placeholder in the skill content
3. Claude receives the fully-rendered prompt with actual PR data

**This is preprocessing**, not something Claude executes. Claude only sees the final result.

**Extended Thinking**: To enable [extended thinking mode](/en/common-workflows#use-extended-thinking-thinking-mode) in a skill, include the word "ultrathink" anywhere in your skill content.

**Source**: Official documentation at <https://code.claude.com/docs/en/skills.md> (sections: "Inject dynamic context", "Advanced patterns")

---

## Directory Structure

```
skill-name/
├── SKILL.md              # Required
├── references/           # Optional: docs loaded on demand
├── scripts/              # Optional: executed, not loaded into context
├── templates/            # Optional: reusable content
└── examples/             # Optional: sample output showing expected format
```

Supporting files can also live at the skill root (e.g., `reference.md`, `forms.md`). Reference them from SKILL.md so Claude knows what each file contains and when to load it.

### Location Priority (Highest to Lowest)

1. **Managed/Enterprise** - System-level (see [managed settings](/en/permissions#managed-settings))
2. **Personal** - `~/.claude/skills/`
3. **Project** - `.claude/skills/`
4. **Plugin** - Bundled with plugins (see `../claude-plugins-reference-2026/SKILL.md`)

When skills share the same name across levels, higher-priority locations win: enterprise > personal > project. Plugin skills use a `plugin-name:skill-name` namespace, so they cannot conflict with other levels.

#### Automatic Discovery from Nested Directories

When you work with files in subdirectories, Claude Code automatically discovers skills from nested `.claude/skills/` directories. For example, if you're editing a file in `packages/frontend/`, Claude Code also looks for skills in `packages/frontend/.claude/skills/`. This supports monorepo setups where packages have their own skills.

#### Skills from Additional Directories

Skills defined in `.claude/skills/` within directories added via `--add-dir` are loaded automatically and picked up by live change detection, so you can edit them during a session without restarting.

**Note**: CLAUDE.md files from `--add-dir` directories are not loaded by default. Set `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1` to load them. See memory documentation for details.

**Source**: Official documentation at <https://code.claude.com/docs/en/skills.md> (section: "Where skills live")

---

## Hooks in Skills

Skills can define hooks in frontmatter to respond to events during the skill's lifecycle. Use `Skill(skill: "plugin-creator:hooks-guide")` for complete hook documentation.

### Hook Events

- `PreToolUse`: Before tool executes
- `PostToolUse`: After successful execution
- `Stop`: When Skill finishes

### Hook Structure

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"           # Regex pattern
      hooks:
        - type: command
          command: "./scripts/check.sh"
          once: true            # Run only once per session
```

### Hook I/O

- Receives JSON via stdin (session info, tool name, parameters)
- Exit 0: Success
- Exit 2: Blocking error (prevents tool, shows stderr)
- Other: Non-blocking error

For complete hook configuration including all events, matchers, JSON output control, and examples, use `Skill(skill: "plugin-creator:hooks-guide")`.

---

## Context Fork Behavior

Add `context: fork` to your frontmatter when you want a skill to run in isolation. The skill content becomes the prompt that drives the subagent. It won't have access to your conversation history.

**Use `context: fork` only when the skill includes explicit instructions and a clear task.** If the skill contains guidelines like "use these API conventions" without a task, the subagent receives the guidelines but no actionable prompt and may return without meaningful output.

### Agent Types

```yaml
context: fork
agent: Explore
```

| Agent             | Model    | Tools                      | Use Case                     |
| ----------------- | -------- | -------------------------- | ---------------------------- |
| `Explore`         | Haiku    | File/web/MCP (read-only)   | Verbatim retrieval only — never analysis or reasoning (~50% hallucination rate on reasoning tasks) |
| `Plan`            | Inherits | File/web/MCP (read-only)   | Research before planning     |
| `general-purpose` | Inherits | File/web/MCP + Bash/system | Complex operations (default) |
| Custom            | Custom   | Custom                     | Project-specific work        |

### Tool Restrictions in Forked Contexts

**VERIFIED BEHAVIOR** (experimentally confirmed 2026-01-22):

When `context: fork` is set, the forked subagent has access to:

- File operations: Read, Write, Edit, Grep, Glob
- Web operations: WebSearch, WebFetch
- MCP tools (if configured)
- Bash and other system tools (depending on agent type)

**The Agent tool is NOT available in forked contexts.** This means forked skills cannot delegate to other subagents. If you need hierarchical delegation (subagent delegates to another subagent), the parent must run in the main context (no `context: fork`), not in a forked context.

**Source**: Experimental verification on 2026-01-22. Official documentation at <https://code.claude.com/docs/en/skills.md> does not explicitly document this restriction.

### Skills vs Subagents

Skills and subagents work together in two directions:

| Approach                     | System prompt                             | Task                        | Also loads                   |
| ---------------------------- | ----------------------------------------- | --------------------------- | ---------------------------- |
| Skill with `context: fork`   | From agent type (`Explore`, `Plan`, etc.) | SKILL.md content            | CLAUDE.md                    |
| Subagent with `skills` field | Subagent's markdown body                  | Claude's delegation message | Preloaded skills + CLAUDE.md |

With `context: fork`, you write the task in your skill and pick an agent type to execute it. For the inverse (defining a custom subagent that uses skills as reference material), see the Sub-Agents documentation.

### Skills vs Agent Teams

Agent teams coordinate multiple independent Claude Code instances with inter-agent messaging and a shared task list. Unlike subagents (which report back to caller only), teammates communicate directly with each other.

| Criterion | Subagents | Agent Teams |
| --- | --- | --- |
| Communication | Results return to caller only | Teammates message each other directly |
| Best for | Focused tasks where only the result matters | Complex work requiring cross-challenge and synthesis |
| Token cost | Lower | Higher (each teammate is separate instance) |

Use agent teams when 3+ workers need to share findings, challenge each other, and coordinate independently. Use subagents when workers report back without needing cross-communication.

For complete agent teams reference including architecture, display modes, lifecycle management, use case patterns, and quality gate hooks (`TeammateIdle`, `TaskCompleted`), see `resources/agent-teams.md`. For implementation-level API details (TeammateTool operations, message formats, spawn backends), activate the `/orchestrating-swarms` skill.

**Source**: [Agent Teams Documentation](https://code.claude.com/docs/en/agent-teams.md) (accessed 2026-02-06)

---

## Invocation Control

### Control who invokes a skill

By default, both you and Claude can invoke any skill. You can type `/skill-name` to invoke it directly, and Claude can load it automatically when relevant to your conversation. Two frontmatter fields let you restrict this:

- **`disable-model-invocation: true`**: Only you can invoke the skill. Use this for workflows with side effects or that you want to control timing, like `/commit`, `/deploy`, or `/send-slack-message`. You don't want Claude deciding to deploy because your code looks ready. This field also removes the skill description from Claude's context entirely.

- **`user-invocable: false`**: Only Claude can invoke the skill. Use this for background knowledge that isn't actionable as a command. A `legacy-system-context` skill explains how an old system works. Claude should know this when relevant, but `/legacy-system-context` isn't a meaningful action for users to take.

**How invocation control affects context loading:**

| Frontmatter                      | You can invoke | Claude can invoke | When loaded into context                                     |
| :------------------------------- | :------------- | :---------------- | :----------------------------------------------------------- |
| (default)                        | Yes            | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes            | No                | Description not in context, full skill loads when you invoke |
| `user-invocable: false`          | No             | Yes               | Description always in context, full skill loads when invoked |

In a regular session, skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked. [Subagents with preloaded skills](/en/sub-agents#preload-skills-into-subagents) work differently: the full skill content is injected at startup.

**Source**: Official documentation at <https://code.claude.com/docs/en/skills.md> (section: "Control who invokes a skill")

### Restrict Claude's skill access

By default, Claude can invoke any skill that doesn't have `disable-model-invocation: true` set. Skills that define `allowed-tools` grant Claude access to those tools without per-use approval when the skill is active. Your [permission settings](/en/permissions) still govern baseline approval behavior for all other tools. Built-in commands like `/compact` and `/init` are not available through the Skill tool.

Three ways to control which skills Claude can invoke:

**Disable all skills** by denying the Skill tool in `/permissions`:

```
# Add to deny rules:
Skill
```

**Allow or deny specific skills** using [permission rules](/en/permissions):

```
# Allow only specific skills
Skill(commit)
Skill(review-pr *)

# Deny specific skills
Skill(deploy *)
```

Permission syntax: `Skill(name)` for exact match, `Skill(name *)` for prefix match with any arguments.

**Hide individual skills** by adding `disable-model-invocation: true` to their frontmatter. This removes the skill from Claude's context entirely.

**Note**: The `user-invocable` field only controls menu visibility, not Skill tool access. Use `disable-model-invocation: true` to block programmatic invocation.

**Source**: Official documentation at <https://code.claude.com/docs/en/skills.md> (section: "Restrict Claude's skill access")

---

## Description Best Practices

**Good**:

```yaml
description: Extract text and tables from PDFs, fill forms, merge documents. Use when working with PDF files or when user mentions PDFs, forms, extraction.
```

**Bad**:

```yaml
description: Helps with documents
```

**Template**:

```
[Action 1], [Action 2], [Action 3]. Use when [situation 1], [situation 2],
or when the user mentions [keywords].
```

---

## Examples

### Simple Skill

```yaml
---
description: Generate conventional commit messages from git diffs. Use when writing commits.
---

# Commit Messages

1. Run `git diff --staged`
2. Determine type (feat, fix, docs)
3. Write message under 50 chars
4. Use imperative mood
```

### Tool-Restricted

```yaml
---
description: Read files without changes. Use for code review.
allowed-tools: Read, Grep, Glob
---

# Safe Reader

ONLY read files. Never modify.
```

### Forked Context

```yaml
---
description: Thorough codebase research. Use for complex investigations.
context: fork
agent: Explore
---

# Deep Research

Runs in isolated context to avoid polluting main conversation.
```

### With Hooks

```yaml
---
description: Audit-logged file operations.
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
          once: true
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "./scripts/lint.sh"
---

# Secure Operations

All modifications logged and validated.
```

### Hidden from Users

```yaml
---
description: Auto-apply code review standards.
user-invocable: false
---

Claude invokes this, users don't see it in menu.
```

### User-Only (No Auto-Invoke)

```yaml
---
description: Deploy to production.
disable-model-invocation: true
---

Only runs when user types `/deploy-production`.
```

---

## Skills vs Other Features

**Note**: Skills and slash commands are now the same system. Files in `.claude/commands/` still work but skills are recommended.

| Feature         | Invocation            | Use Case                                     |
| --------------- | --------------------- | -------------------------------------------- |
| **Skills**      | Claude decides OR `/` | Specialized knowledge/workflows, auto-invoke |
| **CLAUDE.md**   | Always loaded         | Project-wide instructions                    |
| **Subagents**   | Claude delegates      | Isolated complex operations                  |
| **MCP Servers** | Claude calls          | External tools/data                          |
| **Hooks**       | Tool events           | Automate actions                             |

---

## Installation

**Via Plugins**: Skills can be bundled in plugins. See `../claude-plugins-reference-2026/SKILL.md` for plugin creation and distribution.

**Marketplace**:

```bash
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
```

**Manual**: Copy to `~/.claude/skills/` or `.claude/skills/`

**Hot Reload**: Changes apply immediately without restart.

---

## Recent Updates (2.1+)

- **Dynamic token budget** — 2% of context window (fallback 16,000 chars) for skill metadata
- **Skills from --add-dir** — Loaded with live change detection
- **Unified skills and commands** — `.claude/commands/` files now work as skills, skills recommended
- **Dynamic context injection** - \!\`command\` syntax for preprocessing shell command output
- **`argument-hint` field** - Show autocomplete hints for expected arguments
- **Optional name/description** - If omitted, uses directory name and first paragraph
- **`once: true` for hooks** - Run only once per session
- **`${CLAUDE_SESSION_ID}`** - Session-scoped operations
- **`context: fork`** with agent selection
- **Hot reload** - immediate updates without restart

---

## Troubleshooting

**Skill not triggering?** Check the description includes keywords users would naturally say; verify the skill appears in "What skills are available?"; try rephrasing the request; invoke directly with `/skill-name` if user-invocable.

**Skill triggers too often?** Make the description more specific; add `disable-model-invocation: true` if you only want manual invocation.

**Claude doesn't see all skills?** Run `/context` to check for excluded-skills warnings. The budget scales at 2% of context (fallback 16,000 chars). Set `SLASH_COMMAND_TOOL_CHAR_BUDGET` to override.

---

## Related Skills

- **`../agentskills/SKILL.md`** — The portable specification (agentskills.io). Use when creating skills for cross-agent compatibility. Covers the subset of frontmatter fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) recognized by all 25+ compatible agents.
- **`../claude-plugins-reference-2026/SKILL.md`** — Plugin creation, distribution, and plugin.json schema.
- **`../hooks-guide/SKILL.md`** — Complete hook events, matchers, and configuration. Cross-platform coverage with Node.js CJS and Python guides.
- **`resources/claude-code-skills-official.md`** — Authoritative specification from code.claude.com: frontmatter fields, discovery rules, invocation control, budget limits, and bundled skills.
- **`resources/scheduled-tasks.md`** — CronCreate, CronList, CronDelete, /loop syntax, cron expressions, plugin integration patterns.
- **`resources/headless-agent-sdk.md`** — Running Claude Code programmatically via `claude -p`. Covers the critical constraint that skills are unavailable in `-p` mode, all CLI flags, output formats (json/stream-json/schema), automation patterns, and design checklist for plugin authors.
- **`resources/output-styles.md`** — Custom output styles, plugin.json outputStyles field, comparison with CLAUDE.md and skills.
- **`resources/agent-teams.md`** — TeammateIdle/TaskCompleted hooks, team architecture, display modes, lifecycle.

## Sources

- **Primary**: [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills.md) (accessed 2026-03-01) — full reference at `resources/claude-code-skills-official.md`
- **Standards**: [Agent Skills Open Standard](https://agentskills.io) — see also the `../agentskills/SKILL.md` for the full portable specification reference
- **Examples**: [anthropics/skills](https://github.com/anthropics/skills)
- **Blog**: [Anthropic Engineering Blog - Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- **Experimental**: Context fork tool restrictions verified 2026-01-22
