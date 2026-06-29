# Research: Linear Custom Fields and Structured Metadata Capabilities

**Research Date**: 2026-03-21
**Status**: Complete

---

## Executive Summary

Linear **does not offer traditional custom fields** like GitHub Issues Fields (typed, org-wide metadata). Instead, Linear uses a hybrid approach:

1. **Form Templates** with generic fields (text, long text, dropdown, checkbox, date) — only visible during issue creation
2. **Labels and Label Groups** — the primary mechanism for adding metadata to issues
3. **Attachment Metadata** — key-value pairs and structured metadata for attachments, not issues
4. **Standard issue properties** — a fixed set of properties (assignee, priority, status, due date, etc.)

There is **no equivalent to GitHub's Issue Fields feature** that creates typed, queryable, organization-wide custom metadata on issues themselves.

---

## Question 1: Does Linear Support Custom Fields on Issues?

**Finding**: Linear does NOT support custom fields on issues in the traditional sense.

**Evidence**:

Linear's documentation states: "Linear doesn't offer traditional custom fields, but you can use labels to organize your reports." [Linear Docs - Custom Views](https://linear.app/docs/custom-views)

Instead, Linear supports:

1. **Form Templates** (UI-only, for issue creation):
   - Text (single-line text input)
   - Long text (multi-line text input)
   - Dropdown (one value selected from options)
   - Checkboxes (one or more values selected from options)
   - Date (date picker, not tied to issue property)
   - Instructions (static context text)

   These fields are visible **only during issue creation** and do not create queryable metadata on the issue itself. [Linear Docs - Issue Templates](https://linear.app/docs/issue-templates)

2. **Label Groups** (property fields that can appear in form templates):
   - Priority
   - Customer
   - Label group
   - Title
   - Due date

3. **Standard Issue Properties** (fixed, non-extensible):
   - Team, Status, Assignee, Project, Labels, Sub-issues, Cycle, Estimate

---

## Question 2: Can Custom Fields Be Created/Read/Written via API (GraphQL)?

**Finding**: Custom fields cannot be created via API because Linear does not support custom fields. However, you can create and manage form templates via GraphQL.

**Evidence**:

Linear's GraphQL API supports mutations like `issueCreate` and `issueUpdate`, but there is no `customFieldCreate` or equivalent mutation in the public API schema.

The GraphQL schema is explorable at:
- Apollo GraphOS Studio: [Linear API Schema](https://studio.apollographql.com/public/Linear-API/schema/reference?variant=current)
- Linear Developers: [Getting Started](https://linear.app/developers/graphql)

Form templates (which contain form fields) are referenced in the GraphQL schema as `Template` type, accessible via Apollo Studio's schema browser. [Apollo GraphOS Studio - Template Type](https://studio.apollographql.com/public/Linear-API/variant/current/schema/reference/objects/Template)

However, **no dedicated API documentation for form field mutations was found in the search results**, suggesting form field management may be UI-only or limited in the current API.

---

## Question 3: Does Linear Have an Equivalent to GitHub Issue Fields?

**Finding**: No. Linear has no feature equivalent to [GitHub Issue Fields](https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/) (which provides typed, org-wide, queryable custom metadata).

**Evidence**:

GitHub Issue Fields (recent feature, public preview as of March 2026):
- Full REST and GraphQL API support for field settings (create, update, delete) and field values (get, set, clear)
- Typed fields with defined types
- Organization-wide metadata that travels with issues across projects
- Queryable and filterable in views

Linear alternatives:
- **Form Templates** — UI-only, visible at creation time only
- **Labels/Label Groups** — untyped, used for categorization
- **Attachments with metadata** — supports key-value pairs, but not issue-level custom fields

**No equivalent feature exists in Linear as of March 2026.**

---

## Question 4: How Does Linear's MCP Server Expose Custom Field Data?

**Finding**: Linear's MCP server does not expose custom field data because Linear does not support custom fields. The MCP server provides access to standard issue properties and labels.

**Evidence**:

Linear MCP Server documentation states:
- Available via: [linear.app/docs/mcp](https://linear.app/docs/mcp)
- Changelog entry: [Linear MCP Server - May 2025](https://linear.app/changelog/2025-05-01-mcp)

Capabilities include:
- Create, update, and delete issues
- Search issues using text queries and filters (assignee, creator, project, status, priority, dates, labels)
- Comments and relationships

The MCP server tools support filtering by:
- Project
- Status
- Priority
- Assignee
- Creator
- Labels
- Date ranges

**No mention of custom field support in MCP documentation.** For current MCP capabilities, see: [MCP Marketplace - Linear MCP Server](https://mcpservers.org/servers/cosmix/linear-mcp)

---

## Question 5: What Are the Limits (Max Fields, Field Value Sizes)?

**Finding**: Linear does not publicly document field limits for custom fields because custom fields are not supported.

**Evidence**:

Searched:
- Linear Docs: [linear.app/docs](https://linear.app/docs)
- Linear Developers: [developers.linear.app](https://linear.app/developers/graphql)
- API and Webhooks documentation: [API and Webhooks - Linear Docs](https://linear.app/docs/api-and-webhooks)

No published limits found for:
- Maximum number of custom fields per issue
- Maximum field value sizes
- Maximum metadata size

For form templates (the closest analog), Linear allows:
- Up to 5 generic field types per template
- Attachment metadata: key-value pairs with values as "any string or number" (no explicit max size documented)

**Recommendation**: Contact Linear support at <hello@linear.app> for specific limits on metadata and form field constraints.

---

## Question 6: Can Linear Store Structured Data (JSON, Lists) in Fields?

**Finding**: Limited. Linear supports structured metadata only in attachments, not on issues.

**Evidence**:

### Attachment Metadata (Structured)

Linear attachments support **rich metadata structure** with typed fields: [Attachments - Linear Developers](https://linear.app/developers/attachments)

```
{
  "title": "string",           // Modal heading
  "messages": [                // Conversation data (max 10k characters)
    {
      "subject": "string",
      "body": "string",
      "timestamp": "ISO string"
    }
  ],
  "attributes": [              // Name-value pairs
    {
      "name": "string",
      "value": "string"
    }
  ]
}
```

Date formatting options:
- `{variableName__since}` — renders as "2 days ago"
- `{variableName__relativeTimestamp}` — context-aware formatting

### Generic Key-Value Metadata (Attachments Only)

Attachments also support simple key-value pairs with "any string or number" values, accessible only via API (not UI).

### Issue-Level Structured Data

**Not supported.** Linear issues do not support JSON or structured data fields at the issue level. Form template responses map to standard issue properties or labels only.

---

## Question 7: How Does Linear's Resources Section Work via API?

**Finding**: Linear does not have a "Resources" section on issues. However, Linear supports **Attachments** which serve a similar function for linking external resources.

**Evidence**:

### Attachments (External Resource Linking)

Linear attachments represent external resources (GitHub PR, Jira issue, support ticket, etc.) and can be created/read via GraphQL API:

**Query Example**:

```graphql
query {
  issue(id: "ISSUE-ID") {
    attachments {
      nodes {
        id
        title
        url
        metadata
      }
    }
  }
}
```

**Mutation Example** (create attachment):

```graphql
mutation {
  attachmentCreate(input: {
    issueId: "ISSUE-ID"
    url: "https://github.com/org/repo/pull/123"
    title: "Related PR"
    subtitle: "Code changes"
    iconUrl: "https://..."
    metadata: {
      externalId: "123"
      type: "github_pr"
    }
  }) {
    attachment {
      id
      title
    }
  }
}
```

### Attachment Metadata API Support

- **Read**: Full access via GraphQL `attachments` field on Issue type
- **Write**: Via `attachmentCreate` and `attachmentUpdate` mutations
- **Metadata**: Supports key-value pairs and structured metadata (per Question 6)

### Key Constraints

- Attachment URL is the unique identifier — creating an attachment with an existing URL updates the existing record
- Icon URL: JPG or PNG format, max 1MB, optimal dimensions 20x20px
- Metadata: Only exposed through API, not in Linear UI (team considering UI exposure per docs)

See: [Attachments - Linear Developers](https://linear.app/developers/attachments)

---

## Comparison: Linear vs. GitHub Issue Fields

| Feature | Linear | GitHub Issue Fields |
|---------|--------|-------------------|
| **Custom Fields** | None (labels only) | Yes, typed fields |
| **API Support** | GraphQL (labels, attachments only) | REST + GraphQL for fields |
| **Field Types** | N/A (form templates: text, dropdown, checkbox, date) | Configurable per org |
| **Queryable Metadata** | Labels only | Yes, full field queries |
| **Issue-level Structured Data** | Attachment metadata only | Yes, field values |
| **Org-wide Schema** | No | Yes, org-level field definitions |
| **Form Templates** | Yes, UI-only | Issue fields can populate forms |

---

## Recommendations for Linear Integration

If you need structured metadata storage with Linear:

### Option 1: Use Labels + Label Groups
- Native to Linear
- Queryable via API (filter by label)
- No structured data, but sufficient for categorization

### Option 2: Use Attachment Metadata
- Store JSON/structured data in attachment metadata
- Accessible only via API (not UI)
- Limited to attachments, not issue-wide

### Option 3: Use External Field Mapping
- Store custom fields in an external system (database, JSON file, etc.)
- Sync issue IDs and custom data via API webhook
- Not natively integrated with Linear

### Option 4: Request Feature
- Linear's form templates (Feb 2025) and Asks fields (June 2025) suggest custom field support is under consideration
- Contact Linear product team at <hello@linear.app> to inquire about issue field roadmap

---

## Sources Cited

1. [Linear Docs - Custom Views](https://linear.app/docs/custom-views)
2. [Linear Docs - Issue Templates](https://linear.app/docs/issue-templates)
3. [Linear Developers - GraphQL Getting Started](https://linear.app/developers/graphql)
4. [Apollo GraphOS Studio - Linear API Schema](https://studio.apollographql.com/public/Linear-API/schema/reference?variant=current)
5. [Apollo GraphOS Studio - Template Type](https://studio.apollographql.com/public/Linear-API/variant/current/schema/reference/objects/Template)
6. [GitHub Blog - Issue Fields Public Preview (March 2026)](https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/)
7. [Linear MCP Server Documentation](https://linear.app/docs/mcp)
8. [Linear MCP Changelog - May 2025](https://linear.app/changelog/2025-05-01-mcp)
9. [MCP Marketplace - Linear MCP Server](https://mcpservers.org/servers/cosmix/linear-mcp)
10. [Linear Developers - Attachments](https://linear.app/developers/attachments)
11. [Linear Docs - Creating Issues](https://linear.app/docs/creating-issues)
12. [Linear Docs - API and Webhooks](https://linear.app/docs/api-and-webhooks)
13. [Endgrate - Using Linear API with JavaScript](https://endgrate.com/blog/using-the-linear-api-to-get-issues-(with-javascript-examples))
14. [Linear Changelog - Form Templates (Nov 2025)](https://linear.app/changelog/2025-11-20-form-templates)
15. [Linear Changelog - Asks Fields (June 2025)](https://linear.app/changelog/2025-06-05-asks-fields-and-triage-routing)

---

## Search Gaps & Uncertainties

The following questions could not be fully answered from public documentation:

1. **Form template mutations** — No explicit API documentation found for creating/updating form templates via GraphQL. This capability may exist but is not publicly documented.
2. **Field value size limits** — No published limits for attachment metadata or form field values.
3. **Custom field roadmap** — No public roadmap documentation regarding planned custom field support.

**Next steps**: Direct contact with Linear support or monitoring Linear's changelog for future features.
