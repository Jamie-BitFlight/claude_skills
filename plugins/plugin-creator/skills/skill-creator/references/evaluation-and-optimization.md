# Skill Evaluation and Optimization

Post-creation workflow for testing, improving, and optimizing skills using A/B evaluation, grading, and description tuning.

**SOURCE:** Adapted from the official Anthropic skill-creator ([anthropics/skills](https://github.com/anthropics/skills)) with additions for this repository's conventions. Accessed 2026-03-06.

## Table of Contents

- [Development Order: Evaluate Before You Document](#development-order-evaluate-before-you-document)
- [Step 7: Test Cases](#step-7-test-cases)
- [Step 8: Running and Evaluating Test Cases](#step-8-running-and-evaluating-test-cases)
- [Step 9: Improving the Skill](#step-9-improving-the-skill)
- [Claude A / Claude B Collaborative Authoring](#claude-a--claude-b-collaborative-authoring)
- [Advanced: Blind Comparison](#advanced-blind-comparison)
- [Step 10: Description Optimization](#step-10-description-optimization)
- [Reference Files](#reference-files)

## Development Order: Evaluate Before You Document

Create evaluations **before** writing extensive documentation. This ensures your skill solves real problems rather than documenting imagined ones.

**Self-review gate — challenge every token before writing:**

- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

The context window is a public good shared with conversation history, other skills, and the actual task. Only add context Claude doesn't already have.

**Evaluation-driven development sequence:**

1. Run Claude on representative tasks without a skill — document specific failures or missing context
2. Create evaluations that test those gaps
3. Establish a baseline (measure Claude's performance without the skill)
4. Write minimal instructions to address the gaps and pass evaluations
5. Iterate: run evals, compare against baseline, refine

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## Step 7: Test Cases

After writing the skill draft, come up with 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user: "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Then run them.

Save test cases to `evals/evals.json`. Don't write assertions yet — just the prompts. You'll draft assertions in the next step while the runs are in progress.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `schemas.md` for the full schema (including the `assertions` field, which you'll add later).

### Cross-Model Testing

Test your skill with Haiku, Sonnet, **and** Opus before publishing. Skill effectiveness depends on the underlying model — instructions that work on Opus may not provide enough guidance for Haiku.

**What to check per model:**

- **Claude Haiku** (fast, economical): Does the skill provide enough guidance? Haiku needs more explicit direction.
- **Claude Sonnet** (balanced): Is the skill clear and efficient?
- **Claude Opus** (powerful reasoning): Does the skill avoid over-explaining? Opus needs less hand-holding.

If you plan to use a skill across multiple models, aim for instructions that work acceptably across all of them.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, art) often don't need them. Suggest the appropriate default based on the skill type, but let the user decide.

## Step 8: Running and Evaluating Test Cases

This section is one continuous sequence — don't stop partway through.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.). Don't create all of this upfront — just create directories as you go.

### Step 8a: Spawn all runs (with-skill AND baseline) in the same turn

For each test case, launch TWO parallel runs:

- **with-skill**: `claude -p "{prompt}" --allowedTools "..." --permission-mode acceptEdits`
- **without-skill (baseline)**: Same prompt, same tools, but WITHOUT the skill installed

Use `--output-format stream-json` and `--verbose` to capture full transcripts. Run all test cases in parallel using the Agent tool.

Save outputs inside a `run-1/` subdirectory within each config directory. Use underscores in config directory names — the viewer and `aggregate_benchmark.py` use these names verbatim:

```text
iteration-1/
  eval-0/
    with_skill/
      run-1/
        transcript.json
        timing.json
        outputs/
    without_skill/
      run-1/
        transcript.json
        timing.json
        outputs/
  eval-1/
    ...
```

Keep each execution's writable task and instruction environment separate. A fresh conversation alone does not exclude inherited repository instructions, installed skills, memory, user configuration, or another sample's artifacts. Record material exposure differences between arms; do not call contaminated runs a no-skill baseline. The synthetic description-trigger evaluator below is not a substitute for these task executions.

### Step 8b: While runs are in progress, draft assertions

While waiting for runs to complete, write assertions for each test case. Good assertions test meaningful outcomes — they should be hard to satisfy without actually doing the work correctly.

Add assertions to `evals/evals.json`:

```json
{
  "assertions": [
    {
      "type": "file_exists",
      "path": "output/report.md"
    },
    {
      "type": "file_contains",
      "path": "output/report.md",
      "pattern": "Summary"
    },
    {
      "type": "custom",
      "description": "Report includes at least 3 sections with headers"
    }
  ]
}
```

### Step 8c: As runs complete, capture timing data

Save measured `total_duration_seconds` and `total_tokens` in that exact run's `timing.json`, beside `grading.json`, not in a shared eval-directory record. Record the observation boundary and model/environment with the run: executor-only duration and executor-plus-grader duration are not comparable measurements. Use `null` or omit an unavailable measurement; retain measured zero as zero. Character counts belong in `execution_metrics.output_chars`, never in `total_tokens`.

The aggregator resolves each measurement independently from per-run `timing.json` and `grading.json` timing. It also accepts the legacy per-run `metrics.json` carrier. Conflicting values remain unavailable with their source references. Keep `outputs/metrics.json` for execution/tool metrics as described in `schemas.md`.

### Step 8d: Grade, aggregate, and launch the viewer

1. For each completed eval config, dispatch one `plugin-creator:grader` per config (`with_skill` and `without_skill`):

   ```text
   Dispatch `plugin-creator:grader` to grade eval results.
   Context to include in the prompt: evals/evals.json (assertions),
     transcript_path: iteration-N/eval-M/with_skill/run-1/transcript.json,
     outputs_dir: iteration-N/eval-M/with_skill/run-1/outputs/
   Output: iteration-N/eval-M/with_skill/run-1/grading.json
   ```

   Spawn a second grader for the baseline:

   ```text
   Dispatch `plugin-creator:grader` to grade eval results.
   Context to include in the prompt: evals/evals.json (assertions),
     transcript_path: iteration-N/eval-M/without_skill/run-1/transcript.json,
     outputs_dir: iteration-N/eval-M/without_skill/run-1/outputs/
   Output: iteration-N/eval-M/without_skill/run-1/grading.json
   ```

2. Aggregate all grading results using the benchmark script:

   ```bash
   uv run scripts/aggregate_benchmark.py iteration-1/
   ```

3. Generate the eval viewer for the user to review:

   ```bash
   uv run eval-viewer/generate_review.py --static iteration-1/eval-review.html iteration-1/
   ```

   Open the HTML file so the user can see real examples before you attempt any improvements.

Check the report's coverage and measurement gaps before interpreting an average. It counts observed run directories, including missing grader returns, but cannot detect expected directories never created. Reconcile against the caller's expected case/run inventory separately. A `COMPLETE` grading status means those observed returns have usable grading counts, not that every task succeeded or all expected experiments occurred. Missing data is displayed as unavailable, not zero-cost performance. Deltas require two complete matching observed case/run sets; their comparability still depends on the recorded environment and measurement boundaries.

**IMPORTANT:** Generate the eval viewer BEFORE evaluating results yourself. Get examples in front of the user as soon as possible.

### Step 8e: Read the feedback

Check for `feedback.json` from the viewer's "Submit All Reviews" button. The user may have flagged specific issues, approved results, or added notes. Incorporate this feedback into your improvement plan.

**Team feedback (optional but valuable):** Share the skill with teammates and have them try it with real tasks — not test scenarios. Ask: Does the skill activate when expected? Are the instructions clear? What was confusing? Team feedback surfaces blind spots that your own usage patterns won't reveal. Incorporate before the next iteration.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## Step 9: Improving the Skill

### How to think about improvements

The most common failure modes and what to do about them:

**Wrong approach taken.** The skill chose strategy A when strategy B was clearly better. Fix: add decision guidance for when to use which approach. Don't just add rules — add the reasoning, so the skill can generalize.

**Missing information.** The skill didn't know about a constraint, API, or pattern it needed. Fix: add the missing knowledge to a reference file and point to it from SKILL.md.

**Correct approach but poor execution.** The skill knew what to do but made errors in the details — wrong API call, missing edge case, formatting issues. Fix: add a script for the deterministic/error-prone parts, or add concrete examples showing the correct pattern.

**Did something unnecessary.** The skill did extra work that wasn't needed or actively harmful. Fix: add explicit guidance about what NOT to do and why.

**Script failure mode — no voodoo constants:** Every value (timeouts, limits, thresholds) in a script must have a comment explaining why that value was chosen. Unexplained numeric or string constants are a reliability failure mode — future authors cannot know whether the value was deliberate or arbitrary.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

**For each issue, consider:**

- Is this a knowledge gap (add reference)?
- Is this a reliability gap (add script)?
- Is this a judgment gap (add decision guidance)?
- Is this a scope gap (add boundaries)?

### Observing Navigation Behavior

As you iterate, pay attention to how Claude actually navigates the skill in practice. Watch for these signals:

- **Unexpected exploration paths:** Claude reads files in an order you didn't anticipate — your structure may not be as intuitive as you thought
- **Missed connections:** Claude fails to follow references to important files — your links may need to be more explicit or prominent
- **Overreliance on certain sections:** Claude repeatedly reads the same file — consider whether that content should be in the main SKILL.md instead
- **Ignored content:** Claude never accesses a bundled file — it may be unnecessary or poorly signaled in the main instructions

Iterate based on these observations rather than assumptions. The `name` and `description` fields in frontmatter are particularly critical — Claude uses them when deciding whether to trigger the skill. Make sure they clearly describe what the skill does and when it should be used.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

### The iteration loop

```mermaid
flowchart TD
    I1["Review eval results and user feedback"] --> I2
    I2["Identify failure modes and root causes"] --> I3
    I3["Make targeted changes to SKILL.md,<br>scripts, or references"] --> I4
    I4["Re-run test cases (Step 8)"] --> I5
    I5["Compare with previous iteration"] --> IQ{"Improvement<br>sufficient?"}
    IQ -->|"No — regressions or<br>new failures found"| I2
    IQ -->|"Yes — all tests pass<br>or user satisfied"| Done(["Skill is stable"])
```

## Claude A / Claude B Collaborative Authoring

The most effective skill development loop uses two Claude instances: one to write and refine the skill (Claude A), and a separate fresh instance to test it (Claude B). Claude A understands agent needs; Claude B reveals gaps through real usage.

Claude models understand the skill format and structure natively — you don't need special prompts or a "writing skills" skill. Simply ask Claude to create a skill.

### 7-Step Creation Workflow

1. **Complete a task without a skill:** Work through a problem with Claude A using normal prompting. Notice what context you repeatedly provide.
2. **Identify the reusable pattern:** After completing the task, identify what context would be useful for similar future tasks.
3. **Ask Claude A to create a skill:** "Create a skill that captures the pattern we just used. Include the relevant schemas, naming conventions, and key rules."
4. **Review for conciseness:** Check that Claude A hasn't added unnecessary explanations. Ask: "Remove the explanation about X — Claude already knows that."
5. **Improve information architecture:** Ask Claude A to organize content more effectively: "Move the schema to a separate reference file."
6. **Test on similar tasks:** Use the skill with Claude B (a fresh instance with the skill loaded) on related use cases. Observe whether Claude B finds the right information and applies rules correctly.
7. **Iterate based on observation:** If Claude B struggles or misses something, return to Claude A with specifics: "Claude B forgot to filter by date for Q4 — should we add a section about date filtering patterns?"

### 6-Step Iteration Loop

When improving an existing skill, alternate between:

- **Working with Claude A** — the expert who helps refine the skill
- **Testing with Claude B** — the agent using the skill to perform real work
- **Observing Claude B's behavior** — bringing insights back to Claude A

1. Use the skill in real workflows — give Claude B actual tasks, not test scenarios
2. Observe Claude B's behavior — note where it struggles, succeeds, or makes unexpected choices
3. Return to Claude A for improvements — share the current SKILL.md and describe what you observed
4. Review Claude A's suggestions — reorganize to make rules more prominent, use stronger language ("MUST filter" vs "always filter"), or restructure workflows
5. Apply and test changes — update the skill with Claude A's refinements, then test again with Claude B
6. Repeat based on usage — each iteration improves the skill based on real agent behavior, not assumptions

**Why this approach works:** Claude A understands agent needs, you provide domain expertise, Claude B reveals gaps through real usage, and iterative refinement improves skills based on observed behavior rather than assumptions.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## Advanced: Blind Comparison

For significant skill changes, use blind A/B comparison to avoid confirmation bias. Spawn the **comparator agent** (`@plugin-creator:comparator`) with outputs from both versions. The comparator doesn't know which version is "old" or "new" — it evaluates purely on quality.

Then spawn the **analyzer agent** (`@plugin-creator:analyzer`) to understand WHY the winner won, producing actionable improvement suggestions.

## Step 10: Description Optimization

The description field in SKILL.md frontmatter is the primary mechanism that determines whether Claude invokes a skill. After creating or improving a skill, offer to optimize the description for better triggering accuracy.

### How skill triggering works

Claude sees all skill descriptions in the `<available_skills>` block. When a user message comes in, Claude reads the descriptions and decides which (if any) skills to invoke. The description must contain enough signal for Claude to make the right call — invoke when relevant, skip when not.

A good description balances:

- **Precision**: Doesn't trigger on unrelated requests
- **Recall**: Triggers on all relevant requests
- **Specificity**: Distinguishes this skill from similar ones

### Step 10a: Generate trigger eval queries

Create an eval set with positive (should trigger) and negative (should NOT trigger) queries:

```json
[
  {"query": "Create a new skill for handling PDF files", "should_trigger": true},
  {"query": "How do I rotate a PDF?", "should_trigger": false},
  {"query": "Build a slash command for deployment", "should_trigger": true},
  {"query": "What's the weather today?", "should_trigger": false}
]
```

Aim for 15-20 queries minimum, roughly 60% positive and 40% negative. Include edge cases — queries that are close to the boundary. Query strings must be nonempty and unique, with actual boolean labels. Resolve duplicate or conflicting cases before partitioning; do not merge them after seeing results. Repetitions belong in `runs_per_query`, not duplicate query records.

### Step 10b: Review with user

Present the eval set to the user for review using the HTML template:

1. Read the template from `assets/eval_review.html`
2. Replace the placeholders:
   - `__EVAL_DATA_PLACEHOLDER__` with the JSON array of eval items
   - `__SKILL_NAME_PLACEHOLDER__` with the skill's current description
   - `__SKILL_DESCRIPTION_PLACEHOLDER__` with the skill's current description
3. Write to a temp file and open it
4. The user can edit queries, toggle should-trigger, add/remove entries, then click "Export Eval Set"

This step matters — bad eval queries lead to bad descriptions.

### Step 10c: Run the optimization loop

Tell the user what will run and retain its outputs. Use background execution only when the active harness supplies that capability and a way to retrieve completion.

Save the eval set to the workspace, then run:

```bash
uv run scripts/run_loop.py \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <supported-Claude-model-id> \
  --max-iterations 5 \
  --verbose
```

These scripts use the Claude CLI and Anthropic SDK; select a model that those providers support, not an unrelated harness's session model identifier. Their existence does not require other process-evaluation methods to use this provider or harness.

`run_eval.py` launches each synthetic description sample in a separate disposable project containing one temporary command. It does not copy the caller's project; queries requiring real project files need separately provisioned task evaluations. User-level settings, installed capabilities and authentication remain inherited and are reported as not isolated. This is a synthetic invocation-selection experiment, not clean-room model knowledge measurement or full installed-skill certification.

A positive observation is a matching invocation. A negative requires a successful terminal result and process exit without that invocation. Missing executables, malformed/unfinished streams, timeout, or failure remain `ERROR`; `pass: null` and the `inconclusive` count prevent them from passing negative cases. `valid_runs` is the behavioral denominator; `runs` is attempts. If any requested repetition is invalid, that case and the iteration remain inconclusive. The CLI exits 2 for missing evidence, and `run_eval.py` exits 1 for completed behavioral failures.

The optimizer uses training and candidate-selection partitions. The default 40% holdout is used to select the best eligible candidate, so it is not an untouched final test. Legacy `test_*` output keys retain their names for consumers, with `holdout_role: candidate-selection` and `final_generalization_test: NOT_RUN`. Selection observations are withheld from the description-writing prompt. Duplicate cases or a split with an empty training/selection side are rejected; add cases or deliberately use `--holdout 0` for a training-only experiment.

Repetition counts and iteration/time budgets are experiment settings, not proof of reliability. Incomplete evidence stops the loop without an actionable `best_description`; historical completed results remain visible. A claim about generalization needs separate untouched cases evaluated after candidate selection, when that claim is material.

### Step 10d: Apply the result

Review the selected description against the approved trigger contract and the observed coverage. Never apply a null recommendation, an inconclusive iteration, or a supposedly better score caused by missing data. Selection proposes a candidate rather than granting acceptance; retain required negative cases and supported-environment behavior. Update SKILL.md only after the applicable checks support it, then run `quick_validate.py` to confirm structural validity.

## Reference Files

These plugin agents are available for the eval workflow:

- `@plugin-creator:grader` — Evaluates assertions against outputs
- `@plugin-creator:comparator` — Blind A/B comparison between two outputs
- `@plugin-creator:analyzer` — Analyzes why one version beat another

The `references/` directory has additional documentation:

- `schemas.md` — JSON structures for evals.json, grading.json, etc.
- `../../claude-skills-overview-2026/resources/claude-code-skills-official.md` — Canonical Claude Code skills specification
- `workflows.md` — Workflow design patterns for multi-step skills

The `eval-viewer/` directory contains the interactive eval review viewer:

- `eval-viewer/viewer.html` — Interactive HTML viewer for eval results
- `eval-viewer/generate_review.py` — Generates standalone HTML review from eval data

The `assets/` directory contains templates:

- `assets/eval_review.html` — HTML template for reviewing and editing trigger eval sets
