# Cursor agent (IDE Agent mode + `agent` / `cursor-agent` CLI) — harness facts

Date read: 2026-09-06.

**Access caveat (applies to every claim below).** `cursor.com`, `docs.cursor.com`, `forum.cursor.com`,
`web.archive.org`, `r.jina.ai`, `ntorres.dev`, `blog.gitbutler.com` are blocked by this session's egress proxy
(`EGRESS_BLOCKED` / `CONNECT 403`); `Ref-local` returns 405 for the same URLs. So no `cursor.com/docs` page was
read in full. Each claim carries one of these warrants:

- `[repo]` — read from a file fetched verbatim over `raw.githubusercontent.com` from `cursor/plugins` or
  `cursor/plugin-template` (Cursor's own GitHub org; primary source for the plugin format).
- `[docs-snippet]` — text of a `cursor.com/docs/...` page as returned in a WebSearch result summary for that URL.
  The URL and heading are the page the snippet came from; the page itself was not read end to end.
- `[3p]` — third-party observation (forum thread title, GitHub issue, community type-definitions). Secondary;
  marked where it is the only evidence.

Repo prior notes checked: `plugins/development-harness/dh_paths.py` lines 25-70 and
`research/agent-frameworks/cursor-cookbook.md`. The cookbook entry covers only the TypeScript SDK and says nothing
about hooks, plugins, or env vars. `dh_paths.py` asserts that Cursor uses `.cursor-plugin/plugin.json` with
`${CLAUDE_PLUGIN_ROOT}` in script paths and that "Cursor sets `DH_PROJECT_ROOT` to `${workspaceFolder}`" — the
second is this repo's own convention (the repo's `mcp.json` would have to set it), not a Cursor behaviour; see §4
and §6 for what was and was not found. `.cursor/rules/` in this repo holds two `.mdc` rule files only
(`backlog-before-work.mdc`, `json-no-pretty-print.mdc`); there is no `.cursor-plugin/`, `.cursor/hooks.json`,
`.cursor/mcp.json`, or `.cursor/skills/` in the checkout.

---

## 1. Can the agent run a shell command, read a file, write a file? (tool names)

**Answer: yes to all three.**

