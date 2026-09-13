---
name: skylos
research_date: 2026-09-13
source_url: https://github.com/duriantaco/skylos
github_repository: https://github.com/duriantaco/skylos
version_at_research: 4.36.1
license: Apache-2.0
freshness_tracking:
  last_verified: 2026-09-13
  version_at_verification: 4.36.1
  next_review: 2026-12-13
  confidence_map: "Identity/Metadata: high (manifest + changelog); Overview: high (README); Problem Addressed: high (README); Key Features: high (README + local docs); Technical Architecture: medium (docs + bounded code-read); Installation & Usage: high (README); Relevance to Claude Code Development: high (README + agent-verification docs); Limitations: high (README + local docs)"
---

# Skylos

## Overview

Skylos is an Apache-2.0-licensed, local-first static-analysis CLI and PR gate for Python, TypeScript/JavaScript, Go, Java, Kotlin, PHP, Rust, Dart, C#, Shell, and deployment configuration. Its checked-in package metadata declares version `4.36.1`, Python `>=3.10`, and a `skylos` CLI entry point. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md), [pyproject.toml](https://github.com/duriantaco/skylos/blob/main/pyproject.toml), [CHANGELOG.md](https://github.com/duriantaco/skylos/blob/main/CHANGELOG.md)

It combines dead-code, security, secret, dependency, CI/CD, quality, AI-code-defect, and agent-verification checks. Core static analysis is documented as local and independent of API keys; LLM features are optional. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)

---

## Problem Addressed

| Problem | Solution |
| --- | --- |
| A review needs several classes of static checks across source and deployment files. | `skylos . -a` adds security, secrets, dependency, configuration, quality, and AI-defect checks to the default dead-code scan. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md) |
| Generated or edited code can reference nonexistent local symbols or unsupported package APIs. | `skylos verify` performs deterministic verification and reports `pass`, `fail`, or `incomplete`; its coverage object records completed, skipped, and missing checks. [Source: AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md) |
| Agent code needs deterministic evidence of static guardrails before deployment. | `skylos discover` inventories LLM integrations, while `skylos defend` runs 13 deterministic checks, can gate CI, and can emit attested reports. [Source: Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md) |
| A running agent's response and selected tools need contract-based testing. | `skylos agent test` evaluates live or captured observations against scenarios in `.skylos/agent-test.yml`. [Source: Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md) |

---

## Key Features

### Static analysis and PR gates

- The CLI scans for dead code, security flaws, secrets, CI/CD and edge-deployment misconfigurations, quality regressions, AI-generated-code mistakes, and LLM-app risks. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)
- `skylos . -a --diff origin/main` scopes the combined scan to changed work; `skylos cicd init` generates a GitHub Actions PR gate. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)
- The language-support table documents local API proof for Python, TypeScript/JavaScript, Go, and Java. For PHP, Rust, Dart, C#, Kotlin, and Shell, the existing static-analysis rules remain available but local API proof is reported as unsupported. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md), [AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md)

### Deterministic AI-code verification

