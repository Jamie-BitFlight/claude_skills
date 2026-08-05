# Memory Index

- [project_auto_sync_manifests.md](./project_auto_sync_manifests.md) — auto_sync_manifests.py base-ref refactor patterns and seam contracts
- [project_ty_socket_getaddrinfo_typing.md](./project_ty_socket_getaddrinfo_typing.md) — ty's real socket.getaddrinfo return type is Literal-keyed, not the flat typeshed-cache shape; verify with reveal_type
- [feedback_cli_output_not_logging.md](./feedback_cli_output_not_logging.md) — primary CLI output goes through typer.echo()/print(), never logging; logging is for debug/forensic traces only
- [project_typer_echo_dynamic_stream.md](./project_typer_echo_dynamic_stream.md) — typer.echo()/rich Console resolve sys.stdout dynamically per call (CliRunner-safe); a bound logging.StreamHandler does not
- [project_dh_scripts_agent_only_json.md](./project_dh_scripts_agent_only_json.md) — dh scripts/ family is agent-only: structured output is compact JSON via shared cli_output.py err()/output_json(), no tables/panels/logging
- [project_ruff_fix_true_autofix.md](./project_ruff_fix_true_autofix.md) — this repo's ruff has fix=true; plain `ruff check` auto-modifies files, re-Read before next Edit
- [project_ty_isinstance_narrowing_nonfinal_class.md](./project_ty_isinstance_narrowing_nonfinal_class.md) — ty isinstance-narrowing on `list` vs a non-final 3rd-party class widens to object; narrow on the other union member's class instead
- [feedback_worktree_isolated_cwd_must_not_cd.md](./feedback_worktree_isolated_cwd_must_not_cd.md) — worktree-isolated sessions: never `cd` to the shared checkout — only git ops are guarded, non-git mutating commands (uv add/remove) silently pollute it