- Tool list on the Agent tools overview `[docs-snippet]`: **Search** (semantic codebase search, file-name search,
  directory listing, exact keyword/pattern grep), **Web Search**, **Read File** (also image files), **Edit &
  Reapply** ("suggest edits to files and apply them automatically"), **Terminal** ("execute terminal commands and
  monitor output"), **Fetch Rules**, plus browser control. "There is no limit on the number of tool calls Agent can
  make during a task."
  URL: `https://cursor.com/docs/agent/tools` — page title "Overview | Cursor Docs", tool list section. Read
  2026-09-06 via search snippet.
- The Terminal tool has its own page: `https://cursor.com/docs/agent/tools/terminal` ("Terminal | Cursor Docs")
  `[docs-snippet]`.
- Tool names as they appear to hooks (the `preToolUse` matcher runs against the tool name) `[docs-snippet]`:
  **`Shell`**, **`Read`**, **`Write`**, **`Grep`**, **`Delete`**, **`Task`**, and MCP tools as
  **`MCP:<tool_name>`**. URL: `https://cursor.com/docs/hooks`, section on `preToolUse` matchers. A second snippet
  from the same search (source page not certain — it may be `https://cursor.com/docs/reference/third-party-hooks`,
  which documents Claude-Code-format compatibility) lists `Bash, Edit, Write, Read, Glob, Grep, Task,
  mcp__<server>__<tool>` — that is the Claude Code naming Cursor accepts for compatibility, not Cursor's native
  names. Treat `Shell` as the native shell-tool name; treat `Edit`/`Bash`/`Glob` as unconfirmed for Cursor-native
  matchers (looked in the search snippets for cursor.com/docs/hooks, did not find them as Cursor-native names).
- CLI: `agent -p "<prompt>"` runs headless; `--force` (alias `--yolo`) is required for it to *apply* file changes
  in scripts ("without --force, changes are only proposed, not applied") `[docs-snippet]`.
  URL: `https://cursor.com/docs/cli/headless` ("Using Headless CLI | Cursor Docs") and
  `https://cursor.com/docs/cli/reference/parameters`.

---

## 2. Hooks: events, payload fields, `hooks.json` location, plugin-shipped hooks

### Lifecycle events

Event list `[docs-snippet]`, URL `https://cursor.com/docs/hooks` ("Hooks | Cursor Docs"), section listing
"Agent hooks" (the docs group hooks into three categories by trigger; the 2.4 changelog and the CLI changelog
confirm the same list for the CLI):

| Cursor event | Claude-Code equivalent | Notes |
|---|---|---|
| `sessionStart` / `sessionEnd` | SessionStart / SessionEnd | session lifecycle |
| `beforeSubmitPrompt` | UserPromptSubmit | can modify/deny the prompt |
| `preToolUse` / `postToolUse` / `postToolUseFailure` | PreToolUse / PostToolUse | generic, fire for every tool |
| `beforeShellExecution` / `afterShellExecution` | PreToolUse(Bash) / PostToolUse(Bash) | shell-specific |
| `beforeMCPExecution` / `afterMCPExecution` | — | MCP-specific |
| `beforeReadFile` / `afterFileEdit` | — / PostToolUse(Edit\|Write) | file-specific |
| `afterAgentThought` / `afterAgentResponse` | — | streaming events |
| `preCompact` | PreCompact | |
| `subagentStart` / `subagentStop` | SubagentStart / SubagentStop | "Subagent (Task tool) lifecycle hooks" |
| `stop` | Stop | end of agent turn |
| `workspaceOpen` | — | "App lifecycle" hook; fires outside any agent session |

Cloud agents run the command-based subset from the repo's `.cursor/hooks.json`: `preToolUse`,
`beforeShellExecution`, `afterFileEdit`, `beforeSubmitPrompt`, `subagentStart`/`subagentStop`, `preCompact`,
`afterAgentResponse`/`afterAgentThought`, `stop`, and also `afterShellExecution`, `beforeReadFile`, `postToolUse`,
`postToolUseFailure` `[docs-snippet]` (URL `https://cursor.com/docs/cloud-agent`, hooks section).

### Common fields on every hook payload

`[docs-snippet]` URL `https://cursor.com/docs/hooks`, section "Common schema" / "Input (all hooks)":

- `conversation_id` (string) — "Stable ID of the conversation across many turns"
- `generation_id` (string) — "changes with every user message"
- `model` (string) — model configured for the composer that triggered the hook
- `hook_event_name` (string)
- `cursor_version` (string)
- `workspace_roots` (array of paths) — **this is the workspace/working-directory field**
- `user_email` (string | null)
- `transcript_path` (string | null)
- `session_id` — named in the docs' note that `workspaceOpen` "omits conversation_id, generation_id, model,
  session_id, and transcript_path" (so agent-session hooks carry `session_id`); the `sessionStart` input is
  described as carrying `session_id`, an is-background-agent flag, and the composer mode `[docs-snippet]`.

Hooks are "spawned processes that communicate over stdio using JSON in both directions" — input on stdin, response
on stdout `[docs-snippet]`. Hook command paths are relative to the `hooks.json` file's directory `[3p:
johnlindquist/cursor-hooks README; forum thread "Inconsistent working directory for plugin hook commands"]`.

### After-tool and stop events — full field lists

**`afterShellExecution`** `[docs-snippet]` (URL `https://cursor.com/docs/hooks`, `afterShellExecution` section):
common fields + `command` (the shell command string), `cwd` (working directory of the command), `output` (full
terminal output), `duration` (ms, "excludes the time the command spent waiting for approval"), and the same
`sandbox` boolean that `beforeShellExecution` carries. Tool name is implied by `hook_event_name`.
`beforeShellExecution` input: common + `command`, `cwd`, `sandbox`; output `permission` = `allow|ask|deny` with
optional `user_message` / `agent_message` `[docs-snippet]`.

