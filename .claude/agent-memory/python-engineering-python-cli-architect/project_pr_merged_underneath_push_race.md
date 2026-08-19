---
name: pr-merged-underneath-push-race
description: A PR can get squash-merged by another process while you're mid-session verifying its review comments — always re-check `gh pr view --json state,mergedAt` right before pushing, and after pushing before trusting `gh pr checks`
metadata:
  type: project
---

While addressing PR #2987's follow-up Copilot review findings (2026-08-19), the PR got
squash-merged into `main` (commit `e9c1d72d`) by some other process partway through the
session — likely right after CI went green on an earlier commit (`487a06dc`), possibly via
auto-merge. I kept working, committed 6 more fix commits on the same local branch, pushed to
`origin section-name-registry-2970`, and `gh pr checks 2987` still showed all-green — but that
was **stale/cached CI output from the pre-merge run against `487a06dc`**, not a fresh run
against my new push. `gh pr view --json state` only then revealed `"state":"MERGED"`.

**Root cause of the false confidence**: `gh pr checks <N>` on an already-merged PR does not
error or warn — it just shows the last known check results, which can predate your own push if
the merge happened first. A closed/merged PR does not re-run CI on a subsequent push to its
now-detached branch.

**Verification protocol that would have caught this immediately**: run
`gh pr view <N> --json state,mergedAt,mergeCommit` right after any push that's meant to "update
the PR in place", and diff-check whether the merge commit's tree actually contains your new
content (e.g. `git show <mergeSha>:path/to/file.py | grep <marker only in your fix>`) — do not
trust `gh pr checks` alone as evidence the push landed where intended.

**Recovery when this happens**: the branch still holds your commits even though the PR is
closed. Create a new branch from `origin/main`, `git cherry-pick` just the commits that are not
yet an ancestor of `main` (`git log origin/main..origin/<old-branch>` to enumerate them), and
open a fresh PR — do not try to reopen or force-push into the merged PR's branch expecting it
to reflect in `main`.

See also [[project_ruff_fix_true_autofix.md]] for another "re-verify state before trusting a
prior read" pattern in this same repo.
