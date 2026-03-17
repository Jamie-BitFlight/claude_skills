# ctxforge

## Overview

ctxforge is a "protocol-based framework that makes LLMs discover requirements systematically before writing code" (README.md, 2026-03-17). It is a lightweight, zero-dependency context engineering system distributed as an npm package that provides structured workflows for LLM-assisted software development.

- **Author**: Ventsislav Petrov
- **License**: MIT
- **Language**: JavaScript
- **Current Version**: v3.1.2 (released October 2025)
- **Repository**: <https://github.com/vencolini/ctxforge>
- **NPM Package**: <https://www.npmjs.com/package/ctxforge>
- **Node.js Requirement**: >=14.0.0

## Problem Addressed

"LLMs generate solutions based on assumptions when requirements are incomplete. A request like 'add authentication' requires approximately 50 decisions: session duration, password requirements, database choice, rate limiting, 2FA strategy, error handling, security measures, and more. When developers provide 1-2 details, LLMs infer the remaining 48—often incorrectly for your specific context. Result: Solutions that don't match your setup, requiring costly iteration cycles to correct assumptions." (README.md, lines 15-18)

The framework addresses this by implementing "a structured discovery process through protocol-based workflows. Instead of making assumptions, the framework guides LLMs to: (1) Detect intent - Automatically classify the task type, (2) Load relevant protocol - Access specialized workflow for that specific task, (3) Discover requirements - Ask targeted questions before implementation, (4) Present inferences - Show assumptions with confidence levels for approval, (5) Apply quality directives - Enforce performance, security, and accessibility standards" (README.md, lines 24-30).

## Key Statistics

- **GitHub Stars**: 22 (as of 2026-03-17)
- **Framework Token Overhead**: ~15K tokens (7.5% of 200K context window) vs ~185K tokens available for code (92.5%) (README.md, lines 332-338)
- **Development Speed Claim**: "Develop multiple times faster (x2 - x10 faster) from start to finish by dedicating the time to planning and describing the thing you will build, not to fixing endless problems" (README.md, line 40)
- **Iteration Cost Avoidance**: "Framework overhead: 15K tokens. Typical iteration cost when assumptions are wrong: 30-70K tokens per wrong assumption. Break-even: Framework pays for itself by preventing one incorrect assumption per session" (README.md, lines 350-359)
- **Intent Detection Accuracy**: "~95% in testing" (README.md, line 407)

## Key Features

### 16 Specialized Protocols (Modular Workflows)

ctxforge provides "16 specialized workflows, each optimized for specific task types" (README.md, line 370):

1. **FEATURE-DEVELOPMENT** — "Building new functionality" with "Requirements, edge cases, performance targets, accessibility needs" discovery and "Big O analysis, security patterns, WCAG compliance" enforcement (README.md, lines 372-373)

2. **BUG-FIXING** — "Debugging and fixes" with root cause discovery and "regression test creation" enforcement

3. **PERFORMANCE-OPTIMIZATION** — "Speed improvements" with bottleneck identification and "measurement before/after, trade-off analysis, profiling" enforcement

4. **REFACTORING** — "Code improvements" with "test coverage verification, incremental approach" enforcement

5. **CODE-REVIEW** — "Quality assessment" with "security checklist, best practices, complexity analysis" enforcement

6. **TESTING** — "Test creation" with "AAA pattern, isolation, meaningful assertions" enforcement

7. **INVESTIGATION** — "Code exploration" with "systematic exploration, dependency mapping" enforcement

8. **SECURITY-AUDIT** — "Security review" with "OWASP Top 10, input validation, encryption standards" enforcement

9. **ARCHITECTURE-DESIGN** — "System design" with "scalability analysis, trade-off documentation" enforcement

10. **DOCUMENTATION** — "Writing docs" with "completeness, accuracy, examples that work" enforcement

11. **DEPLOYMENT** — "Release process" with "health checks, rollback plan, monitoring setup" enforcement

12. **DEPENDENCY-MANAGEMENT** — "Package updates" with "compatibility testing, changelog review" enforcement

13. **PAIR-PROGRAMMING** — "Collaborative work" with "interactive explanation, knowledge transfer" enforcement

