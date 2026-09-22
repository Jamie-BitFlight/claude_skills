# glab CLI Preflight and Branch Index

Use these forms with `glab 1.118.0`. Run the selected subcommand's `--help` before adapting a form to
another installed version.

## Common Preflight

Run this from the target repository. `glab` infers the GitLab host from repository context and uses
the credential selected by its normal resolution. Every downstream glab/API branch uses that same
resolved credential unless the task explicitly requires a named environment variable. On failure,
request that the user authenticate or correct the credential selected for this repository and
preserve the probe status.

```bash
glab api --silent user >/dev/null || { rc=$?; printf '%s\n' 'glab authentication failed: ask the user to authenticate or correct the credential selected for this repository' >&2; exit "$rc"; }
```

- Self-managed raw API calls use a bare hostname and external `jq`; encode namespaced project paths
  or use the numeric project ID.

Select one branch:

- [API and Repository Selection](./glab-api-and-repository.md) - Load for raw REST/GraphQL calls,
  pagination, typed fields, explicit repository selectors, or Git transport.
- [CI Context Index](./glab-ci-inspection.md) - Load to choose unmerged local candidate validation or
  post-merge/existing-ref inspection.
- [Merge Request Commands](./glab-merge-requests.md) - Load for non-interactive MR create/merge
  command composition or command-local scratch-clone identity.
- [Release Credential Operations](./glab-release-credentials.md) - Load for protected branch/tag
  setup, project-token/variable creation or inspection, existing-resource decisions, or rotation.

Completion criterion: the selected branch names the intended host/project explicitly, uses only
flags exposed by installed help, and keeps credential values out of output.

SOURCE: <https://docs.gitlab.com/cli/> (reviewed 2026-09-22; common preflight live verified with `glab 1.118.0`)
