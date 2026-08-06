# What Not To Use For Sharing Content

## `../other-skill/references/x.md` relative traversal

Does not resolve at runtime once a plugin is installed.

SOURCE: `plugins/plugin-creator/agents/ai-doc-optimizer.md:175` ("Never reference files inside
another skill's directory... won't resolve at runtime"); `plugins/plugin-creator/CLAUDE.md`
§Plugin Caching ("Plugins CANNOT reference files outside their directory").

## Symlinks

Degrade to plain files on a Windows checkout — git symlinks (mode 120000) become plain-text
files containing the link path, not the target content, unless the `repair-symlinks`
pre-commit hook runs first.

SOURCE: `AGENTS.md` §Gotchas item 3. Symlinks also carry their own validator error class,
`SL001` (malformed symlink target), documented in `plugins/plugin-creator/docs/ERROR_CODES.md`.

## Copy-paste

Creates the exact drift the `refactor-validator` agent's `No duplicate content across skills`
checklist item exists to catch — two copies that silently diverge the next time either one is
edited.
