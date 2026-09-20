# Review and Correction Discipline

Process rules for reviewing and correcting AI-facing instruction files (prompts, `SKILL.md`,
agent files, `*.md` rules, `CLAUDE.md`) and for acting on what review finds. These complement the
content rubric in the ensemble-rule-review skill's
[instruction-hygiene reference](plugins/plugin-creator/skills/ensemble-rule-review/references/instruction-hygiene.md);
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
[instruction-hygiene §6](plugins/plugin-creator/skills/ensemble-rule-review/references/instruction-hygiene.md)
(which routes onward to `candidate-fit.md`); do not restate it here.

When a judgment review is wrong, escalate by **changing the reviewer, not by re-running the cheap
one**. Iterating a cheap homogeneous reviewer on a judgment check produces over-flagging and
run-to-run disagreement on the same input.

## 4. Match action to the ask; quiesce agents before committing

**Match action to the ask.** A clarifying question is not a work order. Answer what was asked.
Confirm before rebuilding, replacing a working component, or any architectural change.

- **Wrong:** asked "is this where the runner lives?" → rewrote the working Python runner as bash.
- **Right:** answer the question; if a change seems warranted, propose it and act on confirmation.

**Quiesce agents before committing** (see `commit-cadence-and-worktrees.md`'s prek stash/restore race) — confirm agents are idle (token count stable across two readings) before committing.

## Cross-references

- **Mechanism leaks** — read
  [instruction-hygiene §1–2](plugins/plugin-creator/skills/ensemble-rule-review/references/instruction-hygiene.md)
  before writing or reviewing any task prompt, skill, or agent file: what belongs in the prompt
  versus the executor config, and when a skill narrates itself instead of the reader's task.
- **Custom agents only; verify their claims** — never use general-purpose agents for workers (they
  inherit ~100k tokens of tool/skill/MCP descriptions). Treat agent reports as claims, not facts:
  an agent that lacks execution tools cannot run a gate (the orchestrator runs it), and an agent's
  "not found" is often a wrong-directory confabulation — verify against primary source.

## What belongs in `AGENTS.md`

Every agent reads `AGENTS.md` in full, for every task. It tells the agent where to find what a
task needs, rather than handing over the data itself — a pointer costs its own line; inline data
costs every task, whether or not the convention applies.

Route a new convention by what selects it:

- **A path-based condition** (a file extension, a directory) — give it a rule file with a
  `rules/manifest.json` glob. The hook delivers the file the moment an agent touches a matching
  path, and it costs nothing on every other task.
- **A runtime-state condition a glob cannot express** (a TTY error, a confirmed hypothesis, a
  prompt naming a product, a write above a size estimate) — give it a rule file and a trigger line
  under `AGENTS.md`'s "Situational Rule Triggers" heading, naming the condition and the file to
  read.

Write it inline only when no branch selects it — the convention applies identically to every task,
with nothing to route on. That is the same test that decides where any material sits on the
information hierarchy: inline what every branch needs, push behind a pointer what only some
branches reach.
