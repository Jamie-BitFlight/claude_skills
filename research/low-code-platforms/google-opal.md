---
title: "Google Opal"
research_date: "2026-03-04"
source_url: "https://opal.google/landing/"
github_url: "N/A (closed-source Google experiment)"
version_at_research: "Experiment (no versioned releases; agent step launched February 24, 2026)"
license: "Proprietary (Google Terms of Service)"
last_verified: "2026-03-04"
version_at_verification: "Experiment — agent step (February 2026)"
next_review: "2026-06-04"
---

## Overview

Google Opal is an experimental no-code tool from Google Labs that lets users build, share, and remix AI-powered mini-apps by chaining together prompts, AI model calls, and tools through a natural-language interface and a visual drag-and-drop workflow editor. It targets prototyping, productivity automation, and proof-of-concept development without requiring any programming knowledge. As of February 2026, Opal added a first-class agent step that converts static linear workflows into dynamic agentic pipelines with memory, conditional routing, and interactive chat.

SOURCE: [Introducing Opal — Google Developers Blog](https://developers.googleblog.com/introducing-opal/) (accessed 2026-03-04)
SOURCE: [Build dynamic agentic workflows in Opal — Google Blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/opal-agent/) (accessed 2026-03-04)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Building AI-powered apps requires coding skills most users lack | Natural language descriptions generate fully functional visual workflows, no code required |
| Multi-step AI pipelines are hard to compose and debug | Visual step editor shows each prompt, model call, and tool connection explicitly |
| AI apps are difficult to share and distribute | Each finished Opal gets a shareable link; recipients run it with their own Google account |
| Static AI workflows cannot adapt to context or user input | Agent step uses Gemini to dynamically route between paths, query users, and remember state across sessions |
| Switching between AI tools (text, image, video) requires separate services | Opal integrates Gemini (text/reasoning), Imagen (image generation), and Veo (video/audio) in a single workflow |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | N/A (proprietary) | 2026-03-04 |
| Downloads/month | N/A (web app, no install) | 2026-03-04 |
| Contributors | N/A (Google internal) | 2026-03-04 |
| Countries available | 160+ | 2026-03-04 |
| Launch date | July 24, 2025 (US beta) | 2026-03-04 |
| Agent step launch | February 24, 2026 | 2026-03-04 |
| Pricing | Free (public beta, Google account required) | 2026-03-04 |

SOURCE: [Google Blog - Opal Agent Step](https://blog.google/innovation-and-ai/models-and-research/google-labs/opal-agent/) (accessed 2026-03-04)

---

## Key Features

### Workflow Creation

- Describe an app idea in natural language; Opal generates a visual multi-step workflow automatically
- Workflows chain prompts, AI model calls, and tool integrations into a directed graph
- Conversational mode: iterate by describing changes in natural language; Opal updates the workflow
- Visual editor mode: drag-and-drop steps, edit prompts inline, add/remove connections directly
- Both modes can be combined in the same session

SOURCE: [Introducing Opal — Google Developers Blog](https://developers.googleblog.com/introducing-opal/) (accessed 2026-03-04)

### AI Models Integrated

- **Gemini**: text generation, reasoning, and orchestration of other model calls
- **Imagen**: image generation within workflow steps
- **Veo**: video and audio generation within workflow steps
- **Gemini Flash** (agent step): autonomous model selection within the agent step, choosing tools like Web Search or Veo based on goal

SOURCE: [Google Blog - Opal Agent Step](https://blog.google/innovation-and-ai/models-and-research/google-labs/opal-agent/) (accessed 2026-03-04)

### Agent Step (launched February 2026)

The agent step converts a static pipeline into an agentic one that autonomously determines what tools and models to invoke given a stated goal.

- **Memory**: Persists information across sessions (user name, style preferences, running lists); each Opal's memory is private to the user running it
- **Dynamic routing**: Define multiple output paths with natural-language conditions; agent transitions to the correct path when conditions are met; used for branching logic such as "new client vs. existing client" briefings
- **Interactive chat**: Agent pauses to ask the user clarifying questions or present choices when required input is missing, then resumes the workflow with the gathered information

SOURCE: [Google Blog - Opal Agent Step](https://blog.google/innovation-and-ai/models-and-research/google-labs/opal-agent/) (accessed 2026-03-04)

### Sharing and Templates

- Each published Opal generates a shareable URL; anyone with the link and a Google account can run it
- Gallery of starter template Opals covering common use cases (content generation, research, productivity)
- Templates can be remixed: users fork a shared Opal and customize it without starting from scratch

SOURCE: [Introducing Opal — Google Developers Blog](https://developers.googleblog.com/introducing-opal/) (accessed 2026-03-04)

### Google Workspace Integration

- Connects to Google Docs, Sheets, Gmail, and Drive
- Workflows can read from and write to Workspace data without leaving Opal
- Enables automation of document-heavy tasks (e.g., summarize emails, populate spreadsheets, draft Docs)

SOURCE: [Google Opal Review 2026 — nocode.mba](https://www.nocode.mba/articles/google-opal-review) (accessed 2026-03-04)

---

## Technical Architecture

Opal follows a step-based directed-graph model for workflows:

```text
User description (natural language)
        |
        v
Opal workflow generator (Gemini)
        |
        v
Visual step graph
  [Step 1: Input] --> [Step 2: Gemini prompt] --> [Step 3: Imagen] --> [Step 4: Output]
                                  |
                          (agent step variant)
                                  v
                      Gemini Flash (autonomous)
                        - Selects tools dynamically
                        - Checks memory store
                        - Evaluates routing conditions
                        - Initiates chat if input missing
                        - Outputs to next step or user
```

Each step is a node that accepts typed inputs (text, image, video, file) and passes outputs to downstream steps. The agent step wraps this node type with an autonomous Gemini Flash loop that replaces manual model and tool selection.

Memory is stored per-user, per-Opal, and persists across independent runs. Dynamic routing is declared as natural-language conditions on outgoing edges from an agent step node.

SOURCE: [Google Blog - Opal Agent Step](https://blog.google/innovation-and-ai/models-and-research/google-labs/opal-agent/) (accessed 2026-03-04)
SOURCE: [Building AI Automations with Google Opal — KDnuggets](https://www.kdnuggets.com/building-ai-automations-with-google-opal) (accessed 2026-03-04)

---

## Installation & Usage

Opal is a web application with no installation required.

```text
# Access
1. Navigate to https://opal.google/
2. Sign in with a Google account
3. Click "New Opal" or pick a starter template from the gallery

# Creating a workflow (conversational)
Type a description such as:
  "Build an app that takes a topic, searches the web for recent articles,
   summarizes them, and generates a cover image."
Opal generates the step graph. Refine by typing additional instructions.

# Creating a workflow (visual editor)
- Click "+" to add a step
- Select step type: Generate (text/image/video), Agent, Input, Output, Tool
- Connect steps by dragging between output and input ports
- Configure each step's prompt or parameters in the sidebar

# Publishing and sharing
- Click "Share" to generate a public URL
- Recipients open the URL and run the Opal with their own Google account
- No Opal editing access is granted to recipients unless they explicitly remix it
```

SOURCE: [Introducing Opal — Google Developers Blog](https://developers.googleblog.com/introducing-opal/) (accessed 2026-03-04)

---

## Relevance to Claude Code Development

### Applications

- Opal demonstrates a no-code surface for composing multi-step AI workflows — the same compositional pattern Claude Code skills use (chaining agent calls, tool invocations, and prompts)
- The agent step's dynamic routing and memory model is directly analogous to how complex Claude skills chain sub-agents conditionally and pass context between them
- Opal's shareable mini-app model is a concrete precedent for how Claude skills could be distributed as runnable units with minimal setup

### Patterns Worth Adopting

- **Dual-mode editing**: Opal's combination of conversational editing and visual inspection reduces the cognitive load of composing multi-step pipelines; Claude skill authoring could benefit from a similar dual-mode experience
- **Natural language condition declarations for routing**: Describing branching conditions in plain language (rather than code) and having the model interpret them is a pattern applicable to Claude skill decision trees
- **Memory scoped per-user, per-artifact**: Opal scopes session memory to the (user, Opal) pair, preventing cross-contamination; a useful model for Claude skill state management in multi-user deployments
- **Template gallery for bootstrapping**: A curated gallery of remixable starter workflows accelerates adoption — directly applicable to a Claude skills marketplace

### Integration Opportunities

- Opal workflows that invoke external tools could surface Claude Code skills as tool steps via an MCP-compatible integration
- Research on Opal's agent step architecture (autonomous tool selection within a step) could inform how Claude's `research-curator` and `swarm-task-planner` agents select sub-agents dynamically
- Opal's Google Workspace integration pattern (read/write to Docs, Sheets, Gmail) is a model for how Claude skills could integrate with productivity suites via structured tool steps

---

## References

- [Introducing Opal: describe, create, and share your AI mini-apps](https://developers.googleblog.com/introducing-opal/) (accessed 2026-03-04)
- [Build dynamic agentic workflows in Opal](https://blog.google/innovation-and-ai/models-and-research/google-labs/opal-agent/) (accessed 2026-03-04)
- [Google Opal landing page](https://opal.google/landing/) (accessed 2026-03-04)
- [Google adds a way to create automated workflows to Opal — TechCrunch](https://techcrunch.com/2026/02/24/google-adds-a-way-to-create-automated-workflows-to-opal/) (accessed 2026-03-04)
- [Google Opal Review 2026 — nocode.mba](https://www.nocode.mba/articles/google-opal-review) (accessed 2026-03-04)
- [Building AI Automations with Google Opal — KDnuggets](https://www.kdnuggets.com/building-ai-automations-with-google-opal) (accessed 2026-03-04)
- [Google Labs Introduces Opal, a Visual Platform for Creating AI Mini-Apps — InfoQ](https://www.infoq.com/news/2025/07/google-opal-ai/) (accessed 2026-03-04)

---
