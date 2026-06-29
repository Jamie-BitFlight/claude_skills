---
title: "Improvement Proposals: Omnigent"
---

The Omnigent entry's "Relevance to Claude Code Development" section is populated with six
patterns. Each pattern was mapped to a local system and assessed for an actionable, observable
gap. The two policy mechanisms named concretely in the Policy Configuration section
(`cost_budget`, `max_tool_calls_per_session`) were assessed separately because they are the only
patterns in the entry that name a specific, gateable mechanism rather than an architecture.

No proposal reached **High confidence**, so no backlog items were created. The reasoning for each
assessment is recorded below so a future pass can raise confidence with targeted verification.

---

## Deferred Proposal A: Per-session/per-wave spend cap with ASK threshold

**Source pattern**: Policy Configuration section — `cost_budget` built-in policy: "hard spend cap... with a soft warning on the way" via `max_cost_usd` and `ask_thresholds_usd`.
**Local system**: `plugins/development-harness/skills/implementation-manager/SKILL.md` (hook runtime profiles) and the dispatch orchestration layer (`dispatch_item_status` records a per-item `cost` field — see development-harness CLAUDE.md "Dispatch Orchestration System").
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: confirming absence requires reading the dispatch_state DB layer and server.py to verify no aggregate budget enforcement exists anywhere; and adding a hard cap is a design decision (block vs warn) not a directly observable correction.

### Current state

`dispatch_item_status(milestone, issue, status, result, error, cost)` records a per-item `cost`
value (development-harness CLAUDE.md, Dispatch Orchestration System). A grep for
`cost|budget|spend` across `implementation-manager/` returns no matches — the hook runtime
profiles (`minimal`/`standard`/`strict`, SKILL.md lines 202–243) have no cost concept. There is
no observable mechanism that sums recorded per-item costs across a wave or session and halts (or
asks) when an aggregate threshold is crossed.

### Target state

A policy or hook reads accumulated per-item `cost` from the dispatch state DB and, when the sum
crosses a configured `ask_threshold_usd`, surfaces an approval prompt; when it crosses a
configured `max_cost_usd`, blocks further dispatch. Threshold values readable from
`.dh/config.yaml`.

### Measurable signal

A command or hook exists that, given a milestone, returns `budget_exceeded: true` when the sum of
`dispatch_item_status` `cost` values exceeds the configured cap, and a config key
(`dispatch.max_cost_usd` or equivalent) is present in at least one config schema.

### What would raise confidence to High

Read `plugins/development-harness/scripts/` dispatch_state module and `server.py` to confirm no
aggregate cost enforcement exists, and confirm with the user whether a hard cap (block) or a
warning-only signal is the desired behavior. The block-vs-warn choice is a design decision, which
is why this is not a directly observable gap.

---

## Deferred Proposal B: Per-session tool-call cap as a runaway guardrail

**Source pattern**: Policy Configuration section — `max_tool_calls_per_session` built-in policy: "cap how many tools one session can call" (limit example 50).
**Local system**: `plugins/development-harness/skills/implementation-manager/SKILL.md` — `task_status_hook.py` PostToolUse handler and the `strict` hook profile.
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred — confidence Medium: the local PostToolUse hook already counts tool activity implicitly (LastActivity updates per Write/Edit/Bash) but does not count or cap; adding a cap is a design decision and the strict profile is explicitly observational-only by design (SKILL.md line 212).

### Current state

The PostToolUse handler fires on each Write/Edit/Bash and updates `LastActivity`
(implementation-manager SKILL.md lines 187–200), so per-task tool activity is observed but never
counted or bounded. The `strict` profile "warnings are observational only — they do not prevent
task completion" (line 212). No profile caps the number of tool invocations a session may make.

### Target state

An opt-in profile or config value caps tool invocations per session; when exceeded, the hook emits
a blocking signal (or an ASK) instead of a silent continue. Cap value readable from environment or
config alongside the existing `CLAUDE_SKILLS_HOOK_PROFILE` controls.

### Measurable signal

`task_status_hook.py` reads a `max_tool_calls` value, increments a per-session counter on each
PostToolUse call, and the counter/cap is observable in the active-task context JSON
(`~/.dh/projects/{slug}/context/active-task-{session_id}.json`).

### What would raise confidence to High

Confirm with the user that a hard cap is wanted (the current strict-profile design is deliberately
non-blocking, so a cap contradicts a stated design choice and needs sign-off), and confirm the
PostToolUse handler does not already maintain a counter elsewhere.

---

## Skipped Patterns

| Pattern (Relevance section) | Reason skipped |
|---|---|
| #2 Policy-based governance (ALLOW/DENY/ASK declarative gates) | Already covered. `plugins/plugin-creator/skills/hooks-patterns/SKILL.md` documents PreToolUse `permissionDecision: allow` (lines 439–472), prompt-hook `{"ok": false, "reason"}` deny-with-feedback (lines 150–208), and `PermissionRequest` "intelligent allow/deny dialogs" (line 239) — the ALLOW/DENY/ASK trichotomy is already a first-class, better-integrated local capability. |
| #1 Harness abstraction (meta-layer over Claude Code/Codex/Cursor/Pi) | Not actionable. This is an architecture for abstracting multiple external runtimes; this repo is a Claude Code plugin marketplace, not a multi-harness meta-runtime. Adopting it would replace architecture, not extend a local system. |
| #3 Cross-device session sync (CLI/web/mobile) | Not actionable. Requires a FastAPI server + WebSocket persistence layer (ap-web, SQLAlchemy) that has no local equivalent to extend; incompatible with the plugin/skill architecture. |
| #4 Real-time multi-user collaboration / shared sessions | Not actionable. Same as #3 — depends on the server+persistence layer that does not exist locally. The swarm skills (`swarm-operations`, `swarm-patterns`) already cover multi-agent coordination within a single session; cross-user accounts are out of architectural scope. |
| #5 Custom YAML agent authoring (`name:` + `prompt:`) | Already covered / weaker external form. This repo's agent definition format (`agents/*.md` with frontmatter + body, created via `/plugin-creator:agent-creator`) is richer than Omnigent's two-field YAML. No gap. |
| #6 Model flexibility (Claude/OpenAI/gateway providers) | Not actionable here. Model selection for agent delegation is already governed by `.claude/rules/model-selection.md` (sonnet/opus/haiku tiers + effort). Multi-provider gateway support is a harness-runtime concern, not a skill/agent gap. |

---

## Notes

- The entry is high-confidence and well-sourced, but its actionable surface for *this repo* is
  narrow: five of six Relevance patterns describe a meta-harness/server architecture that this
  plugin marketplace does not and should not replicate. The only patterns naming a concrete,
  potentially-portable mechanism are the two policy built-ins (cost cap, tool-call cap), and both
  require a design decision (block vs warn) plus deeper source verification before they can be
  expressed as a directly observable before/after gap. Per the agent's gap rules, Medium-confidence
  gaps are deferred rather than backlogged.
