# Release Lifecycle Live Evidence

Evidence date: 2026-09-22. The ledger separates historical copied-template evidence from the
component-native lifecycle verified in self-managed GitLab `18.7.0-ee`.

## Historical Copied-Template Evidence

This historical evidence is sourced from the preserved files under
`assets/release-components/live-verified/` and the prior sandbox ledger for project `529`; it is
separate from the project `595` component validation. The files predate the component refactor:

- `semantic-release.gitlab-ci.yml` and `.releaserc.json` from commit `c6de8fb`.
- `python-semantic-release.gitlab-ci.yml` and `pyproject.toml` from release commit `95f5b4c`.

In project `529`, semantic-release `25.0.9` ran through main pipeline/job `5680/7068`, tag
`release-playbook-v1.0.0`, tag pipeline `5681`, and ordered jobs `7069 -> 7070 -> 7071`.
python-semantic-release `10.6.2` ran through `5690/7085`, release commit `95f5b4c`, tag
`release-playbook-v1.1.0`, and tag pipeline `5692` with ordered jobs `7088 -> 7089 -> 7090`.
Release-commit pipeline `5691` reported that `1.1.0` was already released and created no duplicate
tag. Both chains published a Generic package and created the GitLab Release last with a package
link.

These copied files retain sandbox-specific names, commands, and mutable images as observed evidence.
They are not reusable component templates.

## Component-Native Evidence

The component templates from product commit `c96cb30b41275ae8a02910f09f476445136fb72a` were exported
unchanged to retained private validation project
[595](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/issue-3816-release-components-live-20260922-092610).
Validation-specific consumer pipeline configuration, resolved images, and disabled Catalog settings
differed. Main pipeline `5916` and semantic-release version job `7315` succeeded. The version job
created protected tag `v1.0.1` at commit `245a5d419172b27ce5742b0556f9627e2323866a`, which started
ordinary push pipeline `5917`.

The tag pipeline completed in dependency order:

1. `7317` generated the release-notes artifact.
2. `7318` built the release artifact once.
3. `7319` published Generic Package ID `199`.
4. `7320` created GitLab Release ID `199` last.

Independent build-artifact, Generic Package, and Release-link reads matched SHA-256
`775535948def99886df6fc4e4038b702fd93934134809b866c609925a738e717`.

The release credential was protected, masked, hidden, and scoped exactly to environment
`release-version`. Tag jobs `7317` through `7320` reported no environment and therefore did not
receive it. Project token `695` changed from no recorded use to last use at
`2026-09-22T10:03:46.953Z` during version job `7315`; the resulting tag pipeline was attributed to
that token's bot user. Repository pushes with `CI_JOB_TOKEN` remained disabled. This establishes
project-token Git transport and release-credential isolation from tag publication jobs without
exposing credential values.

That command-helper success is bounded to project `595`'s observed credential-free URL and Runner
configuration. It is not evidence that generic helpers override every Runner credential source.

## Cold Run 4 Semantic Component Evidence

[Consumer project 529](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation)
pinned [component project 628](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/cold-run-4-release-components)
at [component commit `7e83114b`](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/cold-run-4-release-components/-/commit/7e83114b51ba284f215f946c1b4b83183cda6e8d).
[Main pipeline 5963](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/pipelines/5963)
and [version job 7393](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/jobs/7393)
used the selected environment-scoped credential through process-scoped Basic `http.extraHeader`,
created `cold-run-4-v0.1.0`, and started bot-attributed
[tag pipeline 5964](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/pipelines/5964).
Its ordered evidence is [notes 7395](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/jobs/7395),
[build 7396](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/jobs/7396),
[publication 7397](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/jobs/7397), and
[Release 7398](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/jobs/7398).
[No-release pipeline 5966](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/pipelines/5966)
and [job 7402](https://gitlab-au.aws.hivemindcloud.com/jamie.nelson/jira-ai-evaluation/-/jobs/7402)
exercised the same transport and completed without another tag.

The run also established the access boundary: a project-access-token bot cannot be added to another
private project, while public project `628` was resolvable by the project-token-created tag pipeline.
Five preceding cold-run jobs showed generic credential helpers did not displace Runner's
host-specific job-token authentication; only process-scoped `http.extraHeader` produced the selected
release identity.
The current Python adapter's equivalent transport is executable-fixture and documentation verified,
not live-verified by cold run 4.

## Corrected Failures

- Historical job `7065` failed because the Node Alpine image lacked Git; installing Git produced
  successful job `7068`.
- Historical job `7074` failed from detached HEAD; attaching the branch and upstream produced
  successful job `7085`.
- Diagnostic pipeline/job `5913/7306` traced GitLab Runner `18.7.1` setting
  `credential.interactive=never` and showed no askpass child process. Clean pipeline/job `5914/7308`
  reproduced the askpass failure without instrumentation before semantic-release ran. Product commit
  `c96cb30b4` replaced askpass with command-scoped credential helpers, and `5916/7315` completed the
  authenticated tag push.

## Evidence Boundary

LIVE-VERIFIED, COPIED TEMPLATE: the project `529` version-tool behavior and release chains preserved
by the exact historical fixture files.

LIVE-VERIFIED, COMPONENT-NATIVE: semantic-release version selection and authenticated protected-tag
push, separate tag-pipeline handoff, scoped credential isolation, release notes, build-once artifact,
Generic publication and matching read-back, and GitLab Release creation last at product commit
`c96cb30b4`. Durable evidence is the retained project `595` and its API-visible pipelines, jobs,
artifacts, package, and Release; the ignored scratch report is not the durable evidence store.

LIVE-VERIFIED, COLD-RUN-4 SEMANTIC TRANSPORT: process-scoped Basic authorization over Runner
`insteadOf`, noninteractive, and host-helper configuration for release and no-release execution in
consumer/component projects `529/628`. This claim does not extend to the Python adapter.

DOCUMENTATION-VERIFIED, NOT LIVE-TESTED: GitLab PyPI, GitLab npm, PyPI.org, and npmjs.com adapters.

SOURCE: <https://docs.gitlab.com/ci/> (reviewed 2026-09-22; historical project 529 claims sourced from preserved fixtures and the prior sandbox ledger; project 595 and cold-run projects 529/628 claims verified through their GitLab API-visible evidence)
