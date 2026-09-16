# Harness facts: Hermes Agent (Nous Research)

Date read: 2026-09-06. Source of truth: `NousResearch/hermes-agent`, default branch `main`, HEAD
`7166071fcaadb36df26f6d753dda97da6b5d699e` (committed 2026-09-06 05:48 -0700), shallow-cloned into the
session scratchpad and read directly. The docs site `https://hermes-agent.nousresearch.com/docs/` is
blocked by this environment's egress proxy (WebFetch returned `EGRESS_BLOCKED`), so every "docs" citation
below points at the Docusaurus source under `website/docs/` in the repository, which is what that site is
built from (`website/docusaurus.config.ts`, `website/sidebars.ts` exist at HEAD). All GitHub URLs are of
the form `https://github.com/NousResearch/hermes-agent/blob/main/<path>`; the path alone is given after the
first mention.

Convention: each claim names the file and function/heading it was read from. `looked in X, did not find
it` means exactly that — the search was run and returned nothing; it is not a claim of absence.

## Which product

**Identified product**: Hermes Agent by Nous Research — `https://github.com/NousResearch/hermes-agent`,
README tagline "The agent that grows with you"; docs site `https://hermes-agent.nousresearch.com/docs/`.

Evidence, repository side (`/home/user/claude_skills`):

- `rules/AGENTS.md` lines 3-9: "Plain-content mirror of `.claude/rules/*.md` for tools without a native
  path-glob mechanism (Codex, Hermes)... a Codex or Hermes wrapper has not been added yet."
- `rules/context-loader.mjs` line 2: "Shared path-based rule loader (Claude Code/Codex/Hermes)".
- `.gitignore` lines 93-94: `# Hermes` / `.hermes/plans/`.
- `plugins/development-harness/docs/beads-and-workflow-usage.md` line 76 and
  `plugins/development-harness/dh_core/operations.py` line 14 reference `.hermes/plans/...` files.

Evidence, product side, tying `.hermes/plans/` to this product:

- `website/docs/user-guide/features/skills.md`, heading "Using Skills": "`/plan [request]` tells Hermes to
  inspect context if needed, write a markdown implementation plan instead of executing the task, and save
  the result under `.hermes/plans/` relative to the active workspace/backend working directory." This is
  the exact directory the repo ignores and links to.
- `hermes_cli/plugins.py` module docstring: project plugins live in `./.hermes/plugins/<name>/`;
  `agent/skill_utils.py` `PROJECT_SKILLS_SUBDIRS` = `.hermes/skills`, `.agents/skills`. The product's
  per-project directory is `.hermes/`.
- WebSearch "Hermes Agent Nous Research github NousResearch/hermes-agent" (2026-09-06) returned the
  GitHub repo, the Nous org page, releases, and the docs site as the top results; the README (fetched
  from `raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md`) states the docs URL
  `https://hermes-agent.nousresearch.com/docs/`.
- The repo's other research entries (`research/skill-generation-tools/claude-code-skills-alirezarezvani.md`
  line 94, `research/api-frameworks/omniroute.md` line 88) list "Hermes Agent" alongside Claude Code, Codex,
  OpenCode as a coding-agent harness, consistent with the `rules/AGENTS.md` grouping.

No other product named "Hermes" with a `.hermes/` directory, `.hermes/plans/`, or `.hermes/skills`
convention surfaced in the search; the identification rests on the `.hermes/plans/` match above.

## 1. Shell command, read file, write file

**Answer**: Yes to all three. Tool names: `terminal` (shell), `read_file`, `write_file`; plus `patch`
(targeted edit) and `search_files`.

- `tools/terminal_tool.py` line 1213 `"name": "terminal"` and line 1312-1314 `registry.register(name="terminal", toolset="terminal", ...)`.
- `tools/file_tools.py` lines 1201-1226: `registry.register(name="read_file", toolset="file", ...)`,
  `registry.register(name="write_file", toolset="file", ...)`, `patch`, `search_files`.