**`afterFileEdit`** `[docs-snippet]` (same page, `afterFileEdit` section; also mirrored by
`johnlindquist/cursor-hooks/src/types.ts` `[3p]`): common fields + `file_path` (absolute path) + `edits`
(array of `{old_string, new_string}`). No response is read (notification hook). A forum thread reports
`old_string` arriving empty in Cursor 2.3.0 `[3p]`. Looked in the snippets for a `cwd` on `afterFileEdit`; did
not find one — the workspace comes from `workspace_roots`.

**`postToolUse`** `[docs-snippet]`: `tool_name`, `tool_input`, `tool_use_id`, `tool_response` plus common fields.
For a shell call `tool_name` is `Shell` and the command string is inside `tool_input`; for a write, `tool_name`
is `Write` and the path is inside `tool_input`. The snippet that listed `session_id, transcript_path, cwd,
permission_mode, hook_event_name, tool_name, tool_input, tool_use_id` is the Claude-Code-shaped variant that Cursor
accepts under third-party-hooks compatibility (`https://cursor.com/docs/reference/third-party-hooks`); Cursor's
own `postToolUse` field list beyond `tool_name/tool_input/tool_use_id/tool_response` + common fields was not
seen — looked in three WebSearch passes on cursor.com/docs/hooks, did not find a fuller list.

**`stop`** `[docs-snippet]`: common fields + `status` (`completed` | `aborted` | `error`) + `loop_count`
(starts at 0). Response may carry `followup_message`; if non-empty Cursor "automatically submit[s] it as the next
user message" (loop flows). `hooks.json` entries for `stop` accept `loop_limit` (seen as `"loop_limit": null` in
`cursor/plugins/ralph-loop/hooks/hooks.json` `[repo]`).

**`subagentStop`** `[docs-snippet]` (same page, `subagentStop` section): common fields + `subagent_type`
(e.g. `generalPurpose`, `explore`, `shell`), `status` (`completed` | `error` | `aborted`), `task`, `description`,
`summary`, `duration_ms`, `message_count`, `tool_call_count`, `loop_count`, `modified_files` (array),
`agent_transcript_path`. Response may carry `followup_message`. Forum reports `[3p]`: `summary` /
`modified_files` / `agent_transcript_path` arrive missing or null, and `subagentStop` does not fire for
background subagents (thread 166681); `subagentStart`/`subagentStop` carry four id fields — `conversation_id`,
`generation_id`, `session_id`, `parent_conversation_id` — all holding the same value (thread 166533), and
`parent_conversation_id` always equals `conversation_id` (thread 163054).

**`subagentStart`** `[docs-snippet]`: matcher runs against `subagent_type`; input documented to include
`subagent_model` (a forum thread reports it absent in the IDE `[3p]`), and a `parent_conversation_id` field is
reported by users `[3p]`. Output may carry `additional_context` and a permission decision. Looked for the
complete `subagentStart` input list on cursor.com/docs/hooks via snippets; did not find one.

**`sessionStart`** `[docs-snippet]`: input includes `session_id`, an is-background-agent flag, and the composer
mode; output may set env vars that are "passed to all subsequent hook executions within that session".

**Sub-agent identifier in the payload**: no dedicated `subagent_id` / `is_subagent` field was found — looked in
the hooks page snippets, in `johnlindquist/cursor-hooks/src/types.ts`, and in forum titles. What exists is
`conversation_id` (a subagent gets its own conversation UUID — see §3) and `parent_conversation_id` on the two
subagent events (reported as equal to `conversation_id` `[3p]`).

### `hooks.json` locations and precedence

`[docs-snippet]` URL `https://cursor.com/docs/hooks`, "Configuration" / locations section — highest to lowest:

1. Enterprise (MDM, system-wide): macOS `/Library/Application Support/Cursor/hooks.json`, Linux/WSL
   `/etc/cursor/hooks.json`, Windows `C:\ProgramData\Cursor\hooks.json`
2. Team (cloud-distributed, Enterprise plan): configured in the dashboard, synced
3. Project: `<project-root>/.cursor/hooks.json`
4. User: `~/.cursor/hooks.json`

