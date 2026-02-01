# Softaworks Agent Toolkit

| Field         | Value                                                    |
| ------------- | -------------------------------------------------------- |
| Research Date | 2026-01-31                                               |
| Primary URL   | <https://github.com/softaworks/agent-toolkit>            |
| GitHub        | <https://github.com/softaworks/agent-toolkit>            |
| Installation  | `npx skills add softaworks/agent-toolkit`                |
| Version       | Active development (last pushed 2026-01-28)              |
| License       | MIT                                                      |
| Author        | [@leonardocouy](https://github.com/leonardocouy)         |
| Organization  | [Softaworks](https://github.com/softaworks)              |

---

## Overview

Softaworks Agent Toolkit is a curated collection of 40+ skills for AI coding agents that follow the Agent Skills format. Skills are packaged instructions and scripts extending agent capabilities across development, documentation, planning, and professional workflows. The toolkit works with Claude Code, OpenAI Codex, Cursor, and other AI coding assistants, offering both marketplace-based installation and direct skill copying.

---

## Problem Addressed

| Problem                                              | Solution                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------- |
| AI coding agents lack specialized domain knowledge   | 40+ pre-built skills covering development, docs, planning, communication  |
| Skills scattered across repositories and formats     | Unified Agent Skills format with consistent SKILL.md structure            |
| Installing skills requires manual copying            | Multiple install methods: npx, plugin marketplace, direct copy            |
| Skills not portable across different AI agents       | Agent Skills format works with Claude Code, Codex, Cursor, claude.ai      |
| No organized taxonomy for agent capabilities         | Categorized skills: AI Tools, Meta, Documentation, Design, Development    |
| Agents and commands are separate from skills         | Unified plugin system includes skills, agents, and slash commands         |
| Skills lack usage documentation                      | Each skill has SKILL.md (for agents) + README.md (for users)              |

---

## Key Statistics

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 378                       | 2026-01-31    |
| GitHub Forks      | 17                        | 2026-01-31    |
| Open Issues       | 0                         | 2026-01-31    |
| Primary Language  | Python                    | 2026-01-31    |
| Repository Age    | Since 2026-01-19          | 2026-01-31    |
| Total Skills      | 40+                       | 2026-01-31    |
| Total Agents      | 6                         | 2026-01-31    |
| Slash Commands    | 7                         | 2026-01-31    |

---

## Key Features

### Skill Categories

| Category           | Count | Examples                                             |
| ------------------ | ----- | ---------------------------------------------------- |
| AI Tools           | 3     | codex (GPT-5.2), gemini (200k context), perplexity   |
| Meta               | 4     | agent-md-refactor, command-creator, plugin-forge     |
| Documentation      | 10    | c4-architecture, mermaid-diagrams, excalidraw        |
| Design & Frontend  | 5     | mui, react-dev, openapi-to-typescript                |
| Development        | 5     | database-schema-designer, dependency-updater         |
| Planning           | 4     | gepetto, requirements-clarity, game-changing-features|
| Professional       | 4     | daily-meeting-update, feedback-mastery               |
| Testing            | 1     | qa-test-planner                                      |
| Git                | 1     | commit-work                                          |
| Utilities          | 7     | humanizer, jira, web-to-markdown, meme-factory       |

### Agents (Claude Code Exclusive)

| Agent                           | Purpose                                        |
| ------------------------------- | ---------------------------------------------- |
| ascii-ui-mockup-generator       | Visualize UI concepts through ASCII mockups    |
| codebase-pattern-finder         | Find similar implementations and patterns      |
| communication-excellence-coach  | Email refinement, tone calibration, roleplay   |
| general-purpose                 | Default agent for complex multi-step tasks     |
| mermaid-diagram-specialist      | Create flowcharts, sequence diagrams, ERDs     |
| ui-ux-designer                  | Research-backed UI/UX design feedback          |

### Slash Commands (Claude Code Exclusive)

| Command                        | Purpose                                    |
| ------------------------------ | ------------------------------------------ |
| `/codex-plan`                  | Create implementation plans using Codex    |
| `/compose-email`               | Draft professional emails                  |
| `/explain-changes-mental-model`| Build mental model of code changes         |
| `/explain-pr-changes`          | Generate PR summaries                      |
| `/sync-branch`                 | Sync feature branch with main              |
| `/sync-skills-readme`          | Update README skills table                 |
| `/viral-tweet`                 | Optimize tweet ideas for engagement        |

### Installation Methods

1. **Quick Install (Recommended)**: `npx skills add softaworks/agent-toolkit`
2. **Plugin Marketplace**: `/plugin marketplace add softaworks/agent-toolkit`
3. **Direct Install**: `/plugin install codex@agent-toolkit`
4. **Manual Copy**: `cp -r skills/<skill-name> ~/.claude/skills/`
5. **claude.ai**: Paste SKILL.md contents into conversation

### Notable Skills Deep Dive

#### Gepetto (Planning Skill)

Multi-step planning orchestration: Research, Interview, Spec Synthesis, Plan, External Review, Sections. Creates detailed implementation plans through stakeholder interviews and multi-LLM review. Generates structured markdown files for each phase.

#### Codex (AI Tools Skill)

Integration with OpenAI Codex CLI for code analysis and automated editing. Supports GPT-5.2 models with configurable reasoning effort levels (xhigh, high, medium, low). Manages sandbox modes (read-only, workspace-write, danger-full-access) and session resumption.

#### Humanizer (Utility Skill)

Removes AI writing patterns from text to make content sound more natural and human-written.

---

## Technical Architecture

### Skill Structure

```text
skills/
  <skill-name>/
    SKILL.md      # Agent-facing instructions (YAML frontmatter required)
    README.md     # User-facing documentation
    scripts/      # Helper automation scripts (optional)
    references/   # Supporting documentation (optional)
```

### SKILL.md Format

```yaml
---
name: skill-name
description: Trigger description for when agent should activate this skill
---

# Skill Title

Instructions, rules, and patterns for the agent to follow...
```

### Plugin System

- Skills, agents, and commands are individual plugins
- Marketplace support for discovery and updates
- Auto-update capability for keeping skills current
- Scoped installation (local/global)

### Agent Skills Format Compatibility

Skills follow the [Agent Skills](https://agentskills.io/) format, ensuring portability across:

- Claude Code (native support)
- OpenAI Codex (via CLI)
- Cursor (skill import)
- claude.ai (manual paste)

---

## Relevance to Claude Code Development

### Direct Applications

1. **Skill Library Reference**: 40+ skills provide patterns for skill design, covering diverse use cases from planning to professional communication.

2. **Multi-LLM Integration Patterns**: codex, gemini, perplexity skills demonstrate patterns for integrating external AI services within Claude Code workflows.

3. **Planning Methodology**: gepetto skill shows sophisticated multi-phase planning with file-based state management and resume capabilities.

4. **Agent Delegation Patterns**: 6 specialized agents demonstrate effective sub-agent design with clear role boundaries.

5. **Command Design**: Slash commands show patterns for reusable workflow automation.

### Patterns Worth Adopting

1. **Dual Documentation**: Every skill has SKILL.md (agent-facing) + README.md (user-facing), ensuring both audiences are served.

2. **YAML Frontmatter Triggers**: `description` field in frontmatter acts as activation trigger, helping agents determine when to apply skills.

3. **Phase-Based Planning**: gepetto's Research, Interview, Spec Synthesis, Plan, Review, Sections phases provide structured approach to complex tasks.

4. **Sandbox Mode Patterns**: codex skill's read-only, workspace-write, danger-full-access modes show graduated permission levels.

5. **Session Resumption**: codex skill's resume capability demonstrates stateful workflow continuation.

6. **Category Organization**: Skills organized by domain (AI Tools, Documentation, Development, etc.) aids discoverability.

### Integration Opportunities

1. **Skill Import**: Skills could be directly imported or adapted for this repository's skill format.

2. **Pattern Extraction**: gepetto's planning methodology could inform task planning improvements.

3. **Cross-Repository Synergy**: agent-md-refactor skill could help maintain this repository's skill documentation.

4. **Tool Patterns**: datadog-cli, jira skills show patterns for external service integration.

5. **Professional Skills**: Workplace communication skills (feedback-mastery, difficult-workplace-conversations) extend agent capabilities beyond pure coding.

### Comparison with This Repository

| Aspect              | Softaworks Agent Toolkit          | This Repository (claude_skills)     |
| ------------------- | --------------------------------- | ------------------------------------ |
| Skill Format        | Agent Skills (agentskills.io)     | Claude Code native + plugins         |
| Installation        | npx, marketplace, manual          | Plugin marketplace, symlinks         |
| Scope               | Opinionated personal toolkit      | Marketplace-oriented collection      |
| Agent Support       | Yes (6 agents)                    | Yes                                  |
| Commands            | Yes (7 commands)                  | Yes                                  |
| Auto-Update         | Yes (marketplace)                 | Yes (marketplace)                    |
| Categories          | 10 categories                     | Category-based                       |
| Primary Author      | @leonardocouy                     | Community                            |

---

## References

| Source                    | URL                                                                 | Accessed   |
| ------------------------- | ------------------------------------------------------------------- | ---------- |
| GitHub Repository         | <https://github.com/softaworks/agent-toolkit>                       | 2026-01-31 |
| GitHub README             | <https://github.com/softaworks/agent-toolkit/blob/main/README.md>   | 2026-01-31 |
| GitHub API (Metadata)     | <https://api.github.com/repos/softaworks/agent-toolkit>             | 2026-01-31 |
| Agent Skills Format       | <https://agentskills.io/>                                           | 2026-01-31 |
| Codex Skill               | skills/codex/SKILL.md (via raw GitHub)                              | 2026-01-31 |
| Gepetto Skill             | skills/gepetto/SKILL.md (via raw GitHub)                            | 2026-01-31 |

**Research Method**: Information gathered from GitHub repository README, GitHub API for repository metadata (stars, forks, license, dates), and raw skill files for technical details. Statistics verified via direct API calls on 2026-01-31.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | Active development                  |
| Last Pushed        | 2026-01-28                          |
| GitHub Stars       | 378 (as of 2026-01-31)              |
| Total Skills       | 40+ (as of 2026-01-31)              |
| Next Review Date   | 2026-05-01                          |

**Review Triggers**:

- GitHub stars milestone (500, 1K)
- Major new skill categories added
- Plugin marketplace format changes
- New AI agent platform support
- Significant skill additions (10+ new skills)
- Changes to Agent Skills format specification
