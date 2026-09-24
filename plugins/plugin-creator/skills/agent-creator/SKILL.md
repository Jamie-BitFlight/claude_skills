---
name: agent-creator
description: Create or adapt Claude Code agent definitions. Use when creating an agent, changing subagent configuration, selecting agent scope, or designing a specialized delegation role.
model: sonnet
user-invocable: true
---

If the request is not agent creation or adaptation, route through
`/plugin-creator:plugin-lifecycle`.

# Agent Creator

Create the smallest agent definition that satisfies the requested runtime behavior.

## Authority Pointers

- Activate `/plugin-creator:claude-subagent-reference` for the canonical frontmatter fields,
  scope rules, plugin restrictions, tool permissions, models, memory, hooks, nesting, and examples.
- Read [references/agent-schema.md](./references/agent-schema.md) only for creation-specific YAML,
  MCP naming, and validation constraints.
- Read [references/agent-templates.md](./references/agent-templates.md) only when the request needs a
  role-based supervisor contract or no similar local agent exists.
- Read [references/agent-examples.md](./references/agent-examples.md) only when a concrete full-file
  example is needed.

Every path, command, fact, and cross-plugin reference in the result must be available in every
target environment, bundled and reached by a relative path, or inlined. A harness variable counts
only where that harness substitutes it.

## Workflow

### 1. Discover

Inspect agents in the requested scope and identify a similar definition before creating one. Read
the candidate completely and inventory conventions that are enforced by repository instructions.

Gate: record the target scope, destination path, nearest reusable agent or template, and any local
conventions that affect the result.

### 2. Resolve Requirements

Establish the agent's single responsibility, activation branches, required inputs, write boundary,
minimum tools, model needs, skill dependencies, and caller-visible output. Ask one focused question
only when a missing choice changes executable behavior.

For an orchestrated agent, require an explicit `STATUS: DONE` / `STATUS: BLOCKED` handoff and read
the role-based material in `references/agent-templates.md`. For a user-facing agent, adapt the
nearest local pattern and omit orchestration machinery.

Gate: every field and body step maps to a stated requirement; unresolved behavior choices block
creation.

### 3. Write

Start with the executable minimum and add optional fields only when required:

```markdown
---
name: {agent-name}
description: '{What it does}. Use when {distinct activation branches}.'
model: {current supported alias or inherit}
tools: {minimum allowlist, when restriction is required}
---

# {Agent Title}

{Single objective.}

## Workflow

1. {Action with a checkable completion criterion.}

## Output Contract

{Exact caller-visible success and blocked forms.}
```

Use plain portable skill notation (`/plugin-name:skill-name`) and agent names
(`plugin-name:agent-name`) in instructions. Preserve ecosystem-owned frontmatter fields when
adapting an existing file.

Gate: the body states ordered work, a checkable completion bound, all authority pointers needed at
runtime, and the complete output contract.

### 4. Place

- Project: `.claude/agents/{agent-name}.md`
- User: `~/.claude/agents/{agent-name}.md`
- Plugin: `{plugin-root}/agents/{agent-name}.md`

For plugin agents, leave `plugin.json` absent when default component paths are sufficient. If a
manifest exists and has no `agents` field, leave the field absent so default discovery continues.
If `agents` already exists, preserve its replacement allowlist and add the new path plus every
default-path agent that must remain loaded.

Gate: the file exists at the selected scope and plugin discovery behavior is unchanged except for
the requested agent.

### 5. Validate

Run:

```text
uvx skilllint@latest check {agent-path}
```

For a plugin agent, also run:

```text
claude plugin validate {plugin-root}          # plugin with a manifest
claude plugin validate {plugin-root}/agents   # manifestless plugin
```

When a manifest already has an explicit `agents` field, run
`uv run plugins/plugin-creator/scripts/check_agent_auto_discovery.py {plugin-root}/.claude-plugin/plugin.json`.
Fix every error and warning before completion. Restart the target Claude Code session after direct
on-disk agent changes so it reloads the definition.

Gate: frontmatter, plugin discovery, links, dependencies, and required tool access all pass.

## Output Contract

```text
STATUS: DONE
Agent: {name}
Path: {path}
Scope: {project, user, or plugin}
Discovery: {default path or explicit manifest path}
Authority: {references used}
Validation: {commands and exact results}
```

```text
STATUS: BLOCKED
Reason: {specific missing input or failed gate}
Completed: {verified work}
Remaining: {uncompleted work}
```
