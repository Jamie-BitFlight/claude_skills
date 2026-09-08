# Claims register — development-harness

Warrants for claims this plugin's runtime prose and design documents make about external
systems. Runtime files state the instruction; this file states how each claim was established,
from what source, on what date, and what re-check would run. A claim with no entry here is one
to re-establish before repeating.

Every entry: **claim** — source and date — confidence — re-check.

Confidence: **source** = the harness's own repository or documentation read verbatim; **repo** =
a repository other than the harness's own, such as a plugin template or sample plugin, read
verbatim; **snippet** = search-result excerpts of a page a proxy blocked; **reported** = a
third-party report, unconfirmed by the vendor.

## Harness capability matrix (read 2026-09-06)

One measurement file per harness, under `docs/work-ledger/measurements/`, holds the answer to
each column with its file, line or heading. This table summarises them; the files are the
warrant.

| harness | shell tool | after-tool hook carries the shell command text | hook carries a working directory | hooks fire inside a sub-agent | sub-agent worktree | `SKILL.md` | MCP | a plugin can ship the hook | confidence |
|---|---|---|---|---|---|---|---|---|---|
| Claude Code | `Bash` | yes, `tool_input.command` | yes, `cwd` | yes, with `agent_id` | yes, an isolation option on the agent | yes | yes | yes, `hooks/hooks.json` | source, docs pages `hooks`, `sub-agents`, `plugins-reference` |
| Codex | `exec_command` | yes, `tool_input.command`; a write is `apply_patch`, whose input is patch text and names no file path | yes, `cwd`, the turn's directory rather than the command's `workdir` | yes, `SubagentStart`/`SubagentStop`, with `agent_id` | none found; the child inherits the turn's directory, and `--worktree` is a root-session CLI flag | yes | yes | yes, manifest `hooks` or `hooks/hooks.json` | source, `openai/codex` `main` `ac192cd7` |
| OpenCode | `bash` | yes, `args.command` on `tool.execute.after` | no field on the event; the directory comes from plugin load context | yes, carrying the child's `sessionID` | none per task; the child inherits the directory | yes | yes | no: plugins are JavaScript loaded from plugin directories, not from skill paths | source, `anomalyco/opencode` `dev` `337fd144` |
| Cursor | `Shell` | yes, `afterShellExecution.command`, and `afterFileEdit.file_path` | on the shell events only; looked for a `cwd` on `afterFileEdit` and did not find one | reported | yes, `isolation: worktree` in agent frontmatter | yes | yes | yes, `hooks/hooks.json` | snippet and repo, `cursor/plugins` and `cursor/plugin-template`; hooks-inside-a-sub-agent is reported |
| Hermes | `terminal` | yes, `args` and `tool_input` on `post_tool_call` | yes, `cwd`, the Hermes process's directory | yes, carrying the child's `session_id`; `task_id` sits under `extra` | yes, `delegation.worktree_isolation` in `config.yaml`, default off, git and local terminal only | yes | yes | no: a plugin ships Python hooks, and shell hooks come from config | source, `NousResearch/hermes-agent` `main` `7166071f` |
| pi | `bash` | yes, `input.command` on `tool_result` | no field on the event; the directory comes from the extension context | no: the sub-agent example runs a child process, and the parent's in-process handlers never see the child's tool calls | none found; the example takes a directory | yes | no native MCP, extension only | no: a TypeScript extension shipped in a pi package | source, `earendil-works/pi` HEAD `9767ba27` |
| Kilo Code | `bash` | yes, `args.command` on `tool.execute.after` | no field on the event; `PluginInput.directory`/`worktree` supply it | yes, carrying the child's `sessionID`, which is the only distinguishing key | none on the `task` tool; the VS Code `agent_manager` tool has a `worktree` mode | yes | yes | not from a skill collection: a hook is a TypeScript plugin from npm, the config `plugin` array, or `.kilo/plugin/*.ts` | source, `Kilo-Org/kilocode` HEAD `78d8d2a3`, v7.5.15 |
| Kimi | `Bash` | yes, `tool_input.command` | yes, `cwd`, the bootstrap directory | yes; the sub-agent's tool and stop payloads carry no agent field, and the parent's `SubagentStart`/`SubagentStop` carry `agent_name`, a profile name rather than an instance id | none found | yes | yes | yes, manifest `hooks` in `kimi.plugin.json` or `[[hooks]]` in `config.toml` | source, `MoonshotAI/kimi-code` `main` `af81bb9`, v0.41.0 |

Re-check, per harness: run the questions in that file's headings against the harness's default
branch and update the commit or version in this row.

**Kilo CLI is a fork of OpenCode** (`README.md` line 171, read 2026-09-06), so its runtime package
is literally `packages/opencode/` and its row tracks OpenCode's rather than any Cline-family
harness's. The Roo-Code-derived VS Code extension is the separate `kilocode-legacy` repository,
end-of-life 2026-07-31.

