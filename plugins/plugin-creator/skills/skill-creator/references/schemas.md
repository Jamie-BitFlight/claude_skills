# JSON Schemas

This document defines the JSON schemas used by skill-creator.

---

## evals.json

Defines the evals for a skill. Located at `evals/evals.json` within the skill directory.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's example prompt",
      "expected_output": "Description of expected result",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "The output includes X",
        "The skill used script Y"
      ]
    }
  ]
}
```

**Fields:**
- `skill_name`: Name matching the skill's frontmatter
- `evals[].id`: Unique integer identifier
- `evals[].prompt`: The task to execute
- `evals[].expected_output`: Human-readable description of success
- `evals[].files`: Optional list of input file paths (relative to skill root)
- `evals[].expectations`: List of verifiable statements

---

## history.json

Tracks version progression in Improve mode. Located at workspace root.

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "v2",
  "iterations": [
    {
      "version": "v0",
      "parent": null,
      "expectation_pass_rate": 0.65,
      "grading_result": "baseline",
      "is_current_best": false
    },
    {
      "version": "v1",
      "parent": "v0",
      "expectation_pass_rate": 0.75,
      "grading_result": "won",
      "is_current_best": false
    },
    {
      "version": "v2",
      "parent": "v1",
      "expectation_pass_rate": 0.85,
      "grading_result": "won",
      "is_current_best": true
    }
  ]
}
```

**Fields:**
- `started_at`: ISO timestamp of when improvement started
- `skill_name`: Name of the skill
- `current_best`: Version identifier of the best performer
- `iterations[].version`: Version identifier
- `iterations[].parent`: Parent version this was derived from
- `iterations[].expectation_pass_rate`: Pass rate from grading
- `iterations[].grading_result`: "baseline", "won", "lost", or "tie"
- `iterations[].is_current_best`: Whether this is the current best version

---

## grading.json

Output from the grader agent. Located at `<run-dir>/grading.json`.

```json
{
  "expectations": [
    {
      "text": "The output includes the name 'John Smith'",
      "passed": true,
      "evidence": "Found in transcript Step 3: 'Extracted names: John Smith, Sarah Johnson'"
    },
    {
      "text": "The spreadsheet has a SUM formula in cell B10",
      "passed": false,
      "evidence": "No spreadsheet was created. The output was a text file."
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": {
      "Read": 5,
      "Write": 2,
      "Bash": 8
    },
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  },
  "claims": [
    {
      "claim": "The form has 12 fillable fields",
      "type": "factual",
      "verified": true,
      "evidence": "Counted 12 fields in field_info.json"
    }
  ],
  "user_notes_summary": {
    "uncertainties": ["Used 2023 data, may be stale"],
    "needs_review": [],
    "workarounds": ["Fell back to text overlay for non-fillable fields"]
  },
  "eval_feedback": {
    "suggestions": [
      {
        "assertion": "The output includes the name 'John Smith'",
        "reason": "A hallucinated document that mentions the name would also pass"
      }
    ],
    "overall": "Assertions check presence but not correctness."
  }
}
```

