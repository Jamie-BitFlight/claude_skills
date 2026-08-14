# MCP Architecture Documentation Index

Complete documentation for adding Model Context Protocol (MCP) servers to claude_skills plugins.

---

## Overview

**Current State:** 1 of 27 plugins has MCP tooling
**Goal:** Universal MCP interface for all high-value plugins
**Pattern:** FastMCP with Python 3.11+ (PEP 723 scripts)

---

## Documents

### 1. [MCP Architecture Analysis](./mcp-architecture-analysis.md)
**Purpose:** Comprehensive analysis of MCP needs across all plugins
**Audience:** Technical leads, architects
**Key Sections:**
- Plugin MCP needs assessment (Tier 1/2/3)
- MCP philosophy and principles
- Design patterns and configuration
- Testing strategies
- Personal vs Plugin MCPs

**When to read:** Before planning MCP implementation

---

### 2. [MCP Implementation Roadmap](./mcp-implementation-roadmap.md)
**Purpose:** Phased rollout plan with timelines and metrics
**Audience:** Project managers, developers
**Key Sections:**
- 3-phase implementation plan (Q1-Q3 2026)
- Status matrix for all plugins
- Tool architecture patterns
- Testing strategy
- Success metrics
- Risk mitigation

**When to read:** When planning sprints or tracking progress

---

### 3. [MCP Quick Start Guide](./mcp-quickstart.md)
**Purpose:** Practical 30-minute tutorial for adding MCP to a plugin
**Audience:** Plugin developers
**Key Sections:**
- 7-step implementation guide
- Code templates and patterns
- Common patterns (CLI wrapping, file ops, progress)
- Debugging tips
- Completion checklist

**When to read:** When actively implementing MCP for a plugin

---

## Quick Links by Role

### For Architects
- Read: **MCP Architecture Analysis** → **Implementation Roadmap**
- Focus on: Design patterns, tool naming conventions, composition model

### For Project Managers
- Read: **Implementation Roadmap** → **Architecture Analysis** (Executive Summary)
- Focus on: Phases, timelines, success metrics, risk mitigation

### For Developers
- Read: **Quick Start Guide** → **Architecture Analysis** (MCP Server Design Pattern)
- Focus on: Step-by-step implementation, code patterns, testing

### For Plugin Maintainers
- Read: **Quick Start Guide** → **Implementation Roadmap** (Plugin Status Matrix)
- Focus on: Is your plugin in Phase 1/2/3? What tools are needed?

---

## Implementation Checklist

Use this checklist when adding MCP to a plugin:

### Planning Phase
- [ ] Read MCP Architecture Analysis
- [ ] Identify core operations needing MCP tools
- [ ] Check plugin status in Implementation Roadmap
- [ ] Review agentskill-kaizen MCP as reference

### Development Phase
- [ ] Follow Quick Start Guide steps 1-7
- [ ] Implement 4-6 core tools minimum
- [ ] Write unit tests for each tool
- [ ] Test with MCP Inspector
- [ ] Update plugin.json with MCP config

### Documentation Phase
- [ ] Add MCP Server section to README
- [ ] Document all tools (inputs, outputs, annotations)
- [ ] Create usage examples
- [ ] Update CHANGELOG

### Quality Phase
- [ ] Run pytest with >90% coverage
- [ ] Verify all tools have proper error handling
- [ ] Test tool chaining (integration tests)
- [ ] Validate type hints and docstrings
- [ ] Complete Quality Checklist in Roadmap

---

## Reference Implementations

### Proven Example
**Plugin:** agentskill-kaizen
**Location:** `plugins/agentskill-kaizen/mcp/server.py`
**Tools:** 6 (process mining, clustering, pattern detection)
**Quality:** Production-ready

**Key Features to Study:**
- PEP 723 inline metadata
- Async tool implementation
- Progress reporting via context
- Tool annotations (readOnlyHint, etc.)
- ToolError usage
- Helper function patterns (`_resolve_glob`, `_build_event_log`)

---

## External Resources

### MCP Protocol
- **Spec:** <https://modelcontextprotocol.io/specification/draft>
- **Sitemap:** <https://modelcontextprotocol.io/sitemap.xml> (use this to find docs)

