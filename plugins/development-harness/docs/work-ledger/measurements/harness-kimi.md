# Harness facts: Kimi (Kimi Code CLI, MoonshotAI/kimi-code)

Date of all reads: 2026-09-06. Sources are the product's GitHub repository at its default branch
`main` (HEAD `af81bb92215dca2f933579ce0119f7add452bc96`, confirmed with
`git ls-remote https://github.com/MoonshotAI/kimi-code.git HEAD`) and the docs source in that
repository (`docs/en/**`). The rendered docs host `moonshotai.github.io` is blocked by this
session's egress proxy, so every doc was read from `raw.githubusercontent.com/MoonshotAI/kimi-code/main/<path>`;
the raw path is what is cited below. Source-file claims are from reading the TypeScript at that
commit; none were reproduced by running the CLI. `apps/kimi-code/package.json` at that commit
declares `"version": "0.41.0"`.

## Identity: which product "Kimi" is

**Established**: the harness is **Kimi Code CLI**, GitHub `MoonshotAI/kimi-code` (TypeScript,
default engine package `@moonshot-ai/agent-core-v2`). It is the successor of **Kimi CLI**,
GitHub `MoonshotAI/kimi-cli` (Python, `src/kimi_cli/`), which is being wound down.

Evidence:

- Repository notes. `plugins/plugin-creator/CLAIMS-REGISTER.md` line 45 lists "Codex, OpenCode,
  Crush, Cursor and Kimi" as harnesses whose source and vendor docs were checked for
  `${CLAUDE_PLUGIN_ROOT}` substitution — a coding-agent harness, alongside other CLI agents.
  `research/skill-generation-tools/compound-engineering-plugin.md` line 66 names "Kimi Code CLI"
  in a list of deployment targets next to Claude Code, Cursor, Codex CLI, OpenCode and Pi.
  `research/coding-agents/pi-mono.md` and `research/claude-code-plugins/claude-codex-settings.md`
  mention only the Kimi *model/provider* (Kimi K2, `api.moonshot.ai`), not a harness. Search run:
  `grep -rn -i "kimi" research/ plugins/plugin-creator/` on 2026-09-06.
- Product docs. `https://raw.githubusercontent.com/MoonshotAI/kimi-cli/main/README.md` (read
  2026-09-06) states verbatim: "**Kimi CLI is evolving into [Kimi Code CLI](https://github.com/MoonshotAI/kimi-code)**
  — the next-generation terminal AI agent from the same team. Installing Kimi Code CLI
  automatically migrates your configuration and sessions. This project will be gradually wound
  down; the docs and existing installations remain available."
  `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/README.md` (read 2026-09-06)
  describes "an AI coding agent that runs in your terminal — it can read and edit code, run shell
  commands, search files, fetch web pages" with bullets "Lifecycle hooks", "Subagents for
  focused, parallel work", "Rich plugin ecosystem. Install skills, MCP servers, and data sources
  from the marketplace or any GitHub repo", "AI-native MCP configuration".
- Web search "Kimi CLI Moonshot AI github MoonshotAI/kimi-cli" (2026-09-06) returned both
  repositories and the docs site `moonshotai.github.io/kimi-code/en/`; the legacy docs at
  `moonshotai.github.io/kimi-cli/en/` are titled "Kimi Code CLI Docs" as well.
- Engine choice inside kimi-code: `docs/en/configuration/env-vars.md` row `KIMI_CODE_LEGACY_FLAG`:
  "Legacy `agent-core` engine for `kimi`, `kimi -p`, ... (default: `agent-core-v2`)", and
  `apps/kimi-code/package.json` depends on `"@moonshot-ai/agent-core-v2": "workspace:^"`. Answers
  below cite `packages/agent-core-v2/` (the default engine); where the legacy
  `packages/agent-core/` differs it is noted.

The legacy `kimi-cli` also had hooks (`docs/en/customization/hooks.md` there, "Hooks (Beta)",
config in `~/.kimi/config.toml`, 13 events, base fields `session_id`, `cwd`, `hook_event_name`,
read 2026-09-06), but the questions below are answered for the successor.

## 1. Shell command, read file, write file