All matching hooks from every source run; on conflicting responses the higher-priority source wins. Schema:
`{"version": 1, "hooks": {"<event>": [{"command": "...", "matcher"?: "...", "timeout"?: n,
"failClosed"?: bool, "type"?: ..., "loop_limit"?: n}]}}` `[docs-snippet + repo]`. The project-level file
requires `"version": 1` — a third-party issue reports all hooks failing to load on Cursor 3.x without it `[3p:
affaan-m/ECC#1519]`; the docs say the `version` field is *not* required for plugin-level hooks
(`~/.cursor/plugins/<plugin>/hooks.json`) `[docs-snippet]`.

### Can a plugin ship hooks? — **Yes.**

- `[repo]` `cursor/plugins/ralph-loop/.cursor-plugin/plugin.json` declares `"hooks": "./hooks/hooks.json"` and
  `ralph-loop/hooks/hooks.json` defines `afterAgentResponse` and `stop` hooks whose `command`s are
  `./hooks/capture-response.sh` and `./hooks/stop-hook.sh` (relative to the plugin root).
- `[repo]` `cursor/plugin-template/plugins/starter-advanced/hooks/hooks.json` defines `afterFileEdit`,
  `beforeShellExecution` (with `"matcher": "rm|curl|wget"`) and `sessionEnd` hooks with `./scripts/...` commands.
- `[repo]` `cursor/plugin-template/docs/add-a-plugin.md` §2: "`hooks/hooks.json` and `scripts/*` for automation
  hooks"; `cursor/plugins/create-plugin/skills/review-plugin-submission/SKILL.md`: "Hooks in `hooks/hooks.json`".
- `[docs-snippet]` `https://cursor.com/docs/hooks`: "Hooks can be defined in hooks.json files at the project or
  user level, or installed through plugins from Customize." Installed plugin hooks live under
  `~/.cursor/plugins/<plugin>/hooks.json`.

---

## 3. Sub-agents

### Spawn mechanism — **the `Task` tool.**

