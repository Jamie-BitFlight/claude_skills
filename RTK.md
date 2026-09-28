# Rust Token Killer (RTK)

RTK filters shell-command output for agent context.

1. Run `command -v rtk`.
2. If it fails, tell the user exactly: `RTK is not installed on this machine. I can install it from https://github.com/rtk-ai/rtk. Shall I proceed? [y/n]` Stop for the answer.
3. If the answer is no, use raw commands. If the answer is yes, install RTK using the official instructions from `https://github.com/rtk-ai/rtk`.
4. Whether RTK was already present or was just installed, validate its resolved path with `command -v rtk`, then run `rtk --version` and `rtk gain`. If any check fails, do not use RTK; report the exact error and use raw commands unless the user directs otherwise.
5. After validation passes, prefix supported shell commands with `rtk`.
