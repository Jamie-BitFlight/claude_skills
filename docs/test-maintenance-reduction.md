# Test maintenance reduction

Base revision: `af33b27379d9c762f69524ebc503013281ba0d32`.
Tracking: [#4134](https://github.com/Jamie-BitFlight/claude_skills/issues/4134).

This change removes representation checks, not supported product behavior. No production code,
pytest discovery, marker selection, warning configuration, dependency, or CI gate changes.

## Decision ledger

Each row identifies the owner/consumer, meaningful fault, and remaining observation. Source
assessment is not proof that the remaining suite detects every fault.

| Family removed | Authority and consumer | Consequential fault and remaining detector | Maintenance decision and limit |
|---|---|---|---|
| Plugin marker-description mirror and its AST helper | Root configuration and each plugin runner own their marker/lane configuration; pytest consumes marker names | Runner contract tests inspect isolated configuration and exercise default/explicit lanes; unknown-marker control observes strict collection rejection | Human descriptions and conftest decomposition are not a shared byte contract. Neither the removed mirror nor the synthetic unknown-marker control proves every real plugin marker is registered. Complete plugin runs exercise their selected registrations. |
| Coverage configuration shape in bounded-runner tests | Coverage consumes `pyproject.toml`; bounded-runner callers consume child status/output and process cleanup | Remaining process tests observe relayed output/status, timeout, descendant reaping and Windows termination arguments | Exact coverage-engine/default choices do not belong to the process-runner contract. Parsing configuration is not proof of effective subprocess coverage; no replacement guarantee is claimed. |
| Harness-generator human success sentences | Contributors consume generated compatibility JSON; pre-commit consumes `--check` status | Remaining generator tests parse manifest/component/blocker/evidence output, reject invalid inputs and observe that `--check` writes no view | Human success wording may change without changing structured output. Exact terminal success text is no longer pinned. |
| Artificial canonical JSONL renderer examples | Activation generator `--check` owns byte freshness; activation validator consumes semantic JSONL | Checked-in matrix byte equality remains, alongside semantic inventory/evidence checks and non-mutating CLI drift rejection | Remove duplicated artificial renderer fixtures, not the canonical-byte contract. The stored artifact remains an independent byte observation. |
| Holistic-linting instructional phrases, retired-name inventory and local resource-helper self-test | Plugin guidance is consumed by agents; hook-detector CLI is executable behavior | Retained hook tests observe actual Git hook/runner selection and incomplete outcomes; Markdown-link tests observe packaged relative targets | Heading/phrase presence does not demonstrate agent behavior. No claim that executable tests replace agent evaluation or semantic documentation review. |
| GitLab source-attribution wording, obsolete terms, prompt vocabulary and fixed route/eval inventories | GitLab CI consumes component YAML/shell; evaluation tooling consumes structured eval data; agents consume guidance | Retained tests parse eval field/type/unique-ID/load-path contracts and reference links, execute component shell paths and distinguish upload success from destination readback; a focused generated-config test preserves consumer-selected tag prefixes | Fixed IDs, link counts and source spelling are removed. Load-path validation does not establish adapter exclusivity or conditional model routing. The removed sandbox denylist's genuine prefix protection is restored behaviorally. |
| Kaizen direct schema heading/size assertion | MCP clients consume the schema tool and resource; plugin owns the bundled schema | Retained in-memory FastMCP calls observe both schema identities and resource/tool equality; packaged-path/read tests remain | Both headings remain observed through MCP; only the arbitrary size threshold is uniquely dropped. Transport checks and a size threshold do not prove documentation completeness. |

Retained explicitly: CI selection/security and test-root ownership guards, canonical matrix freshness,
GitLab publication/readback, plugin-runner isolation and lane controls, stateful DH recovery/backend
boundaries, scientific-method persistence/frozen integrity, summarizer receipt/inventory/CLI/Node
bridge, plugin-creator runtime-escape/evaluation isolation and Python dependency classification.

### Permanent test admission

`test_semantic_release_config_preserves_consumer_tag_prefix` protects the public component's
`tag-prefix` input, consumed by semantic-release through generated CJS `tagFormat`. Independent
review identified a real gap: a hardcoded historical prefix would pass the remaining setup,
credential and publication checks. The test executes the shipped generation block and loads the
result with Node, then observes a distinctive consumer prefix. This is a configuration-consumer
boundary, not a source-string denylist. CI already provisions Node for plugin pytest shards.
No other permanent test is added; disposable controls do not join the maintained suite.

Standalone GitLab test-runner users need Bash and Node on `PATH` for the shipped configuration's
execution check; no release package installation or network publication is performed.

## Evidence boundaries

The root fast suite and every discovered plugin runner were executed independently before editing;
root integration was a separate selection. JUnit results, skips/xfails, exact commands and worker
ledgers are retained in the delivery worktree's `.tmp/scratch/reports/test-reduction/`.

The changed root subset initially exposed an incorrectly removed `tomllib` import still consumed
by `root_fast_marker()`: nine setup failures, not lost product protection. Restoring that dependency
without changing expectations yielded 49 passing affected cases.

Disposable generator copies accepted harmless success-wording edits (eight passing cases), rejected
false manifest output at the manifest assertion, and rejected a writing `--check` at output-file
absence. A semantic-only activation checker failed the retained serialization-drift exit-status
assertion. The hardcoded historical tag prefix failed the new `tagFormat` assertion after successful
generation and Node loading; the unmodified template passed. These controls establish no universal
mutation score or coverage equivalence.

Live provider E2E, DH integration/cross-backend, summarizer integration, production research-vault
scans and interactive harness activation are not established by the fast-suite results. Those
unchanged surfaces must remain explicitly unexercised rather than described as passing.

## Observed verification

| Selection or maintained source | Before | After |
|---|---:|---:|
| Root fast cases (one expected xfail included) | 789 | 785 |
| Root integration cases | 55 | 55 |
| Holistic-linting fast cases | 210 | 198 |
| GitLab fast cases | 107 | 99 |
| Kaizen fast cases | 74 | 73 |
| Tracked test modules | 368 | 367 |
| Tracked test-source lines | 148177 | 147837 |

Every executed before/after selection above finished without failures or errors. The root fast
result after reduction was 784 passed and one expected xfail; integration was 55 passed. Before
editing, the other plugin fast runners also completed: development-harness 6384 passed, 12 skipped,
four xfailed; frustration-analyzer 58 passed; plugin-creator 268 passed, three xfailed;
python-engineering 17 passed; scientific-method 104 passed; summarizer 128 passed. Those unchanged
plugin suites were not rerun after the reduction.

Commands: `uv run pytest`; `uv run pytest -m 'integration and not research_vault'`; each plugin's
`uv run --locked --script plugins/<name>/run_pytests.py`; and changed-file `uv run prek run --files ...`
(including Ruff, formatting, ty, Markdown and applicable repository guards). The four changed root
modules passed together after restoring the import. The complete affected plugin runners passed
after integration, including the added consumer-prefix control.

Actual consumer observations: hook-tool CLI selected `prek` in the delivery worktree; compatibility
generator `--check` validated its inputs; activation-matrix generator `--check` accepted the preserved
checked-in artifact; the new prefix test executed Bash generation and Node loading. These are not
live GitLab publication or interactive-agent observations.

Independent root review found no blocking loss. Independent plugin review identified the prefix
gap, accepted the focused correction and confirmed Node provisioning in the CI lane. Its separate
warning about eval load-list validation versus model-routing evidence is reflected in the ledger.
Review was source assessment; disposable faults and positive execution were performed by the
integration owner. Lower case counts and green suites do not establish identical coverage or reliability.
