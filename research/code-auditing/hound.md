---
name: Hound - Autonomous AI Security Auditor with Knowledge Graphs
description: Hound is a language-agnostic AI auditor that autonomously builds and refines adaptive knowledge graphs for deep, iterative code reasoning in security audits. It introduces a relation-first graph...
license: Apache 2.0
metadata:
  topic: hound
  category: code-auditing
  source_url: https://github.com/scabench-org/hound
  version: "Commit Oct 15, 2025"
  verified: "2026-01-26"
  next_review: "2026-04-26"
---

## Overview

Hound is a language-agnostic AI auditor that autonomously builds and refines adaptive knowledge graphs for deep, iterative code reasoning in security audits. It introduces a relation-first graph engine that enables system-level reasoning across interrelated components in complex codebases.

**Core Value Proposition**: Transform manual security auditing into autonomous AI-driven analysis using flexible knowledge graphs, belief systems, and hypothesis-driven investigation.

---

## Problem Addressed

| Problem                                                      | How Hound Solves It                                                                        |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| Manual security audits are time-consuming and error-prone    | Autonomous agents build knowledge graphs and investigate vulnerabilities systematically    |
| LLM context windows cannot hold entire codebases             | Relation-first graphs enable precise retrieval of relevant code snippets across components |
| AI analyzers lack persistent reasoning across investigations | Belief system maintains long-lived vulnerability hypotheses with confidence scores         |
| Single-pass analysis misses cross-component vulnerabilities  | Multi-aspect graphs (value flows, auth roles, call graphs) enable system-level reasoning   |
| AI findings lack verification                                | QA finalizer confirms or rejects hypotheses using reasoning models                         |

---

## Key Statistics (as of January 26, 2026)

| Metric           | Value            |
| ---------------- | ---------------- |
| GitHub Stars     | 671              |
| Forks            | 135              |
| Contributors     | 9                |
| Open Issues      | 14               |
| Primary Language | Python (95%)     |
| Created          | August 24, 2025  |
| Last Push        | October 15, 2025 |

---

## Key Features

### 1. Graph-Driven Analysis

- **Flexible Agent-Designed Graphs**: Model any aspect of a system (architecture, access control, value flows, math)
- **Relational Graph Views**: High-level graphs support cross-aspect reasoning
- **Code Snippet Anchoring**: Precise retrieval of code backing each subsystem investigated
- **System Architecture Graph**: Automatic baseline graph generation

### 2. Belief and Hypothesis System

- **Persistent Hypotheses**: Long-lived vulnerability findings with confidence scores (0.0-1.0)
- **Evidence Accumulation**: Confidence updated as evidence accrues across sessions
- **Status Lifecycle**: `proposed` -> `investigating` -> `confirmed`/`rejected`
- **Severity Classification**: Critical, high, medium, low
- **Type Classification**: Reentrancy, access control, logic error, etc.

### 3. Dynamic Model Switching

- **Scout Models**: Lightweight models (GPT-4o-mini) handle exploration
- **Strategist Models**: Heavyweight models (GPT-5, Claude Opus) provide deep reasoning
- **Cost Efficiency**: Expert workflows mirrored while keeping costs efficient
- **Multi-Provider Support**: OpenAI, Anthropic, Google Gemini (Vertex AI)

### 4. Strategic Audit Planning

- **Coverage vs Intuition Balance**: Broad code coverage with focused investigation
- **Sweep Mode**: Systematic component analysis for initial discovery
- **Intuition Mode**: Deep, targeted exploration for high-impact vulnerabilities
- **Per-Session Planning**: PlanStore with statuses (planned, in_progress, done, dropped, superseded)

### 5. Interactive Steering (Chatbot UI)

- **Real-time Monitoring**: Live activity, plan, and findings
- **Manual Steering**: Guide investigations via web interface
- **Session Management**: Attach/detach from running audits
- **Manual Hypothesis Control**: Confirm/reject findings manually

---

## Technical Architecture

<eg>
User Input (Codebase Path)
         |
         v
+-------------------------+
|   Project Creation      |
|   - Code ingestion      |
|   - File whitelisting   |
+-------------------------+
         |
         v
+-------------------------+
|   Knowledge Graph Build |
|   - SystemArchitecture  |
|   - Custom aspects      |
|   - Graph refinement    |
+-------------------------+
         |
         v
+-------------------------+
|   Agent Audit           |
|   - Sweep mode          |
|   - Intuition mode      |
|   - Scout/Strategist    |
+-------------------------+
         |
         v
+-------------------------+
|   Hypothesis Store      |
|   - Evidence tracking   |
|   - Confidence scores   |
|   - Status management   |
+-------------------------+
         |
         v
+-------------------------+
|   QA Finalization       |
|   - Reasoning review    |
|   - Confirm/reject      |
+-------------------------+
         |
         v
+-------------------------+
|   Report Generation     |
|   - HTML output         |
|   - PoC integration     |
|   - Professional format |
+-------------------------+
</eg>

### Senior/Junior Pattern

The audit uses a two-tier agent architecture:

1. **Junior (Scout)**: Lightweight models for exploration and coverage
2. **Senior (Strategist)**: Heavyweight reasoning models for planning and deep analysis

### Graph Types

Hound supports multiple analyst-defined graph types:

- **SystemArchitecture**: Baseline component relationships
- **CallGraph**: Function call relationships across modules
- **ValueFlows**: Monetary and value transfer paths
- **AuthRoles**: Authentication and authorization relationships
- **ProtocolInvariants**: System-wide invariant tracking

---

## Audit Workflow

### Phase 1: Project Setup

```bash
# Create project from local code
./hound.py project create myaudit /path/to/code

# List projects
./hound.py project ls
```

### Phase 2: Build Knowledge Graphs

```bash
# Auto-generate graphs (recommended)
./hound.py graph build myaudit --auto \
  --files "src/A.sol,src/B.sol,src/utils/Lib.sol"

# Or manual graph creation
./hound.py graph custom myaudit \
  "Call graph focusing on function call relationships" \
  --iterations 2 --files "..."
```

### Phase 3: Run Audit

```bash
# Sweep: Systematic component analysis
./hound.py agent audit myaudit --mode sweep

# Intuition: Deep targeted exploration
./hound.py agent audit myaudit --mode intuition --time-limit 300

# With telemetry for interactive steering
./hound.py agent audit myaudit --mode intuition --telemetry
```

### Phase 4: Finalize and Report

```bash
# QA review with reasoning model
./hound.py finalize myaudit

# Generate professional HTML report
./hound.py report myaudit
```

---

## Benchmark Results (from Paper)

On a five-project subset of ScaBench:

| Metric       | Hound            | Baseline LLM |
| ------------ | ---------------- | ------------ |
| Micro Recall | 31.2%            | 8.3%         |
| F1 Score     | 14.2%            | 9.8%         |
| Precision    | Modest trade-off | Higher       |

**Key Insight**: Gains attributed to flexible relation-first graphs extending model understanding beyond call/dataflow to abstract aspects, plus the hypothesis-centric loop.

---

## Relevance to Claude Code Development

### Direct Applications

1. **Hypothesis-Driven Investigation**: Model for scientific verification workflows in Claude Code agents
2. **Knowledge Graph Patterns**: Approach for building contextual understanding of large codebases
3. **Belief System Design**: Pattern for maintaining confidence-scored findings across sessions
4. **Coverage Tracking**: Methods for ensuring systematic analysis of code components

### Patterns Worth Adopting

1. **Scout/Strategist Model Switching**: Cost-efficient model selection based on task complexity
2. **Graph-Based Code Navigation**: Precise retrieval using relationship-aware graphs
3. **Session Persistence**: Maintaining investigation state across interruptions
4. **Coverage vs Intuition Balance**: Balancing breadth and depth in analysis
5. **Interactive Steering**: Real-time human guidance during autonomous operations

### Integration Opportunities

1. **Security-Focused Skill**: Create Claude Code skill for security auditing workflows
2. **Hypothesis Pattern**: Adopt for verification and debugging workflows
3. **Graph Construction**: Patterns for building codebase knowledge graphs
4. **Report Generation**: Professional report templates for audit findings

---

## Installation & Usage

### Installation

**1. Clone Repository**

```bash
git clone https://github.com/scabench-org/hound.git
cd hound
```

**2. Install Dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure API Keys**

Set up environment variables for your LLM provider:

```bash
export OPENAI_API_KEY=your_key_here
# Optional: Anthropic, Google Vertex AI
export ANTHROPIC_API_KEY=your_key_here
```

**4. Configure Hound**

```bash
cp hound/config.yaml.example hound/config.yaml
# Edit hound/config.yaml with your preferred settings
```

Source: GitHub repository installation guide (accessed 2026-08-10).

### Configuration Options

**Model Configuration**:

- Scout model: Lightweight exploration (default: gpt-4o-mini)
- Strategist model: Deep reasoning (default: gpt-5)
- QA finalizer: Hypothesis review (default: gpt-5)

**Provider Support**:

- OpenAI (GPT-4, GPT-4o, GPT-5)
- Anthropic (Claude-3-Opus)
- Google Gemini via Vertex AI

**Graph Options**:

- Auto-generation with `--auto`
- Custom aspect definitions
- File whitelisting with `--files`
- Iteration control for refinement

---

## References

1. **GitHub Repository**: <https://github.com/scabench-org/hound> (accessed 2026-01-26)
2. **Academic Paper**: Mueller, B. "Hound: Relation-First Knowledge Graphs for Complex-System Reasoning in Security Audits" arXiv:2510.09633 [cs.CR] (2025-09-29)
3. **Paper Abstract**: <https://arxiv.org/abs/2510.09633> (accessed 2026-01-26)
4. **Author Walkthrough**: <https://muellerberndt.medium.com/hunting-for-security-bugs-in-code-with-ai-agents-a-full-walkthrough-a0dc24e1adf0>
5. **ScaBench Benchmark**: Referenced in paper as evaluation dataset
