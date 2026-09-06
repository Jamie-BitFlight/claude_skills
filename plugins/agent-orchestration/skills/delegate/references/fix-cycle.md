# Fix cycle

Use this to build a bug-fix dispatch prompt: never just "fix X" — carry a reproduction the agent
runs before and after the change.

## What to put in the prompt

- **Root cause** — one sentence naming what is actually wrong, not the symptom reported. Unknown
  → dispatch a `read`/`verify` phase first, not a `write` phase.
- **Reproduction** — the exact command or test that demonstrates the bug, plus its current
  failing output. The agent confirms this fails before touching any code.
- **Fix scope** — only what the root cause names. No adjacent cleanup in the same dispatch.
- **Re-validation** — the same reproduction command, expected to pass after the fix.
- **Regression check** — the project's existing test/lint gate, run after the fix.

## Cycle

1. State the root cause.
2. Write the reproduction; run it; confirm it fails.
3. Make the fix.
4. Re-run the same reproduction; confirm it now passes.
5. Run the project's regression gate; confirm nothing else broke.

If the reproduction won't fail, or still fails after two attempts, report `BLOCKED` with
the command and its output rather than guessing further.
