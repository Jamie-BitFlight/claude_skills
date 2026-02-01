# BMAD-METHOD

| Field         | Value                                                       |
| ------------- | ----------------------------------------------------------- |
| Research Date | 2026-02-01                                                  |
| Primary URL   | <https://github.com/bmad-code-org/BMAD-METHOD>              |
| Documentation | <http://docs.bmad-method.org>                               |
| NPM Package   | <https://www.npmjs.com/package/bmad-method>                 |
| Version       | 6.0.0-Beta.4                                                |
| License       | MIT                                                         |
| Discord       | <https://discord.gg/gk8jAdXWmj>                             |

---

## Overview

BMAD-METHOD (Breakthrough Method of Agile AI-Driven Development) is an AI-driven agile development framework providing 21 specialized agents, 50+ guided workflows, and scale-adaptive intelligence that adjusts methodology depth based on project complexity. Unlike traditional AI tools that generate solutions directly, BMAD agents act as expert collaborators who guide developers through structured processes grounded in agile best practices across analysis, planning, architecture, and implementation phases.

---

## Problem Addressed

| Problem                                          | Solution                                                                   |
| ------------------------------------------------ | -------------------------------------------------------------------------- |
| AI tools produce average results without process | Agents guide structured thinking, eliciting user expertise                 |
| Different project scales need different planning | Scale-domain-adaptive system adjusts planning depth automatically          |
| Full development lifecycle lacks AI guidance     | Complete coverage from brainstorming to deployment with specialized agents |
| AI agents work in isolation                      | Party Mode brings multiple agent personas into collaborative sessions      |
| Complex methodology requires learning curve      | AI-assisted help (`/bmad-help`) provides contextual guidance at each step  |
| One-size-fits-all methodology                    | Domain-specific modules (Game Dev, Test Architecture, Creative Suite)      |
| Traditional docs don't integrate with AI IDEs   | Slash commands install directly to Claude Code, Cursor, Windsurf           |

---

## Key Statistics

| Metric           | Value           | Date Gathered |
| ---------------- | --------------- | ------------- |
| GitHub Stars     | 33,347          | 2026-02-01    |
| GitHub Forks     | 4,286           | 2026-02-01    |
| Watchers         | 348             | 2026-02-01    |
| Open Issues      | 62              | 2026-02-01    |
| Contributors     | 100+            | 2026-02-01    |
| Primary Language | JavaScript      | 2026-02-01    |
| Created          | 2025-04-13      | 2026-02-01    |
| Last Updated     | 2026-02-01      | 2026-02-01    |

---

## Key Features

### Core Framework

- **21 Specialized Agents**: Domain experts including PM, Analyst, Architect, Developer, UX Designer, Scrum Master, Quinn (QA), Tech Writer
- **50+ Guided Workflows**: Structured processes organized into 4 development phases
- **Scale-Domain-Adaptive**: Automatically adjusts planning depth based on project complexity and domain
- **AI Intelligent Help**: `/bmad-help` provides contextual guidance, answers questions, and suggests next steps
- **Party Mode**: Multi-agent collaborative sessions for planning, troubleshooting, and discussion

### Development Phases

| Phase          | Directory              | Purpose                              |
| -------------- | ---------------------- | ------------------------------------ |
| Analysis       | `1-analysis/`          | Problem understanding, research      |
| Planning       | `2-plan-workflows/`    | Product briefs, PRDs, requirements   |
| Solutioning    | `3-solutioning/`       | Architecture, technical design       |
| Implementation | `4-implementation/`    | Development, stories, code review    |

### Quick Flow (Simple Path)

For bug fixes, small features, clear scope:

1. `/quick-spec` - Analyze codebase, produce tech-spec with stories
2. `/dev-story` - Implement each story
3. `/code-review` - Validate quality

### Full Planning Path (BMad Method)

For products, platforms, complex features:

1. `/product-brief` - Define problem, users, MVP scope
2. `/create-prd` - Full requirements with personas, metrics, risks
3. `/create-architecture` - Technical decisions and system design
4. `/create-epics-and-stories` - Break work into prioritized stories
5. `/sprint-planning` - Initialize sprint tracking
6. Per story: `/create-story` -> `/dev-story` -> `/code-review`

