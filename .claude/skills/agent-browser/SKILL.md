---
description: Browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing web apps, or automating any browser task. Triggers include requests to "open a website", "fill out a form", "click a button", "take a screenshot", "scrape data from a page", "test this web app", "login to a site", "automate browser actions", or any task requiring programmatic web interaction.
allowed-tools: Bash(npx agent-browser:*)
---
# Browser Automation with agent-browser

## Core Workflow

Every browser automation follows this pattern:

1. **Navigate**: `npx agent-browser open <url>`
2. **Snapshot**: `npx agent-browser snapshot -i` (get element refs like `@e1`, `@e2`)
3. **Interact**: Use refs to click, fill, select
4. **Re-snapshot**: After navigation or DOM changes, get fresh refs

```bash
npx agent-browser open https://example.com/form
npx agent-browser snapshot -i
# Output: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Submit"

npx agent-browser fill @e1 "user@example.com"
npx agent-browser fill @e2 "password123"
npx agent-browser click @e3
npx agent-browser wait --load networkidle
npx agent-browser snapshot -i  # Check result
```

## Essential Commands

```bash
# Navigation
npx agent-browser open <url>              # Navigate (aliases: goto, navigate)
npx agent-browser close                   # Close browser

# Snapshot
npx agent-browser snapshot -i             # Interactive elements with refs (recommended)
npx agent-browser snapshot -s "#selector" # Scope to CSS selector

# Interaction (use @refs from snapshot)
npx agent-browser click @e1               # Click element
npx agent-browser fill @e2 "text"         # Clear and type text
npx agent-browser type @e2 "text"         # Type without clearing
npx agent-browser select @e1 "option"     # Select dropdown option
npx agent-browser check @e1               # Check checkbox
npx agent-browser press Enter             # Press key
npx agent-browser scroll down 500         # Scroll page

# Get information
npx agent-browser get text @e1            # Get element text
npx agent-browser get url                 # Get current URL
npx agent-browser get title               # Get page title

# Wait
npx agent-browser wait @e1                # Wait for element
npx agent-browser wait --load networkidle # Wait for network idle
npx agent-browser wait --url "**/page"    # Wait for URL pattern
npx agent-browser wait 2000               # Wait milliseconds

# Capture
npx agent-browser screenshot              # Screenshot to temp dir
npx agent-browser screenshot --full       # Full page screenshot
npx agent-browser pdf output.pdf          # Save as PDF
```

## Common Patterns

### Form Submission

```bash
npx agent-browser open https://example.com/signup
npx agent-browser snapshot -i
npx agent-browser fill @e1 "Jane Doe"
npx agent-browser fill @e2 "jane@example.com"
npx agent-browser select @e3 "California"
npx agent-browser check @e4
npx agent-browser click @e5
npx agent-browser wait --load networkidle
```

### Authentication with State Persistence

```bash
# Login once and save state
npx agent-browser open https://app.example.com/login
npx agent-browser snapshot -i
npx agent-browser fill @e1 "$USERNAME"
npx agent-browser fill @e2 "$PASSWORD"
npx agent-browser click @e3
npx agent-browser wait --url "**/dashboard"
npx agent-browser state save auth.json

# Reuse in future sessions
npx agent-browser state load auth.json
npx agent-browser open https://app.example.com/dashboard
```

### Data Extraction

```bash
npx agent-browser open https://example.com/products
npx agent-browser snapshot -i
npx agent-browser get text @e5           # Get specific element text
npx agent-browser get text body > page.txt  # Get all page text

# JSON output for parsing
npx agent-browser snapshot -i --json
npx agent-browser get text @e1 --json
```

### Parallel Sessions

```bash
npx agent-browser --session site1 open https://site-a.com
npx agent-browser --session site2 open https://site-b.com

npx agent-browser --session site1 snapshot -i
npx agent-browser --session site2 snapshot -i

npx agent-browser session list
```

### Visual Browser (Debugging)

```bash
npx agent-browser --headed open https://example.com
npx agent-browser highlight @e1          # Highlight element
npx agent-browser record start demo.webm # Record session
```

### iOS Simulator (Mobile Safari)

```bash
# List available iOS simulators
npx agent-browser device list

# Launch Safari on a specific device
npx agent-browser -p ios --device "iPhone 16 Pro" open https://example.com

# Same workflow as desktop - snapshot, interact, re-snapshot
npx agent-browser -p ios snapshot -i
npx agent-browser -p ios tap @e1          # Tap (alias for click)
npx agent-browser -p ios fill @e2 "text"
npx agent-browser -p ios swipe up         # Mobile-specific gesture

# Take screenshot
npx agent-browser -p ios screenshot mobile.png

# Close session (shuts down simulator)
npx agent-browser -p ios close
```

**Requirements:** macOS with Xcode, Appium (`npm install -g appium && appium driver install xcuitest`)

**Real devices:** Works with physical iOS devices if pre-configured. Use `--device "<UDID>"` where UDID is from `xcrun xctrace list devices`.

## Ref Lifecycle (Important)

Refs (`@e1`, `@e2`, etc.) are invalidated when the page changes. Always re-snapshot after:

- Clicking links or buttons that navigate
- Form submissions
- Dynamic content loading (dropdowns, modals)

```bash
npx agent-browser click @e5              # Navigates to new page
npx agent-browser snapshot -i            # MUST re-snapshot
npx agent-browser click @e1              # Use new refs
```

## Semantic Locators (Alternative to Refs)

When refs are unavailable or unreliable, use semantic locators:

```bash
npx agent-browser find text "Sign In" click
npx agent-browser find label "Email" fill "user@test.com"
npx agent-browser find role button click --name "Submit"
npx agent-browser find placeholder "Search" type "query"
npx agent-browser find testid "submit-btn" click
```

## Deep-Dive Documentation

| Reference | When to Use |
|-----------|-------------|
| [references/commands.md](references/commands.md) | Full command reference with all options |
| [references/snapshot-refs.md](references/snapshot-refs.md) | Ref lifecycle, invalidation rules, troubleshooting |
| [references/session-management.md](references/session-management.md) | Parallel sessions, state persistence, concurrent scraping |
| [references/authentication.md](references/authentication.md) | Login flows, OAuth, 2FA handling, state reuse |
| [references/video-recording.md](references/video-recording.md) | Recording workflows for debugging and documentation |
| [references/proxy-support.md](references/proxy-support.md) | Proxy configuration, geo-testing, rotating proxies |

## Ready-to-Use Templates

| Template | Description |
|----------|-------------|
| [templates/form-automation.sh](templates/form-automation.sh) | Form filling with validation |
| [templates/authenticated-session.sh](templates/authenticated-session.sh) | Login once, reuse state |
| [templates/capture-workflow.sh](templates/capture-workflow.sh) | Content extraction with screenshots |

```bash
./templates/form-automation.sh https://example.com/form
./templates/authenticated-session.sh https://app.example.com/login
./templates/capture-workflow.sh https://example.com ./output
```
