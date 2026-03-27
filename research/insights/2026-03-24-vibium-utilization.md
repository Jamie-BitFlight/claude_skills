# Utilization Proposals: vibium

**Research entry**: ./research/agent-infrastructure/vibium.md
**Generated**: 2026-03-24
**Integration surfaces found**: 4 (CLI binary + MCP server + Python SDK + JavaScript SDK)
**Proposals written**: 1
**Skipped**: 1 — alternative implementation, not new capability

---

## Utilization 1: agent-browser skill → Vibium as standards-based alternative backend

**Research entry**: ./research/agent-infrastructure/vibium.md
**Caller**: ./.claude/skills/agent-browser/SKILL.md
**Integration mechanism**: CLI subprocess (`vibium` binary via bash) or Python SDK (`pip install vibium`)
**Replaces or adds**: Replaces Playwright-based browser automation with WebDriver BiDi (standards-based alternative). Maintains CLI and SDK interfaces but switches underlying protocol from proprietary CDP/Playwright to W3C-standardized BiDi.
**Setup cost**: Medium (API shape is similar but differs in element reference format; session management differs; requires testing against existing workflows)
**Integration surface**: CLI commands (`vibium go`, `vibium map`, `vibium click @e1`, `vibium screenshot`, etc.) and Python SDK (`from vibium import browser; vibe = await browser.start(); await vibe.go(url)`)

### Why this caller

The agent-browser skill (`.claude/skills/agent-browser/SKILL.md`) currently provides browser automation to AI agents using Playwright. It handles navigation, element finding, form filling, screenshots, and session persistence. The skill's purpose and workflow are fully compatible with Vibium's API surface.

According to the research entry, Vibium addresses key pain points with Playwright:

1. **Protocol lock-in**: Playwright is controlled by Microsoft and uses proprietary CDP. Vibium uses WebDriver BiDi, a W3C standard not controlled by any single vendor.
2. **Semantic element finding**: Vibium's `find text`, `find label`, `find role` commands match agent-browser's semantic locator approach. Element references (`@e1`, `@e2`) work similarly to agent-browser's internal ref system.
3. **Cross-browser via standards**: WebDriver BiDi support across Chrome, Firefox, Safari, Edge without proprietary protocol differences. Playwright requires language-specific bindings for each browser.
4. **AI-native design**: Vibium is explicitly designed for AI agents with simple CLI commands, reducing cognitive load compared to Playwright's DOM APIs.

The integration decision is architectural: Vibium is not a new capability but a **replacement backend** that eliminates vendor lock-in while maintaining the same agent-facing interface.

### Integration sketch

**Option A: CLI subprocess (maintains current shell-based architecture)**

```bash
# Current agent-browser workflow (Playwright-based)
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser click @e1
agent-browser screenshot page.png

# Proposed Vibium workflow (WebDriver BiDi-based)
vibium go https://example.com
vibium map
vibium click @e1
vibium screenshot page.png
```

Both CLI interfaces are semantic (element finding by text/role/label), both return references (`@eN`), both provide the same command vocabulary. The transition from bash script level is a find-replace on command names with minor output parsing adjustments.

**Option B: Python SDK (unified programmatic interface)**

```python
# Before (Playwright)
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto("https://example.com")
    snapshot = await page.evaluate("...accessibility tree...")
    await page.click('button[aria-label="Submit"]')
    await page.screenshot(path="page.png")

# After (Vibium)
from vibium.async_api import browser

bro = await browser.start()
vibe = await bro.page()
await vibe.go("https://example.com")
snapshot = await vibe.map()  # Returns @e1, @e2, etc.
await vibe.click("@e1")      # Use reference directly
await vibe.screenshot("page.png")
```

Vibium's API is flatter and semantic-focused compared to Playwright's object hierarchy. No CSS selectors needed; element finding uses accessible names and ARIA roles.

### Key architectural tradeoff

**Cost of switching (Medium)**:
- Current agent-browser tests validate against Playwright snapshots (visual diffs, accessibility tree format)
- Session persistence format differs (agent-browser uses Playwright context snapshots; Vibium uses browser state at HTTP API level)
- Mobile support (agent-browser supports iOS simulator via Appium; Vibium roadmap defers this)

**Benefits of switching**:
- Vendor-neutral protocol (W3C standardized, not controlled by Microsoft)
- Simpler API for AI agents (semantic locators, no CSS selectors)
- Smaller binary footprint (Go-based vs Node.js Playwright runtime)
- Reduced dependency surface (no large npm tree)

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| python3-development plugin (testing infrastructure) | Browser testing is optional feature, not core to language development. Vibium would be added as an optional test fixture, not a replacement for existing pytest patterns. Integration surface exists but scope is testing-specific, not general plugin usage. |

---

## Integration Decision

This proposal flags an **architectural decision point**, not a quick integration win. The research entry documents that:

1. Vibium provides an **equivalent interface** to agent-browser (semantic CLI, element references, same command vocabulary)
2. Vibium uses a **standardized protocol** (WebDriver BiDi) vs agent-browser's proprietary Playwright
3. The **API shape is similar enough** to enable a gradual migration (CLI commands map 1:1 in most cases)

**Recommended next steps:**
1. Create a SAM feature task: "Evaluate Vibium as standards-based agent-browser backend"
2. Spike: Run agent-browser test suite against Vibium CLI interface; measure compatibility gap
3. If compatibility gap is acceptable: Migrate to Vibium for vendor neutrality; or
4. If Playwright's mobile support is critical: Keep Playwright but document Vibium as alternative for web-only workflows

The utilization surface is real, but the integration requires architectural review and stakeholder alignment on protocol standardization vs existing feature parity.
