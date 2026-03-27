---
name: command-development
description: 'Create and configure slash commands for Claude Code — the legacy .claude/commands/ format. Use when asked to "create a slash command", "add a command", "write a custom command", "define command arguments", "use command frontmatter", "organize commands", "create command with file references", "interactive command", "use AskUserQuestion in command", or for guidance on slash command structure, YAML frontmatter fields, dynamic arguments, bash execution in commands, user interaction patterns, or command development best practices. Commands are the legacy format superseded by skills — for new development prefer /plugin-creator:skill-creator'
---

# Command Development for Claude Code

> **Legacy Format Notice.** The `.claude/commands/` directory is a legacy format.
> For new development, use `.claude/skills/<name>/SKILL.md` instead.
> Both formats are loaded identically — the only difference is file layout.
> Use `/plugin-creator:skill-creator` for the preferred skills format.
>
> Commands remain fully supported for backward compatibility and are still
> appropriate when maintaining existing command sets or contributing to
> projects that use the commands/ convention.

## What Commands Are

Slash commands are Markdown files containing prompts that Claude executes when
invoked via `/command-name`. They provide reusable, consistent, shareable
workflows with quick access to complex prompts.

**Commands are instructions FOR Claude, not messages TO users.** When a user
invokes `/command-name`, the command content becomes Claude's instructions.
Write commands as directives to Claude about what to do.

```markdown
<!-- Correct: instructions for Claude -->
Review this code for security vulnerabilities including:
- SQL injection
- XSS attacks
- Authentication issues

Provide specific line numbers and severity ratings.
```

```markdown
<!-- Wrong: message to user — Claude receives this but has no directive -->
This command will review your code for security issues.
You'll receive a report with vulnerability details.
```

## Command Locations

```mermaid
flowchart TD
    Q{"Where should the<br>command live?"}
    Q -->|"Shared with team"| Proj[".claude/commands/<br>Scope — this project only<br>Label — '(project)' in /help"]
    Q -->|"Personal use<br>across all projects"| User["~/.claude/commands/<br>Scope — all projects<br>Label — '(user)' in /help"]
    Q -->|"Bundled with a plugin"| Plugin["plugin-name/commands/<br>Scope — when plugin installed<br>Label — '(plugin-name)' in /help"]
```

## File Format

Commands are `.md` files. No frontmatter is required for basic commands.

```text
.claude/commands/
├── review.md           # /review
├── test.md             # /test
└── deploy.md           # /deploy
```

Add YAML frontmatter for configuration:

```markdown
---
description: Review code for security issues
allowed-tools: Read, Grep, Bash(git:*)
model: sonnet
---

Review this code for security vulnerabilities...
```

## Frontmatter Fields (Summary)

All fields are optional. Commands work without any frontmatter.

```mermaid
flowchart TD
    Start(["Writing command frontmatter"]) --> D{"Need a description<br>in /help?"}
    D -->|Yes| Desc["description — string, under 60 chars<br>Start with verb — Review, Deploy, Generate"]
    D -->|No| AT{"Need to restrict<br>tool access?"}
    Desc --> AT
    AT -->|Yes| Tools["allowed-tools — comma-separated or array<br>Bash(git:*) for filtered bash access"]
    AT -->|No| M{"Need a specific<br>model?"}
    Tools --> M
    M -->|Yes| Model["model — haiku, sonnet, or opus"]
    M -->|No| AH{"Command takes<br>arguments?"}
    Model --> AH
    AH -->|Yes| Hint["argument-hint — e.g. [pr-number] [priority]"]
    AH -->|No| DMI{"Should only user<br>invoke manually?"}
    Hint --> DMI
    DMI -->|Yes| Disable["disable-model-invocation — true"]
    DMI -->|No| Done(["Frontmatter complete"])
    Disable --> Done
```

For the complete field specification with examples, validation rules, and edge
cases, see [./references/frontmatter-fields.md](./references/frontmatter-fields.md).

## Dynamic Arguments

### Positional Arguments

Capture individual arguments with `$1`, `$2`, `$3`:

```markdown
---
description: Review PR with priority and assignee
argument-hint: [pr-number] [priority] [assignee]
---

Review pull request #$1 with priority level $2.
After review, assign to $3 for follow-up.
```

Running `/review-pr 123 high alice` expands to:
`Review pull request #123 with priority level high. After review, assign to alice for follow-up.`

### $ARGUMENTS

Capture all arguments as a single string:

```markdown
---
argument-hint: [issue-number]
---

Fix issue #$ARGUMENTS following our coding standards.
```

### File References with @

Include file contents using `@` syntax:

```markdown
Review @$1 for code quality and potential bugs.
```

Running `/review-file src/api/users.ts` causes Claude to read `src/api/users.ts`
before processing the command.

Static references also work: `Review @package.json and @tsconfig.json for consistency.`

## Bash Execution

Execute shell commands inline with `` !`command` `` syntax to gather dynamic context:

```markdown
---
allowed-tools: Bash(git:*)
---

Files changed: !`git diff --name-only`

Review each file for code quality and potential bugs.
```

