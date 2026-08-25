The purpose and explicit goals of the skill gh:

1. Guarantee a working, authenticated gh CLI is available in any agent environment, auto-installing it (with SHA256-verified binary download) when absent rather than failing on "command not found."
2. Prevent the repo-specific "failed to determine base repo" failure by establishing the -R <owner/repo> flag as mandatory on every gh invocation whenever the git remote is a local proxy instead of github.com.
3. Give the agent a correct, verified command library for the full GitHub project-management surface — issues, labels, milestones, and Projects V2 — choosing the right tool per context: one-off gh CLI, scripted PyGithub, authenticated gh subprocesses for Projects V2 GraphQL, or @octokit in JavaScript hooks.
4. Keep backlog items and GitHub issues in sync via documented field mappings (priority→label, status→label, item→issue number written back to .claude/backlog/), so issue state accurately reflects backlog state.
5. Provide one bulk-automation entry point (github_project_setup.py) for repeatable setup tasks — label taxonomy creation, milestone CRUD, issue creation/listing — instead of ad hoc one-off commands.
