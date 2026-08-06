# Verification Steps

1. Canary the substitution form before relying on it in a new context — activate
   `/example-argument-substitution` and confirm the variable resolves as expected. Do not
   assume a confirmed result from one runtime carries over to an unverified one. SOURCE for the
   `${CLAUDE_PLUGIN_ROOT}` confirmation this skill relies on: canary test, 2026-08-06 — a
   control line plus two `${CLAUDE_PLUGIN_ROOT}` lines (one plain prose, one a markdown link
   target) added to a live `SKILL.md` body outside any bash-injection block; all three resolved
   to the plugin's real absolute path after a plugin reload, with the no-variable control line
   ruling out stale or dropped content as the explanation.
2. Run `uvx skilllint@latest check <plugin-path>` after adding or changing a reference.
3. Confirm every annotated target file exists at the path named in the link.
