# Glossary

Repository terminology. Each entry states the fact that gets guessed wrong most often, then
points to the skill that covers the full spec. Load that skill instead of re-deriving the
definition from context.

Skill: a directory, not a file: `SKILL.md` plus optional `scripts/`, `references/`, and `assets/`.
Load `plugin-creator:agentskills` for the open-standard spec or
`plugin-creator:claude-skills-overview-2026` for Claude-Code-specific behavior.

`SKILL.md`: the required file inside a skill directory. It contains frontmatter and instructions;
it is not the complete skill.

Plugin: a packaging and distribution unit containing `.claude-plugin/plugin.json` and optional
skills, commands, agents, and scripts. Load `plugin-creator:plugin-lifecycle` for the workflow.

Marketplace: `.claude-plugin/marketplace.json`, the registry of installable plugins for a
repository.

Agent: a dispatch target for the `Agent` or `Task` tool, either built in or defined under
`agents/*.md`. This differs from Agent Skills, the open skill format. Load
`agent-orchestration:delegate` for repository dispatch conventions.

Command: a Markdown file under `commands/` invoked as `/name`. A skill directory and command file
sharing a name both produce `/name`; the skill wins. Load `plugin-creator:command-development`.

Hook: a script wired to a lifecycle event through `hooks.json` or skill or agent frontmatter. Load
`plugin-creator:hooks-guide`.

MCP server: a Model Context Protocol server exposing tools or resources through `.mcp.json` or a
plugin's `mcpServers`. It is a tool provider, not instructional content.
