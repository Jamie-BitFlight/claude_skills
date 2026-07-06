---
title: "Notra"
research_date: "2026-03-04"
source_url: "https://www.usenotra.com"
github_url: "Not publicly available (SaaS product)"
version_at_research: "Not versioned (SaaS, continuously deployed)"
license: "Proprietary (commercial SaaS)"
last_verified: "2026-03-04"
version_at_verification: "N/A (SaaS, continuously deployed)"
next_review: "2026-06-04"
---

## Overview

Notra is a SaaS tool that automatically generates publish-ready content — changelogs, blog posts, and social media updates — by monitoring a development team's activity in GitHub, Linear, and Slack. It watches merged PRs, shipped issues, and relevant conversations in the background, then drafts content that matches the team's configured brand voice. The goal is to eliminate the manual effort of writing release notes and announcements after shipping work.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Developer teams ship features but delay or skip publishing changelogs and announcements | Notra auto-generates first drafts from merged PRs and closed issues immediately after shipping |
| Release notes and blog post drafts sound inconsistent across team members | Brand voice matching learns the team's tone and style so all generated content sounds consistent |
| Tracking what shipped requires manually cross-referencing GitHub, Linear, and Slack | Notra aggregates all activity into a unified timeline across all connected sources |
| Writing content about shipped work interrupts development workflow | Content generation runs in the background; team reviews and publishes rather than drafts |
| Small teams lack dedicated technical writers for release communications | AI-generated first drafts reduce the skill barrier; team members only need to review and approve |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | N/A (no public repo) | 2026-03-04 |
| Public customers | Consent, Upstash, DataBuddy, Stack Auth (listed on homepage) | 2026-03-04 |
| Free tier AI credits | 15 per month | 2026-03-04 |
| Pro plan price | $50/month | 2026-03-04 |
| Latest Release | N/A (SaaS, continuously deployed) | 2026-03-04 |

SOURCE: [Notra homepage](https://www.usenotra.com) (accessed 2026-03-04), [Notra pricing page](https://www.usenotra.com/pricing) (accessed 2026-03-04)

---

## Key Features

### Activity Aggregation

- Unified activity feed collects events from GitHub (PRs, commits), Linear (issues, milestones), and Slack (conversations)
- Events appear in a chronological timeline readable by the whole team
- Configurable lookback windows to control how far back Notra scans when generating content

### AI Content Generation

- Auto-generates changelog entries from every merged PR — no manual release notes required
- Drafts blog post announcements from shipped features
- Produces short social media updates from releases and milestones
- All drafts are editable before publishing; Notra writes the first draft, humans review and approve

### Brand Voice Matching

- Teams configure a company profile with a description and tone setting (e.g., "Conversational")
- Notra learns tone and style from the profile configuration so generated content matches the team's voice
- Tone is applied consistently across all output types (changelogs, blog posts, social posts)

### Integrations

- One-click integrations with GitHub, Linear, Slack, DataBuddy, Framer, Marble, and Webflow
- Connection setup completes in under a minute per integration
- More integrations listed as coming soon

### Workflow Automation

- Workflows are configurable pipelines that map activity types to content output types
- Free tier supports 3 workflows; Pro and Enterprise tiers offer unlimited workflows
- Activity logs retained for 7 days (Free), 30 days (Pro), or unlimited (Enterprise)

---

## Technical Architecture

Notra operates as a cloud-hosted SaaS with an event-driven pipeline:

```text
Source integrations (GitHub, Linear, Slack)
  │
  ▼
Activity ingestion
  │  Events: PR merges, issue closures, Slack messages
  │  Stored in activity log (retention: 7–unlimited days)
  ▼
Content workflow trigger
  │  Workflow rules determine which events generate which content types
  │  Configurable lookback window controls event scope
  ▼
AI generation engine
  │  Brand voice profile applied to generation
  │  Outputs: changelog entry, blog draft, social post
  ▼
Review queue
  │  Team reviews and edits generated drafts
  ▼
Publish
  │  Content published to connected output channels (Framer, Webflow, Marble, etc.)
```

There is no self-hosted option; the product is fully managed SaaS. The application is accessible at `app.usenotra.com`. Source code is not publicly available.

---

## Installation & Usage

Notra is a web application — no local installation required.

```text
1. Sign up at https://app.usenotra.com/signup (free tier available)
2. Connect integrations: GitHub, Linear, Slack (one-click OAuth)
3. Configure company profile: description and tone setting
4. Create workflows: map activity types (e.g., merged PR) to content types (e.g., changelog)
5. Review generated drafts in the Notra dashboard
6. Edit and publish approved content
```

The free tier allows 2 team members, 3 workflows, 2 integrations, and 15 AI credits per month.

The Pro tier ($50/month) supports 5 team members, unlimited workflows and integrations, 200 AI credits per month (additional credits at $0.01 each), and 30-day log retention.

Enterprise pricing is custom, with unlimited team members, custom integrations, unlimited log retention, dedicated support, and custom AI credit limits.

SOURCE: [Notra pricing](https://www.usenotra.com/pricing) (accessed 2026-03-04)

---

## Relevance to Claude Code Development

### Applications

- Teams maintaining Claude Code skills or plugins could use Notra to auto-generate changelogs and release announcements from merged PRs in the `claude_skills` repo
- Reduces the documentation overhead of publishing what changed after each release cycle
- Relevant pattern for any team shipping developer tools and needing to communicate changes to users

### Patterns Worth Adopting

- Activity-feed aggregation pattern: collecting events from multiple developer workflow tools (GitHub, Linear, Slack) into a single unified log is a useful architectural pattern for agent context-gathering
- Brand voice configuration: the idea of a persistent company profile that constrains AI output style is a useful prompt engineering pattern — storing tone/style metadata alongside generation prompts
- Workflow mapping: explicitly mapping event types to output types (PR merge → changelog entry) is a clear, auditable automation pattern applicable to skill-based agent workflows

### Integration Opportunities

- Notra could be connected to the `claude_skills` GitHub repo to automatically draft changelog entries for skill releases and plugin updates
- The content review queue pattern (AI drafts, human approves) matches the agent-output review workflow used in this repository's quality gates
- If Notra exposes a future API or webhook, it could be integrated as a post-implementation step in the `/complete-implementation` workflow to auto-draft release communications

---

## References

- [Notra homepage](https://www.usenotra.com) (accessed 2026-03-04)
- [Notra pricing page](https://www.usenotra.com/pricing) (accessed 2026-03-04)
- [Notra docs](https://docs.usenotra.com) (linked from site footer; not fully indexed)
- [Notra changelog/showcase](https://www.usenotra.com/changelog) (linked from site nav; not fully indexed)

---