**Answer**: yes to all three. Built-in tools `Bash` (execute a shell command), `Read` (read a
text file), `Write` (create or overwrite a file), plus `Edit` (string replacement), `Grep`,
`Glob`, `ReadMediaFile`.

- Source: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/reference/tools.md`,
  tables under "File tools" and "Shell execution" (read 2026-09-06). Approval column: `Read`,
  `Grep`, `Glob` auto-allow; `Write`, `Edit`, `Bash` require approval.
- `Bash` parameters (`packages/agent-core-v2/src/agent/tools/os/bash/bash.ts`, `BashInputSchema`,
  read 2026-09-06): `command` (required), `cwd` ("When omitted, the command runs in the
  session's working directory"), `timeout` (seconds), `description`, `run_in_background`,
  `disable_timeout`. The docs page's `Bash` paragraph says "stdin is always closed — interactive
  commands receive EOF immediately".

## 2. Hooks

**Answer**: yes. Hooks are **shell commands** (a `command` string run with `shell: true`),
configured as a `[[hooks]]` array in `~/.kimi-code/config.toml` (`$KIMI_CODE_HOME/config.toml`),
and a **plugin can ship them** in its manifest `hooks` array. The payload is JSON on stdin.

Sources (read 2026-09-06):

- Doc: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/customization/hooks.md`,
  headings "Configuration", "Event Data Format", "Return Values", "Event Reference".
