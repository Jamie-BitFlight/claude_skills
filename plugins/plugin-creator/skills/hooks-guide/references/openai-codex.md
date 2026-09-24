# OpenAI Codex Plugin Hooks

Keep these semantics separate from Claude Code even where event names match.

## Plugin discovery and paths

- OpenAI discovers `hooks/hooks.json` by default for an enabled plugin.
- `extensions.com.openai.hooks` in root `plugin.json`, or `hooks` in the
  `.codex-plugin/plugin.json` compatibility overlay, replaces default-file discovery rather than
  adding to it.
- Hook paths start with `./`, resolve from the plugin root, and remain inside that root.
- Plugin hook commands receive `PLUGIN_ROOT` and persistent `PLUGIN_DATA`. Codex also supplies
  `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` for compatibility.

SOURCE: <https://developers.openai.com/plugins/build/plugins.md#bundled-mcp-servers-and-lifecycle-hooks>
(accessed 2026-09-24)

## Trust and execution

- Plugin hooks load alongside user, project, and managed hooks.
- Enabling or installing a plugin does not trust its hooks. Codex skips a non-managed hook until
  the user reviews and trusts the current definition; changing the definition changes its hash and
  requires another review.
- Matching hooks from multiple sources all run. Multiple matching command handlers for one event
  launch concurrently, so one cannot prevent another from starting.
- Current Codex supports `command` and `mcp_tool` handlers. It parses but skips `prompt` and `agent`
  handlers.
- Commands use the session working directory. Plugin-root-relative script references therefore use
  `PLUGIN_ROOT` rather than assuming the current directory.
- Hook scripts must exist in the execution environment. Installing a plugin on the web does not
  deploy local scripts; administrators must distribute required scripts separately.

## Platform boundaries

- Codex `PostToolUse` runs after supported tools return, including non-zero Bash exits; Claude Code
  has a separate `PostToolUseFailure` event.
- Codex matching and decision support vary by event. A field accepted by Claude Code can be parsed
  but unsupported in Codex, causing the hook run to fail while the operation continues.
- Synchronous hooks can block only where the event contract permits. Background hooks cannot
  block, approve, rewrite, or otherwise control the triggering operation.
- Treat tool hooks as guardrails, not a complete enforcement boundary: hosted tools and specialized
  paths can bypass the local function-tool hook path.

SOURCE: <https://learn.chatgpt.com/docs/hooks> (accessed 2026-09-24)
