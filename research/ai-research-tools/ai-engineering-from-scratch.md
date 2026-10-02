---
name: ai-engineering-from-scratch
title: AI Engineering from Scratch
subtitle: Comprehensive 523-lesson curriculum covering math, ML, agents, and production AI systems
research_date: 2026-10-02
source_url: https://github.com/rohitg00/ai-engineering-from-scratch
github_repository: https://github.com/rohitg00/ai-engineering-from-scratch
version_at_research: main (active development, shallow clone 2026-10-02)
license: MIT
freshness_tracking:
  last_verified: 2026-10-02
  version_at_verification: main
  next_review: 2027-01-02
  confidence_map: "Overview: high | Problem Addressed: high | Key Features: high | Technical Architecture: high | Installation & Usage: high | Relevance to Claude Code Development: medium"
---

# AI Engineering from Scratch

## Overview

AI Engineering from Scratch is a comprehensive, open-source curriculum comprising 523 lessons organized across 20 phases, covering approximately 342 hours of material. The curriculum spans math foundations through autonomous systems, with implementations available in Python, TypeScript, Rust, and Julia. Each lesson is structured to deliver a reusable artifact—a prompt, skill, agent, or Model Context Protocol (MCP) server. The resource is hosted on GitHub, MIT-licensed, and freely accessible. A website at <https://aiengineeringfromscratch.com> provides interactive learning alongside the GitHub-based lessons.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Fragmented AI learning materials scattered across disparate sources | Unified 20-phase curriculum organizing AI education from mathematical foundations through production systems |
| Students using AI tools without understanding foundational concepts | Build-from-scratch approach where every algorithm is implemented before abstraction libraries appear |
| Lack of hands-on, project-oriented AI education | Every lesson includes code implementation, quiz, and tangible artifacts (prompts, skills, agents, MCP servers) |
| Gap between theoretical understanding and production-ready skills | Structured progression from math → ML → deep learning → LLMs → agents → autonomous systems → production |
| Limited exposure to practical AI engineering practices (MCP, agent design, prompt engineering) | Dedicated phases (13-16) for tools, protocols, agents, autonomous systems, and swarms |

---

## Key Features

### Curriculum Structure

- **20 Phases** spanning 523 lessons organized sequentially: Phase 0 (Setup & Tooling) through Phase 19 (Capstone Projects)
- **Estimated Duration**: ~342 hours at self-paced learning
- **Foundation to Production**: Linear algebra and calculus at the base, autonomous swarms at the apex
- **Each lesson** follows the same methodology: Read conceptual documentation, derive mathematics, write code, run test, keep artifact

### Learning Paths and Specializations

The curriculum offers 12 structured learning paths targeting specific goals:
- Agent-Assisted Engineering (using coding agents on real repositories)
- Agent Skills Engineering (writing and shipping agent skills)
- Agentic AI Engineer
- Applied AI Engineer
- AI Data Engineer
- Forward-Deployed AI Engineer
- AI Evaluation & Reliability Engineer
- AI Developer Relations Engineer
- Software Engineering Fundamentals
- Model Context Protocol (MCP) path (17-lesson route)
- Shaping the Build (product judgment and delivery)
- Building and Deploying AI Applications

### Interactive Agent Skills

The curriculum includes 11 installable agent skills for integration with Claude Code and other compatible hosts:
- `start-learning`: Placement quiz and personalized study plan
- `learn`: Lesson delivery with concept, math, code, and quiz per session
- `learn-agent-skills`: Focused path for Agent Skills Engineering
- `learn-mcp`: Model Context Protocol specialization
- `check-understanding`: Phase-specific quizzes
- `course-guide`: Contextual lesson recommendations
- `build-project`: Project scaffolding
- `claude-certification`: Claude AI certification preparation
- `mcpa-certification`: Model Context Protocol Associate (MCPA) certification preparation
- `find-your-level`: Placement assessment
- `start-learning`: Placement tutor with prerequisites guide

Installation via `npx skills add rohitg00/ai-engineering-from-scratch` (requires Node.js and a compatible agent host).

### Certification Programs

Two structured certification pathways:
- **Claude Certification**: Academy on website with structured preparation materials
- **MCPA (Model Context Protocol Associate)**: Official MCP certification track aligned with 17-lesson protocol curriculum

### Multi-Language Support

Implementations available in Python, TypeScript, Rust, and Julia. Many lessons offer multiple language options; learners select their primary language for hands-on practice.

---

## Technical Architecture

### Phased Architecture (20 Layers)

The curriculum uses a strict layered architecture where each phase builds on its predecessors:

1. **Phase 0**: Setup & Tooling (~14 hours)
2. **Phase 1**: Math Foundations (~23 hours) — linear algebra, calculus, probability
3. **Phase 2**: ML Fundamentals (~21 hours) — regression, classification, trees, forests, ensemble methods
4. **Phase 3**: Deep Learning Core (~15 hours)
5. **Phase 4**: Computer Vision
6. **Phase 5**: NLP Foundations to Advanced
7. **Phase 6**: Speech and Audio
8. **Phase 7**: Transformers Deep Dive
9. **Phase 8**: Generative AI — VAE, GANs, 3D generation, visual autoregressive models
10. **Phase 9**: Reinforcement Learning
11. **Phase 10**: LLMs from Scratch
12. **Phase 11**: LLM Engineering — prompt engineering, production LLM applications
13. **Phase 12**: Multimodal AI
14. **Phase 13**: Tools and Protocols — MCP fundamentals through advanced integration
15. **Phase 14**: Agent Engineering — agent loops, agent workbench, coding agents
16. **Phase 15**: Autonomous Systems
17. **Phase 16**: Multi-Agent and Swarms
18. **Phase 17**: Infrastructure and Production
19. **Phase 18**: Ethics, Safety, and Alignment
20. **Phase 19**: Capstone Projects

### Content Organization per Lesson

Each lesson contains:
- `docs/en.md` — Conceptual explanation and problem statement
- `code/` — Language-specific implementations (Python, TypeScript, Rust, Julia where available)
- `notebook/` — Jupyter notebook format (when applicable)
- `outputs/` — Expected outputs and results
- `quiz.json` — Assessment questions
- `assets/` — Images and reference materials

### Website Integration

- Canonical lessons available at <https://aiengineeringfromscratch.com> with interactive interface
- Lessons streamed from the GitHub repository via the `learn` skill
- Site statistics tracked: 114,584 readers, 181,995 page views in 30 days (as of 2026-08-29)
- Translated landing pages for 12 languages (English canonical; lesson pages machine-translated on `translations` branch)

---

## Installation & Usage

### Option 1: Clone and Study Locally

```bash
git clone https://github.com/rohitg00/ai-engineering-from-scratch.git
cd ai-engineering-from-scratch
python3 phases/00-setup-and-tooling/01-dev-environment/code/verify.py --route beginner
python3 phases/01-math-foundations/01-linear-algebra-intuition/code/vectors.py
```

### Option 2: Interactive Learning with Agent Skills

Install the curriculum skills (requires Node.js, npx, Python 3, and a compatible agent host):

```bash
node --version    # Verify prerequisites
npx --version
python3 --version

npx skills add rohitg00/ai-engineering-from-scratch
```

Then invoke skills according to your host:

| Host | Start Course | MCP Path | Agent Skills | Quiz |
|------|--------------|----------|--------------|------|
| Claude Code | `/start-learning` | `/learn-mcp` | `/learn-agent-skills` | `/check-understanding 13` |
| Codex | `start-learning` | `learn-mcp` | `learn-agent-skills` | `check-understanding 13` |

### Standard Lesson Workflow

1. **Read** `docs/en.md` and explain the core idea in your own words
2. **Type and build** the important code instead of treating code blocks as decoration
3. **Run** the lesson command from the repository root
4. **Keep evidence**: command, working directory, exit code, output, artifacts produced
5. **Continue** only when you can explain the output and make one small change without guessing

### Placement and Navigation

- **Placement Quiz**: 10-question assessment maps prior knowledge to starting phase; saves personalized study plan to `LEARNING.md`
- **Course Guide Skill**: Jumps to exact lesson covering stuck topics
- **Certification Paths**: Dedicated onboarding guides in `certifications/claude/GETTING_STARTED.md` and `certifications/mcpa/GETTING_STARTED.md`

---

## Limitations and Caveats

**Content coverage and pacing**: Estimated 342 hours represents self-paced, non-linear study. Actual time varies significantly based on prior knowledge, selected learning path, and depth of engagement. Phases are stackable but not independently accessible — skipping lower phases may leave mathematical or conceptual gaps.

**Language implementation availability**: Not all lessons implement all four languages (Python, TypeScript, Rust, Julia). Language selection is made during curriculum skill installation; lessons without the selected language are marked but still teach concepts through explanation and code walkthrough.

**External tool dependencies**: Some lessons require specific development environments, libraries (PyTorch, NumPy, TensorFlow), and runtime tools. Preflight verification script (`verify.py`) detects missing requirements and provides installation guidance; content assumes Python 3.3+ availability at minimum.

**Website vs. GitHub synchronization**: Lessons are canonical on GitHub. Website lessons are human-readable but translated versions on the `translations` branch may lag canonical updates. Code blocks in lessons are expected to run from the repository root; incorrect working directory yields path errors.