`[docs-snippet]` URL `https://cursor.com/docs/subagents` ("Subagents | Cursor Docs"): "Subagents run
simultaneously when the agent sends multiple Task tool calls in a single message." "The Task tool was called Agent
before v2.1.63; existing Task(...) references still work as aliases." Since Cursor 2.5 subagents can launch child
subagents ("nested launches also need Task tool access in the current mode, and hooks or tool policies can block
spawning"). Built-in subagent types named in the hooks docs: `generalPurpose`, `explore`, `shell`. Custom
subagents are markdown files with YAML frontmatter in `.cursor/agents/` (project; `.claude/agents/` and
`.codex/agents/` also read for compatibility) or `~/.cursor/agents/` (user); frontmatter fields: `name`,
`description`, `model` (`inherit` | `fast` | model id), `readonly`, `is_background`, `isolation`. Subagents "inherit
all tools from the parent, including MCP tools". Available in the editor, the CLI, and Cloud Agents; CLI changelog:
"parallel agents execute locally with live status in interactive, headless, and editor sessions, inheriting your
credentials, rules, and approval policy" `[docs-snippet]` (URL `https://cursor.com/docs/cli/changelog`).

### Do hooks fire inside the sub-agent? — **Yes (observed), with the sub-agent's own `conversation_id`.**

- `[3p]` `rtk-ai/rtk#2786` ("Cursor subagent Shell commands fire preToolUse hook…"): `preToolUse` fires for
  subagent `Shell` tool calls; the subagent payload's `conversation_id` is "a subagent-session-uuid", while the
  parent payload differs by "having a real transcript_path and the main conversation session_id".
- `[3p]` forum 169860 (feature request to block tools on the parent and run them only in subagents) presumes
  the same hooks run in both.
- Looked on cursor.com/docs/hooks and cursor.com/docs/subagents (via snippets) for an explicit sentence "hooks
  run inside subagents"; did not find one. The `subagentStart`/`subagentStop` events are documented; per-tool
  hooks inside subagents are observed, not documented.

### Distinct identifier in the sub-agent's hook payload?

Partially. The tool-level hook payload inside a subagent carries a `conversation_id` that differs from the
parent's `[3p: rtk#2786]`; the `session_id` is reported as the parent's. `parent_conversation_id` exists on
`subagentStart`/`subagentStop` but is reported to equal `conversation_id` `[3p: forum 163054, 166533]`. No
`subagent_id`/`is_subagent` field found (see §2).

### Different working directory / git worktree? — **Yes.**

- `[docs-snippet]` `https://cursor.com/docs/subagents`: "Each subagent gets its own environment: either an
  isolated Git worktree with a separate working directory on the same machine, or its own cloud environment with a
  dedicated VM and clone of the repository." Frontmatter `isolation: worktree` "gives a subagent its own git
  worktree"; "the orchestrator provisions a fresh worktree for each parallel agent invocation … cleaned up when
  the subagent finishes without uncommitted changes." `/in-cloud` makes the next task a cloud subagent;
  `/multitask` dispatches parallel subagents.
- `[docs-snippet]` `https://cursor.com/docs/configuration/worktrees` ("Worktrees | Cursor Docs"):
  `.cursor/worktrees.json` configures setup scripts (`setup-worktree`, `setup-worktree-unix`,
  `setup-worktree-windows`, each a script path or command array); scripts see `$ROOT_WORKTREE_PATH`; Cursor
  "checks [it] when it creates a worktree in the Agents Window, the IDE, or the Cursor CLI". Debug via Output
  panel → "Worktrees Setup". Forum `[3p]` 140187: agents may not wait for the setup script.
- CLI `--workspace <dir>` sets the working directory for a run (`https://cursor.com/docs/cli/reference/parameters`
  `[docs-snippet]`).

---

## 4. Plugins and skills

### `SKILL.md` — **loaded.**

`[docs-snippet]` URL `https://cursor.com/docs/skills` ("Agent Skills | Cursor Docs"): skills auto-load from
`.agents/skills/`, `.cursor/skills/`, `~/.agents/skills/`, `~/.cursor/skills/`, including nested project
subdirectories (e.g. `apps/web/.cursor/skills/`); for compatibility also `.claude/skills/`, `.codex/skills/`,
`~/.claude/skills/`, `~/.codex/skills/`. A skill is a folder containing `SKILL.md` (name comes from the folder),
optional `scripts/`, `references/`, `assets/`. Frontmatter: `name`, `description`, optional
`disable-model-invocation` `[docs-snippet: https://cursor.com/docs/reference/plugins]`. "Reference scripts in
your SKILL.md using relative paths from the skill root." Plugin skills: `<plugin>/skills/<name>/SKILL.md`
`[repo + docs-snippet]`.

### Plugin manifest — **`.cursor-plugin/plugin.json`** (Cursor format) or root `plugin.json` (Agent Plugins standard)

- `[docs-snippet]` `https://cursor.com/docs/reference/plugins` ("Plugins Reference | Cursor Docs"): "Every Cursor
  Plugin requires a `.cursor-plugin/plugin.json` manifest." Two formats: *Agent Plugins* (open standard;
  `plugin.json` at plugin root; skills + MCP) and *Cursor Plugins* (`.cursor-plugin/plugin.json`; adds rules,
  agents, commands, hooks, variables). Manifest declares "up to 17 fields including the six component types:
  skills, agents, rules, hooks, commands, and mcpServers."
- Fields observed in Cursor's own manifests `[repo]` (`cursor/plugins/*/.cursor-plugin/plugin.json`,
  `cursor/plugin-template/plugins/starter-advanced/.cursor-plugin/plugin.json`): `name` (lowercase kebab-case),
  `displayName`, `version`, `description`, `author` `{name, email}`, `homepage`, `repository`, `license`, `logo`
  (relative path), `keywords` (array), `category`, `tags` (array), `minClientVersions` `{"cursor": "3.13.0"}`,
  `variables` (JSON-Schema object with `properties` / `required`; values are substituted as `${NAME}` in
  `mcp.json`), and the component paths `skills` (`"./skills/"`), `rules` (`"./rules/"`), `agents`
  (`"./agents/"`), `commands`, `hooks` (`"./hooks/hooks.json"`), `mcpServers` (`"./mcp.json"`). That is 17.