- `toolsets.py` lines 13-14, 97, 120: toolset `terminal` = `["terminal", "process_manage"]`; toolset
  `file` = `["read_file", "write_file", "patch", "search_files"]`.
- Docs: `website/docs/reference/tools-reference.md` (title "Built-in Tools Reference"), rows `terminal`
  ("Execute shell commands on a Linux environment. Filesystem persists between calls..."), `read_file`,
  `write_file` ("Write content to a file, completely replacing existing content..."), `patch`.
- Tool argument names used by hooks below: `terminal` takes `command`; `write_file`/`patch` take `path`
  (per the worked shell-hook examples in `website/docs/user-guide/features/hooks.md`, "Worked examples"
  1 and 2: `.tool_input.path`, `.tool_input.command`).

## 2. Hooks

**Answer**: Yes — four hook systems. The two that fire around tool calls in CLI and gateway are
(a) Python plugin hooks (`ctx.register_hook(event, callback)` inside a `plugin.yaml` plugin) and
(b) shell hooks (`hooks:` block in `~/.hermes/config.yaml`, any executable, JSON on stdin/stdout). Both
dispatch through the same `invoke_hook()` and the same event names (`VALID_HOOKS`). The other two are
gateway-only `HOOK.yaml`+`handler.py` hooks and outbound webhooks.

Source: `website/docs/user-guide/features/hooks.md`, heading "Event Hooks", the four-row table; and
"Comparison at a glance" table under "Shell Hooks" (Declared in / Language / Runs in / Events).

### Event names

`hermes_cli/plugins.py` `VALID_HOOKS` (lines 107-150 at HEAD): `pre_tool_call`, `post_tool_call`,
`transform_terminal_output`, `transform_tool_result`, `transform_llm_output`, `pre_llm_call`,
`post_llm_call`, `on_stream_start`, `on_stream_delta`, `on_stream_end`, `on_interim_message`,
`pre_verify`, `pre_api_request`, `post_api_request`, `api_request_error`,
`transform_api_error_classification`, `on_session_start`, `on_session_end`, `on_session_finalize`,
`on_session_reset`, `on_skill_lifecycle`, `subagent_start`, `subagent_stop`, `pre_gateway_dispatch`,
`pre_approval_request`, `post_approval_response`, `pre_transcription`, kanban events, and more (read the
set directly; it is longer than this list).

Mapping to the asked-for events:

| Asked | Hermes event | Notes |
|---|---|---|
| before tool call | `pre_tool_call` | can block / modify |
| after tool call | `post_tool_call` | observer, return ignored |
| stop | no event literally named "stop". Closest: `pre_verify` (fires when the agent is about to accept a final answer after editing code; accepts Claude-Code `Stop` dialect `{"decision":"block","reason":...}` to keep going — `agent/shell_hooks.py` `_parse_pre_verify`, docs "pre_verify" row) and `on_session_end` (fires at every turn finalization — docs row: "Canonically at each turn finalization"). | |
| session start | `on_session_start` (first turn of a new session only — `agent/conversation_loop.py` comment "fired once for a brand-new session, not on continuation") | |

### `post_tool_call` payload

Emitted by `model_tools.py` `_emit_post_tool_call_hook()` (line ~617):

```python
invoke_hook(
    "post_tool_call",
    tool_name=function_name,
    args=function_args,
    result=result,
    **_CallIds(task_id, session_id, tool_call_id, turn_id, api_request_id).hook_kwargs(),
    duration_ms=duration_ms,
    status=status,
    error_type=error_type,
    error_message=error_message,
    middleware_trace=list(middleware_trace or []),
)
```

Python-plugin keyword fields (docs table row `post_tool_call`, `hooks.md` line 442): `tool_name`, `args`,
`result`, `task_id`, `session_id`, `tool_call_id`, `turn_id`, `api_request_id`, `duration_ms`, `status`,
`error_type`, `error_message`, `middleware_trace`. `_CallIds.hook_kwargs()` renders `None` ids as `""`.

