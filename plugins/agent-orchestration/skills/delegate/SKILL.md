---
name: delegate
description: Decompose substantive work into phases, dispatch each phase to a sub-agent, and adjudicate what comes back. Use whenever a request asks for implementation, investigation, a fix, a review, or any change to files — including small ones — and whenever you are about to read source or run a diagnostic yourself instead of handing it off. Also use when a report from a sub-agent needs judging, when a phase needs re-dispatching, or when a user names one instance of a pattern. Does not apply when your own prompt begins "Your ROLE_TYPE is sub-agent." — then follow references/sub-agent-contract.md instead.
---

# Delegate

The orchestrator's context is the one window that lasts the whole session. Every file it reads and every command output it holds is judgment budget spent. Sub-agents get a fresh window per task, so the orchestrator routes, defines done, and judges; the agents read, run, and write.

## Two roles

Every dispatch prompt opens with `Your ROLE_TYPE is sub-agent.` That line is an anti-recursion marker: a sub-agent that inherits this skill must not fan out further. If your prompt opened that way, stop here and follow [references/sub-agent-contract.md](references/sub-agent-contract.md). Otherwise you are the delegator and the rest of this file applies.

## When this applies

Any request that changes files, investigates a cause, gathers facts, fixes a bug, or reviews work — regardless of size — and any moment you are about to read source or run a diagnostic yourself instead of handing it off. "It's only two lines" is delegated. The one exception: a check scoped to a single file you edited yourself this turn.

Also applies once work is underway: judging a sub-agent's report (see Adjudicate), re-dispatching a phase, or generalizing a user-named pattern instance (see Pattern expansion).

Answer inline when the answer is already in your context and no file changes.

## Decompose

Split the request into phases. Keep only the phases that produce work; never pad.

| Phase | Produces |
| --- | --- |
| read | The material the work depends on, located and read |
| gather | External facts: docs, prior art, current system state |
| process | The analysis and the chosen approach |
| verify | The approach checked against the real code and environment |
| write | The change |
| validate | Lint, type-check, build results |
| test | Test runs, plus new tests covering the change |
| report | What changed, with evidence |
| review | Independent critique of the result |

Two shapes recur and have their own handling:

- **Bug fix** → [references/fix-cycle.md](references/fix-cycle.md): reproduce before changing.
- **Same edit across many targets** → one `process` dispatch decides the change; N generic dispatches apply it; one `review` dispatch checks. See [parallel-work](../parallel-work/SKILL.md).

## Dispatch

- One phase per dispatch. A phase may fan out across N targets (N dispatches, same phase); it never blends with another phase.
- Send independent dispatches together in one turn so they run concurrently. Serialize only where one consumes another's result, or two would write the same file without isolation.
- Results from `read`/`gather`/`process` go to a file, not into your context. Pass the path to the next phase; do not forward the content.

### Pick the agent

Classify by what the task asks of the agent, not by its name:

- **Specialist** — any agent whose description matches the phase's domain. Gets observations, success criteria, and context. Never gets implementation steps.
- **Generic** — `general-purpose` (or the harness equivalent) and `Explore`. Gets a prescribed implementation: exact edit, exact files, exact verification. `Explore` only for exact-match search.
- **Reviewer** — for the `review` phase, an agent different from the one that wrote, preferring a reviewer- or auditor-typed agent for the domain.

When no specialist fits, dispatch generic with a prescribed task.

### Prompt — specialist mode

```text
Your ROLE_TYPE is sub-agent. Follow the sub-agent contract at <absolute path to references/sub-agent-contract.md>.

PHASE: <one of the phase names>
TASK: <one sentence>

OBSERVATIONS:
- <facts already in your context: user statements, prior STATUS reports, verbatim errors, file:line if known>

DEFINITION OF SUCCESS:
- <measurable outcome>
- <acceptance criteria>
- <how it is verified — a command and its expected result, or the reviewer that will check>

DELIVERY:
- Return STATUS as the first line. Write anything longer than a line to .tmp/scratch/reports/<YYYYMMDD>-<slug>.md and return the path.

CONTEXT:
- Location: <where to look>
- Scope: <boundaries>
- Constraints: <user-mandated requirements; existing patterns to follow>
- Commands: <the project's quality gates for validate/test, or "discover the ones this project defines">

ECOSYSTEM CONTEXT:  (omit the section if empty)
- <session facts the agent cannot read anywhere: authenticated CLIs, a PR under review, another agent live on the same files>

YOUR TASK:
<the phase's row from the table below, verbatim>
```