- Doc: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/customization/plugins.md`,
  heading "Hooks in Plugins".
- Source: `packages/agent-core-v2/src/features/externalHooks/configSection.ts` (config schema),
  `internal/types.ts` (event list), `internal/matchHooks.ts` (payload assembly),
  `internal/runHook.ts` (process spawn), `app/externalHooksRunnerService.ts` (runner),
  `agent/agentExternalHooksService.ts` (agent-scoped events), `session/sessionExternalHooksService.ts`
  (session-scoped events), `packages/agent-core-v2/src/app/plugin/manager.ts` (`enabledHooks()`).

Config fields (`hooks.md` "Configuration", enforced by `HookDefSchema ... .strict()` in
`configSection.ts`): `event` (string, required), `matcher` (regex, optional), `command` (string,
required), `timeout` (integer seconds 1–600, default 30). "`[[hooks]]` only allows these four
fields; extra fields will cause the config file to fail to load."

Event list (`internal/types.ts` `HOOK_EVENT_TYPES`, matches the doc's "Event Reference" table):
`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionResult`,
`UserPromptSubmit`, `UserPromptQueued`, `TurnStarted`, `Stop`, `StopFailure`, `Interrupt`,
`SessionStart`, `SessionEnd`, `SessionHeartbeat`, `SubagentStart`, `SubagentStop`, `TaskStarted`,
`PreCompact`, `PostCompact`, `Notification`. Blockable (exit code 2 or stdout JSON
`hookSpecificOutput.permissionDecision: "deny"`): `PreToolUse`, `Stop`, `UserPromptSubmit` only.
The legacy `packages/agent-core/src/session/hooks/types.ts` lacks `UserPromptQueued`,
`TurnStarted`, `SessionHeartbeat`, `TaskStarted`.

Payload assembly (`matchHooks.ts` `runMatchedHooks` → `toHookInputData`): every camelCase key is
converted to snake_case; base keys are `hookEventName`, `sessionId` (`args.sessionId ?? ''`),
`cwd` (`args.cwd ?? ''`), then `args.inputData` spread on top. The runner
(`externalHooksRunnerService.ts` `triggerInner`) sets `cwd: args.cwd ?? this.bootstrap.cwd` and
prepends `clientType: this.bootstrap.clientIdentity.platform` to `inputData`. Agent-scoped
events (`agentExternalHooksService.ts`) do not pass `cwd`, so their `cwd` is the bootstrap
(process start) working directory, and `withSessionFacts` adds `sessionTitle`. The doc's
"Event Data Format" example of the base object:

```json
{
  "hook_event_name": "PreToolUse",
  "session_id": "session_abc",
  "session_title": "Fix the login page",
  "client_type": "kimi_code_cli",
  "cwd": "/path/to/project"
}
```

**`PostToolUse` payload — every field** (`agentExternalHooksService.ts` `notifyPostToolUse`,
serialized by `JSON.stringify` in `runHook.ts`, which drops `undefined` values):

| Field | Value |
| --- | --- |
| `hook_event_name` | `"PostToolUse"` (`"PostToolUseFailure"` when `result.isError === true`) |
| `session_id` | `this.sessionContext.sessionId` |
| `session_title` | session title (absent if not yet read) |
| `client_type` | `bootstrap.clientIdentity.platform`, e.g. `"kimi_code_cli"` |
| `cwd` | bootstrap cwd (process working directory), not the tool's `cwd` argument |
| `tool_name` | `ctx.toolCall.name`, e.g. `"Bash"`, `"Write"` |
| `tool_input` | the tool's argument object as-is (`ctx.args` if a plain object, else `{}`): for `Bash` this includes `command` and, if the model passed it, `cwd`; for `Write` it includes the file path argument |
| `tool_call_id` | `ctx.toolCall.id` |
| `tool_output` | first 2000 chars of the text output (`PostToolUse` only) |
| `error` | `toKimiErrorPayload(output)` (`PostToolUseFailure` only) |

The doc's "Example: Blocking Dangerous Shell Commands" reads `payload.tool_input?.command` for a
`Bash` `PreToolUse` hook. `PreToolUse` carries the same `tool_name`, `tool_input`, `tool_call_id`.
No field names the tool's own working directory except whatever the model put in
`tool_input.cwd`. **No sub-agent identifier**: `inputData` contains no `agent_id`; the only place
`agentId` appears in that service is the internal `HookResult` UI event, not the stdin payload.

**`Stop` payload — every field** (`runStop`): `hook_event_name: "Stop"`, `session_id`,
`session_title`, `client_type`, `cwd` (bootstrap cwd), `stop_hook_active: false`. No tool name,
no tool input, no agent identifier. `Stop` fires from the agent loop's `onDidFinishStep` when the
finish reason is not `tool_calls`/`filtered` and no requests are pending; if the hook blocks, its
reason is appended as a `user` message with origin `system_trigger`/`stop_hook` and the loop
continues once (`stopHookContinuationUsed`).

Other payload extras read from source: `SubagentStart` → `agent_name` (profile name, e.g.
`coder`), `prompt`, `session_title`, `cwd` = session cwd; `SubagentStop` → `agent_name`,
`response`, `session_title`; `SessionStart` → `source`, `session_title`, `model`, `profile`;
`SessionEnd` → `reason`, `session_title`; `TaskStarted` → `task_id`, `kind`, `description`,
`status`, `detached`, `started_at`; `TurnStarted` → `turn_id`, `origin_kind`, `origin_name`,
`prompt`; `Interrupt` → `turn_id`, `reason`; `StopFailure` → `error_type`, `error_message`;
`PreCompact` → `trigger`, `token_count`; `PostCompact` → `trigger`, `estimated_token_count`;
`UserPromptSubmit` → `prompt`, `is_steer`; `UserPromptQueued` → `prompt_id`, `prompt`,
`queue_length`; `SessionHeartbeat` → `session_title`, `uptime_ms`; `PermissionRequest` /
`PermissionResult` → all fields of the corresponding event object minus `type`/`time`.

Hook process (`runHook.ts` + `internal/matchHooks.ts`): spawned via `hostProcess.spawn(command,
[], { shell: true, cwd, env })`; `cwd` = `hook.cwd` if set, else the trigger `cwd`; doc: "The
working directory for hook commands is the current session's project directory." `env` is
`undefined` for `config.toml` hooks (`hostProcessService.ts` `buildEnv` returns `undefined` →
the child inherits the CLI's environment unchanged; no `KIMI_*` variables are added). Fail-open:
non-zero exit other than 2, timeout, or crash all allow. Multiple matching rules run in
parallel; identical `(cwd, command)` pairs run once.

Plugin hooks (`plugins.md` "Hooks in Plugins"; `manager.ts` `enabledHooks()`): manifest field
`"hooks": [{ "event", "matcher", "command", "timeout" }]`; "Each hook runs with its working
directory set to the plugin root"; "The hook process receives two extra environment variables:
`KIMI_CODE_HOME` and `KIMI_PLUGIN_ROOT` (the plugin root directory)"; active only while the
plugin is enabled. A skill collection that is not a plugin cannot ship hooks: looked in
`docs/en/customization/skills.md` and `skillRoots.ts`, did not find any hook field on a skill or
skill directory. Project-level hooks: looked in `hooks.md`, `config-files.md` ("Project-local
configuration" describes only `[workspace] additional_dir` in `.kimi-code/local.toml`), and
`configSection.ts`; did not find a project-level hook source — hooks come from
`config.toml` plus enabled plugins (`externalHooksRunnerService.ts` `load()`).

## 3. Sub-agents

**Answer**: yes — the **`Agent`** tool (and `AgentSwarm` for fan-out). Hooks do fire inside a
sub-agent, the payload carries **no identifier distinct from the parent**, and there is no
option to give a sub-agent a different working directory or a git worktree.

Sources (read 2026-09-06):

- Doc: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/customization/agents.md`,
  headings "Built-in Sub-Agents", "How to Invoke", "Context Isolation and Resource Cost",
  "Agent File Format", "Agent Locations", "Storage Location in the Session Directory".
