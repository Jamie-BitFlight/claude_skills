---
name: unblocked
research_date: 2026-03-13
source_url: https://getunblocked.com/
documentation_url: https://docs.getunblocked.com/
version_at_research: current
license: Proprietary
freshness_tracking:
  last_verified: 2026-03-13
  version_at_verification: current
  next_review: 2026-06-13
  confidence_map: "Overview: high, Problem Addressed: high, Key Features: high, Technical Architecture: high, Installation & Usage: high, Relevance: high, References: high"
---

# Unblocked

## Overview

Unblocked is a cloud-based context engine and decision-grade information platform that augments AI coding agents with organizational knowledge by synthesizing code history, architectural decisions, team conventions, and cross-functional context from multiple sources (GitHub, Slack, Confluence, Jira, etc.). It enables coding agents to generate production-ready, mergeable code on the first attempt without requiring human intervention between iteration cycles. The platform uses AI-powered retrieval, deconfliction algorithms, and targeted context compression to surface only decision-relevant information, reducing token waste while improving code generation fidelity. (SOURCE: <https://getunblocked.com/>, accessed 2026-03-13)

---

## Problem Addressed

AI coding assistants fail to produce mergeable code on the first attempt because they lack organizational context. Without understanding:
- Architectural patterns and design decisions
- Team naming conventions and coding standards
- Historical context about why code was written a certain way
- Cross-functional knowledge from docs, conversations, and issue tracking

Agents generate code that "break[s] patterns, miss[es] dependencies, and fail[s] tests." (SOURCE: <https://getunblocked.com/>, accessed 2026-03-13) This forces engineers to babysit each session, supplying missing context, fixing wrong assumptions, and burning tokens on retrieval loops.

---

## Technical Architecture

### Context Engine

Unblocked "connects your code, docs, and the conversations to build a model of your engineering system. Agents use that context to generate code that fits." (SOURCE: <https://getunblocked.com/>, accessed 2026-03-13)

The engine operates through four mechanisms:

1. **Unified System Context** — Merges signals from multiple sources:
   - Source code and pull requests (via GitHub, GitLab, Bitbucket, Azure DevOps)
   - Documentation systems (Confluence, Coda, Google Drive, Notion)
   - Project management (Linear, Jira, Asana)
   - Messaging platforms (Slack, Microsoft Teams)
   - CI systems (GitHub Actions, CircleCI, Buildkite, GitLab Pipelines)

2. **Targeted Retrieval** — Retrieves "only the information agents need from the graph" rather than flooding the context window with all available data.

3. **Source Deconfliction** — When multiple sources contradict each other, resolves via "recency + authority signals" to determine the authoritative answer.

4. **Personalized Relevance** — Scopes context to a specific team's repositories, teammates, and work history, ensuring agents receive only applicable decisions and conventions.

5. **Token Optimization** — "Ranked, compressed context — no waste in the prompt window."

### Data Governance

"Permissions + policies are enforced automatically across systems." This means Unblocked respects organization-level access controls and does not surface information that agents should not see. (SOURCE: <https://getunblocked.com/>, accessed 2026-03-13)

---

## Key Features

### 1. AI Code Review

Unblocked analyzes pull requests and generates context-aware code review comments. Unlike generic linters, reviews reference team patterns, historical decisions, and system architecture.

**Mechanism**: The code review feature understands your codebase and company by ingesting all connected data sources. When a PR is submitted, Unblocked examines the changes, cross-references against your team's conventions (from prior commits, discussions, docs), and identifies both logical bugs and style inconsistencies based on your specific patterns — not generic rules.

**CI Failure Agent**: Automatically diagnoses why CI tests fail and suggests fixes grounded in your system's architecture and test patterns.

**PR Summaries**: Auto-generates summaries of pull request changes.

(SOURCE: <https://docs.getunblocked.com/billing/unblocked-plans>, accessed 2026-03-13)

### 2. Q&A Platform — Ask Questions About Your Codebase

Engineers can ask natural-language questions about their code and receive answers with cited sources. Questions can be asked:
- On the web via the Unblocked dashboard
- In the IDE (Unblocked extension)
- In messaging platforms (Slack, Microsoft Teams)
- Programmatically via REST API

**Example answers**: "How does the user authentication system work?" returns an explanation grounded in code references, PR discussions, documentation, and architectural decisions that explain not just what the code does but why it was designed that way.

**Incognito Mode**: Ask questions privately without them being logged to workspace history.

(SOURCE: <https://docs.getunblocked.com/what-is-unblocked>, accessed 2026-03-13)

### 3. IDE Integration

Unblocked surfaces contextual information directly in code editors. When viewing a file or specific line, the IDE extension displays:
- Past decisions and discussions related to that code
- Relevant architectural documentation
- Historical context about why something was written the way it was

(SOURCE: <https://docs.getunblocked.com/what-is-unblocked>, accessed 2026-03-13)

### 4. MCP Integration

Unblocked exposes a Model Context Protocol (MCP) server, enabling direct integration with Claude Code, Cursor, Copilot, and other MCP-compatible agents. This allows agents to query Unblocked's context engine in real-time during code generation without leaving their workflow.

(SOURCE: <https://docs.getunblocked.com/billing/unblocked-plans>, accessed 2026-03-13)

### 5. REST API

The Unblocked API is a REST interface for:
- Adding documents to collections (knowledge bases)
- Asking questions about your codebase programmatically
- Building custom workflows that leverage Unblocked's context engine

**Authentication**: Personal Access Tokens (1,000 calls/day limit) or Team Access Tokens (full org access, rotate regularly).

**Endpoints**:
- `POST /api/v1/collections` — Create a collection
- `PUT /api/v1/documents` — Add a document
- `PUT /api/v1/answers/{questionId}` — Submit a question
- `GET /api/v1/answers/{questionId}` — Poll for answer

Responses include the answer text and references (source URLs/lines).

(SOURCE: <https://docs.getunblocked.com/api-reference/quickstart>, accessed 2026-03-13)

---

## Installation & Usage

### Getting Started

Unblocked is a cloud-based SaaS platform with no local installation required. Users access it through:

1. **Web Dashboard**: <https://app.getunblocked.com> (login with company account or SSO)
2. **IDE Extensions**: Install Unblocked extension for VS Code, JetBrains IDEs, or other editors from respective marketplaces
3. **API Access**: Authenticate with Personal or Team Access Tokens for programmatic queries

### Setup Process

1. Create an Unblocked account on <https://getunblocked.com/>
2. Start 21-day free trial (no credit card required)
3. Connect data sources:
   - GitHub/GitLab/Bitbucket repository access
   - Confluence/Notion/Google Drive documentation
   - Jira/Linear/Asana project management
   - Slack/Microsoft Teams workspace
4. Configure team permissions and data scopes via Unblocked dashboard
5. Launch IDE extension or use web dashboard to query organizational context

(SOURCE: <https://docs.getunblocked.com/what-is-unblocked>, <https://docs.getunblocked.com/billing/unblocked-plans>, accessed 2026-03-13)

---

## Integration Ecosystem

### Supported Data Sources

**Source Code Management** (7 systems):
- GitHub.com and GitHub Enterprise
- GitLab.com and GitLab Self-Managed
- Bitbucket Cloud and Bitbucket Data Center
- Azure DevOps

**Documentation** (8 systems):
- Confluence (Cloud and Data Center)
- Coda, Notion, Google Drive, Google Drive for Workspaces
- External websites (via web crawl)
- Stack Overflow for Teams

**Project Management** (4 systems):
- Linear, Jira (Cloud and Data Center), Asana

**Messaging** (2 systems):
- Slack, Microsoft Teams

**Continuous Integration** (5 systems):
- GitHub Actions, GitLab Pipelines, CircleCI, Buildkite, Bitbucket Pipelines

**Custom Integrations**: Teams can build integrations using the public REST API if their tool is not listed.

(SOURCE: <https://docs.getunblocked.com/data-sources/data-sources-overview>, accessed 2026-03-13)

---

## Performance and Impact

### Quantified Outcomes

**Token Efficiency**: "48% fewer tokens for the same task" — without Unblocked, a coding task consumed 20.9M tokens; with Unblocked, the same task used 10.8M tokens.

**Speed**: "83% faster for the same task" — engineers moved from a multi-step workflow (task → agent response → corrections → more fixes) to a single-pass completion with minimal rework.

**Code Quality**: With context, generated code:
- Preserves backwards compatibility
- Passes tests across modules
- Matches team patterns

Without context, generated code:
- Broke backwards compatibility
- Had 12 compilation failures
- Caused cascading module breaks

(SOURCE: <https://getunblocked.com/>, accessed 2026-03-13)

### ROI Calculation (Industry Benchmarks)

Based on a 200-employee organization with $160K average annual salary:
- Time saved searching: $4M annually
- Onboarding acceleration: $267K annually
- Reduced support overhead: $768K annually
- **Total annual savings: $5M**

(SOURCE: <https://getunblocked.com/pricing/>, accessed 2026-03-13)

---

## Pricing and Billing

### Plan Tiers

**Code Review** — $19 USD per user/month (billed annually)
- Unlimited code reviews
- Unlimited PR summaries
- Unlimited repositories
- Unlimited data sources
- CI Failure Agent
- Adaptive learning

**Platform** — $29 USD per user/month (billed annually)
- Everything in Code Review, plus:
- Connect context to Claude, Cursor, Copilot, and more
- Ask questions about your software and its history
- Incognito mode for private questions
- API access
- Web-based support

**Enterprise** — Custom pricing
- Everything in Platform, plus:
- SSO & advanced security
- Data Shield permission enforcement
- On-premises deployment options
- Support for GitHub Enterprise, Jira Data Center, Bitbucket Data Center
- Guided security review
- Dedicated customer success
- Priority support via Slack and Zoom

### Free Trial

"All new Unblocked accounts receive a 21-day free trial that includes access to all the features available on the Enterprise plan. A credit card is not required to start a trial." (SOURCE: <https://docs.getunblocked.com/billing/unblocked-plans>, accessed 2026-03-13)

### API Limits

- Personal Access Tokens: 1,000 API calls per day
- Team Access Tokens: Unlimited (per plan tier)
- Answers API: 1,000 questions per day per organization

(SOURCE: <https://docs.getunblocked.com/api-reference/quickstart>, accessed 2026-03-13)

---

## Security and Data Privacy

### Isolation and Ownership

"Unblocked's security model means that only your team has access to the model used for generating answers to your questions. Your code, documentation, and questions to Unblocked will never be used to train another organization's Unblocked instance."

Each organization's Unblocked instance is isolated — no cross-contamination of context or training data.

### Compliance

Unblocked supports:
- SOC 2 Type II compliance
- SSO integration (SAML, Okta, Entra ID, and more)
- Encryption in transit and at rest
- Data Shield permission enforcement (respects GitHub/GitLab team permissions)
- On-premises deployment options (Enterprise plan)

(SOURCE: <https://getunblocked.com/>, <https://docs.getunblocked.com/what-is-unblocked>, accessed 2026-03-13)

---

## Limitations and Caveats

1. **API Rate Limits**: Personal Access Tokens are capped at 1,000 calls per day, limiting high-volume automation scenarios. Team tokens have higher limits but still constrain rapid iteration.

2. **Answers API Quota**: Limited to 1,000 questions per day per organization, which may constrain large teams with heavy usage.

3. **Data Source Dependency**: Context quality depends entirely on the quality, freshness, and completeness of connected data sources. If GitHub commits lack context, Slack discussions are archived, or documentation is outdated, Unblocked's context is degraded.

4. **Cold Start Problem**: New teams or projects with minimal history will have less context for agents to work with. The engine improves as more conversations and decisions accumulate.

5. **Training Model Dependency**: While data is isolated per organization, the underlying LLM models used to generate context are not disclosed. Changes to Unblocked's model architecture could affect the quality and style of generated context.

6. **Not mentioned in reviewed sources**: Handling of deprecated data sources, maximum organization size, scaling characteristics for very large codebases (>10M LOC), or failure modes when primary data sources are unavailable.

---

## Relevance to Claude Code Development

Unblocked directly addresses a core pain point in AI-driven development: context starvation. For Claude Code users building complex features in brownfield codebases:

1. **Code Generation Fidelity**: By providing architectural context and team patterns to Claude Code's code generation capabilities, agents produce code that aligns with existing systems without requiring human review cycles.

2. **Integration with Claude Code**: Unblocked's MCP server enables Claude Code to query organizational context in real-time during task execution, reducing hallucinations and pattern violations.

3. **Development Speed**: The documented 83% time savings translates directly to faster feature implementation when using Claude Code for autonomous coding tasks.

4. **Onboarding and Knowledge Management**: New team members using Claude Code benefit from instant access to historical decisions and architectural rationale without interrupting senior engineers.

5. **Code Review Automation**: Unblocked's AI code review feature can serve as a first-pass reviewer for Claude Code-generated PRs, catching logical errors and pattern violations before human review.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude-Mem](./claude-mem.md) | context-management | Alternative persistent memory compression approach; both augment coding agents with session-aware context |
| [Local Memory](./local-memory.md) | context-management | Complementary local-first memory system; shared problem (context amnesia) with different architecture (embedded Qdrant vs cloud integration) |
| [SourceSync.ai](./sourcesyncai.md) | context-management | Unified RAG retrieval layer; Unblocked feeds multi-source data through SourceSync's hybrid search for context enrichment |
| [Straion](./straion.md) | context-management | Overlapping use case: dynamic context injection into agents; Unblocked provides cross-functional knowledge, Straion injects engineering standards |
| [Jina AI](./jina-ai.md) | context-management | Complementary embedding and search layer; Reader API converts URLs to Markdown for Unblocked's content ingestion pipeline |
| [Claude-Task-Master](../task-management/claude-task-master.md) | task-management | Adjacent workflow: task decomposition benefits from Unblocked's architectural context for code generation fidelity |
| [SourceSync.ai MCP](../mcp-ecosystem/sourcesyncai-mcp.md) | mcp-ecosystem | MCP server alternative for unified knowledge base access; both expose RAG context to agents via standardized protocol |
| [Cline](../coding-agents/cline.md) | coding-agents | End-user agent; Unblocked integration improves Cline's ability to generate org-specific code without context hallucinations |

---

## References

- [Unblocked Home](https://getunblocked.com/) (accessed 2026-03-13)
- [What is Unblocked?](https://docs.getunblocked.com/what-is-unblocked) (accessed 2026-03-13)
- [Unblocked Pricing](https://getunblocked.com/pricing/) (accessed 2026-03-13)
- [Unblocked Plans](https://docs.getunblocked.com/billing/unblocked-plans) (accessed 2026-03-13)
- [Quickstart for the Unblocked API](https://docs.getunblocked.com/api-reference/quickstart) (accessed 2026-03-13)
- [Data Sources Overview](https://docs.getunblocked.com/data-sources/data-sources-overview) (accessed 2026-03-13)
- [Unblocked Code Review Review (2026): Honest Take After Testing](https://www.automateed.com/unblocked-code-review-review) — Automateed, March 9, 2026 (accessed 2026-03-13)
- Tracxn Company Profile: Unblocked Inc. — Last updated February 8, 2025 (accessed 2026-03-13)
