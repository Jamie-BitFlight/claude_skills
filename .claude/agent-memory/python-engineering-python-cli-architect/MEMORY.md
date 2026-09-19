# Memory Index

- [feedback_cli_output_not_logging.md](./feedback_cli_output_not_logging.md) — typer.echo() output reaches CliRunner's result.output; a logging.StreamHandler created before the test run writes elsewhere
- [feedback_worktree_isolated_bash.md](./feedback_worktree_isolated_bash.md) — worktree sessions: worktree paths only, one plain command per call; the guard refuses any command it cannot prove is not git, including `git -C <sibling worktree>`; plain `git show <sha>` reads a sibling's commit
- [feedback_sam_task_create_hits_live_github.md](./feedback_sam_task_create_hits_live_github.md) — sam-* leaf commands (sam-task-create etc.) hit live GitHub on invocation; monkeypatch sam_schema.sam_plan.operations first
- [project_dh_content_store_live_plan_records_must_parse.md](./project_dh_content_store_live_plan_records_must_parse.md) — every live ContentKind.PLAN record is parsed on ContentTaskProvider load; a non-plan one breaks all content-store plan commands, so live-test with ARTIFACT_CONTENT
- [project_ruff_fix_true_autofix.md](./project_ruff_fix_true_autofix.md) — ruff check writes safe and unsafe fixes here (fix = true, unsafe-fixes = true); use --no-fix for a read-only lint
- [project_subprocess_lifecycle_test_oracle_elapsed_time.md](./project_subprocess_lifecycle_test_oracle_elapsed_time.md) — process-tree-kill tests: assert elapsed time of a capture_output subprocess.run(); a surviving descendant holds the pipe and keeps the call open
- [project_ty_reveal_type_gotchas.md](./project_ty_reveal_type_gotchas.md) — ty: narrow T | list[T] with isinstance(x, T), because isinstance(x, list) leaves Unknown items; stdlib types (getaddrinfo) come from ty's own typeshed, so confirm them with reveal_type
