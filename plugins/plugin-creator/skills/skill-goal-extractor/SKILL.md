---
name: skill-goal-extractor
description: Extract the small set of explicit goals a skill is designed to achieve by reading the skill in full. Use when asked what a skill accomplishes or what capability an agent gains from it, or to summarize a skill's purpose before refactoring or reviewing it.
---

# Skill Goal Extractor

## Procedure

1. Resolve the target skill directory path from the request or conversation context. Do not guess — if no path is given and none is discoverable from context, ask for one.
2. Read the complete target skill, including every file and referenced resource that materially defines how the skill works.
3. Identify 2-6 short, concrete goals: the capability, judgment, workflow, or quality improvement an agent gains by using the skill. Focus on the golden path. Do not summarize the skill's contents, implementation details, or individual instructions — state them only when they directly express a goal.
4. Return only the format below.

```text
The purpose and explicit goals of the skill `<skill_name>`:

1. `<clear outcome or capability>`
2. `<clear outcome or capability>`
3. `<clear outcome or capability>`
```

## When Used as a Review Step

When this skill runs to characterize a skill for a review or quality-gate decision, prefer running it from an agent that did not author or edit the skill being read — a fresh read catches drift between stated goals and actual content that the editor's own re-read tends to miss.
