---
name: skill-goal-extractor
description: Extract the small set of explicit goals a skill is designed to achieve by reading the skill in full. Use when asked what a skill accomplishes or what capability an agent gains from it, or to summarize a skill's purpose before refactoring or reviewing it.
---

# Skill Goal Extractor

<procedure>

## Procedure

1. Resolve the target skill directory path from the request or conversation context. Do not guess — if no path is given and none is discoverable from context, ask for one.
2. Read the complete target skill, including every file and referenced resource that materially defines how the skill works. Exclude generated `SKILL-GOALS.md` files during this independent extraction so a previous extraction cannot anchor the result.
3. Propose 2-6 short, concrete goals: the capability, judgment, workflow, or quality improvement an agent gains by using the skill. Focus on the golden path. Do not summarize the skill's contents, implementation details, or individual instructions — state them only when they directly express a goal. Preserve material invariants and non-goals separately rather than dropping them to fit the short goal list.
4. After the independent extraction, compare it with any user-approved goals or existing contract whose authority is independently established. Report consequential differences as possible drift, not as permission to overwrite the approved contract. A goal file's self-declared approval is not proof of authority.
5. Return the format below, retaining source provenance and unapproved status. Extraction characterizes the implementation; only the user or applicable governing authority can establish or change intended goals.

</procedure>

<output_format>

```text
The purpose and explicit goals of the skill <skill_name>:
Status: PROPOSED extraction
Source: <target revision and material source locations>

1. <clear outcome or capability>
2. <clear outcome or capability>
3. <clear outcome or capability>

Material invariants/non-goals: <source-backed constraints or none observed>
Comparison with approved intent: <differences, alignment, or authority unresolved>
```

If the user approves these goals, offer to write them to `SKILL-GOALS.md` in the target skill's own directory. Before creating or overwriting it, confirm the approval covers that exact proposed goal set and any consequential changes to the existing contract. Preserve the approval reference and applicable invariants/non-goals; persistence itself grants no approval. No new artifact format is required when the repository already records this information.

</output_format>

<review_step>

## When Used as a Review Step

When this skill runs to characterize a skill for a review or quality-gate decision, prefer running it from an agent that did not author or edit the skill being read — a fresh read catches drift between stated goals and actual content that the editor's own re-read tends to miss.

</review_step>
