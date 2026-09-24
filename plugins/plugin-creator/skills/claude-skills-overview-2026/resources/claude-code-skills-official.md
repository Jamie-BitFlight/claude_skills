# Claude Code Skills — Official Reference

Authoritative specification for how Claude Code discovers, loads, configures, and invokes skills — the runtime environment this skill documents.

**Why read this**: This skill teaches you the skills system. This reference is the primary source from which that teaching derives. When the skill's content and the official docs disagree, the official docs win. Read this to verify claims, check for new features, and understand edge cases not covered in the skill body.

SOURCE: [Extend Claude with skills](https://code.claude.com/docs/en/skills#frontmatter-reference) (accessed 2026-09-24)

---

## Bundled Skills

Bundled skills ship with Claude Code and are available in every session. Unlike built-in commands (which execute fixed logic), bundled skills are prompt-based: they give Claude a detailed playbook and let it orchestrate work using its tools.

- **`/simplify`**: Reviews recently changed files for code reuse, quality, and efficiency issues, then fixes them. Spawns three review agents in parallel (code reuse, code quality, efficiency), aggregates findings, and applies fixes. Pass optional text to focus on specific concerns: `/simplify focus on memory efficiency`.

- **`/batch <instruction>`**: Orchestrates large-scale changes across a codebase in parallel. Researches the codebase, decomposes work into 5–30 independent units, presents a plan for approval. Once approved, spawns one background agent per unit, each in an isolated git worktree. Each agent implements its unit, runs tests, and opens a pull request. Requires a git repository. Example: `/batch migrate src/ from Solid to React`.

- **`/debug [description]`**: Troubleshoots your current Claude Code session by reading the session debug log. Optionally describe the issue to focus the analysis.

Claude Code also includes a bundled developer platform skill that activates automatically when your code imports the Anthropic SDK.

---

## Skill File Format

### SKILL.md Structure

Every skill is a directory with `SKILL.md` as the entrypoint:

```text
my-skill/
├── SKILL.md           # Main instructions (required)
├── template.md        # Template for Claude to fill in
├── examples/
│   └── sample.md      # Example output showing expected format
└── scripts/
    └── validate.sh    # Script Claude can execute
```

Two parts: YAML frontmatter (between `---` markers) for metadata, and markdown content with instructions Claude follows when invoked.

### Frontmatter Reference

All fields are optional. Only `description` is recommended.

| Field                      | Required    | Description |
|:---------------------------|:------------|:------------|
| `name`                     | No          | Display name. If omitted, uses directory name. |
| `description`              | Recommended | What the skill does and when to use it. If omitted, uses the first non-empty markdown line. |
| `when_to_use`              | No          | Additional activation guidance. |
| `argument-hint`            | No          | Hint shown during autocomplete. Example: `[issue-number]` or `[filename] [format]`. |
| `arguments`                | No          | Argument definition used by the skill. |
| `disable-model-invocation` | No          | `true` prevents Claude from automatically loading this skill. Default: `false`. |
| `user-invocable`           | No          | `false` hides from `/` menu. Default: `true`. |
| `allowed-tools`            | No          | Space- or comma-separated string, or YAML list, of tools pre-approved while active. |
| `disallowed-tools`         | No          | Tools unavailable while the skill is active. |
| `model`                    | No          | Model to use when this skill is active. |
| `effort`                   | No          | Effort override while the skill is active. |
| `context`                  | No          | `fork` runs in a fresh skill subagent, not a conversation fork. |
| `agent`                    | No          | Subagent type when `context: fork`. Options: `Explore`, `Plan`, `general-purpose`, or custom. Default: `general-purpose`. |
| `background`               | No          | Forks default to background; `false` waits in the foreground. |
| `hooks`                    | No          | Hooks scoped to this skill's lifecycle. Events: `PreToolUse`, `PostToolUse`, `Stop`. |
| `paths`                    | No          | Path patterns associated with the skill. |
| `shell`                    | No          | Shell configuration for skill commands. |
| `metadata`                 | No          | String-keyed metadata. |
| `license`                  | No          | License name or bundled license reference. |
| `compatibility`            | No          | Environment requirements. |

---

## Where Skills Live

| Location   | Path                                     | Applies to                     |
|:-----------|:-----------------------------------------|:-------------------------------|
| Enterprise | Managed settings                         | All users in organization      |
| Personal   | `~/.claude/skills/<name>/SKILL.md`       | All your projects              |
| Project    | `.claude/skills/<name>/SKILL.md`         | This project only              |
| Plugin     | `<plugin>/skills/<name>/SKILL.md`        | Where plugin is enabled        |

**Precedence**: enterprise > personal > project. Plugin skills use `plugin-name:skill-name` namespace, so they cannot conflict.

### Automatic Discovery

- **Nested directories**: When editing files in `packages/frontend/`, Claude Code also looks for skills in `packages/frontend/.claude/skills/`. Supports monorepo setups.
- **`--add-dir` directories**: Skills in `.claude/skills/` within `--add-dir` directories are loaded with live change detection — editable during sessions without restart.
- **Commands compatibility**: Files in `.claude/commands/` still work and support the same frontmatter. If a skill and command share the same name, the skill takes precedence.

---

## String Substitutions

| Variable               | Description |
|:-----------------------|:------------|
| `$ARGUMENTS`           | All arguments passed. If not present in content, appended as `ARGUMENTS: <value>`. |
| `$ARGUMENTS[N]`        | Specific argument by 0-based index. |
| `$N`                   | Shorthand for `$ARGUMENTS[N]`. |
| `${CLAUDE_SESSION_ID}` | Current session ID. |

---

## Dynamic Context Injection

The `!`command`` syntax runs shell commands before skill content is sent to Claude. Command output replaces the placeholder — Claude receives actual data, not the command.

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

Processing:
1. Each `!`command`` executes immediately (before Claude sees anything)
2. Output replaces the placeholder in skill content
3. Claude receives the fully-rendered prompt

To enable extended thinking in a skill, include the word "ultrathink" anywhere in skill content.

---

## Invocation Control

| Frontmatter                      | You can invoke | Claude can invoke | When loaded into context |
|:---------------------------------|:---------------|:------------------|:-------------------------|
| (default)                        | Yes            | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes            | No                | Description NOT in context, full skill loads when you invoke |
| `user-invocable: false`          | No             | Yes               | Description always in context, full skill loads when invoked |

**Key distinction**: In a regular session, skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked. Subagents with preloaded skills work differently — full skill content is injected at startup.

---

## Restrict Claude's Skill Access

Three methods:

1. **Disable all skills**: Deny the `Skill` tool in `/permissions`
2. **Allow/deny specific skills**: `Skill(commit)` for exact match, `Skill(deploy *)` for prefix match
3. **Hide individual skills**: `disable-model-invocation: true` in frontmatter

**Note**: `user-invocable` only controls menu visibility, not Skill tool access. Use `disable-model-invocation: true` to block programmatic invocation.

---

## Run Skills in a Subagent

`context: fork` runs the skill in a fresh subagent. The skill content becomes the prompt and the subagent does not receive conversation history. This is distinct from a conversation fork, which inherits history and cannot fork again.

**Warning**: `context: fork` only makes sense for skills with explicit instructions and a clear task. Guidelines without a task produce no meaningful output.

| Approach                     | System prompt                             | Task                        | Also loads       |
|:-----------------------------|:------------------------------------------|:----------------------------|:-----------------|
| Skill with `context: fork`   | From agent type (`Explore`, `Plan`, etc.) | SKILL.md content            | CLAUDE.md except Explore and Plan |
| Subagent with `skills` field | Subagent's markdown body                  | Claude's delegation message | Preloaded skills + CLAUDE.md |

---

## Skill Budget and Truncation

- **Budget**: 2% of context window (fallback 16,000 characters) for skill metadata
- **Override**: `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable
- **Check**: Run `/context` for warnings about excluded skills
- Truncated skills can still be invoked explicitly with `/skill-name`

---

## Troubleshooting

- **Not triggering**: Check description keywords, verify with "What skills are available?", invoke directly with `/skill-name`
- **Triggers too often**: Make description more specific, add `disable-model-invocation: true`
- **Claude doesn't see all skills**: Run `/context` to check budget warnings, set `SLASH_COMMAND_TOOL_CHAR_BUDGET` to override

---

## Subagent `skills` Field — Preloading Skill Content

Subagents support a `skills` field in frontmatter that injects the full content of named skills into the subagent's context at startup. This is different from regular skill invocation: the full body is injected immediately rather than made available for on-demand loading.

```yaml
---
name: api-developer
description: Implement API endpoints following team conventions
skills:
  - api-conventions
  - error-handling-patterns
---

Implement API endpoints. Follow the conventions and patterns from the preloaded skills.
```

Key behaviors:

- Subagents do NOT inherit skills from the parent conversation — each skill must be listed explicitly
- Skills with `disable-model-invocation: true` cannot be preloaded (they are excluded from the invocable set Claude draws from)
- If a listed skill is missing or disabled, Claude Code skips it and logs a warning to the debug log

This is the inverse of `context: fork` in a skill. With `skills` in a subagent, the subagent controls its own system prompt and loads skill content at startup. With `context: fork` in a skill, the skill content becomes the task sent to the agent type you specify.

SOURCE: [Create custom subagents](https://code.claude.com/docs/en/sub-agents.md) section "Preload skills into subagents" (accessed 2026-04-23)

---

## Subagent Model Resolution Priority

When Claude invokes a subagent, the model is resolved in this priority order (highest to lowest):

1. The per-invocation `model` parameter passed at invocation time
2. The subagent definition's `model` frontmatter field
3. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, if set
4. The main conversation's model (the default — equivalent to `inherit`)

Set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` to force the environment-configured default over higher-precedence selections.

The `model` field in frontmatter accepts: `sonnet`, `opus`, `haiku`, a full model ID (e.g., `claude-opus-4-7`), or `inherit`. Omitting `model` defaults to `inherit`.

The model override from a skill's `model` field applies for the rest of the current turn only and is not saved to settings; the session model resumes on the next prompt.

SOURCE: [Create custom subagents](https://code.claude.com/docs/en/sub-agents#choose-a-model) (accessed 2026-09-24)

---

## Related

- [Subagents](https://code.claude.com/docs/en/sub-agents.md) — delegate tasks to specialized agents
- [Plugins](https://code.claude.com/docs/en/plugins.md) — package and distribute skills
- [Hooks](https://code.claude.com/docs/en/hooks.md) — automate workflows around tool events
- [Memory](https://code.claude.com/docs/en/memory.md) — manage CLAUDE.md files
- [Permissions](https://code.claude.com/docs/en/permissions.md) — control tool and skill access
