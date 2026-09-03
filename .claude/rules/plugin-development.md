---
paths:
- plugins/**/*
- .claude-plugin/**/*
---

# Plugin Development Workflows

## Local Testing

**Session-based (no installation):**

```bash
claude --plugin-dir ./plugins/plugin-name
```

**Via local marketplace** (persists across sessions; `--scope local` keeps it gitignored):

```bash
/plugin marketplace add ./.claude-plugin/marketplace.json
/plugin install plugin-name@jamie-bitflight-skills --scope local
```

For full add/remove/update procedures, see [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Prerequisite Skills for Plugin Work

Before modifying any plugin file (`plugin.json`, agents, skills, hooks), load these two reference skills:

- `plugin-creator:claude-plugins-reference-2026` — current Claude Code plugin schema, frontmatter fields, and component auto-discovery rules
- `plugin-creator:claude-skills-overview-2026` — current Claude Code skills schema and conventions

**Reason**: Editing plugin files without loading these skills risks schema violations and auto-discovery breakage. Session 2026-03-17 demonstrated this — adding an `agents` key to `plugin.json` without understanding auto-discovery semantics silently dropped 17 of 19 agents.

## plugin.json Auto-Discovery Rules

Claude Code auto-discovers components from default locations within a plugin directory. The `agents`, `skills`, and `commands` keys in `plugin.json` exist ONLY for declaring components in non-default locations.

**Default auto-discovered locations:**

- `agents/` — all `.md` files
- `skills/` — all skill directories containing `SKILL.md`
- `commands/` — all `.md` files
- `hooks/hooks.json` — hooks manifest

```mermaid
flowchart TD
    Q{Are ALL components in default locations?}
    Q -->|Yes — agents/ skills/ commands/ hooks/hooks.json| Omit["Omit agents/skills/commands keys from plugin.json<br>Auto-discovery registers everything"]
    Q -->|No — some components are in non-default paths| Declare["Declare ONLY the non-default paths<br>⚠️ Declaring a subset overrides auto-discovery<br>Unlisted components become invisible"]
    Omit --> Done([All components visible])
    Declare --> Warn["List EVERY component in that key<br>not just the non-default ones"]
    Warn --> Done
```

**Incident record (2026-03-17):** `python3-development` plugin had:

```json
"agents": ["./agents/t0-baseline-capture.md", "./agents/tn-verification-gate.md"]
```

Result: only 2 of 19 agents were registered. The other 17 were invisible to Claude Code because declaring a subset in `agents` overrides auto-discovery — the declared list becomes the complete list.

**Fix**: Remove the `agents` key entirely when all agents are in `agents/`. Auto-discovery registers all of them.

## Skill Validation vs Packaging

**Validation: YES** — Validate skills to ensure quality:

- YAML frontmatter properly formatted
- Required fields present (name, description, tools, model)
- File references correct and target files exist
- Directory structure valid

**Packaging: NO** — Skills in this repository are for local use. They are already in their final location. Do not package skills into .zip files — it creates unnecessary files and serves no purpose for local development.

## Plugin Runtime Files, Reload Lifecycle, and Versioning

**Plugin runtime files vs dev-context files**: A `CLAUDE.md` file inside a plugin directory is project-instruction context loaded only when Claude Code is run with that directory as cwd during plugin development. It is not a runtime plugin file, has no relation to plugin version, and is invisible to agents when the plugin is installed. Plugin runtime files are limited to `.claude-plugin/plugin.json`, `commands/`, `agents/`, `skills/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, and supporting `scripts/`. Do not treat `CLAUDE.md`, `README.md`, or `CHANGELOG.md` inside a plugin directory as authoritative for runtime behavior or version — the manifest at `.claude-plugin/plugin.json` is the source of truth. A plugin's `AGENTS.md` and `CONTEXT.md` are dev-context too: `CLAUDE.md` `@`-includes them, so they carry the same invisibility once installed.

**Where a behavioral instruction goes**: behavior specific to one agent belongs in that agent's own file — that body is its system prompt. Behavior shared across agents, or that a dispatched agent must carry, belongs in a skill named in the agent's `skills:` frontmatter; a subagent does not inherit skills loaded in its parent's conversation, so an unnamed skill never reaches it. Never file a runtime instruction (which subagent to dispatch, what contract to follow, how to handle an artifact) in a plugin's `AGENTS.md`, `CONTEXT.md`, or `README.md` — it reaches maintainers and never reaches the installed agent. An agent file cannot reference another file by relative path: it gets no `${CLAUDE_PLUGIN_ROOT}` substitution and its working directory is the consuming repository's root, so naming a skill to load is its only reliable cross-file reference. A dev-context file may name the skill that owns a behavior; it must not restate the behavior.

**Skill and plugin reload lifecycle**: Skills added or changed in the user or project `.claude/skills/` directory are immediately available after a change. Plugin changes to agents, skills, MCP servers, hooks, language servers, and other components require the plugin version to be bumped (this happens automatically after any commit that changes files in a plugin) and then `/reload-plugins` to pick up the new version from the cache — a full session restart is not required for this. A session restart is only sometimes needed for MCP service updates. To verify the cache is current, check that the plugin cache path includes the same version as the plugin.json: `~/.claude/plugins/cache/<marketplace>/<plugin-name>/<version>/`.

**Automatic version bumping**: `plugin.json` and `marketplace.json` are automatically bumped and staged by the pre-commit hook when any plugin file is modified — this is unchanged and remains the local-testing path: it's what makes `/reload-plugins` see your branch's edits without a session restart. Do not manually edit version fields for a normal local-commit workflow — the hook handles this, and after a successful commit the updated versions are already included.

Branch-side derivation cannot be collision-free on its own: two branches independently computing `origin/main`'s version + 1 can land on the same number, and a PR squash-merged via the GitHub UI/API never runs the local hook at all, so a plugin can also change on `main` with no bump whatsoever. `main` closes both gaps itself: after every push touching `plugins/**`, `.github/workflows/bump-marketplace.yml` runs `check_plugin_version_bump.py --repair` before the marketplace sync — an authoritative, idempotent post-merge pass that patch-bumps any plugin whose content changed without a version increase, regardless of what any branch's local hook did or didn't do. Manual version edits are not sanctioned under any circumstance — the repair job is now the correction mechanism for every case, including a merge that missed the hook entirely.

**Accepted cost**: because branch-side bumping is still active, a branch that keeps bumping while `main`'s repair job also bumps can occasionally hit a one-line `version`-field conflict on rebase (both sides changed the same JSON line). Resolve it by taking the higher version number, or by re-running the pre-commit hook — this is strictly less friction than the manual re-derivation a collision used to require.
