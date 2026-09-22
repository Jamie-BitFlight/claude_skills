# GitLab review operations

Read this reference for every GitLab merge request. The shared review-cycle contract supplies the
policy; this branch supplies GitLab target, availability, and transport semantics.

## Target and collection

Select GitLab and bind the MR IID to its project. For a known self-managed target, provide its bare
host and full namespace/project; otherwise let `glab repo view` resolve the current checkout. Failed
or ambiguous detection stops rather than guessing. Run `fetch --help` for current syntax.

The adapter paginates every list surface and obtains a stable complete observation of discussions,
notes, award emoji, diff versions, MR detail, approvals, and the current actor. A missing page,
unstable collection, schema failure, or exhausted bound yields `SNAPSHOT_INCOMPLETE` or `ERROR`.

System notes remain observable provider metadata, not actor-backed review inputs. Named approvers and
explicit positive or negative award signals remain inputs. Platform approval configuration with no
actor is metadata. GitLab has no established equivalent of GitHub's exact Codex approval convention,
so `codex_approved` stays null and its equivalence stays unavailable. Never infer approval from a
zero-required approval state.

Already-resolved inbound inputs remain outstanding until exact-reference, provider-backed
communication exists. The canonical fingerprint includes reviewability, provider metadata, edit-aware
communication evidence, and the complete input census.

## Authorized actions

Use the same complete snapshot and cycle evidence as every other provider; run each mutation command's
`--help` for current target options. Inline replies use the discussion target and quote the exact
stable input reference. Resolution updates that discussion only after the reply succeeds. Top-level
communication creates an MR note. The adapter validates the created note or resolved discussion
before reporting success.

When a GitLab object cannot be resolved, complete its provider-backed communication and record
resolution as `unavailable`. A capability absence is not a successful resolution. Re-fetch before the
first mutation; a changed revision, fingerprint, body, edit time, state, or target returns to the full
census.

## Platform references

- [glab API command](https://docs.gitlab.com/cli/api/)
- [Discussions API](https://docs.gitlab.com/api/discussions/)
- [Notes API](https://docs.gitlab.com/api/notes/)
- [Merge request approvals API](https://docs.gitlab.com/api/merge_request_approvals/)
