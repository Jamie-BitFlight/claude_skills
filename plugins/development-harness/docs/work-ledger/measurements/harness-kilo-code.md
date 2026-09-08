# Harness facts: Kilo Code (Kilo CLI / Kilo Code VS Code extension, Kilo-Org/kilocode)

Date of all reads: 2026-09-06. Sources are the product's own GitHub repository at its default
branch `main` (HEAD `78d8d2a3efcc66c1196a0a1bcd2175d73c8a31b3`, confirmed with
`git ls-remote https://github.com/Kilo-Org/kilocode.git HEAD` and reproduced with a shallow clone
whose `git rev-parse HEAD` returns the same hash; the tip commit is dated 2026-09-06), plus the
product docs whose Markdown source lives in that same repository under
`packages/kilo-docs/pages/**`. Every path cited below is repository-relative at that commit.
Source-file claims come from reading the TypeScript at that commit; none were reproduced by
running the CLI or the extension. `packages/opencode/package.json` at that commit declares
`"name": "@kilocode/cli", "version": "7.5.15"`; `packages/kilo-vscode/package.json` declares
`"name": "kilo-code", "publisher": "kilocode", "version": "7.5.15"`.

## Identity: which product "Kilo Code" is

**Established**: the harness is **Kilo**, GitHub `Kilo-Org/kilocode` — a Bun/TypeScript monorepo
that ships one agent runtime under three front-ends: the **Kilo CLI** (`@kilocode/cli`, package
`packages/opencode/`), the **Kilo Code VS Code extension** (`kilo-code` by publisher `kilocode`,
package `packages/kilo-vscode/`), and a JetBrains plugin (`packages/kilo-jetbrains/`).

