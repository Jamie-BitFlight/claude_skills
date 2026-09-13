---
name: Niteni - AI-Powered Code Review for GitLab CI Pipelines
description: 'Niteni (Javanese: "to observe carefully, to pay close attention") is an AI-powered automated code review tool for GitLab CI pipelines. It uses the Google Gemini REST API to analyze merge request...'
license: MIT
metadata:
  topic: niteni
  category: developer-tools
  source_url: https://github.com/niteni
  version: "1.0.0"
  verified: "2026-02-15"
  next_review: "2026-05-15"
---

## Overview

Niteni (Javanese: "to observe carefully, to pay close attention") is an AI-powered automated code review tool for GitLab CI pipelines. It uses the Google Gemini REST API to analyze merge request diffs, produces severity-classified findings (CRITICAL, HIGH, MEDIUM, LOW), and posts them as inline diff comments on GitLab merge requests with one-click "Apply suggestion" buttons. It runs as a zero-runtime-dependency TypeScript application requiring Node.js >= 18.0.0.

---

## Problem Addressed

| Problem | Niteni Solution |
|---------|-----------------|
| Manual code reviews are slow and inconsistent, creating bottlenecks in merge request workflows | Automated AI review runs as a GitLab CI job on every `merge_request_event`, providing immediate feedback without human reviewer availability |
| Generic AI review comments lack actionable fixes and clutter MR discussions | Inline diff comments posted directly on changed lines with GitLab suggestion blocks enabling one-click "Apply suggestion" for each fix |
| Review findings lack prioritization, treating all issues equally | Severity classification (CRITICAL, HIGH, MEDIUM, LOW) with distinct visual markers enables triage by importance |
| Previous review comments become stale on re-push, cluttering the MR timeline | Automatic cleanup of previous review comments before posting new findings on re-review |
| Large diffs and irrelevant files (lock files, minified assets) waste API tokens and produce noise | Configurable file include/exclude patterns and diff size limits manage token usage and focus review on meaningful changes |
| No enforcement mechanism for critical issues discovered during review | Optional pipeline failure on CRITICAL findings (`REVIEW_FAIL_ON_CRITICAL=true`) blocks merge until addressed |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Version | 1.0.0 | 2026-02-15 |
| Node.js Requirement | >= 18.0.0 | 2026-02-15 |
| Runtime Dependencies | 0 (devDependencies only: @types/node, typescript) | 2026-02-15 |
| AI Provider | Google Gemini REST API | 2026-02-15 |
| Default Gemini Model | gemini-3-pro-preview | 2026-02-15 |
| CI Platform | GitLab CI (merge_request_event) | 2026-02-15 |
| Author | Deny Herianto | 2026-02-15 |
| Source Files | 8 TypeScript modules + 1 CI helper script | 2026-02-15 |

---

## Key Features

### Inline Diff Review

- **Inline diff comments**: Findings posted directly on changed lines in the merge request, not as generic MR notes
- **GitLab suggestion blocks**: Each finding includes a code suggestion with one-click "Apply suggestion" button for immediate fixes
- **Rationale explanations**: Each suggestion includes a description of why the change is recommended
- **Severity classification**: Findings categorized as CRITICAL, HIGH, MEDIUM, or LOW with distinct text markers

### CI Pipeline Integration

- **GitLab CI trigger**: Runs automatically on `merge_request_event` pipeline events
- **Pipeline failure control**: Optional pipeline failure on CRITICAL findings via `REVIEW_FAIL_ON_CRITICAL` environment variable
- **CI helper script**: `scripts/ci-review.sh` for simplified CI job configuration
- **Job token support**: Uses `$CI_JOB_TOKEN` by default for GitLab API authentication

### File Filtering and Limits

- **Include patterns**: `REVIEW_INCLUDE_PATTERNS` restricts review to matching files
- **Exclude patterns**: Default excludes `package-lock.json`, `yarn.lock`, `*.min.js`, `*.min.css`
- **Max files limit**: `REVIEW_MAX_FILES` caps files reviewed per MR (default: 50)
- **Diff size limit**: `REVIEW_MAX_DIFF_SIZE` caps total diff characters (default: 100,000)

### Review Lifecycle

- **Automatic cleanup**: Removes previous review comments before posting new findings on re-review
- **Simulation mode**: `simulate` mode with mock data for testing without API calls
- **Multiple modes**: `mr` (merge request review), `diff` (local diff review), `simulate` (mock data testing)

---

## Technical Architecture

