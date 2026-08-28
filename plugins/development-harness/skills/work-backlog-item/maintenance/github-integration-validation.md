# GitHub integration validation

Manual verification steps for the GitHub-sync behavior (`setup-github`, issue creation, milestone
assignment, in-progress labeling, closure) — run these after changing that code path, not as part
of normal skill execution. `OWNER/REPO` is discovered via `discover_repo()` from
`backlog_core.models`; verification uses MCP tools only, no `gh` CLI required.

- **Labels**: after `/work-backlog-item setup-github`, `backlog_list_labels()` should show 13
  taxonomy labels (`priority:*`, `type:*`, `status:*`).
- **Issue creation**: after working a P1 item, `backlog_list_issues(state="open")` should show an
  issue with `priority:p1`, `type:*`, `status:in-progress`; `backlog_view(selector="{title}")`
  should show an `issue` field with `"#N"`.
- **Milestone assignment**: `backlog_list_milestones()` should show `open_issues` incremented
  after an item in that milestone is worked.
- **In-progress label**: `backlog_view(selector="#<issue-number>")` should show
  `status:in-progress` present and `status:needs-grooming` absent.
- **Closure**: after `/work-backlog-item close <title>`, `backlog_view(selector="#<issue-number>")`
  should show `state="closed"` and a comment containing the checklist summary.
- **Consistency**: `backlog_view(selector="{title}", summary=false)` should show `issue`, `plan`,
  and `status` fields consistent with GitHub.

Full sequence: `setup-github` → work a new item → implement the fix → `close` the item — confirming
each of the checks above at the matching step.
