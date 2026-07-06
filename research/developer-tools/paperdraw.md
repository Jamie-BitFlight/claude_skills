---
title: "PaperDraw"
research_date: "2026-02-23"
source_url: "https://paperdraw.dev/"
github_url: "Not publicly available (closed-source / proprietary)"
version_at_research: "Unknown (side project / active development)"
license: "Proprietary (free to use, no open-source license identified)"
last_verified: "2026-02-23"
version_at_verification: "Unknown (active development, no versioning scheme identified)"
next_review: "2026-05-23"
---

## Overview

PaperDraw is a browser-based distributed systems simulator and system design tool that gamifies the process of learning software architecture. Users drag-and-drop real backend components onto a canvas, wire them together, and run live simulations to observe latency, throughput, error rates, and cache-hit ratios in real time. It bridges the gap between whiteboard architecture diagrams and production reality by allowing intentional failure injection — traffic spikes, cache crashes, component kills, and latency injection — before any code is written.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| System design is taught theoretically (boxes and arrows) with no feedback loop | Live simulation shows how architecture behaves under real traffic patterns in the browser |
| Engineers don't discover failure modes until 2am production incidents | Chaos injection (traffic spikes, component kills, cache crashes) surfaces failure modes safely |
| System design interview prep relies on rote memorization of patterns | Hands-on experimentation with real components builds intuitive understanding |
| Infrastructure-as-Code tools require provisioning real resources to test ideas | Simulator runs entirely in-browser with no cloud spend or deployment required |
| Understanding cascading failures requires lived experience | Visual propagation of errors through component graph makes cascade behavior tangible |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | N/A (closed-source) | 2026-02-23 |
| Public Repository | None identified | 2026-02-23 |
| Component Library | ~20+ backend components | 2026-02-23 |
| Pre-built Templates | Limited (e.g., "YouTube Simplified") | 2026-02-23 |
| Platform | Browser-based (Flutter web) | 2026-02-23 |
| Pricing | Free (no paywall identified) | 2026-02-23 |

---

## Key Features

### Visual Canvas & Component Library

- Drag-and-drop canvas for assembling distributed system architectures
- 20+ backend components: load balancers, app servers, caches (Redis), relational databases, message queues, CDNs, serverless functions, LLM gateways, vector databases, and more
- Wire components together visually to define data flow paths

### Real-Time Simulation

- Hit "Start Simulation" to watch traffic flow through every node
- Live metrics at each component: latency, throughput, error rates, cache-hit ratios
- Observe bottlenecks forming under normal load before injecting failures

### Chaos Engineering / Failure Injection

- **Traffic spike**: Flood entry point with 10× traffic to find bottlenecks
- **Cache crash**: Kill Redis mid-simulation to visualize the thundering herd problem
- **Component failure**: Drop an app server to test load balancer failover and redundancy
- **Latency injection**: Slow a downstream service to watch upstream queue cascades — surfaces the need for timeouts, circuit breakers, and message queues

### Learning Scenarios

- Iterative "play-test and fix" loop: build, break, recover, rebuild
- Pre-built scenario templates for common architectures (e.g., simplified YouTube)
- Quick decision cheat-sheet patterns built into workflow (e.g., slow reads → cache in front of DB)

### Target Use Cases

- System design interview preparation
- Founders and early-stage teams validating backend architecture decisions
- Engineers practicing chaos engineering concepts before production

---

## Technical Architecture

PaperDraw is built as a Flutter web application running entirely in the browser. The simulation engine is client-side — no backend infrastructure is provisioned; all metrics (latency, throughput, error rates) are computed by a simulation model rather than real network calls. This allows instant, zero-cost experimentation.

The tool uses a graph-based model where:
1. **Nodes** represent backend components (load balancer, cache, DB, queue, etc.)
2. **Edges** represent data flow / network connections between components
3. **Simulation engine** models traffic as flows through the graph, applying configurable failure scenarios to individual nodes or edges
4. **Metrics layer** computes per-node KPIs (latency, throughput, error rate, cache hit ratio) and renders them as live overlays on the canvas

