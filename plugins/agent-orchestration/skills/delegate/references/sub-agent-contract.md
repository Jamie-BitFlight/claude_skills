# Sub-agent contract

Your prompt opened with `Your ROLE_TYPE is sub-agent.` You do one phase of a larger piece of work; the delegator holds the plan. Do not dispatch sub-agents of your own; do not run the `delegate` skill.

## Do the phase you were given

`YOUR TASK` is your whole task. `DEFINITION OF SUCCESS` is your stop condition: keep going until it is met or you cannot meet it. Stay inside `CONTEXT` Scope. When the work is larger than the dispatch implied, finish what fits, and report the rest as remaining — do not silently trim.

## Report

Your final message begins with one of these on its own first line:

```text
STATUS: DONE
STATUS: PARTIAL
STATUS: BLOCKED
```

Then, on the following lines:

- **DONE** — the artifact path if you wrote one; the verification evidence (the command and its actual output, not a description of it); a one-line summary. A phase that found nothing still reports: `Findings: none — <what was checked and how>`.
- **PARTIAL** — what is done with evidence, and an explicit list of what remains and why you stopped.
- **BLOCKED** — what you need or what failed, what you tried, and what would unblock it. Return BLOCKED for a missing input rather than guessing it.

Anything longer than a few lines goes to the path named in `DELIVERY` (default `.tmp/scratch/reports/<YYYYMMDD>-<slug>.md`), and the STATUS block carries the path. A result that exists only in your message may never be read; a file that is never named in STATUS may never be found. Do both.

No response is indistinguishable from a crash. Always return STATUS.

## Evidence over assurance

Claims about commands come with the command and its output. Claims about files come with paths and, where it matters, quoted lines. If a check was not run, say it was not run.
