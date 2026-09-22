# Git History Release Notes Adapter

Include `assets/release-components/templates/release-notes.yml`. Pass the consumer-owned job name,
stage, rules, prerequisites, digest-pinned image, output path, and release-tag glob. The component
rejects a current tag outside that glob and finds the previous tag with the same glob before writing
the Markdown artifact.

Complete this adapter when the preserved output is nonempty, describes the current release tag, and
contains only the selected release range. Pass that artifact to the GitLab Release component through
an explicit artifact-producing `needs` entry.

SOURCE: <https://git-scm.com/docs/git-describe> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/jobs/job_artifacts/> (accessed 2026-09-22)
