# Shared Agent Process Belongs in a Skill

Process or information that more than one agent follows lives in one skill, and each agent that
needs it reaches that skill through its `skills:` frontmatter list. This covers anything an agent
follows rather than decides: output formats, status messaging, expected inputs, ways-of-working,
definition-of-done, and procedures for resolving the environment or configuration an agent runs
against.

**Trigger**: writing into an agent file something another agent also needs, or noticing two agent
files say the same thing.

**Action**: create or extend the skill that owns the process, list it in the `skills:` frontmatter
of every agent that needs it, and cut the process text out of each of those agents. Done when a
grep for a distinctive phrase of the process returns the skill alone.

## A copy is any second rendering

A *copy* is the process appearing a second time anywhere, in any medium: a pasted shell block, a
paragraph paraphrasing it, a one-line summary, a sentence that restates what the skill says before
pointing at it. The question that settles each case is whether more than one agent needs to follow
the text, not whether the text is executable.

A summary is the copy that hides best: shorter than the original, and already drifted the moment
the original changes.

## Why

An agent file is reloaded on every dispatch, so a stale copy is wrong on every run until someone
notices. Two copies drift silently — neither is wrong on its own, and nothing compares them. A
skill has one body, so correcting it corrects every consumer at once, and adding a consumer costs
a frontmatter line.

## What stays in the agent

The agent keeps what is specific to its own assignment: what it is for, what it reads, what it
produces, and the judgement it applies. For everything shared, it names the skill and lets the
skill speak.

## Worked example: backend resolution

[`alignment-analyst.md`](plugins/development-harness/agents/alignment-analyst.md) and
[`impact-analyst.md`](plugins/development-harness/agents/impact-analyst.md) each carried the same
four-line shell heuristic for deciding which backlog backend was active, and both were wrong in
the same two ways.

The first fix replaced the shell block in one agent with a paragraph naming the canonical chain,
and prepared to put that paragraph in the other — two copies again, in a form harder to grep for.

Both agents now list `dh:backend-resolution` in `skills:`, and each body says one sentence — resolve
the backend by following that skill — at the point where it matters.
[`backend-resolution/SKILL.md`](plugins/development-harness/skills/backend-resolution/SKILL.md)
holds the chain, the two heuristics that got it wrong, and what to do with the answer.

That shape is already the norm here: `grep -l subagent-contract plugins/development-harness/agents/*.md`
shows one skill body serving nearly every agent in that plugin.
