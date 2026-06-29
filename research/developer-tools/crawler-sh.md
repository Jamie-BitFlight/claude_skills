---
title: "Crawler.sh"
research_date: "2026-03-04"
source_url: "https://crawler.sh/"
github_url: "Not publicly listed (closed-source / proprietary binary distribution)"
version_at_research: "v0.2.3"
license: "Proprietary (free tier available; premium tier with 50% off launch promotion)"
last_verified: "2026-03-04"
version_at_verification: "v0.2.3"
next_review: "2026-06-04"
---

## Overview

Crawler.sh is a local-first website crawler and SEO/AEO analysis tool available as both a CLI and a native desktop application. It crawls entire sites in seconds, runs 16 automated SEO checks per page, extracts article content as clean Markdown, and exports results as NDJSON, JSON arrays, W3C-compliant Sitemap XML, or CSV reports — all without requiring an account and without sending data to a remote server.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Cloud SEO tools require accounts, subscriptions, and send site data to third parties | Crawler.sh runs entirely on the local machine — no account required, no data leaves the device |
| Generating accurate sitemaps manually is slow and error-prone | Live crawl produces a W3C-compliant Sitemap XML reflecting actual HTTP status codes |
| Detecting SEO issues (missing titles, thin content, duplicate descriptions) across large sites is tedious | 16 automated checks run on every crawled page with CSV/TXT export |
| Extracting readable article content from web pages for pipelines or archival requires custom scraping code | Built-in content extraction converts page body to clean Markdown with word count, author, and excerpt metadata |
| Crawling is blocked by sites that reject non-browser User-Agent strings | Custom `--user-agent` flag (v0.2.3+) overrides the default `crawler.sh/0.1` identity per crawl |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| Product Hunt upvotes | 345 | 2026-03-04 |
| Product Hunt followers | 428 | 2026-03-04 |
| Product Hunt day rank | #2 | 2026-03-04 |
| Latest version | v0.2.3 | 2026-03-04 |
| Launch year | 2026 | 2026-03-04 |
| GitHub stars | Not publicly available (no public repo) | 2026-03-04 |
| npm/PyPI downloads | Not applicable (binary distribution) | 2026-03-04 |

