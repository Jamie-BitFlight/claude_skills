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
SHA, image digests, project commands, and explicit Git remote selection. Keep one version
component: use either `semantic-release-version` or `python-semantic-release-version`, never both
in one pipeline. Pass semantic-release both the selected remote name and repository URL.

Pin production component references to a reviewed commit SHA. A trusted immutable release tag is
also supported, but moving selectors such as a branch, a partial version, and `~latest` do not lock
the fetched configuration.

The consumer owns:

- `workflow:rules` and the complete `stages` list;
- release tag policy and every component's `rules` input;
- the project build and its preserved artifacts;
- one selected version adapter and all `needs` relationships; and
- digest-pinned runtime images.

Create `RELEASE_PUSH_TOKEN` as a masked, hidden, protected runtime variable with the minimum scope
needed to push the protected release tag and, for python-semantic-release, its release commit. Set
its environment scope to exactly the value passed as the version component's `environment` input;
the example uses `release-version`. The version job declares that environment with the `verify`
action. Tag publication jobs declare no environment and therefore do not receive the scoped token.
Protect both the default branch and release-tag pattern. Keep credentials out of component inputs,
and prefer an explicitly requested external secret where available.

The version components replace the selected remote's URL with the credential-free `repository-url`
input and export command-scoped Git configuration for all child processes. The first helper entry
resets inherited Runner helpers; the second returns `oauth2` and reads `RELEASE_PUSH_TOKEN` from the
runtime environment. This works when Runner sets `credential.interactive=never`, and prevents a
lower-precedence `CI_JOB_TOKEN` helper from winning. The secret value is not written to a file or
embedded in a repository URL. Generic package publication and GitLab Release creation use the job's
short-lived `CI_JOB_TOKEN`.

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
- under the target Runner's noninteractive credential configuration, a child Git process resolves
  the scoped release credential instead of inherited job-token helpers, while repository config,
  remote URLs, helper configuration values, and created files contain no release credential;
- a protected matching tag produces notes, one consumer build artifact, the Generic package, and
  the GitLab Release in dependency order; and
- the Catalog publication job exists only for a semantic-version tag and succeeds after component
  validation.

The root jobs execute only local, side-effect-free credential and Git-history fixtures. Before a
production component release, run the version, package, and GitLab Release components in an isolated
GitLab sandbox with disposable protected refs, a scoped credential, and disposable package names.
Require no-release, release, destination read-back, and release-last evidence; do not run those
mutating checks against a production project.

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