Shell-hook stdin JSON is built by `agent/shell_hooks.py` `_payload_fields()` + `_serialize_payload()`:

```json
{"hook_event_name": "post_tool_call",
 "tool_name": "<tool>",
 "tool_input": {<the args dict>},
 "session_id": "<session_id or parent_session_id or ''>",
 "cwd": "<str(Path.cwd()) of the Hermes process>",
 "extra": {"result": ..., "task_id": ..., "tool_call_id": ..., "turn_id": ..., "api_request_id": ...,
           "duration_ms": ..., "status": ..., "error_type": ..., "error_message": ..., "middleware_trace": [...]}}
```

`_TOP_LEVEL_PAYLOAD_KEYS = {"tool_name", "args", "session_id", "parent_session_id"}`; everything else
lands under `extra`. Docs confirm the shape (`hooks.md` "JSON wire protocol": "The `extra` dict carries
all event-specific kwargs").

Per asked field:

- **working directory**: `cwd` — `Path.cwd()` of the Hermes process (`_payload_fields`), not the
  terminal session's tracked cwd. The tracked per-task terminal cwd (`tools/terminal_tool.py`
  `get_session_cwd(task_id)`) is not in the payload. Looked in `_payload_fields`, `_emit_post_tool_call_hook`,
  and the docs `post_tool_call` row for a session-cwd field; did not find it.
- **tool name**: `tool_name` (top level).
- **tool input**: `tool_input` (top level, the full args dict). For `terminal` the command string is
  `tool_input.command`; for `write_file`/`patch` the path is `tool_input.path` (docs "Worked examples").
- **session id**: `session_id` (top level).
- **sub-agent identifier**: no dedicated key. `extra.task_id` is the per-agent task id; inside a
  delegated child it is the child's task id, which `tools/delegate_tool_child_run.py` line 594 sets to
  `self.subagent_id or f"subagent-{self.task_index}-{uuid}"` (the child agent is run with
  `task_id=self.child_task_id`, line 660). `session_id` is also the child's own id (see Q3).

### Stop-adjacent event payloads

- `on_session_end` — `agent/turn_finalizer.py` line ~620: `session_id`, `task_id`, `turn_id`,
  `completed`, `failed`, `interrupted`, `turn_exit_reason`, `model`, `platform`. Interrupted exit paths
  (`cli.py` `_invoke_interrupted_session_end`, `tui_gateway/session_lifecycle.py`) send a reduced shape
  plus `reason`. No cwd, no tool name, no sub-agent id (shell payload: `tool_name`/`tool_input` are
  `null` for non-tool events — docs "JSON wire protocol").
- `pre_verify` — `hermes_cli/plugins.py` `get_pre_verify_continue_message()`: `session_id`, `platform`,
  `model`, `coding`, `attempt`, `final_response`, `changed_paths`.
- `on_session_finalize` — surface-dependent `session_id`, `platform`, optionally `reason`,
  `old_session_id`, `new_session_id` (docs row line 460).

### `pre_tool_call` payload

Docs row (`hooks.md` line 441): `tool_name`, `args`, `task_id`, `session_id`, `tool_call_id`, `turn_id`,
`api_request_id`, `middleware_trace`. Shell response `{"action"|"decision": "block"|"modify", ...}` or
exit code 2 blocks (`agent/shell_hooks.py` `BLOCK_EXIT_CODE = 2`, `_parse_pre_tool_call`).

### Hook implementation language

- Shell hooks: any executable; `command` string split with `split_command_line`, run with `shell=False`,
  JSON piped to stdin, timeout default 60 s, max 300 (`agent/shell_hooks.py` `ShellHookSpec`, `_spawn`).
  First-use consent per `(event, command)` persisted to `~/.hermes/shell-hooks-allowlist.json`; non-TTY
  runs need `--accept-hooks`, `HERMES_ACCEPT_HOOKS=1`, or `hooks_auto_accept: true` (docs "Consent model").
