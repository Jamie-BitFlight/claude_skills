---
name: write-frontmatter-description
description: Write or rewrite frontmatter description fields for Claude Code skills and agents. Use when creating new skills/agents, description exceeds 1024 characters, description uses forbidden YAML multiline indicators (>-, |-), description lacks trigger keywords, or when optimizing descriptions for AI tool selection. Ensures descriptions are single-line, complete, informative, third-person, front-loaded with trigger conditions.
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.


The model MUST write frontmatter descriptions following these rules.

## Formatting Rules

1. **Single-line only** — Never use YAML multiline indicators (`>-`, `|-`, `>`, `|`)
2. **Front-load critical info** — First 1024 characters are most important
   - Claude Code may truncate to 1024 chars in some contexts
   - No hard limit, but keep key information in first 1024 chars
   - Convey purpose, triggers, and value early
3. **Validate with skilllint** — After writing, run `uvx skilllint@latest check --fix <file>` to auto-fix any YAML formatting issues

## Authoring Rules

These rules govern what the description must communicate — not just how it is formatted.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

### 1. Third-Person Phrasing

Write in third person. The description is injected into the system prompt as instructions to Claude about when to activate the skill — inconsistent point of view causes discovery problems.

```yaml
# Correct
description: Generates commit messages by analyzing staged git diffs. Use when the user asks for help writing commit messages.

# Wrong
description: I can help you write commit messages by looking at your staged changes.

# Wrong
description: You can use this to generate commit messages.
```

### 2. Directive Trigger Language

Make descriptions slightly directive — models tend to under-trigger skills. Use action words and list specific activation conditions.

Preferred trigger openers: "Use when", "Activates on", "Triggers on", "Apply when"

List specific file types, commands, or task patterns that activate the skill. Vague descriptions produce missed triggers.

### 3. Description Is the Primary Router

The description field is the main mechanism that determines whether a skill loads from 100+ available skills. It matters more than the skill body for routing. Front-load trigger conditions — the most specific activation signals must appear early.

### 4. Concrete Examples

```yaml
# Bad — vague, no triggers
description: A skill for working with documents

# Bad — too broad, no activation context
description: Helps with Python stuff

# Good — specific activity with named triggers
description: Use when building CLI applications with Typer — creating commands, defining arguments and options, composing subcommands, testing with CliRunner, or using advanced features like callbacks and autocompletion.

# Good — front-loads trigger conditions with action word
description: Validate and fix YAML frontmatter in SKILL.md and agent files. Use when creating new skills or agents, when description exceeds 1024 characters, when description uses forbidden YAML multiline indicators, or when optimizing descriptions for AI tool selection.
```

## Schema Field Awareness

Skills and agents have different valid frontmatter fields. Putting a field in the wrong component type causes silent failures.

**Skill-only fields** (not valid in agent files): `user-invocable`, `disable-model-invocation`, `argument-hint`

**Agent-only fields** (not valid in skill files): `tools`, `disallowedTools`, `memory`, `permissionMode`, `maxTurns`, `hooks`, `color`

**Shared fields**: `name`, `description`, `model`, `skills`, `mcpServers`

For the full schema, activate the `/plugin-creator:claude-skills-overview-2026` skill (skills) or check Anthropic agent docs (agents).

## Validation

After writing, validate with `skilllint`:

```sh
uvx skilllint@latest check [file]
```
