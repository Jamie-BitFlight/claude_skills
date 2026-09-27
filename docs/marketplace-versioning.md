# Marketplace versioning

Patch bumps are assigned once, by CI, after changes land on `main`. The pre-commit hook never
bumps a version, so open PRs that touch the same plugin no longer conflict on the `version` line of
its manifests. A PR may still set a deliberate version, such as a minor or major bump.

The repository uses the stock hook and GitHub Action from
[agent-marketplace-versioner](https://github.com/Jamie-BitFlight/agent-marketplace-versioner),
pinned to the same moving `v1` tag in [.pre-commit-config.yaml](../.pre-commit-config.yaml) and
[bump-marketplace.yml](../.github/workflows/bump-marketplace.yml). The workflow resolves `v1` on
each run. A local hook environment keeps the release it first installed; run
`prek clean && prek install --install-hooks` to pick up a newer `v1`.

## On a branch

The `agent-marketplace-versioner-check` pre-commit hook runs `reconcile --dry-run --staged`. It changes no files.
It fails when a `plugin.json` that lists `skills`, `agents` or `commands` explicitly is missing one
that exists on disk (or lists one that does not), or when a marketplace catalog
(`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) lacks an entry for a plugin
directory under `plugins/`, has a local (`./`) entry for a directory that does not exist, or names a
local entry differently from its `plugin.json`. Entries with an external source (`github`,
`git-subdir`) are not checked; keep them. Fix the reported entry by hand. The `Local / Manifest sync` CI job runs the same hook on every PR
that touches plugins.

To release a minor or major version, set it in the PR. `repair` counts a version change as that
plugin's bump, so it adds no further patch bump after merge. Set a version above `main`'s current
value: `repair` does not correct a lower one.

Branch commits no longer bump a plugin's version automatically, so the plugin cache keyed on that version does
not refresh from branch work. To exercise a plugin from your working copy, load it directly:
`claude --plugin-dir plugins/<name>`.

## On main

[bump-marketplace.yml](../.github/workflows/bump-marketplace.yml) runs on every push to `main`:

1. `repair` patch-bumps every plugin manifest (`.claude-plugin`, `.codex-plugin`, `.cursor-plugin`)
   whose directory changed after the commit
   that last changed that manifest's version. Several PRs merged before a run are covered by one
   bump per plugin. A plugin added by a merge keeps the version it was added with.
2. `sync --marketplace` bumps `.claude-plugin/marketplace.json`'s `metadata.version` once for the
   changes since the last version commit (or, before the first one exists, since the triggering
   commit's parent): a major bump if a plugin was removed, a minor bump if one was added, and a
   patch bump if only plugin contents changed.
3. The result is pushed to `main` as one commit titled
   `chore(plugins): assign plugin versions`. If another merge landed meanwhile, the commit is
   rebased onto it and pushed again (three attempts).

Loop guard: the version commit's push starts one more run, which finds nothing changed since the
last bump and exits without committing or pushing. That run is not skipped on purpose. Runs share
one concurrency group, and GitHub cancels a pending run when a newer one queues. If a merge lands
while a run is active, the version commit's run can replace that merge's pending run, so it must
process the merge. Every run starts from the newest `main` and bumps everything not yet versioned.

## Credential and ruleset bypass

The default-branch ruleset requires a pull request and the `Quality Gate` check, and the built-in
`GITHUB_TOKEN` is not on its bypass list. The workflow therefore pushes with a GitHub App
installation token. Before the workflow can push, a maintainer must:

- Create or choose a GitHub App installed on this repository with **Contents: read and write**.
- Add that App to the `push-protection` ruleset's bypass list with mode **Always**.
- Set the repository variable `VERSIONER_APP_CLIENT_ID` to the App's client ID.
- Set the repository secret `VERSIONER_APP_PRIVATE_KEY` to a private key for the App.

The workflow fails before checkout if either value is missing.

## Changing versioning behavior

Fix shared versioning behavior in [agent-marketplace-versioner](https://github.com/Jamie-BitFlight/agent-marketplace-versioner),
then move the pin in `.pre-commit-config.yaml` and `bump-marketplace.yml` together.
[test_marketplace_versioner_integration.py](../tests/test_marketplace_versioner_integration.py) checks that both pins match and runs the pinned
hook and action against a fixture repository.
