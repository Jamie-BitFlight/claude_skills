---
title: "Utilization Proposals: Prompt Optimizer"
---

## Utilization 1: `/plugin-creator:subagent-refactorer` → Prompt Optimizer MCP Server

**Research entry**: ./research/prompt-engineering/prompt-optimizer.md
**Caller**: `./.claude/skills/plugin-creator/subagent-refactorer/SKILL.md` (orchestrator role)
**Integration mechanism**: MCP server dependency
**Replaces or adds**: Adds side-by-side multi-model evaluation and structured comparison scoring to agent prompt optimization workflow
**Setup cost**: Medium (Docker or standalone Node.js MCP server deployment, schema learning)
**Integration surface**: `@prompt-optimizer/mcp-server` — MCP protocol implementation for evaluate, analyze, and compare operations

### Why this caller

The `/plugin-creator:subagent-refactorer` skill currently refactors agent prompt files using local prompt engineering principles (RT-ICA pre-check, CoVe post-check, Anthropic best practices). After refactoring an agent's instruction set, the skill validates the prompt against target models but does not perform structured side-by-side comparison evaluation or quantify improvement metrics. Prompt Optimizer's `EvaluationService` and `CompareService` (research entry §Dual-Mode Prompt Optimization, §Analysis & Evaluation Pipeline) enable multi-model testing (Claude Haiku, Sonnet, Opus vs. OpenAI GPT-4, Gemini, DeepSeek simultaneously) with structured JSON evaluation artifacts that quantify before/after performance. This capability directly supports the "prove the new prompt produces better outputs than the baseline" use case documented in the research entry's Relevance section (lines 369–371) and aligns with SAM T0/TN verification gate methodology already used in development-harness workflows.

### Integration sketch

```typescript
// Within subagent-refactorer post-refactoring phase (after prompt rewrite, before commit)
// Requires: MCP server instantiated (Docker or standalone Node.js process)

const evaluator = new CompareService(createDataManager());

// Compare baseline (original agent instruction) vs. proposed (refactored) instruction
const baseline = {
  instruction: originalAgentPrompt,
  testInput: representativeEdgeCases, // from agent scope
};

const proposed = {
  instruction: refactoredAgentPrompt,
  testInput: representativeEdgeCases,
};

// Run structured evaluation across multiple models
const comparison = await evaluator.compare(
  baseline,
  proposed,
  [
    { provider: "openai", model: "gpt-4" },
    { provider: "anthropic", model: "claude-opus-4" },
    { provider: "google", model: "gemini-pro" },
  ]
);

// Output: JSON evaluation artifact with per-model scores
// Example: { overall_improvement: 0.27, accuracy_before: 0.68, accuracy_after: 0.95, model_consistency: "high" }

// Register as T0-baseline artifact (research-utilization-assessor can then use TN gate)
await artifactManager.register({
  type: "evaluation",
  agent: "subagent-refactorer",
  baseline_prompt: originalAgentPrompt,
  proposed_prompt: refactoredAgentPrompt,
  comparison_results: comparison,
  timestamp: now(),
});

// Commit message includes evaluation evidence (lines 369–371 of research entry)
// Example: "refactor(agent-name): improve instruction clarity — structured compare evaluation: +27% accuracy across 3 models"
```

**Status**: Deferred implementation — requires MCP server deployment decision and schema learning. Primary blocker: whether development-harness team opts for centralized vs. per-task evaluation service. Recommend prototype phase: (1) deploy MCP server, (2) write thin wrapper in subagent-refactorer, (3) test on 2–3 agent refactors, (4) measure time cost and result quality before full adoption.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `/cove-prompt-design` skill | Covers prompt verification patterns (Chain of Verification structure), not prompt optimization or multi-model evaluation. Prompt Optimizer's scope is iterative refinement + comparison, not verification logic. No integration surface overlap. |
| `/seven-prompt-content-engine` skill | Targets content pipeline (idea → outline → draft → humanize → platform variants). Prompt Optimizer targets prompt engineering (system/user prompt clarity, model behavior refinement, compare evaluation). Different problem domains; no architectural dependency. |
| `dh:multi-perspective-review` agent + reviewer suite | Reviews code (quality, security, performance, accessibility perspectives). Does not review agent instructions or prompt text. Integration would require extending reviewer scope — architectural change beyond utilization assessment scope. Flag as separate enhancement: "Consider prompt-quality reviewer perspective" for backlog. |

---

## Integration Readiness Summary

**High potential** — subagent-refactorer integration is well-scoped and directly addresses documented use case (lines 369–371 of research entry: "prove the new prompt produces better outputs than the baseline"). Evaluation artifacts align with existing SAM T0/TN verification pattern.

**Medium readiness** — MCP server deployment infrastructure decision required. Recommend decision gate: "Should Prompt Optimizer MCP run as shared Docker service, per-task subprocess, or local-only Deno/Node.js?" Answer determines setup cost and adoption timeline.

**Lower priority expansions** (not recommended for immediate integration):
- Integrating web app UI for interactive prompt refinement (requires browser context, not applicable to CLI/agent workflow)
- Text-to-image generation for `/ai-design-tools` skills (out of scope for prompt engineering focus)
- Chrome extension for in-browser optimization (user-facing, not agent-facing)