Phase rows for `YOUR TASK`:

| Phase | Row |
| --- | --- |
| read | Locate and read the material this work depends on. Write exact paths and quoted content to the delivery file; do not summarize away detail a later phase needs. Edit nothing. |
| gather | Collect the external facts named in CONTEXT. Record each with its source in the delivery file. Edit nothing. |
| process | Analyze the material at the paths in OBSERVATIONS. Choose an approach; record it and why alternatives were ruled out. Edit nothing. |
| verify | Check the chosen approach against the real code and environment in CONTEXT. Record where it holds and where it fails. Implement nothing. |
| write | Make the change in DEFINITION OF SUCCESS. Touch only files within CONTEXT Scope. |
| validate | Run the commands in CONTEXT Commands, or discover this project's lint/type/build gates and state which you ran. Report exact output, pass and fail. A silenced failure is a failure. |
| test | Run the test invocation in CONTEXT Commands, or discover it and state which you ran. Add tests covering the change. Report exact output. |
| report | State what changed and the evidence for it: files, commands, outputs. Make no claim the evidence does not support. |
| review | Critique the result at the path in OBSERVATIONS against DEFINITION OF SUCCESS. Report gaps, contradictions, unsupported claims. Fix nothing. |

Rules for filling it in:

- A section you cannot fill from what is already in your context is omitted, not invented. Empty OBSERVATIONS or ECOSYSTEM CONTEXT is a valid state; a guess is not.
- OBSERVATIONS is pass-through: only what is already in your context. Reading, grepping, or running commands to fill it is pre-gathering; the agent does that with a fresh window.
- State observations as facts ("exit code 1", "the error text is: …"). Where you hold a hypothesis, label it: `Hypothesis to verify: …`.
- Constraints are outcomes and boundaries, never steps. Naming the project's own gate in Commands is a constraint, not a step.
- Say nothing the agent inherits: repo conventions, toolchain, "explore freely", "use available skills". Those live in the project's agent instructions. Name a skill only when the agent must load it and would not on its own.
- Paths: written as the agent will resolve them from its own working directory; relative inside the repo, and the symlink form (not the resolved target) for anything reached through a symlink.

### Prompt — generic mode

```text
Your ROLE_TYPE is sub-agent. Follow the sub-agent contract at <absolute path to references/sub-agent-contract.md>.

PHASE: <write | validate | test | read>
TASK: <the exact instruction — the edit to make, the pattern to find, the command to run>

FILES:
- <exact paths>

DEFINITION OF SUCCESS:
- <the verification command and its expected result>

DELIVERY:
- Return STATUS as the first line, with the verification output.
```

## Adjudicate

Reports are claims. For each one:

- Check that the evidence supports the conclusion. "Tests pass" without the command output is not evidence; re-dispatch for the output.
- Judge the returned work; do not re-derive it. Re-reading what the agent read spends the context that delegating saved.
- Two reports conflict → find the falsifiable claim and dispatch a check for it. Confidence is not a tiebreaker.
- `PARTIAL` → re-dispatch the remainder, naming exactly what is left.
- `BLOCKED` on a missing input → supply it and re-dispatch. `BLOCKED` after attempts → change the approach or escalate to the user; do not resend the same prompt.

Re-dispatch the same phase at most twice on the same gap. After that, stop and report `BLOCKED` to the user with the gap named.

Every request that changed code gets an independent review, from a reviewer other than the writer.

## Pattern expansion

A user pointing at one instance of a smell, bug, or missing check is naming a pattern. Unless they said "only this one": dispatch an audit of the whole file or module for the pattern, report the instances found, and confirm with the user before fixing beyond the named file.

## Pointers

- [references/sub-agent-contract.md](references/sub-agent-contract.md) — what dispatched agents follow.
- [references/fix-cycle.md](references/fix-cycle.md) — the reproduce-first cycle for bug-fix dispatches.
- [parallel-work](../parallel-work/SKILL.md) — fan-out, fan-in, maker/checker, tournaments, loops with caps.
- [references/harness-notes/claude-code.md](references/harness-notes/claude-code.md) — Claude Code mechanics; open only when running there.
- `orchestrator-discipline` plugin — what the orchestrator may read and run; enforced by hooks.
- `process-siren` plugin — writing decision points as evaluable Mermaid diamonds.
