# Utilization Proposals: Awesome Codex Skills — Issue Triage

**Research entry**: ./research/skill-generation-tools/awesome-codex-skills-issue-triage.md
**Generated**: 2026-05-10
**Integration surfaces found**: 3 (CLI | SDK | Cross-tool integrations)
**Proposals written**: 1
**Skipped**: 2 — incomplete coverage, incompatible scope

---

## Utilization 1: complete-milestone skill → Composio Issue Triage

**Research entry**: ./research/skill-generation-tools/awesome-codex-skills-issue-triage.md
**Caller**: ./.claude/skills/complete-milestone/SKILL.md
**Integration mechanism**: CLI subprocess (`composio execute` for bulk fetching and bulk updates)
**Replaces or adds**: Replaces manual filtering and reassignment of open issues; adds deduplication capability for bulk bug sweeps
**Setup cost**: Medium (Composio CLI install, Linear/Jira workspace linking via `composio link`)
**Integration surface**: `composio execute LINEAR_LIST_ISSUES`, `composio execute LINEAR_UPDATE_ISSUE`, `composio execute JIRA_SEARCH_FOR_ISSUES_USING_JQL`

### Why this caller

The `complete-milestone` skill currently implements Steps 1–3 of issue lifecycle management: auditing open vs. closed issue counts, displaying state, and offering to reassign issues to new/existing milestones. Today this is done via GitHub REST API calls in `backlog_list_issues()` and `backlog_create_milestone()` (lines 26–34 of SKILL.md).

When a milestone has dozens of open issues, the current workflow requires serial reassignment (`backlog_list_issues()` fetches the set, then loops over each issue to reassign one at a time via a Python script). The Composio toolkit provides two capabilities the skill lacks:

1. **Deduplication** — When open issues span multiple sprints, duplicates (same bug reported twice with different titles) are common. Composio's `LOCAL_DEDUP` clustering by title similarity and labels can identify and link duplicates before mutation (SKILL.md line 67), reducing manual review burden.

2. **Bulk mutation** — `LINEAR_UPDATE_ISSUE` and `JIRA_EDIT_ISSUE` are exposed as callable actions that can be chained in a loop from `composio run` scripts or direct `composio execute` calls, avoiding the subprocess overhead of the current serial reassignment pattern.

### Integration sketch

**Before (current approach):**

```python
# ./.claude/skills/complete-milestone/SKILL.md Step 3, Option B
open_issues = backlog_list_issues(milestone=title, state="open")
for issue in open_issues:
    # One subprocess per issue
    subprocess.run([
        "uv", "run",
        ".claude/skills/gh/scripts/github_project_setup.py",
        "issue", "set-milestone",
        "--issue", str(issue.number),
        "--milestone", chosen_milestone_number
    ])
```

**After (proposed Composio integration):**

```bash
# Fetch and cluster duplicates in a single Composio call
composio execute LINEAR_LIST_ISSUES -d '{
  "filter": {"milestone": "<milestone_id>", "state": {"type": {"eq": "unstarted"}}},
  "first": 100
}'

# Pipe to a Composio TypeScript workflow that dedupes and bulk-reassigns
composio run --file ./complete-milestone-bulk-triage.ts
```

Where `complete-milestone-bulk-triage.ts` would be:

```typescript
const { nodes: issues } = await execute("LINEAR_LIST_ISSUES", {
  filter: { milestone: "<milestone_id>" },
  first: 100
});

// Cluster duplicates locally (Composio provides this mechanism)
const clusters = clusterByTitle(issues);  // title similarity + labels

// Bulk-update: reassign to new milestone
for (const cluster of clusters) {
  const primary = cluster[0];  // keep first

  // Update primary issue
  await execute("LINEAR_UPDATE_ISSUE", {
    id: primary.id,
    milestoneId: "<new_milestone_id>"
  });

  // Link duplicates with comments
  for (const dup of cluster.slice(1)) {
    await execute("LINEAR_CREATE_COMMENT", {
      issueId: dup.id,
      body: `Duplicate of #${primary.number}. Closing as duplicate.`
    });
    await execute("LINEAR_UPDATE_ISSUE", {
      id: dup.id,
      state: { type: "canceled" }
    });
  }
}
```

**Grounding in research entry**: Tool slugs `LINEAR_LIST_ISSUES`, `LINEAR_UPDATE_ISSUE`, `LINEAR_CREATE_COMMENT` are documented in SKILL.md lines 37–48. The deduplication pattern is explicitly documented in lines 52–67: "Cluster by title similarity and labels. The agent groups likely duplicates locally." The TypeScript workflow pattern is demonstrated in Example 3 (lines 215–250).

**Caveats and constraints**:

- Requires `composio link linear` to be run once to store credentials (SKILL.md line 168)
- Linear filter syntax uses nested JSON objects (SKILL.md lines 131–138); requires careful schema mapping from GitHub issue metadata
- Rate limiting applies (SKILL.md line 318: "Bulk edits rate-limited → insert a 250ms sleep")
- **GitHub-only limitation**: The `complete-milestone` skill currently uses GitHub API via MCP backlog server. Integrating Composio's Linear/Jira toolkit would require adding conditional logic to detect workspace type (Linear vs. Jira) and route accordingly. This is feasible but adds complexity.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `./.claude/skills/daily-releases/SKILL.md` | Incompatible scope — daily-releases analyzes commits and generates release notes, not issue triage. No overlap with Composio issue management surfaces. Issue references are incidental to the changelog pipeline, not a primary concern. |
| `./.claude/agents/doc-drift-auditor.md` | No utilization surface — doc-drift-auditor audits documentation against code via git forensics and static analysis. Composio provides issue management APIs, not code analysis or git tools. No cross-use case. |

---

## Summary

**Integration Feasibility**: **MEDIUM**

The Composio CLI triage toolkit is a strong structural fit for the `complete-milestone` skill's bulk issue mutation use case. The deduplication capability (clustering by title similarity) is a direct answer to the pain point of manual duplicate review during large milestone closures.

**Integration Effort**: **MEDIUM**

- Add Composio CLI dependency to project environment
- Create conditional routing logic to detect workspace type (Linear vs. Jira vs. GitHub)
- Write wrapper scripts that translate GitHub API issue filters to Composio tool input schemas
- Add error handling for rate limits and authentication refresh

**Next Steps (if pursued)**:

1. Verify Composio CLI installation and Linear/Jira authentication works in Claude Code environment
2. Prototype a single triage workflow (fetch + dedupe + bulk-reassign) against test Linear workspace
3. Compare performance (serial GitHub API calls vs. bulk Composio `execute` calls) to confirm speed improvement
4. Add to backlog if performance validation confirms benefit
