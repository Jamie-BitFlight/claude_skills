---
title: Awesome Codex Skills — Issue Triage
subtitle: Automated bulk issue triage and deduplication for Linear and Jira via Composio CLI
category: skill-generation-tools
resource_url: https://github.com/ComposioHQ/awesome-codex-skills/tree/master/issue-triage
github_url: https://github.com/ComposioHQ/awesome-codex-skills
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# Awesome Codex Skills — Issue Triage

## Overview

Issue Triage is a Codex skill that automates issue triage and bug sweep workflows across Linear and Jira issue trackers using the Composio CLI. The skill enables bulk-fetching, deduplication, relabeling, reassignment, and summary posting for backlog management — all executable from the terminal without UI interaction.

**Key assertion**: "Triage Linear or Jira backlogs and run bug sweeps via the Composio CLI. Bulk-fetch issues, dedupe, relabel, reassign, and post summaries — all from the shell without clicking through the UI." SOURCE: SKILL.md frontmatter description (accessed 2026-05-07).

## Problem Addressed

Triage workflows typically require manual clicking through multiple UI screens to fetch, filter, dedupe, and update issues across large backlogs. This skill addresses three key problems:

1. **Repetitive manual triage** — "Weekly triage: what's unassigned, stale, or missing a priority?"
2. **Post-release bug sweeps** — "cluster all P1/P2 bugs, dedupe, assign owners"
3. **Cross-tool data synchronization** — "Sentry → Linear, PagerDuty → Jira"

SOURCE: SKILL.md lines 14-16 (accessed 2026-05-07).

The skill is designed for teams that need to triage backlogs at scale without manual UI interaction.

## Key Features

### Issue Discovery and Filtering

The skill provides structured queries for both Linear and Jira:

- **Linear**: `LINEAR_LIST_ISSUES` fetches unstarted, unassigned, or stale issues with nested filter syntax
- **Jira**: `JIRA_SEARCH_FOR_ISSUES_USING_JQL` fetches by JQL (Jira Query Language) with configurable field selection

SOURCE: SKILL.md lines 37-48 (accessed 2026-05-07).

### Bulk Mutations

The skill exposes write operations for both platforms:

- **Linear**: `LINEAR_CREATE_ISSUE`, `LINEAR_UPDATE_ISSUE`, `LINEAR_CREATE_COMMENT`
- **Jira**: `JIRA_CREATE_ISSUE`, `JIRA_EDIT_ISSUE`, `JIRA_ADD_COMMENT`, `JIRA_ASSIGN_ISSUE`

SOURCE: SKILL.md lines 37-48 (accessed 2026-05-07).

### Local Deduplication

"Cluster by title similarity and labels. The agent groups likely duplicates locally." This means the skill processes fetched issues in-memory to identify duplicates before any mutations.

SOURCE: SKILL.md line 67 (accessed 2026-05-07).

### Workflow Execution

Issues can be triaged via:
1. **Shell commands** — `composio execute <SLUG> -d '{...filter...}'`
2. **TypeScript workflows** — `composio run --file scripts/triage-linear.ts` (see Usage Examples)
3. **Inline shell scripts** — `composio run '...'` with JavaScript async/await

SOURCE: SKILL.md lines 51-137 (accessed 2026-05-07).

### Cross-Tool Integration

The skill supports syncing issues from external services into Linear/Jira. Example: fetch top 5 unresolved Sentry issues and create Linear tickets for each.

SOURCE: SKILL.md lines 120-137 (accessed 2026-05-07).

## Technical Architecture

### Component Topology

The skill is built on **Composio CLI** as the primary integration layer:

```
┌─────────────────────────────────────────────┐
│        Composio CLI (composio)              │
│                                             │
│  ├─ composio link <tool>                   │
│  ├─ composio search "<action>"             │
│  ├─ composio execute <SLUG> -d '{...}'     │
│  └─ composio run --file <script.ts>         │
└────────┬──────────────────────────┬────────┘
         │                          │
    ┌────▼─────┐          ┌────────▼────┐
    │  Linear   │          │   Jira      │
    │ Issue API │          │ Issue API   │
    └───────────┘          └─────────────┘
```

