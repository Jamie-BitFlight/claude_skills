---
name: evaluate-and-tighten-skills
description: Generate a focused behavioral contract for an existing skill, then remove instructions that do not contribute to that behavior. Use before eval testing of a skill, use when optimizing skill token usage.
---

# Evaluate and Tighten Skills

Make an existing skill as light as possible without removing behavior that contributes to its purpose.

This is a **pre-eval pruning pass**. Do not run the skill's full benchmark or optimization loop here.

## Resolve the skill goals

Establish the target skill's goals before evaluating any of its prose.

Use the first available source:

1. Goal output explicitly supplied from `skill-goal-extractor`.
2. `<target-skill>/SKILL-GOALS.md`.
3. If neither exists, derive the goals by reading the complete skill and its materially referenced resources using the same goal-extraction standard.

Treat these goals as the purpose of the skill, not its current implementation. Instructions are allowed to disappear even when deliberately written if they do not contribute to those goals.

Goals must be resolved before pruning because they serve two purposes:

* define the behavior that must survive tightening;
* expose instructions or entire branches that are coherent in isolation but have drifted away from what the skill exists to achieve.

## Step 1: Generate the behavioral contract

Create a small set of evals describing the behavior that must survive pruning.

For each explicit goal, ask:

> What observable behavior would distinguish an agent that successfully gained this capability from one that merely received the user's task without this skill?

Inspect the skill's instructions, completion criteria, trigger behavior, scripts, references, and domain gotchas only to discover behavior necessary to achieve those goals.

Write only **discriminating evals**: removing behavior required by the skill should be capable of making at least one eval fail.

Cover only dimensions that materially matter:

* **Outcome** - what the agent must accomplish.
* **Process** - steps, tools, ordering, validation, or decision rules that materially affect the outcome.
* **Style/quality** - conventions whose absence changes the usefulness or correctness of the result.
* **Efficiency** - avoidance of meaningful token, tool, time, or context waste when efficiency is part of the skill's value.
* **Invocation** - for model-invoked skills, the distinct branches that should and should not cause the skill to load.

Do not create an eval merely because a sentence exists in the skill. The evals protect the skill's goals; they do not protect its current wording.

Keep the contract small. Prefer a few requirements that expose meaningful regression over exhaustive checks for incidental details.

Record:

```text
Behavioral contract for <skill_name>

Goal 1: <goal>
- E1: <observable requirement>
- E2: <observable requirement>

Goal 2: <goal>
- E3: <observable requirement>
```

The contract is complete when:

* every explicit goal has at least one discriminating check;
* every check protects behavior contributing to an explicit goal;
* no check exists solely to preserve current implementation detail.

## Step 2: Section-level goal alignment

Before sentence-level pruning, classify each section against the goals resolved above.

For each section, ask:

> Which explicit skill goal does this section or instruction help the executing agent achieve, and how?

Classify:

* **DIRECT** - directly causes behavior required by a goal.
* **SUPPORTING** - provides a decision principle, constraint, domain fact, or capability needed to achieve a goal across variable situations.
* **UNALIGNED** - does not materially contribute to any explicit goal.

Flag `UNALIGNED` sections for removal or relocation before tightening individual sentences. The skill should not preserve behavior merely because it already exists in the current implementation.

## Step 3: Counterfactual deletion pass

Read the complete skill section by section, including frontmatter and referenced instructional material.

For each sentence or independently removable instruction, first classify its function:

* **DOES** - specifies an action, decision, branch, validation, completion condition, output, or required lookup.
* **RESOLVES** - makes execution unambiguous: paths, substitutions, quoting, references, scope, or dependencies.
* **REASONS** - supplies a principle the agent needs to make a good decision where the correct action cannot be fully specified in advance.
* **EXPLAINS** - describes why an already-bounded instruction works, how it was implemented, its history, or why a choice already made for the agent was made.

`DOES`, `RESOLVES`, and `REASONS` may earn their load. `EXPLAINS` should be presumed removable unless its deletion changes expected behavior under the behavioral contract.

When prose gives a reason for an instruction, ask:

> Is the agent expected to reason from this information to choose an action in situations the skill cannot enumerate, or has the action already been fully chosen for it?

If the agent must choose among context-dependent paths, preserve the minimum reasoning principle needed to make that choice well. If the instruction is bounded and already determines the action, its rationale normally does not affect execution and should be removed.

```text
Commit changes between edits.
```

This is bounded. Explanation of why incremental commits are useful normally adds no behavior.

```text
Choose the smallest validation capable of disproving the change before running broader tests.
```

This is unbounded. The principle is operational because the agent must reason about the current change, available checks, cost, and failure risk.

Then ask:

> Is there anything in this sentence, in the context where it is used, that could be removed without changing the expected behavior of an agent following this skill under the behavioral contract?

Answer **YES** or **NO**.

### YES

Give the smallest deletion or replacement that preserves expected behavior.

Prefer deletion over rewriting. Prefer a shorter instruction over preserving its explanation.

```text
YES
Remove: "<text>"
Reason: <brief explanation of why protected behavior is unchanged>
```

