---
title: "Research: How Linear Handles Artifact and Document Linking"
---

## Executive Summary

Linear treats documents and artifacts as **first-class resources** within issues and projects, with multiple linking mechanisms:

1. **Embedded Documents**: Documents created within issues via the Resources section
2. **Bi-directional References**: @ mentions link documents, issues, and projects to each other
3. **Hierarchical Sub-issues**: Parent-child relationships with optional cascade automation
4. **Relationship Types**: Four structured relationship types (Related, Blocked, Blocking, Duplicate)
5. **MCP Integration**: 21+ tools available for programmatic issue/document access (including relationships and sub-issues)

Linear's approach is **artifact-forward**: documents are not attachments but structural entities with full editing, versioning, and comment capabilities.

---

## 1. How Linear Links Design Docs, Specs, and Artifacts to Issues

### Document Attachment Method

Documents are created directly within issues, not uploaded/attached as external files.

> "Documents are created within an issue under the … menu > Add Document and get added to the resources section of an issue." — Linear Docs (Issue Documents)

The Resources section serves as the artifact manifest for each issue — a dedicated container organizing all related documents, specs, and external links.

### External Link Integration

For artifacts outside Linear, you can add links to the Resources section:

> "If you'd like to link related files that live outside of Linear, you can add a link to the Resources section of an issue or using CTRL L on your keyboard." — Linear Docs (Issue Documents)

### Bi-directional Reference System

Cross-linking is enabled through @ mentions:

> "You can reference documents in issue descriptions, comments, and even in other documents by typing @ while in edit mode followed by the document name." — Linear Docs (Issue Documents, Project Documents)

This works in reverse as well:
> "You can also reference issues and projects within documents" using the @ symbol during editing. — Linear Docs (Project Documents)

---

## 2. Linear's Artifact Manifest and Structured Attachment System

### Resources Section as Manifest

Each issue has a dedicated **Resources section** that aggregates:
- **Embedded documents** (created via "Add Document")
- **External links** (URLs to files outside Linear)
- **Related issues/projects** (via @ mentions)

Linear does not use a traditional file attachment system. Instead, it uses structured document objects with full editorial capabilities.

### Document Metadata Tracked

When documents are attached to issues, Linear maintains:

- **Creator information** — document author automatically subscribed to changes
- **Edit history** — displays "when the document was last edited and by whom"
- **Version history** — users can revert documents to previous versions
- **Timestamps** — records creation, edits, comments, deletions
- **Inline comments** — supports resolved/unresolved comment tracking
- **Real-time sync** — changes automatically sync across users without manual saves

### Document Templates

Linear supports reusable templates for consistent artifact structure:

> "You can create document templates to write documents faster and guide creators to share information effectively, which can be selected when creating a new document inside a project or issue, and can be set up in either the workspace template settings or team template settings." — Linear Docs

---

## 3. Linear's MCP Integration and Artifact Relationships

### MCP Server Availability

Linear provides an official MCP server with **21+ tools** for programmatic access. From Linear's MCP documentation and third-party implementations:

> "The MCP server has tools available for finding, creating, and updating objects in Linear like issues, projects, and comments — with more functionality on the way." — Linear Docs (MCP Server)

### Available MCP Tools for Artifact Linking

**Issue Retrieval with Relationships**:
- `get_issue` — Retrieves issue with optional `includeRelationships` parameter that includes:
  - Comments
  - Parent/sub-issues
  - Related issues
  - Extracted mentions

**Issue Creation with Sub-issue Support**:
- `create_issue` — Creates issues or sub-issues with parameters:
  - `parentId` (UUID for parent issue, enables sub-issue creation)
  - `title`, `description`, `teamId`, `status`, `priority`, `assigneeId`, `labelIds`

**Issue Querying**:
- `list_issues` — Advanced filtering for comprehensive issue listing
- `list_my_issues` — Issues assigned to authenticated user

**Comment Management**:
- `list_comments` — Retrieve comments (includes document-level comments)
- `create_comment` — Add comments to issues or documents

**Relationship Management** (implied by available tools):
- Issue relationships are queryable via `get_issue` with relationship expansion
- Sub-issue hierarchies are navigable via parent/child fields

### MCP Tool Summary

The Linear MCP server exposes issue, comment, project, and team management tools but **does not provide dedicated document/artifact querying tools**. Document access is implicit through issue relationships and comment threads.

---

## 4. Linear's Sub-issue and Relationship System

### Sub-issues (Hierarchical Linking)

Linear supports parent-child issue hierarchies:

> "Use sub-issues to break down larger 'parent' issues into smaller pieces of work." — Linear Docs (Parent and Sub-issues)

Sub-issues are useful for work that is "too large to be a single issue but too small to be a project."

**Creation Methods**:
- "+ Add sub-issues" button within parent issue
- Keyboard shortcut: Command Shift O
- Convert checklist items to sub-issues
- Use command menu to transform regular issues into sub-issues

**Cascade Automation**:
> "When all sub-issues are marked as done, the parent issue will also be marked as done automatically." — Linear Docs (Parent and Sub-issues)

### Issue Relationship Types

Linear supports **four structured relationship types**:

1. **Related** — General connections between issues
2. **Blocked** — Issues prevented from progress by other issues
3. **Blocking** — Issues that prevent other work from proceeding
4. **Duplicate** — Issues merged into a canonical issue

**Tracking Mechanism**:
- Automatic linking when issues are referenced in descriptions/comments
- Visual indicators with color-coded flags:
  - Orange: "blocked by"
  - Red: "blocks"
  - Green: resolved (status changed)
- Canonical issue pattern for duplicates (merged with canceled status)

---

