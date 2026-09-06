# Maintenance notes

Design-time context for whoever edits this plugin. The executing agent never reads this file.

## Runtime environment rule (added 2026-09-06)

Two distributed plugins were found shipping paths that only resolve in the authoring repo:
agent-orchestration had links climbing to `../../../../rules/` and described a repo-level hook as
if consumers had it, and development-harness carried 37 such references. The rule forbidding this
lives in the repo's own `rules/` directory, which is design-time — no installed plugin can read
it, so plugin-creator could not pass it on to the plugins it builds. The rule now lives inside
this plugin at `docs/runtime-environment.md`, and the skills and agents that write or review
runtime text point at it.

`skills/lint/scripts/audit_runtime_escapes.py` makes the rule mechanical. It became the durable
artifact of that work: it started as a development-harness-specific scanner, and was generalised
here so one implementation serves every plugin rather than each re-stating the rule.

Two scanner exemptions are deliberate and were decided rather than discovered. Fenced blocks are
never findings, so a document can show an anti-pattern verbatim and still pass — without that,
`docs/runtime-environment.md` could not contain its own worked examples. Angle-bracket
placeholders are exempt because they name a shape that nothing resolves. Inline code spans and
table cells are not exempt, because real paths live in both.

The scanner's `_REPO_ROOT_DIRS` deliberately omits `scripts` and `docs`. Both are valid inside a
plugin — a skill bundles `scripts/`, and shared docs live at `${CLAUDE_PLUGIN_ROOT}/docs/` — so
flagging a bare `scripts/helper.py` reported portable code as broken. Removing them cut
plugin-creator's own count from 66 to 38 with no loss of real findings.

## Tracked follow-ups

Two temporary states in this plugin are tracked as backlog items rather than as notes here, so
they surface on a queue instead of waiting to be re-read:

- **#3429** — the ten SKILL.md pointers use a backticked `${CLAUDE_PLUGIN_ROOT}` path instead of
  a markdown link. That is a workaround for a skilllint LK001 false positive on relative
  invocation, and the item carries the verification command and the revert steps.
- **#3430** — six agents state the portability test inline because substitution in agent bodies
  is undocumented and unverified. The item carries the canary test that would settle it.

## Open: local-path SOURCE citations

Most of plugin-creator's remaining escapes are `SOURCE:` lines citing a local path
(`plugins/other-plugin/skills/x/SKILL.md`, `research/…`, `examples/…`). These sit at the
intersection of two repo rules: citations are required, and runtime text may not carry paths that
only resolve here.

Both are satisfiable. `rules/citation-requirements.md` asks skill derivations to link to the
source *repo* — a URL, which resolves everywhere and which the scanner does not flag. One
citation in this plugin already does it correctly, linking to
`https://github.com/anthropics/claude-plugins`. The remedy is therefore per-citation: an external
derivation becomes a URL, and provenance for an internal cross-plugin reference moves here, where
design-time content belongs.
