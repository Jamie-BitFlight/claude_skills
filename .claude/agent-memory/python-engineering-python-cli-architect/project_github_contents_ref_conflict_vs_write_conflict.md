---
name: project-github-contents-ref-conflict-vs-write-conflict
description: github_contents.py's _content_branch() conflict handling for create_git_ref vs put()'s content-write conflict handling -- why they use different status sets and why ref conflicts need re-verification
metadata:
  type: project
---

`plugins/development-harness/backlog_core/backends/github_contents.py` has two distinct
GitHub-conflict-handling code paths that must NOT share a status-code constant, even though
both originally used `_CONFLICT_STATUSES = frozenset({409, 422})`:

- **Content writes** (`put()`, via `create_file`/`update_file`): on 409 or 422, re-read the
  target path (`_existing()`) and diff its revision against what was expected. There's always a
  revision to compare, so both statuses safely route through the same "re-read and diff" logic.
- **Branch creation** (`_content_branch()`, via `create_git_ref`): GitHub's Git References API
  only documents `422` ("Reference already exists") for this race. There's no revision to diff --
  only branch *existence* to check. Fixed 2026-08-16/17 (PR #2918 follow-up commit `d84c666f`)
  after independent review found `_content_branch()` treated ANY 409/422 as "branch is ready"
  without re-verifying, so a false conflict (transient ref-lock, secondary-rate-limit-as-422,
  malformed-sha 422) permanently set `self._branch_ready = True` with no self-heal path, and every
  subsequent op then 404'd against a git ref that was never created.

Fix pattern (mirrors `put()`'s `_existing()` re-read, applied to branch existence instead of
content revision): give ref-creation its own constant (`_REF_ALREADY_EXISTS = 422`, no 409), and
on that specific conflict call `repository.get_branch(_CONTENT_BRANCH)` before trusting the
conflict -- raise `ContentUnavailableError` if the branch still can't be found.

**Why:** two structurally similar-looking "GitHub said 409/422" branches in the same file had
different correctness requirements (diff-a-revision vs confirm-existence) hidden behind one shared
constant name — a classic case where a constant meant "one HTTP status set" but was actually
encoding two unrelated business rules.

**How to apply:** before reusing `_CONFLICT_STATUSES` for a new GitHub write path in this file,
check whether the new path has a revision/SHA to re-read on conflict. If not (pure existence
checks, like ref/branch creation), it needs its own re-verification step and its own status
constant — don't fold it into `_CONFLICT_STATUSES`.

See also [[project_ty_socket_getaddrinfo_typing]] for the general pattern of not trusting a
library's status-code contract without checking real behavior; [[project_ruff_fix_true_autofix]]
for this repo's ruff auto-fix behavior encountered during the same fix.