- Discovery defaults when the path fields are omitted `[repo: create-plugin/skills/review-plugin-submission/SKILL.md;
  plugin-template/docs/add-a-plugin.md]`: `skills/*/SKILL.md`, `rules/*.mdc`, `agents/*.md`,
  `commands/*.(md|mdc|markdown|txt)`, `hooks/hooks.json`, `mcp.json` ("Using a filename other than `mcp.json` for
  MCP server definitions" is listed as a pitfall).
- Multi-plugin repos add `.cursor-plugin/marketplace.json` `{name, owner{name,email}, metadata{description,
  version}, plugins:[{name, source, description}]}` `[repo]`.
- Validator: `cursor/plugin-template/scripts/validate-template.mjs` `[repo]`.
- Plugins install from Customize / Cursor Marketplace or `/add-plugin <name>` `[repo: create-plugin/README.md]`.
  Cursor "supports the Agent Plugins open standard alongside its own plugin format" `[docs-snippet:
  https://cursor.com/docs/plugins]`.

### `${CLAUDE_PLUGIN_ROOT}` / path variable substitution in skill bodies?

- Looked in the cursor.com/docs/skills, /docs/plugins, /docs/reference/plugins and /docs/mcp snippets, in
  `cursor/plugins` and `cursor/plugin-template` manifests, `mcp.json`s, `hooks.json`s, and the template validator:
  **did not find** `${CLAUDE_PLUGIN_ROOT}` or `${CURSOR_PLUGIN_ROOT}` documented as a substitution token for
  skill bodies, `hooks.json`, `mcp.json`, or `plugin.json`. Cursor's manifests use plugin-relative paths
  (`./hooks/...`, `./scripts/...`) and, in `mcp.json`, `${VARIABLE}` from the manifest's `variables` schema and
  the documented `mcp.json` variables (`${env:NAME}`, `${userHome}`, `${workspaceFolder}`,
  `${workspaceFolderBasename}`, `${pathSeparator}`/`${/}`) `[docs-snippet: https://cursor.com/docs/mcp]`.
  A third-party issue states outright: "Cursor's manifest has no `${CURSOR_PLUGIN_ROOT}` equivalent" `[3p:
  mksglu/context-mode#485]`.
- **As an environment variable at hook runtime** (not a text substitution): a forum bug report titled "Cursor CLI
  2026.08.04 leaks CLAUDE_PLUGIN_ROOT between concurrent plugin hooks" says "A hook belonging to a plugin starts
  with the correct `CLAUDE_PLUGIN_ROOT` and `CURSOR_PLUGIN_ROOT`" for "installed Claude Code-compatible plugin[s]"
  `[3p: forum 167628, Aug 2026]`; `microsoft/GitHub-Copilot-for-Azure/docs/hooks.md` says "At runtime, Cursor
  replaces the `CURSOR_PLUGIN_ROOT` variable to construct the path" `[3p]`; several community session-start hooks
  branch on `${CURSOR_PLUGIN_ROOT:-}` `[3p: GitHub code search, 10 hits]`. So: **env var, reported and
  unconfirmed by vendor docs; text substitution in skill bodies, looked and did not find.** The claim in
  `dh_paths.py` that Cursor uses "the same script path variable `${CLAUDE_PLUGIN_ROOT}/scripts/...`" is not
  supported by any source found today.

---

## 5. MCP: can project config or a plugin register an MCP server? — **Both, yes.**

- Project: `.cursor/mcp.json` (repo root) — "affects only that project"; global: `~/.cursor/mcp.json`. "Cursor
  loads both files and merges the server lists. If the same server is defined in both files, project-level wins."
  Schema `{"mcpServers": {"<name>": {"command", "args", "env"} | {"type": "http", "url", "headers"}}}`; variables
  resolved in `command`, `args`, `env`, `url`, `headers`: `${env:NAME}`, `${userHome}`, `${workspaceFolder}`,
  `${workspaceFolderBasename}`, `${pathSeparator}` / `${/}` `[docs-snippet: https://cursor.com/docs/mcp`, "Model
  Context Protocol (MCP) | Cursor Docs", configuration section]. Nested `.cursor/` folders in multi-root
  workspaces are discussed on the forum `[3p: 158433]`.
- Plugin: `.cursor-plugin/plugin.json` `"mcpServers": "./mcp.json"` with `mcp.json` `{"mcpServers": {"github":
  {"type": "http", "url": "https://api.githubcopilot.com/mcp/", "headers": {"Authorization": "Bearer
  ${GITHUB_PERSONAL_ACCESS_TOKEN}"}}}}` and the token declared in the manifest's `variables` schema `[repo:
  cursor/plugins/third_party/github]`; stdio form `{"command": "npx", "args": [...], "env": {...}}` `[repo:
  plugin-template starter-advanced/mcp.json]`. Team MCP servers can be admin-distributed to Agent Window, IDE,
  and CLI `[docs-snippet: https://cursor.com/docs/cli/overview]`.

---

## 6. Environment variables set for a shell command the harness runs

- **`CI=1`** — "Cursor sets `CI=1` as an environment variable when running terminal commands through Agent" (tip:
  prefix `unset CI &&` when a command changes behaviour under CI) `[docs-snippet: https://cursor.com/docs/agent/tools/terminal`,
  "Terminal | Cursor Docs"]. Forum thread 149560 "Cursor sets `CI=1` in recent versions" `[3p]`.
