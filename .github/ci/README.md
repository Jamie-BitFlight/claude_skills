# Change-aware Code quality

`plan.py` maps a pull request's immutable merge-base/head diff to work. `run.py`
executes that plan with argument arrays. Both bootstrap from standard-library-only
PEP 723 environments; selection does not install the repository's test dependencies.
The workflow is [Code quality](../workflows/code-quality.yml).

## Selection contract

| Changed input | Fast pytest selection | Other checks |
| --- | --- | --- |
| `plugins/<name>/...`, including its source and any `conftest.py` | That plugin's `run_pytests.py` and the global shard | Affected plugin validation, manifest checks, applicable file linters |
| Root documentation, `docs/`, `rules/` documentation | Global shard | Applicable file linters |
| `research/` documentation | Global shard | Research integration and advisory whole-vault validation |
| Development-harness content | Its `run_pytests.py` and the global shard | Its integration and memory/SQLite backend lanes |
| Root/shared code, CI, dependencies, tool configuration, or unclassified inputs | All configured shards | Full checks |
| Main push, manual dispatch, or unavailable PR comparison history | All configured shards | Full checks |

CI decides which plugin needs testing; the plugin decides how it is tested.
[`pyproject.toml`](../../pyproject.toml)'s `tool.pytest.ini_options.testpaths`
lists only repository-owned tests (root tests, example tests and repository-local
skill tests), which form the `global` shard. Each `plugins/<name>/run_pytests.py`
is one plugin shard: the planner discovers the runner and passes it no marker, so
the runner's own default selects the fast lane, and the runner owns that plugin's
test roots and dependencies. `run.py` runs it as `uv run --locked --script`, so
the runner's committed `run_pytests.py.lock` must be current; the setup action's
uv cache key covers these lockfiles as well as `uv.lock`. A plugin
path in root `testpaths`, or a missing configured directory, fails planning; a
plugin without a runner gets no pytest shard. A plugin path in root `pythonpath`
also fails planning: plugin imports belong to the runner's `IMPORT_PATHS`. New
tests still have to satisfy the test-root coverage guard, which reads both
authorities.

A marketplace `metadata.version`-only bump does not expand an otherwise local
change. The planner compares both immutable JSON documents after removing only
that field; changed registrations, other metadata, invalid JSON or unavailable
comparison evidence restore full checks. Manifest validation still runs.

Global tests run for every change, including plugin documentation. They check
cross-plugin/repository contracts, manifests, instruction drift and test discovery,
so directory ownership alone is insufficient to skip them. A plugin source or
`conftest.py` edit selects only that plugin's shard and the global shard: each
runner passes `-c os.devnull` and `--confcutdir` at its plugin root, so no other
plugin's run can import that source or load that conftest.

File-local checks use prek's existing filters and the complete PR diff rather than
maintaining a second lint configuration. Ruff, Biome, Markdown and shell lanes are
omitted when no relevant file type changed. Extensionless files enable these lanes
because prek can classify shebangs. Configuration edits restore whole-tree checking.
Type checking remains repository-wide when Python or its configuration changes,
since changing a provider can break unchanged callers. The dependency evidence
audit always remains global: removing the last use from prose or commands matters
as well as removing a Python import.

File hygiene deliberately keeps the full tracked-file inventory, including
symlink and case-conflict checks. Deleting a target can break an unchanged symlink
outside the diff; these are cross-file invariants rather than file-local lint.
The runner's unnamed `prek` operation is this global hygiene lane. Only explicitly
named language hooks use changed-file selection.

Every development-harness lane is its runner plus a marker, never a list of
test files: `integration and not research_vault` in the integration matrix,
`cross_backend` once per `BACKLOG_BACKEND` (`memory`, `sqlite`) in
`cross_backend_matrix`, and `e2e` in the live job. The runner owns the test roots,
so a test that gains a marker anywhere in the plugin joins its lane; `run.py`
rejects a runner shard that names paths. The planner schedules these lanes only
while the runner exists. The integration matrix also holds the research-backlinks
and rebase-publication root shards. The dh lane table lives in `plan.py`; move it
into the runner contract once a second plugin needs a lane beyond its fast default. Pinned versioner integration remains in the manifest lane. Research-vault
validation stays advisory. The live-E2E job retains its existing main/manual trigger,
sandbox credentials, serialization, process deadlines, cleanup and evidence uploads;
it runs the development-harness runner with `-m e2e -n 0`.

## Safety and evidence

The diff uses event commit SHAs and Git merge-base, not mutable branch names or
GitHub's truncated path-filter/API lists. Rename detection is disabled so both the
old and new owners participate; NUL-delimited paths preserve whitespace. Deleted
plugins still trigger global and manifest checks without passing missing directories
to skilllint. File-local checks run against the checkout's merged content, using
base/head only to select paths. The setup action accepts `fetch-depth: 0` so its
inner checkout preserves the history needed by these jobs.

`Quality Gate` is the stable required-check name. It always runs, requires the
planner and every blocking lane, and uses the existing alls-green action. Only jobs
explicitly deselected by the plan appear in `allowed-skips`; failures and
cancellations are not allowed. An absent plan grants no skip exceptions. Matrix
fail-fast is disabled so one failing shard does not cancel the remaining evidence.
No workflow-level path exclusions hide the required check.

The runner rejects empty/unsafe paths instead of falling back to unqualified pytest
or repository-wide validation. It replaces its process with the child command,
preserving every exit status, including pytest's no-tests-collected failure. The
global shard retains the root marker, strictness, xdist and coverage configuration.
Plugin shards run under the runner's own configuration and without coverage; each
runner's arguments set its parallelism (see `plugins/<name>/run_pytests.py`). Coverage
reports now describe individual shards; they are not an aggregated repository
percentage, and no new aggregate coverage threshold is asserted.

The planner writes its complete compact JSON to stdout and `GITHUB_OUTPUT`, and
selection reasons/shard names to the job summary. Compare job duration and total
runner minutes over equivalent changes before claiming performance improvement.
Parallel shards add setup overhead; selection removes unrelated work.

## Reproduce

Preview a full run from the repository root:

```bash
uv run --script .github/ci/plan.py --event workflow_dispatch
```

Preview a pull request using its actual immutable commit SHAs, both present locally:

```bash
uv run --script .github/ci/plan.py --event pull_request \
  --base "$BASE_SHA" --head "$HEAD_SHA"
```

Run the selector, Git-boundary, runner and workflow-wiring regressions:

```bash
uv run --locked pytest tests/test_ci_plan.py tests/test_ci_workflow_contract.py
```

`run.py` consumes `CI_PLAN` and, for pytest, `CI_SHARD` as JSON environment variables.
Do not place unquoted matrix values into shell command text. See the workflow for
the exact environment handoff. These tests validate selection and wiring, not
GitHub scheduling, hosted runner setup or all underlying plugin suites; inspect the
actual PR checks for that evidence.
