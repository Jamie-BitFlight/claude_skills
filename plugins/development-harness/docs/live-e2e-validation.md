# Live GitHub validation

The live lane exercises the in-process MCP transport, real backlog operations, and a real
GitHub backend. It does not validate an installed plugin, agent behavior, or background server
startup. It must never target the source repository or the production backlog.

## Sandbox configuration

Use a dedicated, disposable repository containing no real work. Give it an initialized default
branch, enable Issues, and create `.dh-e2e-sandbox` on its default branch with exactly this text
and a final newline:

```text
development-harness live-test sandbox
```

Configure the source repository's Actions variable `DH_E2E_REPOSITORY` as `owner/repository` and
secret `DH_E2E_TOKEN` as a credential scoped to that sandbox, with Issues and Contents read/write.
An installation token or fine-grained token restricted to the sandbox is preferable to a broad
personal credential. The automatic source-repository `GITHUB_TOKEN` cannot provide cross-repository
access; increasing its permissions would not fix the target mismatch.

The sandbox marker is an explicit opt-in, not an access-control replacement. Production and source
identities are rejected even when a marker exists. Preflight checks the configured and canonical
repository identities and the marker before any mutation. It cannot prove every fine-grained write
permission from a read: the actual lifecycle and independent readbacks test those capabilities.

CI supplies `DH_E2E_RUN_ID` from the workflow run ID and attempt, sets `GITHUB_REPO` from the same
sandbox variable, and serializes live jobs using that target. Only preflight, test, and cleanup steps
receive the sandbox secret. Missing or inconsistent configuration fails preflight; it never falls
back to production or reports an all-skipped live pass. E2E remains advisory outside Quality Gate.

## Run and diagnose

After exporting `DH_E2E_REPOSITORY`, a unique `DH_E2E_RUN_ID`, `DH_ALLOW_TEST_NETWORK=1`, and the
sandbox credential as `GITHUB_TOKEN`, validate the scope before executing tests:

```bash
uv run --locked python plugins/development-harness/scripts/close_test_issues.py --check-only
uv run --locked python scripts/run_bounded.py --timeout-seconds 480 -- \
  uv run --locked pytest -m e2e -n 0 -x -v --tb=long --capture=tee-sys \
    -o faulthandler_timeout=60 plugins/development-harness/tests/test_live_validation.py
uv run --locked python plugins/development-harness/scripts/close_test_issues.py
```

Run cleanup even if the test command fails. Use the same run ID for cleanup, but a new ID for a new
independent run. `GITHUB_REPOSITORY`, when set, identifies the source repository and is protected.
Legacy `REPO`, `GITHUB_REPO`, and `--repo` values must agree with the sandbox. Do not run concurrent
local invocations against the same sandbox. The lane requires `-n 0` because one real MCP server
and its configured backend are shared within a scenario; neither scenario depends on the other.

`DH_E2E_REPORT_DIR` optionally selects an evidence directory. CI uploads preflight, pytest and
cleanup logs, flushed phase/response journals, and JUnit when pytest completes. No credential or
entire environment dump is written. Journals contain full sandbox responses, so keep real work out
of the sandbox. A missing JUnit file after forced termination is not a passing test result; use the
journal's last started phase and the thread dump.

Client request/initialization timeouts remain distinct from the whole-process deadline. The
existing `scripts/run_bounded.py` kills the isolated process tree before the outer CI step timeout,
including blocked executor threads and descendants. The deadline is a CI execution budget, not a
new product latency guarantee. `-x` stops after a reported failure; immediate journals retain its
context even if client teardown subsequently blocks. No retries hide failures.

Cleanup revalidates the sandbox, requires both the exact run-title prefix and body marker, excludes
pull requests, rechecks ownership before closing, and reads back the resulting state. A denied
close, transport failure, changed ownership, or unchanged open state is nonzero. It stops at the
first unsafe/failed operation rather than claiming the remaining work completed. Repeating cleanup
for that run is idempotent. CI does not suppress its failure.

Cleanup closes issues; it does not delete issue history or the backend's audit comments/content
records. Interrupted requests can leave resources whose ownership cannot be established from a
valid response or both markers; inspect the retained evidence rather than broadening the sweeper.
Rotate the disposable sandbox when its history is no longer a controlled test dataset. Do not
mistake cold-cache recovery over a growing history for the warm lifecycle's cost.

## Test design and preserved obligations

The revision was planned using PR #3904's `test-designer`, `test-reviewer`, and shared testing
principles at commit `ce56380924a39354f4f5136cc1f48329a5879311`. Those skills are methodology,
not runtime dependencies of this lane. The design replaces declaration-order coupling and
strengthens observations without changing production cache completeness, reconciliation, or
provider contracts.

| Original claim | Surviving observation and independent oracle | Disposition |
| --- | --- | --- |
| L1 creates a native issue | Native GitHub read confirms identity, submitted description and run ownership; returned title must contain the supplied title | STRENGTHEN |
| L2 listing includes created work | Page size one and explicit continuation; independently recorded issue references must appear across the collection | STRENGTHEN |
| L3 numeric view resolves the item | MCP view by native reference with live provenance and expected stored identity | KEEP |
| L4 associates a plan | Separate writer-backend view confirms the association, not only the update echo; this does not execute the plan or claim cross-cache plan recovery | STRENGTHEN |
| L5 changes status | Native GitHub labels independently confirm in-progress state | STRENGTHEN |
| L6/L7 full and incremental grooming | Native audit comments and a fresh-cache MCP reader retain both known content values; raw issue bodies remain human-owned | STRENGTHEN |
| L8 sync publishes changes | Independent content observations follow explicit sync, rather than accepting integer counters alone | STRENGTHEN |
| L9 pull refreshes cached work | An independent native title/body edit followed by targeted pull and a non-refresh title lookup; a numeric lookup would mask a no-op pull | REPLACE |
| L10/L11 close and resolve | Each API transition is followed by native closed-state verification on a separately created issue | STRENGTHEN |
| Implicit cold bootstrap | A separate empty-cache scenario triggers default listing; the public backend cache must recover a known closed issue as well as the listed open issue | REPLACE |

The cold scenario checks recovery at the backend-cache boundary, independently of the MCP
listing's presentation filters. Its source dataset includes a natively closed fixture, so an
open-only recovery cannot satisfy the assertion. Warm CRUD explicitly establishes a real open-item
snapshot in setup; it does not fabricate a checkpoint or disable cold-read behavior in production.

Pure helper tests challenge unsafe target selection, lookalike ownership, no-op cleanup, stale
ownership, first-page-only membership, nonadvancing pages, withheld/error responses, and failure
journaling. Native preflight tests use a controlled provider seam to prove rejection before
mutation. Existing `tests/test_run_bounded.py` carries real sleeping/stubborn-descendant controls;
this lane reuses that runner instead of adding another process-termination implementation.

Static review, pure tests, and a green PR gate do not establish live-provider effectiveness. The
original timed-out run lost the exact L2/L3 exceptions; these changes do not invent their causes.
Record the tested revision, actual live outcomes, cleanup outcome, and artifact links before
claiming the live defects resolved. Source-author review is not independent review.

## Pattern references

- [GitHub token permissions and alternatives](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [pytest failure handling and thread dumps](https://docs.pytest.org/en/stable/how-to/failures.html)
- [GitHub artifact upload](https://github.com/actions/upload-artifact)
