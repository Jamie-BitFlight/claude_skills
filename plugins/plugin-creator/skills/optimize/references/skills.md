# Skills — What Belongs Where

SOURCE: [Anthropic skills repo skill-creator SKILL.md](https://github.com/anthropics/skills/tree/main/skills/skill-creator), "Keep the prompt lean. Remove things that aren't pulling their weight." (accessed 2026-03-10)

A skill has two parts with different loading costs: SKILL.md (always loaded when triggered) and references/ (loaded on demand). Keep SKILL.md to workflow and decision logic. Put domain detail in references/.

## SKILL.md — What Belongs Here

**The workflow** — what steps to follow, in what order, with what decision points.

**Pointers to references** — which file to read and when. "For AWS-specific flags, read `references/aws.md`."

**Project-specific tool invocations** — commands, script paths, and flags that only exist in this context.

**The triggering description** — everything that determines when the skill activates goes in frontmatter `description`, not in the body. Body content loads after triggering; it cannot influence whether triggering happens.

## SKILL.md — What Does Not Belong Here

**Content already in a reference file** — pick one place.

**Domain knowledge Claude already has** — TypeScript syntax, SQL patterns, git commands. Only write what's project-specific or tool-specific.

**Agent body content duplicated into the skill** — if an agent file covers a topic, the skill that loads that agent should not re-explain the same topic. The skill tells the agent what to do; the agent knows how to do it.

## References/ — What Belongs Here

**Domain detail** — schemas, API shapes, framework-specific patterns that the skill references by name.

**Variant-specific content** — when a skill supports multiple platforms or languages, one file per variant. Claude reads only the one that applies.

**Content that grows** — documentation that will be updated. Keeping it in references/ means SKILL.md stays stable.

## The Agent–Skill Boundary

The agent file should be small: frontmatter, role, what it produces, and any project-specific constraints. The skill that loads it carries the comprehensive reference material. This way the agent is reusable and the skill is the knowledge layer.

If you find yourself writing the same content in both the agent and the skill, the agent is too large.