- Doc: `.../docs/en/reference/tools.md`, paragraphs "**`Agent`**" and "**`AgentSwarm`**".
- Source: `packages/agent-core-v2/src/agent/tools/agent/agent.ts` (`SubagentToolInputSchema`),
  `agentTool.ts`, `packages/agent-core-v2/src/session/subagent/subagentService.ts` (`spawn`),
  `spawn.ts`, `subagent.ts`, `packages/agent-core-v2/src/features/feature.ts`
  (`contributeAgentService`), `packages/agent-core-v2/src/_base/di/fiber.ts` line 397 and
  `_base/di/instantiation.ts` `ScopeActivation`.

Mechanism: `Agent` parameters (`agent.ts`): `prompt` (required), `description` (required),
`subagent_type` (default `coder`; built-ins `coder`, `explore`, `plan`), `resume` (agent ID),
`run_in_background`, `fork` (experimental, `KIMI_CODE_EXPERIMENTAL_SUBAGENT_FORK`), `model`.
`AgentSwarm`: `prompt_template` with `{{item}}`, `items`, `resume_agent_ids`, `subagent_type`,
`model`; up to 128 subagents. Custom agents are Markdown files with YAML frontmatter (`name`,
`description`, `whenToUse`, `override`, `tools`, `disallowedTools`, `subagents`) discovered from
`.kimi-code/agents/`, `.agents/agents/`, `extra_agent_dirs`, `$KIMI_CODE_HOME/agents/`,
`~/.agents/agents/`, plugins (`agents` manifest field), built-in. Each sub-agent instance gets an
ID (`agent-0` etc.) and a directory `sessions/<workDirKey>/<sessionId>/agents/agent-0/wire.jsonl`
(`data-locations.md` "Session data"; `agents.md` "Storage Location in the Session Directory").

Hooks inside the sub-agent: `ExternalHooksFeature` registers `AgentExternalHooksService` with
`contributeAgentService(...)` (`externalHooksFeature.ts`), i.e. `LifecycleScope.Agent` with no
`activation` option; `fiber.ts` line 397 maps a missing `activation` to `'eager'`, so the service
is instantiated for every agent scope, and `subagentService.ts` `spawn()` creates sub-agents
through the same `agentLifecycle.create(...)`. Therefore `PreToolUse`, `PostToolUse`, `Stop`,
`TurnStarted` etc. fire for the sub-agent's own tool calls and turns. Source-read, not
reproduced by running the CLI.

Identifier: the sub-agent's `PostToolUse`/`Stop` payloads are built by the same
`notifyPostToolUse`/`runStop` code with `sessionId` (shared with the parent), `sessionTitle`,
`cwd` (bootstrap), tool fields — no `agent_id`, no `parent_agent_id`. The parent-side
`SubagentStart`/`SubagentStop` payloads carry `agent_name` (the profile name, e.g. `coder`), not
the instance ID (`AgentTaskStartHookContext` in `subagent.ts` has only `agentName`, `prompt`,
`signal`). The legacy `packages/agent-core/src/session/subagent-host.ts` behaves the same
(`agentName: profileName`); its telemetry event `subagent_created` has `agent_id` and
`parent_agent_id`, but that is telemetry, not a hook payload.

