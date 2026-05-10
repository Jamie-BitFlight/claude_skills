---
title: Internal-Comms Skill
subtitle: Standardized internal company communication templates for six message types via Composio CLI
category: task-management
resource_url: https://github.com/ComposioHQ/awesome-codex-skills/tree/master/internal-comms
github_url: https://github.com/ComposioHQ/awesome-codex-skills
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

# Internal-Comms Skill

**Resource**: Internal Communications Skill Module
**Repository**: [ComposioHQ/awesome-codex-skills/internal-comms](https://github.com/ComposioHQ/awesome-codex-skills/tree/master/internal-comms)
**License**: Apache License 2.0
**Latest Update**: 2026-05-07

## Overview

Internal-comms is a modular Codex skill that provides standardized formats and workflows for writing internal company communications. It helps users compose professional internal messages in company-preferred formats by directing them to specific guideline templates matched to the communication type. The skill covers six primary communication categories: 3P updates (Progress/Plans/Problems), company newsletters, frequently asked question compilations, status reports, leadership updates, project updates, and incident reports.

SOURCE: "A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use" ([SKILL.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/SKILL.md) line 3, accessed 2026-05-10).

## Problem Addressed

Internal communications are critical for organizational alignment but lack standardization across different communication types. Teams and individuals write status updates, leadership summaries, and newsletters with inconsistent formats, tones, and content structures, leading to unclear messaging and inefficient information consumption. Internal-comms solves this by providing Claude-powered guidance to standardize how organizations communicate internally, ensuring executives, team members, and the broader company body receive information in formats tailored to their needs and reading time constraints.

## Key Statistics

- **4 communication guideline templates** provided in the `examples/` directory
- **Three-section structure** for 3P updates: Progress, Plans, Problems (each 1-3 sentences)
- **20-25 bullet points** recommended for company-wide newsletter updates
- **30-60 seconds reading time** target for 3P updates
- **One skill module** containing reusable, composable guidance for multiple communication scenarios

All metrics extracted from primary source documentation.

## Key Features

### 1. **3P Updates (Progress, Plans, Problems)**

"3P updates stand for 'Progress, Plans, Problems.' The main audience is for executives, leadership, other teammates, etc. They're meant to be very succinct and to-the-point: think something you can read in 30-60sec or less."

Structure: Each section contains 1-3 sentences of data-driven content. Progress focuses on shipped features, milestones, and completed tasks. Plans highlight top-priority work for the next week. Problems surface blockers and team challenges.

Format: `[emoji] [Team Name] (Dates) / Progress: [content] / Plans: [content] / Problems: [content]`

SOURCE: [3p-updates.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/3p-updates.md) lines 2-2, 6-9, 40-46 (accessed 2026-05-10).

### 2. **Company-Wide Newsletters**

"You are being asked to write a company-wide newsletter update. You are meant to summarize the past week/month of a company in the form of a newsletter that the entire company will read. It should be maybe ~20-25 bullet points long."

Features:
- Organized into 5-7 thematic sections (e.g., Product Development, Go-to-Market, Finance)
- Uses "we" voice and emphasizes company-wide impact
- Integrates links to Slack announcements, Google Drive documents, email threads
- Prioritizes announcements from leadership, major milestones, and external press recognition
- Each bullet point kept to 1-2 sentences for scannability

SOURCE: [company-newsletter.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/company-newsletter.md) lines 2-2, 21, 24-34 (accessed 2026-05-10).

### 3. **FAQ Compilation**

"Your job is to do two things: Find questions that are big sources of confusion for lots of employees at the company...Attempt to give a nice summarized answer to that question in order to minimize confusion."

Format: Question-and-answer pairs where each question is 1 sentence and each answer is 1-2 sentences.

Data sources: Slack threads with high response counts, company-wide emails, Google Drive documents, and Calendar event attendee lists. Answers grounded in official company communications when possible, with links to authoritative sources.

SOURCE: [faq-answers.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/faq-answers.md) lines 2-5, 11-15, 25-30 (accessed 2026-05-10).

### 4. **General Communications**

"You are being asked to write internal company communication that doesn't fit into the standard formats (3P updates, newsletters, or FAQs)."

Provides a flexible workflow for non-standard internal communications (incident reports, ad-hoc announcements, directional memos) by gathering information about audience, purpose, tone, and formatting requirements before composing.

SOURCE: [general-comms.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/general-comms.md) lines 1-4 (accessed 2026-05-10).

## Technical Architecture

### Data Flow

1. **Trigger**: User requests internal communication writing (e.g., "write a 3P update for the engineering team").
2. **Classification**: Skill identifies communication type from user request.
3. **Template Loading**: Loads appropriate guideline file from `examples/` directory:
   - `examples/3p-updates.md` → Progress/Plans/Problems structured updates
   - `examples/company-newsletter.md` → Broad, cross-team newsletter summaries
   - `examples/faq-answers.md` → Consolidated frequently asked questions
   - `examples/general-comms.md` → Fallback for non-standard formats
4. **Information Gathering**: User provides or skill helps gather context from:
   - Team member updates (Slack posts)
   - Leadership communications (emails, documents)
   - Calendar events and meeting notes
   - Google Drive documents with visibility/attention indicators
5. **Composition**: Skill guides Claude to compose the communication following the guideline's formatting, tone, and structural requirements.
6. **Output**: Formatted internal communication ready for distribution.

### Extension Points

The skill architecture supports addition of new communication types via new guideline files in `examples/`. Each guideline file declares:
- **Instructions**: What the communication is and its primary audience
- **Tools Available**: Data sources to pull from (Slack, Email, Calendar, Documents)
- **Workflow**: Steps for gathering and composing content
- **Formatting**: Exact formatting rules to follow (strict, with examples)

No code changes needed — users or contributors can add new `examples/{new-type}.md` files to support additional communication formats.

SOURCE: [SKILL.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/SKILL.md) lines 21-29 (accessed 2026-05-10).

## Installation & Usage

### Installation

```bash
# Via Skill Installer (Composio)
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo ComposioHQ/awesome-codex-skills \
  --path internal-comms \
  --name internal-comms
```

or

### Manual Installation

1. Clone or download the [awesome-codex-skills](https://github.com/ComposioHQ/awesome-codex-skills) repository.
2. Copy the `internal-comms/` directory into `$CODEX_HOME/skills/` (typically `~/.codex/skills/`).
3. Restart Codex to load the new skill metadata.

### Usage Example

**User Request:**
```
Write a 3P update for the Platform team covering the week of May 3-9.
Progress: shipped async task queuing, fixed 3 critical bugs.
Plans: complete migration to new CDN, start performance benchmarking.
Problems: understaffed due to PTO, dependency on Design team for API specs.
```

**Skill Workflow:**
1. Identifies communication type as "3P update"
2. Loads `examples/3p-updates.md` guidelines
3. Formats content into strict structure: `[emoji] Platform (May 3-9) / Progress: ... / Plans: ... / Problems: ...`
4. Outputs formatted update ready to paste into Slack or email

SOURCE: [SKILL.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/SKILL.md) lines 19-29; [3p-updates.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/3p-updates.md) lines 30-46 (accessed 2026-05-10).

## Relevance to Claude Code Development

Internal-comms is directly relevant for team coordination and status tracking within agent-centric development workflows. When using AI agents or multi-person teams to implement features, creating structured status updates ensures clear handoffs, maintains alignment on blockers, and provides executives with concise summaries for decision-making.

**Use cases in agent-driven development:**

1. **Agent Status Reporting**: Each completed SAM (Structured Agent-Managed) task produces a 3P-formatted status update summarizing agent progress, planned next steps, and any blockers encountered.

2. **Milestone/Sprint Summaries**: Weekly company or team newsletters aggregating achievements across multiple parallel agent runs, with links to merged PRs and closed issues.

3. **Incident Communication**: When agent-driven CI failures occur, internal-comms provides a template for summarizing the incident, root cause, remediation, and prevention steps for the broader team.

4. **Cross-team Visibility**: For distributed teams coordinating on platform improvements or shared tooling, newsletters maintain visibility of progress across team boundaries without requiring separate sync meetings.

## Limitations and Caveats

### Documented Limitations

1. **Format Rigidity**: 3P update format is intentionally strict (`[emoji] [Team Name] (Dates) / Progress: ... / Plans: ... / Problems: ...`). The skill enforces this format without flexibility for teams preferring alternative structures.

2. **Data Source Dependence**: Newsletter and FAQ compilation depend on having access to Slack, Email, Calendar, and Google Drive. Organizations without these tools or with different communication platforms (Microsoft Teams, Discord, etc.) would need to manually provide information or have the skill adapted.

3. **No Audience Segmentation**: Templates assume a single audience per communication type (executives for 3Ps, entire company for newsletters). Generating segmented versions for different organizational levels requires separate skill invocations.

4. **Context Window Constraints**: For large organizations with extensive weekly activity, summarizing 20-25 newsletter items within a tight context window may lose important details or require iterative refinement.

SOURCE: [3p-updates.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/3p-updates.md) lines 40, 29-34 (accessed 2026-05-10). [company-newsletter.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/company-newsletter.md) lines 9-17 (accessed 2026-05-10).

## References

- **GitHub Repository**: [ComposioHQ/awesome-codex-skills/internal-comms](https://github.com/ComposioHQ/awesome-codex-skills/tree/master/internal-comms)
- **Skill Metadata File**: [SKILL.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/SKILL.md) (accessed 2026-05-10)
- **3P Updates Guideline**: [examples/3p-updates.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/3p-updates.md) (accessed 2026-05-10)
- **Company Newsletter Guideline**: [examples/company-newsletter.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/company-newsletter.md) (accessed 2026-05-10)
- **FAQ Answers Guideline**: [examples/faq-answers.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/faq-answers.md) (accessed 2026-05-10)
- **General Communications Guideline**: [examples/general-comms.md](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/examples/general-comms.md) (accessed 2026-05-10)
- **License**: [LICENSE.txt](https://github.com/ComposioHQ/awesome-codex-skills/blob/master/internal-comms/LICENSE.txt) — Apache License 2.0 (accessed 2026-05-10)
- **Parent Repository**: [ComposioHQ/awesome-codex-skills](https://github.com/ComposioHQ/awesome-codex-skills) — "A curated list of practical Codex skills for automating workflows" (accessed 2026-05-10)

## Freshness Tracking

| Section | Confidence | Last Verified | Next Review |
|---------|-----------|---------------|-------------|
| Identity/Metadata | high | 2026-05-10 | 2026-08-10 |
| Overview | high | 2026-05-10 | 2026-08-10 |
| Key Features | high | 2026-05-10 | 2026-08-10 |
| Technical Architecture | high | 2026-05-10 | 2026-08-10 |
| Installation & Usage | high | 2026-05-10 | 2026-08-10 |
| Limitations | medium | 2026-05-10 | 2026-08-10 |
| Relevance to Claude Code | high | 2026-05-10 | 2026-08-10 |

**Confidence Rationale**:
- **High**: All sections drawn from official source files (SKILL.md, guidelines) in the published repository. Direct file reads (not inferred). Recent repository commit (2026-05-07).
- **Medium** (Limitations): Limitations documented in guidelines; no explicit "known issues" section in SKILL.md. Confidence reduced slightly for gap between documented vs. undiscovered limitations.

**Review Cycle**: 3 months. Internal-comms is a stable skill module unlikely to undergo breaking changes. Recheck if Codex skill architecture evolves or if the parent `awesome-codex-skills` repository introduces new communication types or changes template formats.