14. **LEARNING** — "Skill development" with "concept explanation, practice exercises, examples" enforcement

15. **DATABASE-MIGRATION** — "Schema changes" with "data integrity checks, rollback script, performance impact" enforcement

16. **LANDING-PAGE-DESIGN** — New in v3.1.0 (October 2025): "Creating high-converting marketing landing pages" with "7 expert-formulated discovery questions focused on conversion psychology" and "industry-specific page patterns, copy framework library, comprehensive quality standards, and industry conversion benchmarks" (CHANGELOG.md, lines 25-70)

### Protocol Auto-Loading

"The LLM automatically detects intent and loads the appropriate protocol based on keyword analysis" (README.md, line 393). CORE.md contains "a keyword mapping table that the LLM scans against your request" (README.md, line 561-570). For example: "'Add user login' → NEW_FEATURE → FEATURE-DEVELOPMENT.md", "'Search is slow, optimize it' → PERFORMANCE → PERFORMANCE-OPTIMIZATION.md" (README.md, lines 396-404).

### Multi-Protocol Sessions

"v3.0 allows switching protocols within the same session" (README.md, line 416). Users can sequence: FEATURE-DEVELOPMENT → CODE-REVIEW → BUG-FIXING → TESTING → DEPLOYMENT within a single continuous session, with "each protocol loads only when needed, keeping context efficient" (README.md, line 435).

### Performance Directives (Auto-Applied Quality Standards)

"30 quality rules: security, performance, accessibility" (README.md, line 336) automatically applied to all implementations. Covers:
- Algorithmic efficiency (O(n log n) max for user-facing ops, memoization, debouncing)
- Memory management (cleanup, lazy loading, list virtualization)
- Data handling (immutable updates, normalized data, server-side pagination)
- User input & interaction (optimistic UI, loading states, client+server validation)
- Framework-specific standards (React: key props, dependency arrays, component composition)

Source: PERFORMANCE-DIRECTIVES.md (2.6K tokens, auto-applied per README.md line 37-40).

### Discovery Questions Framework

"DISCOVERY-QUESTIONS.md" (referenced in README.md line 275) provides "question templates" that protocols use to systematically extract requirements. Feature development protocol includes: "Happy Path Discovery, Edge Case Discovery, Performance Discovery, Error Discovery, Accessibility Discovery, Scope Discovery, Integration Discovery" (FEATURE-DEVELOPMENT.md, lines 22-70).

### Project Context Maintenance

"project.md" (auto-maintained context file, variable size) persists "Project-specific context and learnings" (README.md, line 337) across sessions. Framework enforces "Keep project.md under 20K tokens" (CORE.md, line 32) through compression of "state snapshots after each task" and "reference interfaces, not implementations" (CORE.md, lines 31-34).

## Technical Architecture

### Component Structure

"ctxforge uses protocol auto-loading to minimize context overhead while providing structured workflows" (README.md, line 250). The framework directory structure:

```
docs/context/
├── CORE.md                    # Entry point (2.7K tokens)
├── protocols/                 # 16 specialized workflows (1-6K each)
│   ├── FEATURE-DEVELOPMENT.md
│   ├── BUG-FIXING.md
│   ├── ... [13 more protocols]
│   └── LANDING-PAGE-DESIGN.md
├── PERFORMANCE-DIRECTIVES.md  # Quality standards (2.6K tokens)
├── DISCOVERY-QUESTIONS.md     # Question templates
├── TEMPLATES.md               # Document structures
└── project.md                 # Auto-maintained context (variable)
```

Source: README.md lines 254-278.

### Execution Flow

1. **User Request** → "Add authentication"
2. **CORE.md Intent Detection** (2.7K tokens): "Scans keyword mapping table" → detects NEW_FEATURE intent
3. **Protocol Load**: FEATURE-DEVELOPMENT.md (4K tokens) loaded automatically
4. **Discovery Phase**: "Ask structured questions: Credentials? Email/username? Session duration? Password requirements? 2FA needed? Rate limiting strategy?" (README.md, lines 301-306)
5. **Inference Phase**: "Show assumptions: [INFER-HIGH] bcrypt for hashing, [INFER-MEDIUM] 24h session timeout, [INFER-LOW] 5 failed attempt limit" (README.md, lines 311-314)
6. **Approval**: "User confirms or corrects" (README.md, line 319)
7. **Implementation**: "Generate code + tests + docs, Apply quality directives, Update project.md" (README.md, lines 323-326)

