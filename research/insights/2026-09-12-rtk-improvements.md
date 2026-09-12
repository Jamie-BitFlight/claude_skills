---
title: "Improvement Proposals: RTK (Rust Token Killer)"
---

# Improvement Proposals: RTK

**Research entry**: ./research/developer-tools/rtk.md
**Generated**: 2026-09-12
**Patterns assessed**: 8
**Backlog items created**: 0 — backlog MCP unavailable this session (see "Backlog Creation Blocked" below)
**Deferred (low confidence)**: 2
**Skipped (already covered)**: 5

---

## Backlog Creation Blocked

`mcp__plugin_dh_backlog__backlog_list` and `backlog_add` could not run in this session. The first
call returned a TLS error from the GitHub backend
(`SSLCertVerificationError ... CA cert does not include key usage extension`); the retry, and the
proxy status probe that would diagnose it, were both denied by the permission classifier
(`Exfil Scouting`).

Consequence for this file:

- No duplicate check against existing backlog titles was possible. Proposals 1–3 below may
  duplicate items already tracked — check before creating.
- No items were created. Each proposal records the priority it should receive under the
  confidence x impact matrix instead of an issue number.

---

## Improvement 1: Add an output-volume dimension to transcript-analysis so verbose commands are ranked by bytes returned

**Source pattern**: "Analytics & Discovery" section of the research entry — `rtk gain` (summary stats
and token savings dashboard), `rtk discover` (find missed savings opportunities), `rtk session`
(adoption across recent sessions). RTK measures the byte volume of command output actually observed
and ranks where reduction would pay off.
**Local system**: /home/user/claude_skills/plugins/agentskill-kaizen/skills/transcript-analysis/SKILL.md
and /home/user/claude_skills/plugins/agentskill-kaizen/skills/transcript-analysis/references/duckdb-queries.md
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — backlog MCP unavailable. Would be P1 (High confidence x Medium impact).

### Current state

`transcript-analysis/SKILL.md` defines a Signal Catalog of nine dimensions (Tool Misuse Detection,
Repeated Errors, Missing Tooling Opportunities, Subagent Delegation Patterns, Shortest Path
Analysis, Red Herring Detection, System Process Interruptions, Missing Hooks, DuckDB SQL Querying).
Every dimension keys on *which* tool was called or *whether it errored*. None measures *how much
output a call returned*. Dimension 1 flags `grep` in a Bash command because a Grep tool exists — a
correctness-of-tool-choice signal — not because the command returned 40 KB.

`references/duckdb-queries.md` contains no query computing a length or byte count over tool results:
`grep -n "bytes\|length(\|size"` against that file returns zero matches. So an agent running kaizen
analysis on this repo cannot answer "which commands cost the most context in the last N sessions",
which is the question that decides whether an output-filtering measure (a wrapper, a skill, a
`--quiet` default) is worth building at all.

### Target state

A tenth Signal Catalog dimension in `transcript-analysis/SKILL.md` — "Output Volume Hotspots" —
extracting from `user` records carrying tool results: for each `tool_use_id`, the byte length of the
returned content, joined back to the originating `assistant` tool_use block to recover the tool name
and, for Bash, `input.command`. The dimension ranks by total bytes returned per command shape (first
two tokens of the command, e.g. `git status`, `cargo test`) and reports call count alongside total
bytes, so a single huge result is distinguishable from a frequently repeated moderate one.

A matching query in `references/duckdb-queries.md` returning columns `command_shape`, `calls`,
`total_bytes`, `max_bytes`, ordered by `total_bytes` descending, over `read_ndjson_auto` with
absolute paths (per the existing path rules for the DuckDB MCP).

The dimension's Recommendation type reuses the existing taxonomy in the Output Format section
(hook, skill patch, agent prompt fix, CLAUDE.md update) — a hotspot with a cheaper invocation
available is a hook or skill-patch candidate.

### Measurable signal

`transcript-analysis/SKILL.md` contains a Signal Catalog entry whose heading contains "Output
Volume". `references/duckdb-queries.md` contains a query whose SELECT list includes `total_bytes`.
Running that query via `kaizen-duckdb execute_query` against this project's transcript directory
returns at least one row with a non-null `total_bytes`, and the top row's `command_shape` is a real
command string, not null.

---

## Improvement 2: Codify transform-failure passthrough in the silent-failure-prevention rule

