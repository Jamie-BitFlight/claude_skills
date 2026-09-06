# DH work ledger — plan

**Tracking:** backlog item #3449. **Date:** 2026-09-06. Paths are relative to
`plugins/development-harness/` unless they start with `rules/` or `.claude/`.

The design is the artefacts below. This file plans their landing and holds no design of its own.

| artefact | what it is | state |
|---|---|---|
| `dh_core/ledger_spec.py` | the ledger's state machine as data: tables and column provenance, event kinds, commands and flags, reason codes, transitions | in the repository |
| `tests_sam/test_ledger_spec.py` | closure tests: every column set, every event emitted, every reason printed, every status handled | in the repository, green |
| `docs/work-ledger/work-loop.md` | the orchestrator's judge table and the launcher shapes | in this pull request |
| `docs/work-ledger/runner-contract.md` | the runner's sequence | in this pull request |
| `CLAIMS-REGISTER.md` | the harness matrix with its sources, dates and confidence | in this pull request |
| `docs/work-ledger/measurements/` | one file per harness, and one per Slice 0 measurement | the seven harness files are drafted at `.tmp/scratch/dh-task-tracking/harness-*.md` and land here in this pull request; the rest are Slice 0's |

The runner key is the task's attempt number, so a runner is any process on any harness that was
told an address and an attempt. `test_ledger_spec.py` asserts no session or agent identifier
appears in the spec; for the two prose files, a grep for `session_id`, `agent_id` and
`CLAUDE_CODE_SESSION_ID` returned nothing on 2026-09-06.

## Layers

A behaviour lives at one layer, and each layer is known one way: **harness** by measurement;
**code** by a test; **surface**, the `sam plan` commands and their reason codes, by `--help` and
a non-zero exit; **prose**, `skills/` and `agents/`, by reading a transcript; **loop** by a rate
across runs. Two rules follow. One rule has one enforcement point, at the lowest layer that can
see the violation. A rate is a finding about the system, so a prose rule followed some of the
time moves one layer down instead of being restated. The spec enforces at the surface every rule
the surface can see; `work-loop.md` and `runner-contract.md` carry the rest, and M6 measures
whether prose can hold them.

## Slice 0 — measure

Keep a measurement when a named step branches on it, or a Done-when compares against it.

1. **M0, interventions today.** On each machine listed in #3449, from the transcripts of the
   last five `implement-feature` runs: the count of user messages sent after the plan was
   finalised and before its last task reached `complete`, with the task state that prompted
   each; and the longest gap between consecutive `sam plan` commands inside one runner, which is
   the floor for `lease.ttl_seconds`. Read by Slice 4's Done-when, which compares against the
   message count, and by the `Lease` entry of `CLAIMS-REGISTER.md`.
2. **M1, live hook payload and the kill.** On Claude Code, Codex, Cursor and Kimi, the four
   harnesses whose plugins can ship a hook: register a throwaway after-tool hook and stop hook
   that append their stdin to a file, launch one runner through the harness's sub-agent call,
   and run one sam command and one file write inside it. Record each payload verbatim, and the
   command that kills a runner mid-task on that harness. Read by Slice 4 step 3, which ships the
   renewing hook where the after-tool payload carries the shell command text, adds the path hook
   where the sub-agent has its own worktree and the write payload carries a path, and ships
   neither otherwise; and by Slice 4's Done-when, which kills a runner.
3. **M2, consumers of the surfaces being removed.** Grep the plugin for each term in "What
   retires" and record every file and the role of each use. Read by every delete step.
4. **M3, store census.** On each machine listed in #3449: every plan and dispatch-plan content
   record the configured backend lists; the files under `~/.dh/projects/*/plan/`, `context/` and
   `kage-bunshin/`; any `dispatch-state.db`; and the `github-cache` queue, each with count,
   shape, hostname and date. Copy the records and the `plan/` files, with issue bodies redacted,
   into `tests_sam/fixtures/census/records/`. Read by Slice 2's import test, which round-trips
   one fixture per record shape and says so when a shape has none.
