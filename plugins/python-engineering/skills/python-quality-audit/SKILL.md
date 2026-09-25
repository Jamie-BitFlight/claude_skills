---
name: python-quality-audit
description: Use when the user asks for a read-only, actionable audit of Python code quality, modernization, maintenance burden, ecosystem opportunities, or Pythonic design across a PR, git diff, staged/unstaged changes, files, or directories.
argument-hint: '[PR | diff | staged | unstaged | file | directory]'
user-invocable: true
---

# Python Quality Audit

Audit Python without modifying the target. Fan out independent evidence gathering, then synthesize one deduplicated report whose findings can be verified and actioned.

Load `python-engineering:standards-for-python-development` first. Its shared rules define the preferred Python engineering defaults and repository-precedence rules.

## Resolve scope

Interpret the argument as exactly one review surface:

- PR: changed Python files plus affected callers/consumers, tests, docs, config, manifests, generated artifacts, and public contracts.
- diff: the supplied/base diff plus the same affected surface.
- staged: `git diff --cached`.
- unstaged: `git diff` plus relevant untracked Python files.
- file/directory: the selected Python target plus materially affected consumers/contracts.

Do not silently broaden into unrelated cleanup. Trace outward far enough to determine whether a finding is local or systemic.

Record the repository's actual Python floor. If the user explicitly supplies a target floor (for example Python 3.15), assess modernization against that target as PROPOSED unless repository configuration already establishes it. Do not recommend syntax or APIs unavailable at the authoritative floor.

## Independent audit lanes

Run the applicable lanes in isolated agents. Give each the resolved scope and starting paths, not another lane's conclusions. Lanes report evidence and candidates; they do not edit.

### 1. Smell and standards lane — StinkySnake

Dispatch an isolated agent and have it load `python-engineering:stinkysnake` against the resolved scope. Its returned findings are evidence for synthesis, not instructions to edit.

The lane must cover:

Find demonstrated deviation from the shared standards and Pythonic design:

- lint/type/test escapes and suppressions, especially exceptions that should be localized in a boundary file;
- cargo-cult leading underscores without a concrete privacy/API reason;
- files approaching/exceeding ~500 physical LOC and responsibility/cohesion problems;
- duplicated logic, unnecessary wrappers/indirection, speculative abstractions, dead branches and compatibility scaffolding;
- weak typing, unchecked external boundaries, misleading casts, exception misuse, sync/async mistakes;
- violations of existing project architecture, public contracts, dependency policy, or configured tooling.

A smell is a signal to trace to its cause. Do not recommend cosmetic churn when the underlying design is sound.

### 2. Python modernization lane — SnakePolish

Dispatch a separate isolated agent and have it load `python-engineering:snakepolish` against the same resolved scope and any explicitly proposed Python floor. Do not give it the StinkySnake findings; independence is intentional.

The lane must cover:

Ask how the same capability could be smaller, clearer, more Pythonic, and lower-maintenance at the authoritative/target Python floor:

- obsolete compatibility code or backports removable at the floor;
- newer stdlib/language features that eliminate custom machinery;
- modules/functions that can be combined or simplified without losing cohesion;
- manual state, parsing, serialization, retry, concurrency, CLI, configuration, packaging, caching, traversal, or validation machinery that modern Python handles better;
- opportunities to delete code rather than rewrite it.

Prefer reduced maintained code and simpler contracts over novelty.

### 3. Ecosystem substitution lane

Identify code/process maintained locally that a mature external Python library or tool could own.

For every candidate, verify current maintenance and capabilities from primary sources before recommending it. Compare:

- maintained local code/process that would disappear;
- dependency/API/compatibility cost introduced;
- project Python floor and platform constraints;
- migration/breaking-change risk;
- whether the library actually owns the hard edge cases rather than merely moving wrappers around them.

Do not recommend a dependency merely because one exists.

### 4. Large-project practice lane

Research how actively maintained, substantial open-source Python projects solve the same demonstrated problems. Use current repository/official evidence.

Look for reusable practices in CI, release automation, dependency management, testing, typing, generated code, docs, repository automation, performance, security, and maintenance. Report a practice only when it addresses a problem observed in this target. Do not import process ceremony by analogy alone.

### 5. Removal and process-debt lane

Challenge what can disappear:

- redundant validation already guaranteed elsewhere;
- duplicate workflow/tool stages;
- generated artifacts maintained by hand;
- compatibility/process steps whose triggering condition no longer exists;
- scripts superseded by project tooling;
- tests coupled only to deleted implementation detail;
- documentation describing obsolete behavior.

Require evidence before calling something dead or redundant.

## Synthesis

Reconcile lane outputs against the actual repository and each other. Merge duplicates by root cause. Reject recommendations that violate repository constraints or merely exchange one maintenance burden for another.

Classify evidence as:

- OBSERVED — directly present in code/config/history/tool output.
- DERIVED — follows from traced repository relationships.
- VERIFIED-EXTERNAL — supported by current primary-source ecosystem/project evidence.
- HYPOTHESIS — plausible improvement requiring an experiment or benchmark.

For every material finding provide:

```text
[P1|P2|P3] <title>
Evidence: <classification + file:line/config/external source>
Current burden: <what is maintained, risky, duplicated, or hard to understand>
Recommendation: <specific change>
Why better: <correctness / deletion / maintenance / clarity / performance>
Protected behavior: <contracts/invariants that must survive>
Verification: <specific command, test, comparison, benchmark, or inspection>
Affected surface: <implementation + consumers/tests/docs/config/generated artifacts>
```

Priority means consequence/opportunity, not certainty:
- P1: correctness/security/release risk or large demonstrated maintenance reduction.
- P2: meaningful design/maintenance improvement.
- P3: worthwhile cleanup with bounded consequence.

Keep correctness/contract findings, qualitative design judgments, and efficiency telemetry separate. Do not compute an aggregate score.

## Actionability gate

A recommendation is actionable only when its affected surface and verification path are known. If library replacement, deletion, Python-floor migration, or process removal lacks enough evidence, report the missing evidence and the smallest experiment needed instead of presenting it as ready work.

End with:

1. findings ordered by consequence;
2. deletion/replacement opportunities;
3. hypotheses/experiments;
4. a smallest sensible implementation sequence that preserves behavior.

Do not edit, stage, commit, or post review comments unless the user separately asks.
