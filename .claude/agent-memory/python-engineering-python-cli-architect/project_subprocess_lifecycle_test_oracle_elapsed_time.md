---
name: project-subprocess-lifecycle-test-oracle-elapsed-time
description: Process-tree-kill regression tests here use elapsed time of a capture_output subprocess.run() as the liveness oracle
metadata:
  type: project
---

In a process-tree-kill regression test, use timing as the liveness oracle:

- Launch the runner with `subprocess.run(..., capture_output=True)`. Every descendant inherits the
  pipe fds, so `communicate()` blocks until the last surviving descendant exits.
- Time that call with `time.monotonic()` and assert it returns within the grace budget
  (e.g. `elapsed < 3`). A leaked descendant shows up as the call lasting its full sleep.

Worked example: `tests/test_run_bounded.py::test_runner_reaps_a_descendant_that_ignores_sigterm`
(also shows the readiness-file rendezvous that removes the SIG_IGN install race).