**Fields:**
- `expectations[]`: Graded expectations with evidence
- `summary`: Aggregate pass/fail counts
- `execution_metrics`: Tool usage and output size (from executor's metrics.json)
- `timing`: Wall clock timing (from timing.json)
- `claims`: Extracted and verified claims from the output
- `user_notes_summary`: Issues flagged by the executor
- `eval_feedback`: (optional) Improvement suggestions for the evals, only present when the grader identifies issues worth raising

---

## metrics.json

Output from the executor agent. Located at `<run-dir>/outputs/metrics.json`.

```json
{
  "tool_calls": {
    "Read": 5,
    "Write": 2,
    "Bash": 8,
    "Edit": 1,
    "Glob": 2,
    "Grep": 0
  },
  "total_tool_calls": 18,
  "total_steps": 6,
  "files_created": ["filled_form.pdf", "field_values.json"],
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

**Fields:**
- `tool_calls`: Count per tool type
- `total_tool_calls`: Sum of all tool calls
- `total_steps`: Number of major execution steps
- `files_created`: List of output files created
- `errors_encountered`: Number of errors during execution
- `output_chars`: Total character count of output files, never a token estimate
- `transcript_chars`: Character count of transcript

The grader copies these execution metrics into `grading.json.execution_metrics`. An unavailable value is omitted or null, not manufactured as zero. The legacy `<run-dir>/metrics.json` timing carrier is supported by the aggregator only when it supplies the same explicit timing/token fields as `timing.json`; this is distinct from `outputs/metrics.json`.

---

## timing.json

Measured timing and token usage for one run. Located at `<run-dir>/timing.json` beside its `grading.json`.

Capture the host's measured values when available. Record the model, environment, and measurement boundary with the run so comparisons use equivalent observations. Do not assume every harness exposes token counts or that missing values can be recovered from character counts.

```json
{
  "total_tokens": 84852,
  "duration_ms": 191000,
  "total_duration_seconds": 191.0,
  "executor_start": "2026-01-15T10:30:00Z",
  "executor_end": "2026-01-15T10:32:45Z",
  "executor_duration_seconds": 165.0,
  "grader_start": "2026-01-15T10:32:46Z",
  "grader_end": "2026-01-15T10:33:12Z",
  "grader_duration_seconds": 26.0
}
```

Here `total_duration_seconds` measures the sum of executor and grader durations, not the one-second gap between them. An executor-only experiment must identify that narrower boundary instead. `total_tokens` is an actual nonnegative integer token measurement over the recorded boundary. Unknown measurements are null or omitted; measured zero is valid. When multiple carriers provide different values for the same metric, the aggregator retains the source conflict and leaves that metric unavailable rather than choosing the cheaper one.

---

## benchmark.json

Output from Benchmark mode. Located at `benchmarks/<timestamp>/benchmark.json`. Existing workspace and legacy `runs/` layouts are supported.

```json
{
  "metadata": {
    "skill_name": "pdf",
    "skill_path": "/path/to/pdf",
    "executor_model": "claude-sonnet-4-20250514",
    "analyzer_model": "most-capable-model",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1],
    "runs_per_configuration": 1,
    "run_counts": [
      {"eval_id": 1, "configuration": "with_skill", "observed_runs": 1}
    ],
    "coverage": "observed-directories-only",
    "grading_status": "COMPLETE",
    "units": {"time_seconds": "seconds", "tokens": "tokens", "output_chars": "characters"}
  },
  "runs": [
    {
      "eval_id": 1,
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 1.0,
        "passed": 1,
        "failed": 0,
        "total": 1,
        "time_seconds": 42.5,
        "tokens": null,
        "output_chars": 12450,
        "tool_calls": 18,
        "errors": 0
      },
      "measurement_sources": {"time_seconds": ["timing.json"], "tokens": []},
      "measurement_gaps": [],
      "expectations": [{"text": "Required output exists", "passed": true, "evidence": "Observed artifact"}],
      "notes": []
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 1.0, "stddev": 0.0, "min": 1.0, "max": 1.0, "observed": 1, "missing": 0},
      "time_seconds": {"mean": 42.5, "stddev": 0.0, "min": 42.5, "max": 42.5, "observed": 1, "missing": 0},
      "tokens": {"mean": null, "stddev": null, "min": null, "max": null, "observed": 0, "missing": 1}
    },
    "delta": {"pass_rate": null, "time_seconds": null, "tokens": null}
  },
  "notes": ["Token usage was unavailable; character counts were not substituted."]
}
```

**Fields:**
- `metadata`: Information about the benchmark run
  - `skill_name`, `skill_path`, model identities and timestamp: provenance; replace placeholders only with known values
  - `evals_run`: Observed eval identifiers
  - `runs_per_configuration`: Observed repetition count when every observed eval/configuration group has that same count, otherwise null; never an assumed default
  - `run_counts`: Actual observed counts per eval/configuration
  - `coverage`: `observed-directories-only`; the caller must separately account for expected directories that never appeared
  - `grading_status`: `COMPLETE` when every observed run has usable grading counts, otherwise `INCOMPLETE`; not a claim that every task passed or all planned work occurred
  - `units`: Units for numeric metrics; tokens and characters remain distinct
- `runs[]`: One result per observed run directory, including missing/invalid grader returns
  - `eval_id`, `configuration`, `run_number`: Stable observed grouping; preserve exact configuration names such as `with_skill` and `without_skill`
  - `eval_name`: Optional human-readable label for the viewer
  - `result`: Nested counts and metrics; unknown values are null, measured zero remains zero
  - `pass_rate`: Derived from usable nonnegative integer `passed`, `failed`, `total` counts with a positive total and `passed + failed == total`; missing/inconsistent grading leaves it null
  - `measurement_sources`: Carriers used for each timing/token metric
  - `measurement_gaps`: Invalid/missing grader records, malformed or conflicting measurements
  - `expectations`, `notes`: Retained grader observations
- `run_summary`: Statistics per configuration, calculated from available values only
  - `observed` and `missing`: Per-metric denominators; missing values are not zero-cost successes
  - `mean`, `stddev`, `min`, `max`: Null when no observations are available
  - `delta`: First configuration minus second, only for exactly two matching observed eval/run sets with complete values for that metric; otherwise null. No absent baseline is invented.
- `notes`: Additional observations and limits from the analyzer

The viewer displays unavailable metrics as N/A. Preserve these field names and nesting; a renamed or omitted field cannot be treated as successful evidence. The aggregator does not establish semantic correctness, model independence, or environment comparability.

---

## Trigger evaluation and description selection

`run_eval.py` accepts a nonempty list of unique nonempty `query` strings with boolean `should_trigger` labels. Repeated executions use `runs_per_query`, not duplicate records.

Each result retains `runs` (attempted), `valid_runs` (completed behavioral observations), `errors`, `triggers`, and `observations` with `run` and `status: TRIGGERED | NOT_TRIGGERED | ERROR`; errors also retain their diagnostic. `trigger_rate` divides by valid runs or is null when none exist. `pass` is boolean only when every requested repetition has a valid observation; otherwise null. The summary separates `passed`, `failed`, and `inconclusive`. A positive records invocation selection, not successful skill execution.

`run_loop.py` keeps legacy `test_*` fields for the candidate-selection partition. `holdout_role` explicitly records `candidate-selection` or `none`; `final_generalization_test` remains `NOT_RUN`. Incomplete iterations cannot select a winner or drive another description change. `best_description` and `best_iteration` are null when no recommendation is admissible. Selection scores are not untouched final-test results. The returned `environment` identifies disposable sample projects and inherited user-level context; it is not proof of clean-room isolation.

---

## comparison.json

Output from blind comparator. Located at `<grading-dir>/comparison-N.json`.

```json
{
  "winner": "A",
  "reasoning": "Output A provides a complete solution with proper formatting and all required fields. Output B is missing the date field and has formatting inconsistencies.",
  "rubric": {
    "A": {
      "content": {
        "correctness": 5,
        "completeness": 5,
        "accuracy": 4
      },
      "structure": {
        "organization": 4,
        "formatting": 5,
        "usability": 4
      },
      "content_score": 4.7,
      "structure_score": 4.3,
      "overall_score": 9.0
    },
    "B": {
      "content": {
        "correctness": 3,
        "completeness": 2,
        "accuracy": 3
      },
      "structure": {
        "organization": 3,
        "formatting": 2,
        "usability": 3
      },
      "content_score": 2.7,
      "structure_score": 2.7,
      "overall_score": 5.4
    }
  },
  "output_quality": {
    "A": {
      "score": 9,
      "strengths": ["Complete solution", "Well-formatted", "All fields present"],
      "weaknesses": ["Minor style inconsistency in header"]
    },
    "B": {
      "score": 5,
      "strengths": ["Readable output", "Correct basic structure"],
      "weaknesses": ["Missing date field", "Formatting inconsistencies", "Partial data extraction"]
    }
  },
  "expectation_results": {
    "A": {
      "passed": 4,
      "total": 5,
      "pass_rate": 0.80,
      "details": [
        {"text": "Output includes name", "passed": true}
      ]
    },
    "B": {
      "passed": 3,
      "total": 5,
      "pass_rate": 0.60,
      "details": [
        {"text": "Output includes name", "passed": true}
      ]
    }
  }
}
```

---

## analysis.json

Output from post-hoc analyzer. Located at `<grading-dir>/analysis-N.json`.

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path/to/winner/skill",
    "loser_skill": "path/to/loser/skill",
    "comparator_reasoning": "Brief summary of why one version beat another"
  },
  "loser_weaknesses": ["Missing required behavior"],
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "Clarify the material decision",
      "expected_impact": "Reduce the observed contract violation"
    }
  ]
}
```
