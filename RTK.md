# Rust Token Killer (RTK)

RTK filters shell-command output for agent context.

1. Assume RTK is installed and invoke it directly for supported shell commands, without existence, resolved-path, or version preflight checks.
2. If RTK errors or is missing, continue the requested task with raw commands. Missing RTK must not block task completion.
3. After the requested task is complete, if RTK is missing, ask: `RTK is not installed on this machine. I can install it from https://github.com/rtk-ai/rtk. Shall I proceed? [y/n]` Install only after approval, using the official instructions at <https://github.com/rtk-ai/rtk>. If authorization is declined, continue using raw commands.
