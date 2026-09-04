# setup-github Command

**Trigger:** <route/> is `setup-github`.

> **Repository**: OWNER/REPO is discovered via `discover_repo()` from `backlog_core.models`. Use MCP tools for all GitHub operations — no `gh` CLI required.

1. Run label taxonomy setup:

   ```text
   MCP: backlog_sync()
   # To verify labels exist: MCP: backlog_list_labels()
   ```

2. Check for existing milestones:

   ```text
   MCP: backlog_list_milestones()
   ```

   If none exist, create the first milestone:

   ```text
   MCP: backlog_create_milestone(
     title="v1.0 — Skills Foundation",
     description="Initial stable milestone for {REPO} skills and plugins",
     due_on="2026-03-31T00:00:00Z"
   )
   ```

3. Check for existing projects:

   ```text
   MCP: backlog_list_projects()
   ```

   If none exist, prompt: "Create GitHub Project '{REPO} Backlog'? (yes/no)"
   If yes:

   ```text
   MCP: backlog_create_project(title="{REPO} Backlog")
   ```

4. Report setup summary:

   ```text
   GitHub setup complete:
   - Labels: N created
   - Milestone: #1 "v1.0 — Skills Foundation"
   - Project: #1 "{REPO} Backlog" (linked to repo)

   Next steps:
   - Add custom fields to the GitHub Project (manual step — not yet available via MCP tools)
   - Import existing backlog: /dh:work-backlog-item <title> for each P0/P1 item
   ```