<eg>
┌─────────────────────────────────────────────────────────────────┐
│                    GitLab CI Pipeline                            │
│                   (merge_request_event)                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Niteni (TypeScript)                       │  │
│  │                                                             │  │
│  │  cli.ts ──> index.ts (orchestrator)                         │  │
│  │                 │                                            │  │
│  │     ┌───────────┼────────────────┐                          │  │
│  │     │           │                │                           │  │
│  │     v           v                v                           │  │
│  │  config.ts   gitlab-api.ts   reviewer.ts                    │  │
│  │  (env vars)  (MR diffs,     (Gemini API,                    │  │
│  │              comments,       structured prompt,              │  │
│  │              suggestions)    finding extraction)             │  │
│  │                                                             │  │
│  │  types/                                                      │  │
│  │    config.ts    ── AppConfig, GitLabConfig, GeminiConfig    │  │
│  │    gitlab.ts    ── MergeRequest, MergeRequestNote           │  │
│  │    reviewer.ts  ── Severity, Finding, ReviewerOptions       │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

Data Flow:
  GitLab MR ──> Fetch Diffs ──> Filter Files ──> Gemini API
                                                      │
                                                      v
                                              Severity-Classified
                                              Findings (JSON)
                                                      │
                                                      v
                                    Post Inline Comments with Suggestions
                                    (after cleaning previous review comments)
</eg>

### Pipeline Stages

1. **Trigger**: GitLab CI job fires on `merge_request_event`
2. **Configuration**: Environment variables loaded via `config.ts` (API keys, model selection, file filters, limits)
3. **Diff Retrieval**: `gitlab-api.ts` fetches merge request diffs via GitLab REST API
4. **File Filtering**: Diffs filtered by include/exclude patterns and size limits
5. **AI Review**: `reviewer.ts` sends filtered diffs to Gemini REST API with structured prompt requesting severity-classified findings
6. **Response Parsing**: Gemini response parsed into typed `Finding` objects with severity, description, suggestion, and line mapping
7. **Comment Cleanup**: Previous Niteni review comments deleted from MR
8. **Comment Posting**: New findings posted as inline diff comments with GitLab suggestion blocks on specific changed lines

### Project Structure

<eg>
niteni/
├── src/
│   ├── types/
│   │   ├── index.ts          # Barrel export
│   │   ├── config.ts         # AppConfig, GitLabConfig, GeminiConfig, ReviewConfig
│   │   ├── gitlab.ts         # MergeRequest, MergeRequestNote, DiffPosition
│   │   └── reviewer.ts       # Severity, Finding, ReviewerOptions, FilterOptions
│   ├── index.ts              # Main module and orchestration
│   ├── cli.ts                # CLI entry point
│   ├── simulate.ts           # Simulation mode with mock data
│   ├── reviewer.ts           # Gemini review + fallback logic
│   ├── gitlab-api.ts         # GitLab API client
│   └── config.ts             # Configuration from environment variables
├── scripts/ci-review.sh      # CI helper script
├── .gitlab-ci.yml
├── tsconfig.json
└── package.json
</eg>

---

## Installation and Usage

### GitLab CI Configuration

```yaml
# .gitlab-ci.yml
stages:
  - review

ai-code-review:
  stage: review
  image: node:18
  only:
    - merge_requests
  variables:
    GEMINI_API_KEY: $GEMINI_API_KEY
    GITLAB_TOKEN: $CI_JOB_TOKEN
  script:
    - npx niteni
```

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key

# Optional (with defaults)
GITLAB_TOKEN=$CI_JOB_TOKEN          # GitLab access token
GEMINI_MODEL=gemini-3-pro-preview   # Gemini model to use
REVIEW_MAX_FILES=50                 # Max files to review
REVIEW_MAX_DIFF_SIZE=100000         # Max diff size in characters
REVIEW_INCLUDE_PATTERNS=            # File patterns to include (empty = all)
REVIEW_EXCLUDE_PATTERNS=package-lock.json,yarn.lock,*.min.js,*.min.css
REVIEW_POST_AS_NOTE=true            # Post review as MR note
REVIEW_FAIL_ON_CRITICAL=false       # Fail pipeline on CRITICAL findings
```

### Running Modes

```bash
# Merge request review (default, runs in CI)
npx niteni mr

# Local diff review
npx niteni diff