**Source pattern**: "Design Principles" section of the research entry, principle 4 — "Fail-Safe — If
filtering fails, fall back to original output" (ARCHITECTURE.md lines 31–36), paired with principle
3, "Exit Code Preservation".
**Local system**: /home/user/claude_skills/rules/silent-failure-prevention.md
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — backlog MCP unavailable. Would be P1 (High confidence x Medium impact).

### Current state

`rules/silent-failure-prevention.md` has exactly two sections: "Write Operations Must Report What
Changed" (side-effecting functions must return what changed, callers must use it) and "Branching on
Input Values Requires an Explicit Fallback" (every `if`/`elif` chain needs a final branch that acts
or errors). Both address code that *writes* or *dispatches*. Neither addresses code that *transforms
a payload on the way to a consumer* — a filter, summarizer, formatter, or validating hook — where the
failure mode is different: the transform throws or produces a degraded result, and the consumer
receives less than the raw input carried, without being told.

The repo already contains such transforms and handles this inconsistently by convention rather than
by rule. `plugins/summarizer/hooks/validate-summarizer-output.cjs` fails open correctly — unparseable
hook input exits 0 (line 257), a missing `agent_transcript_path` exits 0 (line 269), an empty
extracted text exits 0 (line 274) — but nothing in the rules requires that behavior, so the next such
hook may fail closed and silently drop a sub-agent's entire output.

### Target state

A third section in `rules/silent-failure-prevention.md` — "Transforms Must Pass Through on Failure" —
stating that any code reducing, filtering, reformatting, or validating a payload between a producer
and a consumer must, when the transform itself fails, emit the original unmodified payload rather
than a partial, empty, or dropped result; and must preserve the producer's exit status rather than
substituting the transform's own. With a wrong/right pair in the file's existing style:

- Wrong: `try: return filter(out)` / `except Exception: return ""` — consumer cannot distinguish
  "command produced nothing" from "filter crashed".
- Right: `try: return filter(out)` / `except FilterError: warn(...); return out` — the consumer gets
  everything it would have had without the transform.

The section names the exit-status half explicitly: a wrapper returns the wrapped command's status
(the pattern `scripts/run_bounded.py` already implements — its `run` docstring states it returns
"The command's exit status, or ``TIMEOUT_EXIT_CODE`` if it was terminated"), never a status
manufactured by the wrapper on a transform error.

### Measurable signal

`rules/silent-failure-prevention.md` contains a third `##` section covering transform failure, with
a Wrong/Right code pair matching the file's existing format. `grep -c '^## ' rules/silent-failure-prevention.md`
returns 3. The rule is referenced from `docs/cli-output-conventions.md` (which today lists four
output conventions, none about failure behavior), so anyone writing an agent-facing CLI reaches it.

---

## Improvement 3: Register the interception mechanisms of the harnesses this repo targets in the hooks platform-coverage registry

**Source pattern**: "Auto-Rewrite Hook" and "Implementation Details" sections of the research entry —
RTK enumerates distinct interception mechanisms per harness: PreToolUse hooks (Claude Code, VS Code,
Factory Droid), BeforeTool hooks (Gemini), AGENTS.md/rules directives (Codex, Kimi, Windsurf, Cline),
TypeScript extensions (Pi, OMP), Python plugin adapters (Hermes), with per-harness install commands
(`rtk init -g --gemini`, `--codex`, `--agent cline`, `--agent hermes`).
**Local system**: /home/user/claude_skills/plugins/plugin-creator/skills/hooks-guide/references/platform-coverage.md
**Confidence**: High
**Impact**: Low
**Backlog**: Not created — backlog MCP unavailable. Would be P2 (High confidence x Low impact).

### Current state

`platform-coverage.md` is a registry with a "Covered platforms" table holding three rows (Claude Code
hooks.json, Claude Code inline agent frontmatter, GitHub Copilot `.github/hooks/`) and a
"Fetch-attempted platforms" table holding four rows (Cursor, Windsurf, Amp, OpenCode). Gemini CLI and
Codex appear in neither table — there is no row, no attempted URL, and no "no hook system" verdict
recorded for either.

This contradicts the repo's stated targets: `AGENTS.md` says "Plugins are expected to be developed
cross-harness compatible (claude-code, codex, hermes, kimi)" and points at `harness_compatibility.json`
and `docs/cross-harness-smoke-tests.md`. Codex is a first-class target whose interception model
(directive files, not a hook runtime) is absent from the one registry that is supposed to record
exactly that, so an agent asked to add a Codex-side hook has no recorded answer and re-derives it.

