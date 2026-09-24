# Phase 2 — Researcher Prompts

Detailed prompts for the four parallel researchers spawned in Phase 2 (Research). Spawn all four in a single message so they run concurrently. Each researcher writes to its own output file; the orchestrator then merges all four into `research-FINDINGS.md` using the template in `./artifact-templates.md`.

The orchestrator must always run Researcher 0 first (feature discovery), then dispatch Researchers 1–4 with the feature context as input.

---

## Researcher 0 — Feature Discovery

Skill: `plugin-creator:feature-discovery`

Context to include in the prompt:
- Plugin concept from `<plugin_target/>` (everything after "new")
- discuss-CONTEXT.md from Phase 0.5

Output: `.plugin-creator/plans/{plugin-name}/feature-context-{slug}.md` — feature context document used as shared input by Researchers 1–4.

---

## Researcher 1 — Existing Solutions

Dispatch as `plugin-creator:plugin-assessor`.

Context to include in the prompt: plugin concept, feature context from Researcher 0.

Prompt:

> Search `plugins/` and `~/.claude/skills/` for similar functionality. Report what exists, gaps to fill, patterns to follow or avoid.

Output: `.plugin-creator/plans/{plugin-name}/research-1-existing.md`

---

## Researcher 2 — Claude Code Features

Dispatch as `plugin-creator:plugin-assessor`.

Context to include in the prompt: plugin concept, feature context from Researcher 0.

Prompt:

> What capabilities should this plugin use — dynamic context injection (`!command`), subagent execution (`context: fork`), hooks (which events?), MCP/LSP integration opportunities? Report recommended features with rationale.

Output: `.plugin-creator/plans/{plugin-name}/research-2-features.md`

---

## Researcher 3 — Architecture Patterns

Dispatch as `plugin-creator:plugin-assessor`.

Context to include in the prompt: plugin concept, feature context from Researcher 0.

Prompt:

> How do well-structured plugins organize — skill directory structure, reference file patterns, agent definitions, hook configurations? Report recommended structure based on similar plugins.

Output: `.plugin-creator/plans/{plugin-name}/research-3-architecture.md`

---

## Researcher 4 — Pitfalls and Official Docs

Dispatch as the harness-native `general-purpose` agent.

Context to include in the prompt: plugin concept, feature context from Researcher 0.

Prompt:

> Fetch `https://code.claude.com/docs/en/plugins-reference.md` and `https://code.claude.com/docs/en/skills.md`. Identify current schema requirements and accepted list forms, common mistakes, deprecations or new features. Report gotchas to avoid.

Output: `.plugin-creator/plans/{plugin-name}/research-4-pitfalls.md`

---

## Merge

After all four researcher outputs exist on disk, consolidate them into `.plugin-creator/plans/{plugin-name}/research-FINDINGS.md` using the template in `./artifact-templates.md`.
