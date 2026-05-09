---
title: agent-skills-eval
subtitle: Empirical evaluation SDK and CLI for Agent Skills with judge-graded baseline comparison
category: evaluation-testing
resource_url: https://github.com/darkrishabh/agent-skills-eval
github_url: https://github.com/darkrishabh/agent-skills-eval
date_created: "2026-05-09"
date_last_reviewed: "2026-05-09"
status: published
---

# agent-skills-eval

**Research Date**: 2026-05-09
**Source URL**: <https://github.com/darkrishabh/agent-skills-eval>
**Package Registry**: <https://www.npmjs.com/package/agent-skills-eval>
**Version at Research**: 0.1.1
**License**: MIT

---

## Overview

agent-skills-eval is a TypeScript SDK and CLI for empirically evaluating Agent Skills — the open standard from Anthropic for giving agents domain knowledge. It runs evaluations against the same prompts twice (once with skill loaded, once without baseline), has a judge model grade both outputs, and produces evidence-backed reports showing whether a skill measurably improves model performance. The tool is designed to work with any OpenAI-compatible model provider and outputs portable JSON artifacts plus static HTML reports.

Source: README.md lines 1–32 — "A test runner for Agent Skills. Write a SKILL.md, drop in some evals, and find out — empirically — whether your skill actually makes the model better at the task."

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Shipping Agent Skills without empirical evidence of impact | Runs evaluations with/without skill to show measurable lift or absence using judge-graded outputs |
| Operator uncertainty about skill effectiveness | Side-by-side comparison reports with assertion-level grading evidence, timing, token counts, and tool calls |
| Tool-call validation in agent workflows | Deterministic tool-call assertions that check structured calls locally without requiring judge model |
| Infrastructure lock-in when evaluating skills | OpenAI-compatible provider abstraction works with OpenAI, Together, Groq, Anthropic (via compat layers), local Llama servers, and custom providers via interface implementation |
| Difficulty reproducing eval results | Portable JSON + JSONL artifacts and official `iteration-N` layout enable diffs and dashboards downstream |

