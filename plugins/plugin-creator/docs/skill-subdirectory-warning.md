# Skill Subdirectory Warning

Skill directories nested under `skills/` silently fail to register — Claude Code only discovers
`skills/<name>/SKILL.md`, not `skills/<group>/<name>/SKILL.md`. Subdirectory colon-namespacing
(`plugin:group:skill-name`) is a `commands/` feature only; it does not extend to `skills/`.

- `skills/testing/foo/SKILL.md` → **DEAD — not registered**
- `skills/foo/SKILL.md` → `/plugin:foo` — **correct**

All skill directories must sit directly under `skills/` — one level deep only. Do not create
grouping subdirectories to organize related skills.

SOURCE: `.claude/rules/markdown-file-references.md`, section "Subdirectory Namespaces — Skills Do
NOT Support This" (repo-internal convention; added via commit `ea33cf2e`, 2026-03-22).
