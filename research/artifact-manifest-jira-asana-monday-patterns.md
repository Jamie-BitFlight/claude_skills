---
title: "Artifact Linking Patterns: Jira, Asana, Monday.com"
---

## 1. JIRA: Issue-Link Centered Architecture

### 1.1 Core Linking Model

Jira uses two complementary linking mechanisms:

**Issue Links** (internal relationships)
- Bidirectional edges between issues in same Jira instance
- Each link has:
  - **name**: link type identifier (e.g., "Blocks", "Depends", "Relates to")
  - **inward description**: how destination sees the link (e.g., "is blocked by")
  - **outward description**: how source sees the link (e.g., "blocks")

Example: "Issue A blocks Issue B"
- Issue A: has outward link of type "blocks" to Issue B
- Issue B: has inward link of type "is blocked by" to Issue A

[Source: Jira issue linking model](https://developer.atlassian.com/cloud/jira/platform/issue-linking-model/)

**Remote Links** (external references)
- Link Jira issues to resources in external systems
- Represents connection between Jira issue and any remote object (Confluence page, helpdesk ticket, test case, custom document)
- Structure: URL + title + metadata
- Enables architectural separation: artifact lives in specialized system, issue references it without redundancy

[Source: Creating Remote Issue Links](https://developer.atlassian.com/server/jira/platform/creating-remote-issue-links/)

### 1.2 Artifact Linking Patterns

**Confluence Integration** (native)
- Jira automatically creates issue links when a Jira issue is mentioned in Confluence using the Jira Issue Macro
- Confluence pages can be linked as related resources from Jira issue view
- Epics can link to useful Confluence pages (requirements, design specs, project outlines)
- Bidirectional: Confluence pages display linked Jira issues; Jira issues show linked Confluence pages
- Custom field support: when creating issues from Confluence tables, column mappings populate Jira fields including custom fields

[Source: Use Jira and Confluence together](https://support.atlassian.com/confluence-cloud/docs/use-jira-and-confluence-together/)

**Attachment Metadata**
- Issues support native file attachments
- Attachment objects include: ID, name, file type, creation timestamp, creator
- REST API provides dedicated attachment operations: upload, retrieve metadata, delete
- Can reference attachments in issue descriptions and comments

[Source: Jira Cloud REST API - Attachments](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/)

**REST API Design** (extensible remote linking)

```
POST /issue/{issueIdOrKey}/remotelink
{
  "url": "https://example.com/artifact/123",
  "title": "Architecture Specification",
  "relationship": "documents",
  "iconUrl": "https://example.com/icon.png",
  "summary": "Architectural design for auth system"
}
```

Allows custom applications to create structured references without modifying Jira issue structure. Response includes full link object for subsequent access.

[Source: How to use REST API to add remote links](https://support.atlassian.com/jira/kb/how-to-use-rest-api-to-add-remote-links-in-jira-issues/)

### 1.3 Metadata Capabilities

- Custom fields: arbitrary field types with structured validation
- Issue link types: configurable link semantics (admin-defined relationships)
- Attachment metadata: queryable file properties
- No native "linked document manifest" — architects must model this via issue hierarchy or custom fields

### 1.4 Key Pattern

**Separation of concerns**: Issue links model task relationships; remote links model artifact references. Artifacts remain in authoritative systems (Confluence, external docs, design tools); Jira issues maintain references without ownership.

---

## 2. ASANA: Attachment-Embedded Model

### 2.1 Attachment Architecture

Asana supports attachments at three hierarchy levels:

**Project Level**
- "Key resources" section contains files directly attached to project
- Not visible to individual tasks (users must request feature to auto-link project docs to tasks)

**Task Level**
- Files directly associated to individual task
- Inline images in task descriptions appear as attachments in API responses
- Single attachment endpoint: `/tasks/{task_gid}/attachments`

**Attachment Metadata**
- Each attachment includes: name, resource_subtype, created_at, created_by
- Support for external resources via `resource_subtype: "external"` (URL reference)
- 100MB size limit per file
- Cannot attach files from third-party services (Dropbox, Box, Google Drive) via API; must download first or provide URL

[Source: Attachments](https://developers.asana.com/reference/attachments)

### 2.2 Task Dependencies (Structural Linking)

Asana models artifact relationships separately from task dependencies:

**Task Dependencies**
- Establish finish-to-start relationships: Task B cannot start until Task A completes
- Queryable via API in task object
- Carry through task templates (feature released to address earlier limitation)
- No direct connection to attachments — dependencies model timing, not artifact references

[Source: Task dependencies](https://help.asana.com/s/article/task-dependencies?language=en_US)

**Custom Fields** (structured metadata)
- Tasks inherit custom field values from parent project(s)
- Separate from attachments: custom fields and attachments are independent properties
- Useful for artifact classifications (e.g., "design-doc-status": "approved") but don't link to specific files

### 2.3 Artifact Linking Limitations

- No native "project brief" manifest — feature requests exist but not standard
- Attachment linking to external documents requires URL upload via API
- No remote linking equivalent to Jira: artifacts must be files in Asana or plain URLs
- Dependencies and attachments are orthogonal: cannot model "this task depends on completion of this artifact review"

[Source: Get attachments from an object](https://developers.asana.com/reference/getattachmentsforobject)

### 2.4 Key Pattern

**Embedding over referencing**: Attachments live within task scope. Custom fields model metadata about attachments but not connections to external artifact systems. Task dependencies handle workflow orchestration separately.

---

## 3. MONDAY.COM: Column-Based Metadata Model

### 3.1 File Storage Architecture

**Files Column** (dedicated column type)
- Allows adding files directly to column cell
- Supports 500MB per file
- Upload sources: computer, Google Drive, Dropbox, Box, OneDrive, SharePoint
- Files tab displays all files from both file columns AND updates section in single gallery
- Collaboration: comment, tag, converse within file itself

[Source: The Files Column](https://support.monday.com/hc/en-us/articles/360000597900-The-Files-Column)

**Update Comments** (alternative attachment location)
- Files can be attached to updates (timeline/comments)
- Visually and functionally different from dedicated file columns
- Can be queried separately or as part of item activity feed

**Workdoc Linking** (Monday's native documents)
- Can attach workdocs directly to file column
- Workdocs edited in-place maintain link to original
- Edits sync bidirectionally with original document

### 3.2 Structural Linking: Dependencies and Connect Boards

**Dependencies** (cross-board timing relationships)
- Link tasks across multiple boards: "Task A depends on Task B from different board"
- Create "Dependent On" column to select dependency targets
- Cross-project dependencies available on Pro+ plans
- Works across board boundaries with "See all projects" toggle

[Source: Cross-Project Dependencies](https://support.monday.com/hc/en-us/articles/24601183683474-Cross-Project-Dependencies)

**Connect Boards Column** (structured cross-board references)
- Link items to items on other boards
- One column can connect to multiple boards (up to 60 per item)
- Enables automated linking: cross-board automations match data points and auto-create connections
- Bidirectional visibility: connected items appear on both sides

[Source: The Connect Boards Column](https://support.monday.com/hc/en-us/articles/360000635139-The-Connect-Boards-Column)

### 3.3 API Structure

**Assets (Files) API**
- Metadata: name, assetId, isImage, fileType, createdAt, createdBy
- Queryable via GraphQL nested queries
- Separate endpoints for reading, updating, clearing file columns

**Items API**
- Items can have multiple file columns and file attachments
- Dependencies and connect-boards relationships queryable as item properties
- Structured data model: each column type has defined schema

[Source: Assets (files) - Apps Framework](https://developer.monday.com/api-reference/reference/assets-1)
[Source: Items - Apps Framework](https://developer.monday.com/api-reference/reference/items)

### 3.4 Key Pattern

**Column-as-metadata schema**: Files, dependencies, and cross-board links are all column types. Each column is a structured data container with defined field schema. Relationships are first-class board columns, not secondary annotations.

---

## 4. Comparative Analysis: Architectural Patterns

### 4.1 Linking Philosophy

| Platform | Philosophy | Model |
|---|---|---|
| Jira | Issue-centric graph | Bidirectional edge relationships + external references |
| Asana | Task-centric embedding | Attachments embedded in task scope + separate dependency model |
| Monday | Column-centric metadata | All relationships are column types with defined schemas |

### 4.2 Artifact Ownership

**Jira**: Source-of-truth separation
- Artifact lives in Confluence, external system, or attached file
- Issue maintains reference (remote link) without ownership
- Enables single artifact to be referenced by many issues

**Asana**: Embedding
- Attachment owned by task
- Task is the primary container
- Artifact cannot be shared across tasks (no backref available via API)

**Monday**: Column ownership
- File lives in file column (owned by item)
- Connect column creates reference to other items (bidirectional)
- Each item maintains its own files; connect-board is the reference mechanism

### 4.3 Metadata Capabilities

**Jira Custom Fields**
- Arbitrary field types: text, select, number, date, user, etc.
- Can model artifact properties (status, version, type, etc.)
- No native way to connect custom fields to attachments structurally

**Asana Custom Fields**
- Inherit from project to task
- Can model artifact metadata
- Cannot filter/query attachments by custom field values

**Monday.com Columns**
- Column type determines schema (files, links, text, date, people, etc.)
- Each column is a first-class data container
- Can query file column values directly from GraphQL API with full metadata

### 4.4 Cross-System Reference Patterns

**Jira Remote Links** (most sophisticated)

```
Issue -> RemoteLink -> External URL + Metadata
```

Enables: external artifact system maintains single source of truth; multiple issues can reference same artifact without redundancy.

**Monday Connect Boards**

```
ItemA -> ConnectColumn -> ItemB (on different board)
```

Enables: cross-board relationships without duplication; automated linking via shared data fields.

**Asana Dependencies** (limited to timing)

```
TaskA -> DependsOn -> TaskB
```

Enables: workflow sequencing, not artifact referencing. No structural connection between dependencies and attachments.

---

## 5. Data Model Specifics

### 5.1 REST/GraphQL Endpoints

**Jira REST API Issue Links**

```
POST /rest/api/3/issueLink
{
  "outwardIssue": {"key": "PROJECT-1"},
  "inwardIssue": {"key": "PROJECT-2"},
  "linkType": {"name": "Blocks"}
}
```

**Jira REST API Remote Links**

```
POST /rest/api/2/issue/{issueIdOrKey}/remotelink
{
  "url": "https://example.com/spec/123",
  "title": "Design Specification",
  "relationship": "documents",
  "iconUrl": "...",
  "summary": "..."
}
```

**Asana API Attachments**

```
GET /attachments/{attachment_gid}
→ {name, resource_subtype, created_at, created_by, url, view_url, resource}
```

**Monday GraphQL Files Column**

```graphql
query {
  items {
    id
    column_values(ids: ["files_column_id"]) {
      id
      value  # JSON: [{name, assetId, isImage, fileType, createdAt, createdBy}]
    }
  }
}
```

### 5.2 Relationship Direction

**Jira**: Explicit inward/outward semantics
- Each link type has bidirectional interpretation rules
- API query returns both sides depending on perspective
- Enables semantic understanding at issue view time

**Monday**: Implicit bidirectional
- Connect column automatically shows connections from both sides
- No separate "inward" metadata — visibility is automatic
- Simpler model, less semantic detail

**Asana**: No native linking
- Attachments have no back-reference
- Dependencies don't reference artifacts
- External URL attachments are opaque (no metadata extraction)

---

## 6. Applicability to Claude Skills Repository

### 6.1 Pattern for Plan Artifacts

**Current State** (plan files + task files + backlog GitHub issues)

```
Issue #N → GitHub issue body (groomed content)
         → Local plan/tasks-{N}-{slug}.md (SAM plan file)
         → Architecture spec file
         → Feature context file
```

### 6.2 Recommendation: Jira-Inspired Remote Linking

**Why**: Plan artifacts are already distributed (GitHub issues, local plan files, architecture specs). A Jira-style remote-linking approach avoids redundancy:

**Model**:

```
GitHub Issue #N → (canonical source)
                → Links to:
                   - plan/{N}-{slug}.yaml (plan file)
                   - plan/architect-{slug}.md (architecture)
                   - plan/feature-context-{slug}.md (research)
                   - Backlog item metadata (grooming status)
```

**Implementation**:
- Store artifact links in issue body or custom field
- Each plan artifact includes back-reference to GitHub issue
- Single source of truth per artifact; issue maintains reference collection
- CLI/API can traverse links bidirectionally

### 6.3 Alternative: Monday-Inspired Connect Pattern

**Why**: If task/artifact relationships need cross-board querying:

**Model**:

```
Task Item (GitHub issue)
  → Connect Column: [linked plan files]
  → Files Column: [spec attachments]
  → Dependencies Column: [blocking tasks]
```

Benefits: Structured metadata, first-class querying, visual relationship representation.

Drawback: Requires adopting Monday or similar platform; doesn't work with GitHub issues as source of truth.

### 6.4 Alternative: Asana-Inspired Embedding

**Why**: Simpler, no external reference system:

**Model**:

```
GitHub Issue
  → Task description (embedded feature context)
  → Attachments section (inline plan, architecture)
  → Custom field: artifact_manifest (JSON list)
```

Drawback: Creates redundancy (artifacts stored in issue + as files); harder to maintain single source of truth.

---

## 7. Key Insights for Artifact Linking System Design

1. **Separate reference from ownership**: Jira's remote links model avoids redundancy by keeping artifact authoritative and maintaining issue-side references. Monday's connect boards do the same across items.

2. **Bidirectional semantics matter**: Jira's inward/outward descriptions enable rich relationship interpretation. Plain URLs (Asana) lose semantic meaning.

3. **Metadata is structural**: Monday's column model treats all relationships as first-class data structures with queryable schemas. Generic "attachment" fields lose discoverability.

4. **Dependencies ≠ artifact references**: Asana conflates task dependencies (timing) with artifact attachment (content reference). Keep these separate.

5. **API design determines usage**: Jira's REST API for remote links enables programmatic linking; Asana's attachment endpoint is file-transport only. Architecture determines what becomes possible at scale.

6. **Project-level artifacts need special handling**: Asana's "key resources" section (project-level files) is mentioned but underdeveloped. Jira's Confluence integration assumes wiki-style hierarchy. Monday's files columns are task-scoped.

---

## Sources

- [Jira issue linking model](https://developer.atlassian.com/cloud/jira/platform/issue-linking-model/)
- [Jira REST API issue links](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-links/)
- [Creating Remote Issue Links](https://developer.atlassian.com/server/jira/platform/creating-remote-issue-links/)
- [Use Jira and Confluence together](https://support.atlassian.com/confluence-cloud/docs/use-jira-and-confluence-together/)
- [Link Jira issues to Confluence pages automatically](https://www.atlassian.com/blog/confluence/link-jira-issues-to-confluence-pages-automatically)
- [Jira Cloud REST API - Attachments](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/)
- [Asana Attachments API](https://developers.asana.com/reference/attachments)
- [Asana Task dependencies](https://help.asana.com/s/article/task-dependencies?language=en_US)
- [Get attachments from an object](https://developers.asana.com/reference/getattachmentsforobject)
- [Monday.com The Files Column](https://support.monday.com/hc/en-us/articles/360000597900-The-Files-Column)
- [Monday.com Cross-Project Dependencies](https://support.monday.com/hc/en-us/articles/24601183683474-Cross-Project-Dependencies)
- [Monday.com The Connect Boards Column](https://support.monday.com/hc/en-us/articles/360000635139-The-Connect-Boards-Column)
- [Monday.com Assets (files) - API](https://developer.monday.com/api-reference/reference/assets-1)
- [Monday.com Items - API](https://developer.monday.com/api-reference/reference/items)
