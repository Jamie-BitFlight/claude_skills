# GitLab Release Components

This directory mirrors a dedicated GitLab CI/CD component project. Copy the tree to its own
project, keep the top-level `templates/` directory, and publish all components together.

## Components

`component-manifest.json` is the authoritative template inventory. Each listed file under
`templates/` is one independently consumable contract published at the project version.

Each component exposes its job name, stage, rules, image, and component-specific configuration as
typed inputs. The components use predefined GitLab variables for pipeline and project identity.
They do not define workflow admission, a stage list, global defaults, global variables, or a build.

## Consume

Start from `examples/consumer.gitlab-ci.yml`. Replace the component project path, component commit
SHA, image digests, project commands, and explicit credential-free HTTPS Git remote selection. Keep one version
component: use either `semantic-release-version` or `python-semantic-release-version`, never both
in one pipeline. Pass semantic-release both the selected remote name and repository URL.

Pin production component references to a reviewed commit SHA. A trusted immutable release tag is
also supported, but moving selectors such as a branch, a partial version, and `~latest` do not lock
the fetched configuration.

Ensure the actor that creates the release tag can fetch every component in the resulting tag
pipeline. A project-access-token bot cannot be added to another private project. For that release
identity, host components in a public project, an internal project visible to the bot, or use a
different release actor with Reporter-or-higher access to the private component project.

The consumer owns:

- `workflow:rules` and the complete `stages` list;
- release tag policy and every component's `rules` input;
- the project build and its preserved artifacts;
- one selected version adapter and all `needs` relationships; and
- digest-pinned runtime images.

Pass a collision-free CI variable name through `credential-variable`; the example uses
`PROJECT_RELEASE_PUSH_TOKEN`. Create that variable as masked, hidden, protected, raw, and scoped
exactly to the version component's `environment` input. Hidden is creation-only: if an existing key
is not hidden, create a new key instead of expecting update to hide it. Create a protected, raw,
non-secret companion named `<credential-variable>_SHA256` with the same environment scope and the
credential's lowercase SHA-256 digest. Protect both the default branch and release-tag pattern.

The version job validates the variable name and digest before changing the selected remote. It then
binds `Authorization: Basic ...` as command-scoped `http.extraHeader` only to the release process,
scoped to the selected remote's effective HTTPS URL after Runner `insteadOf` rewriting. This
overrides host-specific job-token credentials without sending the release header to other HTTPS
hosts. The secret stays out of component inputs, repository URLs, files, persisted Git config, and logs. The Python adapter uses
`--no-vcs-release`, supplies no GitLab API token, and keeps `ignore_token_for_push` enabled so Git
transport remains on the Basic header. Tag publication jobs have no version environment and use
their short-lived `CI_JOB_TOKEN`.

After changing a component pin, included configuration, variable metadata, credential value, or
digest companion, start a new pipeline. Retrying a job reuses the prior pipeline configuration.

## Test And Publish

The root `.gitlab-ci.yml` includes every component from
`$CI_SERVER_FQDN/$CI_PROJECT_PATH/...@$CI_COMMIT_SHA` and supplies every mandatory input. Before
publication, require observable evidence that:

- the root pipeline compiles every manifest-listed same-SHA include without an unknown or missing
  input;
- `validate-component-tree` confirms the manifest's exact templates at the tagged commit;
- default-branch and protected matching-tag simulations admit the intended jobs while a
  nonmatching tag admits none of the release jobs;
- a selected version component succeeds for both no-release and release-worthy histories;
- under the target Runner's noninteractive credential, `insteadOf`, and host-helper configuration,
  both release processes receive the selected Basic header while repository config, remote URLs,
  files, and logs contain no release credential;
- a protected matching tag produces notes, one consumer build artifact, the Generic package, and
  the GitLab Release in dependency order; and
- the Catalog publication job exists only for a semantic-version tag and succeeds after component
  validation.

The root component-project credential job validates process-scoped Git configuration without making
an HTTP request. The repository pytest fixture validates both generated shell wrappers and their
process-scoped Git transport against local HTTPS; it does not execute either release tool. The
semantic-release adapter additionally has live GitLab proof. The hardened project `595` rerun also
live-verified python-semantic-release through its initiating, release-commit, and tag pipelines.
Before a production component release, run the version, package, and GitLab Release components in an isolated GitLab
sandbox with disposable protected refs, a scoped credential, and disposable package names. Require
no-release, release, destination read-back, and release-last evidence; do not run those mutating
checks against a production project.

Before the Catalog job can publish, an Owner must enable the project's CI/CD Catalog setting. The
project must have a description, and the tagged commit must contain the root `README.md` and at
least one component under `templates/`. A Maintainer or Owner then creates a semantic-version tag;
the tag pipeline uses GitLab's `release` keyword to publish the Catalog version after validation.
Consumers can use that immutable release or pin a reviewed commit SHA.

SOURCE: <https://docs.gitlab.com/ci/components/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/inputs/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/variables/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/components/#publish-a-new-release> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/environments/#limit-the-environment-scope-of-a-cicd-variable> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/environments/#access-an-environment-for-preparation-or-verification-purposes> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/secrets/> (accessed 2026-09-22)
SOURCE: <https://semver.org/spec/v2.0.0.html> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/jobs/job_rules/#compare-a-variable-to-a-regular-expression> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/user/project/settings/project_access_tokens/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/variables/#hide-a-cicd-variable> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/jobs/job_troubleshooting/#a-cicd-job-does-not-use-newer-configuration-when-run-again> (accessed 2026-09-22)
SOURCE: <https://git-scm.com/docs/git-config#Documentation/git-config.txt-httpextraHeader> (accessed 2026-09-22)
SOURCE: <https://gitlab.com/gitlab-org/gitlab-runner/-/raw/v18.7.1/shells/abstract.go> (accessed 2026-09-22)