5. **M4, live-run CI.** Whether a Claude Code session can run inside a `main`-only CI job here,
   and with which credentials. Read by the Done-whens of Slices 4 and 5: yes makes the live runs
   CI jobs, no makes them local runs with transcripts attached to the pull request.
6. **M5, worktree in a sub-agent.** On Claude Code and Cursor, launch a sub-agent with the
   isolation option; on Hermes, set `delegation.worktree_isolation` in `config.yaml` and call
   `delegate_task`. From inside each, record `pwd` and `git rev-parse --git-common-dir`. Read by
   Slice 5's launcher clause: a common directory equal to the parent's means the sub-agent opens
   the same ledger and the harness option is the launcher, and anything else means the launcher
   creates the worktree and starts a child process in it.
7. **M6, prose compliance today.** Across the M0 transcripts, the share of runner turns that
   returned a `STATUS:` line, that appended a section to the task record, and that ran the
   `claim` step. Read by ADR 6: a rule whose analogue holds under half the time is named there
   as one prose cannot carry, and the spec gains a surface check for it before Slice 2's
   implementation begins.

Done when every measurement has a file under `docs/work-ledger/measurements/` holding the
command run or the source read, its full output or the passage quoted, the date and the machine,
and #3449 links each file.

## Slice 1 — decide

One ADR per decision under `docs/adrs/`, named `ADR-3449-{n}-{slug}.md`, each linking the
Slice 0 files it reads and carrying "The system today" copied into its Context section:

1. **Identity.** The address is the identity; the attempt number is the runner key. Adds a
   `Superseded by` line to ADR-1770-1 in the form ADR-3082-1 added to ADR-3075-4, on two points:
   the reason "SAM plans are authored sequentially", and the single-writer decision for
   `append_task` and `finalize_plan`.
2. **The ledger.** One SQLite database per repository, keyed by the git common directory,
   append-only events, materialised tables, WAL on a local filesystem, rebuildable by folding
   the events. Distinguishes itself from ADR-3082-1, whose database is a disposable cache;
   retention stays open until archived plans exist.
3. **The work loop.** The runner finishes; the judge accepts or sends back with a response; the
   loop is bounded by attempts; a plan is satisfied when every task is accepted.
4. **One dispatch path.** A milestone item is a task; a runner is whatever a launcher started;
   the tmux session path, the dispatch-plan schema and the dispatch-state store retire.
5. **Remotes as projections.** Quotes the sentences Slice 8 step 1 names and states their
   replacement.
6. **One enforcement point per rule.** The Layers rules, the spec as the register of what the
   surface enforces, `work-loop.md` and `runner-contract.md` as the register of what prose
   carries, and the M6 result as the evidence for that split.

Done when each ADR carries `Status: Accepted` with the repository owner's review approval on the
pull request that merged it, and ADR-1770-1 carries its `Superseded by` line.

## Slice 2 — build

1. `dh_core/ledger/`: the database path from `dh_paths.state_root()`, whose slug already derives
   from the git common directory (`dh_paths.py:_git_common_root`); open in WAL with a busy
   timeout, refusing with `network-filesystem` on a mount type in `ledger_spec.NETWORK_FILESYSTEMS`;
   the schema generated from `ledger_spec.COLUMNS`; event append and fold; one function per
   `ledger_spec.TRANSITIONS` entry; the derived columns from their rules; import, export and
   `from-milestone`, the last over `dh_core/operations.py:dispatch_conflicts`.
2. The `plan` group in `sam_schema/sam_plan.py`, mounted by `sam_schema/cli.py`: one command per
   `ledger_spec.COMMANDS` entry, flags as that entry names them.