## 5. Linear's Data Model for Issue → Artifact Relationships

### Structural Hierarchy

```
Workspace
  ├─ Project
  │   └─ Documents (project-level)
  └─ Issue
      ├─ Documents (issue-level, in Resources section)
      ├─ Relationships (Related, Blocked, Blocking, Duplicate)
      ├─ Sub-issues (parent-child hierarchy)
      ├─ Comments (with inline threading and resolution)
      └─ External Links (URLs in Resources section)
```

### Artifact Linkage Patterns

**Pattern 1: Embedded Documents**
- Documents are native Linear entities (not files)
- Created within issues via "Add Document"
- Stored in issue's Resources section
- Support full editing, versioning, and comments

**Pattern 2: Bi-directional References**
- @ mention syntax creates cross-references
- Works in issue descriptions, comments, documents
- References are structural (not just text matches)

**Pattern 3: Hierarchical Sub-issues**
- Parent-child relationships via `parentId` in MCP
- Supports cascade automation (all done → parent done)
- Useful for decomposing complex work

**Pattern 4: Typed Relationships**
- Explicit relationship types: Related, Blocked, Blocking, Duplicate
- Tracked in issue's relationship sidebar
- Automatic linking via issue references in text

**Pattern 5: External Links**
- URLs added to Resources section via CTRL L
- Trackable as artifact dependencies
- No automatic content fetch (references only)

### GraphQL API for Artifact Data

Linear's GraphQL API (<https://api.linear.app/graphql>) exposes:
- **Attachments**: Webhook support for attachment change events
- **Documents**: Full document entity with relationships
- **Issue Relationships**: Parent/child and relationship type fields
- **Comments**: Thread-level comment data with resolution status

From Linear's developer documentation:
> "Webhooks support data change events for Issues, Comments, Issue attachments, Documents, Emoji reactions, Projects, Project updates, Cycles, Labels, Users and Issue SLAs" — Linear Developers (API and Webhooks)

---

## 6. Comparison with Other Systems (Contextual Notes)

Linear's approach differs from GitHub Issues in several ways:

| Aspect | Linear | GitHub Issues |
|--------|--------|---------------|
| Documents | Native entities within issues | Rendered markdown in issue body + wiki |
| Sub-issues | Parent-child hierarchy | GitHub Projects with sub-issue tracking |
| Relationships | Typed (Related/Blocked/Blocking/Duplicate) | Pull request links, manual references |
| Versioning | Full document version history | Commit history only |
| MCP Support | Official MCP server (21+ tools) | Unofficial/third-party MCP servers |

---

## Key Findings

### Finding 1: Documents are Structural, Not Attachments
Linear treats documents as first-class entities with full editing, versioning, and commenting. They are not file attachments but organizational primitives.

### Finding 2: Multi-layer Linking
- **Embedded**: Documents in issue Resources sections
- **References**: @ mentions create bi-directional cross-links
- **Hierarchical**: Parent-child sub-issue relationships
- **Relational**: Typed issue-to-issue relationships
- **External**: URLs to out-of-Linear artifacts

### Finding 3: No Dedicated "Artifact Manifest" API
The MCP server does not expose a dedicated artifact-manifest query. Instead:
- Document access flows through issue relationship queries
- Comments include document-level discussions
- Resources section is UI-level, not API-level

### Finding 4: Cascade Automation
Sub-issue completion can automatically mark parent issues complete, providing workflow automation for hierarchical work.

### Finding 5: Template-driven Consistency
Document templates enforce consistent structure across specs, PRDs, and other artifacts created within projects or issues.

---

## Implications for claude_skills Repository

Linear's approach offers insights for the SAM (Structured Agent-Managed) workflow:

1. **Plan Artifacts Could Nest Under Issues**: Like Linear's sub-issues, SAM task files could be structured as child items under a GitHub issue (parent story).

2. **Bi-directional Cross-referencing**: The @ mention pattern is lightweight—SAM could use similar syntax for linking task files to architecture specs, feature contexts, and acceptance criteria.

3. **Manifest vs. Hierarchical**: Linear uses a Resources section (manifest) within each issue. SAM uses a task file as a manifest. Linear's approach is more granular; SAM's is more structured. Both are valid.

4. **Relationship Types**: Linear's four types (Related/Blocked/Blocking/Duplicate) could inspire SAM task dependency classification beyond simple "depends on."

5. **MCP Capability Gap**: Linear's MCP server doesn't expose document queries directly—you must fetch via issue relationships. This suggests artifact access should flow through parent-child hierarchies, not direct document queries.

---

## Sources

- [Linear Docs: Issue Documents](https://linear.app/docs/issue-documents)
- [Linear Docs: Issue Relations](https://linear.app/docs/issue-relations)
- [Linear Docs: Project Documents](https://linear.app/docs/project-documents)
- [Linear Docs: Parent and Sub-issues](https://linear.app/docs/parent-and-sub-issues)
- [Linear Docs: MCP Server](https://linear.app/docs/mcp)
- [Linear Developers: API and Webhooks](https://linear.app/docs/api-and-webhooks)
- [Linear Developers: GraphQL Attachments](https://developers.linear.app/docs/graphql/attachments)
- [GitHub: cosmix/linear-mcp](https://github.com/cosmix/linear-mcp) — Third-party MCP implementation
- [Awesome MCP Servers: Linear](https://mcpservers.org/servers/cosmix/linear-mcp)
- [Jan.ai: Linear MCP Examples](https://www.jan.ai/docs/desktop/mcp-examples/productivity/linear)

---

**Status**: DONE
**Artifacts**: Research findings document at `/tmp/research-linear-artifacts.md`
