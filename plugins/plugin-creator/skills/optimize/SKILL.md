---
name: optimize
description: Audit and trim CLAUDE.md files, rules, skills, and agent definitions for content that Claude does not need — discoverable data, explained-away knowledge, invented constraints, duplicated content, and stale cached facts. Use when writing new memory/rules/skills/agents, or when reviewing existing ones for bloat. Triggers include "write a rule for", "add to CLAUDE.md", "create an agent", "update memory", or any request to author AI-facing instruction content.
user-invocable: true
---

# Writing Lean AI-Facing Instructions

The AI writing an instruction file and the AI reading it share the same training data and reasoning capability. Write only what that shared baseline cannot supply.

## The Only Things Worth Writing

**User decisions** — choices the project made that differ from defaults: "We use pnpm, not npm." "Dark background, cream foreground."

**Project-specific facts** — paths, scripts, and tools that only exist here: "Run `node .claude/scripts/gh-api.cjs release latest <owner>/<repo>` to get the current major."

**Constraints** — things that would be done differently without this instruction: "Never copy a `uses:` version from another workflow file without verifying it."

Everything else is noise.

## What to Cut

**Discoverable data** — version numbers, hex codes, release tags, file listings, schema fields. If a command or lookup can produce it, don't store it. It will be wrong within days.

**Explained knowledge** — step-by-step breakdowns of things Claude already knows how to do. If the instruction explains how to read a releases page and extract a major version, cut it. Claude knows how to do that.

**Invented constraints** — rules, fallback patterns, schemas that weren't requested and have no verified basis. If you can't cite the source or session that established it, cut it.

**Worked examples for obvious operations** — one example that shows a non-obvious pattern format is useful. Three examples walking through the same operation are not.

**Duplicate content** — if it's in the skill, don't put it in the agent. If it's in the agent, don't put it in the rule. Pick the right place and put it there once.

## Where Each Type of Content Belongs

Read the reference for the content type you are writing or auditing:

- Writing or reviewing **CLAUDE.md or `.claude/rules/`** → [references/memory-and-rules.md](./references/memory-and-rules.md)
- Writing or reviewing **SKILL.md or references/** → [references/skills.md](./references/skills.md)
- Writing or reviewing **agent definition files** → [references/agents.md](./references/agents.md)
