# Glossary

Repository terminology. Each entry states the fact that gets guessed wrong most often, then
points to the skill that covers the full spec — load that skill instead of re-deriving the
definition from context.

**Skill** — a directory (not a file): `SKILL.md` plus optional `scripts/`, `references/`,
`assets/`. Load `plugin-creator:agentskills` for the open-standard spec (portable across agent
products) or `plugin-creator:claude-skills-overview-2026` for Claude-Code-specific behavior
(hooks, context fork, invocation control, bundled skills).

**SKILL.md** — the required file *inside* a skill directory (frontmatter + instructions). Not the
skill itself — see Skill.

**Plugin** — a packaging/distribution unit: `.claude-plugin/plugin.json` plus `skills/`,
`commands/`, `agents/`, `scripts/` (see `AGENTS.md`'s "Plugin Structure"). Bundles many skills
together; a skill does not need a plugin to be installed or used on its own (`npx skills add
<owner>/<repo>/path/to/skill` installs one skill by path, no plugin required).

**Marketplace** — `.claude-plugin/marketplace.json`, the registry of installable plugins for a
repo. Load `plugin-creator:plugin-lifecycle` for the create/install/publish workflow.

**Agent** (in this repo's tooling context) — a dispatch target for the `Agent`/`Task` tool: a
built-in type (`general-purpose`, `Explore`, ...) or a plugin-shipped one defined under
`agents/*.md`. Distinct from "Agent Skills" (the open skill format) despite sharing the word. Load
`agent-orchestration:agent-orchestration` for dispatch conventions used in this repo.

**Command** — a `.md` file under `commands/` invoked as `/name`. Skills and commands are the same
underlying system; a skill directory and a command file sharing a name both produce `/name`, and
the skill wins if both exist. Load `plugin-creator:command-development`.

**Hook** — a script wired to a lifecycle event (`PreToolUse`, `PostToolUse`, `Stop`, ...) via
`hooks.json` or skill/agent frontmatter. Load `plugin-creator:hooks-guide`.

**MCP server** — a Model Context Protocol server exposing tools/resources, configured in
`.mcp.json` or a plugin's `mcpServers`. A tool provider, not instructional content — distinct from
a skill or agent.
