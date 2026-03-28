# OpenSpace: Self-Evolving Skills Engine for AI Agents

## Overview

OpenSpace is a self-evolving skills engine that enables AI agents to autonomously develop, refine, and share skills through real-world task execution. Rather than relying on static instruction sets, OpenSpace agents continuously improve their capabilities through automated feedback loops that capture successful patterns, fix broken workflows, and evolve specialized skill variants. The platform emphasizes three core capabilities: agents that learn from experience, dramatic cost reduction through skill reuse and optimization (46% fewer tokens observed), and collective intelligence through skill sharing across agent networks.

**Author/Org**: Data Intelligence Lab@HKU (HKUDS)
**License**: MIT
**Repository**: <https://github.com/HKUDS/OpenSpace>
**Latest Version**: v0.1.0
**Python Support**: ≥3.12

## Problem Addressed

Current AI agents—including Claude Code, OpenClaw, nanobot, and Cursor—face three critical limitations:

1. **Massive Token Waste**: Successful task patterns are not reused, requiring agents to reason from scratch and burn tokens on every similar task.
2. **Repeated Costly Failures**: Solutions are not shared across agents, causing repeated exploration and costly mistakes across the agent network.
3. **Poor and Unreliable Skills**: As tools and APIs evolve, skill reliability degrades silently, with no built-in mechanism to detect and repair failures or maintain community-contributed skill quality.

OpenSpace directly addresses these by introducing automated skill evolution, quality monitoring, and a collaborative skill registry where improvements discovered by one agent become immediately available to all connected agents.

## Key Statistics

- **1,700+ GitHub Stars** (as of March 28, 2026)
- **203 Forks**
- **Economic Performance**: 4.2× higher income vs. baseline ClawWork agents using identical backbone LLM (Qwen 3.5-Plus), earning $11,484 out of $15,764 available task value (72.8% capture) on 50 real-world professional tasks spanning 6 industries
- **Token Efficiency**: 45.9% token usage in Phase 2 (skill-reuse phase) vs. Phase 1 (cold start), demonstrating cost reduction through accumulated skills
- **Quality Improvement**: 70.8% average task quality, outperforming baseline agent (40.8%) by 30 percentage points
- **Evolved Skills**: 165 distinct skills autonomously evolved across benchmark experiments, with skills focused primarily on tool reliability and error recovery (44 file I/O skills, 29 execution recovery skills)

## Key Features

### 1. Self-Evolution Engine

OpenSpace implements three distinct evolution modes triggered automatically:

- **FIX**: Repairs broken or outdated instructions in-place within the same skill directory and name, producing a new version in a lineage DAG
- **DERIVED**: Creates enhanced or specialized variants from parent skills, stored in new directories and coexisting with parents to preserve the evolution tree
- **CAPTURED**: Extracts entirely novel reusable patterns from successful executions, creating brand-new skills with no parent

**Three Independent Triggers**:
- **Post-Execution Analysis** — Runs after every task, analyzing full execution recordings and suggesting FIX/DERIVED/CAPTURED actions for involved skills
- **Tool Degradation** — When tool success rates drop, a quality monitor identifies all dependent skills and batch-evolves them
- **Metric Monitor** — Periodic scan of skill health metrics (applied rate, completion rate, fallback rate) triggers evolution for underperformers

### 2. Full-Stack Quality Monitoring

Multi-layer tracking across the entire execution stack:
- **Skills**: applied rate, completion rate, effective rate, fallback rate
- **Tool Calls**: success rate, latency, flagged issues
- **Code Execution**: execution status, error patterns

When any component degrades (skill workflow or single tool call), cascade evolution automatically triggers for all upstream dependent skills, maintaining system-wide coherence.

### 3. Collective Agent Intelligence

Agents automatically share evolved skills through a cloud skill community:
- **Shared Evolution**: One agent's improvement becomes every agent's upgrade instantly
- **Network Effects**: More agents → richer execution data → faster evolution for every agent
- **Flexible Access Control**: Share skills publicly, within groups, or keep private
- **Smart Discovery**: Auto-imports relevant skills based on BM25 + embedding ranking and LLM filtering

### 4. Token Efficiency Through Skill Reuse

