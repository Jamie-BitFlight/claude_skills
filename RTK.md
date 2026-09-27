# Rust Token Killer (RTK)

RTK filters shell-command output for agent context. It is optional project tooling, not a requirement for repository work.

## Availability

Before the first RTK-wrapped command in a task, run `command -v rtk && rtk --version`.

If that check does not succeed, tell the user exactly: `RTK is not installed on this machine. I can install it from https://github.com/rtk-ai/rtk. Shall I proceed? [y/n]` Stop for the answer; do not install RTK automatically.

If the answer is no, run the original commands without an `rtk` prefix and state that RTK filtering was unavailable. Do not report token savings or command rewriting in that state. If the answer is yes, follow the official RTK installation instructions and verify the correct Rust Token Killer binary with `command -v rtk && rtk --version` before using it.

## When RTK is available

Prefix shell commands with `rtk`, for example `rtk git status`, `rtk pytest -q`, and `rtk uv run pytest`. Keep the prefix on each command in a shell chain.

Use `rtk proxy <command>` only when filtered output is unusable. Use `rtk gain` or `rtk gain --history` only after RTK commands have run.

The upstream project-scoped Codex integration is installed separately with `rtk init --codex`; it can add a Codex hook and replace this file with RTK-managed awareness content. Do not run that installer from a repository task unless the user explicitly authorizes RTK installation and hook registration.
