# Maintenance notes

Design-time context for whoever edits this plugin. The executing agent never reads this file.

## Runtime environment rule (added 2026-09-06)

Two distributed plugins were found shipping paths that only resolve in the authoring repo:
agent-orchestration had links climbing to `../../../../rules/` and described a repo-level hook as
if consumers had it, and development-harness carried 37 such references. The rule forbidding this
lives in the repo's own `rules/` directory, which is design-time — no installed plugin can read
it, so plugin-creator could not pass it on to the plugins it builds.

The rule is stated inline in every skill and agent that writes or reviews runtime text; grep the
shared predicate `bundled and reached by a relative path inside the plugin` to find each copy,
and change all of them together. Do not reintroduce a shared doc for it: the one that briefly
existed was reached by a `${CLAUDE_PLUGIN_ROOT}/docs/…` pointer, so the plugin depended on a
harness substitution in order to deliver the advice not to. Which harnesses substitute that
variable, and how well that is established, is recorded in `CLAIMS-REGISTER.md`.

`skills/lint/scripts/audit_runtime_escapes.py` makes the rule mechanical. It became the durable
artifact of that work: it started as a development-harness-specific scanner, and was generalised
here so one implementation serves every plugin rather than each re-stating the rule.

Two scanner exemptions are deliberate and were decided rather than discovered. Fenced blocks are
never findings, because a fenced block is an illustration rather than an instruction, so a
document can show an anti-pattern verbatim and still pass. Angle-bracket placeholders are exempt
because they name a shape that nothing resolves. Inline code spans and table cells are not
exempt, because real paths live in both.

## Claims this plugin depends on

Warrants — source, date, and the re-check that would overturn each — live in
`CLAIMS-REGISTER.md` beside this file, not here and never in runtime text. The claim this
plugin's own structure rests on: `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` are
substituted in a `SKILL.md` body and not inside `references/*.md`. That is why no `references/`
file here carries a variable-built path. Re-check it per the register before anything new
depends on it.

The scanner's `_REPO_ROOT_DIRS` deliberately omits `scripts` and `docs`. Both are valid inside a
plugin — a skill bundles `scripts/`, and a plugin may bundle shared docs at its root `docs/` —
so flagging a bare `scripts/helper.py` reported portable code as broken. Removing them cut
plugin-creator's own count from 66 to 38 with no loss of real findings.

## Tracked follow-ups

Open states touching this plugin are tracked as backlog items rather than as notes here, so they
surface on a queue instead of waiting to be re-read. Each item's text predates the deletion of the
shared doc, so read it against the current tree:

- **#3429** — filed when ten SKILL.md pointers used a backticked `${CLAUDE_PLUGIN_ROOT}` path to
  work around a skilllint LK001 false positive on relative invocation. Those pointers are gone,
  so the item's revert steps have no target; the LK001 defect it documents is still real. Re-scope
  it to the skilllint bug or close it.
- **#3430** — asks whether agent bodies substitute `${CLAUDE_PLUGIN_ROOT}`. Its resolution branch
  would point the agents at the deleted doc; the rule is now inlined everywhere by decision, so
  the canary still answers `rules/skill-substitution.md`'s open question but changes nothing here.
- **#3445** — the scanner skips every variable-built path (`_PORTABLE_PREFIXES`) on a premise it
  cannot check. Emptying that tuple leaves plugin-creator's count at 38 (measured 2026-09-06):
  the deleted pointers were backticked prose, not links, and `docs` is outside `_REPO_ROOT_DIRS`,
  so the scanner has no detector for that class at all. The fix is a detector, not removing the
  exemption.

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