3. `tests_sam/test_ledger_conformance.py`: a harness that walks `ledger_spec.TRANSITIONS` and,
   for each, builds the from-status, runs the command, and asserts the checks fire in order or
   the effects, events and fold hold. Plus the tests the spec cannot express: 16 processes race
   `dispatch` and exactly one wins, red against a read-then-write implementation; a worktree and
   its main checkout open one database; a network mount type refuses; a database written by the
   previous schema version opens and folds; every M3 fixture round-trips through import field
   for field; `export` prints `unchanged` after a wave that only renewed.
4. `tests_sam/fixtures/loop-plan/` (three tasks, two parallel, one whose first attempt leaves a
   criterion unmet, `lease.ttl_seconds` 60) and `tests_sam/scripted_runner.py`, the PEP 723 entry
   script over `tests_sam/scripted_runner_lib/`, driving dispatch, read, renew, both report
   sections, finish, settle, accept, then one send-back, re-dispatch, finish and accept, as a CI
   job. It records each expected behaviour as
   an observation rather than asserting inline, so `tests_sam/test_scripted_runner.py` names the
   step that broke and a hand run still exits non-zero on the first unsatisfied one.

Done when the conformance and closure tests are green, the race test's red run is recorded in
the pull request, `sam plan --help` lists every `ledger_spec.COMMANDS` entry, and the scripted
runner passes in CI.

## Slice 3 — MCP parity

`sam_task` and `sam_plan` in `sam_schema/server.py` call `dh_core/ledger/`, one action per spec
command; `tests/test_frontend_parity.py` gains a case per command in its existing
CLI-subprocess versus server-function pattern. Done when the parity test is green and its red
run against the pre-slice server is recorded in the pull request.

## Slice 4 — the loop in the skills

One commit for every dispatcher, runner and judge file.

1. `skills/implement-feature`, `skills/dispatch`, `skills/multi-perspective-review`,
   `skills/complete-implementation` and `skills/dispatch-contract` point at `work-loop.md`. Each
   step that starts, waits on, or decides a task quotes the `observed` text of the judge row it
   performs and names that row's command. The `bd ready --parent` branch and the
   `sam-ready-tasks` call become `ready`; the batch check reads `status`;
   `references/agent-health-check.md` is deleted, its cases being rows J5 to J9. In
   `complete-implementation`, a failing quality gate reclaims the task whose reported
   `FILES_CHANGED` the gate output names, rather than adding a task to a finalized plan.
2. `agents/task-worker.md`, `skills/start-task`, `agents/t0-baseline-capture.md`,
   `agents/tn-verification-gate.md` and `skills/work-backlog-item` point at
   `runner-contract.md`, and `task-worker.md`'s report template points there for its fields
   rather than defining them. The `claim` step and the active-task registration in
   `start-task` go, with its `--complete` branch, and `task-worker.md`'s sentence saying
   `start-task` marks the task complete. The other three files carry no claim, active-task or
   `state complete` call today; they gain the `read --attempt`, report and `finish` steps.
3. `hooks/hooks.json` per M1, on the four harnesses whose plugins can ship a hook: Claude Code
   and Codex read `hooks/hooks.json`; Kimi reads a `hooks` array in `kimi.plugin.json`; Cursor
   reads `hooks/hooks.json` through its own manifest. `session-start-session-id.cjs` is deleted
   whatever M1 says.
4. Delete everything the `today` column names in the "What retires" rows marked 4.

Done when a grep of `skills/` and `agents/` for those rows' M2 terms returns zero matches; a
live `implement-feature` run on `tests_sam/fixtures/loop-plan/` ends with every task accepted
after one send-back and with fewer user messages than the M0 count, ideally none; a run with one
runner killed mid-task by M1's recorded command ends with that task settled, reclaimed and
re-run to accepted; both observed through `status`, in an M4 CI job or as attached transcripts.

## Slice 5 — milestones on the same path

