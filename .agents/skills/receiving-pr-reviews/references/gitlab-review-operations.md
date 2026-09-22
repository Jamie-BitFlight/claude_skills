# GitLab Review Operations

Load this reference for a GitLab merge request. The review-cycle ordering in `SKILL.md` remains the
policy; this file supplies only GitLab target and transport facts.

## Target and Snapshot

Use an explicit self-managed target when it is known:

```bash
./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py fetch \
  --provider gitlab --host <hostname> --repo <namespace/project> --pr <IID>
```

Omit `--host` and `--repo` together to let `glab repo view` resolve the current checkout. The
provider operation is the authentication check; an environment token can work when persisted
`glab auth status` does not.

The adapter completely paginates discussions, notes, award emoji, and diff versions, and also reads
merge-request detail, approvals, and the current actor. System notes stay out of `review_inputs[]`.
Named approvers and positive/negative award signals remain assessed inputs. GitLab emits
`codex_approved: null` with `codex_approval_equivalence: unavailable`; zero required approvals never
becomes an actor-backed approval.

## Authorized Mutations

Every mutation takes the same complete snapshot and `READY_FOR_ACTION` cycle files as the GitHub
forms. Replace `--github` with the explicit GitLab target options above. Inline replies use the
discussion ID, resolution updates that discussion, and top-level communication creates an MR note.
The adapter validates the created note or resolved discussion before advancing local cycle state.

GitLab also exposes authenticated-actor approval state:

```bash
./.agents/skills/receiving-pr-reviews/scripts/pr_review_threads.py approval-state \
  --provider gitlab --host <hostname> --repo <namespace/project> --pr <IID> \
  --input-id <canonical-input-id> --approved \
  --snapshot-file review-snapshot.json --state-file review-cycle.json
```

Use `--unapproved` to withdraw approval. Approval uses the authorized snapshot revision as GitLab's
SHA guard, then reads the approval state back and succeeds only when the authenticated actor's state
matches the request. Approval changes neither assessment nor communication completion.

Sources:

- <https://docs.gitlab.com/api/discussions/> (accessed 2026-09-22)
- <https://docs.gitlab.com/api/merge_request_approvals/> (accessed 2026-09-22)
- <https://docs.gitlab.com/api/merge_requests/> (accessed 2026-09-22)
- <https://docs.gitlab.com/cli/api/> (accessed 2026-09-22)

