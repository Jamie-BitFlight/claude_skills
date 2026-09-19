# Memory Index

- [feedback_cli_output_not_logging.md](./feedback_cli_output_not_logging.md) — CLI result output goes through typer.echo()/print()/JSON; logging only for --verbose debug traces
- [feedback_worktree_isolated_bash.md](./feedback_worktree_isolated_bash.md) — worktree sessions: worktree paths only, one plain command per call; guard checks only git, so non-git mutators after cd pollute the shared checkout
- [feedback_sam_task_create_hits_live_github.md](./feedback_sam_task_create_hits_live_github.md) — sam-* leaf commands (sam-task-create etc.) hit live GitHub on invocation; monkeypatch sam_schema.sam_plan.operations first
- [project_dh_content_store_live_plan_records_must_parse.md](./project_dh_content_store_live_plan_records_must_parse.md) — every live ContentKind.PLAN record is parsed on ContentTaskProvider load; a non-plan one breaks all content-store plan commands, so live-test with ARTIFACT_CONTENT
- [project_pr_merged_underneath_push_race.md](./project_pr_merged_underneath_push_race.md) — after pushing, check gh pr view --json state,mergedAt before trusting gh pr checks; if merged, cherry-pick unmerged commits onto a fresh main-based PR
- [project_ruff_fix_true_autofix.md](./project_ruff_fix_true_autofix.md) — ruff check rewrites files here (fix = true); use --no-fix for a read-only lint
- [project_subprocess_lifecycle_test_oracle_elapsed_time.md](./project_subprocess_lifecycle_test_oracle_elapsed_time.md) — process-tree-kill tests: assert elapsed time of a capture_output subprocess.run(); os.kill/ps give false ESRCH in this sandbox
- [project_ty_reveal_type_gotchas.md](./project_ty_reveal_type_gotchas.md) — ty: narrow T | list[T] on isinstance(x, T) not list; stdlib types (getaddrinfo) come from ty's typeshed, not the vendored cache — confirm with reveal_type
