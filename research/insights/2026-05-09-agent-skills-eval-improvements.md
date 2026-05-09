# Improvement Proposals: agent-skills-eval

**Research entry**: ./research/evaluation-testing/agent-skills-eval.md
**Generated**: 2026-05-09
**Patterns assessed**: 7
**Backlog items created**: 3
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Provider abstraction for skill evaluation runner

**Source pattern**: "Provider abstraction pattern: Decoupling model completion from the evaluator logic (via the `Provider` interface) enables testing against mock providers, local models, and multiple cloud providers without code duplication." — `agent-skills-eval.md` Patterns Worth Adopting, line 285.
**Local system**: plugins/plugin-creator/skills/skill-creator/scripts/run_eval.py
**Confidence**: High
**Impact**: Medium
**Backlog**: local-only file `p1-provider-abstraction-for-skill-evaluation-runner.yaml` — GitHub sync pending

### Current state

`run_eval.py` is hardcoded to invoke the `claude` CLI as a subprocess (see lines 75–88, `_build_claude_cmd`). The script has no provider interface, no `baseUrl`/`apiKey` parameters, and no abstraction over completion. As a result the eval workflow cannot be exercised against alternative model backends (mock provider for unit testing, OpenAI-compatible endpoints, local Llama servers, internal APIs) without forking the script. There is no `Provider`, `ProviderResult`, or `complete()` interface anywhere under `plugins/plugin-creator/skills/skill-creator/scripts/`.

### Target state

A new module `plugins/plugin-creator/skills/skill-creator/scripts/providers.py` defines a Python `Provider` Protocol with `name`, `model`, `complete(prompt: str) -> ProviderResult`, and a `ClaudeCliProvider` implementation that wraps the existing subprocess logic. `run_eval.py` accepts a `--provider` argument (default `claude-cli`) that selects the provider implementation. A second built-in provider `MockProvider` returns canned responses for unit testing. The `Provider` protocol and `ProviderResult` dataclass are documented in `references/evaluation-and-optimization.md` under a new "Provider Abstraction" subsection.

### Measurable signal

- File `plugins/plugin-creator/skills/skill-creator/scripts/providers.py` exists and exports a `Provider` Protocol class plus `ClaudeCliProvider` and `MockProvider`.
- `run_eval.py --help` lists `--provider` as a valid argument.
- Running `uv run plugins/plugin-creator/skills/skill-creator/scripts/run_eval.py --provider mock --eval-set <path>` completes without invoking `claude` and produces a valid eval result.
- `references/evaluation-and-optimization.md` contains a "Provider Abstraction" subsection.

---

## Improvement 2: Bounded-concurrency worker pool for parallel skill eval runs

**Source pattern**: "Bounded concurrency worker pool: The `runPool<T>()` pattern (src/evaluate-skills.ts lines 126–136) is a clean, typed implementation of FIFO task queue with N concurrent workers. Applicable to any parallelizable batch task." — `agent-skills-eval.md` Patterns Worth Adopting, line 286. Also Key Features line 67: "Bounded worker pool runs eval cases in parallel; defaults to 4 concurrent evals, configurable per task."
**Local system**: plugins/plugin-creator/skills/skill-creator/references/evaluation-and-optimization.md (Step 8a) and plugins/plugin-creator/skills/skill-creator/scripts/run_eval.py
**Confidence**: High
**Impact**: Medium
**Backlog**: local-only file `p1-bounded-concurrency-worker-pool-for-parallel-skill-eval-runs.yaml` — GitHub sync pending

### Current state

The skill-eval workflow (Step 8a, `evaluation-and-optimization.md` lines 86–93) instructs the orchestrator to "launch TWO parallel runs" per test case "using the Agent tool" but provides no concurrency bound, no task queue, and no per-skill default for how many evals may run simultaneously. With N test cases and 2 modes each, this fans out to 2N concurrent agent invocations — risking rate limits, API quota exhaustion, and chaotic logs. The trigger-eval path (`run_eval.py`) uses `ProcessPoolExecutor` for query parallelism, but the skill-eval path has no equivalent bound.

### Target state

A new section "Concurrency control" in `evaluation-and-optimization.md` between Step 8a and Step 8b documents a `concurrency` parameter (default 4) that the orchestrator MUST honour when launching parallel `with_skill`/`without_skill` runs. The orchestrator launches at most `concurrency` runs in parallel, queues the remainder, and starts the next run as each completes. The section cites the agent-skills-eval `runPool` precedent and explains the rationale (rate limits, log readability, deterministic resource usage). `run_eval.py` exposes a `--concurrency` flag (default 4) for any internal batching it performs.

### Measurable signal

- Grep `evaluation-and-optimization.md` for the literal string `concurrency` returns at least one section header match.
- The Step 8a procedure includes a sentence stating: "Launch at most {concurrency} runs in parallel; queue the remainder."
- `run_eval.py --help` lists `--concurrency` with default 4.

