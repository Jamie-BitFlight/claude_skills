# CUA (Computer-Use Agents) — Improvement Proposals

**Research Entry Date:** 2026-05-03
**Source:** ./research/agent-infrastructure/cua.md
**Extracted By:** Research-Insight-Extractor

---

## 1. Integration Opportunity: Claude-CUA Agent Framework

**Category:** Strategic Integration
**Priority:** HIGH
**Effort:** Medium

**Observation:**
CUA is agent-agnostic and explicitly supports "any LLM provider" including Claude. No documented guidance exists for running Claude agents within CUA's environment abstraction and benchmarking framework.

**Proposal:**
Create a Claude-CUA integration skill that provides:
- Agent templates optimized for CUA's action/perception primitives (click, keyboard, scroll, screenshot)
- Configuration guides for Claude (Opus, Sonnet, Haiku) as the decision-making layer
- Reference implementation for integrating Claude with OSWorld, ScreenSpot, and Windows Arena benchmarks
- Multi-step task decomposition patterns using Claude's tool use and vision capabilities

**Why This Matters:**
- Reduces friction for users wanting to run Claude agents in CUA sandbox environments
- Positions Claude agents as a first-class choice in the CUA ecosystem
- Creates a feedback loop: benchmark results inform model capability improvements
- Reference implementation becomes reusable across users

**Output Artifact:**
`skills/cua-claude-integration/SKILL.md` with:
- CUA environment setup walkthrough (sandbox selection, H.265 video capture)
- Claude agent template (vision loop, tool definitions for screen interaction)
- Benchmark integration example (OSWorld dataset, trajectory export, metric calculation)
- Troubleshooting guide (video encoding, clipboard sharing, multimodal interaction)

---

## 2. Documentation Gap: Platform-Specific Best Practices

**Category:** Knowledge Artifact
**Priority:** MEDIUM
**Effort:** Low-Medium

**Observation:**
CUA supports macOS (Cua Driver, Lume, Parallels), Linux (Docker, QEMU/KVM), Windows (VirtualBox, generic VM), and Android, but the research entry provides no detail on:
- When to choose Cua Driver vs. VM-based sandbox
- Performance characteristics and latency profiles per platform
- Limitations and strengths of each runtime option
- Cost/performance trade-offs (native vs. virtualized)

**Proposal:**
Create a reference document: `./research/references/cua-platform-comparison.md` with:
- Runtime selection flowchart (agent requirements → optimal environment)
- Latency profiles for each environment (screenshot capture, action execution)
- Multi-platform agent deployment patterns (e.g., develop on Docker/Linux, deploy on macOS native)
- Video encoding trade-offs (H.265 efficiency, decoding overhead on different hardware)

**Why This Matters:**
- Guides users toward appropriate environment choices for their workload
- Reduces deployment friction and surprises
- Enables informed scaling decisions (cost, speed, reliability)

---

## 3. Integration Gap: CUA Evaluation Results Export to Claude Skills Repository

**Category:** Process Integration
**Priority:** MEDIUM
**Effort:** High

**Observation:**
CUA has evaluation-first design with trajectory export, OSWorld/ScreenSpot/Windows Arena integration, but no standardized path for:
- Capturing agent performance metrics (success rate, step count, time)
- Analyzing failure modes (where did the agent get stuck?)
- Feeding results back into agent improvement cycles
- Comparing model performance across benchmarks (Opus vs. Sonnet on same task)

**Proposal:**
Define a CUA evaluation integration protocol:
1. Export trajectories and metrics to `.tmp/scratch/cua-benchmarks/{date}-{benchmark}.json`
2. Script to parse trajectories, extract failure signatures (visual recognition, UI parsing, action execution)
3. Reference implementation using Claude vision to analyze failure screenshots
4. Pipeline to update skill documentation with real-world evidence (success rates, typical failure modes per agent model)

**Why This Matters:**
- Closes the feedback loop: benchmarks → insights → skill improvements
- Provides empirical evidence for skill design decisions (which Claude model for which task type?)
- Enables comparative analysis across agent architectures

---

## 4. Documentation Addition: Accessibility & Non-Disruption Design

**Category:** Design Principle
**Priority:** MEDIUM
**Effort:** Low

**Observation:**
Research entry mentions Cua Driver's "non-disruptive automation" and "no accessibility surface modifications," but provides no detail on:
- How CUA preserves user workflows while agent operates
- Conflict resolution when agent and user interact simultaneously
- Visual feedback mechanisms (does user see agent actions?)
- Safety patterns for critical operations (financial, medical, safety-critical systems)

**Proposal:**
Add reference document: `./research/references/cua-safety-patterns.md`
- Non-disruption principles (background automation vs. user intervention)
- Conflict detection and resolution (mutual exclusion, priority rules)
- Logging and audit trail design for accountability
- User safety patterns (readonly mode, simulation, approval gates)

**Why This Matters:**
- Informs responsible agent deployment
- Critical for regulated industries (healthcare, finance, critical infrastructure)
- Differentiates CUA from simpler automation tools

---

## 5. Skill Content Opportunity: CUA Troubleshooting Guide

**Category:** Knowledge Artifact
**Priority:** LOW
**Effort:** Medium

**Observation:**
Installation paths are documented, but no guidance on common failure modes:
- Container/VM setup issues (network, display drivers, X11)
- Video encoding problems (H.265 codec support, decoding performance)
- Clipboard sharing failures (platform-specific permission issues)
- Multimodal interaction debugging (audio/video sync, latency diagnosis)

**Proposal:**
Create skill: `/plugin-creator:cua-troubleshooting`
- Common installation errors and resolution paths
- Environment diagnostics (check video codec support, bandwidth, latency)
- Integration debugging (SDK connection, action/perception latency)
- Performance profiling (benchmark your setup)

**Why This Matters:**
- Reduces support burden and user frustration
- Accelerates first-run success
- Collects common issues for upstream bug reports

---

## Summary

| # | Category | Priority | Improvements Proposed | Effort |
|---|----------|----------|----------------------|--------|
| 1 | Integration | HIGH | Claude-CUA Agent Framework | Medium |
| 2 | Documentation | MEDIUM | Platform-Specific Best Practices | Low-Med |
| 3 | Process | MEDIUM | Evaluation Results Export Integration | High |
| 4 | Documentation | MEDIUM | Accessibility & Non-Disruption Design | Low |
| 5 | Skill | LOW | CUA Troubleshooting Guide | Medium |

**Immediate Action Items:**
- None requiring immediate escalation. Research entry is complete and well-structured.
- Recommend prioritizing **Improvement #1** (Claude-CUA Integration) for strategic value.

---

**Recommendations for Integration:**
1. Cross-reference this insights file with `/dh:create-backlog-item` for skill development tasks
2. Use Improvement #2 as input to existing CUA documentation audit
3. Ensure Improvement #3 includes performance metrics schema aligned with SAM task tracking
