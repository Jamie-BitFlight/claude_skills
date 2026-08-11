---
name: scrapling-skill
research_date: 2026-03-13
source_url: https://github.com/Cedriccmh/claude-code-skill-scrapling
github_repository: https://github.com/Cedriccmh/claude-code-skill-scrapling
upstream_library: https://github.com/D4Vinci/Scrapling
version_at_research: commit 65bcdc7
license: MIT
freshness_tracking:
  last_verified: 2026-03-13
  version_at_verification: commit 65bcdc7
  next_review: 2026-06-13
  confidence_map: "Overview: high, Problem Addressed: high, Features: high, Architecture: high, Installation: high, Relevance: high, References: high"
---

# Scrapling Skill for Claude Code

## Overview

Scrapling Skill is a Claude Code community skill that wraps the Scrapling Python library to provide intelligent web scraping and HTML data extraction capabilities. It implements an automated decision tree to select optimal Fetcher strategies (curl_cffi, Playwright, Camoufox, or pure parsing) based on target website characteristics, then generates and executes parameterized Python scripts for scraping. The skill supports static pages, Cloudflare-protected sites, form-based login sessions, JavaScript-rendered SPAs, and pure HTML parsing, with built-in site pattern library, cookie vault templates, and comprehensive troubleshooting guides. (SOURCE: <https://github.com/Cedriccmh/claude-code-skill-scrapling> README, accessed 2026-03-13)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual Fetcher selection requires deep knowledge of anti-scraping techniques | Automated decision tree guides selection based on site characteristics (static vs JS-rendered, authentication, Cloudflare protection) |
| Cloudflare WAF blocks standard HTTP requests | StealthyFetcher with automatic Cloudflare challenge solving via Camoufox headless browser |
| Cookie management across login sessions is error-prone | FetcherSession with automatic cookie persistence, Cookie Vault template for secure local storage |
| JavaScript-rendered SPA content requires browser automation | DynamicFetcher with Playwright, DOM interaction support, wait_selector parameter for critical UI elements |
| Error messages are cryptic and resolution path is unclear | Comprehensive troubleshooting guide indexed by exact error message with working solutions |
| Successful scraping patterns are lost and must be re-solved | Site pattern library mechanism enables experience accumulation after successful scrapes (SOURCE: SKILL.md 步骤 2 / Step 2, item 6 "沉淀经验（必做）" — accumulate experience, mandatory; verified at commit 65bcdc7 on 2026-08-11) |

---

## Identity and Metadata

**Resource Name**: Scrapling — Claude Code Web Scraping Skill

**Version**: Latest (commit 65bcdc7, bilingual content release)

**Repository**: <https://github.com/Cedriccmh/claude-code-skill-scrapling>

**License**: MIT

**Language**: Python 3

**Type**: Claude Code Skill — installable via `.claude/skills/` directory

**Author**: Cedriccmh

**Bilingual Support**: English + Chinese (中文)

---

## Summary

A Claude Code skill that wraps the [Scrapling](https://github.com/D4Vinci/Scrapling) Python library for web scraping and HTML data extraction. The skill provides an intelligent decision tree for selecting the optimal "Fetcher" (HTTP client) based on target website characteristics, then generates and executes parameterized Python scripts for scraping.

Supports static pages, Cloudflare-protected sites, form-based login sessions, JavaScript-rendered SPAs, and pure HTML parsing. Includes curated site patterns, cookie vault templates, troubleshooting guides, and API reference documentation.

---

## Key Features

### Fetcher Decision Tree — Automatic Selection

The skill guides Claude to select the best fetching strategy based on target website properties:

- **Selector** — Pure HTML parsing (no network request). Used when HTML string or file is already available. SOURCE: SKILL.md Step 1 (accessed 2026-03-13)

- **Fetcher** — Static pages without JavaScript rendering or anti-scraping protection. Based on `curl_cffi` for speed. SOURCE: SKILL.md Step 1, api-quick-ref.md (accessed 2026-03-13)

- **FetcherSession** — HTTP form-based login with session cookie persistence. Maintains session state across multiple requests within a context manager. SOURCE: SKILL.md Step 1, session_login.py template (accessed 2026-03-13)

- **StealthyFetcher** — Cloudflare/WAF-protected sites. Uses Camoufox (headless browser) with automatic Cloudflare challenge solving. Key parameter: `solve_cloudflare=True`. Timeout in milliseconds (e.g., 60000ms minimum). SOURCE: SKILL.md Step 1, stealth_cloudflare.py template, api-quick-ref.md (accessed 2026-03-13)

- **DynamicFetcher** — SPA applications (React/Vue/Next.js) requiring JavaScript rendering. Uses Playwright browser. Supports `wait_selector` parameter to wait for specific DOM elements before parsing. SOURCE: SKILL.md Step 1, site-patterns.md "SPA 应用" section (accessed 2026-03-13)

**Mechanism**: The decision tree is a sequential branching flowchart in SKILL.md Step 1 that examines target characteristics (HTML already present, static vs dynamic, login required, Cloudflare present, SPA detection). Each branch routes to a specific Fetcher class and corresponding template file.

### Cloudflare Bypass — Built-In

StealthyFetcher provides automatic Cloudflare protection bypass without requiring manual `cf_clearance` cookie extraction. Key mechanism:

- Internally uses Camoufox (headless browser rendering)
- Sets `solve_cloudflare=True` parameter
- Handles multi-round Turnstile verification automatically
- Certificate and TLS fingerprinting are handled by the browser environment
- Users should NOT manually pass `cf_clearance` cookies (they are browser-fingerprint-bound and non-transferable)

SOURCE: troubleshooting.md "Cloudflare 403 + Just a moment" section and "cf_clearance cookie 无效" section (accessed 2026-03-13)

### Site Pattern Library — Reusable Patterns

`references/site-patterns.md` documents proven scraping patterns for common site types:

**Discourse Forums** (linux.do, meta.discourse.org):
- Fetcher: StealthyFetcher with `solve_cloudflare=True`, `network_idle=True`, timeout 60000ms
- Key cookies: `_forum_session`, `_t` (do not include `cf_clearance`)
- CSS selectors: `.topic-post` for posts, `[data-user-card]::attr(data-user-card)` for author, `.cooked` with `.get_all_text(strip=True)` for content
- SOURCE: site-patterns.md "Discourse 论坛" section (accessed 2026-03-13)

**Static Blogs/Docs** (GitHub Pages, Hugo, Jekyll):
- Fetcher: Basic Fetcher with `impersonate='chrome'`, timeout 30 seconds
- No special selectors required
- SOURCE: site-patterns.md "静态博客/文档站" section (accessed 2026-03-13)

**SPA Applications**:
- Fetcher: DynamicFetcher with `network_idle=True`, `wait_selector` for critical UI elements, `disable_resources=True`
- Note: Check for API endpoints first (more stable than rendering)
- SOURCE: site-patterns.md "SPA 应用" section (accessed 2026-03-13)

**TAPD Project Management** (tapd.cn):
- Limitation: Scrapling Fetchers insufficient for CSRF-protected API
- Documented workaround: Use Playwright directly with `networkidle` wait and click() for "show more" button interaction
- SOURCE: site-patterns.md "TAPD 项目管理" section (accessed 2026-03-13)

**Template Mechanism**: Pattern docs include repeatable sections with site characteristics, recommended Fetcher, key parameters, CSS selector examples, and notes. Users and Claude can append new patterns as learning accumulates.

### Session Login — HTTP Form-Based

FetcherSession template enables login workflows with automatic cookie persistence:

```python
with FetcherSession(impersonate='chrome') as s:
    login_resp = s.post(LOGIN_URL, data=LOGIN_DATA)
    for url in TARGET_URLS:
        page = s.get(url)  # Cookies from login automatically sent
```

Parameters: LOGIN_DATA dict accepts form fields (e.g., `{'username': '...', 'password': '...'}`). Session maintains cookies across requests within the context manager scope.

Limitation: Does not support JavaScript-based login forms. For JS login, use DynamicFetcher with Playwright.

SOURCE: templates/session_login.py (accessed 2026-03-13)

### Cookie Vault — Secure Local Storage Template

`references/cookie-vault.md` provides a template for storing login cookies with per-site organization:

- Format: Markdown table with site name, cookie dict or list[dict], extraction method
- Instruction: Copy to `cookie-vault.local.md` in local skill installation (never commit real cookies to version control)
- Security: Template is read-only; users fill in actual values from browser DevTools
- Usage: Claude references vault when FetcherSession or StealthyFetcher needs pre-existing authentication

SOURCE: README.md "Cookie Vault" section, SKILL.md Step 2 "沉淀经验" (accessed 2026-03-13)

### Troubleshooting Guide — Error-Indexed Solutions

`references/troubleshooting.md` indexes solutions by error message:

- `ModuleNotFoundError: curl_cffi` — Solution: `pip install "scrapling[fetchers]"`
- Cloudflare 403 "Just a moment" — Solution: Use StealthyFetcher with `solve_cloudflare=True`
- `Expected array, got object at $.cookies` — Solution: Browser Fetchers require `list[dict]` format, not `dict`
- `Cookie should have a url or a domain/path pair` — Solution: Each cookie dict must include `domain` (with leading `.`) and `path` (usually `/`)
- Cloudflare Turnstile multi-round verification — Solution: Increase timeout to 120000ms if 60000ms insufficient
- `scrapling: command not found` — Solution: Use `python -c "from scrapling.cli import main; main(['install'])"` to avoid PATH issues

SOURCE: references/troubleshooting.md (accessed 2026-03-13)

---

## Technical Architecture

### Workflow Architecture

The skill implements a 6-step workflow in SKILL.md Step 2:

1. **Version Check** — Verify scrapling installation; install `pip install "scrapling[fetchers]"` if missing; note changelog on upgrades
2. **Site Pattern Lookup** — Query `references/site-patterns.md` for matching site type (Discourse, SPA, static blog, etc.); reuse pattern if found
3. **Fetcher Selection** — If no pattern match, apply decision tree from Step 1 to select Fetcher
4. **Template Parameterization** — Read corresponding template file (`basic_fetch.py`, `stealth_cloudflare.py`, `session_login.py`, `parse_only.py`); substitute parameters (URL, CSS_SELECTOR, COOKIES, LOGIN_DATA)
5. **Execution** — Run generated script, capture output
6. **Experience Accumulation** — After successful scrape, check whether new site pattern or cookie should be saved to vault

SOURCE: SKILL.md Step 2 (accessed 2026-03-13)

### Data Flow

```
User request (scrape URL / extract data)
    ↓
SKILL.md Step 0: Check version → install if needed
    ↓
SKILL.md Step 1: Apply decision tree → select Fetcher
    ↓
Load template (basic_fetch.py / stealth_cloudflare.py / session_login.py / parse_only.py)
    ↓
Parameterize: replace {{URL}}, {{CSS_SELECTOR}}, {{COOKIES}}, etc.
    ↓
Execute script → scrapling library → network or local HTML
    ↓
Parse response (page.css(), page.xpath(), page.re(), page.text)
    ↓
Return extracted results + status code
    ↓
(Optional) Update site-patterns.md or cookie-vault.md
```

### Fetcher Classification

**Non-Browser Fetchers** (Fast, stateless):
- Fetcher (curl_cffi) — Uses HTTP client with Chrome user-agent impersonation
- FetcherSession (curl_cffi session) — Stateful HTTP client; persists cookies across requests
- Selector (Parso/lxml) — Pure parser; no network request

**Browser Fetchers** (Slower, JS-capable, anti-scraping-resistant):
- StealthyFetcher (Camoufox) — Headless browser with anti-detection optimizations; solves Cloudflare challenges
- DynamicFetcher (Playwright) — Headless browser for JS rendering; supports waiting and DOM interaction

Cookie Format Distinction:
- Non-browser: `dict` format — `{'name': 'value'}`
- Browser: `list[dict]` format — `[{'name': 'n', 'value': 'v', 'domain': '.site.com', 'path': '/'}]`

Timeout Unit Distinction:
- Non-browser: seconds — `timeout=30`
- Browser: milliseconds — `timeout=60000`

SOURCE: api-quick-ref.md, SKILL.md "Cookie 格式速查" and "超时单位速查" sections (accessed 2026-03-13)

---

## Installation & Usage

### Installation Steps

1. **Install scrapling library**:

   ```bash
   pip install "scrapling[fetchers]"
   scrapling install  # Install browser dependencies (Camoufox, Playwright)
   ```

2. **Install skill to Claude Code**:

   ```bash
   # User-level (available in all projects)
   cp -r . ~/.claude/skills/scrapling

   # Or project-level
   cp -r . /path/to/project/.claude/skills/scrapling
   ```

3. **Verify installation**:
   - Check: `pip show scrapling`
   - Verify Fetcher: `python -c "from scrapling.fetchers import Fetcher; print('OK')"`
   - Verify StealthyFetcher: `python -c "from scrapling.fetchers import StealthyFetcher; print('OK')"`
   - Verify DynamicFetcher: `python -c "from scrapling.fetchers import DynamicFetcher; print('OK')"`

SOURCE: README.md "Installation" section, references/maintenance.md (accessed 2026-03-13)

### Activation Triggers

Claude Code automatically activates the skill when requests match:
1. Scrape or crawl a website
2. Extract data from a URL
3. Bypass Cloudflare protection
4. Parse HTML content
5. Login and scrape protected pages
6. Batch collect multiple pages

Activation criteria configured in SKILL.md frontmatter: `allowed-tools: Bash(python*), Bash(pip*), Bash(scrapling*)`

SOURCE: SKILL.md frontmatter, README.md "Usage" section (accessed 2026-03-13)

---

## Usage Examples

### Example 1: Static Blog Post Extraction

**Request**: "Scrape the title and content from <https://example.com/blog>"

**Workflow**:
1. Decision tree → static page, no JS → use Fetcher
2. Load `templates/basic_fetch.py`
3. Parameterize: URL="<https://example.com/blog>", CSS_SELECTOR="article h1::text"
4. Execute:

   ```python
   from scrapling.fetchers import Fetcher
   page = Fetcher.get("https://example.com/blog", impersonate='chrome', timeout=30)
   results = page.css('article h1::text').getall()
   ```

### Example 2: Cloudflare-Protected Site

**Request**: "This site has Cloudflare, scrape it anyway: <https://protected.example.com>"

**Workflow**:
1. Decision tree → Cloudflare detected → use StealthyFetcher
2. Load `templates/stealth_cloudflare.py`
3. Parameterize: URL="<https://protected.example.com>", CSS_SELECTOR=None, COOKIES=None
4. Execute:

   ```python
   from scrapling.fetchers import StealthyFetcher
   page = StealthyFetcher.fetch(
       "https://protected.example.com",
       headless=True,
       solve_cloudflare=True,
       timeout=60000,
       network_idle=True
   )
   ```

### Example 3: Login + Multi-Page Scraping

**Request**: "Login to <https://mysite.com> and scrape these pages: /page1, /page2"

**Workflow**:
1. Decision tree → needs login (HTTP form) → use FetcherSession
2. Load `templates/session_login.py`
3. Parameterize: LOGIN_URL, LOGIN_DATA, TARGET_URLS
4. Execute:

   ```python
   from scrapling.fetchers import FetcherSession
   with FetcherSession(impersonate='chrome') as s:
       s.post(LOGIN_URL, data={'username': '...', 'password': '...'})
       for url in TARGET_URLS:
           page = s.get(url)
   ```

### Example 4: Pure HTML Parsing

**Request**: "I have this HTML, extract all links from it"

**Workflow**:
1. Decision tree → HTML already present, no network → use Selector
2. Load `templates/parse_only.py`
3. Parameterize: Selector(html_string)
4. Execute:

   ```python
   from scrapling.parser import Selector
   page = Selector(html_string)
   links = page.css('a::attr(href)').getall()
   ```

SOURCE: README.md "Examples" and all templates (accessed 2026-03-13)

---

## Limitations and Caveats

### No JavaScript Login Support

FetcherSession and basic Fetcher cannot execute JavaScript login forms (e.g., OAuth, SAML, JS-driven form submission). Workaround: Use DynamicFetcher with Playwright to render and interact with JS-based login.

SOURCE: SKILL.md Step 1 note on FetcherSession, site-patterns.md TAPD example (accessed 2026-03-13)

### cf_clearance Cookies Are Non-Transferable

The `cf_clearance` cookie is bound to browser fingerprint (TLS/JA3/User-Agent) and cannot be manually extracted and reused across different HTTP clients. StealthyFetcher obtains its own `cf_clearance` internally; users should not attempt to pass it.

SOURCE: troubleshooting.md "cf_clearance cookie 无效" section (accessed 2026-03-13)

### Browser Dependency Overhead

StealthyFetcher and DynamicFetcher require browser engines (Camoufox and Playwright) to be installed via `scrapling install`. First-time setup adds 200-500MB. Subsequent requests incur startup latency (3-10 seconds) even for simple pages.

SOURCE: references/maintenance.md "安装浏览器依赖" section (accessed 2026-03-13)

### Cookie Format Strictness

Browser Fetchers (StealthyFetcher, DynamicFetcher) require cookies as `list[dict]` with mandatory fields `name`, `value`, `domain` (with leading `.`), and `path`. Malformed cookies raise validation errors. Non-browser Fetchers use simpler `dict` format.

SOURCE: SKILL.md "Cookie 格式速查", troubleshooting.md "Expected array, got object" and "Cookie should have a url" sections (accessed 2026-03-13)

### Timeout Unit Inconsistency

Non-browser Fetchers use seconds; browser Fetchers use milliseconds. Confusion leads to undersized timeouts (e.g., passing 30 instead of 30000 for browser, causing instant timeout).

SOURCE: SKILL.md "超时单位速查" section (accessed 2026-03-13)

### TAPD Site Pattern — Scrapling Insufficient

The TAPD project management site (tapd.cn) is documented as requiring direct Playwright control rather than scrapling Fetchers, due to CSRF-protected API endpoints and click-based pagination. Scrapling Fetchers return empty responses for internal APIs.

SOURCE: site-patterns.md "TAPD 项目管理" section (accessed 2026-03-13)

### No Documentation for POST/JSON Requests

The API quick reference shows `Fetcher.post()` and `DynamicFetcher` exists but lacks detailed examples for JSON request bodies or handling JSON responses. Users must infer from Fetcher.post(json=...) signature.

SOURCE: api-quick-ref.md (not documented in templates or examples) (accessed 2026-03-13)

---

## Relevance to Claude Code Development

### Direct Integration Point

This skill is designed as a Claude Code community skill for the Claude Code Marketplace. It demonstrates:

- Skill activation triggers based on semantic intent matching (user says "scrape" → skill loads)
- Reference material organization (templates, patterns, vault, troubleshooting guide)
- Bilingual documentation (English + Chinese) for international users
- Parameterized code generation workflow (decision tree → template → substitution → execution)

### Use Cases in Claude Skills Repository

- **Web Research Agents**: When agents need to fetch and parse web content for information gathering
- **Data Extraction Workflows**: Multi-step scraping with session management (login → navigate → extract)
- **Cloudflare-Protected Documentation**: Scraping docs sites behind WAF protection
- **HTML-to-Structured Data**: Converting web pages to JSON/CSV output

### Maintenance Discipline

The skill demonstrates experience accumulation practices:
- Site patterns saved after successful scrapes (avoid re-solving same problem)
- Cookie vault for login credentials (avoid repeated login requests)
- Troubleshooting index keyed by error message (self-serve debugging)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [jina-reader.md](../developer-tools/jina-reader.md) | developer-tools | alternative URL-to-Markdown extraction (Jina Reader via r.jina.ai API vs. Scrapling Fetchers) |
| [browsermcp-mcp.md](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | browser automation MCP server — complementary to Scrapling's browser Fetchers (StealthyFetcher, DynamicFetcher) |
| [claude-quickstarts.md](../developer-tools/claude-quickstarts.md) | developer-tools | browser automation reference — Anthropic's minimal agent loop shows integration patterns for web scraping workflows |
| [surf-cli.md](../developer-tools/surf-cli.md) | developer-tools | zero-config AI agent Chrome control via accessibility tree (alternative to Scrapling for page-reading; complementary for structured extraction) |
| [kernel-sh.md](../agent-infrastructure/kernel-sh.md) | agent-infrastructure | browsers-as-a-service infrastructure — enables Scrapling-like jobs at scale via VM-per-browser isolation and MCP |
| [tinyfish.md](../agent-infrastructure/tinyfish.md) | agent-infrastructure | serverless web agent API — orchestrates parallel Scrapling-like operations (1,000 concurrent scrapes, AgentQL MCP alternative) |
| [tabz-browser-console-forwarder.md](../developer-tools/tabz-browser-console-forwarder.md) | developer-tools | browser debugging in tmux — useful for debugging Scrapling DynamicFetcher/StealthyFetcher console errors during scraping |
| [everything-claude-code.md](../skill-generation-tools/everything-claude-code.md) | skill-generation-tools | comprehensive skill ecosystem (65+ skills) — Scrapling-skill would integrate as web-scraping specialist within this agent harness |
| [fastapi.md](../api-frameworks/fastapi.md) | api-frameworks | Python web framework — pairs with Scrapling for building scraper-backed APIs (fetch data via Scrapling, serve via FastAPI) |
| [jina-ai.md](../context-management/jina-ai.md) | context-management | search foundation platform with Reader API — overlaps with Scrapling's URL extraction; Jina is emerging standard vs. Scrapling's library-based approach |

---

## Freshness Tracking

**Entry Created**: 2026-03-13

**Next Review**: 2026-06-13 (3 months)

**Repository Status**: Active (latest commit 2026-03-13, bilingual content update)

### Confidence Map

- **Identity/Metadata**: high — Repository contains explicit license (MIT), frontmatter with bilingual flags, git commit history
- **Features**: high — Each feature section directly quoted or closely paraphrased from README.md, SKILL.md, templates, and reference files
- **Architecture**: high — Workflow documented explicitly in SKILL.md Step 0-2; data flow synthesized from template structure
- **Installation/Setup**: high — Installation and activation requirements extracted from README.md and SKILL.md frontmatter
- **Usage Examples**: high — Examples adapted from README.md examples section; templates show exact Python syntax
- **Limitations**: high — Limitations sourced from troubleshooting.md and site-patterns.md documented caveats; dependency requirements from maintenance.md
- **Relevance**: medium — Inferred from skill classification (web scraping, developer tools); relevance to Claude Code ecosystem is stated but not quantified

### Sources Accessed

- README.md (English + Chinese bilingual)
- SKILL.md (activation triggers, workflow steps, decision tree, templates, references index)
- templates/basic_fetch.py, stealth_cloudflare.py, session_login.py, parse_only.py
- references/api-quick-ref.md (Fetcher API methods, cookie formats, timeout units)
- references/site-patterns.md (Discourse, static blogs, SPA, TAPD patterns)
- references/troubleshooting.md (error-indexed solutions, cookie format errors, timeout issues)
- references/maintenance.md (installation tiers, browser dependency, verification commands)
- LICENSE (MIT confirmation)
- git log (commit history, repository URL)

---

## References

- [claude-code-skill-scrapling GitHub Repository](https://github.com/Cedriccmh/claude-code-skill-scrapling) — Official source (accessed 2026-03-13)
- [Scrapling Library](https://github.com/D4Vinci/Scrapling) — Upstream web scraping library documentation
- [Claude Code Official Documentation](https://docs.anthropic.com/en/docs/claude-code) — Skill activation and marketplace integration
