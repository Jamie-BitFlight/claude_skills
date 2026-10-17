---
name: skill-research-process
description: Builds a skill from official documentation through categorized research, citation review, integration, and final validation. Use when researching a tool or library before creating a skill, when "research for skill" or "create comprehensive skill" is requested, or when extensive multi-source documentation gathering is needed.
argument-hint: <tool-or-library-name> [target-skill-path]
user-invocable: true
---

# Skill Research Process

Build a skill from source-backed documentation. This is an authoring workflow, not a research-vault entry workflow: use `research-curator` only when the user also requests a durable `research/` entry.

## Invocation and Preconditions

Read the invocation text supplied by the active harness. It must identify the tool or library. Derive the target skill path only when the user supplied it or repository context makes it unambiguous; otherwise ask for the target path before creating files. Treat an unsubstituted argument placeholder as missing input.

Before mutation, read the existing target skill when it exists, its relevant package instructions, and `plugin-creator:skill-creator`. Use its existing structure instead of inventing a second convention. Create a new skill only with that skill's initialization procedure.

Use the host's available worker mechanism rather than literal harness-specific `Task`, `Agent`, or `Skill` calls. Give every worker a concrete file scope, source set, required output, and acceptance checks. Launch independent category workers concurrently when the host supports it; otherwise run the same category handoffs sequentially. Preserve each structured worker result and its exact failure reason for the final relay.

## Process Overview

```text
Stage 1: Categorize → scratch research plan
    ↓
Gate 1: categories are distinct, complete, and sourceable
    ↓
Stage 2: Research → category references and indexes
    ↓
Gate 2: citations, provenance, and gaps are verified
    ↓
Stage 3: Integrate → target SKILL.md links and usage guidance
    ↓
Gate 3: package-appropriate structural, link, and source validation
```

## Stage 1: Categorize

1. Create `.tmp/scratch/plans/{skill-name}-research-plan.md`; it is an intermediate plan, not durable backlog state.
2. Launch one available research worker with the Categorization handoff in [Agent Prompts](./references/agent-prompts.md#categorization-handoff). It writes only that scratch plan.
3. Review the plan before research:
   - categories are distinct and each has a named boundary;
   - all documented aspects of the target have a category or an explicit out-of-scope reason;
   - each category names official sources to inspect;
   - categories are narrow enough for one worker and broad enough to produce a useful index.
4. Merge or redefine overlaps before Stage 2. A missing source or unclear target blocks only the affected category; record the exact gap in the scratch plan.

## Stage 2: Research

1. Launch one available research worker per approved category with the [Research Handoff](./references/agent-prompts.md#research-handoff). Give each worker an exclusive `references/{category}/` directory under the target skill.
2. Each worker creates an `index.md`, detailed reference files, and a structured result containing `STATUS`, `ARTIFACTS`, `SOURCES`, `GAPS`, and `WARNINGS`.
3. Preserve exact worker counts, artifact paths, unavailable-source errors, and unresolved gaps. Do not convert a failed source fetch into a claim about the tool.

### Gate 2: Source and Citation Review

For every category, confirm:

- every factual claim is supported by a source the worker read during this run;
- each citation records URL and access date, and source passages are attributable;
- official documentation is the authority for API behavior; secondary sources are labeled as such;
- examples are source-attributed or actually exercised before being presented as working;
- a source gap is written as `NOT_VERIFIED: {claim}` or an explicit documentation gap, never filled from model knowledge;
- the category index links to every reference file with relative paths.

Return a category with unsupported claims to the same worker with the exact claims, not a summary. Stop a category that cannot obtain a source after its documented fallback and relay the exact reason; do not silently substitute an uncited overview.

## Stage 3: Integrate

1. Launch or perform the [Integration Handoff](./references/agent-prompts.md#integration-handoff) after every category has either passed Gate 2 or reported its explicit gaps.
2. Read all category indexes, then update the target `SKILL.md` with concise links and routing instructions. Keep detailed source material in `references/`.
3. Preserve the target skill's existing lifecycle and package conventions. Attribute external documentation where the target's existing convention requires it.
4. Do not convert the scratch research plan into a durable backlog record. If a user-visible enhancement is deferred, create or match it through the configured backlog backend and record its logical identifier in the scratch plan.

### Gate 3: Final Validation

Run the package-appropriate existing validator, then read every new or changed index and target-skill link to confirm it resolves. Verify that every approved category has an index, every index has only working relative links, and every Stage 1 category is represented or explicitly recorded as unavailable. Run the repository's changed-file checks once after the coherent change.

## Failure Recovery

- **Missing documentation tools**: use the available primary-source reader; if no primary source can be read, report the blocked source and do not make a claim from it.
- **Worker failure or timeout**: inspect only the worker's assigned output path. Retain a complete, cited artifact that passes Gate 2; otherwise relay the exact failure and leave that category incomplete.
- **Incomplete upstream documentation**: document what the source covers, label the gap, and keep the category's unsupported claims out of the target skill.
- **Interrupted run**: resume from the scratch research plan and the category results already written; revalidate their citations before integration.

## Final Report

Relay worker results without interpretation:

```text
## Skill Research Result

Target: {target skill path}
Categories: {passed}/{planned}
Artifacts:
- {path}
Source gaps:
- {exact gap or none}
Validation: {exact command and result}
Scratch plan: .tmp/scratch/plans/{skill-name}-research-plan.md
```

## References

- [Agent Prompt Templates](./references/agent-prompts.md)
- [MCP Tool Usage Guide](./references/mcp-tools.md)
- [Gaps Analysis](./references/gaps-analysis.md)