- `skylos verify . --file src/app.py --range 40:75 --project-context` narrows verification to a file range and project context. Schema-version-2 results use `pass`, `fail`, and `incomplete`; `incomplete` exits with code `2` unless `--no-fail` is set. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md), [AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md)
- Verification is documented not to execute target code, invoke package managers or compilers, call an LLM judge, or query a network service for local/workspace API verification. [Source: AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md)
- `skylos contract init` creates a repository-local AI hallucination contract at `.skylos/ai-contract.yml`; the contract can configure phantom-symbol, dependency, API-surface, route, and test requirements. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md), [contracts/schema.py](https://github.com/duriantaco/skylos/blob/main/skylos/contracts/schema.py)

### Agent verification and behavior testing

- `skylos defend` evaluates ten weighted defense checks and three separately scored operations checks. The documented defense checks cover dangerous output sinks, tool scope and schemas, prompt-injection paths, output validation, RAG isolation, PII filtering, and model pinning. [Source: Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md)
- The `verify_agent` MCP tool returns compact JSON with defense and operations scores, failed checks, OWASP coverage, an attestation digest, and a gate verdict. [Source: Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md)
- Agent behavior contracts can require or forbid tool calls, constrain an exact tool sequence and call count, require response substrings and source IDs, and require an explicit refusal. [Source: Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md), [agents/evaluation/schema.py](https://github.com/duriantaco/skylos/blob/main/skylos/agents/evaluation/schema.py)

---

## Technical Architecture

### Documented execution surfaces

Skylos exposes separate verification surfaces rather than one claim of end-to-end agent correctness: `skylos verify` checks generated-code truth, `skylos defend` checks static guardrails in an agent implementation, and `skylos agent test` checks observed runtime behavior against a contract. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md), [Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md)

For `verify`, selected source files determine the expected proof universe. The verifier reports per-language support and completed or skipped checks in its `coverage` object; unsupported or uncertain proof leaves the result `incomplete` rather than claiming a complete result. [Source: AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md)

### Contract and result structures (bounded code review)

`HallucinationContract` composes `AIContract`, `SecurityContract`, and `TestsContract`; its AI branch contains `PhantomSymbolsContract`, `DependencyContract`, and `ApiSurfaceContract`. This is the code-level shape behind `.skylos/ai-contract.yml`. [Source: `skylos/contracts/schema.py` — `HallucinationContract` (code-read)](https://github.com/duriantaco/skylos/blob/main/skylos/contracts/schema.py)

`AgentBehaviorContract` holds an `AgentTarget` and a tuple of `AgentScenario` values. Each scenario contains a `ScenarioExpectation`, which composes response, tool, refusal, and source expectations. `AgentToolDefinition.openai_dict()` converts a configured tool into the OpenAI function-tool schema. [Source: `skylos/agents/evaluation/schema.py` — `AgentBehaviorContract`, `AgentScenario`, `AgentToolDefinition.openai_dict()` (code-read)](https://github.com/duriantaco/skylos/blob/main/skylos/agents/evaluation/schema.py)

The behavior and agent-verification surfaces use explicit bounded evidence structures: `HarnessRun` records its budget, steps, tool calls, decisions, and artifact paths; `InvestigationToolLimits` caps the investigator layer at 12 calls and 12 distinct files by default. [Source: `skylos/llm/harness/types.py` — `HarnessRun` (code-read)](https://github.com/duriantaco/skylos/blob/main/skylos/llm/harness/types.py), [Source: `skylos/audit/investigator_tools/models.py` — `InvestigationToolLimits` (code-read)](https://github.com/duriantaco/skylos/blob/main/skylos/audit/investigator_tools/models.py)

### Configuration and extension points

`skylos init` adds `[tool.skylos]` configuration. The documented extension points include template paths, vibe-dictionary additions, explicit dead-code entrypoints, and contribution-signal settings. `skylos rules init` creates a local YAML rule pack, and `skylos rules validate` validates that pack. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)

The MCP package entry point imports `main` from `skylos_mcp.server`, and the public MCP-facing commands documented for coding agents are `verify_change` and `verify_agent`. [Source: `skylos_mcp/__main__.py` — module entry point (code-read)](https://github.com/duriantaco/skylos/blob/main/skylos_mcp/__main__.py), [README](https://github.com/duriantaco/skylos/blob/main/README.md), [Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md)

---

## Installation & Usage

Install the core CLI and run its default dead-code scan:

```bash
pip install skylos
skylos .
```

Run the combined scan or deterministic AI-code verification:

```bash
skylos . -a
skylos verify . --file src/app.py --range 40:75 --project-context
```

Create and use a repository-specific generated-code contract:

```bash
skylos contract init
skylos contract inspect
skylos verify .
```

These commands are reproduced from the project's README. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)

---

## Relevance to Claude Code Development

### Applications

- The documented `verify_change` MCP tool exposes the same narrow verification schema as `skylos verify` to Claude, Cursor, and other MCP clients, making it suitable for a post-edit verification step before review. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)
- `verify_agent` is explicitly documented for Claude Code, Cursor, and other MCP clients to statically verify an agent codebase. [Source: Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md)
- Agent-test contracts can make tool selection, refusal behavior, and source identifiers evaluable rather than relying on prose review. [Source: Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md)

### Patterns Worth Adopting

- Preserve an `incomplete` state when a requested proof cannot be established; the documented verifier uses this instead of silently treating unsupported or uncertain checks as a pass. [Source: AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md)
- Bind deterministic evidence to inputs: the documented `defend` attestation digest covers scanned-file hashes, policy, plugin set, CLI filters, inventory, scores, framework selection, and check evidence. [Source: Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md)

### Integration Opportunities

- Use the MCP `verify_change` result as one evidence source in a coding-agent verification gate. This is an integration proposal; its suitability depends on the target repository's languages and accepted `incomplete` policy. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)
- Use `.skylos/agent-test.yml` as a deterministic behavioral-contract format for agents whose tool choices, refusals, or source references are testable. This is an integration proposal, not a claim that Skylos evaluates semantic correctness. [Source: Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md)

---

## Limitations and Caveats

- `skylos verify` supports deterministic local/workspace API proof only for Python, TypeScript/JavaScript, Go, and Java. For PHP, Rust, Dart, C#, Kotlin, and Shell, that proof is documented as unsupported and produces `incomplete`. [Source: AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md)
- Agent verification checks the presence and placement of static guardrail patterns; it does not observe runtime behavior, judge prompt quality, catch semantic failures, or replace runtime controls. [Source: Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md)
- Version-1 behavior testing is single-turn and observes final text plus returned function-tool calls; it does not execute those tools, orchestrate multi-turn tool execution, judge semantic claims, or use an independent LLM judge. [Source: Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md)
- Vue single-file components are skipped by source analysis because Skylos does not yet parse their `<script>` or `<script setup>` blocks. Go dead-code and security checks require the native `skylos-go` engine; if it cannot run, the report is incomplete and exits `2`. [Source: README](https://github.com/duriantaco/skylos/blob/main/README.md)
- `CITATION.cff` declares version `4.2.1`, while `pyproject.toml` and the top changelog release declare `4.36.1`; this entry uses `4.36.1` as the package-manifest and changelog version. [Source: CITATION.cff](https://github.com/duriantaco/skylos/blob/main/CITATION.cff), [pyproject.toml](https://github.com/duriantaco/skylos/blob/main/pyproject.toml), [CHANGELOG.md](https://github.com/duriantaco/skylos/blob/main/CHANGELOG.md)

---

## References

- [GitHub repository](https://github.com/duriantaco/skylos) (accessed 2026-09-13; shallow clone at `./.worktrees/skylos`, commit `635bc358f2acc4bca7703fc7f1a0b8c955d9cb19`)
- [README.md](https://github.com/duriantaco/skylos/blob/main/README.md) (accessed 2026-09-13)
- [pyproject.toml](https://github.com/duriantaco/skylos/blob/main/pyproject.toml) (accessed 2026-09-13)
- [CHANGELOG.md](https://github.com/duriantaco/skylos/blob/main/CHANGELOG.md) (accessed 2026-09-13)
- [AI Code Verification](https://github.com/duriantaco/skylos/blob/main/docs/ai-code-verification.md) (accessed 2026-09-13)
- [Pre-Deployment Agent Verification](https://github.com/duriantaco/skylos/blob/main/docs/agent-verification.md) (accessed 2026-09-13)
- [Agent Behavior Testing](https://github.com/duriantaco/skylos/blob/main/docs/agent-behavior-testing.md) (accessed 2026-09-13)
- [Contract schema](https://github.com/duriantaco/skylos/blob/main/skylos/contracts/schema.py) (accessed 2026-09-13; code-read)
- [Agent behavior schema](https://github.com/duriantaco/skylos/blob/main/skylos/agents/evaluation/schema.py) (accessed 2026-09-13; code-read)
- [Harness types](https://github.com/duriantaco/skylos/blob/main/skylos/llm/harness/types.py) (accessed 2026-09-13; code-read)
- [Investigator-tool models](https://github.com/duriantaco/skylos/blob/main/skylos/audit/investigator_tools/models.py) (accessed 2026-09-13; code-read)
- [MCP entry point](https://github.com/duriantaco/skylos/blob/main/skylos_mcp/__main__.py) (accessed 2026-09-13; code-read)
- [CITATION.cff](https://github.com/duriantaco/skylos/blob/main/CITATION.cff) (accessed 2026-09-13)

---

## Freshness Tracking

| Section | Confidence | Last verified | Notes |
| --- | --- | --- | --- |
| Identity/Metadata | high | 2026-09-13 | Package manifest and current top changelog release read; citation file version conflicts. |
| Overview | high | 2026-09-13 | Project README read. |
| Problem Addressed | high | 2026-09-13 | README and local feature documentation read. |
| Key Features | high | 2026-09-13 | README and three local feature documents read. |
| Technical Architecture | medium (doc + code-read) | 2026-09-13 | Documentation did not fully satisfy component-flow depth; bounded 12-file source review supplied contract and evidence-structure details. |
| Installation & Usage | high | 2026-09-13 | Commands reproduced from README. |
| Relevance to Claude Code Development | high | 2026-09-13 | MCP and Claude Code use are stated in primary project documentation. |
| Limitations and Caveats | high | 2026-09-13 | Explicit project documentation reviewed. |

**Next Review**: 2026-12-13

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Hound](./hound.md) | code-auditing | complements deterministic scans with graph-guided security investigation |
| [Snyk CLI for Open-Source C++ Scans](./snyk-cli-cpp-scans.md) | code-auditing | specializes dependency-vulnerability checks for unmanaged C/C++ source trees |
| [Syft](./syft.md) | code-auditing | supplies SBOM and signed dependency evidence for supply-chain gates |
| [Rope](./rope.md) | code-auditing | shares Python AST and symbol analysis for safe code changes |
| [Merly Mentor](../ai-research-tools/merly-mentor.md) | ai-research-tools | parallel deterministic multi-language code-quality analysis and CI monitoring |
| [CodeGraphContext](../mcp-ecosystem/codegraphcontext.md) | mcp-ecosystem | provides AST graph context and dead-code analysis through MCP |
| [Narsil-MCP](../mcp-ecosystem/narsil-mcp.md) | mcp-ecosystem | extends local code intelligence with MCP security and taint-analysis tools |
| [agent-skills-eval](../evaluation-testing/agent-skills-eval.md) | evaluation-testing | complements deterministic behavior contracts with empirical skill evaluation |