The project is described as a side project, meaning the architecture prioritizes rapid iteration over enterprise-grade polish. It cannot export to actual infrastructure tooling (Terraform, Pulumi, etc.) — it is strictly a simulator and learning tool, not an IaC generator.

---

## Installation & Usage

No installation required — fully browser-based.

```
# Open in browser
https://paperdraw.dev/
```

**Basic workflow**:

```
1. Open https://paperdraw.dev/ in a modern browser (JavaScript required)
2. Drag components from the sidebar onto the canvas:
   - Start with: Load Balancer → App Server → Cache → Database
3. Connect components by drawing edges between them
4. Click "Start Simulation" to watch live traffic flow through the graph
5. Inject a failure from the chaos panel (e.g., kill the cache)
6. Observe cascading effects: latency spikes, error rates climb, DB load increases
7. Fix the architecture (add redundancy, circuit breakers) and re-run
```

**Recommended learning sequence** (from the article "System design just became a video game"):

```
Scenario 1: Traffic spike      → find the bottleneck app server, add a second instance
Scenario 2: Cache crash        → witness thundering herd, understand write-through caching
Scenario 3: Component failure  → verify load balancer rerouting and redundancy
Scenario 4: Latency injection  → understand why timeouts, circuit breakers, and queues exist
```

---

## Relevance to Claude Code Development

### Applications

- **Architecture review tool**: When Claude Code agents generate or review system architecture proposals, PaperDraw provides a mental model for validating that designs handle failure scenarios — useful as a reference tool when writing architecture documentation skills
- **System design skill development**: Developers using Claude Code to automate architecture documentation could reference PaperDraw's component taxonomy (load balancers, caches, queues, LLM gateways, vector DBs) as a standard vocabulary for distributed system descriptions
- **Interview preparation workflows**: Claude Code users building coaching or interview-prep tools can use PaperDraw concepts (chaos injection, cascading failures, thundering herd) as scenario seeds for system design practice skills

### Patterns Worth Adopting

- **Simulate before you build**: PaperDraw's "run simulation before writing code" philosophy maps directly to Claude Code's pattern of generating design documents and architecture reviews before implementation — validate structure, not just syntax
- **Failure-first thinking**: The chaos playbook (spike, crash, kill, slow) is a reusable mental model for writing resilience-focused code review skills that prompt engineers to consider failure modes at design time
- **Progressive complexity**: Start with 4 nodes (LB → app → cache → DB), then add complexity — a useful pattern for incremental scaffolding when Claude generates architecture templates or runbooks

### Integration Opportunities

- A Claude Code skill could use PaperDraw's component vocabulary to generate standardized system design diagrams or architecture documentation stubs from natural language descriptions
- A chaos engineering checklist skill could encode PaperDraw's four scenarios (traffic spike, cache crash, component failure, latency injection) as a review template for production readiness assessments
- When building agent workflows involving LLM gateways or vector databases, PaperDraw's component model (including LLM gateways and vector DBs as first-class nodes) could inform how Claude Code agents reason about AI-native system topologies

---

## References

- [PaperDraw — System Design Tool & Distributed Systems Simulator](https://paperdraw.dev/) (accessed 2026-02-23)
- [System design just became a video game — The AI Signals newsletter](https://www.theaisignals.com/p/system-design-just-became-a-video-game) (accessed 2026-02-23)
- [8 Top System Design Drawing Tools for Software Developers — dev.to](https://dev.to/abdelrahmanallam/8-top-system-design-drawing-tools-for-software-developers-3ol7) (accessed 2026-02-23)
- [Top 7 Tools for Creating System Design Diagrams — designgurus.io](https://www.designgurus.io/blog/top-7-tools-for-creating-system-design-diagrams) (accessed 2026-02-23)

---
