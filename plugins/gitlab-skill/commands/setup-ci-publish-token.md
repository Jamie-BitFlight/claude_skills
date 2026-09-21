---
description: Create a GitLab project access token for CI/CD operations that require elevated permissions
---

# Setup CI Publishing Token

This command launcher is available in Claude Code only because `${CLAUDE_PLUGIN_ROOT}` substitution is measured only there. The Python companion is cross-platform; no launcher is claimed for Codex, Hermes, Kimi, or other harnesses.

Use a project access token only when a CI/CD operation cannot use the preferred release-asset route: `CI_JOB_TOKEN`, `GLAB_ENABLE_CI_AUTOLOGIN=true`, and `glab release create --use-package-registry`.

## Prerequisites

- Python 3.11+ and `uv`.
- Current `glab` on `PATH`.
- `GITLAB_TOKEN` or `GL_TOKEN` set to a personal access token with `api` scope and Maintainer or Owner access. GitLab's project access-token API does not permit creating a project token while authenticated with another project token.
- Run from the Git repository root. Set `CI_PROJECT_PATH` and `GITLAB_HOST` only when the origin remote does not identify the intended GitLab project.
- GitLab.com Premium or Ultimate for project access tokens; GitLab Self-Managed and Dedicated support them with any license.

## Run

Claude Code resolves the installed plugin root in:

```text
uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/setup_ci_publish_token.py"
```

The companion uses `glab` directly without a shell, `jq`, or platform-specific utilities. It verifies the personal token's `api` scope and Maintainer access, pages through matching active tokens and variable scopes, and treats an expiration date equal to the current UTC date as expired. It creates uniquely named replacements and reports ambiguous active tokens or variable scopes without choosing one.

`CI_PUBLISH_TOKEN` is created protected, masked, and hidden. An existing hidden variable is updated non-destructively. Unknown hidden state stops without mutation. Because GitLab does not allow a readable existing variable to become hidden through update, that migration captures the value and metadata before delete/recreate, preserves scope, type, raw behavior, and description, and enforces hidden, masked, protected storage. Failed readable migration restores the original; a failed token-create reconciliation revokes the new token. Combined failures are reported without printing the secret. Variable values are passed to `glab variable set` or `glab variable update` only on standard input.

A timeout, connection/protocol failure without an explicit GitLab HTTP rejection, or undecodable required response after a mutating request does not establish whether GitLab committed it. The companion reports the indeterminate operation and non-secret token name or ID, then stops without rollback or token cleanup that could invalidate a hidden value. Zero-exit undecodable output is ignored only for mutations whose callers require no output; token creation remains indeterminate because its ID and secret are required. For an indeterminate create it checks the exact generated name and revokes only when that token is unambiguous; otherwise inspect project access tokens and `CI_PUBLISH_TOKEN` in GitLab before retrying. No automatic recovery is claimed for an unknown remote state.

Hidden variables cannot be revealed after creation. Masking only replaces exact matching output, subject to GitLab's masking restrictions, and protected variables are available to a protected branch or protected tag and optionally eligible merge-request pipelines.

## Preferred Release Route

For release assets, use the job token through GitLab's package-registry route:

```bash
GLAB_ENABLE_CI_AUTOLOGIN=true glab release create "${CI_COMMIT_TAG}" ./dist/* --use-package-registry
```

Do not assign `CI_JOB_TOKEN` to `GITLAB_TOKEN`; `glab` sends these token types in different headers.

## Behavior

| Token state | Variable state | Action |
| --- | --- | --- |
| Missing | Missing, hidden, or readable | Create a unique token and reconcile the variable; revoke the token if reconciliation fails |
| Expired at or before today's UTC date | Missing, hidden, or readable | Store a unique replacement, then revoke the superseded ID; on write failure revoke only the new token |
| Valid | Missing | Create and store a new token, then revoke the old token by ID |
| Valid | Present, not hidden | Transactionally recreate it as hidden |
| Valid | Present, hidden | Make no change |
| Any | Hidden metadata unavailable | Stop without mutation |
| Any | Mutating request timed out | Report indeterminate state and require inspection before retry |

## Troubleshooting

- A protected variable is available only to pipelines on protected branches or protected tags, and optionally eligible merge-request pipelines. Check Settings > Repository > Branch rules or Settings > Repository > Protected tags.
- If multiple matching active tokens are reported, revoke all but the intended token and rerun the command.
- For release assets, confirm CI auto-login and `--use-package-registry` before introducing a broader project access token.

## Sources

- [GitLab project access tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/)
- [Project access tokens API](https://docs.gitlab.com/api/project_access_tokens/)
- [Project-level CI/CD variables API](https://docs.gitlab.com/api/project_level_variables/)
- [`glab token`](https://docs.gitlab.com/cli/token/)
- [`glab variable set`](https://docs.gitlab.com/cli/variable/set/)
