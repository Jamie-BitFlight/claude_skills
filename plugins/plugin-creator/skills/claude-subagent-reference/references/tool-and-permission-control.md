# Tool and Permission Control

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Control subagent capabilities (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/permission-modes.md> (accessed 2026-05-28)

## Tool allowlist (`tools`)

List only the tools the subagent may use. Inherits all tools when omitted.

```yaml
tools: Read, Grep, Glob, Bash
```

The subagent cannot use Edit, Write, Agent, or any MCP tools not in the list.

Write entries comma-and-space separated, matching the documented convention. A comma without a
space, a space-separated string, and a YAML list parse to the same tool set — none of them is an
error.

## Tool denylist (`disallowedTools`)

Remove specific tools from the inherited or specified pool.

```yaml
disallowedTools: Write, Edit
```

When both `tools` and `disallowedTools` are set, `disallowedTools` is applied first, then `tools` is resolved against the remaining pool. A tool listed in both is removed.

## MCP server-level patterns

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Control subagent capabilities (accessed 2026-08-22)

`tools` and `disallowedTools` both accept MCP server-level patterns in addition to exact tool
names. `mcp__<server>` and `mcp__<server>__*` are equivalent — each grants or removes every tool
the named server exposes, and each composes with named tools in the same list.

```yaml
# Read plus every tool from the dh backlog server
tools: Read, mcp__plugin_dh_backlog__*
```

A plugin-bundled MCP server registers under `mcp__plugin_<plugin-name>_<server-name>`, and the
server-level pattern composes with that prefix.

MCP tool names are case-sensitive: `mcp__Ref__ref_read_url` resolves, `mcp__ref__ref_read_url`
matches nothing.

## How entries resolve

SOURCE: <https://code.claude.com/docs/en/errors.md> (accessed 2026-08-22)

An entry that matches no tool is dropped and the rest of the grant still resolves — one bad name
does not empty the list.

When every entry resolves to nothing, the subagent refuses to launch. The error names the agent and
groups the failed entries by cause: `unrecognized` for a name matching no tool, and `recognized but
matched no tools in this session` for a valid pattern with nothing to match.

```text
Agent 'probe-p2-bad-name' would be spawned with zero tools — refusing. Its tools list resolved to nothing: unrecognized [Grpe].
```

A server-level pattern resolves only while that server is connected. A subagent whose `tools` list
contains only MCP entries therefore cannot be invoked at all while the server is down — the same
definition that resolves to the server's full tool set when connected refuses to launch when it is
not:

```text
Agent 'probe-p3-mcp-wildcard' would be spawned with zero tools — refusing. Its tools list resolved to nothing: recognized but matched no tools in this session [mcp__plugin_dh_backlog__*].
```

Grant at least one non-MCP tool to any subagent that must stay invocable regardless of server
state; accept an MCP-only grant only where that hard runtime dependency is intended.

## Restrict which subagent types can be spawned

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Restrict which subagents can be spawned (accessed 2026-05-28)

When an agent runs as the main thread via `claude --agent`, use `Agent(name, name)` syntax in `tools` to allowlist which subagent types it can spawn:

```yaml
tools: Agent(worker, researcher), Read, Bash
```

Only `worker` and `researcher` subagents can be spawned. All other types fail and the agent sees only the allowed types in its prompt.

To allow spawning any subagent without restrictions:

```yaml
tools: Agent, Read, Bash
```

Omit `Agent` from `tools` entirely to prevent the agent from spawning any subagents.

> **Version note**: In v2.1.63, the Task tool was renamed to Agent. `Task(...)` references still work as aliases.

> **Scope note**: `Agent(agent_type)` restrictions only apply to agents running as the main thread with `claude --agent`. Subagents cannot spawn other subagents, so this field has no effect in subagent definitions used as subagents (not as main thread).

## Disable specific subagents globally

SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Disable specific subagents (accessed 2026-05-28)

Add to `permissions.deny` in `settings.json`:

```json
{
  "permissions": {
    "deny": ["Agent(Explore)", "Agent(my-custom-agent)"]
  }
}
```

Or via CLI flag:

```bash
claude --disallowedTools "Agent(Explore)"
```

Works for both built-in and custom subagents.

---

## Permission modes

SOURCE: <https://code.claude.com/docs/en/permission-modes.md> § Available modes (accessed 2026-05-28)
SOURCE: <https://code.claude.com/docs/en/sub-agents.md> § Permission modes (accessed 2026-05-28)

The `permissionMode` frontmatter field controls how the subagent handles permission prompts.

> **Plugin restriction**: `permissionMode` is **silently ignored** for plugin-shipped agents. Copy the agent to `.claude/agents/` to use this field.

| Mode | What runs without asking | Notes |
|:-----|:------------------------|:------|
| `default` | Reads only | Standard permission checking with prompts |
| `acceptEdits` | Reads, file edits, common filesystem commands (`mkdir`, `touch`, `mv`, `cp`, `sed`, `rm`, `rmdir`) | In-scope paths only (working directory or `additionalDirectories`) |
| `auto` | Everything, with background safety checks | Classifier reviews commands. Requires v2.1.83+. Subagent frontmatter `permissionMode` is **ignored** when parent uses auto mode — subagent inherits auto mode |
| `dontAsk` | Only pre-approved tools | Auto-denies anything that would prompt |
| `bypassPermissions` | Everything | ⚠️ Skips all prompts including protected paths. Root/home rm still prompts. Use only in isolated containers/VMs. Requires session was started with `--dangerously-skip-permissions` or equivalent |
| `plan` | Reads only | Plan mode (read-only exploration) |

**Inheritance rules:**

- If the **parent** uses `bypassPermissions` or `acceptEdits`: takes precedence, cannot be overridden by the subagent.
- If the **parent** uses `auto` mode: subagent inherits auto mode and any `permissionMode` in frontmatter is ignored — classifier evaluates the subagent's tool calls with the same rules as the parent session.

**Auto mode and subagents** (v2.1.83+): The classifier checks subagent work at three points:

1. Before spawn — the delegated task description is evaluated
2. During execution — each action goes through the classifier
3. After completion — the full action history is reviewed; if flagged, a security warning is prepended to results

---

## Protected paths

SOURCE: <https://code.claude.com/docs/en/permission-modes.md> § Protected paths (accessed 2026-05-28)

In all modes except `bypassPermissions`, writes to these paths are never auto-approved:

**Protected directories**: `.git`, `.vscode`, `.idea`, `.husky`, `.claude` (except `.claude/commands`, `.claude/agents`, `.claude/skills`, `.claude/worktrees`)

**Protected files**: `.gitconfig`, `.gitmodules`, `.bashrc`, `.bash_profile`, `.zshrc`, `.zprofile`, `.profile`, `.ripgreprc`, `.mcp.json`, `.claude.json`

In `default`, `acceptEdits`, and `plan`: these writes prompt.
In `auto`: routes to classifier.
In `dontAsk`: denied.
In `bypassPermissions`: allowed.
