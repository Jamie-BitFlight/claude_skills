# GitDocify

| Field         | Value                                  |
| ------------- | -------------------------------------- |
| Research Date | 2026-01-31                             |
| Primary URL   | <https://gitdocify.com>                |
| Backend URL   | <https://api.gitdocify.com>            |
| Version       | Production (SaaS)                      |
| License       | Proprietary (commercial SaaS)          |
| Hosting       | Vercel (frontend), Supabase (database) |

---

## Overview

GitDocify is a commercial SaaS tool that generates README documentation for GitHub repositories using AI. Users connect their GitHub account, select a repository (public or private depending on plan), and receive professionally formatted README files in seconds. The service launched in early 2025 and operates on a freemium model with one-time purchase and subscription options.

---

## Problem Addressed

| Problem                                   | Solution                                                     |
| ----------------------------------------- | ------------------------------------------------------------ |
| Writing README files is time-consuming    | AI-powered generation produces complete README in seconds    |
| Developers neglect documentation          | Low-friction process (connect GitHub, select repo, generate) |
| Inconsistent documentation quality        | Standardized AI output ensures professional formatting       |
| Private repo documentation requires setup | GitHub App integration handles authentication automatically  |
| Documentation maintenance burden          | Regenerate as project evolves (with paid plans)              |

---

## Key Statistics

| Metric                   | Value      | Date Gathered |
| ------------------------ | ---------- | ------------- |
| Public GitHub Repo       | Not found  | 2026-01-31    |
| Supabase Project Created | 2025-01-16 | 2026-01-31    |
| Last Site Update         | 2025-12-06 | 2026-01-31    |
| Hosting Platform         | Vercel     | 2026-01-31    |

Note: GitDocify is a closed-source commercial product. No public GitHub repository or open-source components were found.

---

## Key Features

### GitHub Integration

- OAuth-based GitHub App authentication
- Support for public repositories (all plans)
- Support for private repositories (paid plans)
- Repository browser for easy selection
- Automatic code analysis across repository

### AI Documentation Generation

- README generation in seconds
- Professional markdown formatting
- Project analysis for context-aware content
- "Basic AI agent" (free tier)
- "Most Advanced AI Agent" (paid tiers)

### Output Options

- Markdown export
- Customization via add-ons
- Full project analysis (paid)

### Pricing Tiers (as of 2026-01-31)

| Tier         | Price         | Generations | Features                                       |
| ------------ | ------------- | ----------- | ---------------------------------------------- |
| Free Trial   | $0            | 1           | Public repos, basic AI, no credit card         |
| Starter Pack | $3.99 (once)  | 10          | Public/private repos, add-ons, markdown export |
| Monthly      | $14.99/mo     | 50/month    | Advanced AI, full analysis, all features       |
| Lifetime     | $54.99 (once) | Unlimited   | All features, permanent access                 |

### Announced/Coming Soon

- "Full Documentation Coming Soon" - complete code documentation features beyond README

---

## Technical Architecture

### Stack Components (extracted from production JavaScript)

| Component      | Technology                            |
| -------------- | ------------------------------------- |
| Frontend       | React (SPA), hosted on Vercel         |
| Backend API    | api.gitdocify.com (unknown framework) |
| Database       | Supabase (PostgreSQL)                 |
| Payments       | Stripe (checkout and customer portal) |
| Analytics      | PostHog, Google Tag Manager           |
| Authentication | GitHub OAuth via Supabase             |

### API Endpoints (observed)

```text
/api/github/install-url    # GitHub App installation
/api/github/repositories   # List connected repos
/api/github/link           # Link repo for generation
```

### Workflow

1. User authenticates via GitHub OAuth
2. User selects repository from connected repos
3. Backend analyzes repository code
4. AI generates README based on analysis
5. User downloads/copies markdown output

---

## Installation and Usage

GitDocify is a web-based SaaS product. No local installation required.

### Getting Started

1. Visit <https://gitdocify.com>
2. Click "Get Started" or similar CTA
3. Authenticate with GitHub account
4. Select a public repository (free tier)
5. Generate README
6. Export markdown

### No CLI or Local Tool

There is no command-line interface or self-hosted option. The service operates entirely through the web interface.

---

## Relevance to Claude Code Development

### Direct Applications

1. **Documentation Workflow Comparison**: Provides a reference point for AI-assisted documentation generation patterns. Useful for comparing approaches when building documentation skills for Claude Code.

2. **SaaS Architecture Reference**: Demonstrates production patterns for GitHub-integrated AI services (OAuth, Supabase, Stripe, Vercel).

3. **Pricing Model Insights**: Offers a case study in monetizing AI documentation services with tiered offerings.

### Patterns Worth Studying

1. **GitHub App Integration**: OAuth flow + repository access pattern is reusable for skills that need GitHub integration.

2. **Freemium AI Services**: One-time purchase credits model as alternative to pure subscription.

3. **AI Agent Tiering**: Marketing distinction between "basic" and "advanced" AI agents.

### Limitations for Claude Code

1. **Closed Source**: No codebase to study for implementation details.

2. **Web-Only**: Cannot be integrated as a CLI tool or library.

3. **Narrow Scope**: Currently limited to README generation (full docs "coming soon").

4. **No API Access**: No documented public API for programmatic access.

### Integration Opportunities

1. **Competitive Analysis**: When building documentation generation skills, compare output quality.

2. **Feature Parity Goals**: Target similar or better README quality with local skill.

3. **Workflow Inspiration**: "Connect repo, select, generate, export" is a smooth UX to emulate.

---

## References

| Source                         | URL                                                 | Accessed   |
| ------------------------------ | --------------------------------------------------- | ---------- |
| GitDocify Homepage             | <https://gitdocify.com>                             | 2026-01-31 |
| GitDocify Sitemap              | <https://gitdocify.com/sitemap.xml>                 | 2026-01-31 |
| Features JS Bundle (extracted) | <https://gitdocify.com/assets/Features-DLif5GYB.js> | 2026-01-31 |
| Pricing JS Bundle (extracted)  | <https://gitdocify.com/assets/Pricing-B9ZMlUbY.js>  | 2026-01-31 |
| Main JS Bundle (config)        | <https://gitdocify.com/assets/index-DPVmzviH.js>    | 2026-01-31 |

**Research Method**: Information extracted from client-side JavaScript bundles as the site is a React SPA without server-rendered content. No public documentation, GitHub repository, or press coverage was found.

---

## Freshness Tracking

| Field              | Value                                   |
| ------------------ | --------------------------------------- |
| Version Documented | Production SaaS (2026-01-31)            |
| Site Last Modified | 2025-12-06                              |
| Service Launch     | ~2025-01-16 (Supabase project creation) |
| Next Review Date   | 2026-05-01                              |

**Review Triggers**:

- Launch of "Full Documentation" feature (currently announced as "coming soon")
- Public API release
- Open-source components released
- Significant pricing changes
- Product Hunt launch or major press coverage
