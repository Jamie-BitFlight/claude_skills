# Output Styles — Claude Code Reference

SOURCE: <https://code.claude.com/docs/en/output-styles.md> (accessed 2026-09-13)

Output styles change how Claude responds, not what Claude knows. They set Claude's role, tone, and
output format for every response. A custom style supplies its own instructions and chooses whether
to keep Claude Code's built-in software engineering instructions.

To create one, load `plugin-creator:output-style-creator`. Both files mirror the same upstream page —
re-sync them together via `plugin-creator:skill-sync`.

---

## Built-in Output Styles

| Style | Behavior |
|-------|----------|
| Default | Standard system prompt designed for software engineering tasks |
| Proactive | Executes immediately, makes reasonable assumptions instead of pausing for routine decisions, prefers action over planning. Stronger than auto mode's autonomous-execution guidance and independent of permission mode — the permission mode still decides what runs without asking |
| Concise | Leads with the result, skips preamble and narration, keeps responses short by default while doing the engineering work as thoroughly as Default; answers in full when asked for detail; always keeps error reports, security warnings, and destructive-action confirmations complete. Requires Claude Code v2.1.237 or later |
| Explanatory | Adds educational "Insights" between engineering tasks — explains implementation choices and codebase patterns |
| Learning | Collaborative, learn-by-doing mode — shares "Insights" while coding AND asks the user to contribute small strategic code pieces; adds `TODO(human)` markers in code |

---

## How Output Styles Work

- Claude Code sends the active style's instructions with every request.
- When a style other than Default is selected, Claude Code also reminds Claude of the style during
  the conversation.
- Custom styles omit Claude Code's built-in software engineering instructions — how to scope
  changes, write comments, and verify work — unless `keep-coding-instructions: true` is set.
- Styles apply to the main conversation and to a fork, which inherits the parent's full conversation
  and system prompt. Other subagents run their own system prompt, so styles do not shape their
  responses.

---

## Activating an Output Style

| Surface | Action | Requires |
|---------|--------|----------|
| Terminal | `/config` → Output style; saved to `.claude/settings.local.json` | — |
| VS Code extension | `/` command menu → Output styles (custom styles included) | v2.1.257 or later |
| VS Code extension | Create a style file from the Output styles menu | v2.1.261 or later |
| Desktop app | Set the `outputStyle` field in a settings file; `/config` opens Settings → Claude Code | — |
| Any | Edit `outputStyle` directly in a settings file | — |

```json
{
  "outputStyle": "Explanatory"
}
```

The standalone `/output-style` command was deprecated in v2.1.73 and removed in v2.1.91 — use
`/config` or the `outputStyle` setting.

Switching styles mid-session applies from the next message. Before v2.1.251, the new style applied
only after `/clear` or a new session. In the terminal, style files are read at startup, so restart
Claude Code after creating or editing one during a running session.

SOURCE: <https://code.claude.com/docs/en/output-styles.md> (accessed 2026-09-13)

---

## Custom Output Styles

Markdown files with YAML frontmatter, saved at any of the levels below. The filename becomes the
style name unless `name` is set in the frontmatter.

- `~/.claude/output-styles/` — user level
- `.claude/output-styles/` — project level
- `.claude/output-styles/` inside the managed settings directory — managed policy level

Project styles load from every `.claude/output-styles/` directory between the working directory and
the repository root. When more than one of those directories defines a style with the same name,
Claude Code uses the one closest to the working directory.

### File Format

````markdown
---
name: Diagrams first
description: Lead every explanation with a diagram
keep-coding-instructions: true
---

When explaining code, architecture, or data flow, start with a Mermaid diagram showing the
structure, then explain in prose.

## Diagram conventions

Use `flowchart TD` for control flow and `sequenceDiagram` for request paths. Keep diagrams under
15 nodes.
````

### Frontmatter Fields

| Field | Purpose | Default |
|-------|---------|---------|
| `name` | Name of the output style, if not the file name | Inherits from file name |
| `description` | Description shown in the `/config` picker | None |
| `keep-coding-instructions` | Keep Claude Code's built-in software engineering instructions | `false` |
| `force-for-plugin` | Plugin output styles only: apply automatically whenever the plugin is enabled, overriding the user's `outputStyle` setting. If multiple enabled plugins set this, the first one loaded wins | `false` |

---

## Plugin Integration

Plugins ship output styles in an `output-styles/` directory at the plugin root, auto-discovered when
the manifest does not declare `outputStyles`.

```text
plugin-root/
└── output-styles/
    └── terse.md
```

The `outputStyles` field in `plugin.json` accepts a string or an array of `./`-relative paths and
REPLACES the default directory scan. Declaring it without listing `./output-styles/` makes every
style in that directory invisible.

```json
{
  "outputStyles": ["./output-styles/", "./extras/"]
}
```

Claude Code warns about an ignored default folder in `claude plugin list` and in the `/plugin` detail
view when both a default folder and the matching manifest key exist.

SOURCE: <https://code.claude.com/docs/en/plugins-reference.md> (accessed 2026-09-13)

---

## Token Costs and Prompt Caching

A style's instructions add input tokens on every request; prompt caching reduces this cost after the
first request in a session. For the cost of the first request after a mid-session switch, see
<https://code.claude.com/docs/en/prompt-caching> (accessed 2026-09-13).

The built-in Explanatory and Learning styles produce longer responses than Default by design, which
increases output tokens. Concise does the opposite. For custom styles, output token usage depends on
what the instructions tell Claude to produce.

SOURCE: <https://code.claude.com/docs/en/output-styles.md> (accessed 2026-09-13)

---

## Comparison to Related Features

| Feature | How it works | Use it when |
|---------|--------------|-------------|
| Output styles | Changes Claude Code's default instructions; active every turn once selected | A different role, tone, or default response format is wanted every turn |
| CLAUDE.md | Adds a user message after the system prompt; removes nothing | Claude should always know project conventions and codebase context |
| `--append-system-prompt` | Appends to the system prompt without removing anything | A one-off addition passed as a CLI flag at launch |
| Agents | Runs a subagent with its own system prompt, model, and tools | A separately scoped helper for a focused task is wanted |
| Skills | Loads task-specific instructions when invoked or relevant | There is a reusable workflow |

### Key Distinctions

**Output styles vs CLAUDE.md:** Output styles replace Claude Code's default instructions, including
the software engineering ones unless `keep-coding-instructions` is set. CLAUDE.md adds content as a
user message after the system prompt — it replaces nothing.

**Output styles vs agents:** Output styles shape the main conversation and forks only. Agents are
invoked for specific tasks and configure their own model, tools, and system prompt.

**Output styles vs skills:** Output styles modify HOW Claude responds and stay active for the
session. Skills are task-specific instructions invoked on demand or loaded when relevant — not
persistently active.