The command output replaces the placeholder before Claude processes the prompt.
Ensure `allowed-tools` includes the appropriate Bash filter.

## Command Organization

```mermaid
flowchart TD
    Q{"How many commands?"}
    Q -->|"5-15, no clear categories"| Flat["Flat structure<br>.claude/commands/*.md"]
    Q -->|"15+, clear categories"| NS["Namespaced structure<br>.claude/commands/ci/*.md<br>.claude/commands/git/*.md<br>.claude/commands/docs/*.md"]
```

Subdirectory names become namespaces shown in `/help`. For example,
`.claude/commands/ci/build.md` appears as `/build (project:ci)`.

## Common Patterns

### Review Pattern

```markdown
---
description: Review code changes
allowed-tools: Read, Bash(git:*)
---

Files changed: !`git diff --name-only`

Review each file for:
1. Code quality and style
2. Potential bugs or issues
3. Test coverage
4. Documentation needs
```

### Testing Pattern

```markdown
---
description: Run tests for specific file
argument-hint: [test-file]
allowed-tools: Bash(npm:*)
---

Run tests: !`npm test $1`

Analyze results and suggest fixes for failures.
```

### Workflow Pattern

```markdown
---
description: Complete PR workflow
argument-hint: [pr-number]
allowed-tools: Bash(gh:*), Read
---

PR #$1 Workflow:

1. Fetch PR: !`gh pr view $1`
2. Review changes
3. Run checks
4. Approve or request changes
```

## Best Practices

1. **Single responsibility** — one command, one task
2. **Clear descriptions** — self-explanatory in `/help`, under 60 chars
3. **Document arguments** — always provide `argument-hint`
4. **Restrict tools** — use most restrictive `allowed-tools` that works; prefer `Bash(git:*)` over `Bash(*)`
5. **Consistent naming** — use verb-noun pattern (review-pr, fix-issue)
6. **Validate inputs** — check for required arguments early in the prompt
7. **Handle errors** — consider missing or invalid arguments

## Interactive Commands (AskUserQuestion)

For commands that need complex user input beyond simple arguments, use the
`AskUserQuestion` tool. This enables multi-choice decisions, multi-select
scenarios, and conditional workflows.

```mermaid
flowchart TD
    Q{"What kind of<br>user input?"}
    Q -->|"Simple values —<br>file paths, numbers"| Args["Use command arguments<br>argument-hint + positional vars"]
    Q -->|"Complex choices —<br>multiple options with trade-offs"| AUQ["Use AskUserQuestion<br>Include in allowed-tools"]
    Q -->|"Both"| Both["Arguments for known values<br>AskUserQuestion for decisions"]
```

For complete AskUserQuestion patterns including multi-stage workflows,
conditional flows, multi-select, and validation loops, see
[./references/interactive-commands.md](./references/interactive-commands.md).

## Advanced Workflows

Commands can implement multi-step sequences, maintain state across invocations
using `.local.md` files, coordinate with other commands, and compose into
pipeline workflows.

For state management, command composition, workflow recovery, and error handling
patterns, see [./references/advanced-workflows.md](./references/advanced-workflows.md).

## Plugin Command Features

Plugin commands have access to `${CLAUDE_PLUGIN_ROOT}` for portable paths to
plugin resources, auto-discovery from the `commands/` directory, and can
integrate with plugin agents, skills, and hooks.

For CLAUDE_PLUGIN_ROOT patterns, plugin component integration, validation
patterns, and marketplace distribution guidance, see
[./references/plugin-command-patterns.md](./references/plugin-command-patterns.md).

## Troubleshooting

```mermaid
flowchart TD
    P{"What is the problem?"}
    P -->|"Command not appearing<br>in /help"| NotAppearing["Check file is in correct directory<br>Verify .md extension<br>Ensure valid Markdown format<br>Restart Claude Code"]
    P -->|"Arguments not<br>substituting"| ArgsNotWorking["Verify dollar-sign N syntax<br>Check argument-hint matches usage<br>Ensure no extra spaces"]
    P -->|"Bash execution<br>failing"| BashFail["Check allowed-tools includes Bash<br>Verify command syntax in backticks<br>Test command in terminal first<br>Check required permissions"]
    P -->|"File references<br>not loading"| FileFail["Verify @ syntax correct<br>Check file path is valid<br>Ensure Read tool allowed<br>Use project-relative paths"]
```

## Related Skills

- For the preferred skills format: `/plugin-creator:skill-creator`
- For hook development: `/plugin-creator:hooks-guide`
- For agent creation: `/plugin-creator:agent-creator`
- For plugin lifecycle: `/plugin-creator:plugin-lifecycle`
- For plugin structure and component selection: `/plugin-creator:component-patterns`
- For command documentation and testing strategies: see [./references/frontmatter-fields.md](./references/frontmatter-fields.md) validation section

Source: Adapted from Anthropic's `plugin-dev:command-development` skill
(../claude-plugins-official/plugins/plugin-dev/skills/command-development/, 11 files).