Working directory / worktree: `SubagentToolInputSchema` has no `cwd` or `worktree` parameter;
`subagentService.ts` `spawn()` passes only `binding: { profile, model, thinking }`, `labels`,
`runtimeId`, and `applyPromptPrefix` uses `this.sessionContext.cwd`. Looked in `agents.md`,
`tools.md`, `agent.ts`, `spawn.ts`, `subagentService.ts` for `worktree`/`cwd` options, did not
find one. A GitHub code search `repo:MoonshotAI/kimi-code path:docs/en worktree` returned zero
files; a search over `packages/agent-core-v2/src` returned only
`features/tower/tools/spawn/spawnTool.ts` and `features/tower/towerService.ts` ("tower" missions
with a `worktree` slot) — a separate mechanism from the `Agent` tool that I did not read in full.

## 4. Plugins and skills

**Answer**: yes, it loads `SKILL.md` skills (directory form with YAML frontmatter `name`,
`description`; also flat `.md`). It has a plugin manifest, `kimi.plugin.json` (or
`.kimi-plugin/plugin.json`). It substitutes `${KIMI_SKILL_DIR}` (and, in source,
`${KIMI_SESSION_ID}`) in skill bodies; it does **not** substitute `${CLAUDE_PLUGIN_ROOT}`.

Sources (read 2026-09-06):

- Doc: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/customization/skills.md`,
  headings "Creating a Skill", "File Format", "Frontmatter Fields", "Body Placeholders",
  "Skill Locations".
- Doc: `.../docs/en/customization/plugins.md`, headings "Writing a Plugin" (manifest table),
  "Hooks in Plugins", installation notes.
- Source: `packages/agent-core-v2/src/features/skill/catalog/registry.ts` lines 166–168,
  `packages/agent-core-v2/src/features/skill/catalog/skillRoots.ts`,
  `packages/agent-core-v2/src/app/plugin/manifest.ts`, `packages/agent-core-v2/src/app/plugin/manager.ts`
  `pluginSkillRoots()`.

Skill directories (`skills.md` "Skill Locations", priority Project > User > Extra > Built-in;
constants in `skillRoots.ts`): project level `.kimi-code/skills/` and `.agents/skills/` (project
root = nearest directory containing `.git`, searching upward); user level
`$KIMI_CODE_HOME/skills/` (default `~/.kimi-code/skills/`) and `~/.agents/skills/`; extra
directories from top-level `extra_skill_dirs` in `config.toml`; built-in skills shipped with the
CLI; plugin skills from the manifest's `skills` paths (`manager.ts` `pluginSkillRoots()`; "if
omitted, root `SKILL.md` is the single Skill root"). Frontmatter recognised: `name`,
`description`, `type` (`prompt`/`inline`/`flow`), `whenToUse`, `disableModelInvocation`,
`arguments`. Invocation: `/skill:<name> [args]` by the user, automatic model invocation by
description, or the `Skill` tool for `type: inline`.

Plugin manifest (`plugins.md` table): `name` (required, `[a-z0-9][a-z0-9_-]{0,63}`), `version`,
`description`, `keywords`, `author`, `homepage`, `license`, `interface`, `skills`, `agents`,
`sessionStart.skill`, `skillInstructions`, `systemPrompt`, `systemPromptPath`, `mcpServers`,
`hooks`, `commands`. Located at `<plugin_root>/kimi.plugin.json` or
`<plugin_root>/.kimi-plugin/plugin.json` (`manifest.ts` constants `KIMI_PLUGIN_ROOT_PATH`,
`KIMI_PLUGIN_DIR_PATH`). Installed via `/plugins install <path-or-url>` (GitHub URLs accepted);
"Local installations are copied to `$KIMI_CODE_HOME/plugins/managed/<id>/`, and the CLI always
runs from this managed copy."

Path-variable substitution in skill bodies (`skills.md` "Body Placeholders"; `registry.ts`):
`$ARGUMENTS`, `$ARGUMENTS[n]`/`$n`, `$<name>`, `${KIMI_SKILL_DIR}` ("The directory containing the
current Skill file"); source additionally does `.replaceAll('${KIMI_SESSION_ID}', context.sessionId ?? '')`
(undocumented in `skills.md`). `${CLAUDE_PLUGIN_ROOT}`: GitHub code search
`repo:MoonshotAI/kimi-code CLAUDE_PLUGIN_ROOT` returned zero results on 2026-09-06, and the
`replaceAll` chain in `registry.ts` names only the two `KIMI_*` variables — so the literal string
passes through to the model. `KIMI_PLUGIN_ROOT` exists only as an environment variable given to
plugin hook processes and plugin MCP servers (`manager.ts`), not as a body placeholder.

## 5. MCP

**Answer**: yes. `mcp.json` at user level (`~/.kimi-code/mcp.json` / `$KIMI_CODE_HOME/mcp.json`)
and project level (`.kimi-code/mcp.json`), plus a plugin manifest's `mcpServers`.

- Source: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/customization/mcp.md`,
  headings "Connection Methods", "Configuration" (read 2026-09-06). Schema:
  `{"mcpServers": {"<name>": {"command", "args", "env", "cwd"}}}` for stdio, `{"url"}` for HTTP,
  `{"transport": "sse", "url"}` for legacy SSE; optional `headers`, `bearerTokenEnvVar`,
  `enabled`, `enabledTools`, `disabledTools`. Project entries override same-named user entries.
  TUI: `/mcp-config`, `/mcp`, `/mcp-config login <server>`.
