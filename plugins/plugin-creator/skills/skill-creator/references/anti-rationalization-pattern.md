# Anti-Rationalization Pattern

The anti-rationalization component is an optional two-column table pairing a first-person excuse an agent might use to skip a required step with a direct imperative counter-response, plus an optional Red Flags list of self-checkable warning signs. It defends workflow-enforcing skills against an agent declaring a multi-step process "complete" after silently skipping an intermediate verification or quality-gate step.

## When to Include This Component

Include this component when the skill enforces a multi-step discipline containing at least one skippable quality gate — a sequence an agent could plausibly report as complete after skipping one or more intermediate steps. Do not include it for pure reference lookups, single-action tools, or workflows that contain no gate an agent could skip.

| Skill shape | Needs the component? |
|---|---|
| `dh:verify-done`, `dh:validation-protocol` — multi-step workflows with skippable verification gates | Yes |
| A skill that only documents a CLI flag reference — single lookup, no sequence to skip | No |

## Table Shape

Header row is exactly:

```markdown
| Rationalization | Response |
|---|---|
| "I'll add tests later" | Add the test in this same turn — a task marked complete without tests is not complete |
| "This should be fine, I'm confident" | Confidence is not verification; run the check and cite its output |
| "The step doesn't apply this time" | Confirm the exemption against the skill's stated conditions before skipping; do not assume |
```

Each row pairs a first-person quoted excuse with a direct imperative counter-response. Source rows from rationalizations actually observed in agent output where possible, rather than inventing hypothetical ones. A table needs a minimum of one row; there is no fixed maximum — see the verify-done precedent below for a larger worked example.

## Red Flags (Optional)

Red Flags are an optional bullet list (not a table) of self-checkable warning signs an author includes alongside the table. Optional means the skill author decides, per skill, whether to add it — the authoring-checklist item covers the decision, not a mandate to always include it.

```markdown
- Language in your own output like "should work", "probably fine", or "seems correct" appearing before the verification step ran
- A completion claim ("Done!") followed immediately by a commit or push with no fresh command output in the same turn
- A verification step that exists in the skill's process but is treated as optional in practice
```

## Distinguishing This From Similar Tables

Three tables in this repository share a similar two- or three-column shape but serve different purposes — do not merge them:

- The verify-done `Rationalization | Response` table is the shipped precedent this pattern generalizes from, not a duplicate to fold into this file.
- The agentskills `best-practices.md` Anti-Patterns table (`| Anti-pattern | Problem | Instead |`) documents mistakes an author makes while constructing a skill. It operates at authoring time. The Rationalization | Response table operates at execution time, documenting excuses an agent uses while running a skill's workflow. Keep the two separate.
- This file is the reusable authoring template: it is what a skill author consults to build their own Rationalization | Response table for a new workflow-enforcing skill.

## Source

SOURCE: [research/skill-generation-tools/agent-skills.md](../../../../../research/skill-generation-tools/agent-skills.md) lines 116-131 — quote: "Anti-rationalization. Every skill includes a table of common excuses agents use to skip steps (e.g., 'I'll add tests later') with documented counter-arguments." (accessed 2026-07-10)

SOURCE: <https://github.com/addyosmani/agent-skills/blob/main/README.md> (accessed 2026-07-10) — primary URL for the upstream Consistent Skill Anatomy pattern.

SOURCE: [plugins/development-harness/skills/verify-done/SKILL.md](../../../../../plugins/development-harness/skills/verify-done/SKILL.md) lines 169-182 — precedent for the `Rationalization | Response` column vocabulary.