Source: README.md lines 282-327.

### Token Efficiency Analysis

Framework optimizes context window usage through selective protocol loading:

| Component | Tokens | % of 200K Window | What It Provides |
|-----------|--------|------------------|------------------|
| CORE.md | 2.7K | 1.4% | Intent detection, protocol routing |
| Protocol (avg) | 3.3K | 1.7% | Specialized workflow for task type |
| Performance Directives | 2.6K | 1.3% | 30 quality rules |
| project.md (typical) | 8K | 4% | Project-specific context and learnings |
| **Framework Total** | **~15K** | **7.5%** | Complete structured workflow system |
| **Your Code Context** | **~185K** | **92.5%** | Approximately 6,000 lines of code with context |

**Break-Even Analysis**: "Framework overhead: 15K tokens. Skip framework, LLM guesses correctly: 0K overhead (best case, but relies on luck). Skip framework, LLM guesses wrong: 30-70K in iteration cycles (typical case when assumptions are incorrect). Break-even: Framework pays for itself by preventing one incorrect assumption per session." (README.md, lines 549-557)

Source: README.md lines 332-359.

### Protocol Customization

"All protocols are markdown files you can freely modify or extend" (README.md, line 595). Custom protocols can be created by:

1. Creating new protocol file: `touch docs/context/protocols/CUSTOM-PROTOCOL.md`
2. Following structure of existing protocols: "When to use section, Discovery questions, Workflow steps, Quality criteria" (README.md, lines 613-616)
3. Adding to CORE.md intent detection table with keywords and protocol mapping (README.md, lines 618-620)
4. Organization-specific protocols supported: "ACME-CORP-COMPLIANCE.md, ACME-CORP-API-DESIGN.md, ACME-CORP-DEPLOYMENT.md" (README.md, lines 624-629)

Source: README.md lines 593-629.

## Installation & Usage

### Installation

**For Node.js projects:**
```bash
npx ctxforge init
```

**Universal installation (any language):**
```bash
curl -L https://github.com/vencolini/ctxforge/archive/refs/heads/main.zip -o ctxforge.zip
unzip ctxforge.zip
cp -r ctxforge-main/lib/framework docs/context
rm -rf ctxforge.zip ctxforge-main
```

Source: README.md lines 50-65.

### Basic Usage

"With any LLM (Claude, ChatGPT, Gemini, Cursor, Copilot, local models): Read docs/context/CORE.md and ask what I want to work on. That's it. The framework handles the rest." (README.md, lines 68-75)

### CLI Commands

ctxforge provides utility commands via npm:

```bash
npx ctxforge init           # Initialize framework in current project
npx ctxforge validate       # Validate framework installation and structure
npx ctxforge health         # Check context health and token usage
npx ctxforge status         # Show current project status from project.md
npx ctxforge optimize       # Optimize context size (compress project.md)
npx ctxforge version        # Show version information
npx ctxforge --help         # Show help and available commands
```

Source: README.md lines 774-794.

### Platform Integration

**Claude Code:**
```bash
claude-code docs/context/CORE.md
```

**Cursor (.cursorrules file):**
```
Before starting tasks, read docs/context/CORE.md to load the ctxforge framework and follow the appropriate protocol for the task type.
```

**ChatGPT (Custom Instructions):**
```
For coding projects: If docs/context/CORE.md exists, read it at session start and follow the protocol-based workflow for all tasks.
```

**Cline / Continue / Aider / Other CLIs:**
```
Universal command: Read docs/context/CORE.md and ask what I want to work on
```

**GitHub Copilot (Workspace context):**
```
Add docs/context/ to workspace context sources
Prefix requests with: "Following ctxforge protocols in docs/context/"
```

Source: README.md lines 482-507.

### Example: Feature Development Workflow