SOURCE: [Crawler.sh on Product Hunt](https://www.producthunt.com/products/crawler-sh) (accessed 2026-03-04)

---

## Key Features

### Site Crawling

- Domain-scoped crawling: stays within the same domain, does not follow external links
- Configurable concurrency, depth limits, and polite delay between requests
- Streams results as NDJSON during crawl for real-time pipeline integration
- Custom User-Agent support via `--user-agent` CLI flag or desktop Settings card (v0.2.3+)
- Default User-Agent: `crawler.sh/0.1`

### Content Extraction

- Automatically extracts main article content from any page
- Converts extracted content to clean Markdown
- Attaches metadata per page: word count, author byline, excerpt
- Suitable for content archiving, migration pipelines, and AI ingestion workflows

### SEO / AEO Analysis

- 16 automated checks executed on every crawled page
- Detected issues include: missing titles, duplicate meta descriptions, noindex directives, thin content, long URLs, non-self canonical tags
- Also covers AEO (Answer Engine Optimization) checks for AI search engine visibility
- Export SEO report as CSV or human-readable TXT

### Output Formats

- NDJSON (streaming, one object per line) during crawl
- JSON array (full crawl export)
- Sitemap XML (W3C-compliant, generated from live crawl)
- CSV (SEO issue report)
- TXT (human-readable SEO report)
- Binary `.crawl` file format (inspectable via `info` subcommand)

### CLI Interface

Four subcommands:

1. `crawl` — crawl a website and write a `.crawl` file
2. `info` — inspect a `.crawl` file
3. `export` — convert a `.crawl` file to JSON or Sitemap XML
4. `seo` — run SEO analysis and export CSV/TXT report

### Desktop App

Eight dashboard cards:

1. Live Feed — real-time crawl progress
2. SEO Issues — summary and drill-down
3. Page Status — HTTP status code visualization
4. Settings — User-Agent, concurrency, depth, delay configuration
5. Downloads — access exported files
6. Content Viewer — browse extracted Markdown content per page
7. Newsletter — product updates
8. Premium — premium feature management

---

## Technical Architecture

Crawler.sh is a local binary (no cloud component) distributed as:

- macOS universal binary (Apple Silicon + Intel)
- Linux x86_64 and ARM64 `.deb` package
- Windows desktop app (listed as "coming soon" at research date)

The CLI is installed via a shell installer script:

```bash
curl -fsSL https://install.crawler.sh | sh
```

Crawl data is written to a proprietary `.crawl` binary file format. Exports (JSON, Sitemap XML) are generated from this file via the `export` subcommand. SEO analysis is generated from the `.crawl` file via the `seo` subcommand.

The desktop app wraps the same crawl engine in a native UI with 8 interactive dashboard cards. Settings configured in the desktop app (e.g., User-Agent) persist across sessions.

The product stack includes Loops (email), Neon (database), and Polar (payments) as noted in the Product Hunt "Built With" section — confirming the product has a SaaS backend for premium account management, though the crawling itself is local.

SOURCE: [Crawler.sh product page](https://crawler.sh/product/) (accessed 2026-03-04)
SOURCE: [Crawler.sh download page](https://crawler.sh/download/) (accessed 2026-03-04)
SOURCE: [v0.2.3 changelog](https://crawler.sh/blog/custom-user-agent/) (accessed 2026-03-04)

---

## Installation & Usage

### CLI Installation

```bash
# macOS and Linux — one-liner installer
curl -fsSL https://install.crawler.sh | sh
```

### Basic Crawl

```bash
# Crawl a website and save to .crawl file
crawler crawl https://example.com

# Crawl with concurrency and page limit
crawler crawl https://example.com --concurrency 10 --max-pages 500

# Crawl with custom User-Agent (v0.2.3+)
crawler crawl https://example.com --user-agent "Mozilla/5.0 (compatible; MyCrawler/1.0)"

# Combine flags
crawler crawl https://example.com \
  --user-agent "Mozilla/5.0" \
  --max-pages 500 \
  --concurrency 10
```

### Inspect and Export

```bash
# Inspect a .crawl file
crawler info site.crawl

# Export to JSON array
crawler export site.crawl --format json

# Export to Sitemap XML
crawler export site.crawl --format sitemap
```

### SEO Analysis

```bash
# Run SEO checks and export CSV
crawler seo site.crawl --output report.csv

# Export as human-readable TXT
crawler seo site.crawl --output report.txt
```

---

## Relevance to Claude Code Development

### Applications

- **Content ingestion pipelines**: The Markdown extraction feature makes crawler.sh a practical upstream step when building RAG pipelines or knowledge bases from documentation sites — pages come out as clean Markdown with metadata already attached
- **Documentation auditing**: Running SEO checks (missing titles, thin content, duplicate descriptions) against generated or deployed documentation sites provides automated quality signals
- **Sitemap generation for AI crawlers**: Keeping Sitemap XML current helps AI search engines (AEO) discover and index content — directly relevant when building tools that need to surface in ChatGPT/Perplexity search results

### Patterns Worth Adopting

- **Local-first tool design**: Crawler.sh's approach — no account required, no data leaves the machine — is a strong user trust pattern. Developer tools that handle potentially sensitive site data (internal docs, unreleased features) should consider this model
- **Binary `.crawl` intermediate format with separate export step**: Separating the crawl phase from the export/analysis phase allows re-running analysis without re-crawling — a sound pipeline design for expensive network operations
- **Streaming NDJSON output**: Emitting results as NDJSON during a long-running operation allows downstream consumers to start processing before the full run completes

### Integration Opportunities

- Claude Code skills that generate or maintain documentation could pipe output URLs through `crawler seo` to validate SEO hygiene automatically in CI
- The `export --format sitemap` output could be fed into a post-deploy workflow that submits the sitemap to search engines
- Markdown extraction (`content` in the crawl output) could supply a `/research-curator` agent with structured page content without needing custom scraping code

---

## References

- [Crawler.sh homepage](https://crawler.sh/) (accessed 2026-03-04)
- [Crawler.sh product page](https://crawler.sh/product/) (accessed 2026-03-04)
- [Crawler.sh download page](https://crawler.sh/download/) (accessed 2026-03-04)
- [Crawler.sh blog — v0.2.3 changelog: Custom User-Agent Support](https://crawler.sh/blog/custom-user-agent/) (accessed 2026-03-04)
- [Crawler.sh blog — Technical SEO Audit Guide](https://crawler.sh/blog/technical-seo-audits/) (accessed 2026-03-04)
- [Crawler.sh on Product Hunt](https://www.producthunt.com/products/crawler-sh) (accessed 2026-03-04)

---