Real-world impact across 6 task categories:
- **Compliance & Forms**: +18.5% higher quality, −51% tokens (PDF skill chain evolved through 11 versions)
- **Document Generation**: +3.3% quality, −56% tokens (document-gen-fallback family evolved through 13 versions)
- **Engineering**: +8.7% quality, −43% tokens (multi-deliverable coordination skills)
- **Media Production**: +5.8% quality, −46% tokens (ffmpeg encoding fallbacks)
- **Spreadsheets**: +7.3% quality, −37% tokens (formula and merged-cell patterns)
- **Strategy & Analysis**: +1.0% quality, −32% tokens (document structure and multi-file orchestration reuse)

## Technical Architecture

### Core Components

**OpenSpace Class** (tool_layer.py):
- Central orchestrator managing LLM client, grounding client, recording manager
- Maintains references to skill registry, skill store, execution analyzer, and skill evolver
- Configures execution with model selection (separate models for tool retrieval, visual analysis, skill operations)
- Supports recording with optional screenshot/video capture and conversation logging

**Self-Evolution Engine** (skill_engine/):
- **SkillRegistry**: Discovery and ranking of skills using BM25 + embedding pre-filter and LLM-based selection
- **ExecutionAnalyzer**: Post-execution analysis with full agent loop and tool access to generate evolution suggestions
- **SkillEvolver**: Applies FIX/DERIVED/CAPTURED evolution with intelligent diffing and multi-file patching, includes retry-on-failure and anti-loop guards
- **SkillStore**: SQLite-based persistence with version DAG, quality metrics, and lineage tracking
- **SkillRanker**: Hybrid ranking combining BM25, embeddings, and execution history

**Grounding System** (grounding/):
- **GroundingClient**: Unified backend abstraction across shell, GUI (Computer Use), MCP servers (stdio/HTTP/WebSocket), and web tools
- **SearchTools**: Smart tool RAG using BM25 + embedding + LLM filtering
- **QualityManager**: Tool success rate tracking with automatic degradation detection and cascade evolution
- **Security**: Policies, sandboxing, and E2B integration for safe execution

**MCP Server Integration** (mcp_server.py):
OpenSpace exposes 4 tools to MCP clients:
- `execute_task` — Delegates task with auto-skill registration, search, and evolution
- `search_skills` — Standalone hybrid search across local and cloud skills
- `fix_skill` — Manually repair broken skills (FIX mode only)
- `upload_skill` — Upload local skills to cloud community

### Data Flow

```
User/Agent Task
    ↓
GroundingAgent (with injected skills from SkillRegistry)
    ↓
Skill Selection + Tool Use
    ↓
Tool Execution + Recording (screenshot, tool output, errors)
    ↓
ExecutionAnalyzer (post-execution LLM analysis)
    ↓
Evolution Suggestion (FIX/DERIVED/CAPTURED)
    ↓
SkillEvolver (autonomous diff generation + apply + retry)
    ↓
SkillStore (version DAG + lineage + metrics)
    ↓
Cloud Sync (if API key configured) + Skill Community Discovery
```

### Intelligent Evolution Safety

- **Confirmation gates** reduce false-positive triggers
- **Anti-loop guards** prevent runaway evolution cycles
- **Safety checks** flag dangerous patterns (prompt injection, credential exfiltration)
- **Validation gates** ensure evolved skills meet quality thresholds before replacing predecessors
- **Minimal diffs** — Produces targeted changes rather than full rewrites, with automatic retry on failure

## Installation & Usage

### Quick Start

```bash
git clone https://github.com/HKUDS/OpenSpace.git && cd OpenSpace
pip install -e .
openspace-mcp --help   # verify installation
```

For large clones (assets/ ~50MB), use sparse checkout:

```bash
git clone --filter=blob:none --sparse https://github.com/HKUDS/OpenSpace.git
cd OpenSpace
git sparse-checkout set '/*' '!assets/'
pip install -e .
```

### Path A: Integrate into Existing Agent (nanobot, Claude Code, OpenClaw, etc.)

**1. Add MCP server to agent config**:

```json
{
  "mcpServers": {
    "openspace": {
      "command": "openspace-mcp",
      "toolTimeout": 600,
      "env": {
        "OPENSPACE_HOST_SKILL_DIRS": "/path/to/your/agent/skills",
        "OPENSPACE_WORKSPACE": "/path/to/OpenSpace",
        "OPENSPACE_API_KEY": "sk-xxx (optional, for cloud)"
      }
    }
  }
}
```

**2. Copy host skills**:

```bash
cp -r OpenSpace/openspace/host_skills/delegate-task/ /path/to/your/agent/skills/
cp -r OpenSpace/openspace/host_skills/skill-discovery/ /path/to/your/agent/skills/
```

These two skills teach agents when and how to use OpenSpace's capabilities — no additional prompting required.

### Path B: Use as Standalone AI Co-Worker

**Interactive mode**:

```bash
openspace
```

**Execute task**:

```bash
openspace --model "anthropic/claude-sonnet-4-5" --query "Create a monitoring dashboard for my Docker containers"
```

**Python API**:

```python
import asyncio
from openspace import OpenSpace

async def main():
    async with OpenSpace() as cs:
        result = await cs.execute("Analyze GitHub trending repos and create a report")
        print(result["response"])
        for skill in result.get("evolved_skills", []):
            print(f"  Evolved: {skill['name']} ({skill['origin']})")

asyncio.run(main())
```

### Cloud Skill Management

```bash
# Download skill from community
openspace-download-skill <skill_id>

# Upload local skill
openspace-upload-skill /path/to/skill/dir
```

### Local Dashboard (requires Node.js ≥20)

