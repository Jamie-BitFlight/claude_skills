---
name: feedback-sam-task-create-hits-live-github
description: "sam_plan.py's sam-* leaf commands (sam-task-create, sam-tasks, sam-task-status, sam-ready-tasks) call the live GitHub backend on every invocation; monkeypatch operations before reproducing them"
metadata:
  type: feedback
---

`sam_schema/cli.py plan sam-task-create` creates a real GitHub issue and sub-issue link as soon as it is invoked, including under `CliRunner`. It has no dry-run or `--plan-dir` equivalent, and sessions here have `GITHUB_TOKEN` set. `sam-tasks`, `sam-task-status` and `sam-ready-tasks` also hit the live backend.

To reproduce CLI-boundary behaviour (option validation, forwarding), first stub the operation:
`monkeypatch.setattr("sam_schema.sam_plan.operations.create_sam_task", fake_create)`. The pattern is in `tests_sam/test_cli.py::test_sam_task_create_accepts_and_forwards_repo`.