**Tool API Slugs** (named components):

Linear toolkit:
- `LINEAR_LIST_ISSUES` — fetch issues with nested filter objects
- `LINEAR_CREATE_ISSUE` — create issues
- `LINEAR_UPDATE_ISSUE` — update priority, labels, assignee
- `LINEAR_CREATE_COMMENT` — post comments on issues

Jira toolkit:
- `JIRA_SEARCH_FOR_ISSUES_USING_JQL` — fetch issues via JQL string
- `JIRA_CREATE_ISSUE` — create issues
- `JIRA_EDIT_ISSUE` — update fields including custom fields
- `JIRA_ADD_COMMENT` — post comments
- `JIRA_ASSIGN_ISSUE` — assign issues to users

SOURCE: SKILL.md lines 37-48 (accessed 2026-05-07).

### Data Flow Model

**Triage workflow sequence** (lines 52-80):

```
1. Pull the backlog slice
   ↓
2. Cluster (by title similarity and labels)
   ↓
3. Apply updates in one pass (label, priority, assignee)
   ↓
4. Link duplicates with comments
   ↓
5. Post a digest to Slack
```

SOURCE: SKILL.md lines 51-81 (accessed 2026-05-07).

**Linear filter syntax** (nested objects):
```javascript
{
  filter: {
    state: { type: { eq: "unstarted" } },    // state filter
    assignee: { null: true }                  // assignee filter
  },
  first: 100
}
```

**Jira filter syntax** (JQL string):
```
project = APP AND statusCategory != Done AND assignee is EMPTY ORDER BY updated DESC
```

SOURCE: SKILL.md lines 55-65 (accessed 2026-05-07).

### Extensibility

The skill uses Composio's **pluggable toolkit model**:

- `composio link <tool>` registers credentials for a toolkit (Linear, Jira, Sentry, PagerDuty, Slack)
- `composio search "<action>"` discovers available actions within a toolkit
- `composio tools list <toolkit>` enumerates all available tool slugs for inspection
- `composio execute <SLUG> --get-schema` inspects the exact input/output schema for a tool

This allows new integrations to be wired up without modifying the skill itself.

SOURCE: SKILL.md lines 20-35 (accessed 2026-05-07).

## Installation & Usage

### Prerequisites

```bash
curl -fsSL https://composio.dev/install | bash
composio login
composio link linear        # or: composio link jira
```

SOURCE: SKILL.md lines 20-23 (accessed 2026-05-07).

After linking, credentials are stored locally and reused for subsequent commands.

### Discover Available Tools

```bash
composio search "list issues" --toolkits linear
composio search "search issues" --toolkits jira
composio tools list linear
composio tools list jira
```

This surfaces available action slugs and their expected input schema.

SOURCE: SKILL.md lines 28-32 (accessed 2026-05-07).

### Example 1: Pull Unassigned Linear Issues

```bash
composio execute LINEAR_LIST_ISSUES -d '{
  "filter": { "state": { "type": { "eq": "unstarted" } }, "assignee": { "null": true } },
  "first": 100
}'
```

This returns the first 100 unstarted, unassigned Linear issues. The `filter` field uses Linear's nested filter object syntax.

SOURCE: SKILL.md lines 55-58 (accessed 2026-05-07).

### Example 2: Search and Update Jira Issues

```bash
composio execute JIRA_SEARCH_FOR_ISSUES_USING_JQL -d '{
  "jql": "project = APP AND statusCategory != Done AND assignee is EMPTY ORDER BY updated DESC",
  "maxResults": 100,
  "fields": ["summary","priority","labels","updated","reporter"]
}'
```

This searches Jira using JQL syntax and requests specific fields in the response.

SOURCE: SKILL.md lines 61-65 (accessed 2026-05-07).

### Example 3: TypeScript Workflow (Triage Stale Issues)

Create `scripts/triage-linear.ts`:

```typescript
const { nodes: issues } = await execute("LINEAR_LIST_ISSUES", {
  filter: { state: { type: { eq: "unstarted" } }, assignee: { null: true } },
  first: 100
});

const stale = issues.filter(i => {
  const age = (Date.now() - new Date(i.updatedAt).getTime()) / 86400000;
  return age > 14;
});

for (const i of stale) {
  await execute("LINEAR_CREATE_COMMENT", {
    issueId: i.id,
    body: "Auto-triage: stale for 14+ days. Please assign or close."
  });
}

await execute("SLACK_SEND_MESSAGE", {
  channel: "triage",
  text: `Weekly triage: pinged ${stale.length} stale issues.`
});
```

Run with:
```bash
composio run --file scripts/triage-linear.ts
```

This workflow fetches unstarted issues, filters stale ones (>14 days old), posts comments, and notifies Slack.

SOURCE: SKILL.md lines 94-118 (accessed 2026-05-07).

### Example 4: Cross-Tool Integration (Sentry → Linear)

```bash
composio run '
  const hot = await execute("SENTRY_LIST_A_PROJECTS_ISSUES", {
    organization_slug:"acme", project_slug:"api",
    query:"is:unresolved", sort:"freq", limit:5
  });
  for (const s of hot) {
    await execute("LINEAR_CREATE_ISSUE", {
      teamId: "TEAM_ID",
      title: `[Sentry] ${s.title}`,
      description: `${s.permalink}\nCount: ${s.count}`,
      labelIds: ["label-bug","label-from-sentry"]
    });
  }
'
```

This fetches the top 5 unresolved Sentry issues and creates a Linear issue for each, tagged with "bug" and "from-sentry" labels.

SOURCE: SKILL.md lines 123-137 (accessed 2026-05-07).

### Example 5: Bulk Update (Label and Priority)

```bash
composio execute LINEAR_UPDATE_ISSUE -d '{
  "id":"abc-123","priority":2,"labelIds":["label-bug","label-p1"],"assigneeId":"user-42"
}'

composio execute JIRA_EDIT_ISSUE -d '{
  "issueIdOrKey":"APP-482",
  "fields":{"priority":{"name":"High"},"labels":["bug","p1"]}
}'
```

These commands update a single issue; loops are used to apply bulk updates to multiple issues.

SOURCE: SKILL.md lines 69-77 (accessed 2026-05-07).

## Relevance to Claude Code Development

This skill is relevant to Claude Code development in the following contexts:

1. **AI-Assisted Backlog Triage** — Codex agents can automatically triage issues during development workflows without switching to UI-based tools, keeping the shell-first developer experience intact.

2. **Duplicate Detection** — The skill's "cluster duplicates locally" capability (line 67) can be integrated into Claude Code workflows that process large issue batches, reducing manual review burden.

3. **Cross-Tool Sync** — Developers using multiple tracking systems (Linear for design, Jira for bugs, Sentry for error reporting) can wire them together via Composio without custom API clients.

4. **Release Bug Sweeps** — The post-release triage pattern (Example 4) can be integrated into deployment workflows — "run bug sweep after Vercel deploy" becomes a shell command rather than a manual process.

5. **Extensibility Model** — The skill demonstrates how Composio's toolkit registration system (`composio link`, `composio execute`) can serve as a reusable integration layer for AI agents, avoiding one-off API client code for each service.

SOURCE: SKILL.md lines 14-16, 67, 120-137 (accessed 2026-05-07) + architectural assessment.

## Limitations and Caveats

### Known Constraints (Documented)

1. **Filter Format Differences** — "Unknown field names → `composio execute <SLUG> --get-schema` shows the exact filter shape (Linear uses nested objects; Jira uses JQL strings)."
   - Linear filters use nested JSON objects; Jira uses JQL query strings. These are not interchangeable.

2. **Authentication Refresh** — "`403` on Linear → re-run `composio link linear` with the right workspace."
   - Linear credentials may expire or refer to the wrong workspace; relinking is required.

