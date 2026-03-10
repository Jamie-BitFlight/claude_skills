# Memory and Rules — What Belongs Here

SOURCE: [claude-md-management plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management), quality-criteria.md (accessed 2026-03-10)

CLAUDE.md and `.claude/rules/` files are project-specific instruction sets. They load into every session, so every token they contain is paid on every request.

## What to Write

**Commands that aren't obvious from the repo** — build, test, lint, deploy. Not "run tests with pytest" — the reader knows that. Yes to "use `uv run prek run --files <file>` not `pre-commit`."

**Non-obvious patterns and gotchas** — things that would cause repeated mistakes without documentation. "Git remote points to `127.0.0.1`, not `github.com` — pass `-R owner/repo` on every `gh` command."

**Decisions already made** — tool choices, style preferences, workflow gates. State the decision, not the reasoning behind it unless the reasoning changes behavior.

**Path-scoped rules** — use YAML frontmatter `paths:` when a rule only applies to specific file types.

## What Not to Write

**Generic best practices** — Claude already knows them. "Use descriptive variable names" adds nothing.

**Discoverable facts** — current versions, available commands, file listings. These go stale and become wrong instructions.

**Procedures Claude can execute without guidance** — "fetch the URL, read the tag, extract the major version" describes something Claude does automatically. Write the constraint ("verify before writing") not the procedure.

**Invented constraints from a single session** — if a rule was added because of one incident and has no verified ongoing basis, question whether it belongs permanently in memory.

## The Test

Before writing a line: "Would Claude get this wrong without it?"

If no — cut it.
If yes — write the minimum that prevents the mistake.

## Format

One fact per bullet. No tables of data that change. No multi-step procedures for standard operations. No examples unless the format itself is non-obvious.
