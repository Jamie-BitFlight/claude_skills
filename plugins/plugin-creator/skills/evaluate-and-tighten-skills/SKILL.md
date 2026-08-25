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

`SKILL-GOALS.md` contains only capabilities or outcomes this skill specifically exists to add. Exclude generic competent-agent behavior such as accuracy, thoroughness, following instructions, or using tools correctly unless the skill gives those concepts a domain-specific meaning.

Goals describe what must remain true. They do not document how the current skill achieves it.

Goals must be resolved before pruning because they serve two purposes:

* define the behavior that must survive tightening;
* expose instructions or entire branches that are coherent in isolation but have drifted away from what the skill exists to achieve.

### Existing maintenance context

If `<target-skill>/MAINTENANCE.md` exists, read it before pruning.

Treat it as maintainer-facing context, not as another source of skill goals or runtime instructions. It may identify current invariants, regression provenance, authoritative sources, or evaluation uncertainties that matter when changing the skill.

An entry in `MAINTENANCE.md` does not by itself justify keeping prose in `SKILL.md`. Runtime prose still has to earn its place through the goals and behavioral contract.

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

Flag `UNALIGNED` sections before tightening individual sentences. They cannot remain runtime behavior merely because they already exist in the current implementation.

Do not immediately discard them. During the counterfactual deletion pass, determine whether they contain a durable goal, maintenance fact, local implementation invariant, or architectural decision that belongs somewhere else. Otherwise delete them.

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

### Disposition

After determining what runtime text is necessary, assign removed or retained material one disposition:

* **KEEP-RUNTIME** - required execution instruction, resolution detail, constraint, or validation.
* **KEEP-REASONING** - reasoning principle required for context-dependent judgment.
* **MOVE-GOALS** - expresses a capability or outcome the skill exists to provide and belongs in `SKILL-GOALS.md`.
* **MOVE-LOCAL** - useful maintenance knowledge whose natural scope is one script, config, template, reference, or other artifact.
* **MOVE-MAINTENANCE** - non-obvious whole-skill maintenance context that still constrains present changes.
* **MOVE-ADR** - a significant durable decision that passes the ADR threshold below.
* **DELETE** - has no continuing execution, goal, or maintenance value.

`MOVE-*` never means copy the original prose wholesale. Extract only the smallest durable fact that deserves to survive.

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

### Wrong home and maintenance value

Runtime irrelevance does not automatically mean information is worthless. Some prose is useless to the executing agent but valuable to a future maintainer.

For material leaving runtime context, ask:

> Would a future maintainer be materially more likely to make an incorrect change without knowing this?

If no, delete it.

If yes, determine its narrowest correct home.

#### Scope follows ownership

Put maintenance knowledge where the maintainer naturally encounters the thing it constrains.

Use **MOVE-LOCAL** when the fact applies to one artifact and can live with it:

* script-specific invariants -> script docstring or local documentation;
* configuration-specific constraints -> configuration-adjacent documentation;
* reference-specific maintenance facts -> that reference;
* template-specific constraints -> template-adjacent documentation.

Do not put a local fact into whole-skill maintenance context merely because `MAINTENANCE.md` exists.

Use **MOVE-MAINTENANCE** only when all three are true:

1. **Still constrains the present** - it affects how this skill can safely be changed now.
2. **Non-obvious** - a maintainer cannot reliably recover it by inspecting the artifact they would naturally edit.
3. **Cross-cutting or displaced** - no narrower artifact is the natural place to encounter it.

If any condition fails, do not put it in `MAINTENANCE.md`.

#### MAINTENANCE.md

`MAINTENANCE.md` is optional whole-skill maintenance context. Create it lazily only when at least one fact passes the `MOVE-MAINTENANCE` test.

It is not a scratch pad, author journal, changelog, source dump, or destination for everything removed from `SKILL.md`.

When created, include only sections that have content:

```markdown
# Skill maintenance

## Invariants

- `<non-obvious property that must survive changes>`
  - Owned by: `<file/script/instruction or cross-cutting>`
  - Protected by: `<eval if available>`
  - Origin: `<issue/PR/commit only when useful>`

## Sources of truth

- `<source name>`
  - Source: `<URL, repository path, specification, vendor documentation>`
  - Governs: `<specific current behavior>`
  - Version/ref: `<version, tag, commit, or live documentation>`
  - Refresh when: `<condition that should cause revalidation>`

## Regression provenance

- `<failure that caused durable behavior>`
  - Observed in: `<issue/PR/incident>`
  - Required behavior: `<what must continue to be true>`
  - Protected by: `<instruction/script/eval>`

## Evaluation uncertainties

- `<behavior intentionally retained pending empirical evaluation>`
  - Question: `<what needs to be established>`
  - Relevant goal: `<goal>`
```

Do not create empty sections.