- **`CURSOR_AGENT`** — "Cursor sets the `CURSOR_AGENT` environment variable when it is running, so you can detect
  it in your shell config" (docs show `if [[ -n "$CURSOR_AGENT" ]]` in `~/.zshrc`) `[docs-snippet: same page]`.
  Forum bug 132427 "Cursor CLI is not setting `CURSOR_AGENT=1` … while executing bash commands" `[3p]` implies
  the IDE sets it to `1` and the CLI at some version did not.
- **`CURSOR_CLI`** — reported set by Cursor's *integrated terminal* (not by the agent's shell tool) `[3p: gist
  "Fix: cursor-agent won't run in Cursor/VS Code integrated terminal"]`.
- **`CURSOR_API_KEY`** — read (not set) by the CLI for auth `[docs-snippet: https://cursor.com/docs/cli/reference/configuration]`.
- **`$ROOT_WORKTREE_PATH`** — available to `.cursor/worktrees.json` setup scripts `[docs-snippet:
  https://cursor.com/docs/configuration/worktrees]`.
- **`CLAUDE_PLUGIN_ROOT` / `CURSOR_PLUGIN_ROOT`** — set for *plugin hook processes* in the CLI, per forum bug
  167628 `[3p]`; not found in vendor docs.
- Hook processes: env vars exported by a `sessionStart` hook's output "are passed to all subsequent hook executions
  within that session" `[docs-snippet: https://cursor.com/docs/hooks]`. Forum 157196 reports they do not persist
  across Cursor restarts `[3p]`.
- **Session/agent identity**: looked for `CURSOR_PROJECT_ROOT`, `CURSOR_WORKSPACE`, `CURSOR_SESSION`,
  `CURSOR_TRACE_ID`, `CURSOR_CONVERSATION_ID` across cursor.com/docs snippets (hooks, terminal, CLI configuration,
  MCP) and a plain web search; **did not find** any of them. A forum *feature request* "Cursor conversation ID
  through environment variables" (160346) `[3p]` indicates no such variable existed when it was filed. The
  `CURSOR_PROJECT_ROOT` entry in `dh_paths.py` line 32 is therefore this repo's speculative fallback, not a
  documented Cursor variable; `WORKSPACE_FOLDER_PATHS` (line 31) was likewise not found in Cursor docs (looked in
  the same places). The documented way to learn the workspace is the hook payload's `workspace_roots` (hooks) or
  `${workspaceFolder}` in `mcp.json` (MCP), not a shell env var.