**The single most consequential identity fact: the current Kilo CLI is a fork of OpenCode, not a
continuation of the Roo Code / Cline lineage.** `README.md` line 171 states verbatim: "Kilo CLI is
a fork of [OpenCode](https://github.com/anomalyco/opencode), enhanced to work within the Kilo
agentic engineering platform." That is why the runtime package is literally named
`packages/opencode/`, why its internal service tags read `@opencode/ToolRegistry`,
`@opencode/Plugin`, `@opencode/Skill`, and why `AGENTS.md` documents a
`script/check-opencode-annotations.ts` CI guard requiring every Kilo-specific edit inside
`packages/opencode/` to carry a `kilocode_change` marker so upstream merges stay tractable.
**Everything below therefore resembles OpenCode far more than it resembles the older Roo-Code-derived
VS Code extension** — the sibling measurement `harness-opencode.md` is the closest relative, not
any Cline-family harness.

Evidence for the identity, and for what was ruled out:

- Repository. `https://raw.githubusercontent.com/Kilo-Org/kilocode/main/README.md` (read
  2026-09-06) describes Kilo Code as "an AI coding agent that meets you everywhere you work: VS
  Code, JetBrains, and the CLI", MIT-licensed, 500+ models. Root `package.json` is
  `@kilocode/kilo`, `packageManager: bun@1.3.14`, and its `dev` script is
  `KILO_CLIENT=cli bun run --cwd packages/opencode --conditions=node src/index.ts` — i.e. the CLI
  entry point is `packages/opencode/src/index.ts`.
- The *legacy* extension is a different codebase and is end-of-life.
  `https://raw.githubusercontent.com/Kilo-Org/kilocode-legacy/main/README.md` (read 2026-09-06)
  states verbatim: "The legacy Kilo Code VS Code extension and JetBrains plugin in this repository
  reached end of life on **July 31, 2026**", and that Kilo "will no longer provide updates, bug
  fixes, security patches, compatibility fixes, marketplace releases, or maintenance for this
  legacy codebase." That legacy README's only reference to the Roo lineage is a migration pointer
  — "🚀 **Coming from Roo Code?** Switch to Kilo and check out our [migration
  guide](https://kilo.ai/articles/roo-to-kilo-migration-guide)!" — not a statement of descent.
  Looked in the *current* repo's `README.md`, `AGENTS.md`, `CONTEXT.md` and
  `packages/kilo-docs/pages/**` for any claim that the shipping product is a fork or superset of
  Roo Code or Cline; did not find one. Search run 2026-09-06:
  `grep -rn -i "roo code\|roocode\|cline" README.md AGENTS.md CONTEXT.md packages/kilo-docs/pages`
  returned a single line, and it is a false positive — the substring inside "decline" in
  `packages/kilo-docs/pages/contributing/index.md` line 146.
- Web search "Kilo Code VS Code extension github Kilo-Org/kilocode" (2026-09-06) returned both
  `Kilo-Org/kilocode` and `Kilo-Org/kilocode-legacy`, plus the product site `kilo.ai`.
- Two tool layers exist in the tree and must not be confused. The shipping registry is
  `packages/opencode/src/tool/registry.ts`. A second, newer, Location-scoped tool layer sits in
  `packages/core/src/tool/` (`bash.ts`, `read.ts`, `write.ts`, `registry.ts`, with its own
  `AGENTS.md`), but it is not wired into the CLI: search run
  `grep -rn "tool/bash\|BashTool" --include=*.ts packages` on 2026-09-06 returns, outside
  `packages/core/src/tool/` itself, only `packages/core/test/tool-bash.test.ts` and TUI rendering
  code in `packages/opencode/src/cli/cmd/run/tool.ts` that aliases the *opencode* `ShellTool`. All
  answers below describe `packages/opencode/src/tool/`.

## 1. Shell command, read file, write file

**Answer**: yes to all three. The tool IDs are **`bash`** (execute a shell command), **`read`**
(read a file or directory listing) and **`write`** (create or overwrite a file), alongside `edit`,
`apply_patch`, `glob`, `grep`, `task`, `webfetch`, `websearch`, `todowrite`, `skill`, `plan`,
`question`, `suggest`, `invalid`, and a set of Kilo-only tools.

Sources (read 2026-09-06):

- `packages/opencode/src/tool/registry.ts` lines 257–315 assemble the builtin list
  (`tool.invalid`, `tool.question` when enabled, `tool.shell`, `tool.read`, `tool.glob`,
  `tool.grep`, `tool.edit`, `tool.write`, `tool.task`, `tool.fetch`, `tool.todo`, `tool.search`,
  `tool.skill`, `tool.patch`, `tool.plan`, `tool.suggest`, plus `KiloToolRegistry.extra(...)` and
  the experimental `code-mode` `execute` tool).
- The shell tool's exposed ID is `"bash"`, not `"shell"`.
  `packages/opencode/src/tool/shell/id.ts` states: "Keep the exposed tool ID and permission key as
  `bash` for compatibility with existing plugins, users, and saved permissions. Rename with
  opencode 2.0." followed by `export const ToolID = "bash"`.
  `packages/opencode/src/tool/shell.ts` line 525 registers `Tool.define(ShellID.ToolID, ...)`.
- `bash` parameters (`packages/opencode/src/tool/shell/prompt.ts`, `parameterSchema`):
  `command` (required, "The command to execute"), `timeout` (optional, milliseconds),
  `workdir` (optional, "The working directory to run the command in. Defaults to the current
  directory. Use this instead of 'cd' commands."), `description` (optional). Default timeout is
  2 minutes (`packages/opencode/src/tool/shell.ts`: `flags.bashDefaultTimeoutMs ?? 2 * 60 * 1000`).
  The description text emitted to the model changes per shell (bash / pwsh / powershell / cmd).
- `read` parameters (`packages/opencode/src/tool/read.ts` lines 39–47): `filePath` ("The absolute
  path to the file or directory to read"), `offset`, `limit` (default 2000 lines).
- `write` parameters (`packages/opencode/src/tool/write.ts` lines 24–29): `content`, `filePath`
  ("The absolute path to the file to write (must be absolute, not relative)").
- Doc confirmation: `packages/kilo-docs/pages/automate/extending/plugins.md`, section "What
  plugins can do", refers to "custom tools the model can call (like `read`, `write`, `bash`)";
  its "Name precedence" subsection says a plugin tool with the same name as a builtin wins, "for
  example, to wrap `bash` with extra validation".

Kilo-only additions gated by client and config (`packages/opencode/src/kilocode/tool/registry.ts`,
`KiloToolRegistry.extra`): `kilo_memory_recall` / memory save / `recall`, `semantic_search` (when
indexing is enabled), `background_process` (CLI and VS Code), `interactive_terminal` (CLI only,
primary agents only), `agent_manager` and `agent_manager_models`, `browser_open`, `chart`,
notebook read/edit/execute, `generate_image`, `notify_user`, `send_file`, and a shared
`board_read` / `board_post` pair behind `experimental.shared_agent_board`.

## 2. Hooks

**Answer**: Kilo has no shell-command hook mechanism. Its hooks are **JavaScript/TypeScript
callbacks exported by a plugin module**, loaded in-process at startup. A plugin ships them; a skill
collection cannot. Hook sources are the config `plugin` array (npm package or file path) and any
`plugin/` or `plugins/` directory inside a config directory — so both user-level and project-level
config can ship hooks, and so can a published npm package.

Sources (read 2026-09-06):

- Doc: `packages/kilo-docs/pages/automate/extending/plugins.md`, headings "Use a plugin",
  "Create a plugin", "Hooks reference", "Events", "Custom tools". Opening line: "Plugins extend
  Kilo by hooking into events, adding custom tools, registering auth or model providers, and
  customizing runtime behavior. They are TypeScript or JavaScript modules loaded at startup, and
  work in both the Kilo CLI and the VS Code extension."
- Types: `packages/plugin/src/index.ts` (`export interface Hooks`, lines 222–335;
  `PluginInput` lines 54–66; `Plugin` type line 71).
- Runtime: `packages/opencode/src/plugin/index.ts` (loading, `trigger`, `event` fan-out),
  `packages/opencode/src/config/plugin.ts` (directory scan),
  `packages/opencode/src/session/tools.ts` (per-tool trigger sites),
  `packages/opencode/src/session/prompt.ts` (task-tool trigger sites),
  `packages/opencode/src/project/bootstrap.ts` (load order).

### The complete lifecycle surface

Every field of `Hooks` in `packages/plugin/src/index.ts`, with its signature:

| Hook | Input | Output (mutable) |
| --- | --- | --- |
| `dispose` | — | — |
| `event` | `{ event: { id, type, properties } }` | — |
| `config` | the resolved `Config` object | — (mutated in place; see below) |
| `tool` | map of tool name → `ToolDefinition` | — |
| `auth` | `AuthHook` (provider, methods, prompts) | — |
| `provider` | `ProviderHook` (`id`, `models(provider, ctx)`) | — |
| `chat.message` | `{ sessionID, agent?, model?, messageID?, variant? }` | `{ message, parts }` |
| `chat.params` | `{ sessionID, agent, model, provider, message }` | `{ temperature, topP, topK, maxOutputTokens, options }` |
| `chat.headers` | `{ sessionID, agent, model, provider, message }` | `{ headers }` |
| `permission.ask` | `Permission` | `{ status: "ask" \| "deny" \| "allow" }` |
| `command.execute.before` | `{ command, sessionID, arguments }` | `{ parts }` |
| `tool.execute.before` | `{ tool, sessionID, callID }` | `{ args }` |
| `shell.env` | `{ cwd, sessionID?, callID? }` | `{ env }` |
| `tool.execute.after` | `{ tool, sessionID, callID, args }` | `{ title, output, metadata }` |
| `tool.definition` | `{ toolID }` | `{ description, parameters }` |
| `experimental.chat.messages.transform` | `{}` | `{ messages }` |
| `experimental.chat.system.transform` | `{ sessionID?, model }` | `{ system: string[] }` |
| `experimental.provider.small_model` | `{ provider }` | `{ model? }` |
| `experimental.session.compacting` | `{ sessionID }` | `{ context: string[], prompt? }` |
| `experimental.compaction.autocontinue` | `{ sessionID, agent, model, provider, message, overflow }` | `{ enabled }` |
| `experimental.text.complete` | `{ sessionID, messageID, partID }` | `{ text }` |

`packages/opencode/src/plugin/index.ts` `trigger` runs every plugin's implementation of a hook
sequentially in load order and awaits each; the doc's "Load order" section states the same
("Hooks from multiple plugins run sequentially in load order").

### The after-tool event, field by field

The after-tool event is the `tool.execute.after` hook. Its call site for ordinary tools is
`packages/opencode/src/session/tools.ts` lines 206–211:

```ts
yield* plugin.trigger(
  "tool.execute.after",
  { tool: item.id, sessionID: ctx.sessionID, callID: ctx.callID, args },
  output,
)
```

| Field | Value | Present? |
| --- | --- | --- |
| `input.tool` | the tool ID — `"bash"`, `"write"`, `"read"`, `"task"`, … | yes |
| `input.sessionID` | the session the tool ran in; for a sub-agent this is the **child** session's ID (see §3) | yes |
| `input.callID` | the provider tool-call ID | yes |
| `input.args` | the model's validated arguments object as-is: for `bash` this is `{ command, timeout?, workdir?, description? }`; for `write` it is `{ content, filePath }`; for `read` it is `{ filePath, offset?, limit? }` | yes |
| `output.title` | the tool's display title (mutable) | yes |
| `output.output` | the tool's text output (mutable) | yes |
| `output.metadata` | the tool's metadata (mutable); for `bash` this includes `exit`, `description`, `output` preview, and `outputPath` when output was spilled to a file | yes |
| `output.attachments` | file attachments, when the tool produced any | sometimes |
| working directory | **not a field.** `cwd` never appears in this payload. The nearest thing the model can supply is `args.workdir`, which is present only when the model passed it. The plugin *does* know the instance directory from elsewhere: `PluginInput.directory` and `PluginInput.worktree` are handed to the plugin factory at load (`packages/opencode/src/plugin/index.ts` builds `input` with `worktree: ctx.worktree, directory: ctx.directory`), and plugin state is per-instance, so `directory` is fixed for the life of that plugin instance. | no (derivable) |
| sub-agent identifier | **no dedicated field.** There is no `agentID`, `parentSessionID`, or `subagent` key. `sessionID` is the discriminator (see §3). | no |

`tool.execute.before` carries the same shape minus `args` in the input (`{ tool, sessionID,
callID }`) with `{ args }` as the mutable output, so a before-hook can rewrite the command string.
The doc's "Dependencies" example does exactly that:
`if (input.tool === "bash") { output.args.command = escape(output.args.command) }`.

Ordering caveat, read from source: in `packages/opencode/src/session/tools.ts` the `after` trigger
runs only after `item.execute(...)` succeeds. A tool that fails with an Effect error short-circuits
before the trigger, so `tool.execute.after` does **not** fire for a tool call that threw. A `bash`
command that merely exits non-zero, times out, or is aborted still returns normally
(`packages/opencode/src/tool/shell.ts` `run` builds an output with metadata in all three cases), so
those *do* reach the hook.

The `task` tool is special-cased: `packages/opencode/src/session/prompt.ts` lines 426–430 and
545–549 fire `tool.execute.before` / `tool.execute.after` for `TaskTool.id` with
`{ tool: "task", sessionID, callID: part.id, args: { prompt, description, subagent_type, command } }`
using the **parent** session's ID.

### The stop / completion event, field by field

There is no `Stop` hook. Completion is observed through the `event` hook, which fires for every
event on the internal bus. `packages/opencode/src/plugin/index.ts` lines 263–269:

```ts
const unsubscribe = yield* events.listen((event) => {
  if (event.location?.directory !== ctx.directory) return Effect.void
  return Effect.sync(() => {
    for (const hook of hooks) {
      void hook["event"]?.({ event: { id: event.id, type: event.type, properties: event.data } as any })
    }
  })
})
```

Two consequences worth stating plainly: events are **filtered to the plugin instance's own
directory**, and `event.location` is **dropped from the payload handed to the plugin** — so the
working directory is used as a filter but never delivered.

The completion event is `session.idle`. Its full schema
(`packages/schema/src/session-status-event.ts`, `export const Idle = Event.define({ type:
"session.idle", schema: { sessionID: SessionID } })`, marked `// deprecated` in that file) is:

| Field | Value |
| --- | --- |
| `event.id` | bus event ID |
| `event.type` | `"session.idle"` |
| `event.properties.sessionID` | the session that went idle (the child session ID when a sub-agent finishes) |

No working directory, no tool name, no tool input, no agent identifier. Its non-deprecated
replacement `session.status` (same file) carries `{ sessionID, status }` where `status` is one of
`{type:"idle"}`, `{type:"busy"}`, `{type:"retry", attempt, message, action?, next}`, or
`{type:"offline", requestID, message}` — still no directory, tool, or agent field. The docs'
"Events" section gives the canonical usage:
`if (event.type === "session.idle") { /* session finished responding */ }`.

An experimental v2 event family also exists (`packages/schema/src/session-event.ts`, namespace
`Tool`), gated by `KILO_EXPERIMENTAL_EVENT_SYSTEM`
(`packages/opencode/src/effect/runtime-flags.ts`: `experimentalEventSystem`). Its
`session.next.tool.called` carries `{ timestamp, sessionID, assistantMessageID, callID, tool,
input, provider }` — i.e. the tool name and the full input object — while
`session.next.tool.success` carries `{ timestamp, sessionID, assistantMessageID, callID,
structured, content, outputPaths?, result?, provider }` and notably **does not repeat the tool name
or input**. I read these schemas but did not trace whether the flag is on by default or which code
paths publish them, so treat their availability as unconfirmed; the `tool.execute.after` hook is
the load-bearing mechanism.

Doc caution: the plugins doc's "Events" list includes `tool.execute.before`, `tool.execute.after`,
and `shell.env` among "Common event types". Those three are **hook names, not bus events** — a
plugin cannot observe them through `event`. Search run 2026-09-06: extracting every
`type: "<literal>"` from `packages/schema/src/*.ts` yields no `tool.execute.*` and no `shell.env`
entry; the tool-related bus events are the `session.next.tool.*` family above. The other listed
types do exist (`session.created`, `session.updated`, `session.idle`, `session.error`,
`session.deleted`, `session.compacted`, `session.diff`, `session.status`, `message.updated`,
`message.removed`, `message.part.updated`, `message.part.removed`, `permission.asked`,
`permission.replied`, `file.edited`, `file.watcher.updated`, `command.executed`, `lsp.updated`,
`todo.updated`, `server.connected`, `installation.updated`).

### Are hooks shell commands?

No — and this is a change from upstream OpenCode. Kilo's config schema has no hook section at all.
Searches run on 2026-09-06:

- `grep -rn -i "hook" packages/core/src/config/ packages/opencode/src/config/*.ts` returns nothing.
- The `experimental` block of the live config schema (`packages/core/src/v1/config/config.ts`
  lines 295–350) contains `disable_paste_summary`, `batch_tool`, `image_generation`,
  `image_generation_model`, `native_notebook_tools`, `task_model_selection`,
  `speech_to_text_model`, `openTelemetry`, `shared_agent_board`, `primary_tools`,
  `continue_loop_on_deny`, `sandbox`, `sandbox_restrict_network`, `sandbox_writable_paths`,
  `mcp_timeout`, `policies` — no `hook` key.
- `grep -rn "file_edited\|session_completed" .` across the whole working tree matches exactly one
  file: `packages/sdk/js/src/gen/types.gen.ts` lines 1364–1379, which still declares
  `experimental.hook.file_edited` / `experimental.hook.session_completed` with `{ command:
  string[], environment? }`. That file is *generated*, and the generator input
  `packages/sdk/openapi.json` contains no `file_edited` (checked by parsing the JSON and testing
  for the substring). So the shell-command hook config survives only as a stale artifact in a
  generated type file, not in the schema the CLI validates against.
- `grep -rn '"{hook,hooks}\|hooks/' --include=*.ts packages/opencode/src` returns nothing — there
  is no `hooks/` directory scan analogous to the `plugin/` and `tool/` scans.
- `packages/kilo-docs/pages/automate/extending/plugins.md` documents no shell-command hook; its
  only shell-adjacent hook is `shell.env`, a JS callback that injects environment variables.

### Can a plugin or a skill collection ship them?

A plugin ships them — that is what a plugin *is*. Three loading paths, from
`packages/kilo-docs/pages/automate/extending/plugins.md` "Use a plugin" and the code:

1. **Config `plugin` array** — entries are `"package-name"`, `"package-name@1.2.3"`,
   `["package-name", { options }]`, `"./path/plugin.ts"`, or `"file:///abs/path/plugin.ts"`.
   Schema: `packages/core/src/config/plugin.ts` (`Schema.Union([Schema.String, Entry])`).
   npm entries are installed with Bun at startup with lifecycle scripts blocked.
2. **Plugin directory** — `packages/opencode/src/config/plugin.ts` line 21 scans
   `{plugin,plugins}/*.{ts,js}` in every config directory. Doc: "Global:
   `~/.config/kilo/plugin/`; Project: `.kilo/plugin/` or legacy `.kilocode/plugin/`". Every `.ts`
   or `.js` file there is auto-registered — no config entry needed.
3. **`kilo plugin <pkg>`** — installs an npm plugin and patches the config file for you
   (`--global` for the user-level config).

Config directories are resolved by `packages/opencode/src/config/paths.ts` `directories()`:
`~/.config/kilo` (XDG config dir + app name `kilo`, from `packages/core/src/global.ts`), then
`.kilocode` / `.kilo` walking up from the session directory to the worktree root, then
`.kilocode` / `.kilo` under `$HOME`, then `$KILO_CONFIG_DIR` if set. So a *project* can ship hooks
by committing `.kilo/plugin/foo.ts` — no user-level config edit required.

A module must default-export `{ id, server }` where `server` is the `Plugin` function; bare named
function exports still work as legacy. npm plugins declare `exports["./server"]` (or `main`) in
`package.json`, may pin compatibility with `engines.opencode`, and may carry default option values
in the export's `config` object. There is **no `plugin.json` / `.claude-plugin/plugin.json`-style
manifest**: search run `grep -rn 'plugin\.json' --include=*.ts packages/opencode/src
packages/core/src packages/plugin/src` on 2026-09-06 returned nothing, and the doc's "Package
manifest for npm plugins" section describes `package.json` as the manifest.

A **skill collection cannot ship hooks**. A skill is parsed into
`packages/opencode/src/skill/index.ts`'s `Info` struct — `{ name, description?, location, content,
trusted? }` — and nothing else; skill directories are scanned for `SKILL.md` only
(`EXTERNAL_SKILL_PATTERN`, `KILO_SKILL_PATTERN`, `SKILL_PATTERN` at lines 30–32), never for
`*.ts` plugin files. Looked in `packages/opencode/src/skill/index.ts`,
`packages/opencode/src/skill/discovery.ts`, and
`packages/kilo-docs/pages/customize/skills.md` for any hook, plugin, or event field attached to a
skill; did not find one. A repository that publishes skills *and* a plugin entry point is simply
both — the hooks come from the plugin half.

`KILO_PURE=1` skips all external plugins (built-ins only); `KILO_DISABLE_DEFAULT_PLUGINS` skips the
built-ins.

## 3. Sub-agents

**Answer**: yes — the **`task`** tool. It creates a real **child session** with its own session ID
and a `parentID` back to the caller. Hooks do fire inside it. The sub-agent's hook payloads carry
an identifier distinct from the parent's — the child `sessionID` — though there is no field named
"agent id" and no `parentSessionID` on the hook payload. The `task` tool cannot be given its own
working directory or git worktree; a separate, VS-Code-only `agent_manager` tool can.

Sources (read 2026-09-06):

- `packages/opencode/src/tool/task.ts` (whole file), `packages/opencode/src/agent/agent.ts`,
  `packages/opencode/src/session/prompt.ts`, `packages/opencode/src/session/tools.ts`,
  `packages/opencode/src/worktree/index.ts`,
  `packages/opencode/src/kilocode/tool/agent-manager.ts` and its prompt
  `packages/opencode/src/kilocode/tool/agent-manager.txt`,
  `packages/opencode/src/kilocode/tool/registry.ts`.
- Docs: `packages/kilo-docs/pages/customize/custom-subagents.md`,
  `packages/kilo-docs/pages/automate/agent-manager.md`.

**Mechanism.** `task` parameters (`packages/opencode/src/tool/task.ts`, `BaseParameterFields` and
`Parameters`): `description` (required, 3–5 words), `prompt` (required), `subagent_type`
(required), `task_id` (optional — resume a prior child session), `command` (optional), plus
`background` when `KILO_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true`, plus `model` / `provider` /
`variant` when `experimental.task_model_selection` is enabled. Depth is capped by
`subagent_depth` (`packages/core/src/v1/config/config.ts` line 189), default `1`, enforced at
`task.ts` line 135 by walking `parentID` upward. Built-in sub-agents are `general` and `explore`
(`packages/opencode/src/agent/agent.ts` lines 214–248, both `mode: "subagent"`); custom agents are
JSON entries under the config `agent` key or Markdown files with YAML frontmatter in
`~/.config/kilo/agents/` and `.kilo/agents/` (doc "Configuring Custom Subagents"; scan glob
`{agent,agents}/**/*.md` in `packages/opencode/src/config/agent.ts` line 31), with modes
`primary` / `subagent` / `all`.

**The child session.** `task.ts` calls
`sessions.create({ parentID: ctx.sessionID, title: params.description + " (@<name> subagent)",
agent: next.name, platform, permission: childPermission })` and then prompts *that* session
(`ops.prompt({ sessionID: nextSession.id, ... })`). The child runs the ordinary prompt/tool
machinery, so `packages/opencode/src/session/tools.ts` builds its tools and fires the same
`tool.execute.before` / `tool.execute.after` triggers with `ctx.sessionID` = the child's ID.
Sub-agents are denied `question` and `interactive_terminal` outright, and `todowrite` / `task` when
the agent's permissions or the depth cap forbid them.

**Do hooks fire inside it?** Yes. The plugin service is instance-scoped by directory
(`InstanceState.make` in `packages/opencode/src/plugin/index.ts`), and a child session inherits the
parent's directory, so the same loaded plugin objects receive the child's tool triggers. The
`event` hook's directory filter (`event.location?.directory !== ctx.directory`) also passes for
child-session events for the same reason. This is a source read, not a reproduction.

**Distinct identifier.** The child's `tool.execute.after` payload differs from the parent's only in
`sessionID` (and `callID`). That is a genuine discriminator — unlike a design where the sub-agent
shares the parent's session ID — but a hook cannot tell *from the payload alone* that a session is
a sub-agent, nor which session is its parent: `parentID` lives on the session record, not on the
hook payload. A plugin can recover it, because `PluginInput.client` is a full `@kilocode/sdk`
client against the local server, so `client.session.get({ id: sessionID })` would return the record
carrying `parentID` — I read that `PluginInput` supplies the client
(`packages/opencode/src/plugin/index.ts` builds it with `createKiloClient({ baseUrl, directory,
headers })`) but did not verify the specific SDK call name or that it returns `parentID`.
The parent-side wrapper call is distinguishable directly: `session/prompt.ts` fires
`tool.execute.after` with `tool: "task"` and `args.subagent_type`.

**Own working directory or worktree?** Not for `task`. Its parameter schema has no `cwd`,
`directory`, or `worktree` field, and `sessions.create(...)` in `task.ts` is passed no directory —
the child inherits the parent instance's. Searches run 2026-09-06:
`grep -n "cwd\|worktree\|directory" packages/opencode/src/tool/task.ts` returns zero matches,
and `grep -rn "Worktree" --include=*.ts packages/opencode/src --exclude-dir=worktree` shows the
`Worktree` service reached only from the experimental HTTP API handlers
(`packages/opencode/src/server/routes/instance/httpapi/handlers/experimental.ts` and
`.../groups/experimental.ts`) — i.e. from a client/UI, never from a model-callable tool.

The exception is Kilo's **`agent_manager`** tool, which *does* create git worktrees. Its
`StartParams` (`packages/opencode/src/kilocode/tool/agent-manager.ts`) take
`mode: "worktree" | "local"`, up to 20 `tasks`, each with `prompt`, `name`, `branchName`, `model`,
`provider`, `variant`; its prompt text says "`worktree`: creates a new Agent Manager git worktree
for each task, like the New Worktree dialog" and "`local`: creates Agent Manager sessions in the
current workspace directory without git worktree isolation". It is **exposed only when
`KILO_CLIENT === "vscode"`** (`packages/opencode/src/kilocode/tool/registry.ts`,
`KiloToolRegistry.extra`: `...(Flag.KILO_CLIENT === "vscode" ? [tools.manager] : [])`), and outside
that runtime the underlying service fails with "Agent Manager orchestration is unavailable in this
runtime". Its own prompt draws the line explicitly: "Do not use this for ordinary subagent
research. Use the `task` tool for internal subagents, and use this only when the user wants visible
Agent Manager sessions in the extension." A worktree gets its own instance directory, hence its own
plugin instances and its own `PluginInput.directory`.

## 4. Plugins and skills

**Answer**: yes, Kilo loads Agent-Skills-format `SKILL.md`. Directories: `.kilo/skills/` and
`.kilocode/skills/` (project, walking up), `~/.kilo/skills/`, `~/.config/kilo/skills/`,
`.claude/skills/` and `.agents/skills/` (both project-level and under `$HOME`), plus configured
`skills.paths` and remote `skills.urls`. The plugin "manifest" is a `package.json` for npm plugins
and a default-exported `{ id, server }` descriptor for file plugins — there is no dedicated plugin
manifest file. Skill bodies get `{env:VAR}` and `{file:path}` substitution plus `` !`command` ``
shell injection; **`${CLAUDE_PLUGIN_ROOT}` is not substituted and does not exist anywhere in the
repository.**

Sources (read 2026-09-06):

- Doc: `packages/kilo-docs/pages/customize/skills.md`, headings "Skill Locations", "Compatibility
  Directories", "Additional Skill Paths and Remote URLs", "SKILL.md Format", "Frontmatter Fields",
  "Shell commands in skills", "Priority and Overrides".
- Doc: `packages/kilo-docs/pages/automate/extending/plugins.md`, headings "Module shape", "Package
  manifest for npm plugins", "Engine compatibility".
- Source: `packages/opencode/src/skill/index.ts` (`discoverSkills`, `scan`, `add`, `loadSkills`),
  `packages/opencode/src/skill/discovery.ts` (remote pull), `packages/opencode/src/tool/skill.ts`
  (the `skill` tool), `packages/opencode/src/config/markdown.ts` and
  `packages/opencode/src/config/variable.ts` (substitution),
  `packages/opencode/src/kilocode/config/markdown.ts`,
  `packages/core/src/v1/config/skills.ts` (the `skills` config schema),
  `packages/opencode/src/config/paths.ts` (config directories).

**Format.** The doc states: "Kilo Code implements [Agent Skills](https://agentskills.io/home)…
a skill is a folder containing a `SKILL.md` file with metadata and instructions". Frontmatter
recognised by the parser is `name` (required) and `description` (optional at the type level:
`isSkillFrontmatter` in `packages/opencode/src/skill/index.ts` requires `name: string` and permits
`description` to be absent); the doc's "Frontmatter Fields" table lists `name` and `description` as
required and `license`, `compatibility`, `metadata` as optional per the spec — those three are read
by the YAML parser but not consumed by the loader.

**Directories, in the order `discoverSkills` scans them:**

| Source | Pattern | Trust |
| --- | --- | --- |
| `$HOME/.claude/`, `$HOME/.agents/` | `skills/**/SKILL.md` | trusted |
| `.claude/`, `.agents/` walking up from the session dir to the project root, plus the primary checkout's copies | `skills/**/SKILL.md` | untrusted (project-confined) |
| every config directory — `~/.config/kilo`, `.kilo` / `.kilocode` up-tree, `~/.kilo` / `~/.kilocode`, `$KILO_CONFIG_DIR` | `{skill,skills}/**/SKILL.md` | trusted for global and `$KILO_CONFIG_DIR`; untrusted for project and primary-checkout dirs |
| config `skills.paths` entries (absolute, `~/`-relative, or project-relative) | `**/SKILL.md` | trusted only when declared by a trusted config *and* absolute |
| config `skills.urls` (remote `index.json` manifest) | `**/SKILL.md` | always untrusted |
| built-ins compiled into the binary (`packages/opencode/src/kilocode/skills/builtin`) | — | trusted |

`.claude/` scanning is skipped when `KILO_DISABLE_CLAUDE_CODE` or `KILO_DISABLE_CLAUDE_CODE_SKILLS`
is set; all external (`.claude`/`.agents`) scanning is skipped under `KILO_DISABLE_EXTERNAL_SKILLS`
(`packages/opencode/src/effect/runtime-flags.ts`). Built-ins are seeded first so user skills of the
same name override them; later duplicates log a warning and win by scan order.

The doc's "Name Matching Rule" section claims the frontmatter `name` "**must match** the parent
directory name", but its own "Troubleshooting → Skill Not Loading?" step 1 says the opposite ("The
`name` does not need to match the directory name but should be unique"). The code sides with
troubleshooting: `add()` in `packages/opencode/src/skill/index.ts` keys the registry on
`md.data.name` and performs no directory comparison. A `NameMismatchError` class is declared in
that file but I found no site that constructs it — search run `grep -rn "NameMismatchError"
--include=*.ts packages/opencode/src` on 2026-09-06 returned only the declaration.

**Plugin manifest.** For npm plugins the manifest is `package.json`:
`exports["./server"]` marks a server plugin, `exports["./tui"]` a TUI plugin, `main` is a
server-only fallback, `oc-themes` marks a theme package, `engines.opencode` pins a compatible CLI
range, and an export's optional `config` object supplies default options written into the user's
config on first install. For file plugins the "manifest" is the module's default export,
`{ id, server }` — `id` is required for local-file plugins and inferred from `package.json#name`
for npm plugins. Verified absence of a separate manifest file above (§2).

**Path-variable substitution in skill bodies.** Two mechanisms, both in
`packages/opencode/src/config/markdown.ts` → `KilocodeMarkdown.substitute` →
`ConfigVariable.substitute`:

- `{env:VAR}` — replaced with the environment variable's value. **Rejected outright in untrusted
  (project) markdown**: `packages/opencode/src/config/variable.ts` throws
  `environment references are not allowed in project config: "<token>"`. A per-name allowlist
  (`ConfigVariableGuard.env`) additionally blocks server credentials in trusted contexts.
- `{file:path}` — replaced with the file's contents, resolved relative to the skill file's own
  directory (`~/` expanded, absolute paths honoured). In untrusted markdown the read is confined to
  the project root, and an out-of-scope read raises rather than silently emptying.
- Tokens on a line beginning with `//` are left literal; missing files substitute empty (`missing:
  "empty"`) rather than erroring for markdown.

Separately, `` !`command` `` in a skill body is executed and replaced with the command's stdout when
the skill is loaded — `packages/opencode/src/tool/skill.ts` calls `SkillInject.render({ content,
trusted, disabled: flags.disableSkillShell, cwd, skill, shell, ctx, decompose })`. The doc's "Shell
commands in skills" section states the gates: trusted skills only (global `~/.kilo/skills/`,
`~/.agents/skills/`, `~/.claude/skills/`, built-ins, and absolute paths declared in global config —
project skills and remote skills never execute), a single batched permission prompt listing every
command in the file, and the `KILO_DISABLE_SKILL_SHELL` kill switch. Placeholders inside fenced code
blocks are treated as documentation and never run.

**`${CLAUDE_PLUGIN_ROOT}` is not substituted.** Search run 2026-09-06: `grep -rn
"CLAUDE_PLUGIN_ROOT" .` over the entire shallow-clone working tree (all packages, docs, scripts)
returned zero matches, and the only substitution chain applied to skill bodies is the
`{env:}` / `{file:}` pair above. The literal string would therefore pass through to the model
unchanged. Kilo has no equivalent plugin-root placeholder either; what the skill tool gives the
model instead is prose, appended to the loaded skill content by
`packages/opencode/src/tool/skill.ts`: `Base directory for this skill: <dirname of SKILL.md>` plus
"Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory.",
followed by a sampled `<skill_files>` list of up to 10 absolute paths from the skill directory.
Built-in skills have no directory and get neither.

**Do plugins bundle skills?** Not through a manifest field — there is no `skills` key on a plugin
package. A plugin could add skill directories by mutating `config.skills.paths` from its `config`
hook (see §5 for why config mutation works), but I did not find any code or doc describing that
pattern; looked in `packages/kilo-docs/pages/automate/extending/plugins.md` and
`packages/opencode/src/skill/index.ts`, did not find it.

## 5. MCP

**Answer**: yes for project config, and yes for a plugin — by mutating the config object in the
`config` hook, which the bootstrap explicitly orders to allow.

- Schema: `packages/core/src/v1/config/config.ts` line 229 (`mcp:`) with entry types in
  `packages/core/src/v1/config/mcp.ts`. Local servers: `{ type: "local", command: string[], cwd?,
  environment? (alias`env`), enabled?, timeout? }`. Remote servers: `{ type: "remote", url,
  headers?, enabled?, timeout?, oauth? }`.
- Doc: `packages/kilo-docs/pages/automate/mcp/using-in-cli.md`, headings "Configuration Location",
  "Configuration Format", "Transport Types", "Managing MCP Servers". Its table gives Global
  `~/.config/kilo/kilo.json` (also `kilo.jsonc`, `config.json`) and Project `./kilo.json` or
  `./.kilo/kilo.json` (also `kilo.jsonc`), and states "Project-level configuration takes precedence
  over global settings." CLI commands: `kilo mcp list`, `kilo mcp add`, `kilo mcp auth`; TUI slash
  command `/mcps`.
- Config file discovery in code: `packages/opencode/src/config/config.ts` line 203 lists the
  candidate names `["kilo.jsonc", "kilo.json", "opencode.jsonc", "opencode.json", "config.json"]`;
  lines 399–405 load `config.json`, `kilo.json(c)`, `opencode.json(c)` from `~/.config/kilo`;
  lines 686–688 walk `kilo.*` and `opencode.*` up from the session directory; and every config
  directory contributes `packages/opencode/src/kilocode/config/config.ts` line 41's
  `ALL_CONFIG_FILES = ["kilo.jsonc", "kilo.json", "opencode.jsonc", "opencode.json"]`.
- A **legacy `mcp.json` path also exists** and is live. Search run 2026-09-06,
  `grep -rn '"mcp\.json"' --include=*.ts packages/opencode/src packages/core/src`, returns
  `packages/opencode/src/kilocode/mcp-migrator.ts` line 115, which reads
  `<projectDir>/.kilocode/mcp.json` then `<projectDir>/.kilo/mcp.json` in the old Kilo Code shape
  `{ "mcpServers": { … } }` (`.kilo` wins on name collision), and — only when
  `KILO_PLATFORM=vscode` or `KILOCODE_FEATURE=daemon` — the VS Code extension's global
  `settings/mcp_settings.json`. `McpMigrator.loadMcpConfig` is called from
  `packages/opencode/src/kilocode/config/config.ts` line 390 inside `loadLegacyConfigs`, which
  `packages/opencode/src/config/config.ts` line 490 runs as the *first* contribution to the
  resolved config — so these entries sit at the bottom of the precedence stack and any `mcp` block
  in `kilo.json` overrides them. `alwaysAllow` entries cannot be migrated and produce a warning.
  The current documented location remains the `mcp` key of the ordinary config file.
- Plugin registration: `packages/opencode/src/project/bootstrap.ts` lines 40–43 read
  `// everything depends on config so eager load it for nice traces` / `yield* config.get()` /
  `// Plugin can mutate config so it has to be initialized before anything else.` /
  `yield* plugin.init()`. `packages/opencode/src/plugin/index.ts` then calls each plugin's
  `hook.config?.(cfg)` with the live resolved config object, and
  `packages/opencode/src/mcp/index.ts` line 533 reads `const config = cfg.mcp ?? {}` inside its own
  lazily-materialised instance state — i.e. after bootstrap. So a plugin that writes
  `config.mcp["my-server"] = {...}` in its `config` hook registers an MCP server.
  Caveat worth flagging: the doc's "Hooks reference → Lifecycle" table describes `config` as
  "Receives the fully-resolved config at startup. Read-only — useful for inspection." The doc and
  the in-tree bootstrap comment disagree; the code comment and the ordering it enforces are the
  stronger evidence, but I did not run a plugin to confirm the write lands.
- Project-config MCP entries are treated as untrusted: `packages/opencode/src/config/config.ts`
  annotates the project load path with "MCP entries with variable-bearing headers dropped
  pre-substitution", implemented in `packages/opencode/src/kilocode/config/mcp-headers.ts`.
- Enterprise controls exist as a separate surface
  (`packages/kilo-docs/pages/contributing/features/enterprise-mcp-controls.md`), not read in full.

## 6. Environment variables set for a shell command

**Answer**: Kilo sets **no** variable naming the working directory, the session, the agent, or
itself. The `bash` tool passes the parent process's entire environment through, minus six Kilo
secrets, plus whatever plugins add via the `shell.env` hook. The working directory is applied as the
spawn's `cwd` option, not as an exported variable.

- Source: `packages/opencode/src/tool/shell.ts` lines 536–542:

  ```ts
  const shellEnv = Effect.fn("ShellTool.shellEnv")(function* (ctx: Tool.Context, cwd: string) {
    const extra = yield* plugin.trigger("shell.env", { cwd, sessionID: ctx.sessionID, callID: ctx.callID }, { env: {} })
    return modelEnv(extra.env) // kilocode_change - model shells must not inherit backend credentials
  })
  ```

  and line 765 `env: yield* shellEnv(ctx, cwd)`.
- `modelEnv` is `packages/opencode/src/kilocode/process/env.ts` `model(extra)`: it spreads
  `{ ...process.env, ...extra }`, drops non-string values, then `delete`s exactly
  `KILO_SERVER_PASSWORD`, `KILO_SERVER_USERNAME`, `KILO_BROWSER_BROKER_URL`,
  `KILO_BROWSER_BROKER_TOKEN`, `KILO_CONFIG`, `KILO_CONFIG_CONTENT`, `KILO_CONFIG_DIR`. Nothing is
  added.
- The command is spawned by `cmd()` (`packages/opencode/src/tool/shell.ts` line 478) as
  `ChildProcess.make(command, [], { shell, cwd, env, stdin: "ignore", detached: process.platform
  !== "win32" })` — on Windows with PowerShell it goes through `Shell.args(shell, command, cwd)`
  instead. `cwd` is `params.workdir` resolved against the instance directory, or the instance
  directory itself; unlike some harnesses, Kilo does **not** prefix the command with `cd '<dir>' &&`
  and in fact instructs the model not to (`workdirSection` in
  `packages/opencode/src/tool/shell/prompt.ts`: "AVOID using `cd <directory> && <command>` patterns
  - use `workdir` instead"). `stdin: "ignore"` means interactive commands see EOF.
- Plugins can inject variables. The documented example
  (`packages/kilo-docs/pages/automate/extending/plugins.md`, "Inject environment variables into
  every shell command") is exactly this: `output.env.MY_API_KEY = "secret"; output.env.PROJECT_ROOT
  = input.cwd`. So a plugin can synthesise the cwd/session variables the harness itself omits — the
  `shell.env` input carries `cwd`, `sessionID`, and `callID`.
- When the opt-in sandbox is active (`experimental.sandbox`),
  `packages/opencode/src/kilocode/sandbox/policy.ts` lines 262–276 additionally *deny* the same
  seven `KILO_*` names and *set* `TMPDIR`, `TMP`, `TEMP` to `Global.Path.tmp`. Still nothing
  identifying the session or the agent.
- Looked in `packages/opencode/src/tool/shell.ts`, `packages/opencode/src/kilocode/process/env.ts`,
  `packages/opencode/src/kilocode/sandbox/policy.ts` and
  `packages/core/src/flag/flag.ts` for any `KILO_SESSION_ID`, `KILO_AGENT_ID`, `KILO_CWD`, or
  equivalent exported to a child shell; did not find one. Search run 2026-09-06:
  `grep -rn "KILO_SESSION\|KILO_AGENT\|SESSION_ID\b" --include=*.ts packages/opencode/src
  packages/core/src` returns only variables the CLI *reads* (`KILO_SESSION_RETRY_LIMIT`,
  `KILO_SESSION_INGEST_URL`, `KILO_SESSION_EXPORT_*`, `KILO_AGENT_NOTIFICATION_TIMEOUT_MS`) — none
  written for a child process.
- Note that because the whole parent environment is inherited, any `KILO_*` flag the *user* exported
  before launching (e.g. `KILO_CLIENT`) is visible to the command; that is inheritance, not
  something Kilo sets.

## Synthesis: could a plugin-shipped hook renew a lease by reading `--address` and `--attempt` out of a shell command it observes, with no identifier of its own?

**Yes.** Both required conditions hold, and the mechanism is stronger than the question assumes.

1. **The after-tool payload carries the shell command text.** `tool.execute.after` receives
   `{ tool, sessionID, callID, args }`, and for the shell tool `args` is the validated `bash` input
   — `{ command, timeout?, workdir?, description? }`. `input.tool === "bash"` selects it (the tool
   ID is the literal string `"bash"`, per `packages/opencode/src/tool/shell/id.ts`), and
   `input.args.command` is the raw command string, from which `--address` and `--attempt` can be
   parsed. `tool.execute.before` sees the same string one step earlier and can even rewrite it.
   Evidence: `packages/plugin/src/index.ts` lines 274–281 for the type;
   `packages/opencode/src/session/tools.ts` lines 206–211 for the call site;
   `packages/kilo-docs/pages/automate/extending/plugins.md` "Dependencies" for a worked example that
   reads and mutates `output.args.command` under `input.tool === "bash"`.
2. **A plugin can ship the hook, including from project config.** Drop a `.ts` file into
   `.kilo/plugin/` in the repository — `packages/opencode/src/config/plugin.ts` line 21 scans
   `{plugin,plugins}/*.{ts,js}` in every config directory and auto-registers it with no config-file
   entry — or publish it to npm and list it in the `plugin` array. Evidence:
   `packages/kilo-docs/pages/automate/extending/plugins.md` "From a plugin directory".

Three properties make this easier in Kilo than in a shell-hook harness:

- The hook is an **in-process JS/TS callback**, not a subprocess. It can hold lease state across
  calls in a module-level variable, `await` an HTTP renewal, and use `PluginInput.client` (a
  `@kilocode/sdk` client bound to the local server) — no serialisation boundary, no stdin JSON
  contract, no re-parsing.
- It already has a stable notion of "where": `PluginInput.directory` and `PluginInput.worktree` are
  supplied at construction and the plugin instance is scoped to that directory, so the missing `cwd`
  field in the payload does not matter for a per-checkout lease.
- It has a usable per-session discriminator without inventing one: `sessionID` is the child session
  ID inside a sub-agent, so leases can be keyed per sub-agent as well as per session.

The caveats a lease renewer must handle:

- **`tool.execute.after` does not fire when a tool call fails with a thrown error.** A `bash` command
  that exits non-zero, times out, or is user-aborted still reaches the hook, but a spawn failure or
  a permission rejection does not. Renewal keyed only on the after-hook would miss those; pairing
  with `tool.execute.before` (which fires unconditionally before execution) closes the gap.
- **The hook cannot distinguish parent from sub-agent from the payload alone.** It gets a distinct
  `sessionID` but no `parentID` and no agent name; recovering the relationship needs an SDK call
  (unverified, see §3).
- **The payload carries no working directory.** Use `PluginInput.directory` / `worktree`, or
  `args.workdir` when the model supplied it.
- **A skill collection cannot ship this.** The hook must be delivered as a plugin — an npm package
  or a file under `.kilo/plugin/`. A skills repository would need to add that plugin file
  (or a plugin package) to carry the hook.
