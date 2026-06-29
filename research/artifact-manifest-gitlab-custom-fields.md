---
title: "GitLab Custom Fields and Structured Metadata Capabilities for Issues"
research_date: "March 2026"
---

## Executive Summary

GitLab offers limited but growing structured metadata capabilities for issues. Custom fields (Premium/Ultimate tier) support four basic types (text, number, single-select, multi-select) with strict limits. API support for custom fields remains incomplete—GraphQL support is partial, and REST API access is minimal. Epics and linked items provide hierarchical organization and dependency tracking. The GitLab MCP server provides basic issue operations but does not expose custom field management.

---

## 1. Custom Fields on Issues

### 1.1 Availability & Tier Requirements

Custom fields require **Premium or Ultimate tier** on GitLab.com or self-managed instances. They became generally available in **GitLab 18.0** [Custom fields | GitLab Docs](https://docs.gitlab.com/user/work_items/custom_fields/).

### 1.2 Supported Field Types

GitLab supports **exactly four field types** [Custom fields | GitLab Docs](https://docs.gitlab.com/user/work_items/custom_fields/):

1. **Single-select** – Choose one option from a predefined list
2. **Multi-select** – Select multiple options simultaneously
3. **Number** – Capture quantitative data for calculations
4. **Text** – Store variable information (max 1,024 characters)

### 1.3 Field Configuration Limits

Strict limits are enforced [Custom fields | GitLab Docs](https://docs.gitlab.com/user/work_items/custom_fields/):

- **Top-level group limit**: At most **50 active custom fields** per group
- **Per-work-item-type limit**: Maximum **10 custom fields** per work item type (issues, epics, etc.)
- **Select options limit**: Single-select and multi-select fields allow up to **50 options each**
- **Text field size limit**: **1,024 characters** per text field value

### 1.4 Access & Permissions

- **Configuration**: Maintainer or Owner roles required to create/modify custom fields
- **Value setting**: Planner, Reporter, Developer, Maintainer, or Owner roles can set field values on work items

### 1.5 Structured Data Capability

Custom fields do **NOT support nested JSON or complex structured data**. They are atomic typed values only:
- Text fields accept plain strings (no JSON objects)
- Number fields are scalar values
- Select fields are single or multiple options from a predefined list

**Serialization note** [Serializing Data | GitLab Docs](https://docs.gitlab.com/development/database/serializing_data/): GitLab development guidelines note that storing serialized data such as JSON or YAML "ends up wasting a lot of space." Custom fields do not support this pattern.

---

## 2. API Support for Custom Fields

### 2.1 REST API Status

**REST API support for custom fields is incomplete**. Community forums report that the `/api/v4/projects/:projectid/issues` endpoint does not expose custom field values, despite custom fields being configured on issues [Reading custom field from API - GitLab Forum](https://forum.gitlab.com/t/reading-custom-field-from-api/126492).

Key gaps:
- No endpoint to read custom field values from issues
- No endpoint to write custom field values via REST API
- No custom field metadata endpoint

### 2.2 GraphQL API Status

**GraphQL API includes partial support**. The GitLab GraphQL API reference includes a `CustomField` type, indicating some GraphQL support exists [GraphQL API resources | GitLab Docs](https://docs.gitlab.com/api/graphql/reference/).

However, documentation does not provide:
- Specific field names for querying custom field values on issues
- Mutation signatures for writing custom field values
- Concrete examples of custom field queries

**How to explore**: Use the interactive GraphQL explorer at your GitLab instance's `/-/graphql-explorer` endpoint to inspect the schema for CustomField types and Issue types to discover available fields [Run GraphQL API queries and mutations | GitLab Docs](https://docs.gitlab.com/api/graphql/getting_started/).

### 2.3 API Implementation Status

Long-standing feature request: Issue [#7778 - API for custom fields at project-level](https://gitlab.com/gitlab-org/gitlab/-/issues/7778) demonstrates that API access for custom fields has been requested for years and remains in development.

**Verdict**: Custom fields are **NOT production-ready via API**. UI-only feature as of March 2026.

---

## 3. Issue Attachments and Linked Resources

### 3.1 Attachments

**File upload capability exists; download via API does not**.

Upload path:
- Endpoint: `POST /api/v4/:project_id/uploads` [REST API | GitLab Docs](https://docs.gitlab.com/api/rest/)
- Use case: Upload images/files to include in issue descriptions or notes
- Metric images: Special support for uploading metric dashboard screenshots to incident Metrics tab [Issues API | GitLab Docs](https://docs.gitlab.com/api/issues/)

Download limitation:
- No REST API endpoint to download or retrieve attachments from issues or merge requests
- Feature request: [#24155 - Download attachments through API](https://gitlab.com/gitlab-org/gitlab/-/issues/24155)
- Status: Multiple community requests over years with no resolution ([#51447](https://gitlab.com/gitlab-org/gitlab-foss/-/issues/51447), [Forum discussion](https://forum.gitlab.com/t/couldnt-find-api-to-download-attachments-in-issues-or-merge-requests/107428))

### 3.2 Linked Issues (Bi-directional Relationships)

**Fully supported via REST API**.

Capabilities [Linked issues | GitLab Docs](https://docs.gitlab.com/user/project/issues/related_issues/):
- Create bi-directional relationships between any two issues (cross-project)
- Three relationship types: "relates to", "blocks", "is blocked by"
- Requires Guest role or higher on both projects
- Blocked issues display icon in lists/boards (Premium/Ultimate tier)
- Managed via Issue links API

Visibility: "The relationship only appears in the UI if the user can see both issues" [Linked issues | GitLab Docs](https://docs.gitlab.com/user/project/issues/related_issues/).

### 3.3 Linked Items (General Work Item Relationships)

**Broader than linked issues, newly unified under work items framework** [Linked items | GitLab Docs](https://docs.gitlab.com/user/work_items/linked_items/).

Supported connections:
- Links between issues, epics, tasks, objectives, incidents, and test cases
- Three relationship types: "relates to", "blocks", "is blocked by"
- Bi-directional display of relationships
- Metadata viewable: status, assignee, labels, weight, milestone, iteration, dates, health indicators

Permission: Guest, Planner, Reporter, Developer, Maintainer, or Owner role required.

---

## 4. Epics and Sub-Issues

### 4.1 Epic Structure

Epics organize large initiatives with parent-child relationships [Epics | GitLab Docs](https://docs.gitlab.com/user/group/epics/).

Parent-child relationships:
- **One epic → Many issues**: An epic contains one or more issues as direct children
- **Nested epics** (Ultimate tier only): Epics can have child epics (up to 7 levels deep)
- **Single parent per issue**: An issue can be a child of only one epic

### 4.2 Epic Availability & Tiers

- **Premium or Ultimate tier** required
- Available on GitLab.com, self-managed, and dedicated instances
- Unified work items framework (GitLab 17.2+, GA in 18.1) modernizes epic experience

### 4.3 Epic-to-Issue Linking via MCP

The GitLab MCP server's `create_issue` tool includes an `epic_id` parameter, allowing newly created issues to be linked to existing epics [GitLab MCP server tools | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/).

### 4.4 Linked Epics (Epic-to-Epic)

**Bi-directional epic relationships** (separate from child epics):
- Link any two epics regardless of group hierarchy
- Relationship types: Same as linked items ("relates to", "blocks", "is blocked by")
- Metadata display: Status, assignee, labels, weight, dates

---

## 5. GitLab MCP Server Capabilities

### 5.1 Overview

The GitLab MCP server enables AI tools (Claude, Cursor, etc.) to securely access GitLab data and perform operations [GitLab MCP server | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/).

Authentication: OAuth 2.0 Dynamic Client Registration [GitLab MCP server | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/).

Configuration for Claude Code: `claude mcp add --transport http GitLab https://<gitlab.example.com>/api/v4/mcp` [GitLab MCP server | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/).

### 5.2 Issue and Epic Tools

**Issue Management**:
- `create_issue` – Create new issue with title, description, assignees, milestones, labels, confidentiality, and **epic_id** linkage
- `get_issue` – Retrieve detailed issue information by project ID and issue internal ID
- Availability: Issue functionality introduced GitLab 18.5; assignee_ids, reviewer_ids, description, labels, milestone_id added GitLab 18.8 [GitLab MCP server tools | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/)

**Metadata Tools**:
- `search_labels` – Search for labels in project or group with filtering options [GitLab MCP server tools | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/)
- `search` – Global search across GitLab for issues, merge requests, and other content
- `create_workitem_note` – Add comments/notes to work items (including issues)

**Epic Linking**:
- Only via the `epic_id` parameter in `create_issue`
- No dedicated epic creation tool
- No custom field management tools

### 5.3 Custom Fields NOT Exposed

The GitLab MCP server does **NOT** expose custom field creation, reading, or writing capabilities. Custom fields must be managed via the GitLab UI or are inaccessible via the MCP interface.

### 5.4 Known Limitations

Tool visibility issues reported: Some tools may not appear in Claude Code due to naming patterns (tools not following `mcp__<server>__*` pattern) or tool count limits [MCP Server Tools Not Visible in Claude Code - GitLab Issue #8117](https://gitlab.com/gitlab-org/cli/-/issues/8117).

---

## 6. Comparison to GitHub Issue Fields (Alternative Framing)

GitLab does **NOT have a direct equivalent to GitHub Issue Fields** (custom fields on a per-organization basis with typed enforcement).

Key differences:
- GitHub Issue Fields: Org-wide, required/optional enforcement, multiple field types
- GitLab Custom Fields: Group-wide max 50 fields, no enforcement rules, limited API access
- GitLab lacks GitHub's field schema validation and mutation safety

---

## 7. Limitations Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Custom field types | 4 types (text, number, single-select, multi-select) | No JSON, no nested data |
| Custom field API (REST) | No support | Feature request open since 2018 |
| Custom field API (GraphQL) | Partial | Type exists but queries/mutations undocumented |
| Custom field limits | 50 per group, 10 per work item type, 1,024 char max | Strict limits |
| Attachments (upload) | Supported | `/api/v4/:project_id/uploads` |
| Attachments (download) | Not supported | Long-standing feature request |
| Linked issues | Fully supported | REST API available, bi-directional |
| Linked items | Fully supported | Work items framework, UI complete |
| Epics | Supported (Premium+) | Max 7 levels nesting, UI-driven setup |
| MCP server | Partial | Issue CRUD, no custom field support |

---

## 8. Recommendations for GitHub → GitLab Migration

If planning to migrate GitHub Issue Fields to GitLab:

1. **For simple metadata**: Use custom fields (text, number, select) with manual API workarounds (GraphQL exploration)
2. **For issue relationships**: Leverage linked issues (equivalent to GitHub linked issues)
3. **For hierarchies**: Use epics for strategic organization
4. **For attachments**: Accept that API download is unavailable; store externally
5. **For structure**: Consider storing JSON-like metadata in issue description templates with regex parsing (workaround)

---

## 9. Information Gaps & Future Directions

- **Undocumented GraphQL custom field queries**: The schema exists but query syntax is not documented
- **REST API roadmap**: No public timeline for custom field REST API support
- **Attachment download**: Feature request lacks resolution timeline
- **MCP server tool coverage**: Tool count and naming pattern constraints not fully documented

**To verify current API state**: Use the GitLab GraphQL explorer at `https://your-gitlab.com/-/graphql-explorer` and inspect the Issue and CustomField types directly.

---

## References

- [Custom fields | GitLab Docs](https://docs.gitlab.com/user/work_items/custom_fields/)
- [GitLab MCP server | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/)
- [GitLab MCP server tools | GitLab Docs](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server_tools/)
- [Epics | GitLab Docs](https://docs.gitlab.com/user/group/epics/)
- [Linked items | GitLab Docs](https://docs.gitlab.com/user/work_items/linked_items/)
- [Linked issues | GitLab Docs](https://docs.gitlab.com/user/project/issues/related_issues/)
- [GraphQL API | GitLab Docs](https://docs.gitlab.com/api/graphql/)
- [GraphQL API resources | GitLab Docs](https://docs.gitlab.com/api/graphql/reference/)
- [Issues API | GitLab Docs](https://docs.gitlab.com/api/issues/)
- [REST API | GitLab Docs](https://docs.gitlab.com/api/rest/)
- [Reading custom field from API - GitLab Forum](https://forum.gitlab.com/t/reading-custom-field-from-api/126492)
- [API for custom fields at project-level (#7778) - GitLab Issue](https://gitlab.com/gitlab-org/gitlab/-/issues/7778)
- [Download attachments through API (#24155) - GitLab Issue](https://gitlab.com/gitlab-org/gitlab/-/issues/24155)
- [MCP Server Tools Not Visible in Claude Code (#8117) - GitLab Issue](https://gitlab.com/gitlab-org/cli/-/issues/8117)
- [Serializing Data | GitLab Docs](https://docs.gitlab.com/development/database/serializing_data/)
- [Tutorial: Connect Claude Desktop to GitLab MCP server | GitLab Docs](https://docs.gitlab.com/tutorials/connect_claude_desktop_with_gitlab_mcp_server/)
