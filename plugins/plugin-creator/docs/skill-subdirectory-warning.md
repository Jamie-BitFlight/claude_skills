# Skill Subdirectory Warning

Skill directories nested under `skills/` silently fail to register — Claude Code only discovers
`skills/<name>/SKILL.md`, not `skills/<group>/<name>/SKILL.md`. Subdirectory colon-namespacing
(`plugin:group:skill-name`) is a `commands/` feature only; it does not extend to `skills/`.

- `skills/testing/foo/SKILL.md` → **DEAD — not registered**
- `skills/foo/SKILL.md` → `/plugin:foo` — **correct**

All skill directories must sit directly under `skills/` — one level deep only. Do not create
grouping subdirectories to organize related skills.

SOURCE: <https://agent-plugins.org/specification.md#71-skills> and
<https://code.claude.com/docs/en/plugins-reference.md#skills> (accessed 2026-09-24).
