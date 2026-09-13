# Output Style Schema and Mechanics

SOURCE: [Output styles](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

## File Shape

An output style is a markdown file: YAML frontmatter, then the instructions Claude receives. The
body replaces Claude Code's default system instructions. Setting `keep-coding-instructions: true`
retains the built-in software engineering instructions on top of it.

## Frontmatter Fields

| Field | Purpose | Default |
| --- | --- | --- |
| `name` | Display name of the style | Inherits from the filename |
| `description` | Shown in the `/config` picker | None |
| `keep-coding-instructions` | Keep Claude Code's built-in software engineering instructions | `false` |
| `force-for-plugin` | Plugin styles only: apply automatically whenever the plugin is enabled, overriding the user's `outputStyle` setting. When several enabled plugins set it, the first plugin loaded wins | `false` |

Keep `description` on a single line. `scripts/validate_output_style.py check` enforces it along
with the field types above, so run the script rather than checking frontmatter by hand.

## Install Locations

| Scope | Path |
| --- | --- |
| User | `~/.claude/output-styles` |
| Project | `.claude/output-styles` |
| Managed policy | `.claude/output-styles` inside the managed settings directory |
| Plugin | `output-styles/` at the plugin root |

Project styles load from every `.claude/output-styles/` directory between the working directory and
the repository root. When more than one of those directories defines a style with the same name, the
one closest to the working directory wins.

## Selecting a Style

| Surface | Action | Requires |
| --- | --- | --- |
| Terminal | `/config` → Output style; writes `.claude/settings.local.json` | — |
| VS Code extension | `/` command menu → Output styles | v2.1.257 or later |
| VS Code extension | Create a style file from the Output styles menu | v2.1.261 or later |
| Desktop app | Set `outputStyle` in a settings file; `/config` opens Settings → Claude Code | — |
| Any | Edit `outputStyle` directly | — |

```json
{
  "outputStyle": "Explanatory"
}
```

Settings precedence, highest first: managed settings, command-line arguments passed when starting
`claude`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`.
SOURCE: [Settings files and precedence](https://code.claude.com/docs/en/settings) (accessed 2026-09-13)

The standalone `/output-style` command was deprecated in v2.1.73 and removed in v2.1.91.

## When a Change Takes Effect

- Switching styles mid-session applies from the next message. Before v2.1.251, the new style applied
  only after `/clear` or a new session.
- In the terminal, style files are read at startup. Creating or editing a file during a running
  session requires a restart before Claude Code sees it.

## Scope Boundary: Subagents and Forks

Output styles apply to the main conversation and to a fork, which inherits the parent's full
conversation and system prompt. Other subagents run their own system prompt, so a style does not
shape their responses. Behavior that must hold inside delegated work belongs in the agent
definition, not in a style.
SOURCE: [Subagents](https://code.claude.com/docs/en/sub-agents) (accessed 2026-09-13)

## Packaging in a Plugin

Styles in the plugin's `output-styles/` directory are auto-discovered when the plugin has no
manifest, or has a manifest that does not declare `outputStyles`.

```text
plugin-root/
└── output-styles/
    └── terse.md
```

The `outputStyles` manifest key accepts a string or an array of `./`-relative paths and REPLACES the
default directory scan. Declaring it without listing `./output-styles/` makes every style in that
directory invisible.

```json
{
  "outputStyles": ["./output-styles/", "./extras/"]
}
```

Claude Code warns about an ignored default folder in `claude plugin list` and in the `/plugin` detail
view when both a default folder and the matching manifest key exist.
SOURCE: [Plugins reference](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-13)

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| New style absent from the `/config` picker | File created during a running terminal session | Restart Claude Code; style files are read at startup. For a plugin-bundled style, `/reload-plugins` also picks it up |
| Style picked but behavior unchanged | Change applies from the next message; on versions before v2.1.251 it needed `/clear` | Send another message, or start a new session |
| Wrong style of the same name applied | Two nested `.claude/output-styles/` directories define it | The directory closest to the working directory wins — rename or remove one |
| User's chosen style overridden | An enabled plugin sets `force-for-plugin: true` | Disable that plugin, or drop the field from the plugin style |
| Plugin styles disappear after a manifest edit | `outputStyles` declared without `./output-styles/` | List the default directory explicitly, or remove the key |
| Claude stops scoping or verifying code changes | Custom style dropped the built-in engineering instructions | Set `keep-coding-instructions: true` |

For configuration that still does not take effect, see
[Debug your configuration](https://code.claude.com/docs/en/debug-your-config).
