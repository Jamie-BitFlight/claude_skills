# Command Frontmatter Field Reference

Complete specification for YAML frontmatter fields in slash commands.

YAML frontmatter is optional metadata at the start of command files:

```markdown
---
description: Brief description
allowed-tools: Read, Write
model: sonnet
argument-hint: [arg1] [arg2]
---

Command prompt content here...
```

All fields are optional. Commands work without any frontmatter.

## description

**Type:** String
**Default:** First line of command prompt
**Recommended max:** 60 characters for clean `/help` display

Describes what the command does. Shown in `/help` output.

```yaml
description: Review code for security issues
```

Start with a verb (Review, Deploy, Generate). Be specific about what the command
does. Avoid redundant phrases like "This command" or "A command that".

## allowed-tools

**Type:** String or array of strings
**Default:** Inherits from conversation permissions

Restrict or specify which tools the command can use.

**Single tool:**

```yaml
allowed-tools: Read
```

**Multiple tools (comma-separated):**

```yaml
allowed-tools: Read, Write, Edit
```

**Multiple tools (array):**

```yaml
allowed-tools:
  - Read
  - Write
  - Bash(git:*)
```

**Bash with command filter:**

```yaml
allowed-tools: Bash(git:*)           # Only git commands
allowed-tools: Bash(npm:*)           # Only npm commands
allowed-tools: Bash(docker:*)        # Only docker commands
```

**All tools (not recommended):**

```yaml
allowed-tools: "*"
```

Be as restrictive as possible. Use command filters for Bash (e.g., `git:*`
not `*`). Only specify when different from conversation permissions.

## model

**Type:** String
**Default:** Inherits from conversation
**Values:** `sonnet`, `opus`, `haiku`

Specify which Claude model executes the command.

```yaml
model: haiku    # Fast, efficient for simple tasks
model: sonnet   # Balanced performance (default)
model: opus     # Maximum capability for complex tasks
```

Omit unless specific need. Use `haiku` for speed when possible. Reserve
`opus` for genuinely complex tasks.

## argument-hint

**Type:** String
**Default:** None

Document expected arguments for users and autocomplete.

```yaml
argument-hint: [pr-number]
argument-hint: [environment] [version]
argument-hint: [source-branch] [target-branch] [commit-message]
```

Use square brackets for each argument. Use descriptive names (not `arg1`).
Match order to positional arguments in command (`$1`, `$2`, etc.).

## disable-model-invocation

**Type:** Boolean
**Default:** false

Prevent the SlashCommand tool from programmatically invoking the command.

```yaml
disable-model-invocation: true
```

When true, the command is only invokable by the user typing `/command`.
Not available to the SlashCommand tool.

Use for destructive operations, commands requiring human judgment, or
interactive workflows.

## Complete Examples

### Minimal Command (no frontmatter)

```markdown
Review this code for common issues and suggest improvements.
```

### Standard Command

```markdown
---
description: Review Git changes
allowed-tools: Bash(git:*), Read
---

Current changes: !`git diff --name-only`

Review each changed file for code quality and potential bugs.
```

### Full-Featured Command

```markdown
---
description: Deploy application to environment
argument-hint: [app-name] [environment] [version]
allowed-tools: Bash(kubectl:*), Bash(helm:*), Read
model: sonnet
---

Deploy $1 to $2 environment using version $3

Pre-deployment checks:
- Verify $2 configuration
- Check cluster status: !`kubectl cluster-info`
- Validate version $3 exists

Proceed with deployment following deployment runbook.
```

### Manual-Only Command

```markdown
---
description: Approve production deployment
argument-hint: [deployment-id]
disable-model-invocation: true
allowed-tools: Bash(gh:*)
---

Review deployment $1 for production approval.

Verify all tests passed, security scan clean, rollback plan ready.
Type "APPROVED" to confirm deployment.
```

## Validation Checklist

Before committing a command:

- YAML syntax valid (no parsing errors)
- Description under 60 characters
- allowed-tools uses proper format (comma-separated or array)
- model is valid value if specified (sonnet, opus, or haiku)
- argument-hint matches positional arguments used in command body
- disable-model-invocation used only when manual-only is required

## Documentation and Testing

### Self-Documenting Commands

Embed documentation in HTML comments for maintainability:

```markdown
---
description: Deploy to specified environment
argument-hint: [environment] [version]
---

<!--
PURPOSE: Deploy application with pre-flight checks
USAGE: /deploy [staging|production] [version]
REQUIREMENTS: kubectl configured, cluster access
EXAMPLE: /deploy staging v1.2.3
-->

Deploy $1 using version $2...
```

### Testing Strategy

1. **Syntax validation** — verify YAML frontmatter parses correctly
2. **Field validation** — check types and values are in valid ranges
3. **Manual invocation** — verify command appears in `/help` and executes
4. **Argument testing** — test with no args, single arg, multiple args, special characters
5. **File reference testing** — verify `@` syntax loads file contents
6. **Bash execution testing** — verify `` !`command` `` output is included
7. **Integration testing** — verify command works with hooks, agents, MCP servers

Source: Adapted from Anthropic's plugin-dev command-development
references/frontmatter-reference.md, references/documentation-patterns.md,
and references/testing-strategies.md.
