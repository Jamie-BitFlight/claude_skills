---
name: feedback-sandbox-guard-env-c-pipe-complexity
description: The worktree-isolation Bash guard refuses `env -C <dir> <cmd> | pipe` and `(cd dir && cmd) | pipe` combinations as "too complex to verify" even for read-only, non-git reproduction commands — not just git or shared-checkout targeting
metadata:
  type: feedback
---

Distinct from [[feedback_worktree_isolated_cwd_must_not_cd.md]] (which covers `cd` into the
*shared checkout* specifically): the sandbox also refuses `env -C /some/other/dir <cmd>` — even
targeting a harmless directory like `/tmp`, and even for read-only reproduction commands with no
mutation intent — whenever that invocation is combined with a pipe or multiple redirects in the
same call. Error text: "this command is too complex to verify that it stays inside the worktree,
break it into plain, separate commands."

**What triggered it**: `env -C /tmp uv run "$PATH" plan list 2>/dev/null || echo '...'` and
similar single-line combinations of `env -C` + `2>&1 | head` were refused, while the *same*
`env -C /tmp <cmd>` with only a trailing `2>/dev/null` (no pipe) succeeded.

**Workaround that worked**: drop the pipe/multi-redirect complexity — run `env -C /tmp <cmd>
2>&1` alone (view full output, no `| head`) or `env -C /tmp <cmd> 2>/dev/null` (no `| echo`
fallback chaining) as separate, simpler single calls, then reason about each result manually
rather than compressing verification into one dense one-liner. `export VAR=...` in one Bash call
does NOT persist to the next call (shell state resets per call per the tool's own contract) — so
this workaround only helps within a single call, not across two.

**How to apply**: when reproducing a cwd-dependent bug (e.g. hardcoded relative paths) inside a
worktree-isolated session, keep each verification command to a single redirect/pipe operation.
Split "run from a different cwd" + "suppress stderr" + "pipe to head" + "fallback echo" into
separate Bash calls instead of one compound line, even when targeting a directory that has
nothing to do with git or the shared checkout.