Consequences the design draws, each a claim in its own right:

- **A runner needs only a shell tool.** Every row has one. Confidence: source on every row but
  Cursor, whose tool name is by snippet. Re-check: the shell column.
- **The shell command text reaches an after-tool hook on every harness.** So a hook can renew a
  lease by reading `--address` and `--attempt` out of a sam command it sees, with no identifier
  of its own. Confidence: source on every row but Cursor, by snippet. Re-check: the command-text
  column. On Kilo, `tool.execute.after` does not fire when a tool call raises, so a hook there
  pairs it with `tool.execute.before`; a non-zero exit, a timeout and an abort all still reach
  it.
- **The design reads no per-sub-agent variable from the shell environment.** Codex exports
  `CODEX_THREAD_ID`, Hermes `HERMES_SESSION_ID` and, for kanban workers only,
  `HERMES_KANBAN_TASK`; pi exports `PI_SESSION_ID`. None names a ledger task, and the design
  uses none of them. Confidence: source for Codex, Hermes, pi, OpenCode and Kimi; snippet and
  reported for Cursor. For Claude Code: looked in the three cached documentation pages, found no
  statement either way, so this is unmeasured there and M1 of the plan measures it.
  Re-check: section 6 of each measurement file.
- **The hook this repository ships reaches four harnesses:** Claude Code, Codex, Cursor and
  Kimi, each of which loads hooks from a plugin manifest this marketplace already publishes. On
  Hermes a shell hook comes from user config; on OpenCode and Kilo Code it is a JavaScript or
  TypeScript plugin loaded from plugin directories rather than skill paths; on pi it is a
  TypeScript extension. Those four need a separate install, not a different design.
  Confidence: source, except Cursor by repo. Re-check: the last column.
- **On pi a hook cannot observe a sub-agent at all**, because the sub-agent is a child process
  and the parent's handlers do not see its tool calls. Confidence: source. Re-check:
  `harness-pi.md` section 3.
- **Per-tool-call liveness without an identifier needs a per-runner worktree**, because a write
  event carries a path and nothing else that maps to a task. Claude Code, Cursor and Hermes give
  a sub-agent its own worktree; on Codex, OpenCode, Kimi and pi the launcher creates the
  worktree and starts a child process in it. Confidence: source, Cursor by snippet. Re-check:
  the worktree column. Cursor's write event carries no working directory, so there the path hook
  reads `file_path` alone.
- **MCP is not in the shared layer**, since pi has no native MCP. The CLI over a shell is.
  Every other harness measured, Kilo Code included, registers MCP servers from project config.
  Confidence: source. Re-check: `earendil-works/pi` README.
- **`${CLAUDE_PLUGIN_ROOT}` is substituted in a skill body by Claude Code only.** Codex, Kimi
  and Hermes substitute their own variables in a skill body, and Codex additionally substitutes
  `${CLAUDE_PLUGIN_ROOT}` in a plugin's hook commands; pi removed `{baseDir}` in 0.24.0;
  OpenCode returns the body verbatim; for Cursor, looked in the documentation snippets, both
  Cursor repositories and the plugin template's validator, and did not find it. Confidence:
  source, Cursor by snippet. Re-check: section 4 of each file.
  `plugins/plugin-creator/CLAIMS-REGISTER.md` holds this claim for the skill-portability rule.

## Lease

- **`lease.ttl_seconds` defaults to 1800 and must exceed the longest gap between a runner's sam
  commands.** Unmeasured: the gap is what M0 of the plan reads out of past `implement-feature`
  transcripts, and the default is a guess until then. Confidence: none. Re-check: M0's
  measurement file, then the longest observed gap in a `scripted_runner.py` CI run.

## `dh_paths.py` claims

- The module docstring says Cursor uses `${CLAUDE_PLUGIN_ROOT}` in plugin script paths and sets
  `CURSOR_PROJECT_ROOT`. On `${CLAUDE_PLUGIN_ROOT}` as a script-path substitution: looked in the
  documentation snippets and both Cursor repositories, did not find it; as an environment
  variable of a plugin hook process it is reported in a forum thread, unconfirmed. On
  `CURSOR_PROJECT_ROOT`: looked in the same sources, did not find it; `CURSOR_AGENT` and `CI=1`
  are the documented variables. Confidence: reported. Re-check: run `env` inside a Cursor agent
  shell, and grep both Cursor repositories for `CURSOR_PROJECT_ROOT`.

## SQLite

- **WAL mode needs shared memory, so a database on a network filesystem must not open in WAL.**
  Source: `sqlite/sqlite` `src/wal.c` header comment, read 2026-09-06. Confidence: source.
  Re-check: the same file at `master`. The mount types in
  `dh_core/ledger_spec.py:NETWORK_FILESYSTEMS` are this plugin's choice, not SQLite's.

