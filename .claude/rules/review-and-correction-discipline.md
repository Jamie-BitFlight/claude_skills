# Review and Correction Discipline

Process rules for reviewing and correcting AI-facing instruction files (prompts, `SKILL.md`,
agent files, `*.md` rules, `CLAUDE.md`) and for acting on what review finds. These complement the
content rubric in the ensemble-rule-review skill's
[instruction-hygiene reference](../../plugins/plugin-creator/skills/ensemble-rule-review/references/instruction-hygiene.md);
this file governs the *gates and the orchestrator's behavior around them*, not the rubric itself.

## 1. Two orthogonal gates: structural ≠ content

Structural validation and content review are independent axes. Both are mandatory before shipping
an instruction file; passing one says nothing about the other.

- **Structural gate** — `skilllint`, `prek`, `ruff`, `ty`. Checks form: token thresholds,
  frontmatter schema, fence syntax, link validity, types. It is the lid that stops paint spilling
  from the can. It cannot tell you whether the paint covers the wall.
- **Content gate** — leak review, instruction-bias review, effectiveness and fit-for-purpose
  assessment. Checks substance: does the prose instruct the agent to do the right thing across its
  inputs and edge cases.

A file can pass every structural check and still instruct an agent incorrectly. "skilllint passed"
is never evidence of content quality. Never let a green structural gate stand in for the content
gate.

## 2. Run the review as a gate — a documented checklist is not a gate

A checklist that exists in a file but is not executed against the change protects nothing. Every
change to an instruction file must have the content review **actually run** against the diff before
ship — including changes you authored yourself and changes an agent produced.

The author is blind to their own leaks and decoration. Route the content gate to fresh eyes — a
separate review pass or agent — not the author's own re-read. Writing the rubric does not satisfy
the rubric.

**Wrong:** author `instruction-hygiene.md`, then ship edits to it gated only by `prek`.
**Right:** run the hygiene checklist against the diff (fresh-eyes for the judgment items) as a
required step, then ship.

## 3. Judgment review needs capable adjudication, not iterated cheap passes

Route each review check by its error structure, not by a fixed reviewer tier — mechanical checks to
cheap corroborating workers, judgment checks to capable heterogeneous reviewers, adjudicated once.
The full routing taxonomy lives in
[instruction-hygiene §6](../../plugins/plugin-creator/skills/ensemble-rule-review/references/instruction-hygiene.md)
(which routes onward to `candidate-fit.md`); do not restate it here.

The orchestrator action this adds: when a judgment review is wrong, escalate by **changing the
reviewer, not by re-running the cheap one**. Iterating a cheap homogeneous reviewer on a judgment
check produces over-flagging and run-to-run disagreement — a cheap leak-pass flagged
`Do NOT partition the rules` (a real arm procedure) as a leak and disagreed with its own prior run.

## 4. Match action to the ask; quiesce agents before committing

**Match action to the ask.** A clarifying question is not a work order. Answer what was asked.
Confirm before rebuilding, replacing a working component, or any architectural change.

- **Wrong:** asked "is this where the runner lives?" → rewrote the working Python runner as bash.
- **Right:** answer the question; if a change seems warranted, propose it and act on confirmation.

**Quiesce agents before committing.** Do not commit, lint, or stash while a background agent is
editing the same files — `prek`'s stash/restore races the agent's writes and produces partial
state. Confirm agents are idle — token count stable across two readings — then commit.

## Cross-references

- **Mechanism leaks** in task prompts, skills, and task files — the prompt is what a real user would
  type; schema, paths, model tier, and skill names live in the executor config. Provide CLEAR + CoVe
  instructions for the executing agent, not the system's implementation. See instruction-hygiene §1–2.
- **Custom agents only; verify their claims** — never use general-purpose agents for workers (they
  inherit ~100k tokens of tool/skill/MCP descriptions). Treat agent reports as claims, not facts:
  an agent that lacks execution tools cannot run a gate (the orchestrator runs it), and an agent's
  "not found" is often a wrong-directory confabulation — verify against primary source. See
  source-fidelity §4.

SOURCE: observed failures while de-biasing the ensemble-rule-review skill and building the SOLID
A/B harness (session 2026-06-03). Signed off "lint clean" on files carrying content leaks; authored
`instruction-hygiene.md` without running it against the same session's edits; iterated a cheap
leak-pass that flagged a real procedure and disagreed run-to-run; rewrote a working runner on a
clarifying question; held commits because background agents were mid-write. Each is a process error
that the rules above prevent.