- `plugins.md` table row `mcpServers`: "MCP server declarations; enabled by default, can be
  disabled from `/plugins`"; stdio paths must start with `./` inside the plugin root.
- `config-files.md` line 512: "MCP server declarations are configured in `~/.kimi-code/mcp.json`
  or the project-local `.kimi-code/mcp.json`, not in `config.toml`."

## 6. Environment variables set for a shell command

**Answer**: the `Bash` tool sets only `NO_COLOR=1`, `TERM=dumb`, `GIT_TERMINAL_PROMPT` (inherited
value or `0`), and `SHELL=<shell path>` on top of the CLI's own environment; it sets nothing
naming the working directory, session, or agent. The working directory is applied by prefixing
the command with `cd '<cwd>' &&`.

- Source: `packages/agent-core-v2/src/agent/tools/os/bash/bashTool.ts` `spawn()` (read
  2026-09-06):
  `const noninteractiveEnv = { NO_COLOR: '1', TERM: 'dumb', GIT_TERMINAL_PROMPT: process.env['GIT_TERMINAL_PROMPT'] ?? '0', SHELL: env.shellPath }`
  and `shellCommand = \`cd ${shellQuote(shellCwd)} && ${command}\``; then
  `processService.spawn(env.shellPath, ['-c', shellCommand], { env: noninteractiveEnv })`.
  `packages/agent-core-v2/src/os/backends/node-local/hostProcessService.ts` `buildEnv` merges
  `{ ...process.env, ...overrides }`. The legacy`packages/agent-core/src/tools/builtin/shell/bash.ts`
  lines 281–297 build the same four variables merged over `process.env`.
- Doc: `https://raw.githubusercontent.com/MoonshotAI/kimi-code/main/docs/en/configuration/env-vars.md`
  (read 2026-09-06) lists only variables the CLI *reads* (`KIMI_CODE_HOME`, `KIMI_MODEL_*`,
  runtime switches, `KIMI_SHELL_PATH`, proxies, `HOME`, `PATH`, ...) and states "The CLI also reads
  several standard system variables to detect the runtime environment; it does not modify them".
  Looked in that page and in `bashTool.ts`/`hostProcessService.ts` for any `KIMI_SESSION*`,
  `KIMI_AGENT*`, or cwd variable exported to child shells; did not find one. Variables the harness
  *does* set for other child processes: `KIMI_CODE_HOME` and `KIMI_PLUGIN_ROOT` for plugin hooks
  and plugin MCP servers (`app/plugin/manager.ts`), and `env`/`cwd` from `mcp.json` for stdio MCP
  servers.
