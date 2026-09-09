# Marketplace versioning

The repository uses the stock Python hook and GitHub Action from
[agent-marketplace-versioner](https://github.com/Jamie-BitFlight/agent-marketplace-versioner),
pinned to the same full commit SHA in `.pre-commit-config.yaml` and both versioning workflows.
There is no repository-specific adapter or versioner configuration.

Local commits synchronize and stage plugin versions through
`uv run prek run agent-marketplace-versioner`. These plugin versions are local development
cache busters: manual or automatic cache refresh can pick up changes during the session.
Marketplace membership changes locally when plugins are added or removed, but its version
bump belongs to the normal post-merge/default-branch release flow.
The `Local / Manifest sync` CI job also checks
the PR's actual base and head revisions; a missing version bump fails the quality gate.

After plugin changes merge, `bump-marketplace.yml` runs the shared `repair` and `sync` commands
against current `main`. Historical audits and collision repair remain available. The workflow
opens or updates `automation/marketplace-version-repair` as a normal PR instead of pushing to
`main`. Corrections take effect only after that PR passes checks and is reviewed and merged.
The generated title, `chore(marketplace): repair versions and synchronize catalog`, is owned
by the workflow: retain it in the merge commit message. The workflow recognizes it to avoid
opening another repair PR for its own merge, while ordinary required CI still runs.
All other plugin changes, including manifest-only edits, retain the original push trigger.

## Repair workflow credential

Before enabling automated repair delivery, a maintainer must configure the Actions secret
`VERSIONER_PR_TOKEN`: a fine-grained personal access token restricted to this repository with
Contents and Pull requests write permissions. A trusted GitHub App installation token with
the same permissions can also be supplied by the deployment's credential management.
The workflow fails before checkout or repair if the secret is absent.

The built-in `GITHUB_TOKEN` is unsuitable for this delivery path because its PR events do not
trigger the required downstream workflows. See the
[create-pull-request token requirements](https://github.com/peter-evans/create-pull-request#token).
The workflow token itself retains only Contents read permission; the repair credential does
not bypass branch protection, approve, or merge the PR.

## Existing plugin tools

The documented `plugins/plugin-creator/scripts/auto_sync_manifests.py` and
`check_plugin_version_bump.py` remain available for existing plugin users and their tests.
They are compatibility tools, no longer this repository's hook or CI implementation.
New infrastructure consumers should install the shared distribution. Keep fixes to shared
versioning behavior in that project rather than adding a consumer adapter here.
