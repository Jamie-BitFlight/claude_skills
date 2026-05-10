# Improvement Proposals: brooks-lint

**Research entry**: ./research/coding-agents/brooks-lint.md
**Generated**: 2026-05-10
**Patterns assessed**: 8
**Backlog items created**: 6 (issues: #2248, #2250, #2251, #2252, #2253, #2254)
**Deferred (low/medium confidence)**: 2
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Adopt Iron Law structured diagnosis chain (Symptom → Source → Consequence → Remedy) for every code-review finding

**Source pattern**: README.md lines 95–99, common.md lines 6–14 — "Every finding follows: Symptom → Source → Consequence → Remedy" where Source cites a named principle (e.g., "Fowler — Refactoring — Divergent Change"). Benchmark shows 100% structured findings with citations vs. 0% for ungrounded LLM review.
**Local system**: plugins/development-harness/agents/code-reviewer.md
**Confidence**: High
**Impact**: High
**Backlog**: #2248 created

### Current state

`plugins/development-harness/agents/code-reviewer.md` lines 200–211 specify the Output Format for findings as:

```text
- **[SECURITY|CORRECTNESS|TESTS|CONTRACT|NAMING|ERROR-HANDLING|PERFORMANCE]** `{file}:{line}` — {description} — {specific fix required}
```

Findings include a dimension tag, a file:line reference, a description, and a fix. They do NOT include:

- A "Source" field naming the principle, book, or rule that identifies the pattern
- A "Consequence" field stating why this matters (regression surface, business impact, maintenance risk)
- A consistent four-part structure that distinguishes the symptom from its causal source

The seven `code-review-{stack}` skills (e.g., `code-review-python/SKILL.md`) list rules as flat bullet points without the structured chain — there is no template requiring contributors to express each rule in Symptom/Source/Consequence/Remedy form.

### Target state

`plugins/development-harness/agents/code-reviewer.md` Output Format requires every finding to use the four-part structure:

```text
- **[DIMENSION]** `{file}:{line}`
  - **Symptom**: {observed pattern}
  - **Source**: {principle name + rule reference, e.g., "code-review-python — bare except is blocking"}
  - **Consequence**: {regression surface, business impact, or maintainability risk}
  - **Remedy**: {concrete actionable fix}
```

A new `plugins/development-harness/skills/code-review-shared/SKILL.md` (see Improvement 2) defines the four-part chain as the canonical finding format, and each `code-review-{stack}` skill rule includes a Source identifier so the agent can cite it.

### Measurable signal

Run the code-reviewer agent against a known-bad sample. The artifact registered as `codebase-analysis` contains, for at least one finding:

```text
grep -E "Symptom:|Source:|Consequence:|Remedy:" {artifact_content}
```

returns 4 distinct lines per finding. The agent prompt at `plugins/development-harness/agents/code-reviewer.md` contains a section titled "Iron Law" or "Four-Part Finding Format" that names all four required fields explicitly.

---

## Improvement 2: Add shared `_shared/` framework directory for code-review skills (Iron Law, severity table, report template, source-coverage matrix)

**Source pattern**: README.md lines 388–396, CLAUDE.md lines 18–19, 27–32 — `skills/_shared/` contains `common.md` (Iron Law, report template, project config parsing, Health Score algorithm), `decay-risks.md` (R1–R6 diagnostic criteria), `source-coverage.md` (12-book coverage matrix and tradeoff discipline), `remedy-guide.md`. All six brooks-lint analysis skills load this shared framework before mode-specific guides.
**Local system**: plugins/development-harness/skills/code-review-{python,typescript,nodejs,web,cli,llm,claude-skills}/
**Confidence**: High
**Impact**: High
**Backlog**: #2250 created

### Current state

The seven local code-review skills (`code-review-python`, `code-review-typescript`, `code-review-nodejs`, `code-review-web`, `code-review-cli`, `code-review-llm`, `code-review-claude-skills`) each contain a single `SKILL.md` with stack-specific rules (`ls plugins/development-harness/skills/code-review-*/` returns only `SKILL.md` for each). There is no shared file defining:

- The severity tier table (Critical / Warning / Suggestion) — currently inferred per-stack
- The standard report template — defined inline in `agents/code-reviewer.md` Output Format only, not loaded by skills
- The "what not to flag" guards (false-positive avoidance discipline)
- A book/principle coverage matrix that the cited Source field draws from

Each stack skill restates the patterns differently. There is no `code-review-shared` skill or `_shared/` directory under `skills/` that the per-stack skills can reference.

### Target state

A new skill `plugins/development-harness/skills/code-review-shared/SKILL.md` exists. It contains:

- **Iron Law** — the four-part Symptom/Source/Consequence/Remedy format
- **Severity tiers** — table mapping severity labels (Critical/Warning/Suggestion) to deductions and PR-block behaviour
- **Report template** — the canonical markdown structure for a `codebase-analysis` artifact
- **What Not To Flag** — guards against common false-positive patterns
- **Source registry** — a `references/source-registry.md` listing every named principle that any rule cites (named after `source-coverage.md` in brooks-lint)

Each `code-review-{stack}` SKILL.md begins with: `Load /dh:code-review-shared first.` Each stack-specific rule is rewritten to reference a Source ID from the registry.

### Measurable signal

```bash
ls plugins/development-harness/skills/code-review-shared/
# returns: SKILL.md, references/

ls plugins/development-harness/skills/code-review-shared/references/
# returns: source-registry.md (and other shared references)

grep -l "Load /dh:code-review-shared" plugins/development-harness/skills/code-review-*/SKILL.md
# returns one line per stack-specific code-review skill
```

The `agents/code-reviewer.md` Step 6 ("Apply Stack-Specific Rules") instruction is updated to load `code-review-shared` first, then the matching `code-review-{stack}`.

---

## Improvement 3: Add eval/benchmark suite for code-review skills with structured pass/fail scenarios

**Source pattern**: README.md lines 153–166, AGENTS.md line 31, CLAUDE.md lines 36–41 — `evals/evals.json` contains 49 benchmark scenarios covering R1–R6 production risks, T1–T6 test risks, false-positive guards, and tradeoff edge cases. `run-evals.mjs` runs structural validation; `run-evals-live.mjs` runs live AI evaluation. Benchmark accuracy: 94% pass rate for brooks-lint vs. 16% for plain Claude. The eval suite is a forcing function for finding quality.
**Local system**: plugins/development-harness/skills/code-review-{python,typescript,nodejs,web,cli,llm,claude-skills}/, plugins/development-harness/agents/code-reviewer.md
**Confidence**: High
**Impact**: High
**Backlog**: #2251 created

### Current state

```bash
find plugins/development-harness -name "evals.json" -o -name "evals" -type d
```

returns nothing inside the development-harness plugin. The `code-reviewer` agent and the seven per-stack skills have no test fixtures, no expected-output assertions, and no false-positive guard tests. There is no way to detect whether a change to `code-review-python/SKILL.md` rules makes the code-reviewer more or less accurate. Compare with `.agents/skills/copy-editing/evals/evals.json` which already follows the eval pattern (id, prompt, expected_output, assertions, files) — the precedent exists locally for one skill but not for code-review.

The `agents/code-reviewer.md` agent has no regression test even though it is the central S6 Forensic Review enforcer for the entire SAM pipeline.

### Target state

`plugins/development-harness/skills/code-review-shared/evals/evals.json` exists, modelled after `.agents/skills/copy-editing/evals/evals.json`. Each entry has:

- `id` — sequential identifier
- `prompt` — code snippet or directory under review
- `expected_findings` — list of finding dimensions (e.g., `["error-handling.bare-except", "naming.magic-number"]`) the reviewer MUST surface
- `false_positive_guards` — list of patterns the reviewer MUST NOT flag (e.g., a `try: ... except Exception: raise` block)
- `assertions` — verifiable claims about the produced report (e.g., "Iron Law four-part structure present", "Source field cites a named principle")

A runner script `plugins/development-harness/scripts/run_code_review_evals.py` invokes the `code-reviewer` agent against each scenario and computes pass/fail. Initial scenario count: at least 10, covering each of the 7 universal quality dimensions plus at least one false-positive guard and one tradeoff scenario.

### Measurable signal

```bash
test -f plugins/development-harness/skills/code-review-shared/evals/evals.json && \
  uv run python -c "import json; d = json.load(open('plugins/development-harness/skills/code-review-shared/evals/evals.json')); assert len(d['evals']) >= 10"
```

exits 0. Running `uv run plugins/development-harness/scripts/run_code_review_evals.py` reports a baseline pass rate that can be tracked across changes.

---

## Improvement 4: Auto-scope detection for code-review when no files are provided

**Source pattern**: common.md lines 81–94 — Each brooks-lint mode auto-detects scope when files are not provided: PR Review uses `git diff --cached` → `git diff` → `git diff main...HEAD` → ask user. Reports always state detected scope explicitly.
**Local system**: plugins/development-harness/agents/code-reviewer.md Step 2
**Confidence**: High
**Impact**: Medium
**Backlog**: #2252 created

### Current state

`plugins/development-harness/agents/code-reviewer.md` Step 2 ("Identify Files Under Review") instructs the agent: "Use `Glob` and `Grep` to identify the files changed or added by this task. Patterns to search: source files mentioned in the task body or acceptance criteria, test files corresponding to changed source, configuration or schema files touched by the task. If no files can be identified, return STATUS: BLOCKED with a request for explicit file paths."

There is no fallback chain that consults git state. If the task body does not list files explicitly, the agent returns BLOCKED rather than examining `git diff --cached`, `git diff`, or `git diff origin/main...HEAD`. This forces every dispatch to pre-discover files — duplicating work and creating an explicit failure mode for tasks where the files-changed list is implied by the branch.

### Target state

Step 2 of `agents/code-reviewer.md` updates to a fallback chain modeled on common.md lines 81–94:

```text
1. Files explicit in delegation prompt? → use those
2. Else: git diff --cached → if non-empty, use those files
3. Else: git diff → if non-empty, use those files
4. Else: git diff origin/main...HEAD → if non-empty, use those files
5. Else: STATUS: BLOCKED with request for explicit file paths
```

The agent's STATUS output includes a "Scope" line stating which fallback level was used (`Scope: explicit | staged | working | branch | blocked`) so the orchestrator can verify the scope was correct.

### Measurable signal

`plugins/development-harness/agents/code-reviewer.md` Step 2 contains the four-step fallback chain by name. Output Format includes a "Scope" line in the STATUS block. Running the agent on a task with no file list and a non-empty `git diff --cached` produces a successful review citing the staged files in the artifact and a `Scope: staged` STATUS line.

---

## Improvement 5: Add quantified Health Score (0–100) with severity-weighted deductions to code-review verdict

**Source pattern**: common.md lines 14–15, AGENTS.md lines 15–16 — Base score 100; deductions per finding: Critical −15, Warning −5, Suggestion −1; floor 0. Score is reported with each review and tracked over time via `.brooks-lint-history.json`. Allows fail-on-threshold checks (`fail-below: 70`) and trend analysis.
**Local system**: plugins/development-harness/agents/code-reviewer.md Step 7
**Confidence**: High
**Impact**: Medium
**Backlog**: #2253 created

### Current state

`plugins/development-harness/agents/code-reviewer.md` Step 7 ("Compute Verdict") produces a ternary verdict — `PASS`, `NEEDS-WORK`, or `FAIL`. There is no quantified score, no severity weighting, no historical comparison. Two reviews that both return `NEEDS-WORK` are indistinguishable, even if one has 1 blocking finding and the other has 12. The orchestrator (forensic-review skill) cannot reason about whether code is improving or degrading across iterations of the same task.

### Target state

Step 7 produces both a verdict AND a Health Score:

```text
Verdict: PASS | NEEDS-WORK | FAIL
Health Score: 0–100
  Calculation: 100 - sum(severity_weights)
    Critical: -15
    Warning: -5
    Suggestion: -1
    Floor: 0
  Severity per dimension defined in code-review-shared/references/severity.md
```

The STATUS output includes `Health Score: NN/100`. The artifact registered as `codebase-analysis` includes a `## Health Score` section with the score and the per-finding deduction breakdown.

### Measurable signal

`plugins/development-harness/agents/code-reviewer.md` Output Format Summary section contains a `Health Score:` field. STATUS block contains a `Health Score:` line. Run the agent on a sample with 2 critical and 1 warning finding — the artifact reports `Health Score: 65/100` (100 − 15 − 15 − 5).

---

## Improvement 6: Repository consistency validation script (manifest version sync, skill structure inventory, README badge presence)

**Source pattern**: CLAUDE.md lines 36–41 — `validate-repo.mjs` checks manifest sync, README badge, CHANGELOG, source inventory, skill structure as a single repo health invariant. Runs in CI and locally.
**Local system**: existing pre-commit hooks in `.pre-commit-config.yaml`, scripts/, skilllint
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: a partial equivalent exists (skilllint validates skill structure; pre-commit hook auto-bumps `plugin.json`/`marketplace.json` versions per CLAUDE.md "Automatic version bumping"). Would need to enumerate which specific brooks-lint checks are missing locally before the gap can be expressed concretely. To raise confidence, run `find plugins/ -name "plugin.json" -exec jq .version {} \;` and `cat .claude-plugin/marketplace.json | jq '.plugins[] | {name, version}'` and compare to confirm whether marketplace.json versions track per-plugin versions today; verify whether README has stale links by running a link-check; verify whether CHANGELOG entries are required per plugin.

### Current state

Pre-commit auto-bumps `plugin.json` and `marketplace.json` versions when plugin files change (per `.claude/CLAUDE.md` "Automatic version bumping"). `skilllint` validates skill structure (per `.claude/rules/frontmatter-requirements.md`). No single script aggregates all repo-wide invariants (manifest version sync across plugins, source inventory, README badge presence, CHANGELOG entry per release) into one validation pass.

### Target state

To be defined after running the inventory commands in the confidence note. Likely shape: `scripts/validate_repo.py` runs all invariants and exits non-zero if any fail. Pre-commit hook calls it.

### Measurable signal

To be defined.

---

## Improvement 7: Per-project code-review configuration overrides (`.code-review.yaml`)

**Source pattern**: README.md lines 340–364, common.md lines 21–70 — `.brooks-lint.yaml` allows per-project disable, severity override, ignore globs, and focus list. Customizes review behavior without modifying the skills themselves.
**Local system**: plugins/development-harness/skills/code-review-shared/ (proposed) and code-review-{stack}/ skills
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: relates to existing tracked work. Issue #2105 (Configurable gate composition for /complete-implementation per project) tracks configurable per-project gate composition for the broader complete-implementation pipeline. The brooks-lint pattern is finer-grained (per-rule severity override, focus list, ignore globs) but overlaps. To raise confidence: compare #2105's design intent — does it cover code-review rule-level overrides specifically, or only gate phase composition? If #2105 covers only phases, then this gap is genuinely separate and should become its own item.

### Current state

The 7 `code-review-{stack}` skills have rules baked in. There is no per-project override file at the repo root that disables a rule, downgrades a severity, restricts review to a focus list, or ignores generated files. Issue #2105 covers configurable gate composition for `/complete-implementation` phases (T1–T6) but does not address rule-level overrides within a code-review skill.

### Target state

To be defined after confirming whether #2105 covers this case.

### Measurable signal

To be defined.

---

## Improvement 8: Architecture audit Mermaid dependency graph generator skill

**Source pattern**: README.md lines 109–145 — Mode 2 (Architecture Audit) generates a native Mermaid flowchart of module dependencies with color-coded severity. Renders in GitHub, Notion, and Markdown without extra tools. Identifies circular dependencies, Conway's Law misalignment, and dependency direction violations.
**Local system**: no local equivalent; closest is `plugins/development-harness/skills/forensic-review/` and `agents/codebase-analyzer.md`
**Confidence**: High
**Impact**: Low
**Backlog**: #2254 created

### Current state

`plugins/development-harness/agents/codebase-analyzer.md` and `code-reviewer.md` produce textual reports. Neither generates a visual dependency graph. There is no skill named `architecture-audit`, `architecture-graph`, `dependency-graph`, or similar in `plugins/development-harness/skills/`. Circular dependency detection, dependency direction analysis, and module-level coupling visualization are not part of any current local workflow.

### Target state

A new skill `plugins/development-harness/skills/code-review-architecture/SKILL.md` (or similar) instructs the agent to:

1. Build a module dependency graph from import/include relationships in the project source
2. Detect circular dependencies
3. Output a Mermaid `flowchart` with nodes color-coded by finding severity (red = circular dep / critical, yellow = warning, green = clean)
4. Register the Mermaid block as part of the `codebase-analysis` artifact

The skill is loadable independently and is invoked when a task asks for architecture review.

### Measurable signal

```bash
ls plugins/development-harness/skills/code-review-architecture/SKILL.md
```

exists. Running the skill against a sample project produces an artifact containing a fenced ` ```mermaid ` block with `flowchart` keyword and at least one `style {node} fill:#` directive demonstrating severity color-coding.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Repository consistency validation script (Improvement 6) | medium | A partial equivalent exists (skilllint + pre-commit auto-bump). Need to enumerate the specific invariants brooks-lint checks vs. what local checks already cover before the gap can be expressed concretely. |
| Per-project code-review config overrides (Improvement 7) | medium | Closely related to existing tracked issue #2105 (Configurable gate composition for /complete-implementation per project). Need to determine whether #2105 covers code-review rule-level overrides or only pipeline phase composition before creating a separate item. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-perspective parallel review (Security/Performance/Quality/Accessibility) | Already tracked: backlog #2181 "Multi-perspective parallel review skill (Security/Performance/Quality/Accessibility) over the same diff" — this directly addresses the parallel-perspective review pattern that brooks-lint's six analysis modes embody. |
| Confidence scoring + dedup for parallel review findings | Already tracked: backlog #1430 "Confidence gating and deduplication pipeline for multi-agent review findings" — covers structured findings with confidence + dedup. |
| Persona-based specialized review agents | Already tracked: backlog #1423 "Persona-based specialized review agents for quality gates". |
| GitHub Action for PR review | Already implemented: `.github/workflows/claude-code-review.yml` runs Anthropic's `claude-code-action@v1` on every PR with the `code-review@claude-code-plugins` plugin. The CI integration pattern is already in place. |