When only part is necessary:

```text
YES
Replace:
"<current text>"

With:
"<smallest instruction preserving the behavior>"
```

### NO

```text
NO
```

No justification is required unless the dependency is non-obvious.

## What earns its place

Keep material when removing it could change:

* whether the skill is invoked on a required branch;
* an action the agent performs;
* a decision the agent makes;
* ordering where order affects the result;
* a completion criterion;
* validation or error detection;
* a required output property;
* a domain constraint or gotcha the base model cannot reliably infer;
* selection or correct use of a bundled script, tool, reference, or asset;
* behavior on a meaningful edge case covered by the contract;
* whether an instruction can actually be resolved and executed in the supported environment.

## Hunt these specifically

### No-ops

Look for:

* **Exposition attached to an instruction.** If the command is already unambiguous, explanation of why it works does not earn execution-context load.
* **Past-decision rationale.** "Use X instead of Y because Z" is unnecessary when the agent has no X/Y decision to make.
* **Reminders already encoded in the example.** If the fenced command contains the required quoting, spelling, or arguments, determine whether another sentence repeating them changes behavior.
* **Anti-reversion instructions aimed at another reader.** Ask who needs the information and whether that audience reads this document at the point where it matters.
* **Weak modifiers.** "Be thorough", "carefully", "make sure to", and similar language are no-ops when they do not beat default behavior. Replace them with a stronger leading word or checkable completion bound when behavior actually needs strengthening.

The test is model-relative:

> Does this instruction change expected behavior compared with the agent's default behavior?

If not, delete it.

### Duplication

Look for:

* the same fact stated twice in one file;
* a step pre-explaining something another step already states where it is acted upon;
* prose in the skill re-deriving behavior already owned by a script, configuration file, or referenced resource;
* reminders added after the underlying command or example was already corrected.

Keep each meaning at one authoritative location.

### Resolvability

Shorter is only equivalent when it remains executable.

Check:

* every required file pointer can be resolved from the agent's actual environment;
* commands containing substituted paths remain valid for supported installation paths;
* variables, aliases, helper names, and references used by an instruction have an available definition;
* moving reference behind progressive disclosure does not remove the pointer needed to find it.

Do not delete text carrying a dependency merely because that dependency looked obvious while reviewing it.

### Wrong home

Remove material whose audience or lifecycle belongs elsewhere:

* design history;
* alternatives considered;
* explanations of rejected approaches;
* maintenance commentary to future editors;
* anti-reversion notes whose relevant edit occurs in another file;
* human onboarding or explanatory prose that does not alter agent execution.

Move genuinely important architectural decisions to an existing appropriate source of truth such as an ADR, commit, PR, or maintainership documentation. Do not create new documentation merely to preserve trivia removed from a skill.

Explanatory material stays only when an agent that actually loads the document uses it to make a materially different decision.

### Structural load

Look for:

* reference material loaded on every execution when only one branch needs it;
* branch-specific gotchas that can sit behind a resolvable pointer;
* vague completion criteria such as "properly handled" or "understanding reached";
* negated instructions where the target behavior can be stated directly.

Prefer:

* inline instructions required by every path;
* disclosed reference for branch-specific material;
* observable completion criteria;
* positive executable instructions.

## Fastest filter

For every sentence ask:

> Does this tell the agent what to do, what outcome to reach, what it must resolve, or how to reason when the correct action depends on context - or does it only explain an action that has already been chosen?

Explanation is a deletion candidate by default.

Then run the counterfactual:

> If this text disappears, can any behavioral-contract eval reasonably produce a different result?

If **no**, remove it.

## Example

Load [references/example.md](./references/example.md) for a worked classification and reduction example.

## Step 4: Whole-skill preservation pass

After applying the accepted deletions, reread the **complete tightened skill** against the behavioral contract.

Local equivalence is insufficient if several individually safe deletions combine to remove a required behavior.

For every contract eval, identify where the tightened skill still supplies any behavior that the base agent cannot be expected to provide reliably.

If a requirement no longer has adequate support, restore the smallest instruction necessary.

Do not restore explanatory material merely because the original version contained it.

## Completion

Finish when:

1. every behavioral-contract requirement remains supported where explicit support is necessary;
2. no remaining sentence contains a removable part whose deletion is expected to preserve behavior;
3. pointers still expose every required branch without redundant trigger language;
4. scripts and references remain resolvable exactly where their behavior is needed;
5. no explanation remains solely to document how or why an already-unambiguous instruction works.

Return:

```text
Tightening complete: <skill_name>
Before: <word/token count>
After: <word/token count>
Reduction: <percentage>

Behavioral contract preserved: YES

Removed:
- <short description>
- <short description>

Uncertain:
- <only items whose behavioral effect requires empirical evaluation>

Goal deviations found:
- <behavior, section, or instruction that does not advance any explicit skill goal>
```

Report `Goal deviations found: none` when none are found.

`Uncertain` items become candidates for the subsequent full skill eval.

Do not delete uncertain behavior based on intuition, and do not permanently retain it based on intuition. Let the empirical eval determine whether it earns its load.
