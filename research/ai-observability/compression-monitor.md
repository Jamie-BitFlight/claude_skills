---
title: "compression-monitor"
description: "Behavioral drift detection toolkit for persistent AI agents across context compression boundaries."
created: "2026-03-29"
last_reviewed: "2026-03-29"
confidence_baseline: "high"
category: "ai-observability"
---

# compression-monitor

**Repository**: <https://github.com/agent-morrow/compression-monitor>
**License**: MIT (inferred from README; pyproject.toml lists no license field)
**Version**: 0.2.1 (released 2026-03-28)
**Python**: 3.9+
**Author**: Morrow (agent-morrow) · [morrow.run](https://morrow.run)

---

## Overview

**Compression-monitor** is a Python toolkit for detecting silent behavioral changes in long-running AI agents after context compression events. When persistent agents' context windows fill and history is summarized, compressed, or evicted, the agent continues operating but may exhibit degraded performance — vocabulary loss, changed tool-use patterns, semantic drift — without reporting the change.

The toolkit provides **three surface-level instruments** that measure distinct behavioral dimensions to triangulate compression events:

1. **Ghost Lexicon** — vocabulary decay across boundaries
2. **Behavioral Footprint** — tool-use pattern shifts
3. **Semantic Drift** — topic embedding distance movement

**Problem Addressed**: Compression fidelity in long-running agents. After a 3-hour Claude Code session with a context compression event, an agent might abandon verification steps, suggest approaches it previously avoided, and use different vocabulary — all silently, without triggering any error or warning. This toolkit surfaces those changes through measurable behavioral signals.

**Key Finding** (from author's benchmark): Memory retrieval systems show ~40% fidelity loss after compression, yet the agent reports confidence unchanged. This toolkit detects when that loss occurs.

---

## Key Statistics

| Metric | Value | Date |
|--------|-------|------|
| **GitHub Stars** | 2 | 2026-03-29 |
| **Forks** | 0 | 2026-03-29 |
| **Open Issues** | 2 | 2026-03-29 |
| **Commits** | 1 (scaffold released) | 2026-03-28 |
| **Repository Created** | 2026-03-28 | GitHub API |
| **Last Push** | 2026-03-29T11:43:25Z | GitHub API |

**Maturity**: Alpha (Development Status :: 3 - Alpha per pyproject.toml). Functional scaffold with tested logic, not production-hardened.

---

## Key Features

### 1. Ghost Lexicon — Vocabulary Decay Detection

**What it measures**: Loss of low-frequency, high-precision terms after a compression boundary.

**Implementation** (`ghost_lexicon.py`):
- Tokenizes agent outputs into word tokens
- Identifies "ghost terms" — vocabulary present in pre-compression sample but absent post-compression
- Focuses on low-frequency but present terms (appear 2+ times, outside top-N common terms)
- Returns a decay score: `len(ghost_terms) / len(pre_vocab)`
- Interprets result: >0.3 = "HIGH — likely compression boundary"; >0.1 = "MODERATE — monitor"; else "LOW"

**Mechanism**: High-precision terms (e.g., "immutable", "schema", "rollback") are more vulnerable to compression loss than common terms. Their disappearance signals constraint loss without output-quality change.

**Example Output** (from README):
```
pre_vocab_size: 145
post_vocab_size: 118
ghost_term_count: 27
decay_score: 0.1862
interpretation: MODERATE — monitor
ghost_terms (first 30): ["schema", "immutable", "constraint", ...]
```

### 2. Behavioral Footprint — Tool-Use Pattern Tracking

**What it measures**: Shifts in response length, tool-call frequency, and latency across session boundaries.

**Implementation** (`behavioral_footprint.py`):
- Accepts three log formats: flattened exchange logs, lightweight text logs, OpenClaw chat-style logs
- Per-session fingerprint: mean response length, tool-call ratio, average tool calls, latency distribution
- Shift score between sessions: normalized distance across response length and tool-call ratio
- Detects multi-session drift via lead-lag ordering

**Mechanism**: Behavioral patterns (How often does the agent call tools? How long are responses?) are operationally stable when context is clean. Post-compression, the agent might reduce verification tool calls or shorten responses. Output quality stays flat, but operational pattern changed.

**Output Fields**:
- `response_length.mean`, `response_length.std`
- `tool_call_ratio` (fraction of responses that include tool calls)
- `avg_tool_calls` per response
- `latency_ms.mean`, `latency_ms.std` (optional, if available)

### 3. Semantic Drift — Embedding-Based Topic Tracking

**What it measures**: Cosine distance movement in pre/post agent output embeddings.

**Implementation** (`semantic_drift.py`):
- Uses sentence-transformers (optional dependency: `sentence-transformers>=2.0.0`)
- Embeds agent outputs as vectors
- Computes mean embedding per session
- Measures cosine distance between pre/post session means
- Detects topic reorientation independent of vocabulary or tool use

### 4. Delegation Quality Analysis

**What it measures**: Changes in subagent delegation prompt quality across compression boundaries.

**Implementation** (`delegation_quality.py`):
- Extracts delegation prompts from agent logs
- Analyzes: file-path specificity, constraint density, verification presence
- Compares pre/post boundary metrics
- Detects when delegation instructions degrade post-compression

### 5. Negative-Space Logging

**What it measures**: Options the agent *considered and skipped* before output.

**Implementation** (`negative_space_log.py`):
- Append-only event log: two record types: `skip` (option considered + criterion for skipping) and `skip_resolution` (eventual outcome)
- Requires explicit instrumentation at agent decision points
- Generates calibration report: compares agent's significance labels ("low", "medium", "high") against eventual outcome impact
- Detects when compaction suppresses deliberation before output layer

**Usage**:
```python
from negative_space_log import NegativeSpaceLog
log = NegativeSpaceLog("agent_skips.jsonl")
skip_id = log.log_skip(cycle_id="turn_42", option_considered="rewrite_module", criterion="time_budget_exceeded", significance="medium")
# Later, after outcome observed:
log.log_resolution(skip_id, outcome="option_taken")
```

---

## Technical Architecture

### Core Components

**Entry Points**:
- `ghost_lexicon.py` — standalone CLI for vocabulary decay analysis
- `behavioral_footprint.py` — standalone CLI for behavioral pattern drift
- `semantic_drift.py` — standalone CLI for embedding-based topic drift
- `delegation_quality.py` — standalone CLI for delegation prompt quality analysis
- `negative_space_log.py` — append-only skip event recorder + calibration reporting
- `parse_claude_session.py` — auto-extracts pre/post-compression samples from Claude Code JSONL logs
- `preregister.py` — pre-registration protocol for falsifiable predictions before compression events

**Framework Integrations** (drop-in wrappers for major agent frameworks):
- `crewai_integration.py` — wraps Crew.kickoff()
- `langgraph_integration.py` — wraps compiled LangGraph graphs
- `autogen_integration.py` — hooks for ConversableAgent or snapshot at session boundaries
- `smolagents_integration.py` — wraps HuggingFace smolagents MultiStepAgent
- `semantic_kernel_integration.py` — detects drift after ChatHistorySummarizationReducer
- `ai_scientist_integration.py` — measures consistency across BFTS phases in AI-Scientist-v2
- `mem0_integration.py` — detects hallucinated memory injection noise
- `letta_integration.py` — behavioral monitoring at in-context → archival eviction boundary
- `deer_flow_integration.py` — monitors ByteDance DeerFlow multi-day session resumption
- `agent_framework_integration.py` — validates isolation in microsoft/agent-framework multi-agent meshes
- `mcp_behavioral_checkpoint.py` — reference implementation for MCP SEP session resumption with behavioral metadata

**Claude Code Integration**:
- `parse_claude_session.py --auto` — auto-detects and extracts samples from `~/.claude/projects/*/*.jsonl`
- `parse_claude_session.py --watch` — polling mode (10s default) for live session monitoring
- `.claude-plugin/` — Claude Code plugin with PostToolUse hook for real-time drift alerts

### Data Flow

```
Agent Output Stream (text, tool calls, latency)
    ↓
[Session Boundary Detection]
    ↓
Pre-Compression Sample (N exchanges) ← Cloud Boundary → Post-Compression Sample (N exchanges)
    ↓
[Three Parallel Instruments]
    ├→ Ghost Lexicon (tokenize, count, measure decay_score)
    ├→ Behavioral Footprint (extract fingerprint, shift_score)
    └→ Semantic Drift (embed, cosine distance)
    ↓
[Triangulation]
    Composite Signal = (decay_score, shift_score, drift_score)
    ↓
[Decision Rule]
    Pattern (e.g., "all three shift") → Interpretation → Action
```

### Design Decisions

**Surface-Observable Only**: The toolkit measures what the agent emits — vocabulary, tool calls, response length, topic embeddings. It does **not** measure internal reasoning suppression, framing-level shifts, or pre-output deliberation that never reaches the surface.

**Three Uncorrelated Signals**: Vocabulary decay, behavioral footprint, and semantic drift are intentionally distinct instruments. If all three signal together, they are likely measuring the same phenomenon. If only one fires, it identifies the compression axis (vocabulary loss vs. operational change vs. topic shift).

**Perturbation Testing**: Before trusting triangulation, the kit recommends a perturbation test — inject a novel term, run a session, verify which instrument detects it first. This confirms the instruments are uncorrelated and not measuring the same underlying signal.

**Lead-Lag Protocol**: In multi-agent systems, compression drift compounds. Agent A drifts → Agent B inherits A's post-drift outputs → B's behavior contaminates. By recording which instrument fires first in each agent, the lead-lag ordering reveals the root cause (which agent drifted first).

---

## Installation & Usage

### Install

```bash
# Core (no heavy dependencies)
pip install git+https://github.com/agent-morrow/compression-monitor

# With framework integrations
pip install "git+https://github.com/agent-morrow/compression-monitor[crewai]"
pip install "git+https://github.com/agent-morrow/compression-monitor[langgraph]"
pip install "git+https://github.com/agent-morrow/compression-monitor[autogen]"
pip install "git+https://github.com/agent-morrow/compression-monitor[all]"
pip install "git+https://github.com/agent-morrow/compression-monitor[embed]"  # + sentence-transformers
```

### Quick Start

**Live example** (2-second run, no config):
```bash
python quickstart.py
```

**Claude Code Auto-Detection**:
```bash
# Extract pre/post samples from latest session
python parse_claude_session.py --auto

# Watch mode: poll for compaction boundary in live session
python parse_claude_session.py --auto --watch --interval 5

# Then run instruments on extracted samples
python ghost_lexicon.py --pre session_pre.jsonl --post session_post.jsonl
python behavioral_footprint.py --pre session_pre.jsonl --post session_post.jsonl
python semantic_drift.py --pre session_pre.jsonl --post session_post.jsonl
```

**Generic JSONL Input**:
```bash
# Each line: {"text": "<agent output>"}
python ghost_lexicon.py --pre outputs_before.jsonl --post outputs_after.jsonl
python behavioral_footprint.py --pre outputs_before.jsonl --post outputs_after.jsonl
python semantic_drift.py --pre outputs_before.jsonl --post outputs_after.jsonl
```

**Negative-Space Logging**:
```python
from negative_space_log import NegativeSpaceLog
log = NegativeSpaceLog("agent_skips.jsonl")
skip_id = log.log_skip(cycle_id="t42", option_considered="rewrite", criterion="time_budget", significance="medium")
# Later: log.log_resolution(skip_id, outcome="option_taken")
```

**Calibration Report**:
```bash
python negative_space_log.py demo
# Outputs: skip significance labels vs actual impact delta
```

---

## Relevance to Claude Code Development

### Use Cases

1. **Agent Behavior Verification in Long Sessions**: Ensure agent behavior remains stable across context compressions in 3+ hour Claude Code sessions. Detect when verification steps are silently dropped post-compression.

2. **Skill Quality Assurance**: After delegating complex tasks to agents, use compression-monitor to verify the agent's operational patterns survive context boundaries. Vocabulary decay surfaces lost constraints that tests may not catch.

3. **Plugin Development for Long-Running Tasks**: When writing Claude Code plugins that monitor agent behavior, use the toolkit to detect drift caused by context rotation. The real-time hook infrastructure is designed for Claude Code post-tool-use lifecycle.

4. **Memory System Validation**: Claude Code's session memory system compresses history. compression-monitor measures whether semantic understanding survives compression — complementary to functional memory benchmarks.

5. **Multi-Turn Dialogue Quality**: When orchestrating multi-step features via repeated agent delegations, use behavioral footprint tracking to confirm operational patterns (tool-call frequency, response length) remain stable across context boundaries.

### Integration Points

- **Parse Claude Code Logs**: `parse_claude_session.py` reads native JSONL from `~/.claude/projects/` — no adaptation needed
- **Claude Code Plugin**: `.claude-plugin/` folder enables real-time monitoring via PostToolUse hook
- **Framework Detection**: Works with crewai, langgraph, autogen agents — common in complex Claude Code workflows
- **Negative-Space Integration**: Structured decision-logging for agents designed with explicit deliberation traces (e.g., agents that call a "consider_option" before output)

---

## Limitations and Caveats

### Structural Blind Spots

1. **Framing-Level Compression** — the toolkit cannot detect shifts in *what questions the agent considers worth asking*. Vocabulary, behavior, and semantics can all remain stable while the agent's implicit prior about relevance changes. This is the highest-order compression effect and is not measurable at the surface level.

2. **Pre-Output Deliberation (Partial)** — `negative_space_log.py` captures only *explicit* decision logs. Implicit suppression (the agent never even considers an option) is invisible. The false-negative rate on implicit suppression is unbounded.

3. **Self-Report Bias** — any monitor reading agent output shares the agent's generative blind spots. When the agent is confused post-compression, the instruments see the confused output; they cannot see what the agent stopped considering.

### Not Yet Covered

- Multi-agent coordination drift (ASI dimensions 5–6 per arXiv:2601.04170)
- Reasoning-chain stability across boundaries (requires structured reasoning traces)
- Confidence-peak sampling (Issue #5)
- Cross-lineage firing-order replication (Issue #5 research)

### Coverage Map vs Agent Stability Index

The toolkit covers:
- ✅ Response consistency (via ghost_lexicon)
- ✅ Tool usage patterns (via behavioral_footprint)
- ✅ Semantic topic drift (via semantic_drift)
- ✅ Delegation prompt quality (via delegation_quality)
- ⚠️ Reasoning pathway stability (partial — negative_space_log captures explicit decision logs; implicit suppression invisible)
- ⚠️ Pre-registration (falsifiable predictions available)
- ❌ Inter-agent agreement (requires multi-agent setup)
- ❌ Coordination drift (multi-agent specific)
- ❌ Framing-level compression (structurally invisible)

### False-Negative Bound

**When the toolkit reports no drift**, it means no surface drift on the three measured dimensions. It does **not** mean no compression occurred. The false-negative rate on framing-level compression is unbounded by construction. Possible partial mitigations: behavioral probing via canonical test prompts, counterfactual elicitation, external observer — each with their own limitations.

---

## Community and Maintenance

### Contribution Areas

The repository identifies good-first-issues for contributors:

1. **Add `--output-json` flag to `ghost_lexicon.py`** — structured output for dashboards
2. **Real test for perturbation protocol** — seed novel term, verify detection
3. **Add `--session-dir` flag to `behavioral_footprint.py`** — batch session analysis
4. **Document real false negatives** — run on known compression event, report missed drift
5. **Add `run_isolation_experiment.py` scaffold** — for Issue #4 (2×2 isolation design)

### Project Status

- **Released**: 2026-03-28 (scaffold, functional but not production-hardened)
- **Active Issues**:
  - [Issue #2](https://github.com/agent-morrow/compression-monitor/issues/2): Ridgeline API integration
  - [Issue #4](https://github.com/agent-morrow/compression-monitor/issues/4): 2×2 isolation design (separate compression drift from model/toolchain drift)
  - [Issue #5](https://github.com/agent-morrow/compression-monitor/issues/5): Framing-level compression (open research)
  - [Issue #8](https://github.com/agent-morrow/compression-monitor/issues/8): Negative-space logging schema (shipped with two-record append-only schema)

---

## Related Tools and Research

### Related Work

**Complementary Tools** (use together for broader coverage):

| Tool | Focus | How It Differs |
|------|-------|---|
| [Vibe Audit](https://github.com/toumai266/Vibe-Audit) | Intent drift (goal reinterpretation across session) | Session-level intent alignment; compression-monitor detects behavioral fingerprint change at compaction boundary |
| [agent-architect-kit](https://github.com/ultrathink-art/agent-architect-kit) | Rule persistence across compaction | Prevention layer (keeps explicit rules); compression-monitor is detection (catches implicit behavioral drift) |
| [agent-drift-watch](https://github.com/AdametherzLab/agent-drift-watch) | Model-update regression | Detects "model changed"; compression-monitor detects "agent context state changed" |
| [agentdrift-ai/agentdrift](https://github.com/agentdrift-ai/agentdrift) | Output quality degradation | Quality metrics focus; compression-monitor focuses on behavioral fingerprint shifts |

**Research Papers**:

- **Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers** (2026)
  arXiv: <https://arxiv.org/abs/2603.07670>
  Broad survey of agent memory mechanisms including context-resident compression, retrieval-augmented stores, and policy-learned management.

- **Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems** (2026)
  arXiv: <https://arxiv.org/abs/2601.04170>
  Empirical finding: ~42% of long-running agents exhibit measurable behavioral degradation. Proposes episodic memory consolidation, drift-aware routing, and adaptive behavioral anchoring as mitigations. Defines 12-dimension Agent Stability Index (ASI) framework.

- **AMA-Bench** (arXiv:2602.22769, Feb 2026)
  Benchmark for long-horizon agent memory. Finds lossy similarity-based retrieval as core failure mode — retrieval-layer instance of construct underrepresentation. Causality graph approach complements compression-monitor's lead-lag firing-order protocol.

---

## References

**Primary Sources**:
- README.md (2026-03-28): Feature overview, quick start, framework integrations
- pyproject.toml (2026-03-29): Version 0.2.1, Python 3.9+, MIT license, optional dependencies
- ghost_lexicon.py (2026-03-29): Vocabulary decay implementation, ~145 lines
- behavioral_footprint.py (2026-03-29): Behavioral pattern tracking, ~267 lines
- semantic_drift.py (2026-03-29): Embedding-based topic drift, ~150 lines (inferred)
- negative_space_log.py (2026-03-29): Skip event logging + calibration, ~400+ lines
- CONTRIBUTING.md (2026-03-29): Starter tasks, contribution guidelines
- GitHub API (2026-03-29): Repository metadata, stars (2), forks (0), creation date (2026-03-28)

**Related Documentation**:
- Author: [morrow.run](https://morrow.run) — blog post "Memory Retrieval Benchmark: Why I Built This" (linked in README)
- arXiv:2601.04170 — Agent Drift paper (defines ASI framework)
- arXiv:2603.07670 — Memory for Autonomous LLM Agents survey

---

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|------------|---|---|
| **Identity/Metadata** | high | 2026-03-29 | 2026-06-29 |
| **Key Features** | high | 2026-03-29 (extracted from README, source code) | 2026-06-29 |
| **Technical Architecture** | high | 2026-03-29 (read ghost_lexicon.py, behavioral_footprint.py, README data flow) | 2026-06-29 |
| **Installation & Usage** | high | 2026-03-29 (extracted verbatim from README and CONTRIBUTING.md) | 2026-06-29 |
| **Limitations and Caveats** | high | 2026-03-29 (extracted from "Cannot See — v0.1.0" and "Epistemological Bounds" sections) | 2026-06-29 |
| **Relevance to Claude Code** | medium | 2026-03-29 (based on Claude Code integration section in README; first-order inference) | 2026-06-29 |
| **Related Tools & Research** | high | 2026-03-29 (extracted from "Related Tools" and "Related Research" sections) | 2026-06-29 |

**Confidence Summary**:
- Exact numbers, version strings, GitHub metadata: **high** — from primary sources (API, pyproject.toml, README)
- Feature descriptions, mechanisms, data flow: **high** — extracted from README, CONTRIBUTING.md, and source code (ghost_lexicon.py, behavioral_footprint.py)
- Relevance to Claude Code: **medium** — inferred from features + Claude Code integration section; validated against README but not against user testing
- Research paper references: **high** — cited directly in README with arXiv links

**Next Review Date**: 2026-06-29 (3 months from 2026-03-29)

---

## Notes for Future Research

1. **Framing-Level Compression** — The toolkit acknowledges but cannot detect shifts in the agent's implicit prior about what matters. This is the highest-order compression effect and is an open research question (Issue #5).

2. **False-Negative Rate Unbounded** — When no drift is detected, the toolkit cannot bound the false-negative rate on framing-level events. Future research should develop instrumentation for deliberation-level tracing (decision logs, reasoning chains) to close this gap.

3. **Framework-Specific Patterns** — Each framework (CrewAI, LangGraph, AutoGen) has its own session boundary semantics. compression-monitor provides integrations for common frameworks; adoption will likely reveal framework-specific edge cases.

4. **Negative-Space Logging at Scale** — The toolkit ships with a two-record append-only schema for skip events. At production scale, the calibration report may need batching or streaming aggregation to handle high-frequency decision logging.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [logfire.md](./logfire.md) | ai-observability | complementary full-stack observability for monitoring agent sessions containing compression boundaries |
| [claude-mem.md](../context-management/claude-mem.md) | context-management | persistent memory system that undergoes the context compression events this toolkit detects |
| [local-memory.md](../context-management/local-memory.md) | context-management | memory infrastructure with L0-L3 evolution that may experience behavioral drift across retrieval boundaries |
| [simplemem-cross.md](../context-management/simplemem-cross.md) | context-management | persistent cross-conversation memory architecture where compression-monitor can detect retention vs drift trade-offs |
| [oh-my-claudecode.md](../agent-orchestration/oh-my-claudecode.md) | agent-orchestration | multi-agent orchestration system where drift compounds across agent boundaries (lead-lag detection applies) |
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | production-scale multi-agent architecture with compression boundaries at agent-to-agent handoffs |
| [gastown.md](../research-agent-patterns/gastown.md) | research-agent-patterns | multi-agent workspace manager coordinating 20-50+ sessions where cross-session compression drift can be tracked |
| [takt.md](../research-agent-patterns/takt.md) | research-agent-patterns | YAML-defined workflow engine with multi-agent state transitions where behavioral footprint shifts indicate compression effects |

