# Harness facts: pi (pi coding agent)

Read date: 2026-09-06. Source: default branch `main` of `github.com/badlogic/pi-mono`, cloned at
commit `9767ba275f3e9a5ee0f5c5342249b629ab1b2282` (committed 2026-09-06T00:30:17+02:00). Every
file path below is relative to `packages/coding-agent/` in that checkout unless stated otherwise.
Pinned URL base: `https://github.com/badlogic/pi-mono/blob/9767ba275f3e9a5ee0f5c5342249b629ab1b2282/packages/coding-agent/`.

Identity note (read 2026-09-06): `git ls-remote https://github.com/badlogic/pi-mono HEAD` and
`git ls-remote https://github.com/earendil-works/pi HEAD` both return `9767ba27...` — the repo
now lives at `earendil-works/pi` and the old URL redirects. `package.json` `"name"` is
`@earendil-works/pi-coding-agent`, `"version": "0.85.1"`. The npm registry
(`https://registry.npmjs.org/@mariozechner/pi-coding-agent/latest`, read 2026-09-06) reports
`@mariozechner/pi-coding-agent` at 0.73.1 with `deprecated: "please use
@earendil-works/pi-coding-agent instead going forward"`; `@earendil-works/pi-coding-agent/latest`
is 0.85.1, repository `git+https://github.com/earendil-works/pi.git`. Docs still say
`~/.pi/agent` and `.pi/` for config directories.

## 1. Shell command, read file, write file

Yes to all three. Built-in tool names are `read`, `bash`, `powershell`, `edit`, `write`,
`grep`, `find`, `ls`.

- `bash` runs an arbitrary shell command (input `{ command: string; timeout?: number }`);
  `read` reads a file (`{ path; offset?; limit? }`); `write` writes a file; `edit` patches a file.
- Source: `src/core/tools/index.ts` line 95:
  `export type ToolName = "read" | "bash" | "powershell" | "edit" | "write" | "grep" | "find" | "ls";`
  and `src/core/tools/bash.ts` (`name: "bash"`, line 376), `read.ts` (`name: "read"`, line 71),
  `write.ts` (`name: "write"`, line 50), `edit.ts` (`name: "edit"`, line 149).
- Docs: `docs/extensions.md` heading "Overriding Built-in Tools" (line 2082): "Extensions can
  override built-in tools (`read`, `bash`, `powershell`, `edit`, `write`, `grep`, `find`,
  `ls`) by registering a tool with the same name." Heading "tool_call" (line 778) shows the
  typed inputs for `bash` and `read`.
- URL: `.../docs/extensions.md`, `.../src/core/tools/index.ts`. Read 2026-09-06.

## 2. Hooks (Extension API)

### Lifecycle events exposed

Docs: `docs/extensions.md` heading "Events" > "Lifecycle Overview" (line 273) and the
`ExtensionEvent` union in `src/core/extensions/types.ts` (line 1086). Read 2026-09-06.

Full list of event names at HEAD (from the `ExtensionEvent` union and the per-event
interfaces in `types.ts`, lines 521-1020):

- Startup: `project_trust`, `resources_discover`
- Session: `session_start`, `session_info_changed`, `session_before_switch`,
  `session_before_fork`, `session_before_compact`, `session_compact`, `session_compact_failed`,
  `session_before_tree`, `session_tree`, `session_shutdown`
- Agent: `before_agent_start`, `agent_start`, `agent_end`, `agent_settled`,
  `ui_prompt_start`, `ui_prompt_end`, `turn_start`, `turn_end`, `message_start`,
  `message_update`, `message_end`
- Tool execution: `tool_execution_start`, `tool_execution_update`, `tool_execution_end`
- Tool gate/patch: `tool_call` (before execution, can block/mutate input), `tool_result`
  (after execution, can modify result)
- Provider: `context`, `before_provider_headers`, `before_provider_request`,
  `after_provider_response`
- Model: `model_select`, `thinking_level_select`
- User shell: `user_bash` (for user-typed `!` commands, not LLM tool calls)
- Input: `input`

Mapping to the asked-for names: `tool_call` = pre-tool; `tool_result` and
`tool_execution_end` = after-tool; `turn_end` = end of one LLM turn; `agent_end` = end of the
agent run (docs note Pi may still auto-retry/compact after it; `agent_settled` fires when
nothing more will run automatically); `session_start` exists; `session_shutdown` is the
session-end event.

### Fields on the after-tool events (verbatim from `src/core/extensions/types.ts`)

`tool_result` (lines 957-1020):

```
interface ToolResultEventBase {
	type: "tool_result";
	toolCallId: string;
	input: Record<string, unknown>;
	content: (TextContent | ImageContent)[];
	isError: boolean;
	usage?: Usage;
}
```

