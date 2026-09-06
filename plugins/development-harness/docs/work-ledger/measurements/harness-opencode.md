# OpenCode harness facts

Sources: local shallow clone of `anomalyco/opencode` branch `dev` at commit `337fd144d2ba144743368f78d9579a99cce175bd` (committed 2026-09-06 04:32 UTC), cloned to `/home/user/anomalyco/opencode`. All paths below are relative to that clone. Docs are the `.mdx` files under `packages/web/src/content/docs/` (the source of opencode.ai/docs). Every item was read on 2026-09-06. The cached `packages/plugin/src/index.ts` in the scratchpad is byte-identical to the clone (`diff` returned nothing).

## 1. Shell command, read file, write file

Yes to all three. Built-in tool ids, from `packages/opencode/src/tool/registry.ts` lines 209-249 (`builtin` list) and each tool's `Tool.define(...)` id:

| Capability | Tool id | Parameters | Where |
|---|---|---|---|
| Arbitrary shell command | `bash` | `command` (string), `timeout` (ms, optional), `workdir` (optional; "Use this instead of 'cd' commands") | id: `packages/opencode/src/tool/shell/id.ts` line 16 (`export const ToolID = "bash"`, comment: kept as "bash" for compatibility; the file is `shell.ts`); params: `packages/opencode/src/tool/shell/prompt.ts` lines 15-23 |
| Read file | `read` | `filePath` (absolute path) | `packages/opencode/src/tool/read.ts` lines 29, 69 |
| Write file | `write` | `content`, `filePath` (absolute) | `packages/opencode/src/tool/write.ts` lines 20-28 |
| Edit file | `edit` | `filePath`, `oldString`, `newString`, `replaceAll?` | `packages/opencode/src/tool/edit.ts` lines 47-56, 59 |
| Patch (GPT models only) | `apply_patch` | replaces `edit`/`write` when the model id contains `gpt-` and not `oss`/`gpt-4` | `packages/opencode/src/tool/registry.ts` lines 297-300 |

Other built-ins in the same list: `invalid`, `question` (app/cli/desktop clients only), `glob`, `grep`, `task`, `webfetch`, `todowrite`, `websearch`, `skill`, and flag-gated `execute` (code mode), `lsp`, `plan_exit`. Docs: `packages/web/src/content/docs/tools.mdx` headings `### bash`, `### edit`, `### write`, `### read`. Permission keys gating them: `agents.mdx` table under `### Permissions` (`bash` → `bash`; `edit` → `write`, `edit`, `apply_patch`; `read` → `read`).

The shell tool spawns the configured shell (`Shell.acceptable(cfg.shell)`) with the command string; on POSIX it is `ChildProcess.make(command, [], { shell, cwd, env })` — `packages/opencode/src/tool/shell.ts` lines 293-310 and 597-641. It runs in `instanceCtx.directory` unless `workdir` is given (lines 611-614).

## 2. Hooks

### Which lifecycle hooks exist

A plugin is a JS/TS module exporting `async (input, options) => Hooks`; the `Hooks` interface is the complete list — `packages/plugin/src/index.ts` lines 222-335 (read 2026-09-06):

| Hook key | Input (first arg) | Output (second arg, mutable) |
|---|---|---|
| `event` | `{ event: Event }` — every bus event (see below) | — |
| `config` | `Config` | — |
| `tool` | map of custom tool definitions | — |
| `auth`, `provider` | provider auth/model hooks | — |
| `chat.message` | `{ sessionID, agent?, model?, messageID?, variant? }` | `{ message: UserMessage, parts: Part[] }` |
| `chat.params` | `{ sessionID, agent, model, provider, message }` | `{ temperature, topP, topK, maxOutputTokens, options }` |
| `chat.headers` | same as chat.params | `{ headers }` |
| `permission.ask` | `Permission` | `{ status: "ask" \| "deny" \| "allow" }` |
| `command.execute.before` | `{ command, sessionID, arguments }` | `{ parts }` |
| `tool.execute.before` | `{ tool: string; sessionID: string; callID: string }` | `{ args: any }` |
| `shell.env` | `{ cwd: string; sessionID?: string; callID?: string }` | `{ env: Record<string,string> }` |
| `tool.execute.after` | `{ tool: string; sessionID: string; callID: string; args: any }` | `{ title: string; output: string; metadata: any }` |
| `experimental.chat.messages.transform` | `{}` | `{ messages }` |
| `experimental.chat.system.transform` | `{ sessionID?, model }` | `{ system: string[] }` |
| `experimental.provider.small_model` | `{ provider }` | `{ model? }` |
| `experimental.session.compacting` | `{ sessionID }` | `{ context: string[]; prompt? }` |
| `experimental.compaction.autocontinue` | `{ sessionID, agent, model, provider, message, overflow }` | `{ enabled }` |
| `experimental.text.complete` | `{ sessionID, messageID, partID }` | `{ text }` |
| `tool.definition` | `{ toolID }` | `{ description, parameters }` |
| `dispose` | — | — |

