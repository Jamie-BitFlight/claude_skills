# Workflow Identification

Use this reference only for source units that show at least two distinct workflow signals.

## Two-Signal Rule

Count these signals:

1. Order-dependent actions whose reordering changes the outcome
2. Observable branch or retry conditions
3. Named actors or states with explicit transitions
4. Named terminal success, failure, completion, or stop outcomes

Classify material as workflow-shaped only when at least two signals are present. A list of steps with
no branch, state transition, or terminal outcome remains procedural atoms rather than a separate
workflow.

## Preserve the Workflow

Map every action, condition, transition, retry bound, and terminal outcome to its own atom. Keep the
source order and exact technical tokens. Choose the smallest representation that preserves the
behavior:

- imperative ordered steps for a linear procedure
- an explicit branch table for a compact decision
- a diagram or separate workflow reference when it makes three or more transitions easier to follow

The baseline workflow can author each representation directly. A compatible installed diagram
specialist may analyze the complete workflow atom set, but its output is evidence rather than
completion authority. Verify every proposed node and edge against the atoms before emission.

If the source omits an actor, observable condition, transition, or terminal state needed to preserve
the behavior, mark the affected atom `UNRESOLVED`. Do not invent the missing fact or publish a stub as
complete.

## Example Classification

```text
1. Run `acme check PATH`.
2. If it prints `E_BUSY`, wait one second and retry once.
3. If the retry prints `E_BUSY`, stop and report `CHECK_BLOCKED`.
```

This is workflow-shaped because it contains order-dependent steps, observable branch conditions,
and a named terminal outcome. Preserve `acme check PATH`, `E_BUSY`, `one second`, `retry once`, and
`CHECK_BLOCKED` exactly.

## Output Accounting

When a workflow lives in a separate candidate file, record that relative path and section for every
workflow atom and link it from the loading step in `SKILL.md`. When it stays inline, record the exact
`SKILL.md` section. Every emitted transition must trace to an atom, and every workflow atom must have
one disposition before the classification step completes.