plus `toolName` (`"bash" | "powershell" | "read" | "edit" | "write" | "grep" | "find" | "ls"` or
`string` for custom tools) and `details` (typed per tool: `BashToolDetails`, `ReadToolDetails`,
`EditToolDetails`, `undefined` for `write`, etc.).

`tool_execution_end` (lines 815-822): `type`, `toolCallId: string`, `toolName: string`,
`result: any`, `isError: boolean`.

`tool_call` (lines 888-953): `type: "tool_call"`, `toolCallId: string`, `toolName`, `input`
(typed per built-in tool; `BashToolInput` is `{ command: string; timeout?: number }`,
`ReadToolInput` is `{ path: string; offset?: number; limit?: number }` per docs line 800-812).
`event.input` is mutable.

Specifically asked-for fields:

- Tool name: `event.toolName` on `tool_call`, `tool_result`, `tool_execution_*`. Present.
- Tool input: `event.input` on `tool_call`/`tool_result` — for `bash` the command string is
  `event.input.command`; for `write` the path is `event.input.path` (docs, lines 800-812;
  `WriteToolInput` imported from `tools/write.ts`). Present.
- Working directory: not a field on any event object. Looked in every event interface in
  `types.ts` lines 521-1020, did not find a `cwd` field. It is on the context argument:
  `ctx.cwd` (`ExtensionContext`, `types.ts` line 317: `/** Current working directory */ cwd: string;`;
  docs heading "ctx.cwd", line 976).
- Session id: not a field on any event object (same search). Available through
  `ctx.sessionManager.getSessionId()` — `ReadonlySessionManager` is a `Pick<SessionManager, ... "getSessionId" | "getSessionFile" ...>`
  (`src/core/session-manager.ts` lines 190-194); ids are `uuidv7()` (line 208-210).
  `session_start` carries `reason: "startup" | "reload" | "new" | "resume" | "fork"` and
  `previousSessionFile?: string` (`types.ts` lines 564-571).
- Sub-agent identifier: looked in `types.ts` (all event interfaces and `ExtensionContext`,
  lines 309-352) and `docs/extensions.md` "ExtensionContext" (lines 960-1108); did not find any
  parent-session, child-session, agent-id, or sub-agent field. See question 3.

End events:

- `turn_end` (`types.ts` 771-776): `type`, `turnIndex: number`, `message: AgentMessage`,
  `toolResults: ToolResultMessage[]`.
- `agent_end` (735-738): `type`, `messages: AgentMessage[]`.
- `agent_settled` (741-743): `type` only.
- `session_shutdown` (633-638): `type`, `reason: "quit" | "reload" | "new" | "resume" | "fork"`,
  `targetSessionFile?: string`.
- Working directory / session id: not on these events either; via `ctx` as above.

### Shipping an extension inside a skill collection or package

Yes. `docs/packages.md` heading "Creating a Pi Package" (line 116, read 2026-09-06):

```json
{
  "name": "my-package",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions"],
    "skills": ["./skills"],
    "prompts": ["./prompts"],
    "themes": ["./themes"]
  }
}
```

"Paths are relative to the package root. Arrays support glob patterns and `!exclusions`."
Heading "Convention Directories" (line 158): with no `pi` manifest, `extensions/` loads
`.ts`/`.js` files and `skills/` recursively finds `SKILL.md` folders. Installed with
`pi install npm:<pkg>` / `git:<url>` or listed under `packages` in `settings.json`
(`docs/extensions.md` heading "Extension Locations", line 109). Standalone discovery
locations: `~/.pi/agent/extensions/*.ts`, `~/.pi/agent/extensions/*/index.ts`,
`.pi/extensions/*.ts`, `.pi/extensions/*/index.ts` (project ones only after trust), plus
`settings.json` `"extensions": [...]` paths and CLI `-e/--extension <source>`.

## 3. Sub-agents

- Nothing built in. `docs/usage.md` line 309: "It intentionally does not include built-in MCP,
  sub-agents, permission popups, plan mode, to-dos, or background bash. You can build or
  install those workflows as extensions or packages, or use external tools such as containers
  and tmux." `README.md` line 501: "**No sub-agents.** ... Spawn pi instances via tmux, or
  build your own with extensions, or install a package". Read 2026-09-06.
