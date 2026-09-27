# Rust Token Killer (RTK)

RTK filters shell-command output for agent context. It is optional project tooling, not a requirement for repository work.

## Availability

Before the first RTK-wrapped command in a task, run `command -v rtk`.

If `command -v rtk` fails, tell the user exactly: `RTK is not installed on this machine. I can install it from https://github.com/rtk-ai/rtk. Shall I proceed? [y/n]` Stop for the answer; do not install RTK automatically.

If `command -v rtk` succeeds, validate the resolved binary with `rtk --version` and `rtk gain`. If `command -v rtk` succeeds but `rtk --version` or `rtk gain` fails, do not use RTK or claim it is absent; report the exact validation failure and continue with raw commands unless the user directs otherwise.

If the answer is no, run the original commands without an `rtk` prefix and state that RTK filtering was unavailable. Do not report token savings or command rewriting in that state. If the answer is yes, install RTK using the official instructions, then validate the correct Rust Token Killer binary with `command -v rtk` (the resolved executable path), `rtk --version`, and `rtk gain`. Immediately prefix supported shell commands with `rtk` after those checks pass. If installation or any validation fails, do not use RTK; report the exact failure and continue with raw commands unless the user directs otherwise.

## When RTK is available

Prefix shell commands with `rtk`, for example `rtk git status`, `rtk pytest -q`, and `rtk uv run pytest`. Keep the prefix on each command in a shell chain.

Use `rtk proxy <command>` only when filtered output is unusable. Use `rtk gain` or `rtk gain --history` only after RTK commands have run.

The upstream project-scoped Codex integration is installed separately with `rtk init --codex`; it can add a Codex hook and replace this file with RTK-managed awareness content. Do not run that installer from a repository task unless the user explicitly authorizes RTK installation and hook registration.