3. **Rate Limiting** — "Bulk edits rate-limited → insert a 250ms sleep in the `composio run` loop; don't use `--parallel`."
   - Linear/Jira rate limits apply per API; serial execution with delays is required for large bulk operations.

SOURCE: SKILL.md lines 141-144 (accessed 2026-05-07).

### Undocumented Limitations

The following limitations are inferred from the architecture and not explicitly documented:

- **No local batch validation** — Issues are fetched, processed locally, and then updated serially. No transactional rollback if midway mutations fail.
- **Deduplication heuristic not specified** — The skill mentions "cluster by title similarity" but does not specify the similarity threshold or algorithm.
- **Custom field handling unclear** — Jira custom fields must be requested explicitly in the `fields` array, but the mechanism for discovering which fields are available is not detailed.

Confidence in documented limitations: **high** (explicitly stated in SKILL.md). Confidence in undocumented limitations: **medium** (inferred from examples, not verified against Composio source code).

## References

- **Primary source**: [ComposioHQ/awesome-codex-skills/issue-triage/SKILL.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/issue-triage/SKILL.md) (accessed 2026-05-10)
- **Repository root**: [ComposioHQ/awesome-codex-skills](https://github.com/ComposioHQ/awesome-codex-skills) (accessed 2026-05-10)
- **Composio CLI documentation**: [docs.composio.dev/docs/cli](https://docs.composio.dev/docs/cli) (referenced in SKILL.md line 146, not directly verified)
- **Linear API**: Referenced via `LINEAR_*` tool slugs (accessed 2026-05-07)
- **Jira API**: Referenced via `JIRA_*` tool slugs (accessed 2026-05-07)

## Freshness Tracking

| Section | Confidence | Last Updated | Next Review |
|---------|-----------|---|---|
| Overview | high | 2026-05-10 | 2026-08-10 |
| Problem Addressed | high | 2026-05-10 | 2026-08-10 |
| Key Features | high | 2026-05-10 | 2026-08-10 |
| Technical Architecture | high | 2026-05-10 | 2026-08-10 |
| Installation & Usage | high | 2026-05-10 | 2026-08-10 |
| Limitations and Caveats | medium | 2026-05-10 | 2026-08-10 |
| Relevance to Claude Code | medium | 2026-05-10 | 2026-08-10 |

**Confidence assessment rationale**:

- **High**: All claims in Overview, Problem Addressed, Key Features, Technical Architecture, and Installation & Usage are directly extracted from the official SKILL.md file (primary source). Composio CLI tool slugs and examples are verbatim.
- **Medium**: Limitations section relies on three explicitly documented constraints; undocumented limitations are inferred but not verified against Composio source. Relevance section applies architectural findings to Claude Code context — not verified in Claude Code documentation.

**Next review date**: 2026-08-10 (3 months from verification date 2026-05-10). This allows time to detect changes in Composio CLI API, new Linear/Jira endpoints, or updates to the awesome-codex-skills repository.

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Composio Codebase Migrate](./composio-codebase-migrate.md) | skill-generation-tools | sibling Composio-based Codex skill; codebase-migrate handles large-scale refactors, issue-triage handles bulk backlog management |
| [codex-skills](./codex-skills.md) | skill-generation-tools | 19-skill Codex catalog of which issue-triage is an Awesome Codex Skills example |
| [Codebase Recon Skill](./codebase-recon-skill.md) | skill-generation-tools | sibling production-grade Codex skill; both exemplify structured skill implementation with multi-agent compatibility |
| [Agent Skills (Addy Osmani)](./agent-skills.md) | skill-generation-tools | production-grade skills library providing skill authoring patterns and standards that issue-triage exemplifies |
| [jira.js](../developer-tools/jirajs.md) | developer-tools | TypeScript Jira API client; issue-triage skill wraps this API via Composio for bulk triage operations |
| [GitHub CLI (gh)](../developer-tools/github-cli.md) | developer-tools | CLI-based issue/PR management; issue-triage extends to Linear/Jira what gh handles for GitHub |
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | large-scale skill ecosystem and CLI integration patterns; issue-triage demonstrates specialized skill design for issue tracking workflows |