Sources: README.md lines 26–72 (sections "Why this exists" and "What you get")

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| npm Package Version | 0.1.1 | 2026-05-09 |
| Initial Public Release | v0.1.0 | Changelog line 11 |
| Repository Commit Count (visible) | 1 | 2026-05-09 (shallow clone) |
| Latest Commit Date | 2026-05-06 | git log output |
| TypeScript Source Lines | ~3,628 | wc -l src/*.ts |
| Node.js Requirement | >=18 | package.json line 115 |
| Primary Dependencies | commander (^12.1.0), js-yaml (^4.1.1) | package.json lines 105–107 |

Sources: package.json, CHANGELOG.md, git log, source directory statistics

---

## Key Features

### Evaluation Execution

- **Baseline comparison**: Runs each eval in two modes — `with_skill` (skill loaded into context) and `without_skill` (baseline) — on the same target model against identical prompts. Source: README.md lines 85–116 (diagram and explanation)
- **Judge-graded outputs**: Configurable judge model grades both sides independently using rubric assertions and optional structured output validation. Source: src/grade.ts lines 15–37 (GradeOutputsArgs interface)
- **Deterministic tool assertions**: Validates tool calls locally without judge involvement — checks function names, argument structure, and call sequencing. Source: src/grade.ts lines 16–24, src/index.ts line 49 (`runToolAssertions` export)
- **Concurrency control**: Bounded worker pool runs eval cases in parallel; defaults to 4 concurrent evals, configurable per task. Source: src/evaluate-skills.ts lines 126–136 (runPool function)

### Configuration & CLI

- **YAML config file**: `agent-skills-eval.yaml` defines root, workspace, baseline flag, target/judge models, API base URL, include/exclude patterns, concurrency, report output, logging format, and model params. Source: README.md lines 123–151 (YAML config example)
- **CLI one-liner**: `npx agent-skills-eval ./skills --target gpt-4o-mini --judge gpt-4o-mini --baseline --strict` runs evals without prior installation. Source: README.md lines 37–42
- **Logging modes**: `pretty` (human-readable terminal output), `jsonl` (structured event stream), `silent` (CI-friendly). Source: README.md line 310

### SDK & Extensibility

- **TypeScript SDK**: Programmatic API with `evaluateSkills()`, `gradeOutputs()`, `runEval()`, custom reporters. Source: src/index.ts lines 1–55 (export statements)
- **Provider interface**: Custom provider implementation with five fields (`name`, `model`, `capabilities`, `complete()`, `completeChat?()`) enables integration with any backend — local Llama, internal APIs, mock providers for testing. Source: src/provider.ts lines 55–61; README.md lines 213–232
- **OpenAI-compatible provider**: Built-in provider accepts any OpenAI-compatible endpoint (baseUrl, apiKey, model). Source: package.json export "./openai-compatible" (line 25); README.md lines 170–175 usage example
- **Event-driven reporters**: Structured event stream with `onEvent` callback; bundled `consoleReporter()` and `jsonlReporter()` for real-time and file-based observability. Source: src/evaluate-skills.ts lines 40–42; src/index.ts lines 45, 50

### Artifacts & Reports

- **Iteration workspace layout**: Follows agentskills.io spec: `iteration-N/<eval>/<mode>/outputs`, `timing.json`, `grading.json`, `benchmark.json` per skill. Source: README.md lines 47–56; src/evaluate-skills.ts lines 71–74 (workspaceLayout parameter)
- **Static HTML reports**: Single-page application generated from disk artifacts; includes pass rates, assertion grading evidence with judge reasoning, full outputs side-by-side, timing/token usage, tool calls. Source: README.md lines 312–321
- **Flat workspace layout**: Alternative layout (not agentskills.io) outputs `<workspace>/<skill>/<eval>/<mode>/...` for dashboards. Source: src/evaluate-skills.ts lines 70–74

### Skill Discovery & Validation

- **SKILL.md frontmatter**: Requires YAML frontmatter with `name`, `description`, optional `license`, `compatibility`, `metadata`, `allowed-tools`. Source: README.md lines 257–266
- **Strict validation**: When `--strict` flag enabled, validates name length, lowercase-hyphenated format, parent-directory name match, description length, compatibility text length against agentskills.io spec. Source: README.md lines 327–330
- **evals.json discovery**: Scans skill folders for `evals/evals.json` containing `skill_name`, `evals[]` array with `id`, `name`, `prompt`, `expected_output`, `files`, `assertions`. Source: README.md lines 268–286

---

## Technical Architecture

The evaluator operates as a bounded-concurrency worker pool processing a queue of eval tasks.

**Core execution flow** (src/evaluate-skills.ts):

1. **Skill discovery** (discoverSkills): Recursively scans root directory for folders containing `SKILL.md` + `evals/evals.json`, applies include/exclude patterns, filters to skills with evaluations.
   Source: src/index.ts line 46 export; referenced in src/evaluate-skills.ts line 139

2. **Preparation phase**: For each discovered skill, load SKILL.md metadata and evals.json; initialize per-skill workspace directories; validate frontmatter if `strict: true`.
   Source: src/evaluate-skills.ts lines 104–113 (PreparedSkill interface)

3. **Task queue & worker pool**: Build flat queue of `{skill, evalCase, index}` objects. Spawn N workers (configurable, default 4). Each worker pops the next task and runs it to completion; order of completion is non-deterministic.
   Source: src/evaluate-skills.ts lines 115–136 (Task interface, runPool function)

4. **Per-eval run** (runEval in src/run-eval.ts): For each eval case, execute in both modes (`with_skill`, `without_skill`) by:
   - Injecting skill context (or omitting for baseline)
   - Calling target provider's `complete()` or `completeChat()` method
   - Recording output, latency, token counts, structured tool calls (if any)
   - Saving artifacts (outputs.json, timing.json, prompts)

5. **Grading** (gradeOutputs in src/grade.ts): For each mode output:
   - Run deterministic tool assertions locally (source: src/grade.ts lines 84–87, `failClosed` function)
   - Construct judge prompt from `expected_output` and rubric `assertions`
   - Call judge model; parse JSON response
   - Normalize assertion results with fallback to `fail-closed` on parse error (source: src/grade.ts lines 59–87)

6. **Aggregation**: Rollup pass/fail per skill; compute benchmarks; emit progress events; optionally snapshot to history (loop mode); optionally generate static HTML report.
   Source: src/evaluate-skills.ts lines 138–250 (evaluateSkills function)

**Provider contract** (src/provider.ts):

- `Provider.complete(prompt: string): Promise<ProviderResult>` — accepts plain text, returns structure with output, latency, token counts, optional error.
- `Provider.completeChat?(args: CompleteChatArgs): Promise<ProviderResult>` — optional; accepts system message, user message, files, tools, tool choice, model-specific params; returns same ProviderResult plus optional `toolCalls` array.
- `ProviderCapabilities` — optional metadata: `attachments`, `systemRole`, `toolCalls` (boolean flags declaring feature support).

Sources: src/provider.ts lines 31–61

**Tool assertion semantics** (src/grade.ts):

Tool assertions check captured tool calls deterministically:
- Match function name against expected name
- Validate argument keys and types against schema (if provided)
- Check order/count constraints (if specified)

Failures are recorded as assertion failures; no judge model needed for these checks.

Source: README.md line 68 ("Tool-call assertions — Deterministic checks for agents that call tools")

---

## Installation & Usage

### CLI Installation & Usage

```bash
# Without installing: run directly
npx agent-skills-eval ./skills \
  --target gpt-4o-mini \
  --judge gpt-4o-mini \
  --baseline \
  --strict
```

```bash
# With installation to node_modules
npm install agent-skills-eval

# Then run:
OPENAI_API_KEY=sk-... npx agent-skills-eval ./skills --config agent-skills-eval.yaml
```

Output structure after running:
```text
agent-skills-workspace/
└── iteration-1/
    ├── meta.json            # run metadata
    ├── benchmark.json       # rolled-up pass/fail per skill
    ├── eval-basic/
    │   ├── with_skill/      # output, timing, judge grading
    │   └── without_skill/   # ↑ same, with the skill stripped
    └── report/
        └── index.html       # the visual report
```

Source: README.md lines 34–56

### SDK Usage

```typescript
import {
  OpenAICompatibleProvider,
  consoleReporter,
  evaluateSkills,
} from "agent-skills-eval";

const provider = new OpenAICompatibleProvider({
  baseUrl: "https://api.openai.com/v1",
  apiKey: process.env.OPENAI_API_KEY!,
  model: "gpt-4o-mini",
  providerName: "openai",
});

const result = await evaluateSkills({
  root: "./skills",
  workspace: "./agent-skills-workspace",
  baseline: true,
  concurrency: 4,
  workspaceLayout: "iteration",
  strict: true,
  target: { model: provider.model, provider },
  judge: { model: provider.model, provider },
  onEvent: consoleReporter(),
});

console.log(result);
```

Source: README.md lines 163–187

### YAML Configuration

```yaml
# agent-skills-eval.yaml
root: ./skills
workspace: ./agent-skills-workspace
baseline: true
target: gpt-4o-mini
judge: gpt-4o-mini
baseUrl: https://api.openai.com/v1
apiKeyEnv: OPENAI_API_KEY
include:
  - "skills/**"
exclude:
  - "**/draft-*"
