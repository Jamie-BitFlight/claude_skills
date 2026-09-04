# GitHub CLI Conventions

- The canonical `<owner/repo>` for this checkout is written to `.dh/config.yaml` under `gh.repo`
  (set by `setup_gh.py`). Pass `-R <owner/repo>` on every `gh` command rather than relying on
  remote auto-detection — checkout remotes vary and proxied setups break auto-detection.
  `GITHUB_TOKEN` set in environment handles authentication automatically.
- Prefer extending this repo's existing GitHub tooling — backlog MCP tools
  (`mcp__plugin_dh_backlog__*`) and PyGithub-based scripts — over adding new `gh` CLI usage; the
  project has invested in portable Python tooling that needs no separate `gh` auth/installation.
- When `gh` is the right tool, prefer `gh graphql` (single call) over `gh api` (slower, often
  multi-step) for new usage — the PR Review Protocol is an existing exception that already depends
  on `gh api`.
- To read a GitHub-hosted file's contents, use
  `gh api repos/{owner}/{repo}/contents/{path}?ref={branch} --jq '.content' | base64 -d` rather
  than a URL-fetch tool — it authenticates automatically and returns exact file bytes.
