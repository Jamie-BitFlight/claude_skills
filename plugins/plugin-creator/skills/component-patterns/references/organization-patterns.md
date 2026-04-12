# Organization Patterns by Component Type

Detailed directory structures, scaling strategies, and when-to-use guidance for each plugin component type. Companion to [SKILL.md](../SKILL.md) which provides the component selection framework.

SOURCE: All patterns adapted from `../claude-plugins-official/plugins/plugin-dev/skills/plugin-structure/references/component-patterns.md` (568 lines, accessed 2026-03-24). Adapted to plugin-creator conventions — no verbatim copy.

## Command Organization

Commands use the legacy `.claude/commands/` format. For new work, prefer skills with `user-invocable: true`. These patterns remain relevant for maintaining existing command-based plugins.

### Flat Structure

All commands in a single directory:

```text
commands/
├── build.md
├── test.md
├── deploy.md
├── review.md
└── docs.md
```

Use when you have 5-15 commands at the same abstraction level with no clear categorization. Simple to navigate, no configuration needed, fast discovery.

### Categorized Structure

Multiple directories for different command types:

```text
commands/              # Core commands
├── build.md
└── test.md

admin-commands/        # Administrative
├── configure.md
└── manage.md

workflow-commands/     # Workflow automation
├── review.md
└── deploy.md
```

Requires explicit registration in `plugin.json`:

```json
{
  "commands": [
    "./commands",
    "./admin-commands",
    "./workflow-commands"
  ]
}
```

Use when you have 15+ commands with clear functional categories or different permission levels.

### Hierarchical Structure

Nested organization for complex plugins:

```text
commands/
├── ci/
│   ├── build.md
│   ├── test.md
│   └── lint.md
├── deployment/
│   ├── staging.md
│   └── production.md
└── management/
    ├── config.md
    └── status.md
```

Claude Code does not auto-discover nested commands. Each subdirectory must be registered explicitly:

```json
{
  "commands": [
    "./commands/ci",
    "./commands/deployment",
    "./commands/management"
  ]
}
```

Use when you have 20+ commands with multi-level categorization.

## Agent Organization

Agents live in `agents/` by default. Every `.md` file in the plugin's `agents/` directory is auto-discovered by Claude Code — **do not** add an `agents` array to `plugin.json` for agents in this default location. Writing the `agents` key (even to add one entry) OVERRIDES auto-discovery: the declared list becomes the complete set and every unlisted agent becomes invisible. The `agents` array exists ONLY for agents stored in non-default paths — and when used, every agent file (default-path and non-default-path) must be listed explicitly. See `.claude/rules/plugin-development.md` for the 2026-03-17 / 2026-04-12 incident history.

### Role-Based

Organize agents by their primary role:

```text
agents/
├── code-reviewer.md
├── test-generator.md
├── documentation-writer.md
└── refactorer.md
```

Use when agents have distinct, non-overlapping responsibilities and users invoke agents manually.

### Capability-Based

Organize by specific domain or technology expertise:

```text
agents/
├── python-expert.md
├── typescript-expert.md
├── api-specialist.md
└── database-specialist.md
```

Use when agents target specific technologies and Claude Code selects them automatically based on capability matching.

### Workflow-Based

Organize by pipeline or workflow stage:

```text
agents/
├── planning-agent.md
├── implementation-agent.md
├── testing-agent.md
└── deployment-agent.md
```

Use when agents serve sequential workflow stages with stage-specific expertise.

## Skill Organization

Skills live in `skills/` by default. Each skill occupies its own subdirectory containing at minimum a `SKILL.md` file. Skills are auto-discovered — do not add a `skills` key to `plugin.json` unless you need to override auto-discovery with explicit paths.

Important constraint: skills do NOT support subdirectory namespacing. All skill directories must sit directly under `skills/` — one level deep only. Nested skill directories silently fail to register.

### Topic-Based

Each skill covers a specific knowledge domain:

```text
skills/
├── api-design/
│   └── SKILL.md
├── error-handling/
│   └── SKILL.md
├── testing-strategies/
│   └── SKILL.md
└── performance-optimization/
    └── SKILL.md
```

Use for knowledge-based skills, educational or reference content, and broadly applicable guidance.

