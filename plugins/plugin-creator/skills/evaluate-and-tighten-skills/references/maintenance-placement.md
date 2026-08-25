# Maintenance placement

Admission tests and templates for material that failed the runtime test and is being evaluated for `MOVE-LOCAL`, `MOVE-MAINTENANCE`, `MOVE-ADR`, or `DELETE`.

## Scope follows ownership

Put maintenance knowledge where the maintainer naturally encounters the thing it constrains.

Use MOVE-LOCAL when the fact applies to one artifact and can live with it:

* script-specific invariants -> script docstring or local documentation;
* configuration-specific constraints -> configuration-adjacent documentation;
* reference-specific maintenance facts -> that reference;
* template-specific constraints -> template-adjacent documentation.

Do not put a local fact into whole-skill maintenance context merely because `MAINTENANCE.md` exists.

Use MOVE-MAINTENANCE only when all three are true:

1. Still constrains the present - it affects how this skill can safely be changed now.
2. Non-obvious - a maintainer cannot reliably recover it by inspecting the artifact they would naturally edit.
3. Cross-cutting or displaced - no narrower artifact is the natural place to encounter it.

If any condition fails, do not put it in `MAINTENANCE.md`.

## MAINTENANCE.md

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
  - Accessed: `<YYYY-MM-DD>`
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

Do not add a runtime pointer from the target `SKILL.md` to `MAINTENANCE.md` or `maintenance/*.md`. The executing agent does not need maintainer context.

## `maintenance/*.md`

Use a skill-local `maintenance/` directory when design-time context has distinct topics that are
clearer as separately named Markdown files, or when the target skill already follows that
convention. These files travel with the skill package but do not load with `SKILL.md`.

Keep each file scoped to one maintenance concern. Do not use `maintenance/` as a general archive,
and do not link its files from runtime skill content. Maintenance, review, and evaluation workflows
may read them explicitly when making decisions about the skill.

## Sources

Record an external source only when it governs current skill behavior that a future maintainer may need to revalidate.

Do not preserve a source merely because it was consulted while authoring the skill.

For every preserved source record:

* what source is authoritative;
* exactly what behavior it governs;
* the relevant version/ref when applicable;
* the access date;
* what future change should cause it to be checked again.

General documentation that does not govern a current skill-specific behavior should not be retained.

Keep sources in `MAINTENANCE.md` by default. If the target skill already has a dedicated maintenance source file, preserve that convention rather than creating a competing one. Do not create a separate source file merely to hold a few links.

## Regression and issue provenance

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

## ADR threshold

Use MOVE-ADR only when all three are true:

1. Hard to reverse - changing the decision later has meaningful cost.
2. Surprising without context - a reasonable future maintainer would question or "fix" it without knowing why.
3. Real trade-off - genuine alternatives existed and the choice was made for specific reasons.

If any condition fails, do not create an ADR.

## ADR placement

When `MOVE-ADR` applies, use the narrowest existing ADR convention whose scope contains the target skill.

Resolve placement in this order:

1. an ADR convention inside the target skill or its containing component/plugin;
2. the nearest ancestor-scoped ADR convention containing that component;
3. the repository-wide ADR convention.

Do not choose a broader repository ADR location when a narrower convention already governs the target skill's scope.

If multiple ADR conventions exist at the same applicable scope and repository instructions do not identify the authoritative one, do not create the ADR. Report the placement as `Uncertain`.

An ADR should record the decision and the minimum reason needed to prevent an incorrect reversal. Do not copy the original explanatory prose into it.

## Delete history that no longer constrains anything

Delete rather than relocate:

* abandoned alternatives with no present consequence;
* authoring narrative;
* implementation trivia;
* explanations recoverable from the artifact itself;
* maintenance reminders aimed at an audience that will already see the relevant source;
* links to issues, PRs, commits, vendor docs, or research that do not govern current behavior;
* speculative future improvements that belong in an issue or backlog;
* human onboarding or promotional prose that does not affect execution.