- Mechanism provided as an example (not bundled, must be symlinked/installed):
  `examples/extensions/subagent/` — an extension registering a tool that spawns a separate
  `pi` process per task. `examples/extensions/subagent/index.ts` line 300:
  `const args: string[] = ["--mode", "json", "-p", "--no-session"];` then `--model`,
  `--thinking`, `--tools`, `--append-system-prompt <tmpfile>`, and `Task: <task>`; line 346
  `spawn(invocation.command, invocation.args, { cwd: cwd ?? defaultCwd, shell: false, stdio: [...] })`.
  `README.md` for the example: "Each subagent runs in a separate `pi` process". Agent
  definitions are `~/.pi/agent/agents/*.md` and `.pi/agents/*.md` (frontmatter `name`,
  `description`, `tools`, `model`). Alternative in-process route: the SDK
  (`docs/sdk.md`, `createAgentSession({ cwd, ... })`), and `pi.exec()` from an extension
  (`docs/extensions.md` line 1668).
- Do extension events fire inside the sub-agent: the child is a full `pi` invocation with
  `--mode json -p`. `docs/extensions.md` heading "Mode Behavior" (line 2928) table: JSON mode
  "Event stream to stdout; UI methods are no-ops"; Print (`-p`) "Extensions run but can't
  prompt". The example does not pass `--no-extensions` (looked in
  `examples/extensions/subagent/index.ts`, found only the `ExtensionAPI` import and the args
  list above). So extensions discovered from the child's cwd and `~/.pi/agent/extensions`
  load in the child and their handlers fire there; the parent's in-process handlers do not
  see the child's tool calls (separate process). Not reproduced locally; derived from the
  docs table and the spawn args.
- Distinct identifier: the child is started with `--no-session`, which makes `main.ts` line
  359-360 use `SessionManager.inMemory(cwd, ...)`; `newSession()` assigns
  `this.sessionId = options?.id ?? createSessionId()` (`session-manager.ts` line 930), i.e. a
  fresh uuidv7. So the child's `PI_SESSION_ID` (question 6) differs from the parent's.
  Looked in `examples/extensions/subagent/index.ts` (spawn call, args), `docs/extensions.md`,
  `docs/environment-variables.md` and `src/core/extensions/types.ts`; did not find any
  variable, flag, or event field that marks a process as a sub-agent or links it to a parent
  session id. The bash tool deletes inherited `PI_SESSION_*` before setting its own
  (`src/core/tools/bash.ts` lines 172-177), so a nested pi's shell commands never see the
  parent's session id either.
- Different working directory: yes — the example tool's schema has
  `cwd: Type.Optional(Type.String({ description: "Working directory for the agent process" }))`
  (`index.ts` lines 445, 451, 468) and passes it to `spawn({ cwd })`. The SDK takes `cwd`
  in `createAgentSession` (`docs/sdk.md` heading "Directories", line 333).