concurrency: 4
layout: iteration
strict: true
report:
  enabled: true
  title: Agent Skills Report
logging:
  format: pretty   # pretty | jsonl | silent
  verbose: false
  color: auto
targetParams:
  temperature: 0
judgeParams:
  temperature: 0
```

Source: README.md lines 124–151

### Custom Provider

```typescript
import type { Provider, ProviderResult } from "agent-skills-eval";

export const provider: Provider = {
  name: "my-provider",
  model: "my-model",
  async complete(prompt: string): Promise<ProviderResult> {
    return {
      provider: "my-provider",
      model: "my-model",
      output: "model output",
      latencyMs: 0,
      inputTokens: 0,
      outputTokens: 0,
      costUsd: 0,
    };
  },
};
```

Source: README.md lines 217–232

---

## Relevance to Claude Code Development

### Applications

- **Skill evaluation for Agent Skills ecosystem**: Directly applicable to validating skills created with `/plugin-creator:skill-creator` or for the `agentskills.io` standard integration. Use to empirically measure whether a skill improves agent performance on target tasks.
- **Agent capability assessment**: Can be adapted to evaluate agent prompt quality or specialized agent behaviors by using agent outputs as the target model source.
- **Prompt optimization validation**: When iterating on prompts or system instructions, use this framework to measure quantitative improvement over baseline with judge-graded assertions.

### Patterns Worth Adopting

- **Provider abstraction pattern**: Decoupling model completion from the evaluator logic (via the `Provider` interface) enables testing against mock providers, local models, and multiple cloud providers without code duplication. Worth applying to any tool that needs multi-backend support.
- **Bounded concurrency worker pool**: The `runPool<T>()` pattern (src/evaluate-skills.ts lines 126–136) is a clean, typed implementation of FIFO task queue with N concurrent workers. Applicable to any parallelizable batch task.
- **Judge-based grading with fallback**: The `fail-closed` strategy (src/grade.ts lines 84–87) where unparseable judge responses default to assertion failure is a robust defensive pattern for LLM-based grading.
- **Iteration workspace versioning**: The `iteration-N` layout (following agentskills.io spec) provides a natural history of successive runs, enabling side-by-side comparison and regression detection without manual naming.

### Integration Opportunities

- **Backlog task validation**: Could be used in `/dh:validate-implementation` workflows to verify that completed implementation tasks meet acceptance criteria via skill-style evaluations.
- **Claude Code plugin quality gates**: Pre-publish gate in `/plugin-creator:plugin-creator` to run skills against standard test cases and report results before marketplace submission.
- **Agent iteration loops**: Integrate with `/scientific-method:scientific-thinking` workflows to empirically validate hypothesis-driven agent prompt changes.

---

## References

- [agent-skills-eval GitHub Repository](https://github.com/darkrishabh/agent-skills-eval) (accessed 2026-05-09)
- [agent-skills-eval npm Package](https://www.npmjs.com/package/agent-skills-eval) (accessed 2026-05-09)
- [Agent Skills Open Standard](https://agentskills.io) (referenced in README.md, accessed 2026-05-09)
- README.md — project overview, features, usage examples, architecture diagram (accessed 2026-05-09)
- package.json — version, dependencies, entry points, metadata (accessed 2026-05-09)
- CHANGELOG.md — release history (accessed 2026-05-09)
- src/provider.ts — Provider interface, ProviderResult, CompleteChatArgs types (accessed 2026-05-09)
- src/evaluate-skills.ts — EvaluateSkillsArgs, evaluateSkills() function, runPool() worker pool (accessed 2026-05-09)
- src/grade.ts — GradeOutputsArgs, grading logic, assertion normalization (accessed 2026-05-09)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Harness Engineering Discipline (Martin Fowler)](./harness-engineering-martin-fowler.md) | evaluation-testing | Shared foundational framework for constraining AI agents; agent-skills-eval operationalizes the harness-engineering principles via judge-graded assertions |
| [OpenAI Codex Harness Engineering](./harness-engineering-openai.md) | evaluation-testing | Production A/B testing methodology for code agents; 3-layer harness architecture directly parallels agent-skills-eval's provider + grading separation |
| [Anthropic Agent Skills](../skill-generation-tools/anthropics-skills.md) | skill-generation-tools | Official Agent Skills standard with 17 skills; primary evaluation target for agent-skills-eval's SKILL.md validation and evals.json discovery |
| [Everything Claude Code](../skill-generation-tools/everything-claude-code.md) | skill-generation-tools | 65+ skills, 16 agents harness requiring empirical evaluation; uses agent-skills-eval pattern for impact measurement |
| [AI Agents Frameworks](../agent-frameworks/ai-agents-frameworks.md) | agent-frameworks | 10-framework comparative benchmarking study; agent-skills-eval provides the evaluation infrastructure that enables cross-framework performance comparison |
| [Codex App Server (JSON-RPC)](./codex-harness-openai.md) | evaluation-testing | Bidirectional harness protocol enabling agent evaluation; complements judge-graded output validation with structured event streaming |
| [mattpocock/skills](../skill-generation-tools/mattpocock-skills.md) | skill-generation-tools | 21 battle-tested specialized skills for Claude Code; exemplar use case for agent-skills-eval's empirical impact measurement |
| [Superpowers Framework](../agent-frameworks/superpowers.md) | agent-frameworks | Agentic skills framework with TDD enforcement; shares goal-driven evaluation patterns and skill-to-capability mapping with agent-skills-eval |
| [awesome-ai-apps](../ai-research-tools/awesome-ai-apps.md) | ai-research-tools | Curated 76 AI agent projects across 6 categories; agent-skills-eval enables comparative evaluation of these diverse implementations |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-09 |
| Version at Verification | 0.1.1 |
| Next Review Recommended | 2026-08-09 |
| Confidence Map | `Overview: high`, `Problem Addressed: high`, `Key Statistics: high`, `Key Features: high`, `Technical Architecture: high (code-read)`, `Installation & Usage: high`, `Relevance to Claude Code: medium`, `References: high` |

**Confidence Notes:**
- Technical Architecture confidence is `high (code-read)` because the execution flow was verified by reading src/evaluate-skills.ts, src/provider.ts, and src/grade.ts directly.
- Relevance to Claude Code Development confidence is `medium` because applications are inferred from the tool's design and the Claude Code ecosystem, not explicitly documented in the repository.
- Version 0.1.1 (released 2026-05-06 per git commit date) is very recent; monitor for v0.2.0 or later releases that may introduce breaking changes to the Provider interface or artifact layout.

