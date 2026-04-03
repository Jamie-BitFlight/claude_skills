# Context-Fit Complexity: Claim Distillation and Experimental Validation

This document extracts the discrete, testable claims from the Context-Fit Complexity Model and its economic extensions, then designs experiments to validate or refute each one.

## Source Material

The concept combines three threads:

1. **Context-fit complexity equation** — task complexity as a function of knowledge loading, uncertainty resolution, and live context overhead relative to available context
2. **Context-fit spectrum** — zero-overhead execution, single-agent loading zone, knowledge-boundary scale-out
3. **Session economics** — persistent vs fresh sessions, cache amortization, contamination risk

## Claim Inventory

Each claim is numbered for cross-reference in experiment designs.

### C1: Complexity is context-fit, not implementation difficulty

> A task is "complex" not because the implementation is hard, but because the agent must assemble too much project-specific knowledge, manage too many volatile constraints, or absorb too many unresolved unknowns before it can act reliably.

**What this actually says**: Two tasks with identical implementation effort (same LOC, same algorithmic difficulty) will have different failure rates depending on how much external knowledge must be loaded to execute them.

**What it does NOT say**: Implementation difficulty is irrelevant. It says implementation difficulty is not the *primary* driver of agent task failure.

### C2: The three-term equation is sufficient

> Complexity = required non-native knowledge + active uncertainty + live context overhead

**What this claims**: These three terms account for the variance in agent task success. No additional term is needed.

**Skeptical reading**: This could be missing terms. Candidates for a fourth term:
- **Tool reliability** — the agent may have sufficient context but fail because tool calls are flaky
- **Instruction ambiguity** — the prompt may be clear to a human but ambiguous to the model
- **Model capability ceiling** — some tasks exceed what the model can do regardless of context

### C3: Decomposition should follow knowledge boundaries, not code boundaries

> If two steps require the same knowledge payload, combine them. If a step requires a distinct or oversized knowledge payload, isolate it.

**What this claims**: Tasks split along module/file/function boundaries will have worse outcomes than tasks split along "which knowledge is needed" boundaries, all else equal.

### C4: Stable constraints should be encoded; volatile constraints should be discovered dynamically

> Every hardcoded rule has a maintenance cost proportional to how volatile the thing it references is.

**What this claims**: Hardcoding volatile constraints (ones that change frequently) creates more maintenance burden and more breakage than discovering them at runtime. Hardcoding stable constraints (ones that rarely change) is net-positive.

### C5: Progressive disclosure improves agent reliability

> Do not preload all project knowledge. Load only the minimum layer needed for the current step.

**What this claims**: An agent given only the knowledge it needs for the current step will outperform an agent given all knowledge for all steps upfront.

**Skeptical reading**: This could fail when steps have hidden dependencies — loading step 3's knowledge might reveal that step 1's assumptions were wrong. Progressive disclosure could miss cross-cutting concerns.

### C6: Context garbage collection improves agent reliability

> Do not keep raw intermediate artifacts after they have been consumed. Retain only the durable findings needed downstream.

**What this claims**: Removing consumed intermediate context (logs, failed attempts, verbose tool output) improves downstream task quality.

### C7: Unknown unknowns become known unknowns through structured reality contact

> Unknown unknowns become known unknowns when assumptions are forced into contact with something concrete: a checklist, an artifact, an experiment, a reviewer, or a failing execution path.

**What this claims**: Structured enumeration and early execution surface unknowns that introspection alone cannot find.

### C8: Persistent sessions amortize context loading cost

> If several tasks all operate on the same data, instructions, and accumulated working state, a persistent agent can amortize the expensive prompt-load cost across all of them.

**What this claims**: For N related subtasks sharing a large common context prefix, a single persistent session is cheaper (in tokens) than N fresh sessions.

### C9: Context bloat erases the persistent session advantage

> If the agent keeps accumulating irrelevant intermediate text, the reused context becomes large enough that even cheap cached reads add up, and quality may degrade before cost does.

