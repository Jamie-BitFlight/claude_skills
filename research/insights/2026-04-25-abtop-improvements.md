# Improvement Proposals: abtop

**Research entry**: ./research/developer-tools/abtop.md
**Generated**: 2026-04-25
**Patterns assessed**: 6
**Backlog items created**: 5 (issues: #1944, #1945, #1946, #1947, #1948)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: Stalled-session detection using LastActivity timestamp

**Source pattern**: "Real-time session status detection: Thinking (generating, no active tool), Executing (tool active), Waiting (idle, user input), RateLimited (quota exceeded), or Done (finished)" (Key Features → Session Discovery and Monitoring; src/model/session.rs `SessionStatus` enum).
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py` and `plugins/development-harness/skills/implementation-manager/scripts/implementation_manager.py`
**Confidence**: High
**Impact**: High
**Backlog**: #1944 created — P1

### Current state

`task_status_hook.py` writes a `LastActivity` timestamp on every `Write|Edit|Bash` PostToolUse event (lines 15, 854, 930-933 — confirmed via Read). `implementation_manager.py status` and `ready-tasks` commands report `in_progress`, `not_started`, `blocked`, `deferred`, `skipped` task counts (lines 1060-1067) but never inspect `LastActivity`. Grep of `plugins/development-harness/` for `stall`, `stalled`, `stall_threshold`, `inactive_threshold` returns zero matches outside the LastActivity-write site itself. The orchestrator (`implement-feature` Progress Loop) has no observable signal that a task claimed `IN_PROGRESS` 30 minutes ago has stopped emitting tool events.

Symptom: a kage-bunshin or task-worker that hangs (model stuck in retry loop, deadlocked on missing input, network partition to MCP server) leaves the task `IN_PROGRESS` indefinitely. The dispatch loop cannot tell the difference between a task actively working and a task that has gone silent. The orchestrator must either wait the maximum allowed time or kill blindly.

### Target state

`implementation_manager.py status` output includes a `stalled_tasks: [...]` array enumerating every task where `status=IN_PROGRESS` AND `now - LastActivity > stall_threshold_minutes`. Default threshold = 15 minutes; readable from plan-level `stall_threshold_minutes` field on the `Plan` model in `sam_schema/core/models.py` or from a new top-level field in the plan YAML. New CLI subcommand `implementation_manager.py stalled <project> <slug>` returns only the stalled list (machine-parseable JSON). `ready-tasks` callers can decide to re-dispatch a stalled task to another agent.

### Measurable signal

Run `uv run plugins/development-harness/skills/implementation-manager/scripts/implementation_manager.py status <project> <slug>` against a plan with one IN_PROGRESS task whose `LastActivity` is older than the threshold. Output JSON contains a `stalled_tasks` field with at least that task's `id` and a `last_activity_age_minutes` integer. Run with `--threshold-minutes=N` overrides the default. Field `stall_threshold_minutes` is present in `sam_schema/core/models.py` `Plan` class (search returns a non-zero match).

---

## Improvement 2: Orphan-port detection for spawned kage-bunshin processes

**Source pattern**: "Orphan port detection: identifies ports held open by processes whose parent agent sessions have ended (Source: src/model/session.rs — `OrphanPort` struct). Orphan port killing: press `X` to terminate all detected orphan processes" (Key Features → Child Process and Port Monitoring).
**Local system**: `plugins/development-harness/skills/kage-bunshin/scripts/spawn.py` and `plugins/development-harness/skills/kage-bunshin/scripts/monitor.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #1945 created — P1

### Current state

`monitor.py` (472 lines) detects interactive state of tmux sessions (`_detect_interactive_state`, `_is_idle`, `_capture_pane`) and reads a registry file at `_registry_path()` (lines 127-145). It does not enumerate child processes of spawned `claude -p` sessions, does not run `lsof -i`, and does not detect ports left open by completed sessions. Grep of `plugins/development-harness/` for `lsof`, `orphan_port`, `port_check` returns zero matches. The dispatch state DB (`dispatch_state.DispatchStateManager`) tracks PID liveness (`dispatch_stale_check`) but only at the wave-item level — child servers spawned by a task (test servers, dev servers, MCP servers) are not tracked.

Symptom: a kage-bunshin task that spins up `pytest --pdb`, `npm run dev`, or a test FastMCP server may leave that subprocess listening on a port after the parent `claude -p` exits (process orphaning, signal mishandling). The next wave hits a port-conflict on retry. There is no audit trail of which task left which port open.

### Target state

`monitor.py` (or a new `port_audit.py` companion) runs `lsof -i -n -P` on slow ticks (every 30s, configurable) and cross-references PID → kage-bunshin session via the registry file. Output JSON includes `orphan_ports: [{port, pid, command, owning_session_id, exit_status}]` for each port held by a process whose parent kage-bunshin session has terminated (registry says `done` but child PID still listening). New `monitor.py kill-orphans` subcommand sends SIGTERM (then SIGKILL after 5s) to the orphaned PIDs. Optional integration into `dispatch_wave_status` to surface orphan counts at wave end.

### Measurable signal

Spawn a kage-bunshin session that runs `python -m http.server 8765 &` and exits. Run `uv run plugins/development-harness/skills/kage-bunshin/scripts/monitor.py audit-ports`. Output JSON contains an entry with `port: 8765` and the spawned session ID. Run `monitor.py kill-orphans` then `lsof -i :8765` returns no results. Grep of `plugins/development-harness/` for `lsof` returns at least one match in `monitor.py` or its companion.

---

## Improvement 3: AgentCollector trait for pluggable session discovery

**Source pattern**: "`AgentCollector` trait: defines interface for agent-specific session discovery (Source: `pub trait AgentCollector`) — `collect()` returns all live sessions, `live_rate_limit()` returns agent's current rate limit status, `discovered_config_dirs()` returns config directories" (Technical Architecture → Collector Framework).
**Local system**: `plugins/development-harness/skills/kage-bunshin/scripts/monitor.py` and `plugins/development-harness/skills/implementation-manager/scripts/implementation_manager.py`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the local dh `BacklogBackend` and `TaskBackend` Protocols already provide a pluggable-backend pattern (per `plugins/development-harness/CLAUDE.md` Backend Providers section). Whether a *third* Protocol for "live agent session collector" adds value over those two depends on whether session monitoring will ever need to discover Codex/Sonnet-CLI/other agent processes — not currently a stated requirement. Raising confidence requires (a) a concrete second agent runtime to monitor and (b) verification that the existing kage-bunshin registry file isn't already the right abstraction.

### Current state

`monitor.py` reads kage-bunshin's own registry file (`_load_registry`, line 292) and tmux sessions (`_live_tmux_sessions`, line 185). Discovery is hardcoded to kage-bunshin-spawned sessions. There is no Protocol like `AgentSessionCollector` with `collect_live_sessions()` and `live_rate_limit()` methods.

### Target state (deferred)

A `SessionCollector` Protocol in `plugins/development-harness/sam_schema/core/` (or a new `plugins/development-harness/monitoring/` package) with implementations for kage-bunshin (current), tmux-pane introspection (future), and a hypothetical `claude --print` session indexer. Backends select via a `MONITOR_COLLECTOR` env var or `monitor.toml` config.

### Measurable signal (deferred)

Not actionable until a second collector concretely needed.

---

## Improvement 4: --once snapshot mode for implementation_manager status

**Source pattern**: "One-time snapshot mode: `abtop --once` prints current session state and exits (useful for scripting and CI integration) (Source: src/main.rs — `--once` flag logic)" (Key Features → Snapshot Export and Batch Mode).
**Local system**: `plugins/development-harness/skills/implementation-manager/scripts/implementation_manager.py`
**Confidence**: High
**Impact**: Low
**Backlog**: #1948 created — P2

### Current state

`implementation_manager.py status` already prints a JSON snapshot once and exits (lines 1045-1069) — this matches the `--once` semantic abtop describes for plan progress. However, `ready-tasks` (line 1072) and `validate` (line 1126) emit JSON to stdout without a stable wrapper schema, no `as_of_timestamp`, no `schema_version`, and no `--format yaml|markdown` option. CI dashboards and external snapshot consumers must re-implement parsing per command. The `--demo` mode abtop offers (sample data for screenshots/tests) does not exist for `status` — there's no fixture-mode way to populate a synthetic plan for snapshot validation tests.

Symptom: snapshot consumers (CI status badges, external dashboards reading `~/.dh/projects/*/plan/`) parse three different output shapes from three subcommands. Test fixtures must build full plan files instead of using a flag.

### Target state

`implementation_manager.py status --format=json|yaml|markdown` supports all three formats with a stable wrapper: `{schema_version: "1", as_of: "2026-04-25T...", project: "...", feature: "...", data: {...}}`. New `--demo` flag populates synthetic data without requiring a real plan file (useful for screenshot tests and skill examples). The same wrapper is applied to `ready-tasks` and `validate` commands.

### Measurable signal

Run `uv run plugins/development-harness/skills/implementation-manager/scripts/implementation_manager.py status . my-feature --format=yaml`. Output is valid YAML beginning with `schema_version: '1'`. Run `... status . any --demo --format=json`. Output is a synthetic snapshot with at least one in-progress task and one ready task. `jq -r .schema_version` against any of the three commands' JSON output returns `1`.

---

## Improvement 5: Secret redaction in agent monitoring/logging output

**Source pattern**: "**Secret Redaction**: Tool names and file paths are displayed, but credentials are filtered before rendering. abtop's `redact_secrets()` function masks common token prefixes (`sk-ant-`, `sk-proj-`, `ghp_`, etc.) before UI display" (Technical Architecture → Key Design Decisions).
**Local system**: `plugins/development-harness/skills/kage-bunshin/scripts/monitor.py` (and any other place that prints session transcripts/output)
**Confidence**: High
**Impact**: High
**Backlog**: #1946 created — P1

### Current state

`monitor.py` prints session pane captures via `_capture_pane` (line 203) and emits payloads via `_emit` (line 145). There is no `redact_secrets`-equivalent function in `plugins/development-harness/skills/kage-bunshin/`. Grep of `plugins/development-harness/` for `redact`, `mask_token`, `sk-ant`, `ghp_` returns zero matches. tmux pane output (which can include `echo $GITHUB_TOKEN`, accidentally pasted credentials, or LLM-replayed secrets from training data) flows into the monitor's emitted JSON without filtering. The same JSON is consumed by orchestration scripts and may end up in logs, dispatch state DBs, or `~/.dh/projects/{slug}/state/` files.

Symptom: a kage-bunshin agent that runs `env | grep TOKEN` (or pastes a curl command with a header) leaks secrets to the monitor output and to any downstream consumer. There is no defense-in-depth at the boundary that captures and redistributes that text.

### Target state

A `redact_secrets(text: str) -> str` function in a shared module (e.g. `plugins/development-harness/dh_paths.py` companion or new `plugins/development-harness/redact.py`) masks: `sk-ant-*`, `sk-proj-*`, `sk-*`, `ghp_*`, `gho_*`, `ghs_*`, `github_pat_*`, AWS access key IDs (`AKIA[0-9A-Z]{16}`), and bearer tokens of the form `Bearer [A-Za-z0-9_-]{20,}`. `monitor.py._capture_pane` and `_emit` route all string fields through it. Same function reused by `kage-bunshin/scripts/spawn.py` log capture and any future TUI dashboard.

### Measurable signal

Add a unit test at `plugins/development-harness/tests/test_redact.py` with cases asserting `redact_secrets("sk-ant-api03-abcdef...")` returns `"sk-ant-***"` (or similar mask). Run `uv run pytest plugins/development-harness/tests/test_redact.py` — exit 0. Grep of `plugins/development-harness/skills/kage-bunshin/scripts/monitor.py` shows `redact_secrets` imported and applied to `_capture_pane` output before emission.

---

## Improvement 6: Read-only state discovery from JSON/transcript files

**Source pattern**: "**Read-Only File Access**: abtop reads only `.claude/sessions/`, `.claude/projects/`, and rate limit JSON files; it never modifies Claude Code's configuration or state. This ensures compatibility across versions and multiple agent instances without synchronization issues." (Technical Architecture → Key Design Decisions).
**Local system**: `plugins/development-harness/skills/kage-bunshin/scripts/monitor.py`, `~/.claude/sessions/` (untouched by dh today)
**Confidence**: High
**Impact**: Medium
**Backlog**: #1947 created — P1

### Current state

`monitor.py` only knows about kage-bunshin's own registry file at `_registry_path()` (lines 127-145). It does not parse `~/.claude/sessions/*/transcript.jsonl` or `~/.claude/projects/*/` files. Token counts, context-window utilization, and current-task fields exist in those Claude-Code-internal transcript files (per abtop's `src/collector/claude.rs`) but the dh plugin does not read them. Live session token consumption per kage-bunshin child is therefore not observable to the orchestrator.