### SDKs
- **Python SDK:** <https://github.com/modelcontextprotocol/python-sdk>
- **TypeScript SDK:** <https://github.com/modelcontextprotocol/typescript-sdk>
- **FastMCP:** <https://github.com/jlowin/fastmcp>

### Tools
- **MCP Inspector:** `npx @modelcontextprotocol/inspector <command>`
- **uv (Python):** <https://github.com/astral-sh/uv>

### Warp-Specific
- **Warp MCP Docs:** <https://docs.warp.dev/agent-platform/capabilities/mcp>
- **Warp University Examples:** <https://app.gitbook.com/o/-MbqIZLCtzerswjFm7mh/s/c5dAwvMCRiTxUOdDicqy/>

---

## Priority Plugins for MCP (Phase 1)

| Plugin | Tools Needed | Why Priority | ETA |
|--------|--------------|--------------|-----|
| **plugin-creator** | 6 (validation, scaffolding) | Critical for ecosystem health | Feb 2026 |
| **python3-development** | 6 (quality, testing) | High usage, Python focus | Feb 2026 |
| **holistic-linting** | 6 (linter orchestration) | Cross-cutting concern | Feb 2026 |

**Next Steps:**
1. Review architecture analysis
2. Assign developers to each plugin
3. Use Quick Start Guide for implementation
4. Track progress in roadmap

---

## FAQ

### Why MCP instead of just scripts?
- **Standardization:** Consistent interface across all plugins
- **Discoverability:** Tools auto-discovered by agents
- **Composition:** Tools can be chained programmatically
- **Error Handling:** Well-defined error propagation
- **Testing:** Tools are isolated, testable units
- **Documentation:** Tool schemas serve as API docs

### Do all plugins need MCP?
No. Only plugins with programmatic tooling benefit from MCP. Knowledge-based plugins (skills only) don't need MCP servers.

### Can I use TypeScript instead of Python?
Yes! gitlab-skill is planned for TypeScript. The patterns are similar. See TypeScript SDK docs.

### How do personal MCPs differ from plugin MCPs?
- **Plugin MCPs:** Distributed with plugin, versioned, universal interface to plugin tools
- **Personal MCPs:** User-added (GitHub, Sentry, etc.), individual agent customization

### What if my plugin already has CLI scripts?
Perfect! Wrap them. Extract core logic, create MCP tool wrappers, keep CLI as convenience. See Quick Start Guide Pattern 1.

### How long does MCP implementation take?
- **Basic (1-2 tools):** 30 minutes
- **Comprehensive (6+ tools):** 2-4 hours
- **With tests & docs:** 4-6 hours

### Where do I get help?
1. Read the Quick Start Guide
2. Study agentskill-kaizen implementation
3. Test with MCP Inspector
4. Check FastMCP docs
5. Ask in team chat

---

## Document Relationships

```
MCP Architecture Analysis (What & Why)
           │
           ├──────────────────────┐
           │                      │
           ▼                      ▼
Implementation Roadmap      Quick Start Guide
(When & How Much)           (How & Step-by-Step)
           │                      │
           └──────────┬───────────┘
                      │
                      ▼
            plugin-creator MCP
            python3-development MCP
            holistic-linting MCP
                      │
                      ▼
              Phase 2 plugins...
```

---

## Next Actions

1. **Team Review** (Week 1)
   - Read Architecture Analysis
   - Discuss priorities and timeline
   - Assign Phase 1 plugins

2. **Template Creation** (Week 2)
   - Generate boilerplate for Phase 1
   - Document shared patterns
   - Set up CI for MCP testing

3. **Implementation** (Weeks 3-6)
   - plugin-creator MCP
   - python3-development MCP
   - holistic-linting MCP

4. **Retrospective** (Week 7)
   - Review learnings
   - Update documentation
   - Plan Phase 2

---

## Version History

- **2026-02-23:** Initial documentation suite created
  - MCP Architecture Analysis
  - MCP Implementation Roadmap
  - MCP Quick Start Guide
  - MCP Index (this document)

---

*For questions or updates to this documentation, contact the plugin-creator maintainers.*
