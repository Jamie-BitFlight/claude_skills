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
explicit and detected target paths are implemented at lines 140–190 of
[`pr_review_cli_target.py`](../scripts/pr_review_cli_target.py).

The adapter uses `glab api --paginate --output ndjson` for list surfaces [1], reads every required
surface twice, and rejects the snapshot when the observations differ. It recomputes the remaining
absolute-deadline bound before each command. According to lines 100–234 of
[`pr_review_gitlab_transport.py`](../scripts/pr_review_gitlab_transport.py), this applies to
discussions, notes, award emoji, diff versions, merge-request detail, approvals, and the current
actor.

System notes remain provider metadata rather than review inputs. Named approvers and explicit
positive/negative award signals remain assessed inputs. Zero-required approval state remains
platform metadata and does not become an actor-backed approval. GitLab emits `codex_approved: null`
with `codex_approval_equivalence: unavailable`. According to lines 283–382 of
[`pr_review_gitlab_normalize.py`](../scripts/pr_review_gitlab_normalize.py), reviewability,
platform metadata, edit-aware exact-reference communication evidence, and the complete input census
all bind the snapshot fingerprint. Already-resolved inbound inputs remain outstanding until
provider-backed communication exists. The approval response fields retained by the adapter are
documented by GitLab's approvals API [4].

## Authorized Mutations

Every mutation takes the same complete snapshot and `READY_FOR_ACTION` cycle files as the GitHub
forms. Replace `--github` with the explicit GitLab target options above. Inline replies use the
discussion ID and quotes the exact stable input reference, resolution updates that discussion [2],
and top-level communication creates an MR note [3]. According to lines 83–210 of
[`pr_review_gitlab_provider.py`](../scripts/pr_review_gitlab_provider.py), the adapter validates the
created note or resolved discussion before returning success. Before any mutation, lines 20–47 of
[`pr_review_cli_actions.py`](../scripts/pr_review_cli_actions.py) fetch current provider state and
reject a saved revision or fingerprint that no longer matches.

## References

1. [glab api](https://docs.gitlab.com/cli/api/) (accessed 2026-09-22)
2. [Discussions API](https://docs.gitlab.com/api/discussions/) (accessed 2026-09-22)
3. [Notes API](https://docs.gitlab.com/api/notes/) (accessed 2026-09-22)
4. [Merge request approvals API](https://docs.gitlab.com/api/merge_request_approvals/) (accessed 2026-09-22)