- Plugin hooks: Python callables registered in `register(ctx)` (`hermes_cli/plugins.py` module docstring).
- Gateway hooks: Python `handler.py` + `HOOK.yaml` under `~/.hermes/hooks/<name>/` (`gateway/hooks.py`).

### Can a plugin or skill collection ship hooks?

- A **Python plugin** (`plugin.yaml` + `__init__.py` `register(ctx)`) ships hooks via
  `ctx.register_hook(...)` — `website/docs/developer-guide/plugins/index.md` (title: "Step-by-step guide
  to building a complete Hermes plugin with tools, hooks, data files, and skills"); same plugin can bundle
  skills (heading "Bundle skills").
- **Shell hooks are config-owned**: `_parse_hooks_block` reads only `config.yaml`'s `hooks:` mapping;
  `re_register_config_hooks()` docstring: "they are config-owned, not plugin-owned, so the ledger cannot
  restore them". Looked in `hermes_cli/plugins_manifest.py` `PluginManifest` fields and
  `_KNOWN_MANIFEST_KEYS` (line 32-33 lists a `hooks` key) and in `hermes_cli/agent_plugins.py`
  (portable `plugin.json`), did not find a path by which a plugin package declares shell-hook commands;
  the manifest's `provides_hooks` is an advisory list of names ("This tells Hermes: 'I'm a plugin called
  calculator, I provide tools and hooks.'" — plugins/index.md).
- **Portable "Agent Plugins v1" packages** (`plugin.json`): `hermes_cli/agent_plugins.py` reads
  `plugin.json`, `skills/*/SKILL.md`, and root `mcp.json` only; docs (plugins/index.md, "portable")
  say "An enabled package may provide immediate `skills/*/SKILL.md` directories and stdio MCP servers
  from root `mcp.json`." Looked in that module for hook handling; did not find it.
- **Skills** ship no hooks: skill directories hold `SKILL.md` + `references/ templates/ scripts/
  assets/ examples/` (`skills.md` "Skill Directory Structure"). Looked in `tools/skills_tool.py` and
  `agent/skill_utils.py` for hook registration from a skill; did not find it.

## 3. Sub-agents

**Answer**: Yes — the `delegate_task` tool (toolset `delegation`). Hooks fire inside the child. The
child's hook payloads carry its own `session_id` and `task_id` (= subagent id), distinct from the parent's,
and `subagent_start`/`subagent_stop` carry explicit parent/child ids. A model-facing per-task working
directory is not accepted; opt-in `delegation.worktree_isolation: true` gives each child its own git
worktree.

- Mechanism: `tools/delegate_tool.py` line 511 `"name": "delegate_task"`, registered at line 598;
  `toolsets.py` line 142 `"delegation": ... ["delegate_task"]`. Docs:
  `website/docs/user-guide/features/delegation.md` ("The `delegate_task` tool spawns child AIAgent
  instances with isolated context, inherited tool access, and their own terminal sessions"). Schema
  parameters: `tasks[]{goal, context, output_schema}`, `action` (`spawn|list|steer|stop`), `subagent_id`,
  `message`. Also a plugin-facing `ctx.subagent_lifecycle.launch(SubagentLaunchRequest(...))` API
  (`website/docs/developer-guide/subagent-lifecycle-api.md`).
- Hooks inside the child: the child is an `AIAgent` run through the same tool executor
  (`tools/delegate_tool_child_run.py` line 660 `run_conversation(user_message=self.goal,
  task_id=self.child_task_id, ...)`), and `model_tools.py` `_emit_post_tool_call_hook` has no
  child-specific gate — its only suppression is the `_post_tool_call_hook_suppressed` ContextVar, whose
  sole setter is `agent/tool_executor.py` line 1514 (`suppress_post_tool_call_hook()` "Let an outer
  executor own the terminal post-tool event", i.e. the executor emits it once). Looked in
  `tools/delegate_tool*.py` for a hook-suppression for children; did not find one. The docs' shell-hook
  intro lists "write a log line when a subagent completes (`subagent_stop`)", and `pre_llm_call` carries
  `parent_session_id` (`agent/turn_context.py` `_collect_pre_llm_call_context`).
- Distinct identifiers: `tools/delegate_tool.py` line ~203 sets `child._subagent_id`,
  `child._parent_subagent_id`, and `child_session_ref["session_id"] = child.session_id`; the
  `subagent_start` hook (line ~227) sends `parent_session_id`, `parent_turn_id`, `parent_subagent_id`,
  `child_session_id`, `child_subagent_id`, `child_role`, `child_goal`; `subagent_stop`
  (`tools/delegate_tool_results.py` `_fire_subagent_stop_hooks`) sends `parent_session_id`,
  `parent_turn_id`, `child_session_id`, `child_role`, `child_summary`, `child_status`,
  `tool_call_history`, `duration_ms`. Docs table rows `subagent_start`/`subagent_stop` (`hooks.md`
  lines 463-464). Subagent ids look like `sa-0-1a2b3c4d` (delegation.md "Steering a Running Subagent").
- Working directory / worktree: `delegate_task` has no cwd parameter (schema above). Child cwd is seeded
  from the parent's tracked terminal cwd (`delegate_tool_child_run.py` line 601
  `record_session_cwd(self.child_task_id, get_session_cwd(self.parent_task_id))`). With
  `delegation.worktree_isolation: true` (`tools/delegate_tool_config.py` `_get_worktree_isolation`,
  default False) each child gets `<repo>/.worktrees/subagent-<id>` on branch
  `hermes-subagent/subagent-<id>` and its terminal cwd is set there (line 608); docs delegation.md
  heading "Worktree Isolation": "opt-in, git-only, and local-terminal-backend-only". The plugin
  lifecycle API "explicitly reject[s] ... working-directory overrides" (subagent-lifecycle-api.md, last
  paragraph). Separately, the kanban worker system gives each task its own workspace
  (`HERMES_KANBAN_WORKSPACE`, `agent/delegation_context.py` `KANBAN_ENV_KEYS`) — a different mechanism
  from `delegate_task`.

## 4. Plugins and skills

**Answer**: Yes, `SKILL.md` skills in the agentskills.io format. Directories: `~/.hermes/skills/`
(primary, categorised subdirs), `skills.create_dir`, `skills.external_dirs` (config), and project-local
`<git-root>/.hermes/skills/` and `<git-root>/.agents/skills/` (only after `hermes skills trust`).
Plugin manifests: native `plugin.yaml`, and portable Agent-Plugins-v1 `plugin.json`. Path variables
substituted in skill bodies: `${HERMES_SKILL_DIR}` and `${HERMES_SESSION_ID}`; `${CLAUDE_PLUGIN_ROOT}` is
not substituted (looked, did not find); `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` are expanded only in portable
`mcp.json` values, not in skill bodies.

- Format: `skills.md` intro: "compatible with the agentskills.io open standard"; frontmatter shown under
  "SKILL.md Format" (`name`, `description`, `version`, `platforms`, `metadata.hermes.*`).
- Directories: `skills.md` "All skills live in `~/.hermes/skills/`"; "External Skill Directories"
  (`skills.external_dirs` in `config.yaml`); "Project-Local Skills": `<project-root>/.hermes/skills/`
  and `<project-root>/.agents/skills/`, root = nearest `.git` ancestor, loaded only when the root is in
  `skills.trusted_project_dirs` (`hermes skills trust`); precedence `project → local → external_dirs`.
  Code: `agent/skill_utils.py` `PROJECT_SKILLS_SUBDIRS`, `get_project_skills_dirs`,
  `get_external_skills_dirs`, and the "Skill dirs: local `~/.hermes/skills/` first, then create_dir,
  then external" docstring (line 394). Looked in `agent/skill_utils.py` for `.claude/skills` or
  `.codex`; did not find it — Claude Code skills enter only via `hermes import-agent claude-code`, which
  copies `~/.claude/skills/<name>/` to `~/.hermes/skills/claude-code-imports/<name>/`
  (`website/docs/user-guide/import-from-other-agents.md` table).
- Plugin-bundled skills: a native plugin registers skills from its own `skills/` dir (plugins/index.md
  "Bundle skills"; served by `tools/skills_tool_plugin.py`, names `plugin:skill`); portable packages
  expose `skills/*/SKILL.md` under namespace `agent-plugin-<slug>-<hash>` (plugins/index.md, portable
  section). Both are read-only and not listed in the system-prompt index.
- Plugin manifest: native — `plugin.yaml` with `name`, `version`, `description`, `author`,
  `requires_env`, `provides_tools`, `provides_hooks`, `kind`, `manifest_version`, `api_version`,
  `requires_plugins`, `python_dependencies`, `config_schema`, ... (`hermes_cli/plugins_manifest.py`
  `class PluginManifest`; docs plugins/index.md manifest table). Portable — root `plugin.json` with
  `$schema` `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` (`hermes_cli/agent_plugins.py`
  `PLUGIN_SCHEMA_V1`; discovered when a plugin dir contains `plugin.json` — `hermes_cli/plugins_discovery.py`
  line 116-123). Plugin discovery dirs: bundled `<repo>/plugins/<name>/`, `~/.hermes/plugins/<name>/`,
  `./.hermes/plugins/<name>/` (opt-in `HERMES_ENABLE_PROJECT_PLUGINS`), pip entry points
  `hermes_agent.plugins` (`hermes_cli/plugins.py` module docstring).
- Path variable substitution in skill bodies: `agent/skill_preprocessing.py` line 15
  `_SKILL_TEMPLATE_RE = re.compile(r"\$\{(HERMES_SKILL_DIR|HERMES_SESSION_ID)\}")`;
  `substitute_template_vars` replaces `${HERMES_SKILL_DIR}` with the absolute skill dir and
  `${HERMES_SESSION_ID}` with the session id (unresolvable tokens left in place); on by default,
  `skills.template_vars: false` disables. Docs: `website/docs/developer-guide/creating-skills.md` table
  "Token / Replaced with" (line 288-291). The loaded-skill message also appends
  `[Skill directory: <abs path>]` plus a note to resolve relative paths against it
  (`agent/skill_commands.py` `_SKILL_DIR_NOTE`). `grep -rn CLAUDE_PLUGIN_ROOT` over `*.py` and `*.md`
  in the repo (excluding tests) returned nothing. `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` expansion
  (`hermes_cli/agent_plugins.py` `_expand`, `_PLACEHOLDER_RE`) applies to `mcp.json` `args`, `env`,
  `cwd`; looked for its use on `SKILL.md` content in that module and in `tools/skills_tool_plugin.py`,
  did not find it.

## 5. MCP

**Answer**: Yes. `mcp_servers:` in `~/.hermes/config.yaml` (stdio `command`/`args`/`env`, or HTTP
`url`/`headers`, plus `enabled`, `timeout`, `tools.include/exclude`, `auth: oauth`, `trust`, ...).

- `website/docs/user-guide/features/mcp.md` "Quick start" step 2 (`mcp_servers: filesystem: command:
  "npx" args: [...]`); tip box: "The `mcpServers` block in your `~/.claude.json` maps to `mcp_servers`
  in Hermes' `config.yaml` — and `hermes import-agent claude-code` migrates it".
- `website/docs/reference/mcp-config-reference.md` "Root config shape" and "Server keys" table; `${VAR}`
  and `${env:VAR}` references resolve in string values ("Environment variable references").
- Also: curated catalog `hermes mcp install <name>` from `optional-mcps/<name>/manifest.yaml`
  (mcp.md "Catalog"), and portable plugin root `mcp.json` (Q4). Code: `tools/mcp_tool_config.py`,
  `tools/mcp_tool.py`.

## 6. Environment for a shell command

**Answer**: The `terminal` tool's local backend spawns `bash -c` with `cwd=self.cwd` (the tracked
per-task session cwd) and `env=_make_run_env(self.env)`; that env is the process environment with
Hermes-managed secrets stripped, PATH fixed, and these Hermes identifiers bridged in:

- `HERMES_SESSION_ID` — "Exported automatically into every tool subprocess Hermes spawns (`terminal`,
  `execute_code`, persistent shell, Docker/Singularity backends, delegated subagent runs). Set by the
  agent to the current session ID" (`website/docs/reference/environment-variables.md`, "Session
  Settings" table, line 889). Code: `tools/environments/local.py` `_inject_session_context_env` copies
  every bound `HERMES_SESSION_*` ContextVar into the child env; the var list is
  `gateway/session_context.py` `_SESSION_VARS`: `HERMES_SESSION_PLATFORM`, `HERMES_SESSION_SOURCE`,
  `HERMES_SESSION_CHAT_ID`, `HERMES_SESSION_CHAT_TYPE`, `HERMES_SESSION_CHAT_NAME`,
  `HERMES_SESSION_THREAD_ID`, `HERMES_SESSION_USER_ID`, `HERMES_SESSION_USER_ID_ALT`,
  `HERMES_SESSION_USER_NAME`, `HERMES_SESSION_SCOPE_ID`, `HERMES_SESSION_KEY`, `HERMES_SESSION_ID`,
  `HERMES_UI_SESSION_ID`, `HERMES_SESSION_MESSAGE_ID`, `HERMES_SESSION_PROFILE`,
  `HERMES_BROWSER_CONTROL_PRINCIPAL`, `HERMES_BROWSER_CONTROL_TRANSPORT_FAMILY`, `HERMES_CRON_SESSION`
  (only those bound for the current session are present; in a gateway session unbound ones are stripped).
