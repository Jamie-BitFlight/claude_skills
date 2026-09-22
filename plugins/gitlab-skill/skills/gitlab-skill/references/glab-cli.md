# glab CLI Preflight and Branch Index

Use these forms with `glab 1.118.0`. Run the selected subcommand's `--help` before adapting a form to
another installed version.

## Common Preflight

- Environment API authentication: confirm `GITLAB_TOKEN` is present without printing it, then call
  `glab api --hostname "$HOST" user`.
- Persisted authentication: use `glab auth status --hostname "$HOST"` only when persisted login is
  the subject.
- Git transport: use the user-supplied SSH URL. REST authentication does not test Git transport.
- Self-managed raw API calls use a bare hostname and external `jq`; encode namespaced project paths
  or use the numeric project ID.

Select one branch:

- [API and Repository Selection](./glab-api-and-repository.md) - Load for raw REST/GraphQL calls,
  pagination, typed fields, explicit repository selectors, or Git transport.
- [CI Read-Only Inspection](./glab-ci-inspection.md) - Load for listing pipelines, inspecting one
  pipeline and its jobs, tracing a requested completed job, or CI Lint.
- [Merge Request Commands](./glab-merge-requests.md) - Load for non-interactive MR create/merge
  command composition or command-local scratch-clone identity.
- [Release Credential Operations](./glab-release-credentials.md) - Load for protected branch/tag
  setup, project-token/variable creation or inspection, existing-resource decisions, or rotation.

Completion criterion: the selected branch names the intended host/project explicitly, uses only
flags exposed by installed help, and keeps credential values out of output.

SOURCE: <https://docs.gitlab.com/cli/> (reviewed 2026-09-22; common preflight live verified with `glab 1.118.0`)
