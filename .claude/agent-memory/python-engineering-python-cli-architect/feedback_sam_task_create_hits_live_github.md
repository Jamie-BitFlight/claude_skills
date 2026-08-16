---
name: feedback-sam-task-create-hits-live-github
description: sam_schema/sam_plan.py's sam-task-create CLI command calls the live GitHub API immediately when GITHUB_TOKEN is set — a bare reproduction invocation creates a real issue
metadata:
  type: feedback
---

`sam_schema/cli.py plan sam-task-create` (`sam_plan.sam_task_create` →
`dh_core.operations.create_sam_task` → `backlog_core.operations.create_sam_task`) is not a
pure/local command — it calls the
GitHub REST/GraphQL API to create a real issue and link it as a sub-issue as soon as it's
invoked, with no dry-run or local-backend flag. This repo's sessions have `GITHUB_TOKEN`
set in the environment by convention (see AGENTS.md "GitHub CLI Conventions"), so a
throwaway `CliRunner.invoke(app, ["plan", "sam-task-create", ...])` reproduction script —
run only to check a CLI-boundary validation error (e.g. whether `--skill` is still
required) — actually created issue #2798 in `Jamie-BitFlight/claude_skills` during a PR
review-fix session (2026-08-06). Had to `gh issue close` it with an explanation comment.

**Why:** Unlike `plan create`/`plan update`/`plan append-task` (all pure local-YAML
mutations against a `--plan-dir`), the four `sam-*` leaf commands
(`sam-task-create`, `sam-tasks`, `sam-task-status`, `sam-ready-tasks`) always hit the live
network backend — there is no local plan-dir equivalent for them in `sam_plan.py`.

**How to apply:** Before invoking `sam-task-create` (or any `sam-*` leaf) directly via
`CliRunner`/subprocess for reproduction or verification, either (a) `monkeypatch` the
underlying `sam_schema.sam_plan.operations.create_sam_task` (see
`tests_sam/test_cli.py::test_sam_task_create_accepts_and_forwards_repo` for the pattern —
`monkeypatch.setattr("sam_schema.sam_plan.operations.create_sam_task", fake_create)`), or
(b) accept that a real GitHub issue will be created and be ready to `gh issue close` it
immediately after. Never assume a CLI reproduction script is side-effect-free just because
it looks like an input-validation check.
