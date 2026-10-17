# Research Worker Handoffs

Use these plain handoffs with the active host's available worker mechanism. Do not paste a harness-specific tool call into a worker prompt. Give each worker only the paths it owns and retain its structured result for the orchestrator's final report.

## Categorization Handoff

```markdown
## Task

Inspect official documentation for {TOOL_OR_LIBRARY} and write a category plan at `.tmp/scratch/plans/{skill-name}-research-plan.md`.

## Required plan

- One bounded category per checklist item, with its documentation boundary.
- Official source URLs to inspect for each category.
- Explicit overlap resolutions and any known documentation gaps.
- A `STATUS: complete | blocked` line, then `ARTIFACTS`, `SOURCES`, `GAPS`, and `WARNINGS` sections.

## Constraints

- Do not create the target skill or reference files.
- Do not infer undocumented behavior.
- If a source cannot be read, record its exact URL and access error in `GAPS`.
```

## Research Handoff

```markdown
## Task

Research the `{CATEGORY_NAME}` category of {TOOL_OR_LIBRARY} for `{target-skill-path}`.

## File scope

Write only under `{target-skill-path}/references/{category}/`. Create a lowercase `index.md` that links with relative paths to every detailed reference file in that directory.

## Required evidence

- Attribute every factual claim to a source URL and access date.
- Prefer official documentation for API behavior and mark secondary sources as secondary.
- Record unsupported claims as `NOT_VERIFIED: {claim}`; do not fill gaps from model knowledge.
- Attribute examples to their source, or exercise them before calling them working.

## Result

Return `STATUS: complete | blocked | failed`, followed by `ARTIFACTS`, `SOURCES`, `GAPS`, and `WARNINGS`. Preserve exact access errors and do not modify another category's files.
```

## Integration Handoff

```markdown
## Task

Integrate the completed category indexes into `{target-skill-path}/SKILL.md`.

## Steps

1. Read every `references/{category}/index.md` named by the approved research plan.
2. Add concise relative links and usage routing to SKILL.md; keep source detail in `references/`.
3. Check every new or changed Markdown link and report the exact paths checked.
4. Preserve the target skill's existing frontmatter, lifecycle, and package conventions.

## Result

Return `STATUS: complete | blocked | failed`, `ARTIFACTS`, `SOURCES`, `GAPS`, and `WARNINGS`. Do not hide an unavailable category or a broken link.
```
