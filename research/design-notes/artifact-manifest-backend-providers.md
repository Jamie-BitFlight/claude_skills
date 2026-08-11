---
title: Artifact Manifest Backend Providers — Cross-Platform Comparison
description: Comparative analysis of structured metadata and artifact linking capabilities across GitHub, Linear, GitLab, and Supabase for the ArtifactBackend provider abstraction layer
category: task-management
tags:
  - task-management
  - github-projects-v2
  - linear
  - gitlab
  - supabase
  - artifact-manifest
  - backend-abstraction
  - issue-tracking
  - structured-metadata
url: https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields
version: "1.0"
date_created: "2026-03-22"
last_reviewed: "2026-03-22"
---

# Artifact Manifest Backend Providers

Research into how GitHub, Linear, GitLab, and Supabase store structured metadata on issues/work items — informing the `ArtifactBackend` Protocol provider implementations for the artifact manifest system (issue #965).

## Context

The artifact manifest system uses an `ArtifactBackend` Protocol with 3 methods:

- `get_manifest(issue_number) -> ArtifactManifest`
- `set_manifest(issue_number, manifest) -> None`
- `read_artifact_content(path) -> str`

Each backend implements this interface using its native primitives. This research documents what each platform provides.

## Provider Comparison

### Storage Mechanism per Platform

| Platform | Native Primitive for Manifest | API Access | Structured Query | Limits |
|----------|-------------------------------|-----------|-----------------|--------|
| GitHub (current) | Issue body markdown section (HTML comment delimiters) | PyGithub REST + GraphQL | Parse markdown table | 65,536 char body limit |
| GitHub Issue Fields | Org-level typed fields (Text, Number, Date, Single Select) | GraphQL `issueFieldCreate` | Native field filtering | 25 fields per org |
| GitHub Projects V2 | Project-level custom fields | GraphQL `updateProjectV2ItemFieldValue` | Exact match only on text | 50 fields per project |
| Linear | Attachments with rich metadata (key-value pairs) | GraphQL `attachmentCreate` | Attachment metadata query | Not publicly documented |
| GitLab | Custom fields (Premium/Ultimate only) | REST API has NO custom field access; GraphQL undocumented | UI-only as of 2026-03 | 50 per group, 10 per work item type, 1,024 char max |
| Supabase | Database table | REST + client SDK | Full SQL query | Standard PostgreSQL limits |

### GitHub — Three Storage Options

**Option A: Issue Body Section (current implementation)**

SOURCE: Implemented in `backlog_core/artifact_provider.py`

- Manifest stored between `<!-- artifact-manifest:begin -->` and `<!-- artifact-manifest:end -->` delimiters
- Parsed/rendered as markdown table
- No setup required, works with any GitHub repo
- Risk: body edits by humans can corrupt delimiters

**Option B: GitHub Issue Fields (public preview 2026-03-12)**

SOURCE: [GitHub Blog Changelog 2026-03-12](https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/)

- Up to 25 typed fields per organization (Text, Number, Date, Single Select)
- Cross-repository — applies to all issues in the org
- Full GraphQL and REST API support for CRUD
- Searchable and filterable by field value
- Webhook support: `field_added`, `field_removed` events
- Default fields auto-created: Priority, Effort, Start date, Target date
- Public preview status — API stability not confirmed

SOURCE: [Managing Issue Fields](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/managing-issue-fields-in-your-organization)

**Option C: GitHub Projects V2 Custom Fields**

SOURCE: [Understanding Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields)

- 5 types: Text, Number, Date, Single Select, Iteration
- 50 field max per project (including system fields)
- Can create fields via GraphQL `createProjectV2Field`
- Can read/write values via GraphQL `updateProjectV2ItemFieldValue`
- Cannot edit field definitions via API (creation only)
- Text field character limit: not documented
- Text fields: no structured query (exact match only, no substring/regex)

SOURCE: [GitHub Discussion #35922](https://github.com/orgs/community/discussions/35922) — field editing limitation confirmed

### Linear

SOURCE: [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)

- **No custom fields** — uses labels/label groups instead
- **Attachments** are the native primitive for structured metadata:
  - Support key-value pairs and rich metadata structure
  - Fully queryable/writable via GraphQL API
  - Used for external resource linking (GitHub PRs, Jira issues, etc.)
- Resources section in the UI is implemented via the Attachments API
- MCP server exposes labels, standard properties, and attachments — not custom fields
- Field limits not publicly documented

A `LinearArtifactProvider` would store each artifact as an Attachment on the Linear issue, encoding artifact type, path, and status in the attachment metadata fields.

### GitLab

SOURCE: [GitLab Custom Fields Documentation](https://docs.gitlab.com/ee/user/custom_fields.html)

- Custom fields exist but require **Premium/Ultimate tier**
- 4 types: text, number, single-select, multi-select
- **REST API has NO custom field access** — feature request open since 2018
- GraphQL has a `CustomField` type but queries/mutations are undocumented
- Custom fields are effectively UI-only as of 2026-03
- Limits: 50 per group, 10 per work item type, 1,024 char max per text field
- No JSON/nested data support

SOURCE: [GitLab Issue #324786](https://gitlab.com/gitlab-org/gitlab/-/issues/324786) — REST API feature request

**Alternative: Linked Items**

- Three relationship types: "relates to", "blocks", "is blocked by"
- Bi-directional, cross-project capable
- Fully supported via REST API

SOURCE: [GitLab Linked Issues API](https://docs.gitlab.com/ee/api/issue_links.html)

A `GitLabArtifactProvider` would need to use issue description sections (similar to current GitHub approach) or linked issues, since custom fields have no API access. Alternatively, wait for REST API custom field support.

**Attachments**

- Upload supported (`POST /api/v4/:project_id/uploads`)
- Download via API is NOT supported (long-standing feature request)

SOURCE: [GitLab Issue #24155](https://gitlab.com/gitlab-org/gitlab/-/issues/24155) — attachment download feature request

### Supabase

No research conducted — Supabase is a PostgreSQL database with a REST API. Implementation is straightforward: create an `artifact_manifests` table with columns matching `ArtifactEntry` fields. Full SQL query capability, no field limits beyond PostgreSQL constraints.

## Provider Implementation Mapping

| ArtifactBackend Method | GitHub (current) | GitHub (Issue Fields) | Linear | GitLab | Supabase |
|------------------------|------------------|-----------------------|--------|--------|----------|
| `get_manifest` | Parse issue body section | Query issue field values | Query attachments by issue | Parse issue description section | `SELECT * FROM manifests WHERE issue_id = ?` |
| `set_manifest` | Replace issue body section | Update issue field values | Create/update attachments | Replace issue description section | `UPSERT INTO manifests` |
| `read_artifact_content` | Read from root worktree | Read from root worktree | Read from root worktree | Read from root worktree | Read from root worktree |

Note: `read_artifact_content` is always filesystem-based regardless of backend — the manifest stores references (paths), the content lives in plan files on disk.

## Design Principle

Follow each platform's native primitive rather than forcing one model:

- GitHub: Issue body sections (stable) or Issue Fields (when GA)
- Linear: Attachments with metadata
- GitLab: Issue description sections (until REST API supports custom fields)
- Supabase: Database table

The `ArtifactBackend` Protocol insulates all consumers from these differences.

## Freshness Tracking

- **Created**: 2026-03-22
- **Last Verified**: 2026-03-22
- **Version**: GitHub Projects V2 API (current), GitHub Issue Fields (public preview 2026-03-12), Linear API (current), GitLab API v4 (current)
- **Next Review**: 2026-06-22

## Source Files

- `/tmp/research-github-projects-v2-fields.md` — GitHub Projects V2 and Issue Fields research
- `/tmp/research-linear-custom-fields.md` — Linear custom fields and attachments research
- `/tmp/research-gitlab-custom-fields.md` — GitLab custom fields and API limitations research
- `/tmp/research-linear-artifacts.md` — Linear artifact linking patterns (from grooming phase)
- `/tmp/research-jira-asana-monday-artifacts.md` — Jira/Asana/Monday artifact patterns (from grooming phase)
