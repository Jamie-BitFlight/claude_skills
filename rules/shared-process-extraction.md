# Shared Agent Process Belongs in a Skill

Process or information that more than one agent follows lives in one skill, and each agent that
needs it reaches that skill through its `skills:` frontmatter list. This covers anything an agent
follows rather than decides: output formats, status messaging, expected inputs, ways-of-working,
definition-of-done, and procedures for resolving the environment or configuration an agent runs
against.

**Trigger**: writing into an agent file something another agent also needs, or noticing two agent
files say the same thing.

**Action**: create or extend the skill that owns the process. If the copy sits in an agent file,
list the owning skill in that agent's `skills:` frontmatter and cut the process text from the
agent. If the copy sits in another skill's `SKILL.md`, replace the restated process with a
cross-reference to the owning skill (e.g. "activate `/plugin:skill-name`") and cut the restated
text. Done when a grep for a distinctive phrase of the process returns the skill alone.

## A copy is any second rendering

A *copy* is the process appearing a second time anywhere, in any medium: a pasted shell block, a
paragraph paraphrasing it, a one-line summary, a sentence that restates what the skill says before
pointing at it. The question that settles each case is whether more than one agent needs to follow
the text, not whether the text is executable.

A summary is the copy that hides best: shorter than the original, and already drifted the moment
the original changes.

## What stays in the agent

The agent keeps what is specific to its own assignment: what it is for, what it reads, what it
produces, and the judgement it applies. For everything shared, it names the skill and lets the
skill speak.
