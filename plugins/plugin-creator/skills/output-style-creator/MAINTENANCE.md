# Skill maintenance

## Sources of truth

- Claude Code output styles
  - Source: <https://code.claude.com/docs/en/output-styles>
  - Governs: built-in style roster, frontmatter fields, install levels, and every Claude Code
    version threshold quoted in `SKILL.md` and `references/output-style-schema.md` — grep those
    files for `v2.` to enumerate them rather than trusting a copy of the list kept here
  - Version/ref: live documentation
  - Accessed: 2026-09-13
  - Refresh when: a built-in style is added or renamed, or a quoted version threshold is superseded
    by a newer Claude Code release
- Claude Code plugins reference
  - Source: <https://code.claude.com/docs/en/plugins-reference>
  - Governs: the `outputStyles` manifest key replacing the default `output-styles/` scan, and which
    plugin components `/reload-plugins` picks up
  - Version/ref: live documentation
  - Accessed: 2026-09-13
  - Refresh when: the manifest merge rules for `outputStyles` change

`plugin-creator:claude-skills-overview-2026`'s `resources/output-styles.md` mirrors the same upstream
page. Re-sync both together via `plugin-creator:skill-sync`.
