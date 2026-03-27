---
name: component-patterns
description: 'Decide which plugin component type to use and how to organize components at scale. Covers the component lifecycle (discovery and activation phases), decision framework for choosing between commands, skills, agents, hooks, and MCP servers, and organization patterns for each component type. Use when asking "which component type should I use", "command vs skill vs agent", "when to use a hook vs MCP server", "component lifecycle", "how to organize plugin components", "plugin structure patterns", or "scale a plugin with many components".'
user-invocable: true
---

## Component Lifecycle

Every plugin component goes through two phases — discovery at startup and activation at runtime.

### Discovery Phase

When Claude Code starts, it processes each enabled plugin:

1. Scan enabled plugins — read `.claude-plugin/plugin.json`
2. Discover components — search default and custom paths
3. Parse definitions — read YAML frontmatter and configuration files
4. Register components — make available to Claude Code
5. Initialize — start MCP servers, register hooks

Discovery happens once during Claude Code initialization, not continuously. Components added after startup require a session restart to become available.

### Activation Phase

Each component type activates through a different mechanism:

```mermaid
flowchart LR
    User["User action"] --> Cmd["Command — user types /command"]
    Context["Task context"] --> Skill["Skill — description matches task"]
    Context --> Agent["Agent — capabilities match task"]
    Event["System event"] --> Hook["Hook — event matches registration"]
    ToolCall["Tool call"] --> MCP["MCP Server — capability matches call"]
```

SOURCE: Adapted from `../claude-plugins-official/plugins/plugin-dev/skills/plugin-structure/references/component-patterns.md` lines 1-27

## Component Selection Framework

Use this decision tree to select the right component type for a given need.

```mermaid
flowchart TD
    Start(["What do you need<br>to add to your plugin?"]) --> Q1{"Does it need to<br>intercept or validate<br>tool calls or events?"}
    Q1 -->|"Yes — gate writes,<br>enforce policies,<br>inject context on events"| Hook["Use a Hook<br>Create with /plugin-creator:hook-creator"]
    Q1 -->|No| Q2{"Does it provide<br>external tool access<br>via API or process?"}
    Q2 -->|"Yes — database queries,<br>API calls, file processing<br>via external process"| MCP["Use an MCP Server<br>Create with /fastmcp-creator"]
    Q2 -->|No| Q3{"Does it need its own<br>identity, tools, model,<br>or permission scope?"}
    Q3 -->|"Yes — specialized worker<br>with restricted tools<br>or different model"| Agent["Use an Agent<br>Create with /plugin-creator:agent-creator"]
    Q3 -->|No| Q4{"Is it domain knowledge,<br>a workflow, or a<br>procedural guide?"}
    Q4 -->|"Yes — reference material,<br>multi-step process,<br>best practices"| Skill["Use a Skill<br>Create with /plugin-creator:skill-creator"]
    Q4 -->|"No — simple user-triggered<br>action with bash execution"| Command["Use a Command (legacy)<br>See /plugin-creator:command-development"]

    Hook --> HookNote["Events — PreToolUse, PostToolUse,<br>Stop, Notification, SubagentStop"]
    MCP --> MCPNote["Transports — stdio, SSE,<br>HTTP, WebSocket"]
    Agent --> AgentNote["Frontmatter — name, description,<br>tools, model, skills, hooks"]
    Skill --> SkillNote["Progressive disclosure —<br>SKILL.md + references/"]
    Command --> CmdNote["Legacy format —<br>prefer skills for new work"]
```

### Quick Reference

```mermaid
flowchart TD
    subgraph Components["Component Capabilities"]
        direction LR
        H["Hook"]
        M["MCP Server"]
        A["Agent"]
        S["Skill"]
        C["Command"]
    end

    subgraph Traits["Key Differentiators"]
        direction LR
        H --- HT["Intercepts events and tool calls<br>Can block or modify operations<br>Runs on system events"]
        M --- MT["Provides tools via external process<br>Persistent server with its own state<br>Accessed through tool calls"]
        A --- AT["Has its own identity and tool scope<br>Can use a different model<br>Selected by capability matching"]
        S --- ST["Provides knowledge and workflows<br>Activated by context matching<br>Progressive disclosure via references/"]
        C --- CT["User-triggered via /name<br>Can execute bash commands<br>Legacy — skills preferred for new work"]
    end
```