**Interactive skill availability**: The agent skills require a supported host (Claude Code, Codex, compatible alternatives), Node.js, `npx`, and writable skill scope. Without these, the curriculum is accessible via website (<https://aiengineeringfromscratch.com>) and direct GitHub reading, but skill-based interactive features and placement quizzes remain unavailable.

**Real-time metrics**: Audience statistics ("114,584 readers, 181,995 page views in 30 days as of 2026-08-29") reflect snapshot at time of clone; no historical trend data is provided in the repository.

---

## Relevance to Claude Code Development

### Applications

- **Agent Skills and SDK Integration** → `plugins/plugin-creator/` and `.claude/skills/README.md`
  - Term: `agent skill`
  - Today: "Guides you through creating high-quality Claude Code agents from scratch or by adapting existing agents as templates"
  - Change: The resource's Agent Skills path (5-lesson route covering contract, discovery, invocation, sandbox boundaries, release evals, portability) directly aligns with plugin-creator's agent design patterns; integration could enrich agent creation guidance with curriculum-level foundational material

- **Model Context Protocol Implementation** → `docs/MCP-INDEX.md`
  - Term: `Model Context Protocol`
  - Today: "Complete documentation for adding Model Context Protocol (MCP) servers to claude_skills plugins"
  - Change: The resource's Phase 13 (Tools and Protocols) includes MCP fundamentals and 17-lesson deep-dive path; existing MCP documentation could reference or link to the curriculum's layered approach as supplementary learning material

- **LLM Engineering and Prompt Engineering** → `.claude/skills/`
  - Term: `prompt engineering`
  - Today: Multiple skills reference prompt patterns and optimization (learn-prompting.md, vanderbilt-prompt-patterns.md referenced in brainstorming-skill)
  - Change: none — curriculum's Phase 11 (LLM Engineering) covers prompt engineering; already a parallel resource for developers needing deeper LLM foundations

### Patterns Worth Adopting

- **Layered Skill Learning Path** → `plugins/development-harness/docs/`
  - Term: `learning path`
  - Today: Development harness uses work ledger and stage-based progression (SAM 7-stage pipeline)
  - Change: none — The resource's 20-phase architecture and 12 learning paths provide a proven pattern for structuring complex multi-stage workflows; already comparable to harness's phase-based progression model

### Integration Opportunities

- **AI Evaluation and Reliability Engineering Practices** → `plugins/development-harness/docs/impact-analysis-principals.md`
  - Term: `evaluation`
  - Today: "Current evaluation practice emphasizes real-world cases, explicit criteria, expert-labelled examples, continuous evaluation, production monitoring, and human calibration."
  - Change: The resource's AI Evaluation & Reliability Engineer learning path directly parallels development-harness's evaluation requirements; integration could enrich evaluation frameworks with curriculum-level structured reliability engineering methodology

- **Multi-Agent Orchestration and Parallel Work Patterns** → `plugins/agent-orchestration/skills/parallel-work/SKILL.md`
  - Term: `Fan-out`
  - Today: "**Fan-out, fan-in.** N dispatches of the same phase, one per unit, sent together."
  - Change: The resource's Phases 15-16 (Autonomous Systems, Multi-Agent Swarms) provide deep curriculum foundations in multi-agent coordination; could inform expansion of parallel-work skill with swarm coordination and inter-agent communication patterns

- **Agent Orchestration and Research Workflows** → `.claude/agents/research-curator.md`
  - Term: `orchestrat`
  - Today: "Works standalone or orchestrated by the /research-curator skill"
  - Change: The resource's agent coordination and orchestration patterns could enhance existing research-curator orchestrator with standardized swarm-coordination and multi-agent task distribution patterns from curriculum phases 15-17

---

## References

- [AI Engineering from Scratch — GitHub Repository](https://github.com/rohitg00/ai-engineering-from-scratch) (accessed 2026-10-02)
- [AI Engineering from Scratch — Website](https://aiengineeringfromscratch.com) (accessed 2026-10-02)
- [ROADMAP.md](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/ROADMAP.md) — Phase and lesson status tracker (accessed 2026-10-02)
- [README.md](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/README.md) — Curriculum overview and learning path selection guide (accessed 2026-10-02)
- [Learning Paths Directory](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/learning-paths) — 12 structured learning path JSON manifests (accessed 2026-10-02)
- [Skills Directory](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/skills) — 11 agent skills for interactive learning (accessed 2026-10-02)
- [Certifications Directory](https://github.com/rohitg00/ai-engineering-from-scratch/tree/main/certifications) — Claude and MCPA certification materials (accessed 2026-10-02)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Everything Claude Code](../agent-frameworks/everything-claude-code.md) | agent-frameworks | Comprehensive harness with 65+ skills implementing concepts from curriculum phases |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | Production orchestration demonstrating multi-agent patterns taught in Phase 15-16 |
| [The Unwind AI](./the-unwind-ai.md) | ai-research-tools | Newsletter with 95K+ readers covering AI engineering topics across curriculum domains |
| [Agent Skills](../skill-generation-tools/agent-skills.md) | skill-generation-tools | 24-skill lifecycle library encoding engineering disciplines taught in curriculum phases |
| [pi-mono](../agent-frameworks/pi-mono.md) | agent-frameworks | Unified TypeScript agent platform implementing LLM and agent architecture concepts |
| [mattpocock/skills](../skill-generation-tools/mattpocock-skills.md) | skill-generation-tools | 21 engineering skills teaching patterns and disciplines covered in curriculum |
| [Compound Engineering Plugin](../skill-generation-tools/compound-engineering-plugin.md) | skill-generation-tools | Plan/Work/Review workflow implementing structured engineering methodology |
| [Anthropic Agent Skills](../skill-generation-tools/anthropics-skills.md) | skill-generation-tools | Official repository of production skills demonstrating skill creation patterns taught in curriculum |
