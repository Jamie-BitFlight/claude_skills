---
name: pr-merged-underneath-push-race
description: "A PR can be squash-merged mid-session; after pushing, confirm gh pr view --json state,mergedAt before trusting gh pr checks, and cherry-pick unmerged commits onto a fresh main branch if it merged"
metadata:
  type: project
---

Auto-merge can squash-merge a PR as soon as CI goes green on an earlier commit, while you are still pushing fixes to its branch. On a merged PR, `gh pr checks <N>` shows the last pre-merge results without any warning, and CI does not re-run on later pushes. A green check list is therefore no evidence that your push landed.

After any push meant to update a PR in place, run `gh pr view <N> --json state,mergedAt,mergeCommit`. If `state` is `MERGED`, list the commits that did not land (`git log origin/main..origin/<branch>`), cherry-pick them onto a new branch cut from `origin/main`, and open a fresh PR.