### Agents in BMM Module

| Agent File                      | Role                                   |
| ------------------------------- | -------------------------------------- |
| `analyst.agent.yaml`            | Business and requirements analysis     |
| `architect.agent.yaml`          | Technical architecture design          |
| `dev.agent.yaml`                | Development and implementation         |
| `pm.agent.yaml`                 | Product management and roadmap         |
| `quick-flow-solo-dev.agent.yaml`| Streamlined solo development           |
| `quinn.agent.yaml`              | QA and test automation                 |
| `sm.agent.yaml`                 | Scrum Master, sprint management        |
| `ux-designer.agent.yaml`        | User experience design                 |

### Extension Modules

| Module                      | NPM Package                          | Purpose                                       |
| --------------------------- | ------------------------------------ | --------------------------------------------- |
| BMad Method (BMM)           | `bmad-method`                        | Core framework, 34+ workflows across 4 phases |
| BMad Builder (BMB)          | `bmad-builder`                       | Create custom agents, workflows, modules      |
| Test Architect (TEA)        | `bmad-method-test-architecture-enterprise` | Risk-based test strategy, 8 workflows    |
| Game Dev Studio (BMGD)      | `bmad-game-dev-studio`               | Unity, Unreal, Godot workflows                |
| Creative Intelligence (CIS) | `bmad-creative-intelligence-suite`   | Innovation, brainstorming, design thinking    |

---

## Technical Architecture

### Project Structure

```text
BMAD-METHOD/
  src/
    bmm/                    # BMad Method module
      agents/               # 8 agent YAML definitions
      workflows/            # 9 workflow categories
      teams/                # Multi-agent team configurations
      data/                 # Supporting data files
      module.yaml           # Module manifest
      module-help.csv       # AI help knowledge base
    core/                   # Core framework utilities
    utility/                # CLI and helper utilities
  tools/
    cli/                    # npx bmad-method install
  docs/                     # Documentation (Astro/Starlight)
  website/                  # Marketing site
```

### Agent Definition Format

Agents are defined in YAML files (`*.agent.yaml`) with:

- Role and expertise definition
- Available workflows and commands
- Knowledge and data file references
- Menu-driven interaction patterns

### Workflow Structure

Each workflow directory contains:

- Workflow definition files
- Templates and prompts
- Output document specifications
- Validation rules

### Installation Flow

```bash
# Install to any project
npx bmad-method install

# Follow prompts to select:
# - Core module (BMM)
# - Optional modules (TEA, BMGD, CIS)
# - IDE integration (Claude Code, Cursor, Windsurf)
```

### IDE Integration

- Installs slash commands to `.claude/commands/` or equivalent
- Agents accessible via `/agent-name` syntax
- Workflows triggered via `/workflow-name` commands
- AI help via `/bmad-help` with contextual awareness

---

## Installation and Usage

### Prerequisites

- Node.js v20.0.0 or higher
- AI IDE (Claude Code, Cursor, Windsurf, or similar)

### Installation

```bash
npx bmad-method install
```

### Using AI Help

```text
/bmad-help
/bmad-help How should I build a web app for my TShirt Business?
/bmad-help I just finished the architecture, what's next?
```

### Quick Flow Example

```text
# Step 1: Analyze and create tech spec
/quick-spec

# Step 2: Implement stories
/dev-story

# Step 3: Code review
/code-review
```

### Full Method Example