SOURCE: Decision framework derived from component capabilities documented in `../claude-plugins-official/plugins/plugin-dev/skills/plugin-structure/references/component-patterns.md` and `/plugin-creator:claude-plugins-reference-2026`

## Organization Patterns by Component Type

For detailed organization patterns (directory structures, scaling strategies, when-to-use guidance) for each component type, see [component organization reference](./references/organization-patterns.md).

Summary of available patterns:

```mermaid
flowchart TD
    subgraph Commands["Command Patterns"]
        CF["Flat — up to 15 commands"]
        CC["Categorized — 15+ with functional groups"]
        CH["Hierarchical — 20+ with nested structure"]
    end

    subgraph Agents["Agent Patterns"]
        AR["Role-based — distinct non-overlapping roles"]
        AC["Capability-based — technology or domain expertise"]
        AW["Workflow-based — pipeline stage specialists"]
    end

    subgraph Skills["Skill Patterns"]
        ST["Topic-based — knowledge and reference content"]
        SL["Tool-based — specific tool or technology expertise"]
        SW["Workflow-based — multi-step process automation"]
        SR["Rich resources — SKILL.md + references/ + scripts/ + assets/"]
    end

    subgraph Hooks["Hook Patterns"]
        HM["Monolithic — single hooks.json, up to 10 hooks"]
        HE["Event-based — separate config per event type"]
        HP["Purpose-based — grouped by security, quality, workflow"]
    end
```

## Cross-Component Patterns

When plugins grow beyond simple single-component designs, these patterns help manage complexity.

### Shared Resources

Components can share common utilities via a `lib/` directory at the plugin root:

```text
plugin/
├── commands/
│   └── test.md        # references lib/test-utils.sh
├── agents/
│   └── tester.md      # references lib/test-utils.sh
├── hooks/
│   └── scripts/
│       └── pre-test.sh # sources lib/test-utils.sh
└── lib/
    ├── test-utils.sh
    └── deploy-utils.sh
```

Access shared resources via `${CLAUDE_PLUGIN_ROOT}/lib/` in scripts.

### Layered Architecture

Separate concerns into layers for large plugins (100+ files):

```text
plugin/
├── commands/          # User interface layer
├── agents/            # Orchestration layer
├── skills/            # Knowledge layer
└── lib/
    ├── core/          # Core business logic
    ├── integrations/  # External service adapters
    └── utils/         # Shared helper functions
```

### Modular Extensions

Optional features as self-contained modules within the plugin:

```text
plugin/
├── .claude-plugin/
│   └── plugin.json
├── core/
│   ├── commands/
│   └── agents/
└── extensions/
    ├── extension-a/
    │   ├── commands/
    │   └── agents/
    └── extension-b/
        ├── commands/
        └── agents/
```

Register extension paths in `plugin.json` under `commands` and `agents` arrays. Note that listing paths explicitly overrides auto-discovery — all paths must be listed or unlisted components become invisible.

SOURCE: Cross-component patterns adapted from `../claude-plugins-official/plugins/plugin-dev/skills/plugin-structure/references/component-patterns.md` lines 448-535

## Best Practices

- **Start simple** — use flat structures, reorganize when growth demands it
- **Consistent naming** — match file names to component purpose using full descriptive words
- **Minimize nesting** — deep directory structures slow discovery and increase configuration burden
- **Use defaults** — rely on auto-discovery paths (`commands/`, `agents/`, `skills/`) before adding custom paths to `plugin.json`
- **Separate concerns** — do not mix unrelated functionality in the same component
- **Plan for growth** — choose structures that scale without requiring full reorganization

## Related Skills

- For creating hooks — `/plugin-creator:hook-creator`
- For creating agents — `/plugin-creator:agent-creator`
- For creating skills — `/plugin-creator:skill-creator`
- For MCP server creation — `/fastmcp-creator`
- For command development (legacy) — `/plugin-creator:command-development`
- For full plugin lifecycle — `/plugin-creator:plugin-lifecycle`
- For plugin structure and plugin.json schema — `/plugin-creator:claude-plugins-reference-2026`
- For plugin settings and .local.md patterns — `/plugin-creator:plugin-settings`