# Simulation mode (mock data, no API calls)
npx niteni simulate
```

### Building from Source

```bash
git clone https://gitlab.com/denyherianto/niteni.git
cd niteni
npm install
npm run build
```

---

## Relevance to Claude Code Development

### Applications

1. **CI-Integrated AI Review Reference Architecture**: Niteni demonstrates a complete pipeline from diff extraction through AI analysis to inline comment posting. This architecture (fetch diff, filter, prompt AI, parse structured response, post findings) is transferable to any CI platform and any AI provider.

2. **Severity Classification System**: The four-tier severity model (CRITICAL, HIGH, MEDIUM, LOW) with distinct visual markers and optional pipeline failure on CRITICAL findings provides a reusable pattern for categorizing AI-generated feedback in any code review context.

3. **GitLab Suggestion Block Integration**: The one-click "Apply suggestion" pattern demonstrates how AI review findings can be made immediately actionable rather than merely informational. This pattern reduces the friction between identifying an issue and fixing it.

### Patterns Worth Adopting

1. **Structured Prompt for Finding Extraction**: Niteni sends diffs to Gemini with a structured prompt that constrains output to severity-classified findings with specific fields (severity, description, suggestion, line number). This structured extraction pattern ensures consistent, parseable AI responses.

2. **Comment Cleanup on Re-Review**: Automatically removing previous review comments before posting new ones prevents stale finding accumulation. This pattern is essential for any system that posts AI-generated comments on iterative artifacts (PRs, MRs, documents).

3. **Configurable File Filtering**: The include/exclude pattern system with sensible defaults (excluding lock files and minified assets) demonstrates how to focus AI review on meaningful changes while managing token costs.

4. **Pipeline Failure as Enforcement**: The optional `REVIEW_FAIL_ON_CRITICAL` flag demonstrates a graduated enforcement model where AI review can be advisory (default) or blocking, allowing teams to adopt progressively.

### Integration Opportunities

1. **GitHub Actions Equivalent**: The Niteni architecture could be adapted for GitHub Actions, replacing GitLab API calls with GitHub API calls and GitLab suggestion blocks with GitHub suggested changes. The Gemini review and finding extraction layers would remain unchanged.

2. **Provider-Agnostic Review Engine**: Niteni's reviewer module could serve as a template for building a provider-agnostic review engine where Gemini, Claude, or other models provide the analysis through a common finding interface.

3. **Pre-Commit Review Hook**: The diff review mode (`niteni diff`) suggests the pattern could be adapted as a local pre-commit or pre-push hook, providing AI review feedback before code reaches CI.

### Considerations

1. **Gemini-Only**: Currently hardcoded to Google Gemini REST API. No provider abstraction layer exists for using alternative AI models. Adapting to Claude or other providers would require modifying `reviewer.ts`.

2. **GitLab-Only**: The GitLab API client (`gitlab-api.ts`) and CI integration (`.gitlab-ci.yml`) are GitLab-specific. No GitHub, Bitbucket, or other platform support exists.

3. **Zero Runtime Dependencies**: The project lists no runtime dependencies in `package.json` (only `@types/node` and `typescript` as devDependencies), meaning all HTTP calls to Gemini and GitLab APIs use Node.js built-in `fetch` (available in Node.js >= 18).

4. **Early Project**: Version 1.0.0 with a single author. The project is functional but may have limited community testing and edge case handling compared to more established review tools.

5. **Token Cost Management**: While configurable file limits and diff size caps help manage costs, there is no built-in token counting or cost estimation. Large MRs near the limits could result in significant Gemini API costs.

---

## References

1. **Niteni GitLab Repository** - <https://gitlab.com/denyherianto/niteni> (accessed 2026-02-15)
2. **Niteni GitHub Mirror** - <https://github.com/denyherianto/niteni> (accessed 2026-02-15)
3. **Niteni Source Code** - Cloned repository inspection of `src/` directory, `package.json`, `tsconfig.json`, `.gitlab-ci.yml` (accessed 2026-02-15)
4. **Google Gemini API Documentation** - <https://ai.google.dev/docs> (accessed 2026-02-15)
5. **GitLab Merge Request API** - <https://docs.gitlab.com/ee/api/merge_requests.html> (accessed 2026-02-15)
6. **GitLab Suggestion Blocks** - <https://docs.gitlab.com/ee/user/project/merge_requests/reviews/suggestions.html> (accessed 2026-02-15)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [gstack](../agent-frameworks/gstack.md) | agent-frameworks | referenced by gstack (agent-frameworks) |
| [merly-mentor](../ai-research-tools/merly-mentor.md) | ai-research-tools | referenced by merly-mentor (ai-research-tools) |