### Target state

`platform-coverage.md` carries a row for every harness named in `AGENTS.md` as a target
(codex, hermes, kimi) plus Gemini CLI, each placed in the correct table with its hook concept
filled in — including the negative verdicts, which are findings, not gaps: a harness whose
interception is a directive file rather than a hook runtime is recorded as "No hook runtime —
interception via AGENTS.md/rules directives" with the URL that was checked and the date, in the same
shape as the existing Cursor row ("Rules system, not hooks").

Where a row states a hook runtime exists, a fetch entry is added to
`hooks-guide/scripts/fetch-and-transform-hooks-docs.sh` per the file's own "Adding a new platform"
procedure, so the reference file is generated rather than hand-written.

### Measurable signal

`platform-coverage.md` contains rows matching `codex`, `hermes`, `kimi`, and `gemini`
(case-insensitive), each with a non-empty "Last verified" or "Result" cell. For every row placed in
"Covered platforms", the named reference file exists in `hooks-guide/references/` and the platform
has a corresponding fetch entry in `scripts/fetch-and-transform-hooks-docs.sh`.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason / what would raise it |
|---|---|---|
| Reduce-with-recall-handle as a sanctioned third option under "No Invented Limits" — RTK persists unfiltered output to a configurable retriever (`[retriever] mode = "sqlite" \| "tee" \| "disabled"`) and hands back `rtk recall {token-id}`, automatically on command failure | Medium | `.claude/CLAUDE.md` "No Invented Limits" already requires that shortened content "provide a way to access the rest", and offers `--offset`/`--limit` pagination as the mechanism. RTK's store-and-handle mechanism is absent by name but the principle is present, so this is "present in spirit, specific mechanism absent". Raising it requires finding a concrete in-repo case where paginating is not possible (a one-shot subprocess whose output is not re-derivable) and the rule therefore leaves the author with no sanctioned option — I did not verify such a case exists. |
| Per-command exclusion config for interception hooks (`[hooks] exclude_commands = ["curl", "playwright"]`) — an opt-out list so a rewriting or injecting hook can be disabled for commands it breaks | Low | Inferred, not observed. This repo's hooks (`.claude/hooks/*.mjs`, `plugins/*/hooks/*.cjs`) inject context or validate rather than rewrite commands, so the failure mode the exclusion list solves may not exist here. Raising it requires identifying a repo hook that mutates a command's behavior and has no documented opt-out. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| PreToolUse hook rewriting a Bash command before execution (RTK's default `rtk init -g` auto-rewrite mode) | Already covered. `plugins/plugin-creator/skills/hooks-io-api/SKILL.md` documents `hookSpecificOutput.updatedInput` ("Modifies tool input before execution. Include all fields, not just changed ones", line 684) and the PermissionRequest form `"updatedInput": { "command": "npm run lint" }` (line 701) — the exact mechanism, with the all-fields caveat. |
| Exit-code preservation through a command wrapper (RTK design principle 3) | Already covered as implementation. `scripts/run_bounded.py` returns the wrapped command's exit status, with `124` reserved for timeout, documented in its own docstrings. Its rule-level half is folded into Improvement 2 rather than proposed separately. |
| Detecting shell commands that should have used a first-class tool (RTK's `rtk discover` framing applied to tool choice) | Already covered. `transcript-analysis/SKILL.md` Signal Catalog dimension 1, "Tool Misuse Detection", maps `grep`→Grep, `find -name`→Glob, `cat/head/tail`→Read, `ls`→Glob, `sed/awk`→Edit, and excludes legitimate pipeline uses. Improvement 1 adds the volume axis it lacks, not this axis. |
| Reduced output must carry a pointer back to the full source | Already covered for summaries. `plugins/summarizer/skills/summarizer/SKILL.md` requires `source_path` in every summary's YAML frontmatter, and `hooks/validate-summarizer-output.cjs` blocks (exit 2) when that field is missing (`validateStructured`, lines 93–107). |
| Adopting RTK itself as a dependency of this repo's agent workflows | Not a local-system improvement. The repo's own agent-facing output convention (`docs/cli-output-conventions.md`) already mandates compact JSON from every script and MCP server it ships, and RTK filters *other tools'* output at the shell boundary — installing it is an operator choice about a developer's machine, not a change to a skill, agent, or workflow in this repo. The entry's own "Built-in Tool Limitation" note (the hook does not apply to Read/Grep/Glob) further narrows what it would reach here. |
