# Automatic Tag and Release Lifecycle

Compose this lifecycle from replaceable adapters. This file defines universal behavior and routes
selected implementations; the numbered validation gates are the sole completion authority.

## Invariant State Machine

Every default-branch push runs one version adapter.

1. The version adapter evaluates the push.
2. **No release:** evaluation succeeds, creates no version tag, and terminates the lifecycle.
3. **Release:** evaluation pushes one protected version tag with an authorized non-job-token Git
   credential. The ordinary tag push starts a separate tag pipeline.
4. The tag pipeline preserves a release-description artifact, builds immutable artifacts, completes
   one publication adapter for every selected destination, then runs one GitLab Release adapter.
5. The GitLab Release targets the existing tag and starts only after every publication succeeds.

SOURCE: <https://docs.gitlab.com/ci/> (reviewed 2026-09-22; this is the user's composed lifecycle)

## Required vs Replaceable

| Required lifecycle contract | Replaceable adapter choice |
|---|---|
| Every default-branch push reaches version evaluation | Version tool and release policy |
| No-release terminates successfully without a tag | Tool-specific no-release output |
| Release pushes one protected tag and triggers a tag pipeline | Tag format and credential type |
| Tag jobs match only the resolved release-tag regex | Regex derived from the tag format |
| One release-description artifact precedes Release creation | Generator, format, command, and path |
| One build produces immutable artifacts | Runtime, image, and build command |
| One publication adapter runs per selected destination | Destinations, authentication, and names |
| One GitLab Release adapter runs after all publications | Release implementation and durable links |

## Project Intake

New setup branch: use shipped assets and the current project state as the implementation authority.
Migration branch: when the owner explicitly requests migration, include deleted historical
configuration as migration input.
Uncertainty branch: when a current authority leaves one named unresolved uncertainty that deleted
configuration can answer, consult only the history needed to answer that uncertainty.

Resolve the GitLab target and Git remote; actual default branch; approved merge path; existing
workflow sources/jobs; one version adapter and release policy; one resolved tag contract whose
neutral default is owned by `base.gitlab-ci.yml` (or one explicit project override changing all
derived values together); release-commit behavior; credential
interface; one notes adapter; one build adapter; selected
destinations and one publication adapter per destination; one Release adapter; immutable images;
commands, paths, duplicate policies, durable URLs; and expected validation metadata.

Apply **Gate G1: Intake** before composition.

## Adapter Interfaces

### Version

Exactly one adapter evaluates each default-branch push and returns no-release or release. Release
pushes one matching protected tag; an adapter may also push its declared release commit. The main
pipeline performs version evaluation and Git transport only. `CI_JOB_TOKEN` cannot provide the
required ordinary tag-push handoff.

Select an implementation from [Version Adapter Index](./release-version-adapters.md). Validate with
**Gates G2, G3, and G5**.

### Release Notes

Exactly one adapter turns the existing release tag and selected history into one preserved Release
description artifact. Generator, format, command, and path are project choices. Every executable
used by setup and generation commands must be installed and proven available before the history
command runs. Validate with **Gates G2 and G6**.

### Build

Exactly one adapter builds immutable outputs once and preserves them for every publication. Validate
with **Gates G2 and G6**.

### Publication

Select exactly one adapter per destination. Each consumes preserved build outputs and returns exact
destination metadata, a read-back command, and a durable URL. Publication does not calculate or push
version refs. Select implementations from
[Publication Adapter Index](./release-publication-adapters.md). Validate with **Gates G2, G6, and
G7**.

### GitLab Release

Exactly one adapter consumes the preserved description and durable links after every publication
job succeeds. Validate with **Gates G6 and G7**.

### Credential

The interface is one protected non-job-token Git credential authorized for the release tag and any
selected release commit. Credential type is replaceable; role, scope, state, expiry, variable
metadata, and protected-ref authorization remain observable without reading the secret.

For the LIVE-VERIFIED project-access-token implementation, load
[Release Credential Operations](./glab-release-credentials.md). Validate with **Gate G4**.

## Composition Contract

The final project contains exactly:

- one authoritative `base.gitlab-ci.yml`;
- one version adapter;
- one release-notes adapter;
- one build adapter;
- one publication adapter per selected destination; and
- one GitLab Release adapter after all publication jobs.

Each generalized adapter includes the base and extends one hidden contract. Merge existing project
workflow sources/jobs into the final root configuration. Replace every marker and mutable image
reference. Generalized assets are **DERIVED + CI-LINT-VERIFIED**; exact sandbox files are example
compositions, not reusable adapters.

GitLab identity comes from predefined variables. Keep explicit only project policy: alternate tag
contract, destinations, artifact path/name, protected-tag role, and duplicate/retry behavior.
Override shared defaults once in root CI rather than duplicating them in adapters.

Apply **Gates G2 and G3** after composition.

## Validation Gates

1. **G1 Intake:** every Project Intake value is read from the project or supplied by its owner;
   existing workflow behavior is accounted for.
2. **G2 Substitution:** no unresolved marker or mutable image reference remains; version tag output,
   CI regex, and protected wildcard agree.
3. **G3 CI Lint:** before merge, load [Pre-Merge Candidate Validation](./glab-ci-candidate-validation.md)
   and validate the complete worktree-resolved candidate. After files and context refs exist
   remotely, load [Post-Merge and Existing-Ref Inspection](./glab-ci-existing-ref-inspection.md) and
   simulate the default branch, matching tag, nonmatching tag, and preserved existing sources.
4. **G4 Credential:** protected refs, credential role/scope/state/expiry, and variable
   flags/type/scope equal the resolved interface.
5. **G5 Main:** the version job succeeds. No-release creates no matching tag or lifecycle tag
   pipeline. Release creates exactly one intended protected tag. No main-pipeline job uses any
   declared lifecycle-only tag stage; unrelated jobs in other stages remain allowed.
6. **G6 Tag:** for release, tag-pipeline SHA equals the dereferenced tag commit; notes, build, every
   publication, and Release succeed in stage order with Release last.
7. **G7 Destination:** every selected read-back finds the exact package/version/files; the Release
   targets the existing tag, contains the preserved description, and links resolve as intended.
8. **G8 Generic Verifier:** for the LIVE-VERIFIED Generic branch, run
   `verify_release_playbook.py --help` and follow that authoritative CLI contract. External
   destinations remain outside its scope. The helper returns `"ok":true`; separate read-backs pass
   for every additional destination.

The lifecycle is complete only when every applicable named gate passes.

## Evidence-Minimizing Golden Sequence

1. Resolve intake, substitutions, notes executables, latest matching tag, and complete forecast range.
2. Follow the pre-merge candidate reference once; defer the post-merge reference until its refs exist.
3. Reuse or establish credential/protected-ref state, then merge one release-worthy change.
4. Observe main and matching-tag pipelines and run the Generic verifier once. Its named checks replace
   separate final reads for protected refs, token/variable metadata, pipelines/jobs, tag binding,
   package/file, Release description/link, and asset resolution.
5. Collect only evidence outside verifier scope: the no-release version-job trace, absence of a
   pipeline for the fetched nonmatching tag, and a secret scan of worktree/traces/report.

Verifier-established state completes those final metadata reads and polling; only the named evidence
outside verifier scope remains.
