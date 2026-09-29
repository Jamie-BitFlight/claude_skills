# Testing

## Commands

```bash
uv run pytest                              # Repository-owned fast suite (parallel via xdist); e2e, cross_backend, integration, and research_vault are deselected by addopts
uv run pytest -m "not e2e and not cross_backend and not integration and not research_vault and not slow"  # Same, also excluding slow tests
uv run --locked --script plugins/<name>/run_pytests.py  # One plugin's fast suite, from its run_pytests.py.lock (the runner's default -m), from any cwd; -m "" selects every marker
uv run --locked --script plugins/development-harness/run_pytests.py -m "integration and not research_vault"  # development-harness integration tests, every test root
uv run --locked --script plugins/development-harness/run_pytests.py -m cross_backend  # development-harness cross-backend lane; the tests parametrize every backend
uv run pytest -m "integration and not research_vault" tests/research_backlinks/  # Repository integration tests (deselected by default)
uv run pytest -m research_vault tests/research_backlinks/test_graph_asymmetry.py  # Advisory, read-only production-vault scan
uv run --locked --script plugins/development-harness/run_pytests.py tests/test_migrate_tasks_to_github.py  # Specific plugin test file, relative to the plugin root
```

Coverage (`--cov=scripts --cov=plugins`) is always on via root addopts — passing `--cov` again is redundant. Plugin runners read no root config, so they run without coverage unless you pass it. Each runner's own arguments set its parallelism; read `plugins/<name>/run_pytests.py`.

## Testing policy: maintenance-adjusted value

Tests are maintained software. Every retained test consumes recurring reading/reasoning context,
execution resources, failure-investigation effort, and modification work. Optimize for the smallest
maintainable suite that gives strong confidence in consequential system behavior, not for test count,
coverage percentage, a conventional test pyramid, or the appearance of thoroughness.

Use the economic rule `retained-test value = expected protection benefit - expected ownership cost`
qualitatively, not as a fabricated numeric score. Protection benefit comes from consequential faults
uniquely detected, their plausible recurrence, detection effectiveness, contract durability, and
useful feedback. Ownership cost accumulates through human/agent context, implementation-coupled churn,
fixtures/data, execution/CI resources, diagnosis, flakiness, environment/dependency upkeep, refactor
drag, duplicated protection, and review/merge coordination. A fast test can still be expensive to own.

Validation and permanent regression protection are separate decisions. Every claimed fix must have
direct validation before closure against the behavior it was meant to change. Prefer a discriminating
before/after observation when practical: reproduce the incorrect behavior, apply the fix, then run
the same observation and show the corrected result. A one-time command, probe, isolated scenario,
existing contract/system test, linter, parser, compiler, or other direct evidence may satisfy this
close criterion. Necessary validation does not automatically become a permanent test.