`skills/work-milestone`: the plan comes from `from-milestone --milestone-number N
--integration-branch B --quality-gate …`; each item runs through `work-loop.md` with a launcher
that gives the runner its own worktree, the harness option where M5 found a matching common
directory and a child process in a worktree the launcher created otherwise; the merge follows
row J14, gates on a scratch merge, then accepts, then fast-forwards `integration_branch`. Move
the `DISPATCH_PLAN` reader under `sam_schema/readers` for `import --from dispatch`, then delete
everything the rows marked 5 name. Done when a live run on a milestone with two independent
items and one conflict group ends with every item accepted and merged, observed through
`status`, per M4, and the M2 grep for those rows matches only the ADRs and `import --from
dispatch`.

## Slice 6 — retire the content record as a store

`sam_plan.py:_backend` and `server.py:_get_backend` become one accessor used by `import` and
`export`; delete everything the rows marked 6 name, the `sam_schema/readers` surviving inside
`import`; `dh_config.py` drops the `task` and `context` subsystems and reads
`ledger_spec.CONFIG`; `DependencyGraph.get_ready_tasks` in `sam_schema/core/dependencies.py`,
the module-level `get_ready_tasks` in `dh_core/operations.py`, and the cascade in
`dh_core/operations.py:update_task_status` are deleted, leaving one implementation of readiness
and one of the cascade, both in `dh_core/ledger/`. Done when the M2 grep for those rows matches
only `import`, `export`, their tests and the ADRs; a test asserts `ImportError` for each retired
provider; a test reads each `ledger_spec.CONFIG` key with its default; and "What retires" and
"The system today" are deleted from this file.

## Slice 7 — projection checks

Per backend, with GitHub under the `main` plus `GITHUB_TOKEN` gate the repository `AGENTS.md`
names, SQLite on every pull request, and Beads where `bd` is installed on the CI machine: export
twice and assert one record whose revision advanced once; edit the record out of band, export,
and assert `divergences` lists it and the record equals the projection. Done when green, with
the red run against an exporter without the divergence re-read recorded in the pull request.

## Slice 8 — documentation

1. Three sentences cite ADR 5: in `docs/PURPOSE.md` "Current Boundary", the one naming plans and
   tasks among what the configured backend routes; in `docs/backend-providers.md`, the one
   saying the backend owns task state; and in `backlog_core/ARCHITECTURE.md`, the
   "Provider-owned artifacts and plans" heading's claim.
2. `backlog_core/ARCHITECTURE.md` "Module: dispatch_state.py" and
   `docs/component-architecture.md` each cite the ADR that retires what they describe.
3. Both copies of `workflow-architecture-diagram.md`, the plugin's and `.claude/docs/`, and the
   plugin `README.md` line saying a SubagentStop hook marks tasks complete, each describe
   `finish` and `settle`.
4. The plugin `AGENTS.md` carries, beside its `dh_core/operations.py` line: "The CLI is the PEP
   723 script `sam_schema/cli.py`, run as `uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py"
   <group> <command>` from a Claude Code skill body, or `scripts/run_sam_cli.py` from a shell;
   `sam plan --help` lists the plan group."
5. `.dh/config.yaml` documentation gains each `ledger_spec.CONFIG` key with its default.
6. `rules/plugin-layer-triage.md` carries the Layers section above, named as the first step of
   the fix cycle in `rules/fix-delegation-discipline.md` and by the "Fix" branch of the Task
   Classification diagram in `.claude/CLAUDE.md`.
7. `dh_paths.py`'s docstring drops the two Cursor claims `CLAIMS-REGISTER.md` marks reported.

Done when a fresh-context agent given `work-loop.md`, `runner-contract.md`, `sam plan --help`
and step 4's sentence drives the `scripted_runner.py` path through one send-back to acceptance,
reading nothing under `sam_schema/`, `dh_core/`, `backlog_core/` or `skills/`.

## What retires

