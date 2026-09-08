# Shared Agent Process Belongs in a Skill

Process or information that more than one agent follows lives in a skill those agents load. It is
never copied into each agent that needs it.

This covers anything an agent follows rather than decides: output formats, status messaging,
expected inputs, ways-of-working, definition-of-done, and procedures for resolving the
environment or configuration an agent runs against.

**Trigger**: writing into an agent file something another agent also needs, or noticing two agent
files say the same thing.

**Action**: create or extend a skill that owns it, delete the text from every agent carrying a
copy, and add the skill to each agent's `skills:` frontmatter list.

## The medium does not matter

A duplicated shell block and a duplicated paragraph are the same defect. Replacing copied code
with copied prose that points at the canonical source is not the fix — it is the same two copies,
free to drift, in a form that is harder to grep for.

The test is not "is this text executable". It is "does more than one agent need to follow this".

## Why

An agent file is reloaded on every dispatch, so a stale copy is not a one-time error — it is
wrong on every run until someone notices. Two copies of a procedure drift silently because
neither one is wrong on its own, and nothing compares them. A skill has one body, so correcting
it corrects every consumer at once, and adding a consumer costs a frontmatter line rather than a
paste.

## What stays in the agent

The agent keeps what is specific to its own assignment: what it is for, what it reads, what it
produces, and the judgement it applies. It loads the shared process rather than restating any part
of it — including a summary of it. A summary is a copy that has already begun to drift.

## Worked example: backend resolution

**What it was**: `agents/alignment-analyst.md` and `agents/impact-analyst.md` each carried the
same four-line shell heuristic for deciding which backlog backend was active. Both stopped at the
`BACKLOG_BACKEND` environment variable and a `.beads` directory, so both missed the configured
value in `.dh/config.yaml`, and both read a project that keeps a `.beads` directory for some other
purpose as a Beads backlog.

**The near-miss**: the first fix replaced the shell block in one agent with a paragraph naming the
canonical chain, then prepared to put the same paragraph in the other. That is two copies again.

**What it became**: a skill owning the resolution procedure, listed in the `skills:` frontmatter of
each agent that needs it. `docs/backend-providers.md` remains the canonical description of the
chain; the skill is the agent-facing procedure for following it.

## Precedent

`dh:subagent-contract` is listed in the `skills:` frontmatter of 27 of the development-harness
plugin's 29 agents. That is the shape: one body, many consumers, no copies.