**Without ctxforge:**
```
Developer: "Add search functionality"
LLM: [Implements Elasticsearch cluster with Docker, Redis caching, complex distributed architecture]
Developer: "I need simple PostgreSQL full-text search for 50K items..."
[Multiple iteration cycles to correct assumptions and align with requirements]
```

**With ctxforge:**
```
Developer: "Add search functionality"
LLM: ✓ Intent detected: NEW_FEATURE
     ✓ Loading: docs/context/protocols/FEATURE-DEVELOPMENT.md

Before implementing, let me understand the requirements:
1. What data should be searchable?
2. Approximately how many items?
3. Should search happen as user types or when they press Enter?
4. What kind of matching? (exact, fuzzy, typo-tolerant?)
5. Current database and version?
6. Performance expectation?
7. Accessibility needs?

Developer: "Product names and descriptions. 50K items. Real-time as they type. Fuzzy matching with typos. PostgreSQL 14. Under 200ms. Yes to accessibility."

LLM: Based on your answers, here are my inferences:
     [INFER-HIGH] PostgreSQL GIN index with tsvector for full-text search
     [INFER-HIGH] pg_trgm extension for fuzzy matching capabilities
     [INFER-MEDIUM] Debounced search input (300ms) to reduce query load
     [INFER-MEDIUM] ARIA live regions for screen reader announcements
     [INFER-LOW] Limit results to 50 items, paginate if more needed

Developer: "Yes"
LLM: [Implements complete solution with tests, docs, performance logging]
     Implementation complete. Average query time: 140ms
```

Source: README.md lines 79-155.

## Relevance to Claude Code Development

ctxforge is relevant to Claude Code development in the following areas:

1. **Context Engineering Patterns** — Demonstrates systematic protocols for requirement extraction and validation. ctxforge's approach to "Make ALL technical assumptions explicit" with "Show confidence levels (HIGH/MEDIUM/LOW)" aligns with Claude Code's emphasis on transparent reasoning.

2. **LLM-Assisted Development Workflows** — Provides tested patterns for structuring human-LLM interactions at scale. The "16 specialized workflows" pattern enables different task types to be handled with appropriate discovery depth, reducing assumption-driven iteration.

3. **Token Efficiency** — Models token budget allocation: framework overhead (~7.5%) vs. available code context (~92.5%). The "break-even by preventing one wrong assumption" analysis is directly applicable to Claude Code session planning.

4. **Quality Enforcement** — PERFORMANCE-DIRECTIVES.md provides actionable quality standards (30+ rules) that can be auto-applied: algorithmic efficiency targets, memory management patterns, accessibility compliance, security baselines. These are language-agnostic and testable.

5. **Multi-Protocol Session Orchestration** — Demonstrates how to switch between specialized workflows in a single session without reloading all context. Pattern applicable to Claude Code agent delegation.

6. **Custom Protocol Development** — Shows how to extend a framework through markdown-based configuration without modifying the core system. This pattern is relevant for building domain-specific Claude Code extensions.

## Limitations and Caveats

**From documented sources:**

1. **LLM Capability Requirements** — "LLM must be able to read local files. Recommended: 50K+ token context window (framework uses ~15K). Any programming language (framework is language-agnostic)" (README.md, lines 641-643). Not compatible with "LLMs without file reading capability, very small context windows (<30K tokens), models with poor instruction following (older or smaller models)" (README.md, lines 656-659).

2. **Intent Detection Not Foolproof** — While "Intent detection accuracy: ~95% in testing" (README.md, line 407), manual protocol selection is available: "Read docs/context/protocols/REFACTORING.md and help me refactor the auth module" (README.md, line 411-412). Ambiguous cases prompt: "I detect you want to [intent]. Is that correct? If yes: I'll load the [PROTOCOL_NAME] protocol. If no: What specifically do you need?" (README.md, lines 587-591).

3. **Context Window Still a Constraint** — Framework optimizes but does not eliminate context limitations. "Total session cost: CORE.md (5K) + Protocol (~4K) + project.md (~5-10K) = 14-19K tokens" leaves 180K for code in a 200K window (README.md, line 148). For very large codebases, project.md compression becomes critical.

