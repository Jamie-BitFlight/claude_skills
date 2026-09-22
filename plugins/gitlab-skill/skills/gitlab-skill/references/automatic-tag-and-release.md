# Automatic Tag and Release Lifecycle

Compose the lifecycle from self-contained components and consumer-owned orchestration. The consumer
configuration is the authority for workflow admission, complete stage order, release policy,
project build, dependencies, and one selected version adapter.

## Invariant State Machine

Every default-branch push runs exactly one version component.

1. The selected version component evaluates the push.
2. No release: evaluation succeeds, creates no version tag, and terminates the lifecycle.
3. Release: evaluation pushes one protected version tag with an authorized non-job-token Git
   credential. The ordinary tag push starts a separate tag pipeline.
4. The tag pipeline generates one release-description artifact, runs the consumer-owned build once,
   publishes the immutable build output to each selected destination, then creates one GitLab
   Release.
5. The GitLab Release targets the existing tag and starts only after every publication succeeds.

SOURCE: <https://docs.gitlab.com/ci/> (reviewed 2026-09-22; lifecycle composition)

## Intake

Read the current project before composing the consumer pipeline: GitLab target and remote, actual
default branch, existing workflow admission and jobs, complete stage list, one version adapter,
release policy and tag format, release-commit behavior, protected credential interface, notes
artifact, project build command and outputs, publication destinations, Release links, immutable
runtime images, component-project access for both branch and tag-pipeline actors, and validation
evidence.

For a migration, account for all current workflow sources and jobs. Consult deleted configuration
only when the owner requests migration or one named uncertainty cannot be resolved from current
authority.

## Component Project

Use `assets/release-components/` as the dedicated component-project shape. Its
`component-manifest.json` is the authoritative template inventory used by the root same-project SHA
test pipeline and repository tests.

Each template defines typed `spec:inputs` and one input-named job. It contains no workflow, stage
list, global default, global variables, copied base, nested local include, or shared hidden job. It
uses no `spec:component` context and therefore does not require GitLab 18.7.

Test a component-project change by including every component from
`$CI_SERVER_FQDN/$CI_PROJECT_PATH/<component>@$CI_COMMIT_SHA` in that project's root pipeline. Pin a
production consumer to a reviewed commit SHA or trusted immutable release tag.

SOURCE: <https://docs.gitlab.com/ci/components/#directory-structure> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/components/#test-the-component> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/components/#cicd-component-security-best-practices> (accessed 2026-09-22)

## Adapter Selection

Select exactly one implementation from [Version Adapter Index](./release-version-adapters.md).
Apply the component invocation and credential contract through the component-project README pointer
below rather than redefining it here.

Both version adapters are component-native live-verified in the hardened project `595` rerun. Local
fixtures independently cover their generated shell/config and HTTPS process-transport boundaries.

Select one implementation from [Release Notes Adapter Index](./release-notes-adapters.md). Preserve
the description artifact interface when substituting a project-owned notes component.

Select one publication implementation per destination from
[Publication Adapter Index](./release-publication-adapters.md). Generic Package publication and
GitLab Release creation use predefined project coordinates and `CI_JOB_TOKEN`.

For the LIVE-VERIFIED credential implementation, load
[Release Credential Operations](./glab-release-credentials.md).

## Consumer Composition

Apply the ownership, remote-selection, credential, and pinning contract in the
[component-project README](../assets/release-components/README.md). Start from its consumer example
and resolve every marker against the target project before validation.

## Validation Gates

1. Intake: every intake value comes from the project or its owner, and existing workflow behavior
   remains accounted for.
2. Structure: the dedicated project has exactly the declared templates; every component is
   self-contained and its inputs compile at pipeline creation. Both the branch-pipeline actor and
   release-tag-pipeline actor can fetch every pinned component.
3. Composition: the consumer owns admission, all stages, policy, project build, dependencies, and
   exactly one version adapter; no substitution marker or mutable production pin remains.
4. Credential: protected refs, credential role/scope/state/expiry, collision-free credential key,
   non-secret digest companion, creation-time hidden state, and exact environment scopes match the
   resolved interface. Runner fixtures prove process-scoped Basic transport for both version paths.
5. Main: the version job succeeds and records whether it selected no-release or release.
6. Tag: the tag-pipeline SHA equals the dereferenced tag commit; notes, consumer build, every
   publication, and Release succeed in dependency order with Release last.
7. Destination: every selected read-back finds the exact package version and files; the Release
   targets the existing tag, contains the preserved description, and exposes the intended links.

### Branch Completion

- Default-branch no-release is complete when project verification and exactly one version job pass,
  no matching tag is created, and no lifecycle tag pipeline exists.
- Default-branch release is complete when project verification and exactly one version job pass,
  one protected matching tag points to the intended commit, and its ordinary push creates one tag
  pipeline.
- Matching-tag publication is complete when runtime assertions confirm a protected tag push, notes
  use the configured release-tag pattern, exactly one consumer build job produces the immutable
  artifact set, and each selected destination has exactly one publication job consuming that same
  set. Every destination's independent read-back must find the expected version and files before the
  GitLab Release runs last against that tag.
- Nonmatching-tag validation is complete when existing-ref CI Lint reports the documented
  workflow-excluded result; authentication, syntax, or server failures remain failures.
- Component Catalog publication is complete when all same-SHA components compile, component
  validation passes, and a semantic-version tag pipeline creates the release in a project meeting
  the Catalog prerequisites.

After any component pin, included configuration, variable metadata, credential, or digest change,
run a new pipeline. Do not treat a retried job's configuration snapshot as evidence of the change.

After refs exist remotely, load
[Post-Merge and Existing-Ref Inspection](./glab-ci-existing-ref-inspection.md) to inspect the default
branch, matching tag, nonmatching tag, pipelines, jobs, and traces. Apply only the completion branch
that matches the observed version outcome, then apply matching-tag and destination completion when
a release tag exists.

SOURCE: <https://docs.gitlab.com/ci/inputs/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/variables/predefined_variables/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/variables/#protect-a-cicd-variable> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/components/#publish-a-new-release> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/jobs/job_troubleshooting/#a-cicd-job-does-not-use-newer-configuration-when-run-again> (accessed 2026-09-22)
