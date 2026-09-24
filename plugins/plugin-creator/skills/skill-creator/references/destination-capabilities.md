# Destination Capabilities Reference

Destination affects which frontmatter fields work and what runtime capabilities are available. Choose destination before writing frontmatter.

| Skill destination | `hooks` in frontmatter | `context: fork` subagent | Direct `/<skill-name>` in `-p` / Agent SDK |
|---|---|---|---|
| Plugin (`plugins/*/skills/`) | Executed at plugin trust level | Fresh context; ordinary depth-limited nesting | Supported when discovered and user-invocable |
| Project (`.claude/skills/`) | Executed at project trust level | Fresh context; ordinary depth-limited nesting | Supported when discovered and user-invocable |
| User (`~/.claude/skills/`) | Executed at user trust level | Fresh context; ordinary depth-limited nesting | Supported when discovered and user-invocable |
| Portable upload/API package | Not portable | Not portable | N/A |

Plugin agents ignore `hooks`, `mcpServers`, and `permissionMode`; these fields do not block startup. See the [Plugin Agent Security Restrictions](../claude-plugins-reference-2026/SKILL.md) section in `claude-plugins-reference-2026`.

**Headless / `-p` mode (any destination):**

Send `/<skill-name>` in the prompt to dispatch a discovered, user-invocable skill directly. This works in `claude -p` and Agent SDK sessions and is independent of the SDK `skills` allowlist.

SOURCE: [headless.md](https://code.claude.com/docs/en/headless.md) (accessed 2026-04-23)

**`context: fork` skill subagents (any Claude Code destination):**

Despite the field name, this is not a conversation fork. The skill content becomes the prompt for a fresh subagent with no conversation history. It follows ordinary depth-limited subagent nesting. A separate conversation fork inherits the full history and cannot spawn another conversation fork.

SOURCE: [Claude Code skills](https://code.claude.com/docs/en/skills#run-skills-in-a-subagent) and [subagents](https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation) (accessed 2026-09-24)

**Portable upload/API package:** only `name`, `description`, `license`, `compatibility`, `metadata`, and experimental `allowed-tools` are accepted. claude.ai uploads, the Skills API, and Anthropic packaging hard-fail unexpected fields.

SOURCE: [Using skill frontmatter outside Claude Code](https://code.claude.com/docs/en/skills#using-skill-frontmatter-outside-claude-code) (accessed 2026-09-24)