Do not add a runtime pointer from the target `SKILL.md` to `MAINTENANCE.md`. The executing agent does not need maintainer context.

#### Sources

Record an external source only when it governs current skill behavior that a future maintainer may need to revalidate.

Do not preserve a source merely because it was consulted while authoring the skill.

For every preserved source record:

* what source is authoritative;
* exactly what behavior it governs;
* the relevant version/ref when applicable;
* what future change should cause it to be checked again.

General documentation that does not govern a current skill-specific behavior should not be retained.

Keep sources in `MAINTENANCE.md` by default. If the target skill already has a dedicated maintenance source file, preserve that convention rather than creating a competing one. Do not create a separate source file merely to hold a few links.

#### Regression and issue provenance

Preserve an issue, PR, commit, or incident reference only when it explains a behavior or invariant that still constrains the present.

Reduce history to the current durable fact.

Prefer:

```markdown
- Parallel invocations must not share a run address.
  - Origin: #142
  - Protected by: concurrent-run eval
```

over narrative history of approaches that were tried and rejected.

Git history remains the source of historical detail.

#### ADR threshold

Use **MOVE-ADR** only when all three are true:

1. **Hard to reverse** - changing the decision later has meaningful cost.
2. **Surprising without context** - a reasonable future maintainer would question or "fix" it without knowing why.
3. **Real trade-off** - genuine alternatives existed and the choice was made for specific reasons.

If any condition fails, do not create an ADR.

Follow the repository's existing ADR convention when one exists.

If no ADR convention exists, do not create one merely to preserve minor skill history. A standalone skill may create `maintenance/adr/` lazily when the first decision actually passes all three conditions.

An ADR should record the decision and the minimum reason needed to prevent an incorrect reversal. Do not copy the original explanatory prose into it.

#### Delete history that no longer constrains anything

Delete rather than relocate:

* abandoned alternatives with no present consequence;
* authoring narrative;
* implementation trivia;
* explanations recoverable from the artifact itself;
* maintenance reminders aimed at an audience that will already see the relevant source;
* links to issues, PRs, commits, vendor docs, or research that do not govern current behavior;
* speculative future improvements that belong in an issue or backlog;
* human onboarding or promotional prose that does not affect execution.

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

If the answer is no, runtime deletion is correct. Then decide whether the smallest durable fact deserves `MOVE-GOALS`, `MOVE-LOCAL`, `MOVE-MAINTENANCE`, `MOVE-ADR`, or `DELETE`.

Do not use maintenance value as a reason to retain text in runtime context.

## Example

Load [references/example.md](./references/example.md) for a worked classification and reduction example.

## Step 4: Whole-skill preservation pass

After applying the accepted deletions, reread the **complete tightened skill** against the behavioral contract.

Local equivalence is insufficient if several individually safe deletions combine to remove a required behavior.

For every contract eval, identify where the tightened skill still supplies any behavior that the base agent cannot be expected to provide reliably.

If a requirement no longer has adequate support, restore the smallest instruction necessary.

Do not restore explanatory material merely because the original version contained it.

Then inspect all `MOVE-*` results:

* `MOVE-GOALS` entries express genuine skill-specific goals and are not generic agent expectations.
* `MOVE-LOCAL` entries are stored beside the artifact whose maintenance they constrain.
* `MOVE-MAINTENANCE` entries pass all three maintenance admission criteria.
* `MOVE-ADR` entries pass all three ADR criteria and follow the repository's existing convention.
* no runtime instruction now depends on maintainer-only material to execute correctly;
* no information was moved merely to avoid deleting it.

If relocation produced a longer explanation than the durable fact requires, tighten the relocated text too.

## Completion

Finish when:

1. every behavioral-contract requirement remains supported where explicit support is necessary;
2. no remaining runtime sentence contains a removable part whose deletion is expected to preserve behavior;
3. pointers still expose every required execution branch without redundant trigger language;
4. scripts and references remain resolvable exactly where their runtime behavior is needed;
5. no explanation remains solely to document how or why an already-unambiguous instruction works;
6. every retained maintenance fact still constrains present maintenance and lives at its narrowest useful scope;
7. `MAINTENANCE.md` exists only if at least one cross-cutting or displaced maintenance fact earns it;
8. every ADR created by this pass satisfies the hard-to-reverse, surprising, and real-trade-off tests;
9. historical detail with no current execution or maintenance consequence has been deleted rather than relocated.

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

Relocated:
- GOALS: <items or none>
- LOCAL: <items or none>
- MAINTENANCE: <items or none>
- ADR: <items or none>

Maintenance file:
- unchanged | created | tightened | not needed
```

Do not report every sentence. Summarize material changes.

Report `Goal deviations found: none` when none are found.

`Uncertain` items become candidates for the subsequent full skill eval.

Do not delete uncertain behavior based on intuition, and do not permanently retain it based on intuition. Let the empirical eval determine whether it earns its load.