Symptom: `dispatch_wave_status` reports per-item `status` and `cost` (set by `dispatch_item_status` on completion) but cannot show in-flight token usage. A wave orchestrator deciding whether to dispatch the next batch has no signal that running items are about to hit the context window.

### Target state

A new `plugins/development-harness/scripts/claude_session_reader.py` (read-only, no writes) parses `~/.claude/sessions/{session_id}/transcript.jsonl` for a given session ID and returns `{token_count, context_window_pct, current_tool, last_message_at}`. `monitor.py` calls it on slow ticks (every 5 ticks, 10s) and merges the result into the registry payload. `dispatch_wave_status` includes per-item `live_token_count` and `live_context_pct` for items still `in_progress`.

### Measurable signal

Run `uv run plugins/development-harness/scripts/claude_session_reader.py <session-id>` against a real `~/.claude/sessions/` directory. Output JSON has `token_count` (int), `context_window_pct` (float 0.0-1.0), `current_tool` (str|null), `last_message_at` (ISO timestamp). Reading triggers no writes to `~/.claude/`: `find ~/.claude -newer /tmp/marker` returns zero entries after invocation. Wired into `dispatch_wave_status` so its response shape gains `live_token_count` and `live_context_pct` fields for in-progress items.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| AgentCollector trait for pluggable session discovery (Improvement 3) | Medium | Existing `BacklogBackend` and `TaskBackend` Protocols already provide a pluggable-backend pattern. A third Protocol adds value only if a concrete second agent runtime needs monitoring — not currently a stated requirement. Raising confidence requires (a) naming the second runtime and (b) verifying the kage-bunshin registry isn't already the right abstraction. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Theme framework with colorblind variants | Skill framework here is text/markdown only — no colored terminal UI surface to theme. Pattern is incompatible with the local architecture. |
| tmux pane jumping (Enter to switch pane) | Already covered by `Skill(skill: "using-tmux-with-claude-code")` per the cross-reference table in the research entry; tmux integration is handled at the user-workflow layer, not the plugin layer. |
| Self-update via `--update` flag | Plugin updates are handled by the Claude Code marketplace and pre-commit version-bump hook — equivalent mechanism already exists. |
| Rate limit observability (5h / 7d windows) | Already adjacent to backlog #1062 (`--max-turns` cap) and #1061 (`--effort` flag). The 5h/7d window-based rate-limit metric is API-internal to Anthropic and not derivable without a dedicated StatusLine hook. Treated as a Claude-Code platform feature, not a dh-layer concern. |
