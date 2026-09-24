# What Not To Use For Sharing Content

## `../other-skill/references/x.md` relative traversal

Does not resolve at runtime once a plugin is installed.

SOURCE: [Plugin caching and runtime paths](../../claude-plugins-reference-2026/references/caching-and-runtime.md)
and the runtime-escape audit owned by `/plugin-creator:lint`.

## Symlinks

Degrade to plain files on a Windows checkout — git symlinks (mode 120000) become plain-text
files containing the link path, not the target content, unless the `repair-symlinks`
pre-commit hook runs first.

SOURCE: `AGENTS.md` §Gotchas item 3. Symlinks also carry their own validator error class —
`skilllint` reports `SL001` for a malformed symlink target, with the explanation in its output.

## Copy-paste

Creates two copies that can silently diverge the next time either one is edited. Store the prose
once and point each consumer to it.
