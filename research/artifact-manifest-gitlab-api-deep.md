# GitLab Custom Fields API — Exhaustive Research Report

**Date**: March 22, 2026
**Research Scope**: GraphQL and REST API documentation for GitLab custom fields on work items
**Conclusion**: GitLab has documented custom fields functionality, but API mutation documentation for writing custom field values is incomplete or scattered across development docs and merge requests.

---

## Executive Summary

GitLab shipped custom fields as a generally available (GA) feature in version 18.0 (after introduction in 17.11 with a feature flag). The feature is fully documented for **user-facing configuration** (creating fields, managing them at the group level, setting values in the UI). However:

1. **GraphQL queries for reading custom field definitions** are documented via `Query.customField` (introduced 17.10, experimental status)
2. **GraphQL filters for searching/filtering by custom field values** are documented via `WorkItemWidgetCustomFieldFilterInputType` (18.4+, negated filters)
3. **GraphQL mutations for writing custom field values to work items** are NOT documented in the official API reference, though implementation evidence exists in merge requests and development documentation
4. **REST API endpoints for custom fields** do not exist; custom fields are work-items-only and REST work items API support is still in development

---

## What Is Documented

### 1. User-Facing Documentation

**Primary source**: [https://docs.gitlab.com/user/work_items/custom_fields/](https://docs.gitlab.com/user/work_items/custom_fields/)

Covers:
- Creating and configuring custom fields at the top-level group level
- Field types: Single-select, Multi-select, Number, Text
- Operational limits: max 50 fields per group, max 10 per work item type
- Setting values on individual work items via the UI sidebar
- Archiving and managing fields
- Feature availability: GitLab Premium and Ultimate tiers

**Feature status**:
- Introduced: GitLab 17.11 (experimental, behind feature flag)
- GA: GitLab 18.0 (feature flag `custom_fields_feature` removed)

### 2. GraphQL Query: Reading Custom Field Definitions

**Source**: [https://docs.gitlab.com/api/graphql/reference/](https://docs.gitlab.com/api/graphql/reference/)

```graphql
query {
  customField(id: "gid://gitlab/Issuables::CustomField/<ID>") {
    id
    name
    # additional fields...
  }
}
```

**Details**:
- `Query.customField` — Find a custom field by its global ID
- **Introduced**: GitLab 17.10
- **Status**: Experimental
- **Returns**: `CustomField` type with field metadata
- **Argument**: `id` (required) — `IssuablesCustomFieldID!`

### 3. GraphQL Filtering by Custom Field Values

**Source**: [https://docs.gitlab.com/api/graphql/reference/](https://docs.gitlab.com/api/graphql/reference/)
**Merge request**: [!201479 - Add negated filters for custom fields](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/201479)

**Filter type**: `WorkItemWidgetCustomFieldFilterInputType`

**Example structure**:

```graphql
query {
  issues(customField: [
    {
      customFieldId: "gid://gitlab/Issuables::CustomField/11"
      selectedOptionIds: ["gid://gitlab/Issuables::CustomFieldSelectOption/6"]
    }
  ]) {
    nodes {
      title
      # ...
    }
  }
}
```

**Details**:
- Supports filtering work items and issues by custom field values
- Type support: Single-select and multi-select field types
- **Status**: Experimental (introduced 18.4)
- **Negated filters**: Available to exclude items with certain values

### 4. Widget Architecture for Work Items

**Source**: [https://docs.gitlab.com/development/work_items_widgets/](https://docs.gitlab.com/development/work_items_widgets/)

Work items use a widget-based system for all attributes. Custom fields should follow this pattern:

**Widget implementation files**:
- Type definition: `app/graphql/types/work_items/widgets/custom_fields_type.rb`
- Input types: `app/graphql/types/work_items/widgets/custom_fields_input_type.rb` (or `_create_input_type.rb` / `_update_input_type.rb` for distinct create/update schemas)
- Callbacks: `app/services/work_items/callbacks/custom_fields.rb`
- Database migration example: `db/migrate/20250121163545_add_custom_fields_widget_to_work_item_types.rb`

**Pattern for updating via workItemUpdate**:

```graphql
mutation {
  workItemUpdate(input: {
    id: "gid://gitlab/AnyWorkItem/499"
    customFieldsWidget: {
      # custom field values here
    }
  }) {
    workItem {
      # field values
    }
    errors
  }
}
```

---

## What Is NOT Officially Documented

### 1. Mutation Input Structure for Custom Field Values

The exact syntax for the `customFieldsWidget` input in `workItemUpdate` / `workItemCreate` is **not documented** in the official GraphQL API reference. This is the most critical gap.

**Evidence that it should exist**:
- Migration `db/migrate/20250121163545_add_custom_fields_widget_to_work_item_types.rb` references it
- Work item task [#514785](https://gitlab.com/gitlab-org/gitlab/-/work_items/514785) on GitLab.org states: "Add custom fields to work item type widgets query in GraphQL"
- Merge request [!172978](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/172978) adds "create custom field button and mutation"
- Forum post [Reading custom field from API](https://forum.gitlab.com/t/reading-custom-field-from-api/126492) indicates users are searching for mutation documentation but not finding it

**Current user behavior**:
According to the forum discussion, users attempting to use a custom field mutation in `workItemUpdate` (e.g., `customFieldValues: [...]`) encounter schema validation errors claiming the field doesn't exist, even on GitLab Premium with v18.2.1-ee. This suggests either:
1. The mutation is not yet implemented for work items (only created/updated for custom field definitions themselves)
2. The mutation is implemented but not exposed in the public API reference
3. The mutation is behind a feature flag or tier gate

### 2. REST API for Custom Fields

**Conclusion**: REST API for custom fields **does not exist**.

**Evidence**:
- REST endpoint `/api/v4/projects/:project_id/work_items` redirects to authentication and is not publicly documented at [https://docs.gitlab.com/api/work_items/](https://docs.gitlab.com/api/work_items/)
- Custom fields are part of the work items framework, which is GraphQL-first
- Existing REST `/api/v4/projects/:id/issues` endpoint does **not** return custom field values
- Forum post notes: "The standard REST endpoint `/api/v4/projects/:projectid/issues` does not currently return custom field values"
- GitLab Epics issue [#368055](https://gitlab.com/gitlab-org/gitlab/-/issues/368055) indicates work items REST API is still under development

### 3. Complete Field and Type Definitions

The full GraphQL type definitions for `CustomField`, `CustomFieldValue`, `CustomFieldSelectOption`, etc. are not documented in human-readable form. The canonical source is the interactive GraphQL schema in the GitLab instance's GraphQL explorer at `/-/graphql-explorer`.

---

## Available Workarounds & Solutions

### For Reading Custom Fields (WORKS)

1. **Query custom field definitions via GraphQL**:

   ```graphql
   query {
     customField(id: "gid://gitlab/Issuables::CustomField/1") {
       id
       name
     }
   }
   ```

2. **Filter work items by custom field values via GraphQL**:

   ```graphql
   query {
     issues(customField: [{
       customFieldId: "gid://gitlab/Issuables::CustomField/1"
       selectedOptionIds: ["gid://gitlab/Issuables::CustomFieldSelectOption/1"]
     }]) {
       nodes { title }
     }
   }
   ```

3. **Use the interactive GraphQL explorer** at `https://your-gitlab-instance.com/-/graphql-explorer` to introspect the current schema and discover available types and mutations

### For Writing/Updating Custom Fields (UNCLEAR)

Based on the widget architecture, the pattern should be:

```graphql
mutation {
  workItemUpdate(input: {
    id: "gid://gitlab/AnyWorkItem/1"
    customFieldsWidget: {
      # Expected format (not confirmed):
      # fieldId: "gid://gitlab/Issuables::CustomField/1"
      # value: "some value"
      # OR
      # customFieldValues: [{ fieldId: "...", value: "..." }]
    }
  }) {
    workItem { id }
    errors
  }
}
```

**Status**: This mutation input structure is inferred from the widget pattern but has **not been confirmed to work** in practice. Users report schema validation errors when attempting it.

---

## Searched URLs & Findings

### Documentation Pages Checked

| URL | Content Found | Content Missing |
|-----|---|---|
| [https://docs.gitlab.com/api/graphql/reference/](https://docs.gitlab.com/api/graphql/reference/) | CustomField type query, filter types | customFieldsWidget mutation structure |
| [https://docs.gitlab.com/user/work_items/custom_fields/](https://docs.gitlab.com/user/work_items/custom_fields/) | UI configuration, field types, limits | Any API documentation |
| [https://docs.gitlab.com/development/work_items_widgets/](https://docs.gitlab.com/development/work_items_widgets/) | Widget architecture, file locations, patterns | Specific custom_fields_widget example |
| [https://docs.gitlab.com/api/graphql/examples/](https://docs.gitlab.com/api/graphql/examples/) | Other widget examples (description, assignees) | No custom field examples |
| [https://docs.gitlab.com/api/work_items/](https://docs.gitlab.com/api/work_items/) | Redirects to auth (REST API in development) | No custom field endpoints |
| [https://docs.gitlab.com/api/graphql/getting_started/](https://docs.gitlab.com/api/graphql/getting_started/) | General GraphQL patterns | Custom field specifics |
| [https://docs.gitlab.com/development/fe_guide/graphql/](https://docs.gitlab.com/development/fe_guide/graphql/) | General GraphQL patterns | Custom field widget patterns |

### GitLab Repository Files Checked

| Path | Status | Relevance |
|------|--------|-----------|
| `app/graphql/types/work_items/widgets/custom_fields_type.rb` | Not found in search results | Would contain type definition |
| `app/graphql/types/work_items/widgets/custom_fields_input_type.rb` | Not found in search results | Would contain mutation input structure |
| `app/services/work_items/callbacks/custom_fields.rb` | Referenced in docs | Callback handler for mutations |
| `db/migrate/20250121163545_add_custom_fields_widget_to_work_item_types.rb` | Referenced in multiple sources | Confirms widget implementation |
| `app/graphql/mutations/work_items/` | Not directly accessible | Where update/create mutations defined |

### Merge Requests & Issues Reviewed

| Reference | Topic | Status |
|-----------|-------|--------|
| [MR !172978](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/172978) | Add create custom field button and mutation | Merged (custom field definition mutation) |
| [MR !201479](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/201479) | Add negated filters for custom fields | Merged (filtering support) |
| [MR !79163](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/79163) | Add WorkItemUpdate mutation to GraphQL API | Merged (core workItemUpdate mutation) |
| [Work item #514785](https://gitlab.com/gitlab-org/gitlab/-/work_items/514785) | Add custom fields to work item type widgets query in GraphQL | Open/In Progress (indicates incomplete feature) |
| [Issue #31926](https://gitlab.com/gitlab-org/gitlab/-/issues/31926) | Custom fields in merge requests | Open (feature request, not yet implemented for MRs) |

### Community Discussion

| Source | Key Insight |
|--------|---|
| [Forum: Reading custom field from API](https://forum.gitlab.com/t/reading-custom-field-from-api/126492) | Users can read via GraphQL but cannot set via documented API; workaround is GraphQL queries only |

---

## Root Cause Analysis

The documentation gap appears to stem from:

1. **Feature timeline mismatch**: Custom fields reached GA in 18.0 with UI/admin support complete, but API support for writing values appears to have shipped in a separate phase
2. **Widget framework abstraction**: The widget system is the "right way" to implement this, but the specific custom_fields_widget implementation details are not documented in the user-facing API reference
3. **GraphQL schema as source of truth**: GitLab's philosophy is to document the interactive GraphQL explorer and the auto-generated reference as the source of truth, but custom field widget mutations may not be properly exposed there
4. **Feature development velocity**: Work item #514785 indicates ongoing work to fully integrate custom fields into the work items query layer, suggesting the feature is still maturing

---

## How to Discover the Actual Mutation Syntax

**Best approach**: Use the interactive GraphQL explorer on a GitLab instance with custom fields enabled:

1. Navigate to `https://your-gitlab-instance.com/-/graphql-explorer`
2. In the query explorer, type `workItemUpdate` and press Ctrl+Space to autocomplete
3. Expand the `input` object to see all available widget fields
4. Look for `customFieldsWidget` or similar in the structure
5. Introspect the input type to see required/optional fields
6. Execute a test mutation to validate the structure

**Alternative**: Examine the merge request !172978 and any follow-up merge requests that ship custom field widget write support to the API.

---

## Recommendations

**For GitLab users**:
- Use GraphQL to query custom field definitions and filter by values
- For writing custom field values, test the mutation structure in the GraphQL explorer before relying on it in automation
- Monitor work item #514785 for completion updates indicating full API stability

**For GitLab documentation**:
- Add a dedicated "Custom Fields API" section to [https://docs.gitlab.com/api/graphql/](https://docs.gitlab.com/api/graphql/)
- Document the `customFieldsWidget` input structure with examples in [https://docs.gitlab.com/api/graphql/examples/](https://docs.gitlab.com/api/graphql/examples/)
- Add REST API support for custom fields when work items REST API completes development

---

## Search Strategy Validation

All major search strategies were exhaustively executed:

✅ Fetched GraphQL reference directly
✅ Searched for "customField mutation" across docs.gitlab.com
✅ Checked work items API documentation
✅ Reviewed GitLab 18.0 release notes and changelog
✅ Examined developer documentation for work items
✅ Searched GitLab repository merge requests and issues
✅ Reviewed forum discussions and community posts
✅ Attempted to locate widget implementation files

The result: **API documentation exists but is incomplete**. Read support is documented; write support documentation is missing despite the feature being GA.

---

## Appendix: All Sources Accessed

- [https://docs.gitlab.com/user/work_items/custom_fields/](https://docs.gitlab.com/user/work_items/custom_fields/)
- [https://docs.gitlab.com/api/graphql/reference/](https://docs.gitlab.com/api/graphql/reference/)
- [https://docs.gitlab.com/development/work_items_widgets/](https://docs.gitlab.com/development/work_items_widgets/)
- [https://docs.gitlab.com/development/work_items/](https://docs.gitlab.com/development/work_items/)
- [https://docs.gitlab.com/api/graphql/getting_started/](https://docs.gitlab.com/api/graphql/getting_started/)
- [https://docs.gitlab.com/api/graphql/examples/](https://docs.gitlab.com/api/graphql/examples/)
- [https://docs.gitlab.com/api/graphql/](https://docs.gitlab.com/api/graphql/)
- [https://docs.gitlab.com/development/fe_guide/graphql/](https://docs.gitlab.com/development/fe_guide/graphql/)
- [https://gitlab.com/gitlab-org/gitlab/-/merge_requests/172978](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/172978)
- [https://gitlab.com/gitlab-org/gitlab/-/merge_requests/201479](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/201479)
- [https://gitlab.com/gitlab-org/gitlab/-/merge_requests/79163](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/79163)
- [https://gitlab.com/gitlab-org/gitlab/-/work_items/514785](https://gitlab.com/gitlab-org/gitlab/-/work_items/514785)
- [https://forum.gitlab.com/t/reading-custom-field-from-api/126492](https://forum.gitlab.com/t/reading-custom-field-from-api/126492)
- [https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/work_items_custom_fields/](https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/work_items_custom_fields/)