After deciding how the change will be validated, apply the
[DH test admission gate](../plugins/development-harness/docs/testing-principles.md#test-admission-gate)
or load [Test Designer](../plugins/development-harness/skills/test-designer/SKILL.md) to decide whether
new regression protection should be retained. A maintained test must add independent protection for a
meaningful behavior, invariant, interface, failure mode, or externally observable contract that existing
protection does not already cover adequately. `NO NEW TEST JUSTIFIED` is a valid retention result.

Prefer higher contract altitude when it gives useful fault discrimination at acceptable cost:
holistic/system outcome -> user/public/cross-component contract -> component/interface contract ->
TDD-sized unit behavior -> private implementation detail. The last level is not a test contract by
default. A retained test should be traceable upward to a meaningful system goal or supported
contract, even when it runs at a smaller boundary.

Keep unit tests at TDD scale: small executable examples that drive one meaningful behavior and remain
green across behavior-preserving refactors. Do not turn unit tests into mirrors of private helpers,
branches, hard-coded constants, incidental call counts, internal ordering, or current decomposition
unless one of those details is itself an authoritative contract. When a small lifecycle/contract test
protects the same consequential failure, prefer it to many implementation-coupled unit tests.

Do not add tests merely to freeze intentional wording or structure. Judge text assertions by the
behavior they discriminate. Exact text is legitimate when the observed text proves a consequential
path/outcome or is itself an authoritative externally observable contract; an expected error message,
for example, can prove that the intended error path was reached. A keyword-presence assertion over
`SKILL.md`, `AGENTS.md`, README/reference prose, prompts, comments, headings, examples, or phrases
does not prove behavioral value merely because the text exists.

For instruction text, require evidence that changing/removing the instruction adversely affects the
desired agent behavior before retaining a presence assertion as regression protection. Otherwise use
representative behavioral evaluation of consequential actions, routing, side effects, or outcomes.
Machine-readable frontmatter, schemas, manifests, generated inventories, and parsable metadata may
receive structural validation through their actual parser/consumer contract. Lint, schema validation,
link checking, typing, compilation, and other deterministic mechanisms can validate an edit without
creating another long-lived regression test.

Coverage is diagnostic evidence in this repository, not a quality target or merge gate. Continue
collecting it where inexpensive, but do not create tests solely to cover lines and do not reject a
change merely because its percentage decreases. Any future threshold requires a documented,
subsystem-specific reason that percentage coverage is a useful proxy for a demonstrated risk.

## Failure investigation and test effectiveness

For a CI failure, use
[Root-Cause Tracing Process](../plugins/development-harness/skills/root-cause-tracing-process/SKILL.md)
to preserve the failing state, establish contract authority, trace product and test boundaries,
and choose an evidence-backed correction. Use
[Comprehensive Test Review](../plugins/development-harness/skills/comprehensive-test-review/SKILL.md)
to assess oracle validity, relevant fault sensitivity, refactor tolerance, and boundary fidelity.
Read those skills directly when their invocation routes are unavailable.

The [regression evaluation guide](../plugins/development-harness/skills/root-cause-tracing-process/evals/README.md)
explains baseline/candidate scenario runs, independent grading, Python entry-point checks, and
validation limits. These agent evaluations are separate from pytest and are not automatically
executed by the CI commands above. Do not report authored scenarios as passing behavior.

## Live GitHub E2E

Read the [live validation runbook](../plugins/development-harness/docs/live-e2e-validation.md)
for the explicit sandbox, scoped credential, run identity, and cleanup requirements. The lane
uses `-n 0`, immediate failure journals, a process-tree deadline, and independently observed
remote outcomes. Missing sandbox configuration is a failure, not a passing skip.

## Plugin installation testing

```bash
claude --plugin-dir ./plugins/python-engineering        # Load single plugin
claude --plugin-dir ./plugins/holistic-linting          # Load multiple plugins
/plugin marketplace add ./.claude-plugin/marketplace.json  # Add local marketplace
/plugin install python-engineering@jamie-bitflight-skills --scope local
/plugin validate ./plugins/plugin-name                  # Validate plugin structure
```

## Codex activation matrix

`MAPPED` means an unexecuted task mapping with no activation evidence; its `evidence` fields remain
null until the validation runner records an observed result. It is not a passing activation status.

## Patterns and conventions

- **Framework**: pytest with `pytest-xdist` (parallel), `pytest-asyncio` (async), `pytest-mock`
- **Markers**: `unit`, `integration`, `e2e`, `slow`, `demos`, `cross_backend`, `critical`,
  `research_vault`
- **Default deselection**: addopts include `-m "not e2e and not cross_backend and not integration and not research_vault"`,
  so a bare `uv run pytest` runs the fast in-process suite only. Integration tests (real-subprocess
  CLI/network-guard behavior, ~2-30s each) and cross-backend tests run as separate CI jobs; the
  one `research_vault` test reads the production corpus only in the advisory research-validation job;
  e2e tests need the explicit sandbox configuration above and run on main or manual dispatch.
- **Async mode**: `asyncio_mode = "auto"` — tests auto-detect async
- **Test discovery**: root `pyproject.toml` `testpaths` owns repository tests only. Each pytest-owning plugin's root `run_pytests.py` owns that plugin's complete test topology and PEP 723 execution dependencies. CI discovers those runners rather than reconstructing plugin paths. `tests/test_testpaths_collection_coverage.py` derives coverage from both authorities and fails if a tracked test is owned by neither.
- **Type checker exclusions**: Test files get relaxed rules in `pyproject.toml` per-file overrides
- **Test file placement**: A test lives beside the code it exercises. Tests for code inside a
  plugin go in that plugin's own test directory (`plugins/{name}/tests/`, or the module-local
  directory a plugin already uses, e.g. `sam_schema/tests/`). Root `tests/` is only for code that
  serves repository maintenance and systems — `scripts/`, `.claude/` skill scripts, and CI
  tooling. Placement follows the import target, not convenience: a test that imports plugin code
  belongs in that plugin even when it also touches root tooling. A plugin test placed in root
  `tests/` runs in CI but is invisible to that plugin's standalone runner, so its coverage
  silently disappears for anyone who installs the plugin on its own. Move a misplaced test file
  to the correct location rather than leaving it and noting the exception.
- **Close criteria**: passing pre-existing tests proves no regression, not correctness. A fix does
  not close without direct evidence that the targeted behavior changed as intended. Prefer the same
  discriminating observation before and after the fix when practical. If the original failure cannot
  be reproduced, report that evidence limit rather than treating a green unrelated suite as proof.
  Retention is a separate decision: create a maintained regression test only when the admission gate
  justifies its recurring cost. One-time validation can be the correct close evidence.
- **SAM/backlog MCP error contract**: `sam_schema/server.py` tool handlers let exceptions
  (`PlanNotFoundError`, `TaskNotFoundError`, etc.) propagate rather than returning
  `{"error": ...}` dicts — FastMCP converts them to `isError=true` responses. Tests for
  invalid-input paths must use `pytest.raises(ToolError)` (`fastmcp.exceptions.ToolError`), not
  `assert result["error"]`.
- **pytest parallelism**: Tests run with `-n 2 --dist loadgroup` (xdist): one controller plus two
  workers. Tests marked with `@pytest.mark.xdist_group` run in same worker.
- **conftest name collision**: a test directory carrying `__init__.py` makes its conftest resolve
  as `tests.conftest`, which collides with any other `tests/__init__.py` directory in the repo
  (pytest refuses with "Plugin already registered under a different name"). Leave a test directory
  a plain directory unless its tests actually need package-relative imports.
- **top-level module squatting**: a conftest that puts a plugin's own source directory on
  `sys.path` claims generic module names (`server`, `models`) for the whole session, so the suite
  whose conftest ran last wins. Load the module by explicit path instead — see
  `plugins/frustration-analyzer/tests/_server.py` and `plugins/agentskill-kaizen/tests/conftest.py`.
- **test-root coverage guard**: `tests/test_testpaths_collection_coverage.py` fails when a tracked test file sits outside both repository `testpaths` and every plugin runner's declared test roots.
- **Validation warnings**: Warnings fail validation unless a versioned, scope-limited exception is
  recorded in the relevant plan with an expiry/review condition. Never disable pytest's strict
  configuration to make a warning non-fatal; a minimal runner must explicitly retain
  `--strict-config` and install each configured pytest plugin it needs.
