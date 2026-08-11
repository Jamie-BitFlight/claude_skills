---
name: Backend-first artifact storage providers
description: "The artifact manifest system (P965) stores manifests in GitHub Issue body with HTML comment delimiters. This works but has limitations: body edits can corrupt delimiters, and the same approach won't work for Linear (which uses Attachments) or GitLab. Research completed on GitHub Issue Fields (public preview 2026-03-12), GitHub Projects V2 fields, pinned comments, Linear attachments API, and GitLab (pending). The ArtifactBackend Protocol abstraction exists but only has one provider (GitHubArtifactProvider). Success: multiple providers exist, each using the backend's native storage primitive. Research files: /tmp/research-github-projects-v2-fields.md, /tmp/research-linear-custom-fields.md, /tmp/research-gitlab-custom-fields.md (pending)."
metadata:
  topic: backend-first-artifact-storage-providers
  source: 'GitHub Issue #984'
  added: '2026-03-22'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#984'
  last_synced: '2026-03-22T15:08:43Z'
---

## Story

As a **developer using Claude Code skills**, I want to **backend-first artifact storage providers** so that **the tooling becomes more capable and complete**.

## Description

The artifact manifest system (P965) stores manifests in GitHub Issue body with HTML comment delimiters. This works but has limitations: body edits can corrupt delimiters, and the same approach won't work for Linear (which uses Attachments) or GitLab. Research completed on GitHub Issue Fields (public preview 2026-03-12), GitHub Projects V2 fields, pinned comments, Linear attachments API, and GitLab (pending). The ArtifactBackend Protocol abstraction exists but only has one provider (GitHubArtifactProvider). Success: multiple providers exist, each using the backend's native storage primitive. Research files: /tmp/research-github-projects-v2-fields.md, /tmp/research-linear-custom-fields.md, /tmp/research-gitlab-custom-fields.md (pending).

## Acceptance Criteria

- [ ] Work matches description
- [ ] Plan or implementation complete

## Context

- **Source**: Session observation — discovered during #965 implementation session 2026-03-21
- **Priority**: P2
- **Added**: 2026-03-22
- **Research questions**: None

## Artifact Manifest

<!-- artifact-manifest:begin -->
| Type | Path | Status | Agent | Created |
|------|------|--------|-------|---------|
| research | research/design-notes/artifact-manifest-linear-patterns.md | current | artifact-migrate | 2026-03-22T05:59:41.536590+00:00 |
| research | research/design-notes/artifact-manifest-jira-asana-monday-patterns.md | current | artifact-migrate | 2026-03-22T05:59:44.902521+00:00 |
| research | research/design-notes/artifact-manifest-github-fields.md | current | artifact-migrate | 2026-03-22T05:59:48.525429+00:00 |
| research | research/design-notes/artifact-manifest-linear-custom-fields.md | current | artifact-migrate | 2026-03-22T05:59:52.207421+00:00 |
| research | research/design-notes/artifact-manifest-gitlab-custom-fields.md | current | artifact-migrate | 2026-03-22T05:59:55.892611+00:00 |
| research | research/design-notes/artifact-manifest-gitlab-api-deep.md | current | artifact-migrate | 2026-03-22T05:59:59.488305+00:00 |
<!-- artifact-manifest:end -->