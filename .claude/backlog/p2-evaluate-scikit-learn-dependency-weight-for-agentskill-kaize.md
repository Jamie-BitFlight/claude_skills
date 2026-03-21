---
name: Evaluate scikit-learn dependency weight for agentskill-kaizen cluster_sessions tool
description: The `cluster_sessions` tool in `plugins/agentskill-kaizen/mcp/server.py` uses `scikit-learn` (`KMeans`, `CountVectorizer`) for session clustering. scikit-learn pulls in ~40MB of transitive dependencies (numpy, scipy, joblib, threadpoolctl). The typical use case is clustering dozens of sessions, not thousands. The Phase 1-2 research produced no durable artifact evaluating library choices — `scikit-learn` was assumed from the backlog without validation. Investigate whether a lighter alternative (e.g., `pyclustering`, stdlib-based implementation, or just `numpy` directly) would suffice for this scale, and whether the KMeans-on-bag-of-words approach is even appropriate for tool-call sequence similarity.
metadata:
  topic: evaluate-scikit-learn-dependency-weight-for-agentskill-kaize
  source: agentskill-kaizen MCP server review (2026-02-18)
  added: '2026-02-18'
  priority: P2
  type: Feature
  status: needs-grooming
  issue: '#118'
  last_synced: '2026-03-21T03:46:33Z'
---

## Story

As a **developer using Claude Code skills**, I want to **evaluate scikit-learn dependency weight for agentskill-kaizen cluster_sessions tool** so that **the tooling becomes more capable and complete**.

## Description

The `cluster_sessions` tool in `plugins/agentskill-kaizen/mcp/server.py` uses `scikit-learn` (`KMeans`, `CountVectorizer`) for session clustering. scikit-learn pulls in ~40MB of transitive dependencies (numpy, scipy, joblib, threadpoolctl). The typical use case is clustering dozens of sessions, not thousands. The Phase 1-2 research produced no durable artifact evaluating library choices — `scikit-learn` was assumed from the backlog without validation. Investigate whether a lighter alternative (e.g., `pyclustering`, stdlib-based implementation, or just `numpy` directly) would suffice for this scale, and whether the KMeans-on-bag-of-words approach is even appropriate for tool-call sequence similarity.

## Context

- **Source**: agentskill-kaizen MCP server review (2026-02-18)
- **Priority**: P2
- **Added**: 2026-02-18
- **Research questions**: What clustering approaches work for short categorical sequences? Is cosine similarity on bag-of-words tool vectors meaningful for workflow comparison? What lightweight Python clustering libraries exist that don't pull in scipy?