Deleted from this file when Slice 6 merges; the ADRs carry the terms. "Produced at" is the layer
the failure lives at today; "fixed at" is the layer the replacement enforces at.

| today | replaced by | M2 terms | produced at | fixed at | slice |
|---|---|---|---|---|---|
| the active-task record, `sam_schema/cli_active_task.py`, `sam_active_task`, every `ContextBackend` implementation and its protocol, `hooks/session-start-session-id.cjs` | the attempt number | `active-task`, `sam_active_task`, `CLAUDE_CODE_SESSION_ID`, `ContextBackend` | harness: one session id per agent tree (#3431) | surface | 4 |
| `task_status_hook.py` STATUS parsing and active-task resolution; `start-task`'s `--complete` branch; `task-worker.md`'s claim that `start-task` marks the task complete | `finish` | `STATUS: COMPLETE`, `STATUS: PARTIAL`, `--complete`, `task_status_hook` | prose | surface | 4 |
| `skills/implementation-manager/scripts/implementation_manager.py` and its `context/sam-tasks-*.json` caches; the `sam-task-create`, `sam-tasks`, `sam-task-status` and `sam-ready-tasks` commands; `plan claim` | `status`, `ready`, `dispatch` | `implementation_manager.py`, `sam-task-create`, `sam-tasks`, `sam-ready-tasks`, `plan claim`, `claim_task` | code: a check-then-write claim | surface | 4 |
| `references/agent-health-check.md` transcript inspection | rows J5 to J9 of `work-loop.md` | `agent-health-check` | prose | surface | 4 |
| `dispatch_schema`, `DISPATCH_PLAN` records, `backlog_core/dispatch_state.py`, `dispatch-state.db` built from `Path.home()` outside `DH_STATE_HOME`, the `dispatch` CLI group and its `dispatch_*` MCP tools, `check_stale_pids` | milestone plans in the ledger; `from-milestone` | `dispatch_state`, `DispatchStateManager`, `dispatch_schema`, `DISPATCH_PLAN`, `cli.py dispatch`, `dispatch_wave_start`, `check_stale_pids` | code: a second store and a second task model | code | 5 |
| `skills/kage-bunshin` as a skill, `spawn.py`'s session registry, the kage-bunshin hooks in `hooks/hooks.json`, the Stop hook files registered nowhere, and `wait "${PIDS[$i]}"` with `result_file` in `work-milestone` | the launcher shapes in `work-loop.md`, `spawn.py` kept as one of them | `kage-bunshin`, `kage-bunshin/sessions`, `registry-`, `KB_SESSION_ID`, `PIDS[`, `result_file` | surface: a call whose flags its parser rejects | prose | 5 |
| `ContentTaskProvider` as the plan store; `LocalYamlTaskProvider`; `GistTaskLayer`; the plan-index artifact on the `sam.plan_index_issue` sentinel; `sam_schema/core/backends/github_task.py`; the writer paths of `sam_schema/writers/yaml_writer.py`; the `plan migrate` command | the ledger; `import` and `export` | `ContentTaskProvider`, `LocalYamlTaskProvider`, `GistTaskLayer`, `gist_task_layer`, `plan_index_issue`, `sam_schema/writers/yaml_writer`, `plan migrate` | code: a whole-plan record and a remote round trip per write | code | 6 |
| the `.dh/config.yaml` keys `task.backend` and `context.backend`, and `TASKBACKEND` and `CONTEXTBACKEND` | `backend.name`; `ledger_spec.CONFIG` | `TASKBACKEND`, `CONTEXTBACKEND` | code | code | 6 |
| `~/.dh/projects/{slug}/plan/`, `context/`, `kage-bunshin/` and `dispatch-state.db` | `dh.db`; `github-cache/` stays the backend's; `plan/` is read by `import --from legacy` | `projects/{slug}/plan`, `active-task-`, `dispatch-state.db` | code | code | 6 |

## The system today

Context for the Slice 1 ADRs, as read 2026-09-06; deleted from this file when Slice 6 merges.

**SAM tasks**, a prose rule with enforcement at no layer. A plan `P…` holds tasks `T…`
(`sam_schema/core/models.py`). The orchestrator skills read ready tasks and start one in-process
`Agent()` per task: `implement-feature` "Progress Loop" step 3 passes the address as the whole
prompt, and `dispatch` and `multi-perspective-review` wrap it in more text. The runner
(`agents/task-worker.md` into `skills/start-task`) claims the task, registers an active-task
record keyed by `${CLAUDE_CODE_SESSION_ID}`, works, appends sections, and returns a `STATUS:`
text. `task-worker.md` line 60 says `start-task` marks the task complete; `start-task` carries
that call only in its `--complete` branch (line 45), which a grep of `skills/` and `agents/` on
2026-09-06 found no caller for, so completion falls to the SubagentStop hook
(`skills/implementation-manager/scripts/task_status_hook.py`), which resolves the stopping agent
through the active-task record. A read of `implement-feature` steps 4, 4a and 4b found no step
that judges a task against its acceptance criteria or sends it back.

**Milestone items**, a surface failure: a call whose flags its parser rejects. The `dispatch`
CLI group's `create-plan` writes a `DISPATCH_PLAN` record (`dispatch_schema/core/models.py`:
waves of `WaveItem`s with `issue`, `priority`, `depends_on`, `conflict_group`).
`skills/work-milestone` spawns one `claude` process per item through
`skills/kage-bunshin/scripts/spawn.py`, which runs a tmux session and records it under
`~/.dh/projects/{slug}/kage-bunshin/sessions/{session_id}/{name}.json`, then waits on the pid
and classifies the `STATUS:` text to decide merging. Both the skill's invocation and
`dh_core/operations.py:_build_spawn_cmd` pass `--worktree` and `--branch` with no subcommand,
which `spawn.py`'s parser rejects, so the path cannot run as written.
`backlog_core/dispatch_state.py` holds a second SQLite store, whose `items` table is keyed
`(milestone, wave_num, issue)` and carries a `pid` column that `check_stale_pids` probes with
`os.kill(pid, 0)`; the `pid` write sits after the branch the failing spawn takes. Two
kage-bunshin hooks in `hooks/hooks.json` read `registry-{sessionId}.json`, a path `spawn.py`
replaced, and the Stop hook files are registered nowhere.

