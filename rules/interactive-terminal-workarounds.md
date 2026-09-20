# Interactive Terminal and PTY Workarounds

Claude Code sessions do NOT have a TTY attached. When a tool requires a TTY (errors like `Inappropriate ioctl for device`, `not a terminal`, `ENOTTY`), **solve the constraint — do not skip the task**.

## Available PTY Provider

**tmux** — best for long-running interactive programs with output capture

```bash
# Launch program with PTY
tmux new-session -d -s mysession -x 160 -y 50 "command here"
# Wait for output
sleep 5
# Capture rendered text
tmux capture-pane -t mysession -p > /tmp/output.txt
# Capture with ANSI escape sequences
tmux capture-pane -t mysession -p -e > /tmp/output-ansi.txt
# Clean up
tmux kill-session -t mysession
```

## Prohibited Interactive Commands

`git rebase -i` and `git add -i` require real interactive input — use non-interactive equivalents. For all other TTY-blocked tasks, apply the provider above before reporting blocked.
