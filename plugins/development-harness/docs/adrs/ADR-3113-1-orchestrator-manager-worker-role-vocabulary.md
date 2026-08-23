# ADR-3113-1: Dispatch roles name scope, not capability, and enforcement sits with the dispatcher

**Status:** Accepted
**Date:** 2026-08-22
**Issue:** [#3113](https://github.com/Jamie-BitFlight/claude_skills/issues/3113), incident: [#3060](https://github.com/Jamie-BitFlight/claude_skills/issues/3060)
**Related:** [#3099](https://github.com/Jamie-BitFlight/claude_skills/issues/3099) (per-task failure
policies, including executor-loss), [#3100](https://github.com/Jamie-BitFlight/claude_skills/issues/3100)
(executor-type declaration on the SAM task schema)

## Context

During #3060's implementation, a dispatched agent (`work-3060`) delegated the entire
`dh:implement-feature` skill invocation to a `dh:task-worker` subagent instead of running it
inline in its own context. `implement-feature/SKILL.md` is written in first person for "the
orchestrator": query ready tasks, dispatch one `dh:task-worker` per ready task, repeat. The
receiving task-worker complied with that borrowed voice literally — it loaded and executed
`dh:implement-feature`'s dispatch loop, itself spawning a team of further task-workers and a
contract-verification agent. Cost: roughly $100 of unplanned spend before the pattern was caught
and stopped.

Two facts about the incident were confirmed by direct transcript forensics, not inferred:

1. `implement-feature/SKILL.md` uses "the orchestrator" to mean "whoever is executing this
   skill." That phrasing was unambiguous until recently: subagents dispatching further subagents
   is a platform capability added within the last ~8 weeks, newer than this workflow. Before it
   existed, only the top-level interactive session could ever execute a skill written in that
   voice, so there was nothing to disambiguate. The docs were never revisited against the new
   capability.
2. The invocation was handed to a subagent by the agent holding it. The subagent received a
   free-prose delegation string naming a plan-level skill, and had no information distinguishing
   that string from any other assignment it might legitimately receive.

**Sub-dispatch is not the defect.** An agent decomposing its own assignment into subagents is
ordinary problem-solving and must stay available to every agent. The defect is narrower: an
assignment was handed down that re-entered the workflow level which produced it, restarting a
loop whose earlier round was still in flight.

**Cross-harness constraint.** This plugin targets Claude Code, Codex, and OpenCode. The one
role-detection mechanism verified during triage (comparing system-prompt first lines) is
Claude-Code-specific and was a diagnostic probe, not a sanctioned runtime mechanism even there.
Any fix requiring an agent to introspect its own environment to determine its role does not port
across harnesses and is not built here.

## Decision

The invariant is scope, and it is stated once, in prose, at the place that can act on it:

**An agent's assignment must not re-enter the workflow level that produced that assignment.**

Enforcement sits with the dispatching agent, never the receiving one. The dispatcher can directly
observe the condition the rule names — it is holding the invocation and deciding whether to run it
itself or hand it over. The receiver cannot: a dispatched agent has no observable signal telling it
which workflow level dispatched it, and this ADR rejects building one (see Considered
alternatives). A constraint the actor cannot observe is unenforceable, so it is written where the
actor can observe it.

Concretely, `post-planning.md` — the one place transcript forensics confirmed this incident's
proximate cause — instructs the agent holding the `dh:implement-feature` invocation to run it
inline and never copy it into a delegation prompt. That instruction sits with the agent about to
make the call, and states the observable condition ("am I about to hand this invocation to someone
else?"), not an unobservable one.

`CONTEXT.md` carries the vocabulary — Orchestrator, Manager, Worker — redefined by the scope an
assignment covers rather than by any capability a role holds:

- **Orchestrator** — the single interactive agent acting on behalf of the human; its assignment is
  the human's request in full.
- **Manager** — an agent whose assignment covers a scoped body of work and its decomposition.
- **Worker** — an agent whose assignment covers one unit of work. `dh:task-worker` is this
  plugin's canonical Worker implementation.

`CONTEXT.md` is a design-time document about the plugin and is not loaded by the plugin's agents at
runtime, which makes it the correct home for vocabulary and the wrong home for enforcement. The
runtime-facing counterpart is the `dh:dispatch-contract` skill, whose framing this vocabulary
matches: the dispatcher passes a task reference and does not choose a specialist; the dispatched
agent reads the task and resolves its own agent profile from it.

`task-worker.md` carries no role prose at all. Its Identity section states what the agent is for
("you become whatever the task requires by loading the right skills") and nothing about workflow
levels, permissions, or what it may not be asked to do.

## Considered alternatives

**Split the roles by capability — a Manager may dispatch, a Worker may not.** Rejected. Nothing was
ever gated: no tool grant, no schema field, no runtime check distinguished the two, so the split
existed only as prose asserting a difference the system did not implement. Worse, it encodes
capability as identity, and decomposing one's own assignment into subagents is ordinary
problem-solving that must remain available to every agent. The mirror-image fix — a sentence
granting permission to subdivide — is equally rejected: it reads as instruction, and changes
nothing an agent would not already have done.

**Write the constraint as receiver-side prose in `task-worker.md`.** Tried on the first pass of
this branch and rejected. The added Identity block named the agent a Worker, enumerated its
assignment forms, carved out an exception for assignments naming skills that fan out, and told it
to report `STATUS: BLOCKED` on receiving a plan-managing skill. Every one of those clauses asks the
agent to classify a condition it cannot observe — whether the instruction in front of it came from
the level it would be re-entering. The exception carve-outs are the symptom: each one exists
because a legitimate dispatch pattern (`dh:multi-perspective-review`'s four-reviewer fan-out;
`close/start.md`'s plan-address-with-no-task-ID verification dispatch, both verified against source
during PR review) collided with a rule stated in terms the receiver has no way to evaluate. Prose
that needs an exception per legitimate caller is a rule written in the wrong place.

**Restrict `task-worker.md`'s `tools:` frontmatter to exclude agent-dispatch capabilities.**
Rejected, confirmed by the repo owner. `task-worker` must be able to adopt the full capability set
of whatever specialist profile `profile_load` injects; a static allowlist on the base agent works
against that design. `profile_load` only injects text into context — it does not adjust the runtime
tool grant per profile — so there is no mechanism today to scope tools per-task even if it were
wanted.

**Detect role via harness or environment introspection** (an agent checking its own system prompt
or a harness-specific signal to determine whether it is top-level): rejected. Claude-Code-specific,
not sanctioned even within Claude Code, and would require separate unverified detection logic per
harness with no guarantee of staying correct as each harness's subagent model evolves.

**Rewrite every "orchestrator" occurrence across the plugin in this pass** (458 hits, ~70 files):
rejected for this ADR's scope. The incident's proximate cause is addressed by the files this
decision touches; a plugin-wide terminology sweep is real work but independent and larger, better
tracked as its own item.

## Consequences

- Prevention exists at exactly one confirmed site (`post-planning.md`) rather than as a general
  behavioural rule carried by every dispatched agent. Other sites that hand off a plan-level
  invocation are not covered by this ADR and must each carry the instruction at the dispatching
  agent, in the same form, when found.
- `implement-feature/SKILL.md` is not rewritten here. Its "orchestrator" voice is correct when the
  skill runs in the context of an agent whose assignment covers the plan, which is the only way it
  is designed to run. What this ADR closes is that nothing stopped that invocation from being
  handed onward.
- No tool-permission change accompanies this ADR, and no capability is gated for any agent.
- #3100's executor-type field, once implemented, gives the dispatcher typed data to state scope
  with instead of free prose. That is the natural extension of this decision: the dispatcher
  already owns the constraint, and the field gives it a machine-checkable place to put it.
