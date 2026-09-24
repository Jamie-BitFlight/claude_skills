# Fork Mode

SOURCE: <https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation> (accessed 2026-09-24)

Fork mode is enabled by default in interactive Claude Code.

---

## What a fork is

A fork is a subagent that inherits the **entire conversation so far** instead of starting fresh. It sees the same system prompt, tools, model, and message history as the main session.

- Fork's own tool calls stay out of your conversation
- Only its final result comes back to the main context
- Your main context window stays clean

Use a fork when a named subagent would need too much background context to be useful, or when you want to try several approaches in parallel from the same starting point.

---

## Starting a fork

```bash
/subtask draft unit tests for the parser changes so far
```

Works in interactive mode, non-interactive mode (`-p`), and the Agent SDK.

---

## What changes when fork mode is enabled

Three behaviors change:

1. **Fork is a distinct requested type**: Claude may request the `fork` subagent type. When Claude requests no type, it gets `general-purpose`; subagents spawned from named definitions such as Explore, Plan, and custom agents work as usual.
2. **Claude-spawned subagents run in the background**: Forks and non-fork subagents run in the background apart from documented foreground exceptions. Every background subagent surfaces permission prompts in the main session, naming the subagent that is asking.
3. **`/subtask` starts a fork**. `/fork` applied only in versions v2.1.161-v2.1.211.

---

## /subtask command

```text
/subtask draft unit tests for the parser changes so far
```

Claude Code names the fork from the first words of the directive. The fork appears in a panel below your prompt and runs in the background while you continue working. When it finishes, its result arrives as a message in your main conversation.

---

## Observe and steer running forks

Running forks appear in a panel below the prompt input, with one row for the main session and one for each fork.

| Key | Action |
|:----|:-------|
| `↑` / `↓` | Move between rows |
| `Enter` | Open the selected fork's transcript; send follow-up messages |
| `x` | Dismiss a finished fork or stop a running one |
| `Esc` | Return focus to the prompt input |

---

## Forks vs named subagents

| | Fork | Named subagent |
|:-|:-----|:---------------|
| Context | Full conversation history inherited | Fresh context with the delegation prompt |
| System prompt and tools | Same as main session | From the subagent's definition file |
| Model | Same as main session | From the subagent's `model` field |
| Permissions | Prompts surface in your main session | Prompts surface in your main session when running in background |
| Prompt cache | **Shared with main session** (cheaper) | Separate cache |

Because a fork's system prompt and tool definitions are identical to the parent, its first request reuses the parent's prompt cache — making forking cheaper than spawning a fresh subagent for tasks needing the same context.

When Claude spawns a fork through the Agent tool, it can pass `isolation: "worktree"` so the fork's file edits go to a separate git worktree instead of your checkout.

---

## Limitations

- A fork cannot spawn further forks
- To keep spawns synchronous, set `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` alongside fork mode

SOURCE: <https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation> (accessed 2026-09-24)
