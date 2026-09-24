---
name: claude-skills-overview-2026
description: Claude Code runtime skills router. Use when configuring SKILL.md frontmatter, discovery, invocation, hooks, context forks, substitutions, loading behavior, or headless skill dispatch.
user-invocable: true
---

# Claude Code Skills Runtime

Use this skill for Claude Code runtime behavior. Use `plugin-creator:agentskills` for portable
frontmatter, package, upload, or cross-client requirements. Use `plugin-creator:skill-creator` for
the skill-authoring workflow.

Load the reference that matches the current branch:

- **Frontmatter, discovery, invocation, substitutions, dynamic injection, forks, preloaded skills,
  or metadata budgets**: Read
  [claude-code-skills-official.md](./resources/claude-code-skills-official.md).
- **Programmatic sessions or direct `/<name>` dispatch**: Read
  [headless-agent-sdk.md](./resources/headless-agent-sdk.md).
- **Skill hooks**: Load `plugin-creator:hooks-guide`; skill-frontmatter hooks use Claude Code hook
  configuration and become active after invocation.
- **Plugin packaging and namespace behavior**: Load
  `plugin-creator:claude-plugins-reference-2026`.
- **Agent teams**: Read [agent-teams.md](./resources/agent-teams.md).
- **Scheduled interactive prompts**: Read [scheduled-tasks.md](./resources/scheduled-tasks.md).
- **Output styles**: Read [output-styles.md](./resources/output-styles.md).

Claude Code accepts runtime fields beyond the portable Agent Skills schema. Do not submit those
extensions to a portable package or upload boundary unless that boundary documents them.

Primary source: [Extend Claude with skills](https://code.claude.com/docs/en/skills) (accessed
2026-09-24).
