# Plugin Creator

Use this plugin when creating, changing, refactoring, or validating plugins, skills, agents,
commands, hooks, MCP configuration, or plugin-facing AI documentation.

## Route By Intent

- Create or update a skill: activate `/plugin-creator:skill-creator`.
- Create or update an agent: activate `/plugin-creator:agent-creator`.
- Create a plugin or route an end-to-end plugin change: activate
  `/plugin-creator:plugin-lifecycle`.
- Refactor an oversized skill: activate `/plugin-creator:refactor-skill` after `skilllint` reports
  SK006 or SK007.
- Assess and plan a plugin refactor: activate `/plugin-creator:assessor`.
- Execute an existing refactor task file: activate `/plugin-creator:implement-refactor`.
- Validate a completed refactor: activate `/plugin-creator:ensure-complete`.
- Share instructional prose across components: activate
  `/plugin-creator:shared-content-references`.
- Wrap changing external documentation: activate `/plugin-creator:add-doc-updater`.
- Check a skill, agent, or plugin: activate `/plugin-creator:lint`.

## Canonical Authorities

- Read `.claude-plugin/plugin.json` for the current version and plugin metadata. Read the actual
  `skills/`, `agents/`, and `commands/` directories for the component roster; do not cache either
  in this file.
- For Claude Code skill runtime behavior, including frontmatter, invocation, substitutions, and
  `allowed-tools`, activate `/plugin-creator:claude-skills-overview-2026` and read its official
  primary-source reference.
- For plugin manifests, packaging, discovery, cache behavior, and CLI behavior, activate
  `/plugin-creator:claude-plugins-reference-2026` and follow the branch-specific reference it
  names.
- For agent fields and permissions, activate `/plugin-creator:claude-subagent-reference`.
- For hook configuration, activate `/plugin-creator:hooks-guide`.
- For portable Agent Skills requirements, activate `/plugin-creator:agentskills` rather than
  applying Claude Code extensions to another host.
- For marketplace versioning, read [Marketplace versioning](../../docs/marketplace-versioning.md)
  before changing version or manifest fields.

## Project boundary

For plugin directory ownership, test-runner boundaries, centralized development policy, and standalone extraction, read `skills/plugin-lifecycle/references/plugin-project-layout.md`. Do not infer that a plugin needs a local Python project merely because it contains Python.

## Validation

Run `uvx skilllint@latest check <path>` for frontmatter, complexity, links, and plugin structure.
For plugin directories, also run the runtime-escape audit documented by `/plugin-creator:lint`,
`claude plugin validate <plugin-directory>` when the CLI is available, and
`uv run plugins/plugin-creator/scripts/check_agent_auto_discovery.py
<plugin-directory>/.claude-plugin/plugin.json` when an explicit agent or command allowlist exists.

Treat validator output as the authority for current error codes and token thresholds. Keep
runtime facts and checklists at their canonical owners; workflows point to them instead of copying
their contents or line numbers.