- `AI_AGENT=hermes-agent` and `HERMES_AGENT=true` — set by the CLI/gateway entry points
  (`hermes_cli/main.py` line 3100-3101, `gateway/run.py` line 5340, `os.environ.setdefault`) and
  "exported into every terminal-tool shell — including remote backends" (environment-variables.md
  "Session Settings" rows `AI_AGENT`, `HERMES_AGENT`).
- `HERMES_HOME` — bridged when a profile override is active (`local.py` `_apply_profile_home`).
- Working directory: not exported as a variable; it is the subprocess `cwd` (`local.py` `_run_bash`,
  `cwd=self.cwd`; `_resolve_safe_cwd` falls back to an ancestor if the dir is gone). Docs: `terminal.cwd`
  in `config.yaml` for gateway/cron, launch directory for CLI (`website/docs/user-guide/git-worktrees.md`
  "Why Use Worktrees with Hermes?"). Looked in `local.py` `_finalize_child_env`, `_make_run_env`,
  `_scrubbed_env` for a `HERMES_CWD`/`HERMES_TASK_ID`/`HERMES_SUBAGENT_ID` export; did not find one.
- Delegated child marker: `HERMES_DELEGATED_CHILD_CONTEXT` (`agent/delegation_context.py`
  `DELEGATED_CHILD_ENV_MARKER`) is on the `execute_code` allow-list
  (`tools/code_execution_env.py` `_HERMES_CHILD_ALLOWED` = `HERMES_HOME`, `HERMES_PROFILE`,
  `HERMES_CONFIG`, `HERMES_ENV`, `HERMES_DELEGATED_CHILD_CONTEXT`); kanban workers additionally receive
  `HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_WORKSPACE`, `HERMES_KANBAN_BOARD`,
  `HERMES_KANBAN_DB`, ... (`KANBAN_ENV_KEYS`; environment-variables.md rows `HERMES_KANBAN_*`), which
  `_finalize_child_env` scrubs from `delegate_task` children.
- Passthrough of user secrets: skill-declared `required_environment_variables` and
  `terminal.env_passthrough` (`website/docs/user-guide/security.md` "Environment Variable Passthrough").
