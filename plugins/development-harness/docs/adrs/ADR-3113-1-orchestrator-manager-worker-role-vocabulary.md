# ADR-3113-1: Orchestrator, manager, and worker are three roles, not one capability

**Status:** Accepted
**Date:** 2026-08-22
**Issue:** [#3113](https://github.com/Jamie-BitFlight/claude_skills/issues/3113), incident: [#3060](https://github.com/Jamie-BitFlight/claude_skills/issues/3060)
**Related:** [#3099](https://github.com/Jamie-BitFlight/claude_skills/issues/3099) (per-task failure
policies, including executor-loss), [#3100](https://github.com/Jamie-BitFlight/claude_skills/issues/3100)
(executor-type declaration on the SAM task schema — the eventual typed-data formalization of the
vocabulary this ADR establishes in prose)

## Context

During #3060's implementation, a dispatched agent (`work-3060`) delegated the entire
`dh:implement-feature` skill invocation to a `dh:task-worker` subagent instead of running it
inline in its own context. `implement-feature/SKILL.md` is written in first person for "the
orchestrator": query ready tasks, dispatch via `TeamCreate`, run one `dh:task-worker` per ready
task. The receiving task-worker complied with that borrowed voice literally — it loaded and
executed `dh:implement-feature`'s dispatch loop, itself spawning a team of further task-workers
and a contract-verification agent. Cost: roughly $100 of unplanned spend before the pattern was
caught and stopped.

Two independent gaps produced this, confirmed by direct transcript forensics (not inferred):

1. **`implement-feature/SKILL.md` uses "the orchestrator" to mean "whoever is executing this
   skill."** That phrasing was never ambiguous until recently: subagents dispatching further
   subagents is a platform capability added within the last ~8 weeks, newer than this workflow.
   Before that capability existed, only the top-level interactive session could ever be in a
   position to execute a skill written in this voice, so there was nothing to disambiguate. The
   docs were never revisited against the new capability.
2. **`task-worker.md`'s Identity section provides no resistance to executing orchestrator-voiced
   content it's handed, and actively discourages the pushback that should catch this.** Its text —
   "you become whatever the task requires by loading the right skills... your job is to do the
   work — not to ask the manager how to do it" — places no restriction on which skills are
   appropriate to load, and directly forecloses questioning an instruction to load and fully
   execute a skill written for a different role.

A live, verifiable distinction underlies both gaps: the interactive Claude Code session's own
system prompt opens "You are Claude Code... an interactive agent that helps users." A dispatched
subagent's system prompt carries no such framing — confirmed by direct comparison this session,
not assumed. The orchestrator/subagent boundary is not a convention this ADR invents; it already
exists structurally. The plugin's prose was simply not consistent with it.

**Sub-dispatch itself is not the defect.** A subagent dispatching further subagents, when planned
by whoever dispatched it, is a legitimate and valuable decomposition pattern — the platform
capability that makes it possible is new, not wrong. The actual defect is narrower: a subagent
*inferring* a coordinating role for itself from a skill's authorial voice, rather than being
*explicitly assigned* that role by its own dispatcher.

**Cross-harness constraint.** This plugin targets Claude Code, Codex, and OpenCode. The one
role-detection mechanism verified this session (comparing system-prompt first lines) is
Claude-Code-specific and not a sanctioned runtime mechanism even there — it was a diagnostic
probe, not something plugin prose can instruct an agent to do. Any fix that relies on an agent
introspecting its own environment to determine its role does not port across harnesses and
should not be built. The fix below relies on none of that: role is asserted by the dispatcher and
stated in the dispatch prompt, which every harness's delegation mechanism already carries a place
for.

## Decision

Three roles, defined by relationship to the human and to the dispatcher — not by capability, and
not by whether an agent happens to dispatch further work:

- **Orchestrator** — the single interactive agent acting directly on behalf of the human. Exactly
  one per session. Never inferred, never a subagent, regardless of what that subagent itself goes
  on to dispatch.
- **Manager** — a subagent explicitly assigned, by its own dispatcher, to decompose a scoped piece
  of work and dispatch further subagents within that scope. The assignment must be stated in the
  delegation prompt (or, once #3100 lands, in the SAM task's `executor` field) — never inferred
  from a loaded skill's own voice, and never adopted on the subagent's own initiative. Acts on
  behalf of whoever assigned it the scope, not on behalf of the human directly.
- **Worker** — a subagent assigned one unit of work to execute directly, whether that assignment
  is a SAM task or a direct prompt with no SAM reference (`dh:task-worker` is dispatched both ways
  throughout the plugin — see AGENTS.md's Dispatch Pattern, "used for every agent dispatch — no
  exceptions"). A Worker's assignment may explicitly name a specific skill to invoke, including one
  that itself dispatches a fixed, bounded set of subagents to complete that one unit of work — a
  quality-gate task naming `dh:multi-perspective-review`, which fans out four reviewers, is the
  Worker's assignment, not a coordinating role it inferred. What a Worker never does is
  independently drive an open-ended, multi-round dispatch loop across an entire plan — deciding
  what's ready, batching, and repeatedly spawning further task-workers as the plan progresses —
  that requires the Manager role, explicitly assigned. On receiving an instruction to run a
  plan-managing skill it was not assigned to run, a Worker reports the conflict (`STATUS: BLOCKED`)
  instead of complying. `dh:task-worker` is this plugin's canonical Worker implementation.

Role is always explicit, asserted by the dispatcher, carried as data in the delegation prompt —
never detected by an agent introspecting its own harness or environment. This is what makes the
definitions portable across Claude Code, Codex, and OpenCode: nothing about "am I the orchestrator,
a manager, or a worker" depends on a mechanism any one harness happens to expose.

This vocabulary is written into `CONTEXT.md` as the plugin's authoritative definition (single
source of truth — skills reference the terms, they do not restate the definitions). `task-worker.md`
is rewritten to state the Worker role's boundary explicitly — execute the assignment as given,
including a specific skill the assignment names, but never independently drive a plan's dispatch
loop — rather than the open-ended "become whatever is needed" it carried before. `post-planning.md`
gets an explicit warning at the one confirmed instance of this incident's proximate cause:
`dh:implement-feature`'s invocation runs inline in the orchestrating agent's own context and must
never be copied into a delegation prompt for a task-scoped subagent.

**Revised during PR review (#3114), confirmed against source before accepting.** The first draft
of the Worker definition and `task-worker.md`'s rewrite stated a closed SAM-task-only job
enumeration with no dispatch of any kind. Two independent review findings, each verified against
the actual referenced source before this revision was made, showed that was too narrow and would
have broken existing, intentional behavior: (1) `AGENTS.md` (`plugins/development-harness/AGENTS.md`,
"Dispatch Pattern" section) states `dh:task-worker` is dispatched with a direct prompt and no SAM
task reference throughout the plugin — confirmed against `groom/error.md` (a diagnostic-review
dispatch) and `groom-backlog-item/references/drift-check.md` (a plan-drift analysis dispatch),
neither of which has any SAM task to read; (2) the quality-gate Phase 0 task
(`sam_schema/core/quality_gates.py`'s `_phase_body`) explicitly instructs its task-worker to invoke
`dh:multi-perspective-review`, which fans out four reviewer agents by design — a legitimate,
bounded, assignment-named fan-out, not the open-ended role self-assignment this ADR exists to stop.
The definitions above reflect the corrected, narrower boundary: what's prohibited is independently
driving a plan's dispatch loop, not dispatch in any form.

**Revised again during the same PR review, confirmed against source before accepting.** A third
finding showed the "direct prompt" bucket was still too narrow: `close/start.md`'s Step 5.5
dispatches `dh:task-worker` with a plan address (e.g. `P{id}`) for an acceptance-criteria
verification, but no task ID — a caller that fits neither "SAM task reference" (no task ID present)
nor the prior wording of "direct prompt... with no plan/task ID attached" (a plan address *is*
present). The Worker definition and `task-worker.md` are corrected again: the deciding signal is
whether a task ID is present to delegate to `start-task`, not whether any plan reference appears at
all. A direct prompt may legitimately carry a plan address for read-only reference.

This same PR review also flagged Claude-Code-specific tool names (`TeamCreate`, `SendMessage`,
literal `Skill(skill="...")` call syntax) surviving in `task-worker.md`'s frontmatter and
Completion Report — this plugin targets Claude Code, Codex, and OpenCode, and prose describing what
a Worker does should name the capability (dispatch as part of a coordinated group, report back to
the group's lead) rather than one harness's specific tool. Corrected in the same pass.

## Consequences

- `task-worker.md`'s Identity section changes from an open self-concept ("become whatever the task
  requires") to a stated boundary: execute the assignment as given — a SAM task via `start-task`,
  or a direct prompt naming a specific skill, including one that fans out its own fixed subagents —
  but never independently drive a plan's multi-round dispatch loop. Explicit BLOCKED routing
  replaces language that discouraged surfacing a role conflict.
- `implement-feature/SKILL.md` itself is not rewritten by this ADR — its "orchestrator" language is
  correct when the skill runs in the orchestrator's or an assigned manager's own context, which is
  the only way it is designed to run. The gap this ADR closes is that nothing previously stopped
  that invocation from being handed to a Worker instead; `post-planning.md`'s new warning addresses
  the one place this session confirmed that actually happened. A broader sweep of "orchestrator"
  usage across the rest of the plugin (458 hits across ~70 files, audited but out of scope here) is
  tracked separately, not resolved by this ADR.
- #3100's `executor` field, once implemented, becomes the typed-data backing for the Manager/Worker
  distinction this ADR defines in prose; this ADR's definitions are the vocabulary that field must
  match, not superseded by it.
- No tool-permission change accompanies this ADR. `task-worker.md` intentionally carries no
  restricted `tools:` list — it must be able to adopt the full capability set of whatever
  specialist profile `profile_load` injects, which a static allowlist would break. The safety
  mechanism here is entirely behavioral (the stated role boundary and the BLOCKED path), not
  structural.

## Considered alternatives

**Restrict `task-worker.md`'s `tools:` frontmatter to exclude `Agent`/`TeamCreate`/`EnterWorktree`**
(defense-in-depth, proposed during incident triage): rejected as the primary fix, and dropped
entirely as a secondary one — confirmed by the repo owner. `task-worker` is designed to act with
whatever capability set the specialist profile it loads via `profile_load` requires; hardcoding a
restricted list on the base agent works against that design, not alongside it, and `profile_load`
only injects text into context — it does not adjust the actual runtime tool grant per profile — so
there is no clean mechanism today to scope tools per-task even if desired.

**Detect role via harness/environment introspection** (e.g., an agent checking its own system
prompt or a harness-specific signal to determine if it's top-level): rejected. Confirmed
Claude-Code-specific and not a sanctioned mechanism even within Claude Code; would require separate,
unverified detection logic per harness (Codex, OpenCode) with no guarantee of staying correct as
each harness's subagent model evolves independently. Explicit dispatcher-stated role, carried as
prompt/plan data, achieves the same goal without depending on any harness's internals.

**Rewrite every "orchestrator" occurrence across the plugin in this pass** (458 hits, ~70 files):
rejected for this ADR's scope. The incident's proximate cause is fully addressed by the four files
this decision touches; a plugin-wide terminology sweep is real work but independent, larger, and
better tracked as its own item rather than expanding this one past what the incident evidence
actually required.