- Git worktree: looked in `docs/*.md`, `examples/**` (grep -i worktree), and `CHANGELOG.md`;
  found only unrelated fixes (context files loading twice under a linked worktree, #7221;
  status bar branch in a worktree, #490; autocomplete). Did not find any worktree-creation
  feature for sub-agents. A different `cwd` pointing at an existing worktree is the only
  route shown.

## 4. Skills

- Yes: `docs/skills.md` line 7: "Pi implements the [Agent Skills standard]
  (<https://agentskills.io/specification>), warning about most violations but remaining
  lenient." Pi does not require `name` to match the parent directory. Read 2026-09-06.
- Directories (`docs/skills.md` heading "Locations", line 24):
  - Global: `~/.pi/agent/skills/`, `~/.agents/skills/`
  - Project (after trust): `.pi/skills/`, and `.agents/skills/` in `cwd` and ancestor
    directories up to the git repo root (or filesystem root)
  - Packages: `skills/` directories or `pi.skills` entries in `package.json`
  - Settings: `skills` array (files or directories) — the doc shows `"skills":
    ["~/.claude/skills", "~/.codex/skills"]` and project `"skills": ["../.claude/skills"]`
  - CLI: `--skill <path>` (repeatable); `--no-skills` disables discovery
  - Discovery: directories containing `SKILL.md` are found recursively in all locations;
    root `.md` files with valid frontmatter count as skills in `~/.pi/agent/skills/` and
    `.pi/skills/`.
- Path variable substitution at HEAD: none. Evidence:
  - `src/core/skills.ts` reads the file only to parse frontmatter (`readFileSync` at line
    286) and builds the system-prompt XML with `<name>`, `<description>`, `<location>`
    (lines 374-376); no `replace` touching `{baseDir}` (grep for `baseDir` across
    `packages/coding-agent/src` finds only the `Skill.baseDir` field, line 78, and unrelated
    `migrations.ts`/`config-selector.ts` uses).
  - `/skill:name` expansion, `src/core/agent-session.ts` `_expandSkillCommand` (lines
    1353-1377): `const body = stripFrontmatter(content).trim();` then wraps it as
    `<skill name="..." location="${skill.filePath}">\nReferences are relative to ${skill.baseDir}.\n\n${body}\n</skill>`.
    The body is inserted verbatim; the directory is stated in a prefix line, not substituted
    into the body.
  - Model-driven loading is a plain `read` of `SKILL.md` (`docs/skills.md` "How Skills
    Work", line 76: "the agent uses `read`, or `bash` when `read` is unavailable, to load the
    full SKILL.md ... using relative paths to reference scripts and assets").
  - No `{baseDir}` token appears in any `.md` under `packages/coding-agent` other than the
    changelog (grep, read 2026-09-06).
  - Changelog history (`CHANGELOG.md`): under `## [0.19.0] - 2025-12-12` (line 5253):
    "Skills system ... Supports `{baseDir}` placeholder." Under `## [0.24.0] - 2025-12-19`
    (line 5063): "Skills standard compliance ... Removed `{baseDir}` placeholder in favor of
    relative paths. ([#231](https://github.com/badlogic/pi-mono/issues/231))". So the
    placeholder existed for one week in Dec 2025 and is gone at HEAD (0.85.1).
  - Prompt templates (not skills) do substitute `$1`, `$ARGUMENTS`, `$@`, `${N:-default}`
    (`src/core/prompt-templates.ts` `substituteArgs`, lines 60-90).

## 5. MCP

- Natively: no. `README.md` line 499: "**No MCP.** Build CLI tools with READMEs (see
  Skills), or build an extension that adds MCP support." `docs/usage.md` line 309 (quoted in
  question 3). Looked in `docs/settings.md`, `docs/sdk.md`, `docs/index.md`, `CHANGELOG.md`,
  `examples/**`, and `src/**` for "mcp" (case-insensitive); the only hits are the two prose
  statements above and a comment in `src/utils/tool-result-images.ts` ("extensions, MCP
  bridges, screenshot tools"). Did not find any settings key or CLI flag registering an MCP
  server. Read 2026-09-06.
- Via an extension: yes, that is the documented route (`README.md` "Extensions" > "What's
  possible" lists "MCP server integration", line 395). A third-party pi package exists:
  `@spences10/pi-mcp` 0.0.60 on npm (`https://registry.npmjs.org/@spences10/pi-mcp/latest`,
  read 2026-09-06): description "MCP server integration for Pi that exposes configured MCP
  tools safely and manages large responses", keywords include `pi-package`, `pi.extensions:
  ["./dist/index.js"]`, repository `github.com/spences10/my-pi` (`packages/pi-mcp`). Its
  README (`raw.githubusercontent.com/spences10/my-pi/main/README.md`) says servers come from
  an `mcp.json` file ("stdio and HTTP/streamable-HTTP servers from `mcp.json`"). This is a
  third-party claim about a third-party package; not reproduced. `pi.dev/packages` (the
  official gallery) is blocked by this session's egress proxy — looked, could not read.

## 6. Environment variables set for a shell command

Source: `docs/environment-variables.md` (headings "Process Marker" and "Shell Tool Session
Environment") and `src/core/tools/bash.ts` `resolveSpawnContext` (lines 165-190). Read
2026-09-06.

Injected into commands run by the LLM-callable `bash` and `powershell` tools (resolved at
each command start; not injected into user-typed `!`/`!!` commands):

| Variable | Value |
|---|---|
| `PI_SESSION_ID` | `ctx.sessionManager.getSessionId()` (uuidv7; also set for ephemeral `--no-session` sessions) |
| `PI_SESSION_FILE` | absolute path of the session JSONL; unset for ephemeral sessions |
| `PI_PROVIDER` | selected model provider |
| `PI_MODEL` | selected model id |
| `PI_REASONING_LEVEL` | `off`/`minimal`/`low`/`medium`/`high`/`xhigh`/`max` |

Code (`bash.ts` 172-187): inherited `PI_SESSION_ID`, `PI_SESSION_FILE`, `PI_PROVIDER`,
`PI_MODEL`, `PI_REASONING_LEVEL` are deleted first, then re-set from the current session when
`exposeSessionEnvironment` (default `true`) is on. A `spawnHook` receives
`{ command, cwd, env }` and may change any of them.

Process markers set on the pi process itself and inherited by all children (CLI and RPC
entry points; `src/cli/setup.ts` lines 6-7, `src/rpc-entry.ts` lines 7-8): `AI_AGENT=pi`,
`PI_CODING_AGENT=true`. Docs: "They are not session-specific and are not set automatically
when Pi is embedded through the SDK."

Working directory: no environment variable carries it. The command is spawned with `cwd`
set to the tool's cwd (`BashSpawnContext.cwd`, `bash.ts` lines 157-161), so `$PWD` inside
the shell reflects it, but looked in `docs/environment-variables.md` and `bash.ts`, did not
find a `PI_CWD`-style variable. No variable identifies a sub-agent or parent session (see
question 3).