Session idle: there is no dedicated hook key; it arrives through the `event` hook as `event.type === "session.idle"` (docs example: `plugins.mdx` heading `### Send notifications`, lines 222-233). `plugins.mdx` heading `### Events` (lines 142-208) lists the event types delivered to `event`: `command.executed`, `file.edited`, `file.watcher.updated`, `installation.updated`, `lsp.client.diagnostics`, `lsp.updated`, `message.part.removed`, `message.part.updated`, `message.removed`, `message.updated`, `permission.asked`, `permission.replied`, `server.connected`, `session.created`, `session.compacted`, `session.deleted`, `session.diff`, `session.error`, `session.idle`, `session.status`, `session.updated`, `todo.updated`, `shell.env`, `tool.execute.after`, `tool.execute.before`, `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`.

Sub-agent completion: looked in `packages/plugin/src/index.ts`, `packages/schema/src/session-status-event.ts`, `packages/core/src/background-job.ts` (grep `Event|publish`: no matches) and `packages/opencode/src/tool/task.ts` — did not find a dedicated "subagent finished" event or hook. What does fire when a sub-agent finishes: (a) the child session's own `session.status` (`{ sessionID, status: { type: "idle" } }`) and the deprecated-but-still-published `session.idle` (`{ sessionID }`) — `packages/opencode/src/session/status.ts` lines 39-48 publishes both whenever a session's status becomes idle, and `packages/opencode/src/session/processor.ts` lines 626 and 638 set idle for the session that just ran (the child, for a sub-agent); the schema is `packages/schema/src/session-status-event.ts` lines 35-49 (`Idle` is marked `// deprecated`, line 43); and (b) `tool.execute.after` for `tool: "task"` in the parent session, whose `output.output` is `<task id="<child sessionID>" state="completed|error">...` — `packages/opencode/src/tool/task.ts` lines 64-79 (`renderOutput`) and 341-345, and `packages/opencode/src/session/tools.ts` lines 121-125.

### Payload of `tool.execute.after`

Exact trigger sites (all pass the same shape):

- Built-in and plugin tools: `packages/opencode/src/session/tools.ts` lines 121-125 — `{ tool: item.id, sessionID: ctx.sessionID, callID: ctx.callID, args }` with output `{ ...result, attachments }` where `result` is the tool's `{ title, output, metadata }`.
- MCP tools: `packages/opencode/src/session/tools.ts` lines 208-212 — `{ tool: key, sessionID, callID: opts.toolCallId, args }`, output is the raw MCP result.
- `@mention` subtasks: `packages/opencode/src/session/prompt.ts` lines 390-394 — `{ tool: "task", sessionID, callID: part.id, args: taskArgs }`.

Field-by-field for the questions asked:

| Wanted | Present? | Where it is |
|---|---|---|
| Tool name | yes — `input.tool` (`"bash"`, `"write"`, `"read"`, `"task"`, MCP key) | index.ts line 275 |
| Tool input | yes — `input.args` is the tool's parameter object: for `bash` it is `{ command, timeout?, workdir? }` (so the command string is `input.args.command`), for `write` it is `{ filePath, content }`, for `read` `{ filePath }`, for `task` `{ description, prompt, subagent_type, task_id?, command?, background? }` | index.ts line 275; shell/prompt.ts lines 15-23; write.ts lines 20-25; task.ts lines 43-62 |
| Session id | yes — `input.sessionID`, the session the call ran in (the child's id when a sub-agent made the call) | tools.ts line 60 sets `sessionID: input.session.id` |
| Call id | yes — `input.callID` | index.ts line 275 |
| Working directory | not in the hook input. Looked in index.ts lines 266-281 and tools.ts lines 58-125: `tool.execute.before/after` carry no `cwd`/`directory`. The plugin receives `directory` and `worktree` once at load time (`PluginInput`, index.ts lines 56-66; docs `plugins.mdx` lines 116-122) and can also read `client.session.get(sessionID).directory` (session schema `packages/opencode/src/session/session.ts` line 229 `directory: Schema.String`). For a `bash` call the effective cwd is `args.workdir` if set, else the instance directory (shell.ts lines 611-614). `shell.env` does receive `{ cwd, sessionID, callID }` (index.ts lines 270-273; shell.ts lines 416-421) and fires immediately before each bash spawn. | |
| Sub-agent identifier | not in the hook input. Looked in index.ts lines 266-281: no `agent`/`parentID` field. The session record for `input.sessionID` has `agent` (agent name) and `parentID` (parent session id) — session.ts lines 231, 238; task.ts lines 156-172 creates the child with `parentID: ctx.sessionID, agent: next.name`. Tool output metadata for `task` also carries `{ parentSessionId, sessionId, model }` (task.ts lines 185-190). | |
| Output | `output.title`, `output.output`, `output.metadata`; for `bash`, `title` is the command string and `metadata` is `{ output, exit, truncated, outputPath? }` (shell.ts lines 585-594) | |

### JS function or shell command

JS/TS plugin function only. `plugins.mdx` line 69: "A plugin is a **JavaScript/TypeScript module** that exports one or more plugin functions." Loader: `packages/opencode/src/plugin/index.ts` lines 114-125 (`applyPlugin` calls the exported function and pushes the returned hooks) and lines 284-297 (`trigger` awaits each hook function). Looked in `packages/core/src/v1/config/*.ts` (grep `hook`, case-insensitive: no match) and `config.mdx`/`permissions.mdx` (only a prose mention of "hooks" in the Plugins section, line 800) — did not find any config key that runs a shell command as a hook. A hook can itself run shell commands via the `$` Bun shell passed in `PluginInput` (index.ts line 65; docs example line 228).

### Where plugins load from (shipping with a skill collection)

`plugins.mdx` heading `## Use a plugin`, lines 18-42, and source:

- Files under `{plugin,plugins}/*.{ts,js}` in every config directory — `packages/opencode/src/config/plugin.ts` lines 18-30 and `config.ts` lines 476-479. Config directories are (`packages/opencode/src/config/paths.ts` lines 23-41): `~/.config/opencode` (`Global.Path.config`), every `.opencode` directory found walking up from the working directory to the git worktree root, `~/.opencode`, and `$OPENCODE_CONFIG_DIR` if set.
- npm package names, or path specs (`./x.ts`, absolute, `file://`) in the `plugin` array of any `opencode.json`/`opencode.jsonc` — `config/plugin.ts` lines 40-60 resolves path specs relative to the config file that declared them; `plugin/shared.ts` lines 171-173 (`isPathPluginSpec`). Docs `plugins.mdx` lines 29-40 mention only npm names for the `plugin` array.
- Load order (docs lines 54-63): global config, project config, global plugin directory, project plugin directory.

Consequence for a skill collection: `skills.paths` / `skills.urls` (see §4) only scan for `**/SKILL.md` (`packages/opencode/src/skill/index.ts` lines 25, 219, 225) — a plugin file placed inside a skills directory is not loaded from there. A collection can ship a plugin only by being (or living under) an `.opencode/plugins/` directory, a `$OPENCODE_CONFIG_DIR/plugins/` directory, an npm package, or a path listed in a project/global `opencode.json` `plugin` array. There is no "install a plugin per skill collection" mechanism in the sources read.

## 3. Sub-agents

- Spawn from inside a session: the built-in `task` tool with `subagent_type`, `prompt`, `description`, optional `task_id` (resume), `command`, and `background` (only when `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true`) — `packages/opencode/src/tool/task.ts` lines 24, 43-62, 96-102. Users can also `@mention` a subagent; the mention becomes a `subtask` part handled by `handleSubtask` in `packages/opencode/src/session/prompt.ts` lines 1144-1147, which itself calls the task tool (lines 307-311, 323-337). Docs: `agents.mdx` heading `### Subagents` (line 37) and `## Usage` item 2 (lines 123-129); `## Types` lists built-in subagents `general`, `explore`, `scout`. Nesting depth is governed by `subagent_depth` (default 1) — task.ts lines 104-117; `config.mdx` heading `### Subagent depth` (lines 548-560).
- Hooks for the sub-agent's tool calls: yes. The child runs through the same prompt loop (`ops.prompt({ sessionID: nextSession.id, agent: next.name, ... })`, task.ts lines 200-212), which resolves tools via `SessionTools.resolve` with `session: <child>` (prompt.ts line 1226; tools.ts lines 41-60), and every tool execution triggers `tool.execute.before`/`after` (tools.ts lines 106-125). Nothing in the trigger path (`packages/opencode/src/plugin/index.ts` lines 284-297) filters by session. The `event` hook is filtered only by `event.location?.directory !== ctx.directory` (index.ts line 256); child sessions are created with `directory: ctx.directory` (session.ts lines 668-690), so their events pass the filter.
- Distinct session id: yes. `sessions.create({ parentID: ctx.sessionID, title: "<description> (@<agent> subagent)", agent: next.name, permission: [...] })` — task.ts lines 156-172. `Session.Info` has `parentID: optional(SessionID)` and `agent: optional(String)` — session.ts lines 231, 238. The hook input `sessionID` for a sub-agent's call is the child's id (tools.ts line 60). The parent's id is recoverable via `client.session.get(childID).parentID` or via the `task` tool metadata `parentSessionId` (task.ts lines 185-190).
- Different working directory / git worktree for a sub-agent: looked in task.ts (parameters lines 43-62) and `Session.create` (session.ts lines 668-690) — no parameter for a directory or worktree; the child inherits `ctx.directory` and the parent's `workspaceID`. A separate "workspace" concept exists behind `OPENCODE_EXPERIMENTAL_WORKSPACES` (`runtime-flags.ts` line 50; `cli.mdx` line 734 "Enable workspace support") with a `WorktreeAdapter` ("Create a git worktree") in `packages/opencode/src/control-plane/adapters/worktree.ts` lines 28-31 and a plugin `experimental_workspace.register(type, adapter)` API (index.ts lines 47-54, 61-63) — but that is a user/server-level workspace, not something the task tool can target. Community plugin `opencode-worktree` is listed in `ecosystem.mdx` line 52; not verified here.

## 4. Plugins and skills (SKILL.md)

- Loads `SKILL.md` skills: yes, via the built-in `skill` tool (`packages/opencode/src/tool/skill.ts` line 13; `skills.mdx` lines 6-7 and heading `## Recognize tool description`). Frontmatter recognized: `name` (required), `description` (required), `license`, `compatibility`, `metadata`; `name` must match the directory name — `skills.mdx` headings `## Write frontmatter` and `## Validate names` (lines 34-62). Note: the source parser (`skill/index.ts` lines 53-59, 123) accepts any frontmatter with a string `name` and optional string `description`; skills without a `description` are loaded but omitted from the listing (line 322).
- Directories, from `packages/opencode/src/skill/index.ts` lines 173-227 and `skills.mdx` lines 11-30:
  - `~/.claude/skills/**/SKILL.md` and `~/.agents/skills/**/SKILL.md` (globals; `.claude` skipped when `OPENCODE_DISABLE_CLAUDE_CODE` or `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS` is set, both skipped under `OPENCODE_DISABLE_EXTERNAL_SKILLS` — lines 185-193; flags in `runtime-flags.ts` lines 21, 27-30; `cli.mdx` lines 696-698).
  - Every `.claude/` and `.agents/` directory found walking up from the working directory to the git worktree root, pattern `skills/**/SKILL.md` (lines 196-202).
  - Every config directory (`~/.config/opencode`, each `.opencode` up to the worktree, `~/.opencode`, `$OPENCODE_CONFIG_DIR`) with pattern `{skill,skills}/**/SKILL.md` (lines 205-208; `config/paths.ts` lines 23-41).
  - Extra directories from config `skills.paths` (absolute, `~/`-relative, or relative to the working directory; pattern `**/SKILL.md`) and remote `skills.urls` (fetches `<url>/index.json` then each skill's files into `~/.cache/opencode/skills/<name>`) — lines 210-227; schema `packages/core/src/v1/config/skills.ts` lines 5-12; discovery in `skill/discovery.ts` lines 49-132. `skills.mdx` (cached and at HEAD) does not document `skills.paths`/`skills.urls`; the config schema does.
  - A built-in `customize-opencode` skill is registered before disk discovery (lines 32-35, 276-283).
- Path variable substitution in skill bodies: none found. The body is returned verbatim — `tool/skill.ts` line 51 `info.content.trim()` — and the parser is `gray-matter` with no template pass (`packages/core/src/config/markdown.ts` lines 4-10; `packages/opencode/src/config/markdown.ts` lines 20-34). The `{env:VAR}`/`{file:path}` substitution lives in `packages/opencode/src/config/variable.ts` (lines 33-61) and is applied to config text, not to skill markdown (grep `ConfigVariable|Variable\.` in `config/markdown.ts`, `skill/index.ts`, `tool/skill.ts`: no match). Looked for `CLAUDE_PLUGIN_ROOT`, `{baseDir}`, `baseDir`, `SKILL_DIR` across `packages/opencode/src` (grep): no match. What the tool does instead is append `Base directory for this skill: <dir>` plus a sampled `<skill_files>` list (up to 10 files) after the body — `tool/skill.ts` lines 34-60.

## 5. MCP from project config

Yes. `mcp` is a top-level config key in `opencode.json`/`opencode.jsonc`, and project config files are discovered by walking up from the working directory to the worktree root (`ConfigPaths.files("opencode", ...)`, `config.ts` lines 421-424; `paths.ts` lines 10-21), plus `.opencode/opencode.json[c]` in each config directory (`config.ts` lines 438-447). Docs: `config.mdx` heading `### Per project` (line 109) and `### MCP servers` (lines 783-794); `mcp-servers.mdx` heading `## Enable` and `## Local` (`type: "local"`, `command: [...]`, `environment`, `enabled`, `cwd`, `timeout`) and remote (`type: "remote"`, `url`, `headers`, `oauth`, `timeout`) — schema `packages/core/src/v1/config/mcp.ts` lines 6-24, 47-60. `cwd` for local servers: "Relative paths resolve from the workspace directory" (mcp.ts line 12). MCP tool calls also pass through `tool.execute.before/after` (tools.ts lines 199-212) and are permission-gated by their tool name (`agents.mdx` line 453).

## 6. Environment variables for a shell command

The `bash` tool spawns with `env = { ...process.env, ...extra.env }` where `extra.env` is whatever plugins add in the `shell.env` hook — `packages/opencode/src/tool/shell.ts` lines 416-426 and 636. Looked in `shell.ts` and `tool/shell/*.ts`: the tool itself adds no variable naming the session, agent, or working directory; the working directory is passed as the process `cwd` (lines 293-310), not as a variable. The `shell.env` hook input gives a plugin `{ cwd, sessionID, callID }` so it can export them itself (docs example `plugins.mdx` lines 261-273 sets `PROJECT_ROOT = input.cwd`).

Variables the OpenCode process sets on itself before any command runs, and which are therefore inherited: `AGENT=1`, `OPENCODE=1`, `OPENCODE_PID=<pid>` — `packages/opencode/src/index.ts` lines 75-77; `OPENCODE_PRINT_LOGS`, `OPENCODE_LOG_LEVEL`, `OPENCODE_PURE` only when the matching CLI flag is given (lines 67-71); `OPENCODE_CLIENT=acp` under `opencode acp` (`cli/cmd/acp.ts` line 23). Under experimental workspaces, a child server is started with `OPENCODE_WORKSPACE_ID` and `OPENCODE_EXPERIMENTAL_WORKSPACES=true` (`control-plane/workspace.ts` lines 531-532). The user `!command` shell path (not the LLM tool) additionally sets `TERM=dumb` (`session/prompt.ts` lines 555-563). The PTY terminal also runs the `shell.env` hook with `{ cwd }` only (`server/routes/instance/httpapi/handlers/pty.ts` line 71; `plugin/pty-environment.ts` line 18). Looked in `index.ts`, `shell.ts`, `prompt.ts`, `runtime-flags.ts` (grep `process.env.OPENCODE_[A-Z_]+ *=`): did not find any variable that carries the session id, agent name, or worktree into the shell. The documented list of variables OpenCode *reads* is `cli.mdx` heading `## Environment variables` (lines 676-734).