### Tool-Based

Skills for specific tools or technologies:

```text
skills/
├── docker/
│   ├── SKILL.md
│   └── references/
│       └── dockerfile-best-practices.md
├── kubernetes/
│   ├── SKILL.md
│   └── references/
│       └── deployment-patterns.md
└── terraform/
    ├── SKILL.md
    └── scripts/
        └── validate-config.sh
```

Use for tool-specific expertise, complex tool configurations, and tool best practices.

### Workflow-Based

Skills for complete multi-step processes:

```text
skills/
├── code-review-workflow/
│   ├── SKILL.md
│   └── references/
│       ├── checklist.md
│       └── standards.md
├── deployment-workflow/
│   ├── SKILL.md
│   └── scripts/
│       ├── pre-deploy.sh
│       └── post-deploy.sh
└── testing-workflow/
    ├── SKILL.md
    └── references/
        └── test-structure.md
```

Use for multi-step processes, company-specific workflows, and process automation.

### Rich Resources

Comprehensive skill with all resource types (progressive disclosure):

```text
skills/
└── api-testing/
    ├── SKILL.md              # Core skill — overview, decision trees, workflow
    ├── references/
    │   ├── rest-api-guide.md
    │   ├── graphql-guide.md
    │   └── authentication.md
    ├── scripts/
    │   ├── run-tests.sh
    │   └── generate-report.py
    └── assets/
        └── test-template.json
```

Resource usage:

- `SKILL.md` — overview and when to use each resource (loaded when skill triggers)
- `references/` — detailed guides loaded on demand by Claude
- `scripts/` — executable automation, can run without loading into context
- `assets/` — templates and configurations used in output, not loaded into context

## Hook Organization

Hooks are defined in `hooks/hooks.json` and optionally backed by scripts in `hooks/scripts/`. The `hooks.json` file is auto-discovered — no need to add a `hooks` field to `plugin.json`.

### Monolithic Configuration

Single configuration file with all hooks:

```text
hooks/
├── hooks.json     # All hook definitions
└── scripts/
    ├── validate-write.sh
    ├── validate-bash.sh
    └── load-context.sh
```

Use when you have up to 10 hooks with simple logic and centralized configuration.

### Event-Based

Organize hook scripts by event type:

```text
hooks/
├── hooks.json
└── scripts/
    ├── pre-tool-use/
    │   ├── validate-write.sh
    │   └── validate-bash.sh
    ├── post-tool-use/
    │   └── lint-output.sh
    └── stop/
        └── cleanup.sh
```

Use when you have 10+ hooks and different teams or concerns manage different event types.

### Purpose-Based

Group hook scripts by functional purpose:

```text
hooks/
├── hooks.json
└── scripts/
    ├── security/
    │   ├── validate-paths.sh
    │   ├── check-credentials.sh
    │   └── scan-output.sh
    ├── quality/
    │   ├── lint-code.sh
    │   ├── check-tests.sh
    │   └── verify-docs.sh
    └── workflow/
        ├── notify-team.sh
        └── update-status.sh
```

Use when you have many hook scripts with clear functional boundaries or team specialization.

## Script Organization

Scripts in `scripts/` at the plugin root are shared utilities. Scripts inside skill or hook directories are scoped to that component.

### Flat

All scripts in a single directory:

```text
scripts/
├── build.sh
├── test.py
├── deploy.sh
├── validate.js
└── report.py
```

Use when you have 5-10 related scripts for a simple plugin.

### Categorized

Group scripts by purpose:

```text
scripts/
├── build/
│   ├── compile.sh
│   └── package.sh
├── test/
│   ├── run-unit.sh
│   └── run-integration.sh
├── deploy/
│   ├── staging.sh
│   └── production.sh
└── utils/
    ├── log.sh
    └── notify.sh
```

Use when you have 10+ scripts with clear categories and reusable utilities.

### Language-Based

Group scripts by programming language:

```text
scripts/
├── bash/
│   ├── build.sh
│   └── deploy.sh
├── python/
│   ├── analyze.py
│   └── report.py
└── javascript/
    ├── bundle.js
    └── optimize.js
```

Use when scripts span multiple languages with different runtime requirements.
