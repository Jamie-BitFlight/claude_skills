# Interactive Terminal and PTY Workarounds

Claude Code sessions do NOT have a TTY attached. When a tool requires a TTY (errors like `Inappropriate ioctl for device`, `not a terminal`, `ENOTTY`), **solve the constraint — do not skip the task**.

## Available PTY Providers (in order of preference)

1. **tmux** — best for long-running interactive programs with output capture

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

2. **script** — simplest for commands that run and exit

   ```bash
   # Run command with PTY, capture output
   timeout 15 script -qc "command here" /tmp/output.txt
   ```

3. **Python pty** — for programmatic PTY allocation

   ```python
   import pty, os
   master, slave = pty.openpty()
   # slave fd is a real TTY: os.ttyname(slave)
   ```

## Browser Tools (carbonyl, etc.) — Use DevTools Protocol

Terminal browsers render pixels (▄ blocks), not extractable text. For text extraction:

```bash
# Launch with DevTools Protocol enabled
tmux new-session -d -s browser "npx -y carbonyl --no-sandbox --remote-debugging-port=9222 URL"
sleep 8

# Extract text via CDP
curl -s http://localhost:9222/json  # list tabs
# Use WebSocket to Runtime.evaluate → document.body.innerText
```

The CDP interface (`--remote-debugging-port`) is the primary value — not terminal rendering.

## Decision Flowchart

```text
Tool needs TTY?
├─ YES → Use tmux/script/pty to provide one
│        ├─ Interactive program → tmux (capture-pane for output)
│        ├─ Run-and-exit command → script -qc
│        └─ Programmatic control → Python pty module
└─ NO → Run normally

Output is pixel blocks (▄)?
├─ YES → Use DevTools Protocol / CDP for text extraction
└─ NO → Parse terminal output directly
```

## Prohibited Interactive Commands

`git rebase -i` and `git add -i` require real interactive input — use non-interactive equivalents. For all other TTY-blocked tasks, apply one of the providers above before reporting blocked.