```bash
# Terminal 1: Start backend API
openspace-dashboard --port 7788

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

The dashboard provides:
- Skill class browser with search and sorting
- Cloud skill record discovery and lineage
- Version evolution graph visualization
- Workflow session history and execution metrics

## Relevance to Claude Code Development

OpenSpace is directly compatible with Claude Code and other agent platforms that support MCP servers and skills:

1. **Claude Code Integration**: Plugs in via MCP server configuration in Claude Code's MCP settings, immediately enabling self-evolving skills and cloud community access
2. **Skill Format Compatibility**: Works with SKILL.md format used by Claude Code and other agents
3. **Real-World Validation**: Demonstrated autonomously building a complete live dashboard ("My Daily Monitor" with 20+ panels) entirely through evolved skills, proving viability for real development work
4. **Token Efficiency**: Documented 46% token reduction in Phase 2, directly reducing operational costs for Claude Code deployments
5. **Collective Intelligence**: Enables skill sharing across Claude Code agents through the cloud registry
6. **Automation-Friendly**: MCP server interface makes it easy for Claude Code agents to delegate complex tasks while skill evolution handles optimization

## Limitations and Caveats

1. **Early-Stage Code Quality**: OpenSpace is at v0.1.0 and being actively developed. The codebase shows signs of rapid iteration — not all modules have comprehensive documentation, and API stability is not guaranteed.

2. **Benchmark-Specific Performance**: The 4.2× income improvement and 46% token reduction were demonstrated on the GDPVal benchmark using Qwen 3.5-Plus. Results with different LLMs (Claude, GPT-4, etc.) are not documented. The benchmark included only 50 tasks across 6 categories — generalization to arbitrary tasks unknown.

3. **Evolution Trigger Tuning**: The three evolution triggers (post-analysis, tool degradation, metric monitor) require careful tuning. Over-aggressive triggering risks token waste; under-aggressive triggering misses improvement opportunities. Tuning guidance per task domain is not documented.

4. **Cloud Community Reliability**: The open-space.cloud skill registry depends on community contributions. No documented vetting process, version pinning strategy, or skill deprecation policy. Possible risks: outdated skills, breaking changes in evolved variants, skill namespace collisions.

5. **Safety Boundaries**: Anti-injection and sandboxing safeguards are mentioned but not detailed. The specific dangerous patterns flagged, scope of sandboxing (local-only vs. remote tools), and fallback behavior on sandbox violation are not documented.

6. **Skill Name Length Limitation**: Skill names truncated to 50 characters at word boundaries, potentially causing ambiguity for related skills with long, similar names.

7. **Limited Platform Support**: Grounding system supports shell, GUI (Computer Use), MCP, and web, but not all specialized tool ecosystems. Integration with proprietary tools, VPNs, or legacy systems not documented.

8. **Execution Recording Overhead**: Screenshot and video recording are optional but may impact performance on bandwidth-limited environments. Recording storage costs on local disk unconstrained in documentation.

## References

- **Main Repository**: <https://github.com/HKUDS/OpenSpace> (accessed 2026-03-28)
- **README**: <https://github.com/HKUDS/OpenSpace/blob/main/README.md> (accessed 2026-03-28)
- **GDPVal Benchmark Details**: <https://github.com/HKUDS/OpenSpace/tree/main/gdpval_bench> (accessed 2026-03-28)
- **Showcase (My Daily Monitor)**: <https://github.com/HKUDS/OpenSpace/tree/main/showcase> (accessed 2026-03-28)
- **pyproject.toml**: <https://github.com/HKUDS/OpenSpace/blob/main/pyproject.toml> (accessed 2026-03-28)
- **License**: MIT, Copyright (c) 2026 Data Intelligence Lab@HKU (accessed 2026-03-28)
- **Related Projects**:
  - AnyTool: <https://github.com/HKUDS/AnyTool>
  - ClawWork: <https://github.com/HKUDS/ClawWork>
  - WorldMonitor: <https://github.com/koala73/worldmonitor>
- **Web Portal**: <https://open-space.cloud> (accessed 2026-03-28)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [clawhub.md](../skill-generation-tools/clawhub.md) | skill-generation-tools | Public skill registry with vector search and versioning — complementary skill discovery mechanism to OpenSpace's cloud community |
| [skillsmp.md](../skill-generation-tools/skillsmp.md) | skill-generation-tools | 66,500+ skill marketplace with MCP server — overlapping use case for skill ecosystem and multi-agent reuse at scale |
| [everything-claude-code.md](../skill-generation-tools/everything-claude-code.md) | skill-generation-tools | 65+ skills + 16 agents with hook-based automation — shares skill optimization and reuse methodology with OpenSpace |
| [claude-skills-library.md](../skill-generation-tools/claude-skills-library.md) | skill-generation-tools | 205 production-ready skills with 9-phase quality gates — alternative approach to skill lifecycle management and quality tracking |
| [mcpskills-cli.md](../mcp-ecosystem/mcpskills-cli.md) | mcp-ecosystem | MCP-to-skill converter for polyglot output — feeds OpenSpace's skill discovery pipeline via standardized tool definitions |
| [ruflo.md](../agent-frameworks/ruflo.md) | agent-frameworks | 100+ specialized agents with RuVector self-learning layer — shares self-evolving agent design and skill reuse model |
| [oh-my-opencode.md](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | 37.5K-star production Claude Code orchestration with model routing — adjacent workflow: skill evolution improves agent coordination |
| [gastown.md](../research-agent-patterns/gastown.md) | research-agent-patterns | Multi-agent workspace manager with Dolt SQL ledger — potential integration point for OpenSpace skill versioning via SQL record store |

## Freshness Tracking

**Created**: 2026-03-28
**Next Review**: 2026-06-28
**Last Updated**: 2026-03-28

### Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Version, license, and author extracted directly from pyproject.toml and LICENSE file |
| Key Statistics | high | Star count and economic benchmark from official README and GitHub web interface; all numbers sourced from primary documentation |
| Key Features | high | Feature descriptions extracted directly from README.md sections on Self-Evolution, Quality Monitoring, and Collective Intelligence |
| Technical Architecture | medium-high | Core components documented in README code structure section and source files (tool_layer.py, evolver.py, mcp_server.py); data flow inferred from component relationships and README framework diagram |
| Installation & Usage | high | Installation steps, configuration examples, and CLI commands extracted verbatim from README.md and host_skills/README.md |
| Relevance to Claude Code | medium | Based on official compatibility statements in README (Claude Code listed as supported agent); specific integration examples from pyproject.toml MCP server and mcp_server.py; real-world validation through showcase project |
| Limitations | medium | Caveats identified from v0.1.0 versioning, missing tuning guidance in docs, cloud community governance not documented, safety mechanism details limited to high-level mentions |