4. **v3.0 Migration Path Required** — v2.1 and v3.0 are "both maintained, fully backward compatible" (README.md, line 717), but v3.0 is recommended for new projects due to "40% reduction in token overhead, 15 vs 6 workflows, intent detection automation" (README.md, lines 705-712).

5. **Framework Gets in the Way for Simple Tasks** — Acknowledged in FAQ: "You have full control: Skip framework for specific task, Use framework selectively, Override protocol choice, Start fresh mid-session" (README.md, lines 728-759). Framework assumes "systematic discovery adds value; skip when requirements are already clear" (README.md, line 760).

6. **Manual Protocol Customization Burden** — While "All protocols are markdown files you can freely modify" (README.md, line 595), there is no built-in UI or command to create protocols. Custom organization-specific protocols require manual file creation and CORE.md table updates.

## References

- **README.md** — <https://github.com/vencolini/ctxforge/blob/main/README.md> (accessed 2026-03-17)
- **package.json** — <https://github.com/vencolini/ctxforge/blob/main/package.json> (accessed 2026-03-17)
- **CHANGELOG.md** — <https://github.com/vencolini/ctxforge/blob/main/CHANGELOG.md> (accessed 2026-03-17)
- **lib/framework/CORE.md** — <https://github.com/vencolini/ctxforge/blob/main/lib/framework/CORE.md> (accessed 2026-03-17)
- **lib/framework/PERFORMANCE-DIRECTIVES.md** — <https://github.com/vencolini/ctxforge/blob/main/lib/framework/PERFORMANCE-DIRECTIVES.md> (accessed 2026-03-17)
- **lib/framework/protocols/FEATURE-DEVELOPMENT.md** — <https://github.com/vencolini/ctxforge/blob/main/lib/framework/protocols/FEATURE-DEVELOPMENT.md> (accessed 2026-03-17)
- **NPM Package** — <https://www.npmjs.com/package/ctxforge> (v3.1.2, accessed 2026-03-17)
- **GitHub Repository** — <https://github.com/vencolini/ctxforge> (22 stars as of 2026-03-17)

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Prompt Engine](../prompt-engineering/prompt-engine.md) | prompt-engineering | automated prompt optimization tool complementing ctxforge's discovery process with generation/refinement |
| [Claude Code Prompt Improver](../prompt-engineering/claude-code-prompt-improver.md) | prompt-engineering | shares discovery-first methodology: both systems perform context research before execution to improve requirement clarity |
| [System Prompts and Models of AI Tools](../prompt-engineering/system-prompts-ai-tools.md) | prompt-engineering | reference for understanding how production AI systems structure instructions and apply quality standards (patterns similar to ctxforge performance directives) |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | progressive disclosure pattern (search → timeline → get_observations) complements ctxforge's token efficiency optimization for context window usage |
| [Superpowers](../agent-frameworks/superpowers.md) | agent-frameworks | shares structured discovery-and-validation methodology: both enforce systematic workflows before implementation to guide LLM behavior and reduce assumption-driven errors |

---

## Freshness Tracking

**Last Reviewed**: 2026-03-17
**Next Review**: 2026-06-17 (3 months)

### Confidence Summary

| Section | Confidence | Notes |
|---------|-----------|-------|
| Identity/Metadata | high | Full official sources (GitHub API, package.json, git log) |
| Problem Addressed | high | Directly quoted from official README |
| Key Statistics | high | GitHub API data and official documentation; stars verified at access time |
| Key Features | high | All 16 protocols documented with full descriptions in README; v3.1.0 landing page protocol verified in CHANGELOG |
| Technical Architecture | high | Full component structure and execution flow from README with diagram; token analysis provided with exact figures |
| Installation & Usage | high | Official installation commands and CLI reference verified against package.json and bin/ctxforge.js |
| Relevance to Claude Code | medium | Analysis based on feature extraction and cross-domain application; no explicit Claude Code integration documented |
| Limitations | high | Quoted directly from README FAQ and compatibility sections; migration notes from CHANGELOG verified |

### Content Changes from Previous Review

No previous version on record. Initial entry created 2026-03-17.
