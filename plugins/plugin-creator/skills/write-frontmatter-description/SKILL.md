---
name: write-frontmatter-description
description: Write or tighten the description field of a skill or agent so the right one loads. Use when creating a skill or agent, when a description is vague, bloated, or missing triggers, when YAML multiline or quoting breaks the frontmatter, or when choosing between a model-invoked and a user-invoked skill.
user-invocable: true
---

If the user's intent does not match the purpose of this skill, load `plugin-creator:plugin-lifecycle` to route to the right skill and process.

# Write Frontmatter Description

A description is a **context pointer**: a line that names material the agent cannot see, and encodes the condition for reaching it. A model-invoked skill's description sits in the context window on every turn of every session, whether the skill fires or not. It is the only part of the skill that is always loaded, and it decides on its own whether the skill loads at all from among a hundred others.

So a description earns harder pruning than the body it points at. A word that does not help the agent decide *reach it or not* is paid for on every turn and returns nothing.

SOURCE: [writing-for-agents](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents) (accessed 2026-09-13) — the pointer model, branch counting, and the no-op test. Adapted here to the `description` field specifically.

SOURCE: <https://agentskills.io/skill-creation/optimizing-descriptions.md> (accessed 2026-09-24) — imperative `Use this skill when...` phrasing.

## The two jobs

A pointer does two things: it states what the material is, and it lists the **branches** that should trigger reaching it. A branch is a distinct case the skill handles — a path a run can take through it. Anything that is neither is waste.

### Job 1 — name the material

Open with the verb the agent is scanning for, then its object. `Generate conventional commit messages from staged git diffs` names both in eight words.

Then stop. Cut identity the body already carries: a clause that summarises the skill's own quality bar (`Ensures output is complete, accurate, and consistently formatted`) spends permanent context restating a sentence the agent reads again the instant the skill loads.

### Job 2 — list the branches

Be directive and specific — models under-trigger skills, so name the concrete file types, commands, and task patterns that should fire this one. Open the list with `Use when`, `Activates on`, `Triggers on`, or `Apply when`.

Then count branches, and write **one trigger per branch**. Synonyms that rename a single branch are one branch written twice:

- `create a changelog` / `make a changelog` / `build a changelog` — one branch, three times.
- `is not taking effect` / `does not show up` / `applies the wrong one` — one branch, three times.
- `creating a skill` / `fixing broken YAML frontmatter` — two branches. Both stay.

Specificity and brevity pull the same way once you count branches: spend the words on covering every distinct case, and recover them by writing each case once.

Quoted phrases buy nothing. The agent matches on meaning, not on literal strings, and quotes are what force the whole value into YAML quoting.

## Write direct activation guidance

The description is injected into the system prompt as an instruction about activation. State the
action, then give direct `Use when...` guidance.

```yaml
# Direct activation guidance
description: Generate commit messages by analyzing staged git diffs. Use when writing a commit message.

# First person — describes a helper the agent is not
description: I can help write commit messages by looking at staged changes.

# Second person — addresses a reader who is not there
description: You can use this to generate commit messages.
```

## Model-invoked or user-invoked

The invocation choice decides what the description is *for*, so settle it before writing.

| Skill | Frontmatter | The description is | Write it |
| --- | --- | --- | --- |
| Model-invoked | omit `disable-model-invocation` | the agent's context pointer, loaded every turn | full branch list, imperative `Use this skill when...` guidance |
| User-invoked | `disable-model-invocation: true` | a human-facing menu line the agent never sees | one line of summary, triggers stripped |

Pick model-invocation when the agent, or another skill, must reach this skill on its own. A skill that only ever fires because a human typed its name pays permanent context load for reach nobody uses — set `disable-model-invocation: true` and pay none.

`user-invocable` and `disable-model-invocation` are skill-only fields. An agent file carries neither, and an agent's `description` is always model-facing, so it always takes the full branch list. Field semantics and the upstream length cap: `plugin-creator:claude-skills-overview-2026`. Agent frontmatter: `plugin-creator:agent-creator`.

## Worked rewrites

Each pair names the single operation performed.

**Collapse synonym branches.**

```yaml
# Before — "create"/"make"/"build a release" rename one branch
description: Use when the user asks to create a changelog, make a changelog, build a release changelog, or generate release notes for a version.

# After — two real branches, one trigger each
description: Generate a changelog from merged pull requests. Use when cutting a release or when asked for release notes.
```

**Cut the identity the body carries.**

```yaml
# Before — the second sentence is the skill's own summary of itself
description: Validate and fix YAML frontmatter in SKILL.md and agent files. Use when creating a skill or agent, or when frontmatter fails to parse. Ensures frontmatter is complete, informative, and front-loaded with trigger conditions.

# After
description: Validate and fix YAML frontmatter in SKILL.md and agent files. Use when creating a skill or agent, or when frontmatter fails to parse.
```

**Give a vague description its branches.**

```yaml
# Before — no verb, no object, no branch
description: A skill for working with documents

# After
description: Extract text and tables from PDFs, fill forms, and merge documents. Use when the user names a PDF file, a form, or a document merge.
```

## Keep it on one line

Write the value as a single-line string. Claude Code's skill indexer misparses the YAML multiline indicators (`>-`, `|-`, `>`, `|`) and can surface the indicator itself in place of the description — a silent failure with no error and no working skill. Quote the value only when YAML requires it: a colon, a leading special character, or a boolean literal.

SOURCE: `plugin-creator:claude-skills-overview-2026` § YAML Multiline Bug, citing Anthropic skill-authoring docs.

## Validate

```sh
uvx skilllint@latest check <file>
```

It reports multiline-indicator, quoting, length, and trigger-phrase failures against the thresholds in force, and `uvx skilllint@latest check --fix <file>` repairs the YAML ones. Run it rather than checking by hand.

## Done when

Both bars are met:

1. **Every branch the skill handles appears exactly once.** Enumerate the branches from the skill body first, then check the description against that list — a branch you cannot find in the description is a request that will never reach this skill.
2. **Every surviving clause changes the routing decision.** Take each clause in turn and ask: remove it — does the agent's choice to load this skill change? Delete the whole clause that fails, rather than trimming words from it.

Then `skilllint` exits clean.
