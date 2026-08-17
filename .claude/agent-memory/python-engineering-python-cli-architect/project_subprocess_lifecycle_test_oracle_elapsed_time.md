---
name: project-subprocess-lifecycle-test-oracle-elapsed-time
description: os.kill/ps against a doubly-orphaned descendant is unreliable in this sandboxed shell — use elapsed wall-clock time of a capture_output=True subprocess.run() call as the liveness oracle for subprocess-group-kill regression tests instead
metadata:
  type: project
---

Writing a regression test for a process-group-kill bug (a descendant that survives SIGTERM and
should be reaped by a later SIGKILL escalation) is not safely testable via `os.kill(pid, 0)` or
`ps -p <pid>` from the outer test process in this sandboxed shell environment. Both consistently
reported a demonstrably-still-running descendant (confirmed via the descendant's own log file,
written from inside its own process, continuing well past the check) as already dead — a false
negative, not a sandbox permission error (no `PermissionError`/`EPERM` was raised; `ESRCH` came
back for a live PID). Verified via instrumented repro scripts (a signal-logging descendant whose
own log outlived the "dead" verdict) before trusting this, not assumed from a single failure.

**The reliable oracle:** if the target process under test was launched by a runner invoked via
`subprocess.run([..., RUNNER, ...], capture_output=True, ...)` — as `run_bounded.py`'s own
`tests/test_run_bounded.py::run_runner()` helper does — every descendant in that process tree
inherits the runner's stdout/stderr pipe file descriptors (since none of the layers in the chain
redirect stdout/stderr for their own children). `capture_output=True`'s `communicate()` blocks
until **every** holder of those pipe fds closes them, not just the immediate child. So an
un-reaped, still-alive descendant keeps `run_runner()` itself blocked until that descendant exits
naturally — observable purely as **the outer `subprocess.run()` call taking far longer to return
than expected**, with no `os.kill`/`ps` involved at all.

Empirically, for a bug where a descendant that ignores SIGTERM should be SIGKILL-escalated within
`TERMINATION_GRACE_SECONDS` (~0.5s) but instead survives until its own `time.sleep(N)` naturally
elapses: the pre-fix code consistently produced `elapsed ≈ N` seconds (blocked on the pipe);
the fixed code consistently produced `elapsed ≈ 1s` (grace period + reap). This matches the
existing style already used elsewhere in `tests/test_run_bounded.py`
(`test_runner_times_out_and_returns_the_timeout_status`, `assert elapsed < 3`) — no new tooling
needed, just apply the same pattern to the specific behavior under test.

**How to apply:** When writing a regression test in this repo for "does the runner actually kill
every process in a group/tree," do NOT reach for `os.kill(descendant_pid, 0)` or `ps -p
<descendant_pid>` polling loops from the test process — they are not trustworthy here even though
they work in a plain terminal. Instead:

1. Time the full behavioral call (`run_runner(...)` or equivalent `subprocess.run(...,
   capture_output=True)` invocation) with `time.monotonic()`.
2. Assert the elapsed time stays within the expected grace-period budget (e.g. `< 3`), not that a
   process ID becomes unreachable.
3. If the scenario needs a signal-handler race eliminated (e.g. "descendant must have already
   installed `SIG_IGN` before the runner's short timeout fires"), add a readiness-file rendezvous:
   the descendant writes a marker file only after installing its handler, and its parent polls for
   that marker before its own long sleep — this removes flakiness unrelated to the actual fix
   being tested.
4. Falsify: run the exact same test against the pre-fix implementation and confirm it fails
   (or, better, takes the full unbounded duration) before trusting the assertion measures the
   right thing.

See `scripts/run_bounded.py` and `tests/test_run_bounded.py::test_runner_reaps_a_descendant_that_ignores_sigterm`
for the worked example this was derived from.
