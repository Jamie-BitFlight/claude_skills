---
name: code-review-claude-skills
description: Loaded automatically when reviewing Claude skills or agent definitions — covers SKILL.md structure, frontmatter validity, token budget, description quality, and agent contract compliance.
user-invocable: false
---

# Claude Skills and Agent Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `SKILL.md`, agent frontmatter files, or `plugin.json` files are detected.

## Frontmatter Validity

- `name` must match the containing directory name exactly — mismatch causes lookup failures
- `name` must satisfy `^[a-z][a-z0-9-]*$` — lowercase letters, digits, hyphens only
- `description` must be a single-line string — no YAML multiline indicators (`>-`, `|-`, `>`, `|`)
- `description` must not contain colons (`:`) except in URLs — colons trigger YAML quoting requirements
- `tools` field (in agents) must be a comma-separated string, not a YAML array — `Read, Grep, Glob` not `[Read, Grep, Glob]`
- `model` must be one of `sonnet`, `opus`, `haiku`, or `inherit` — no version strings, no full model IDs
- Run `uvx skilllint@latest check <path>` after every frontmatter edit

## Description Quality

- The description is the primary routing mechanism when Claude selects from 100+ available skills — it must contain specific trigger keywords
- First 1024 characters are most important — front-load trigger conditions and activation signals
- Preferred trigger openers: "Use when", "Activates on", "Triggers on", "Loaded automatically when"
- Descriptions must be third-person ("Generates commit messages" not "I can help you generate")
- Vague descriptions produce missed triggers — "Helps with Python stuff" is a blocking finding

## Token Budget

- Skills must not include information Claude already has from training (general language patterns, well-known APIs, common idioms)
- Include only project-specific context, conventions, and domain knowledge that Claude cannot infer
- Skills over 4000 tokens should be flagged as oversized (warn); over 6400 tokens are blocking
- Inline examples are valuable — prefer 2-3 focused examples over exhaustive lists

## Scope of Tools

- `allowed-tools` in agent frontmatter must be scoped to the minimum required for the agent's task
- Agents that only review code must not have `Write` or `Edit` in their tools list
- Verification-only agents must not have destructive tools

## Non-Invocable Skills

- `user-invocable: false` must be set for skills intended only for agent context injection, not direct user activation
- `disable-model-invocation: true` must be set for skills that execute shell commands or other side-effecting operations that should not be run as prompts

## Agent Contracts

- All agents that return results to an orchestrator must include STATUS: DONE or STATUS: BLOCKED as the first line of their terminal response
- STATUS: BLOCKED must include a NEEDED section listing specific missing inputs
- STATUS: DONE must include an ARTIFACTS section listing what was produced and where
- Agents must not guess at missing inputs — BLOCKED is always correct when information is unclear

## File Reference Standards

- All file references in SKILL.md use markdown link syntax: `[text](./path/to/file.md)` with `./` prefix
- Skills in subdirectories under `skills/` silently fail to register — all skill directories must be directly under `skills/` (one level deep only)
- Cross-skill references use activation syntax — "For X, activate the `/plugin:skill-name` skill" — never backtick paths to other skills' internal files
- No `docs/` path references at runtime — developer documentation must not appear in agent-facing skill content

## Code Fence Requirements

- All code fences must have a language specifier — bare triple backticks are a blocking finding
- Nested code blocks use 4 outer backticks and 3 inner backticks
- Markdown links use `./` relative paths, not absolute paths or backtick references

## Plugin.json Auto-Discovery

- `agents`, `skills`, and `commands` keys in `plugin.json` are only for non-default locations — omit them when all components are in their default directories
- Declaring a subset of agents in the `agents` key overrides auto-discovery completely — unlisted agents become invisible
- If any component path is declared in `plugin.json`, every component in that category must be listed

## Anti-Patterns

```yaml
# WRONG: multiline description
description: >-
  This skill helps with TypeScript code review
  when the user asks for a review.

# RIGHT: single-line description
description: TypeScript-specific code review patterns covering strict mode, ESM, type safety, and branded types. Loaded automatically when reviewing TypeScript code.

# WRONG: colon in description (breaks YAML without quoting)
description: Code review: TypeScript patterns for strict mode and type safety.

# RIGHT: no colon
description: Code review for TypeScript — strict mode, type safety, branded types, and ESM patterns.
```

```markdown
<!-- WRONG: cross-skill backtick path reference -->
See `plugins/plugin-creator/skills/prompt-optimization/SKILL.md` for optimization patterns.

<!-- RIGHT: activation syntax -->
For prompt optimization, activate the `/plugin-creator:prompt-optimization` skill.
```