## n8n as a reference for the graph model (read 2026-09-07)

n8n was offered as an analogy for configurable node templates with conditional data flow; these
entries separate what it establishes from what it does not.

- **A node in a saved workflow is an instance referencing a registered type, not a copy of it.**
  `INode` carries `type: string` (e.g. `n8n-nodes-base.httpRequest`), `typeVersion` and its own
  `parameters`; a workflow is `{ nodes: INode[], connections: IConnections, settings, ... }`. The
  type's behaviour and property schema live in a separately registered `INodeTypeDescription`.
  Source: `n8n-io/n8n` `packages/workflow/src/interfaces.ts` at `master`, read 2026-09-07.
  Confidence: source. Re-check: the same interface at `master`.

- **Connections carry no payload type, so nothing checks that a producer satisfies a consumer.**
  `NodeConnectionType` (`main`, `ai_tool`, `ai_languageModel`, …) distinguishes wiring-slot kind,
  not data shape, and neither `INodeInputConfiguration` nor `INodeOutputConfiguration` carries a
  schema field — only `required` and `maxConnections`, which are cardinality. Looked in those
  interfaces and in `packages/cli/src/workflows/workflow-validation.service.ts`, found cardinality
  and channel-kind only. Source: the same files, read 2026-09-07. Confidence: source for those
  files; not established repository-wide, since the search covered the structures that would carry
  such a check rather than every file. Re-check: grep the repository for a schema or data-type
  field on either configuration interface.

- **Branch conditions are evaluated inside a node, not on the connection.** `IfV2.node.ts` declares
  two `main` outputs named `true`/`false` and, per item, reads `conditions` from node parameters in
  `execute()` and pushes to an output array index. `SwitchV3.node.ts` computes its output count from
  a parameter expression and routes in `execute()` likewise. Source: `packages/nodes-base/nodes/If/
  V2/IfV2.node.ts` and `packages/nodes-base/nodes/Switch/V3/SwitchV3.node.ts`, read 2026-09-07.
  Confidence: source. Re-check: the same files.

- **No pre-execution check of graph well-formedness exists at activation or execution start.**
  `validateForActivation` checks trigger presence, node-type registration, credential presence and
  required-parameter validity. Looked there and in `packages/core/src/execution-engine/
  workflow-execute.ts` for cycle detection, reachability, or connection compatibility, and found
  none; the only cycle-adjacent mechanism is a runtime guard that throws once the same
  `nodeName:runIndex` repeats. Cycles are a supported pattern, not an error — the Loop Over Items
  node exists to create one. Source: those two files, read 2026-09-07. Confidence: source for those
  files; partially established repository-wide. Re-check: the same files, plus
  `packages/core/src/execution-engine/partial-execution-utils/`, whose `DirectedGraph` is reported
  to serve partial re-execution rather than topology rejection and was not read directly.

- **A node can invoke an entire other workflow, and no depth limit was found.** The Execute
  Sub-workflow node (`packages/nodes-base/nodes/ExecuteWorkflow/ExecuteWorkflow.node.ts`) passes
  items into a saved workflow and receives its output back. Looked in
  `packages/cli/src/workflow-execute-additional-data.ts`, which owns sub-workflow invocation, and
  found no maximum-depth constant or self-call guard. Source: those files, read 2026-09-07.
  Confidence: source for the mechanism; the absence of a limit is partially established, from one
  file rather than the repository, and a community forum thread reporting a practical bound of
  server memory is **reported**, not vendor-confirmed. Re-check: grep the repository for a
  recursion-depth constant on the sub-workflow path.

- **Error routing is a per-node flag that changes effective topology at runtime.** `OnError` is
  `'continueErrorOutput' | 'continueRegularOutput' | 'stopWorkflow'`, set on `INode`; when a node
  selects the error output, `handleNodeErrorOutput` moves failed items into the last output slot.
  `INodeOutputConfiguration.category: 'error'` marks a declared output as the error one. Source:
  `packages/workflow/src/interfaces.ts` and `packages/core/src/execution-engine/workflow-execute.ts`,
  read 2026-09-07. Confidence: source. The workflow-level Error Trigger and error-workflow setting
  rest on search-result excerpts because the proxy blocked `docs.n8n.io`: **snippet**. Re-check:
  fetch the error-handling documentation page directly.

- **Per-node input and output data is retained per run, keyed by node name.** `IRunExecutionData`
  and `ITaskData` are imported by `packages/workflow/src/interfaces.ts` from
  `packages/workflow/src/run-execution-data/run-execution-data.ts`; that file was not opened, so the
  field list rests on converging secondary descriptions of `resultData.runData[nodeName][runIndex]`
  and on the `$node["Name"].json` expression form reading the same structure. Read 2026-09-07.
  Confidence: **reported** at the level of the field list; the import itself is source. Re-check:
  read `run-execution-data.ts` directly.
