---
title: "GitHub Projects V2 Custom Fields API Research"
---

## Research Questions Answered

### 1. What field types does GitHub Projects V2 support?

**VERIFIED FIELD TYPES** (Source: [GitHub Projects V2 Understanding Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields))

GitHub Projects V2 supports the following custom field types:

- **Text** — freeform text content, searchable in filters
- **Number** — numeric values including decimals, supports comparison filters (>, >=, <, <=, ..)
- **Date** — date picker interface with searchable values
- **Single Select** — dropdown with predefined options, each with name, description, and color
- **Iteration** — sprint/iteration planning, includes `duration`, `startDate`, and `title` properties

**System/Built-in Field Types** (not custom-creatable):
- **Issue fields** — organization-level structured metadata (Priority, Effort, Start date, Target date by default)
- **Label** — references to GitHub labels
- **Milestone** — references to GitHub milestones
- **Repository** — linked repository references
- **Pull Request** — linked PR references and reviewer information
- **Parent/Sub-issue Progress** — shows parent issue and sub-issue progress
- **Issue Type** — displays the issue type

Sources:
- [Understanding Fields Index](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields)
- [About Text and Number Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-text-and-number-fields)
- [Gist: Notes about using the new GitHub ProjectV2 API](https://gist.github.com/richkuz/e8842fce354edbd4e12dcbfa9ca40ff6)

---

### 2. What is the maximum character/byte limit for text fields?

**STATUS**: NOT EXPLICITLY DOCUMENTED

GitHub's official documentation for Projects V2 text fields does not specify a character or byte limit. The documentation states only: "You can use text fields to include notes or any other freeform text in your project."

For comparison, GitHub issue comments have a 65,536 character limit, but this does not apply to Projects V2 text fields.

**Note**: Maximum likely follows broader GitHub API string limits (typically 65KB), but this is not officially confirmed for Projects V2 text fields. Empirical testing would be required to determine the exact limit.

Sources:
- [About Text and Number Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-text-and-number-fields) — no limit stated
- [GitHub Discussion #41331: Comment Character Limits](https://github.com/orgs/community/discussions/41331) — applies to issue comments, not Projects V2 fields

---

### 3. Can text fields store structured data (JSON, markdown tables)?

**STATUS**: UNSUPPORTED FOR STRUCTURED QUERIES

Text fields are designed for freeform text only. While you can technically store JSON or markdown tables as text strings, the API provides no structured parsing, validation, or query support for such data.

Key limitation:
- Text field filters treat content as literal strings: `field:"exact text"`
- No JSON schema validation or path-based queries
- No markdown rendering or special parsing

**Better approach for structured metadata**: Use [GitHub Issue Fields](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/managing-issue-fields-in-your-organization) (organization-level, in public preview) which support typed Single Select, Text, Number, and Date fields with validation and filtering.

Sources:
- [About Text and Number Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-text-and-number-fields)
- [Issue Fields: Structured Metadata Public Preview](https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/)

---

### 4. Can you create custom fields programmatically via GraphQL API?

**STATUS**: PARTIALLY SUPPORTED WITH LIMITATIONS

**Yes, you can create custom fields using the `createProjectV2Field` mutation**

The GraphQL mutation accepts these parameters:
- `projectId` (required) — the project ID
- `name` (required) — field name
- `dataType` (required) — field type (TEXT, NUMBER, DATE, SINGLE_SELECT)
- `singleSelectOptions` — array of option definitions for single-select fields

**Critical limitation: Field editing is NOT supported via API**

According to GitHub community discussion, "the issue though is editing them" and "the api does not allow for that at the time being." Once created, you cannot modify field definitions through the GraphQL API.

Sources:
- [GitHub Community Discussion #35922: Create custom field with options](https://github.com/orgs/community/discussions/35922)
- [WebSearch Results: GitHub Projects custom fields create programmatically](https://github.com/orgs/community/discussions/35922)

---

### 5. Can you read/write custom field values via GraphQL API?

**STATUS**: FULLY SUPPORTED

**Reading field values:**
- Query via `ProjectV2Item` with `fieldValueByName(name: "FieldName")`
- Returns typed values: `ProjectV2ItemFieldTextValue`, `ProjectV2ItemFieldDateValue`, `ProjectV2ItemFieldNumberValue`, `ProjectV2ItemFieldSingleSelectValue`, `ProjectV2ItemFieldIterationValue`

**Writing field values:**
- Use `updateProjectV2ItemFieldValue` mutation
- Supports:
  - Text, number, date fields: use `text` parameter
  - Single select fields: use `singleSelectOptionId` parameter
  - Iteration fields: use `iterationId` parameter
- **Cannot be used for**: Assignees, Labels, Milestone, Repository (these are issue properties, not project properties)

Sources:
- [Using the API to Manage Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [WebFetch: Reading and Writing Custom Field Values](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)

---

### 6. Is there a limit on the number of custom fields per project?

**STATUS**: VERIFIED LIMIT

**Projects support up to 50 total fields**, including both custom fields and system fields.

Breakdown:
- Issue fields (organization-level): count toward the 50-field limit
- System fields (Title, Assignee, etc.): count toward the limit
- Custom text/number/date/single-select fields: count toward the limit

**If a project reaches the 50-field limit**, you must delete existing fields before adding new ones.

Additional limits for organization-level Issue Fields:
- Up to **25 Issue Fields** per organization (separate from project-level limit)
- Up to **50 options** per single-select field
- Up to **10 pinned fields** per issue type

Sources:
- [Managing Issue Fields in Your Organization](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/managing-issue-fields-in-your-organization) — "Field limits in projects" section
- [GitHub Discussion #66977: fields limits](https://github.com/orgs/community/discussions/66977)

---

### 7. Can field values be queried/filtered via the API?

**STATUS**: FULLY SUPPORTED

**Querying in REST API:**
- Text fields: exact string match `field:"text value"`
- Number fields: comparison operators (`>`, `>=`, `<`, `<=`) and range queries (`field:5..15`)
- Date fields: date-based filtering
- Single select: option value filtering

**Querying in GraphQL API:**
- Use `fieldValueByName(name: "Field Name")` to retrieve field values for an item
- Full field object includes type-specific properties

**Limitations:**
- Text fields do not support substring or regex matching, only exact matches
- Field value queries require explicit field name knowledge (fragile if field renamed)
- Text field filtering also searches item titles if no field is specified

Sources:
- [About Text and Number Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-text-and-number-fields)
- [Filtering Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/filtering-projects)
- [Some Natalie's Blog: GraphQL Intro using Custom Fields](https://some-natalie.dev/blog/graphql-intro/)

---

## Bonus Questions Answered

### Can GitHub issue comments be pinned or marked as "bot comments"?

**YES — Issue comments can be pinned**

The GraphQL API supports:
- `isPinned` field on `IssueComment` objects — returns boolean indicating pinned status
- `pinnedAt` field — timestamp when pinned
- `pinnedBy` field — user who pinned the comment
- `viewerCanPin` and `viewerCanUnpin` mutations — for programmatic pinning

Pinned comments generate timeline events: `IssueCommentPinnedEvent` and `IssueCommentUnpinnedEvent`

**Bot comment identification:**
- No official "bot" marker field on comments
- Bot identification relies on:
  - Author's `authorAssociation` field (values: COLLABORATOR, CONTRIBUTOR, FIRST_TIMER, FIRST_TIME_CONTRIBUTOR, MANNEQUIN, MEMBER, NONE, OWNER)
  - User account type (bots typically have robot icon)
  - Comment author user agent or username pattern matching
- REST API returns pinned event type in issue timeline

Sources:
- [GraphQL Objects: IssueComment](https://docs.github.com/en/graphql/reference/objects) — `isPinned`, `pinnedAt`, `pinnedBy` fields
- [REST API: Issue Event Types - Pinned](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types?apiVersion=2022-11-28#pinned)

---

### Is there a way to store structured metadata on a GitHub issue beyond the body, labels, and milestones?

**YES — GitHub Issue Fields (Public Preview, 2026-03-12)**

[Issue Fields](https://docs.github.com/en/issues/tracking-your-work-with-projects/using-issues/managing-issue-fields-in-your-organization) provide organization-level structured metadata:

**Capabilities:**
- Create up to **25 typed fields** per organization
- Four field types: Single Select, Text, Number, Date
- Cross-repository: fields apply to all issues in the organization
- Searchable and filterable by field value
- Webhook support: `field_added`, `field_removed` events
- GraphQL and REST API management
- Optional visibility control: org-only or public

**Default fields** (auto-created):
- Priority (single select: Urgent, High, Medium, Low)
- Effort (single select: High, Medium, Low)
- Start date (date)
- Target date (date)

**Advantage over labels:**
- Typed values with validation
- Consistent across organization
- Reportable and queryable
- Not limited to predefined labels

**Additional metadata storage:**
- Issue body (markdown, manually parsed)
- Custom labels (limited, untyped)
- Milestone (single value)
- Assignees (user references)

Sources:
- [GitHub Blog Changelog: Issue Fields Public Preview](https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/)
- [Managing Issue Fields in Your Organization](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/managing-issue-fields-in-your-organization)

---

## Summary Table: GitHub Custom Metadata Solutions

| Feature | Projects V2 Fields | Issue Fields | Labels | Milestone |
|---------|-------------------|--------------|--------|-----------|
| Scope | Per-project | Org-wide | Org-wide | Per-repo |
| Field Types | Text, Number, Date, Single Select, Iteration | Text, Number, Date, Single Select | — | — |
| Create via API | Yes (GraphQL) | Yes (GraphQL/REST) | Yes | Yes |
| Edit via API | No | Yes | Yes | Yes |
| Query/Filter via API | Yes | Yes | Yes | Yes |
| Validation | Basic | Yes (typed) | No | No |
| Max per org/project | 50 per project | 25 per org | Unlimited | 1 per issue |
| Access Control | Project-level | Org-level visibility | Repo-level | Repo-level |

---

## Evidence Inventory

All claims in this report are sourced from primary GitHub documentation or verified GitHub community discussions:

| Question | Primary Sources | Status |
|----------|-----------------|--------|
| Field types | [Understanding Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields), [Gist](https://gist.github.com/richkuz/e8842fce354edbd4e12dcbfa9ca40ff6) | VERIFIED |
| Text field character limit | [Text and Number Fields Docs](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-text-and-number-fields) | NOT DOCUMENTED |
| Structured data in text fields | Text and Number Fields Docs | UNSUPPORTED |
| Programmatic field creation | [Discussion #35922](https://github.com/orgs/community/discussions/35922) | VERIFIED WITH LIMITATION |
| Read/write field values | [Using the API to Manage Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects) | VERIFIED |
| Field count limit | [Managing Issue Fields](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/managing-issue-fields-in-your-organization) | VERIFIED |
| Query/filter support | [Text and Number Fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-text-and-number-fields), [Filtering Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/filtering-projects) | VERIFIED |
| Comment pinning | [GraphQL Objects](https://docs.github.com/en/graphql/reference/objects), [REST Events](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types) | VERIFIED |
| Structured metadata on issues | [Issue Fields Announcement](https://github.blog/changelog/2026-03-12-issue-fields-structured-issue-metadata-is-in-public-preview/) | VERIFIED |