**The store**, a code failure. Both SAM frontends persist a plan as one JSON content record:
`sam_plan.py:_backend` and `server.py:_get_backend` wrap the configured backlog backend in
`ContentTaskProvider` (`sam_schema/core/backends/content.py`), which loads every plan record at
process start, mutates in memory, and flushes the whole plan with `expected_revision`. On the
GitHub backend that record is a file under `.dh/content/v1/plan/…` on the `dh-content` branch,
written through the Contents API with blob-SHA compare-and-swap and cached under
`state_root()/github-cache`. `LocalYamlTaskProvider` is constructed by
`implementation_manager.py`, by `task_config.py` in `create_task_backend`'s `local` route and in
`get_backend(wrap_gist=True)`, by `gist_task_layer.py`, and by tests.

**What fails**, in code and in the harness. Record granularity is the plan, so two runners
mutating different tasks write one record; the later flush raises `ContentConflictError`, which
`claim_task` turns into `False`, reading as "already claimed". Every write is a remote round
trip, including the PostToolUse `last-activity` update on every Write, Edit and Bash call. Every
CLI process loads every plan record before doing anything. The active-task record is keyed by a
value every sub-agent of one session shares (#3431), so a stop is attributed to whichever task
registered last. Liveness has three mechanisms and no working one: `tmux has-session` for a tmux
session, the unreachable `os.kill` probe for a dispatch-state row, and transcript inference for
an in-process agent (`skills/implement-feature/references/agent-health-check.md`).
