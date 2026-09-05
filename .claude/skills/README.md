# Claude Code Skills Reference

This directory contains skills that extend Claude's capabilities with specialized knowledge, workflows, and reference documentation. Skills are automatically invoked by Claude when relevant to your request, or you can explicitly activate them using the activation syntax shown below.

## Quick Reference Table

| Skill Name                                                      | Category           | Purpose                                                          | User-Invocable        |
| --------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------- | --------------------- |
| [agent-creator](#agent-creator)                                 | Creation Tools     | Create and design Claude Code agents                             | Yes                   |
| [subagent-contract](#subagent-contract)                         | Workflow Contracts | Enforce specialist agent behavior patterns                       | No (loaded by agents) |
| [rt-ica](#rt-ica)                                               | Planning Tools     | Pre-planning checkpoint that blocks until prerequisites verified | Yes                   |
| [scientific-method:scientific-thinking](#scientific-method-scientific-thinking) (plugin) | Workflow Tools     | Hypothesis-driven reasoning for complex problems                 | Yes                   |
| [verify](#verify)                                               | Workflow Tools     | Self-assessment checklist before task completion                 | Yes                   |
| [claude-skills-overview-2026](#claude-skills-overview-2026)     | Reference          | Skills and Slash Command system documentation                    | Yes                   |
| [hooks-guide](#hooks-guide)                                     | Reference          | Cross-platform hooks reference (Claude Code, Copilot, Cursor)    | Yes                   |
| [claude-plugins-reference-2026](#claude-plugins-reference-2026) | Reference          | Plugins system documentation                                     | Yes                   |
| [git-commit-helper](#git-commit-helper)                         | Development Tools  | Generate conventional commit messages                            | Yes                   |

---

## Creation Tools

### agent-creator

**What it does**: Guides you through creating high-quality Claude Code agents from scratch or by adapting existing agents as templates. Provides agent architecture expertise following Anthropic's post-January 2026 best practices.

**AI behavior when loaded**:

- Analyzes existing agents in your project to identify patterns and conventions
- Guides systematic requirements gathering through structured questions
- Recommends appropriate agent templates based on your needs (standard user-facing agents or role-based contract archetypes)
- Walks through template adaptation with section-by-section guidance
- Validates agent files against frontmatter schema and best practices
- Provides model selection, permission mode, and tool access guidance

**How to trigger**:

- Explicitly: `@agent-creator` or `Skill(skill: "agent-creator")`
- Automatically: When you request creating, modifying, or reviewing agents, or when asking about agent structure and configuration

**What to expect**:

- Comprehensive agent creation workflow from discovery through validation
- Template recommendations with multiple options (existing project agents, role-based archetypes, or from scratch)
- Structured guidance for frontmatter configuration (name, description, tools, model, permissions, skills)
- Agent body structure recommendations with XML tagging and output formats
- Testing methodology to verify agent behavior before production use

**Related skills**: `subagent-contract` (for orchestrated agents that use DONE/BLOCKED signaling)

**Example usage**:

```
"I need to create an agent that reviews Python code for PEP 8 compliance"
```

---

## Workflow Contracts

### subagent-contract

**What it does**: Provides a global contract that enforces disciplined behavior patterns for specialist agents in orchestrated workflows. Not directly user-invocable - loaded by role-based agents that participate in orchestration patterns.

**AI behavior when loaded**:

- Enforces strict scope discipline (agent stays within assigned boundaries)
- Requires DONE or BLOCKED status signaling upon task completion
- Prevents scope creep, assumption-making, and requirement invention
- Forces explicit blocking when information is missing rather than guessing
- Validates work meets acceptance criteria before signaling DONE

**How to trigger**:

- Loaded automatically by agents that include `skills: subagent-contract` in their frontmatter
- Not user-invocable (set to `user-invocable: false`)

**What to expect**:
When an agent loads this skill, it will:

- Begin by restating the task and acceptance criteria
- Execute only within the minimal scope defined
- Report STATUS: DONE with deliverables when complete
- Report STATUS: BLOCKED with specific requirements when unable to proceed
- Follow its Standard Operating Procedure (SOP) exactly as defined
- Prefer blocking over making assumptions

**Related skills**: `agent-creator` (which provides role-based contract archetypes that use this skill)

**Contract enforcement**:

- Agent must restate task before starting
- Agent cannot expand scope without explicit approval
- Agent must signal DONE (with deliverables) or BLOCKED (with requirements)
- Agent follows quality verification checklists before completion

---

## Planning Tools

### rt-ica

**What it does**: Reverse Thinking - Information Completeness Assessment. A mandatory pre-planning checkpoint that blocks planning until prerequisites are verified. Ensures all required information is AVAILABLE, DERIVABLE, or explicitly MISSING before proceeding with implementation planning.

**AI behavior when loaded**:

- Performs goal reconstruction (statement, output form, scope boundaries)
- Enumerates reverse prerequisites working backwards from the goal
- Classifies each prerequisite as AVAILABLE, DERIVABLE, or MISSING
- Makes completeness decision: APPROVED (proceed) or BLOCKED (request missing inputs)
- Blocks planning with MISSING conditions unless user explicitly requests assumption-based planning
- Produces structured RT-ICA SUMMARY output block

**How to trigger**:

- Explicitly: `@rt-ica` or `Skill(skill: "rt-ica")`
- Automatically: When receiving specs, PRDs, tickets, RFCs, architecture designs, or any multi-step engineering task
- Via SessionStart hook: Automatically reminded at session start in this repository

**What to expect**:

- Structured RT-ICA SUMMARY block with goal, conditions, verification status, and decision
- BLOCKED decisions with categorized missing input questions
- APPROVED decisions with assumptions to confirm for DERIVABLE items
- Integration points: before top-level planning, agent delegation, acceptance criteria, and rollout steps

**Key concepts**:

- **AVAILABLE**: Explicitly present in the input material
- **DERIVABLE**: Inferred with high confidence from provided material (must show basis)
- **MISSING**: Not present and not safely inferable

**Related skills**: `subagent-contract` (DONE/BLOCKED signaling), `agent-orchestration` (scientific delegation)

**Example usage**:

```
"Build a user authentication service"
→ RT-ICA will identify MISSING prerequisites (auth protocol, session management, security requirements)
→ Ask only for missing inputs before proceeding with planning
```

---

## Workflow Tools

<a id="scientific-method-scientific-thinking"></a>

### scientific-method:scientific-thinking

> Migrated to plugin: /scientific-method:scientific-thinking

**What it does**: Forces hypothesis-driven scientific reasoning for complex problems. Provides a structured framework for debugging, architecture design, and complex refactoring using the scientific method.

**AI behavior when loaded**:

- Lists only factual observations (logs, errors, file contents) without interpretation
- Formulates null hypothesis (H₀) and alternative hypothesis (Hₐ)
- Makes specific, testable predictions
- Designs experiments with multiple paths (Tree-of-Thought)
- Identifies and isolates confounding variables
- Records results factually and draws evidence-based conclusions

**How to trigger**:

- Explicitly: `@scientific-method:scientific-thinking` or `Skill(skill: "scientific-method:scientific-thinking")`
- Automatically: When debugging strange behavior, investigating root causes, designing architecture, performing complex refactoring, or when initial attempts have failed

**What to expect**:

- Structured reasoning through Observation → Hypothesis → Prediction → Experiment → Conclusion
- Clear separation of facts from interpretations
- Multiple experimental paths to increase confidence
- Evidence-based conclusions (Reject H₀ or Fail to Reject H₀)

**When NOT to use**: Simple typo fixes, straightforward feature additions, following explicit instructions.

---

### verify

**What it does**: Provides a rigorous self-assessment checklist before marking any task as complete. Requires evidence for every assertion to prevent premature completion claims.

**AI behavior when loaded**:

- Identifies task type (FIX, FEATURE, REFACTOR, DOCS, INVESTIGATION)
- Determines verification strategy (executable vs static)
- For code: requires execution output, regression evidence, edge case testing
- For static assets: requires accuracy verification, format compliance, link validation
- Enforces the "Golden Rule": no evidence = not done

**How to trigger**:

- Explicitly: `@verify` or `Skill(skill: "verify")`
- Automatically: When about to claim task completion, before final commit, when user asks "is it done?", or when transitioning from implementation to reporting

**What to expect**:

- Checklist with evidence requirements for each item
- Task-type-specific verification criteria
- Quality gate verification (pre-commit, linting, type checking)
- Honesty check distinguishing "should work" from "verified to work"

**The Golden Rule**: If you cannot demonstrate it working in practice with evidence, it is NOT done.

---

## Claude Code Reference Documentation

These skills provide comprehensive reference documentation for Claude Code's capabilities system. Claude loads these automatically when you're working with the respective features.

### claude-skills-overview-2026

**What it does**: Complete reference guide for the Claude Code skills system as of January 2026. Covers SKILL.md format, frontmatter fields, hooks, context forking, and best practices.

**AI behavior when loaded**:

- Provides accurate frontmatter schema and field constraints
- References directory structure requirements
- Explains skill invocation patterns and user-invocable settings
- Documents hooks configuration within skills
- Clarifies description best practices for skill activation
- Covers context fork options with agent selection

**How to trigger**:

- Explicitly: `@claude-skills-overview-2026`
- Automatically: When creating, modifying, or understanding skills, SKILL.md format, frontmatter fields, hooks, context fork, or skill best practices

**What to expect**:

- Complete SKILL.md format specification
- All frontmatter field documentation with types and constraints
- Hook configuration examples (PreToolUse, PostToolUse, Stop)
- String substitutions ($ARGUMENTS, ${CLAUDE_SESSION_ID})
- Context fork patterns with agent types (Explore, Plan, general-purpose)
- Installation and location priority rules

**Key sections**:

- Frontmatter field reference table
- Description writing templates and anti-patterns
- Hook event types and I/O specifications
- Skills vs other features comparison table

---

### hooks-guide

**What it does**: Cross-platform hooks reference for Claude Code, GitHub Copilot, Cursor, Windsurf, and Amp. Covers hook authoring in Node.js CJS and Python, per-platform event schemas, inline-agent hooks, common JSON I/O, exit codes, best practices, and a fetch script to refresh docs from official sources.

**AI behavior when loaded**:

- Routes to per-platform reference files via embedded flowchart
- Provides Claude Code hook event reference (PreToolUse, PostToolUse, Stop, SessionStart, etc.)
- Covers inline-agent hooks and MCP in agent frontmatter
- Documents JSON I/O, exit codes, and matcher syntax
- References Node.js CJS and Python authoring guides
- Provides best practices and anti-patterns

**How to trigger**:

- Explicitly: `@hooks-guide`
- Automatically: When creating hooks, understanding hook events, matchers, exit codes, JSON output control, environment variables, or hook best practices

**What to expect**:

- Routing flowchart to the right reference file
- Per-platform coverage with language-specific guides
- Specialist skills for deeper coverage: `hooks-core-reference`, `hooks-io-api`, `hooks-patterns`
- Execution details (parallelization, deduplication, timeout)

**Key sections**:

- All hook events reference table
- Configuration locations and precedence
- Hook I/O patterns with JSON examples
- Prompt-based vs command-based hooks
- Best practices and anti-patterns

---

### claude-plugins-reference-2026

**What it does**: Complete reference guide for the Claude Code plugins system. Covers plugin.json schema, marketplace configuration, bundling skills/commands/agents/hooks/MCP/LSP servers, and plugin validation.

**AI behavior when loaded**:

- Provides plugin.json schema and field requirements
- Explains directory structure requirements
- Documents distribution methods (marketplace, direct installation)
- Clarifies bundled capability types
- References environment variables for plugins
- Covers validation and testing approaches

**How to trigger**:

- Explicitly: `@claude-plugins-reference-2026`
- Automatically: When creating, distributing, or understanding plugins, plugin.json schema, marketplace configuration, bundling components, or plugin validation

**What to expect**:

- Complete plugin.json schema with required and recommended fields
- Directory structure patterns
- Marketplace configuration format
- Installation scope options (user, project, local, managed)
- Bundled capability documentation (commands, agents, skills, hooks, MCP, LSP)
- Environment variable reference (CLAUDE_PLUGIN_ROOT, CLAUDE_PROJECT_DIR)
- Validation and testing commands

**Key sections**:

- plugin.json field reference tables
- Directory structure requirements
- Distribution methods and marketplace format
- Installation scopes comparison
- Component bundling patterns
- Enterprise features and constraints

---

## Development Tools

### git-commit-helper

**What it does**: Analyzes git diffs and generates descriptive commit messages following conventional commits format. Guides commit message structure with types, scopes, and best practices.

**AI behavior when loaded**:

- Analyzes staged changes with `git diff --staged`
- Determines appropriate commit type (feat, fix, docs, refactor, test, chore, style)
- Identifies scope based on files changed
- Generates commit message following conventional commits format
- Explains WHY changes were made, not just WHAT changed
- Follows best practices (imperative mood, under 50 chars for summary, etc.)

**How to trigger**:

- Explicitly: `@git-commit-helper` or `Skill(skill: "git-commit-helper")`
- Automatically: When you ask for help writing commit messages or reviewing staged changes

**What to expect**:

- Commit message with proper type and scope
- Summary line under 50 characters using imperative mood
- Optional body explaining rationale and impact
- Breaking change indicators when applicable
- Adherence to conventional commits format

**Commit types supported**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style/formatting changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example usage**:

```
"Help me write a commit message for these staged changes"
```

**Conventional commits format**:

```
<type>(<scope>): <description>

[optional body explaining WHY]

[optional footer with breaking changes or issue references]
```

---

## Activation Patterns

### Explicit Activation

Use `@skill-name` or `Skill(skill: "skill-name")` to explicitly activate a skill:

```
@agent-creator
@git-commit-helper
Skill(skill: "claude-skills-overview-2026")
```

### Automatic Activation

Claude automatically activates skills based on your request. Skills have trigger keywords in their descriptions that Claude uses for selection:

- **agent-creator**: "create agent", "modify agent", "agent structure", "agent configuration"
- **rt-ica**: "planning", "prerequisites", "spec", "PRD", "ticket", "RFC", "architecture design", "multi-step task"
- **scientific-method:scientific-thinking**: "debugging", "strange behavior", "root cause", "architecture design", "complex refactoring", "investigation"
- **verify**: "is it done", "task complete", "before commit", "completion", "finished"
- **audit**: "review output", "hallucination", "suspicious", "probably", "likely", "verify claims"
- **claude-skills-overview-2026**: "skill format", "SKILL.md", "skill frontmatter", "skill best practices"
- **hooks-guide**: "hook", "PreToolUse", "PostToolUse", "hook events", "inline-agent hooks", "platform hooks"
- **claude-plugins-reference-2026**: "plugin", "plugin.json", "marketplace", "bundle"
- **git-commit-helper**: "commit message", "staged changes", "git diff"

---

## Skill Relationships

### Agent Creation Workflow

```
agent-creator → creates agents that may load → subagent-contract
```

When creating orchestrated agents with DONE/BLOCKED signaling, use agent-creator which will recommend loading the subagent-contract skill.

### Reference Documentation Chain

```
claude-plugins-reference-2026
  ├── references → claude-skills-overview-2026 (for bundled skills and commands)
  └── references → hooks-guide (for bundled hooks)
```

When working with plugins, you may need the other reference skills to understand bundled components.

---

## Additional Resources

### Learning More About Skills

- Official Documentation: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
- Anthropic Skills Repository: [github.com/anthropics/skills](https://github.com/anthropics/skills)
- Agent Skills Blog: [anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

### Creating Your Own Skills

To create a custom skill, use the `agent-creator` skill which also provides guidance for skill creation patterns. Skills follow the same SKILL.md format documented in `claude-skills-overview-2026`.

### Installation

Skills in this directory are already installed and available. To add skills from plugins:

```bash
/plugin marketplace add owner/repo
/plugin install plugin-name@marketplace-name
```

Skills automatically reload when modified (hot reload enabled in Claude Code 2.1+).

---

## Notes

- Skills are **model-invoked**: Claude automatically decides which skills to use based on your request
- Skills can be **user-invocable** (appear in menus) or **internal** (only programmatically loaded)
- Skills can restrict tool access, override the model, and configure hooks
- Skills support **context fork** to run in isolated sub-agent contexts
- Skills have a 15,000 character budget for metadata

For detailed information about any skill, activate it directly or consult its SKILL.md file.