---

## Improvement 3: Deterministic tool-call assertions in evals.json schema

**Source pattern**: "Tool-call assertions — Deterministic checks for agents that call tools" — README.md line 68; "Validates tool calls locally without judge involvement — checks function names, argument structure, and call sequencing." — `agent-skills-eval.md` Key Features line 66.
**Local system**: plugins/plugin-creator/skills/skill-creator/references/schemas.md (evals.json schema)
**Confidence**: High
**Impact**: High
**Backlog**: local-only file `p1-deterministic-tool-call-assertions-in-evalsjson-schema.yaml` — GitHub sync pending

### Current state

`schemas.md` (lines 9–35) defines the `evals.json` schema with `expectations` (array of strings, judge-graded) and an implicit `assertions` array referenced in `evaluation-and-optimization.md` lines 122–138 with three types: `file_exists`, `file_contains`, `custom`. There is no `tool_call` assertion type. The grader agent (`agents/grader.md`) is therefore the only mechanism that can verify whether a skill caused the model to invoke a specific tool, and judge-graded checks for tool invocation are unreliable when the transcript is large or noisy. `metrics.json` (lines 167–183) records aggregate `tool_calls` counts per tool type but offers no per-eval assertion semantics.

### Target state

`schemas.md` adds a fourth assertion type `tool_call` with the following sub-fields: `name` (required, string — function name to match), `arguments` (optional, object — partial argument-key match), `min_count` / `max_count` (optional, integer), `before` / `after` (optional, string — name of another tool call that must precede/follow this one). The grader agent (`agents/grader.md`) gains a deterministic step that, before invoking the judge, runs all `tool_call` assertions against the captured transcript's tool-call entries and records pass/fail in `grading.json` under a new `tool_call_results` array. Failures are recorded as assertion failures without consulting the judge.

### Measurable signal

- `schemas.md` contains a documented `tool_call` assertion type with the listed sub-fields.
- `grading.json` example in `schemas.md` shows a `tool_call_results` array.
- `grader.md` has a step describing deterministic tool-call assertion evaluation that explicitly states it runs before the judge model is consulted.

---

## Improvement 4: Fail-closed grading on judge parse error

**Source pattern**: "Judge-based grading with fallback: The `fail-closed` strategy (src/grade.ts lines 84–87) where unparseable judge responses default to assertion failure is a robust defensive pattern for LLM-based grading." — `agent-skills-eval.md` Patterns Worth Adopting, line 287.
**Local system**: plugins/plugin-creator/agents/grader.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: confirming the absence requires reading the full grader.md and any fallback handling logic in scripts that consume `grading.json`. The first 60 lines confirm a process for evaluating expectations but do not describe behaviour when the grader's own JSON output is malformed or partial. To raise confidence to High, read the remainder of `grader.md` plus `aggregate_benchmark.py` to confirm there is no fail-closed handler for malformed grader output.

### Current state (provisional)

`grader.md` lines 38–50 describe the verdict logic (PASS / FAIL based on evidence) but do not describe what happens when the grader itself fails to produce valid JSON. If a downstream consumer (e.g., `aggregate_benchmark.py`) treats a missing `grading.json` or unparseable output as "no result" rather than "fail", silent quality regressions can slip through. The agent-skills-eval `fail-closed` pattern would specify: any malformed grader response is treated as assertion failure, surfaced in the report, and counted in pass-rate calculations as a fail.

### Target state

An explicit "Fail-closed on parse error" section in `grader.md` instructing the grader to emit a valid `grading.json` even on internal error (with all expectations marked failed and an `error` field describing the failure). `aggregate_benchmark.py` rejects evals lacking a parseable `grading.json` by recording them as fails — not by skipping them silently.

### Measurable signal

- `grader.md` contains a section titled "Fail-closed on parse error" or equivalent.
- `aggregate_benchmark.py` has a code path that, when `grading.json` is missing or invalid, records the eval as failed in benchmark output.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Fail-closed grading on judge parse error | medium | Confirming absence requires reading the full grader.md (over 60 lines) and aggregate_benchmark.py to verify no fail-closed handler exists today. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Iteration workspace versioning (`iteration-N` layout) | Already implemented in `references/evaluation-and-optimization.md` lines 84–112 with `iteration-1/`, `eval-0/`, `with_skill/`, `without_skill/` structure. |
| Baseline comparison (`with_skill` vs `without_skill`) | Already implemented in `references/evaluation-and-optimization.md` Step 8a lines 86–93 with parallel with-skill and baseline runs. |
| Judge-graded outputs with rubric | Already implemented via the `grader` agent at `plugins/plugin-creator/agents/grader.md` and `grading.json` schema in `references/schemas.md` lines 86–149. |
| Static HTML reports | Already implemented via `plugins/plugin-creator/skills/skill-creator/eval-viewer/generate_review.py` and `viewer.html`. |