**What this claims**: There is a crossover point where accumulated stale context in a persistent session degrades quality enough to negate the cost savings.

### C10: The context-fit spectrum has three distinct regions

> Zero-overhead execution, single-agent loading zone, knowledge-boundary scale-out.

**What this claims**: These three regions produce qualitatively different failure modes and optimal strategies. Tasks misclassified between regions perform worse than correctly classified tasks.

### C11: A sparse-plan + auditor loop identifies minimum viable seeded knowledge

> Give the lightly seeded agent a real task. Audit which steps were speculative. Extract the minimal missing knowledge units. Re-seed and re-run.

**What this claims**: Iterative knowledge discovery via speculation detection converges to a minimal effective knowledge set faster than upfront comprehensive knowledge loading.

---

## Experiment Designs

### Experiment 1: Context-fit vs implementation difficulty (Tests C1)

**Hypothesis**: Task success rate correlates more strongly with context-fit cost than with implementation complexity.

**Method**:

1. Select 20 tasks from this repository's backlog or commit history
2. For each task, independently score:
   - **Implementation complexity** (LOC changed, cyclomatic complexity delta, number of files touched)
   - **Context-fit cost** (number of files agent must read, number of unresolved prerequisites at task start, number of distinct knowledge domains required)
3. Have 3 agents attempt each task (fresh session per attempt, identical prompt)
4. Record: success/failure, number of tool calls, number of errors, final correctness