```text
# Planning phase
/product-brief
/create-prd
/create-architecture

# Story breakdown
/create-epics-and-stories
/sprint-planning

# Per-story development
/create-story
/dev-story
/code-review
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **Structured Workflow Patterns**: 50+ workflows provide templates for Claude Code skill workflows, showing how to break complex tasks into guided steps.

2. **Agent Definition Format**: YAML-based agent definitions demonstrate a portable, readable format for agent persona and capability specification.

3. **Scale-Adaptive Intelligence**: Methodology that adjusts based on project complexity shows patterns for context-aware skill activation.

4. **AI-Assisted Help System**: `/bmad-help` with contextual awareness demonstrates patterns for self-documenting, adaptive skill systems.

5. **Multi-Agent Collaboration**: Party Mode shows patterns for coordinating multiple specialized agents in collaborative sessions.

### Patterns Worth Adopting

1. **Phase-Based Organization**: Grouping workflows into analysis, planning, solutioning, and implementation phases provides clear navigation.

2. **Module System**: Extension modules (BMB, TEA, BMGD, CIS) show how to package domain-specific agent collections.

3. **Progressive Disclosure**: Quick Flow (3 commands) vs Full Method (many commands) allows users to choose depth.

4. **Knowledge-Driven Help**: CSV-based help knowledge base enables AI-assisted guidance that evolves with installed modules.

5. **Dual-Path Methodology**: Simple path for quick tasks, full path for complex projects addresses different use cases.

### Integration Opportunities

1. **Workflow Import**: BMAD workflows could inform Claude Code skill design for product development tasks.

2. **Agent Personas**: Agent definitions could be adapted as Claude Code agent configurations.

3. **Help System Pattern**: AI-assisted help could inform Claude Code skill documentation approaches.

4. **Module Marketplace**: BMAD's module system and upcoming community marketplace could inform Claude Code plugin ecosystem design.

5. **IDE Neutral Design**: Installation to multiple AI IDEs shows patterns for portable agent systems.

### Comparison with Claude Code Ecosystem

| Aspect                 | BMAD-METHOD                     | Claude Code                      |
| ---------------------- | ------------------------------- | -------------------------------- |
| Primary Focus          | Agile methodology               | Developer workflow automation    |
| Agent Format           | YAML (*.agent.yaml)             | Markdown + YAML frontmatter      |
| Workflow Scope         | Full SDLC                       | Task-specific                    |
| Installation           | npx installer                   | Plugin marketplace               |
| IDE Support            | Claude Code, Cursor, Windsurf   | Claude Code                      |
| Extension Model        | NPM modules                     | Plugins and skills               |
| Collaboration          | Party Mode (multi-agent)        | Task delegation                  |

---

## References

| Source                    | URL                                                         | Accessed   |
| ------------------------- | ----------------------------------------------------------- | ---------- |
| GitHub Repository         | <https://github.com/bmad-code-org/BMAD-METHOD>              | 2026-02-01 |
| GitHub README             | <https://github.com/bmad-code-org/BMAD-METHOD/blob/main/README.md> | 2026-02-01 |
| Official Documentation    | <http://docs.bmad-method.org>                               | 2026-02-01 |
| Getting Started Tutorial  | <http://docs.bmad-method.org/tutorials/getting-started/>    | 2026-02-01 |
| NPM Package               | <https://www.npmjs.com/package/bmad-method>                 | 2026-02-01 |
| Package.json              | <https://github.com/bmad-code-org/BMAD-METHOD/blob/main/package.json> | 2026-02-01 |
| BMM Agents Directory      | <https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/bmm/agents> | 2026-02-01 |
| BMM Workflows Directory   | <https://github.com/bmad-code-org/BMAD-METHOD/tree/main/src/bmm/workflows> | 2026-02-01 |
| Discord Community         | <https://discord.gg/gk8jAdXWmj>                             | 2026-02-01 |
| GitHub Discussions        | <https://github.com/bmad-code-org/BMAD-METHOD/discussions>  | 2026-02-01 |

**Research Method**: Information gathered from GitHub repository README, GitHub API (repository metadata, directory structure, package.json), and official documentation links. Statistics verified via direct GitHub API calls on 2026-02-01.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | 6.0.0-Beta.4                        |
| Last Commit        | 2026-02-01                          |
| GitHub Stars       | 33,347 (as of 2026-02-01)           |
| Contributors       | 100+ (as of 2026-02-01)             |
| Next Review Date   | 2026-05-01                          |

**Review Triggers**:

- Version 6.0.0 stable release (exit beta)
- GitHub stars milestone (40K, 50K)
- New module releases
- Breaking changes to agent/workflow format
- Community marketplace launch
- New IDE integrations
