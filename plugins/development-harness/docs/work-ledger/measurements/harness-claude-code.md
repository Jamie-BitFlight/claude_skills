# Harness facts: Claude Code

Sources, all read 2026-09-06 as cached copies of `code.claude.com/docs/en/`:
`hooks` (cited as **hooks:N**), `sub-agents` (**sub-agents:N**), `plugins-reference`
(**plugins:N**), where N is the line of the cached markdown.

## 1. Shell command, read file, write file

The `Bash` tool runs a shell command, with `PowerShell` as the Windows alternative; hooks match
on tool names and the page's examples match `Bash`, `Write` and `Edit` (hooks:89, hooks:271).
Reads and writes are the `Read`, `Write` and `Edit` tools. Looked in the cached hooks and
sub-agents pages for a single authoritative tool-list table and did not find one; the tool names
appear in matcher examples rather than in a roster.

## 2. Hooks

Events named on the page include `PreToolUse`, `PostToolUse`, `SessionStart`, `SubagentStart`,
`SubagentStop`, `Stop`, `StopFailure`, `PreModelSwitch`, `PostModelSwitch` and `PreCompact`
(hooks:1109, 2295, 2329, 2474, 2570).

**Common input fields**, on every event (hooks:725-737): `session_id`, `prompt_id`,
`transcript_path`, `cwd` ("current working directory when the hook is invoked"),
`permission_mode`, `effort`, `hook_event_name`.

**Inside a subagent, two more** (hooks:739-741): `agent_id`, "unique identifier for the
subagent, present only when the hook fires inside a subagent call", and `agent_type`, the agent
name.

**PostToolUse** adds the tool name, the tool input and the tool response; the input for a `Bash`
call carries the command string, and for `Write` or `Edit` the file path. Looked for a field
table dedicated to PostToolUse in the cached page and found the event described through examples
rather than a table, so the field names here are read from those examples and should be
confirmed against a live payload (that is M1 of the plan).

**SubagentStop** adds `stop_hook_active`, `agent_id`, `agent_type`, `agent_transcript_path` and
`last_assistant_message`, the last holding "the text content of the subagent's final response,
so hooks can access it without parsing the transcript file" (hooks:2329-2344).

**Stop** adds `stop_hook_active`, `last_assistant_message`, `background_tasks` and
`session_crons` (hooks:2474).

**Where hooks live.** Settings files, managed policy settings, and plugins all supply hooks, and
all of them run inside subagents (hooks:267). A plugin ships them as `hooks/hooks.json` or
through its manifest (plugins:90). A command hook takes `command` plus optional `args`, `async`,
`asyncRewake` and `shell` (hooks:452-460); `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PROJECT_DIR}`
are substituted into `command` and into each `args` element (hooks:468).

## 3. Sub-agents

The `Agent` tool spawns one; its parameter table lists `prompt`, `description`, `subagent_type`
and `model` (hooks:1690-1695). Hooks fire inside it: "When a subagent calls a tool, tool events
such as `PreToolUse` and `PostToolUse` fire the same configured hooks as in the main
conversation, and the input carries the `agent_id` and `agent_type`" (hooks:267).

**Worktree isolation is an agent-level setting, not a parameter of the Agent tool's own table.**
`isolation: worktree` is a supported frontmatter field: "run the subagent in a temporary git
worktree, giving it an isolated copy of the repository branched by default from your default
branch rather than the parent session's HEAD. The worktree is automatically cleaned up if the
subagent makes no changes" (sub-agents:305). It is also accepted in the `--agents` JSON
(sub-agents:225) and can be passed "on the call itself" (sub-agents:900). Without it, "a
subagent starts in the main conversation's current working directory" (sub-agents:269), and with
it "a subagent with `isolation: worktree` runs its Bash and PowerShell commands inside its
worktree" (sub-agents:271).

## 4. Plugins and skills

Plugins carry skills, agents, commands, hooks and MCP servers. `${CLAUDE_PLUGIN_ROOT}` is
substituted in "skill and agent content | anywhere the placeholder appears" (plugins:701) and in
hook commands (hooks:468).

## 5. MCP

A plugin registers MCP servers through its manifest, and a project through its own settings
(plugins, MCP section).

## 6. Environment variables for a shell command

`$CLAUDE_EFFORT` is set for hook commands and for the Bash tool (hooks:733). `${CLAUDE_PROJECT_DIR}`
and `${CLAUDE_PLUGIN_ROOT}` are placeholders substituted into hook command strings rather than
variables exported to an arbitrary Bash tool call (hooks:89, 468). The page states there is no
`$CLAUDE_MODEL` variable (hooks:745).

**No per-subagent variable was found.** Looked in the cached hooks page for an exported variable
naming the subagent or the session, and found `agent_id` only as a hook input field, never as an
environment variable. This is the one column of the register's matrix that is unmeasured for
this harness; M1 of the plan measures it by printing the environment inside a runner.
