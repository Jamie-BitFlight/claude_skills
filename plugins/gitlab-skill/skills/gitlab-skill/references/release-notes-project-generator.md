# Project-Owned Release Notes Adapter

Replace the shipped notes component with one self-contained project component. Preserve the
consumer-selected job name, stage, rules, prerequisites, release-tag policy, and one nonempty
Markdown artifact path. Keep release calculation, build, package publication, and GitLab Release
creation outside the replacement.

Complete this adapter when its isolated fixture proves the selected tag range and the tag pipeline
passes the artifact to the GitLab Release job through an explicit artifact-producing `needs` entry.

SOURCE: <https://docs.gitlab.com/ci/components/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/jobs/job_artifacts/> (accessed 2026-09-22)