**Analysis**: Compute rank correlation (Spearman's rho) between success rate and each predictor. If context-fit cost correlates more strongly than implementation complexity, C1 is supported.

**Controls**:
- Same model, same temperature, same tool set
- Randomize task order to avoid learning effects
- Blind the scorer to agent outcomes when rating complexity and context-fit

**Falsification**: If implementation complexity is the stronger predictor, C1 is refuted.

---

### Experiment 2: Three-term sufficiency (Tests C2)

**Hypothesis**: The three terms (knowledge, uncertainty, overhead) explain >80% of variance in agent task success.

**Method**:

1. Use the same 20 tasks from Experiment 1
2. For each task, score each of the three terms on a 1-5 scale:
   - **Knowledge load**: how many distinct files/docs must be read (1 = 0-2 files, 5 = 10+ files)
   - **Uncertainty**: how many prerequisites are unverified at task start (1 = all verified, 5 = most unknown)
   - **Overhead**: how much transient context accumulates during execution (1 = minimal, 5 = extensive logs/retries)
3. Also score candidate fourth terms:
   - **Tool reliability**: how many tool calls fail or return unexpected results
   - **Instruction ambiguity**: rated by a second human reading only the prompt
   - **Model capability**: rated by difficulty of the core algorithm/logic
4. Run regression: success_rate ~ knowledge + uncertainty + overhead + (optional fourth terms)

**Analysis**: Compare R-squared of three-term model vs four-term models. If three terms explain >80% and adding a fourth term does not improve R-squared by more than 5 percentage points, C2 is supported.

**Falsification**: If a fourth term adds >10pp to R-squared, C2 is incomplete.

---

### Experiment 3: Knowledge-boundary vs code-boundary decomposition (Tests C3)

**Hypothesis**: Tasks decomposed at knowledge boundaries have higher completion rates than tasks decomposed at code boundaries.

**Method**:

1. Select 5 medium-complexity features (each requiring 3-5 subtasks)
2. For each feature, create two decompositions:
   - **Code-boundary**: split by module/file/function — each subtask modifies one module
   - **Knowledge-boundary**: split by required knowledge payload — each subtask uses one distinct set of reference material
3. Execute both decompositions (10 task sets total, 5 per condition)
4. Each subtask is executed by a fresh agent with identical model and tools
5. Record: subtask success rate, total tokens consumed, number of context-loading tool calls per subtask

**Analysis**: Compare mean success rate and mean token cost between conditions. Knowledge-boundary decomposition should show higher success rate and/or lower token cost.

**Controls**:
- Same features, same total scope
- Randomize execution order
- Same agent model and configuration

**Falsification**: If code-boundary decomposition achieves equal or higher success rates, C3 is not supported for this codebase.

**Confound to watch**: Knowledge boundaries and code boundaries may overlap significantly in well-designed codebases. If overlap >80%, the experiment may not differentiate the conditions.

---

### Experiment 4: Volatile vs stable constraint encoding (Tests C4)

**Hypothesis**: Volatile constraints that are hardcoded cause more maintenance failures than volatile constraints that are discovered dynamically.

**Method**:

1. Audit the repository's CLAUDE.md, SKILL.md files, and agent prompts
2. Classify each encoded constraint as:
   - **Stable**: has not changed in the last 3 months (check git log)
   - **Volatile**: has changed at least twice in the last 3 months
3. For each volatile constraint, check:
   - How many times was it updated? (git log --follow)
   - How many times did an agent produce incorrect output because the constraint was stale? (search session transcripts or commit messages mentioning "stale", "outdated", "wrong constraint")
4. Compare failure rate: volatile-hardcoded vs stable-hardcoded constraints

**Analysis**: If volatile-hardcoded constraints have a higher associated failure rate (stale reference leading to incorrect agent behavior), C4 is supported.

**Data source**: This repository's git history provides a natural dataset. The `.claude/` directory has been actively maintained, providing change frequency data.

**Falsification**: If volatile constraints do not cause more failures than stable ones, either the claim is wrong or the maintenance process is good enough to keep volatile constraints current.

---

### Experiment 5: Progressive disclosure vs full preload (Tests C5)

**Hypothesis**: Agents given minimal per-step context outperform agents given full task context upfront.

**Method**:

1. Select 5 multi-step tasks (each with 3+ sequential steps)
2. For each task, run two conditions:
   - **Full preload**: agent receives all reference files, all context, all constraints in the initial prompt
   - **Progressive**: agent receives only the context needed for step 1; additional context is provided only when the agent reaches subsequent steps
3. Each condition runs 3 times (total: 30 runs)
4. Record: final correctness, tokens consumed, number of hallucinated claims, number of "lost" instructions (instructions present in prompt but not followed)

**Analysis**: Compare correctness and instruction-following rate between conditions.

**Expected finding for C5**: Progressive disclosure leads to fewer lost instructions and fewer hallucinations.

**Expected finding against C5**: Full preload leads to better cross-cutting awareness (the agent catches conflicts between steps that progressive disclosure would miss).

**Falsification**: If full preload achieves equal or higher correctness AND equal or lower hallucination rate, C5 is not supported.

---

### Experiment 6: Context garbage collection impact (Tests C6)

**Hypothesis**: Removing consumed intermediate context improves downstream task quality.

**Method**:

1. Select 5 tasks that produce significant intermediate output (test runs, search results, build logs)
2. For each task, run two conditions:
   - **Accumulated**: all intermediate output remains in context throughout the session
   - **Collected**: after each step, intermediate output is replaced with a one-paragraph summary of findings
3. Each condition runs 3 times
4. Record: correctness of final output, number of references to stale/irrelevant intermediate data, total tokens at task completion

**Analysis**: Compare correctness and stale-reference count between conditions.

**Falsification**: If accumulated context does not degrade downstream quality (no increase in stale references, no decrease in correctness), C6 is not supported. This would suggest models are better at ignoring irrelevant context than the claim assumes.

---

### Experiment 7: Structured reality contact for unknown discovery (Tests C7)

**Hypothesis**: Structured prerequisite enumeration surfaces unknowns that pure planning does not.

**Method**:

1. Select 5 tasks where the initial plan turned out to be wrong (from commit history — the first attempt failed and a different approach succeeded)
2. For each task, run two conditions:
   - **Plan-only**: agent plans the task, then executes
   - **Plan + enumerate + validate**: agent plans, then enumerates all assumptions as a checklist, then validates each assumption against the codebase before executing
3. Record: whether the agent discovers the blocking issue before or during execution, number of wasted tool calls on wrong approaches

**Analysis**: If plan+enumerate discovers the blocker before execution more often than plan-only, C7 is supported.

**Falsification**: If both conditions discover the blocker at the same point (during execution failure), structured enumeration adds overhead without benefit.

---

### Experiment 8: Persistent vs fresh session economics (Tests C8, C9)

**Hypothesis**: For tasks sharing >50% context, a persistent session is cheaper. The advantage degrades as context accumulates.

**Method**:

1. Select a set of 5 related subtasks that share a common context (same module, same reference files)
2. Run three conditions:
   - **Fresh**: each subtask in a new session (context loaded 5 times)
   - **Persistent-clean**: all 5 subtasks in one session, with context compaction between tasks (summaries replace raw output)
   - **Persistent-dirty**: all 5 subtasks in one session, no compaction (all intermediate output accumulates)
3. Record: total tokens (input + output), wall-clock time, correctness of each subtask

**Analysis**:
- Fresh vs persistent-clean: compare total token cost. C8 predicts persistent-clean is cheaper.
- Persistent-clean vs persistent-dirty: compare correctness of later subtasks. C9 predicts persistent-dirty degrades.

**Falsification (C8)**: If fresh sessions are cheaper or equivalent despite shared context, the cache amortization claim is wrong — possibly because modern API caching already handles prefix reuse transparently.

**Falsification (C9)**: If persistent-dirty maintains quality across all 5 subtasks, context bloat is not a real problem at this scale.

---

### Experiment 9: Context-fit spectrum classification (Tests C10)

**Hypothesis**: Tasks in different spectrum regions exhibit qualitatively different failure modes.

**Method**:

1. Classify 30 tasks into three regions:
   - **Zero-overhead**: all inputs already present, no external reads needed (e.g., P1_ADD-style validated input tasks)
   - **Single-agent loading**: requires some file reads but fits in one agent's context
   - **Knowledge-boundary scale-out**: requires multiple distinct knowledge domains that exceed one agent's effective window
2. For each task, run with two strategies:
   - **Single-agent**: one agent handles the entire task
   - **Multi-agent**: task is split across parallel agents
3. Record: success rate, token cost, failure mode (if failed: was it knowledge-related, tool-related, or reasoning-related?)

**Analysis**:
- Zero-overhead tasks should succeed with single-agent and fail to benefit from multi-agent (overhead of coordination exceeds benefit)
- Loading-zone tasks should succeed with single-agent most of the time
- Scale-out tasks should fail with single-agent (context exhaustion or knowledge gaps) and succeed with multi-agent

**Falsification**: If single-agent handles scale-out tasks equally well, the spectrum regions do not produce distinct failure modes — context windows are large enough that the scale-out region does not exist at current model sizes.

---

### Experiment 10: Iterative knowledge discovery via speculation detection (Tests C11)

**Hypothesis**: A sparse-plan + auditor loop converges to effective task completion with less total seeded knowledge than upfront comprehensive loading.

**Method**:

1. Select 3 domain-specific tasks requiring specialized knowledge (e.g., FastMCP server patterns, SAM task file format, backlog lifecycle rules)
2. For each task, run two conditions:
   - **Upfront**: load all potentially relevant skills, reference docs, and context before the agent starts
   - **Iterative**: start with minimal context; after each agent attempt, audit which claims were speculative (not grounded in loaded context); load only the knowledge that would have grounded those specific claims; re-run
3. Track per iteration: number of speculative claims, total context loaded (tokens), task correctness
4. Stop iterative condition when speculative claim count reaches 0 or correctness matches upfront

**Analysis**:
- Compare total tokens loaded at convergence (iterative) vs total tokens loaded upfront
- If iterative loads fewer tokens and achieves equal correctness, C11 is supported
- Track convergence speed: how many iterations to reach equivalent quality?

**Falsification**: If iterative requires more total tokens (due to repeated runs) or never converges to upfront quality, the overhead of the auditor loop exceeds the savings from selective loading.

---

## Experiment Execution Notes

### Practical constraints

- **Model variance**: Run each condition at least 3 times to account for model non-determinism. Report mean and range.
- **Blind scoring**: Where human scoring is required (instruction ambiguity, correctness), use a second scorer who does not know the condition.
- **Natural data preferred**: Use real tasks from this repository's history rather than synthetic tasks. Synthetic tasks risk being designed to confirm the hypothesis.
- **Cost tracking**: Record API token counts (input, output, cached) per run. The economics claims (C8, C9) require actual cost data, not estimates.

### Suggested execution order

```text
Experiment 4 (constraint audit)     — requires no agent runs, pure git analysis
Experiment 1 (context-fit vs impl)  — establishes the fundamental correlation
Experiment 2 (three-term sufficiency) — reuses Experiment 1 data
Experiment 5 (progressive disclosure) — directly actionable result
Experiment 6 (garbage collection)    — directly actionable result
Experiment 3 (decomposition strategy) — requires feature-level task design
Experiment 8 (session economics)     — requires controlled multi-task sessions
Experiment 7 (reality contact)       — requires historical task selection
Experiment 9 (spectrum regions)      — requires 30-task classification
Experiment 10 (iterative discovery)  — most complex setup, run last
```

Experiment 4 is the cheapest starting point — it uses only git history and produces results without any agent execution.

### What would change if claims are refuted

| Claim refuted | Implication for the model |
|---|---|
| C1 | Implementation difficulty matters more than context-fit. The equation needs a fourth term or a reweighting. |
| C2 | The equation is incomplete. Identify which fourth term has the most explanatory power and add it. |
| C3 | Code boundaries are sufficient decomposition heuristics. Knowledge-boundary analysis is unnecessary overhead. |
| C4 | Constraint volatility does not predict maintenance cost. Encode all constraints or none. |
| C5 | Full context is not harmful; models handle large contexts well enough. Progressive disclosure adds complexity without benefit. |
| C6 | Models ignore irrelevant context effectively. Garbage collection is unnecessary engineering. |
| C7 | Structured enumeration does not surface unknowns earlier than execution failure. Skip the checklist step. |
| C8 | API-level caching already handles prefix reuse. Session persistence is not an optimization lever. |
| C9 | Context bloat is not a real degradation factor at current context window sizes. |
| C10 | The spectrum is continuous, not regionalized. A single strategy works across all task sizes. |
| C11 | Upfront loading is more efficient than iterative discovery. The auditor loop costs more than it saves. |

---

## Measurement Protocol

All queries verified against live session data at
`~/.claude/projects/-home-ubuntulinuxqa2-repos-claude-skills/*.jsonl`
using the `kaizen-duckdb` MCP `execute_query` tool (2026-03-29).

Replace `PATH` in all queries with the absolute project JSONL glob path.
Project key encoding: replace all `/` in the absolute project path with `-`.
Example: `/home/ubuntulinuxqa2/repos/claude_skills` →
`/home/ubuntulinuxqa2/.claude/projects/-home-ubuntulinuxqa2-repos-claude_skills/*.jsonl`

### Schema notes (verified)

- `type`, `sessionId`, `timestamp`, `gitBranch` — direct VARCHAR columns
- `message.usage.input_tokens`, `message.usage.cache_read_input_tokens`,
  `message.usage.output_tokens` — STRUCT dot access, no JSON extraction needed
- `message.content` — JSON column; tool calls inside require
  `unnest(from_json(message.content, '["json"]'))` to iterate
- No `result` type records in main session files; session totals are computed
  by summing `assistant` records
- User message text is in `message.content::VARCHAR`

---

### M1 — Session labeling by timestamp (used by all experiments)

Identifies session start time and branch for pre/post cohort splitting.
Label sessions as pre/post by comparing `session_start` against the git commit
timestamp of the instruction change under test (`git log --follow -1 --format="%aI" <file>`).

```sql
SELECT
  sessionId,
  MIN(timestamp) AS session_start,
  gitBranch
FROM read_ndjson_auto('PATH')
WHERE timestamp IS NOT NULL
GROUP BY sessionId, gitBranch
ORDER BY session_start DESC
```

---

### M2 — Read calls before first write per session (Experiments 1, 2, 3, 5)

Measures context acquisition load: how many Read/Glob/Grep calls occur before
the first Write or Edit in a session. Used as the proxy for "knowledge payload loaded."

```sql
WITH tool_sequence AS (
  SELECT
    sessionId,
    timestamp,
    json_extract_string(tool_item, '$.name') AS tool_name,
    ROW_NUMBER() OVER (PARTITION BY sessionId ORDER BY timestamp) AS seq
  FROM read_ndjson_auto('PATH'),
    LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
  WHERE type = 'assistant'
    AND json_extract_string(tool_item, '$.type') = 'tool_use'
    AND json_extract_string(tool_item, '$.name')
        IN ('Read', 'Write', 'Edit', 'Glob', 'Grep', 'Bash')
),
first_write AS (
  SELECT sessionId, MIN(seq) AS first_write_seq
  FROM tool_sequence
  WHERE tool_name IN ('Write', 'Edit')
  GROUP BY sessionId
)
SELECT
  t.sessionId,
  COUNT(*) AS reads_before_first_write,
  f.first_write_seq AS first_write_position
FROM tool_sequence t
JOIN first_write f ON t.sessionId = f.sessionId
WHERE t.tool_name IN ('Read', 'Glob', 'Grep')
  AND t.seq < f.first_write_seq
GROUP BY t.sessionId, f.first_write_seq
ORDER BY reads_before_first_write DESC
```

---

### M3 — Token cost per session (Experiments 2, 3, 8, 9)

Sums token usage across all assistant turns in a session.
`cache_read` tokens are the amortized context reuse signal for C8/C9.

```sql
SELECT
  sessionId,
  SUM(message.usage.input_tokens)             AS total_input,
  SUM(message.usage.cache_read_input_tokens)  AS total_cache_read,
  SUM(message.usage.output_tokens)            AS total_output,
  COUNT(*)                                    AS turns
FROM read_ndjson_auto('PATH')
WHERE type = 'assistant'
  AND message.usage.input_tokens IS NOT NULL
GROUP BY sessionId
ORDER BY turns DESC
```

---

### M4 — User correction and denial signals (Experiments 1, 5, 6, 7)

Detects user corrections and tool denials. These are post-failure signals:
the user observed non-compliant or incorrect behavior and acted.

```sql
SELECT
  sessionId,
  timestamp,
  CASE
    WHEN message.content::VARCHAR LIKE '%Request interrupted by user for tool use%'
      THEN 'tool_denial'
    WHEN message.content::VARCHAR LIKE '%Request interrupted by user%'
      THEN 'interrupt'
    WHEN message.content::VARCHAR LIKE '%User denied%'
      THEN 'denied'
  END AS signal_type
FROM read_ndjson_auto('PATH')
WHERE type = 'user'
  AND message.content IS NOT NULL
  AND (
    message.content::VARCHAR LIKE '%Request interrupted by user%'
    OR message.content::VARCHAR LIKE '%User denied%'
  )
ORDER BY sessionId, timestamp
```

---

### M5 — Bash tool misuse rate (Experiments 1, 4)

Identifies Bash calls that violate the "use built-in tools" instruction.
Each violation type maps to a specific instruction in CLAUDE.md.

```sql
WITH bash_calls AS (
  SELECT
    sessionId,
    timestamp,
    json_extract_string(tool_item, '$.input.command') AS command
  FROM read_ndjson_auto('PATH'),
    LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
  WHERE type = 'assistant'
    AND json_extract_string(tool_item, '$.name') = 'Bash'
    AND json_extract_string(tool_item, '$.type') = 'tool_use'
)
SELECT
  sessionId,
  command,
  CASE
    WHEN regexp_matches(command, '^\s*ls\b')              THEN 'use_glob'
    WHEN regexp_matches(command, '\bgrep\b')              THEN 'use_grep'
    WHEN regexp_matches(command, '\bfind\b.*-name')       THEN 'use_glob'
    WHEN regexp_matches(command, '\bcat\b\s+\S+\.\w+')   THEN 'use_read'
    WHEN regexp_matches(command, '\bhead\b|\btail\b')     THEN 'use_read'
    WHEN regexp_matches(command, '\bsed\b|\bawk\b')       THEN 'use_edit'
  END AS violation_type
FROM bash_calls
WHERE command IS NOT NULL
  AND violation_type IS NOT NULL
ORDER BY sessionId, timestamp
```

---

### M6 — Tool call sequence per session (Experiments 3, 9, 10)

Produces the full ordered tool sequence for a session.
Used to reconstruct whether agents followed prescribed workflow order,
and to compare decomposition strategies by tool pattern.

```sql
SELECT
  sessionId,
  timestamp,
  json_extract_string(tool_item, '$.name')         AS tool_name,
  json_extract_string(tool_item, '$.input.file_path') AS file_path,
  json_extract_string(tool_item, '$.input.command')   AS command,
  ROW_NUMBER() OVER (PARTITION BY sessionId ORDER BY timestamp) AS step
FROM read_ndjson_auto('PATH'),
  LATERAL (SELECT unnest(from_json(message.content, '["json"]')) AS tool_item)
WHERE type = 'assistant'
  AND json_extract_string(tool_item, '$.type') = 'tool_use'
ORDER BY sessionId, step
```

---

### How to tag sessions to conditions

Session logs do not contain experiment condition labels.
Two approaches to assign sessions to conditions:

**Timestamp split (pre/post instruction change):**
1. Run `git log --follow -1 --format="%aI" .claude/CLAUDE.md` (or the relevant file)
   to get the exact commit timestamp of the instruction change
2. Use M1 to get `session_start` per session
3. Sessions with `session_start < commit_timestamp` are the pre-instruction cohort;
   sessions with `session_start >= commit_timestamp` are the post-instruction cohort

**Explicit tagging (for forward experiments):**
Include a recognizable tag in the first user prompt of each experimental session,
e.g. `[EXP:C5-progressive-2026-04-01]`. Retrieve it with:

```sql
SELECT DISTINCT sessionId
FROM read_ndjson_auto('PATH')
WHERE type = 'user'
  AND message.content::VARCHAR LIKE '%[EXP:C5-progressive%'
```

Explicit tagging is the only reliable method when conditions are applied within
the same time window. Timestamp split only works when conditions are separated
in time (e.g., before and after a CLAUDE.md change).

---

### Experiment-to-metric mapping

| Experiment | Metrics needed | Query(s) |
|---|---|---|
| 1 (context-fit vs impl difficulty) | reads_before_write, correction count | M1, M2, M4 |
| 2 (three-term sufficiency) | reads_before_write, correction count, turn count | M1, M2, M4 |
| 3 (knowledge vs code boundaries) | reads_before_write, token cost | M1, M2, M3 |
| 4 (volatile constraint cost) | bash misuse rate, git log | M1, M5 |
| 5 (progressive disclosure) | token cost, correction count by cohort | M1, M3, M4 |
| 6 (garbage collection) | token growth across turns, correction count | M1, M3, M4 |
| 7 (structured reality contact) | tool sequence (when blocking issue hit) | M1, M6 |
| 8 (session economics) | cache_read vs input token ratio | M1, M3 |
| 9 (spectrum regions) | token cost, tool sequence | M1, M3, M6 |
| 10 (iterative discovery) | token cost across iterations | M1, M3 |

---

## Relationship to Existing Artifacts

- Codified model: [context-fit-complexity.md](./sdlc-layers/layer-0/context-fit-complexity.md)
- RT-ICA (uncertainty resolution method): `/dh:planner-rt-ica`
- Orchestrator discipline (context window management): `.claude/rules/orchestrator-discipline`
- SAM pipeline (stage boundaries): [sam-pipeline.md](./sdlc-layers/layer-0/sam-pipeline.md)
