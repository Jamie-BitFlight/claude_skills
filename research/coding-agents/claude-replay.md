---
title: claude-replay
resource_name: claude-replay
description: Convert AI coding agent session transcripts (Claude Code, Cursor, Codex CLI) into self-contained, embeddable HTML replays
source: https://github.com/es617/claude-replay
license: MIT
current_version: 0.4.0
released: 2026-03-13
language: JavaScript
status: Active
---

# claude-replay

## Identity and Metadata

**Resource name**: claude-replay

**Description**: Community tool (not affiliated with or endorsed by Anthropic) that converts Claude Code, Cursor, and Codex CLI session transcripts into interactive, shareable HTML replays.

**Source**: <https://github.com/es617/claude-replay>

**License**: MIT License

**Current version**: 0.4.0 (released 2026-03-13)

**Language**: JavaScript (Node.js 18+)

**Repository**: GitHub public repository

**Community support**: 500 GitHub stars (as of 2026-03-13), 24 forks, 1 open issue

## Overview

claude-replay solves a specific problem with AI-assisted coding workflows: sessions are great for development but difficult to share effectively. Screen recordings are bulky, and JSONL transcripts are hard to navigate. This tool auto-detects session transcript formats from Claude Code, Cursor, and Codex CLI, parses them, and renders them as interactive, self-contained HTML files suitable for documentation, blog posts, bug reports, and teaching.

**Key design principles**:

1. **Zero external dependencies** — the generated replay is a single HTML file with no external requests, CDN dependencies, or framework loading
2. **Self-contained compression** — uses browser-native `DecompressionStream` API (Chrome 80+, Firefox 113+, Safari 16.4+) to decompress deflate-compressed transcript data embedded in the HTML
3. **Format auto-detection** — detects Claude Code (streaming JSON), Cursor, and Codex CLI formats automatically with no user intervention
4. **Session discovery** — auto-locates sessions from standard storage locations (`~/.claude/projects/`, `~/.cursor/projects/`, `~/.codex/sessions/`)

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI coding sessions are difficult to share with team members | Converts JSONL transcripts into interactive, self-contained HTML files suitable for documentation, blogs, bug reports, and teaching |
| Screen recordings consume excessive storage and bandwidth | Single HTML file output with compression reduces typical session size by 60-70% using native browser decompression |
| Raw JSONL transcripts are tedious to navigate and understand | Interactive playback with adjustable speed, step-by-step navigation, and collapsible thinking/tool blocks enables clear session review |
| Sharing requires manual copying or email attachment | Self-contained HTML can be emailed, hosted, or embedded via iframe with zero external dependencies or CDN requests |
| Viewing session details requires special tools or manual parsing | Web-based editor provides visual session browser, turn editing, live preview, and one-click export |

**Source**: <https://github.com/es617/claude-replay/blob/main/README.md> (accessed 2026-03-13)

## Key Features

### Core Playback

- Interactive block-by-block animation of turns
- Play/pause with adjustable playback speed (0.5x to 5x)
- Step forward/back through individual blocks within turns
- Progress bar with turn dots and bookmark indicators
- Session timer showing elapsed and total time
- Keyboard shortcuts: Space/K (play/pause), arrows/H/L (step), Shift+arrows (jump turns), T (jump thinking/tool blocks)
- Splash screen with play button for initial engagement

### UI and Customization

- **Terminal-style bottom-to-top scroll** — new messages appear at bottom, old content scrolls upward (mimics terminal behavior)
- **Toggle blocks** — user can show/hide thinking blocks and tool calls independently
- **6 built-in color themes**: tokyo-night (default), monokai, solarized-dark, github-light, dracula, bubbles
- **Custom theme support** — JSON color overrides, with fallback to tokyo-night defaults for unspecified keys
- **Advanced CSS customization** — `extraCss` key in theme JSON for arbitrary style overrides

### Editor (v0.4.0+)

New web-based UI launched by default (`claude-replay` with no arguments or `claude-replay editor`):

- **Three-panel layout**: session browser on left, turn editor in center, live preview on right
- **Session browser** — auto-discovers sessions from standard locations and file system folder navigation
- **Turn editor** — include/exclude individual turns, edit user prompts, expand/view assistant blocks (read-only), add bookmarks at specific turns
- **Options panel** — configurable theme, speed, thinking/tool toggles, redaction rules, labels, metadata
- **Live preview** — updates in real-time as edits are made
- **Export** — download final HTML replay from the editor
- **File browser** — restricted to home directory for safety

### Session Handling

- **Session chaining** — concatenate up to 20 sessions into one replay; turns are sorted chronologically if timestamps present, otherwise by command-line order
- **Session ID lookup** — pass a session ID instead of file path; claude-replay searches `~/.claude/projects/`, `~/.cursor/projects/`, and `~/.codex/sessions/`
- **Multiple input formats**: full JSONL file path or session ID string

### Secret Redaction

Default automatic redaction of common secret patterns **before** writing to output file:

- API keys (`sk-...`, `sk-ant-...`, `key-...`)
- AWS access key IDs (`AKIA...`)
- Bearer and JWT tokens
- Database connection strings (`postgres://...`, `mongodb://...`, etc.)
- Private key blocks (`-----BEGIN ... PRIVATE KEY-----`)
- Generic key/value secrets (`api_key=...`, `auth_token: ...`)
- Environment variable secrets (`PASSWORD=...`, `TOKEN=...`)
- Long hex tokens (40+ characters)

**Important**: Pattern-based redaction is best-effort only and cannot catch every secret format. User must review output before sharing publicly.

Custom redaction via `--redact "text"` or `--redact "text=replacement"` flags.

### Transcript Format Support

**Claude Code**: One JSON object per line with `type` field (`user`, `assistant`, `system`, `progress`, etc.). Includes timestamps, thinking blocks, tool calls with results. Format auto-detected.

**Cursor**: One JSON object per line with `role` field. No timestamps; paced timing is used by default. Thinking appears inline. Format auto-detected.

**Codex CLI (OpenAI)**: Event-based JSONL with typed events. Includes timestamps. Tool calls (`exec_command`, `apply_patch`) are normalized to Claude Code equivalents (Bash, Edit/Write) for consistent rendering. Codex encrypted reasoning blocks are skipped; commentary mapped to thinking blocks. Format auto-detected.

### Timing Modes

Three modes control how playback speed is derived from or generated for turns:

- **`auto`** (default) — uses real timestamps if available in transcript, falls back to paced mode
- **`real`** — forces use of original timestamps from transcript
- **`paced`** — generates synthetic timing based on content length (presentation-style reveal speed scaling with text length)

Paced timing is default for Cursor (which has no timestamps) and available for Claude Code for demonstration purposes.

### Output Optimization

Two layers of optimization for zero external dependencies:

- **Minified CSS/JS** — the player template is minified with esbuild; variable names are mangled, whitespace removed. Use `--no-minify` for readable output.
- **Compressed data** — transcript JSON is deflate-compressed and base64-encoded, reducing output size by ~60-70% typically. Browser decompresses at load time using native `DecompressionStream` API. For older browsers, use `--no-compress` to embed raw JSON.

### Embedding and Sharing

- Single self-contained HTML file — no dependencies, can email it or host on any server
- Embeddable via iframe: `<iframe src="replay.html" width="100%" height="600"></iframe>`
- Open Graph and Twitter Card meta tags for link previews (with default or custom OG image)
- Deep linking via URL fragment: `replay.html#turn=5` jumps to turn 5

## Technical Architecture

### Core Components

**Parser** (`src/parser.mjs`): Reads JSONL transcripts line by line.

- Handles Claude Code streaming format where a single assistant message spans multiple JSONL lines with incremental content blocks
- Groups turns as: user message + assistant response (text, tool calls, thinking blocks) + tool results
- Merges consecutive command messages (slash commands + stdout)
- Strips internal XML tags (`<system-reminder>`, `<local-command-caveat>`, etc.)
- Filters empty turns and "No response requested." boilerplate
- Implements time range filtering (`--from`, `--to` ISO 8601 timestamps) and turn range filtering (`--turns N-M`)
- Auto-detects transcript format (Claude Code, Cursor, Codex) and applies format-specific parsing
- Applies paced timing generation when needed

**Session Resolver** (`src/resolve-session.mjs`): Locates session files by ID.

- Searches `~/.claude/projects/`, `~/.cursor/projects/`, and `~/.codex/sessions/` for matching session JSONL files
- Handles Claude Code project directory structure with encoded project names
- Supports Cursor `<uuid>.jsonl` filename pattern

**Secrets Redactor** (`src/secrets.mjs`): Pattern-based secret detection and replacement.

- Scans all embedded text for credential patterns (API keys, tokens, connection strings, etc.)
- Replaces matched text with `[REDACTED]` before HTML is written
- Enables custom redaction patterns via `--redact` flags

**Themes** (`src/themes.mjs`): Color scheme and layout customization.

- 6 built-in themes with predefined CSS color variables
- Custom theme support via JSON file with optional `extraCss` for arbitrary style overrides
- Fallback to tokyo-night defaults for missing keys in custom themes
- Variables control main background, surfaces, text styles, accents, tool/thinking backgrounds, etc.

**Renderer** (`src/renderer.mjs`): Compresses parsed turns and injects into HTML template.

- Takes parsed turns and formatting options
- Applies secret redaction to all text
- Deflate-compresses transcript JSON with base64 encoding
- Injects compressed data and theme into HTML template
- Selects minified or unminified template based on availability

**Editor Server** (`src/editor-server.mjs`): Web-based session editor.

- Launches local HTTP server on `127.0.0.1` (localhost only, not exposed to network)
- Provides REST API for session discovery, turn loading, preview rendering
- Three-panel UI: session browser, turn editor, live preview
- Never modifies original JSONL files; all edits held in memory
- Exports final HTML replay on user request
- File browser with home directory restriction for safety

**CLI Entry Point** (`bin/claude-replay.mjs`): Command-line argument parsing and orchestration.

- Parses options for turn ranges, filtering, themes, redaction, timing, output format
- Routes to editor (default), CLI generation, or extract subcommand
- Handles session ID lookup via resolver
- Coordinates parser, renderer, and file output

**Data Extraction** (`src/extract.mjs`): Reverse operation to recover turns from generated replay.

- Parses previously generated HTML to extract embedded compressed turn data
- Decompresses and outputs as JSON for regeneration with different options
- Useful when original JSONL is no longer available

### Data Flow

```
JSONL Input
    ↓
[Parser] — auto-detect format
    ↓
Filtered & Parsed Turns
    ├─ [Secrets Redactor]
    ├─ [Themes] — apply color scheme
    └─ [Optional: Paced Timing Generator]
    ↓
[Renderer] — deflate compress, base64 encode
    ↓
Compressed JSON Blob
    ↓
[Template Injection] — HTML + embedded data
    ↓
Output: Single Self-Contained HTML File
    ↓
[Browser] — decompress with native DecompressionStream
    ↓
[Player.js] — vanilla JS, zero frameworks
    ↓
Interactive Playback
```

### Player Implementation

- **Vanilla JavaScript** — no frameworks, no bundled dependencies
- **Native APIs** — uses `DecompressionStream` (Chrome 80+, Firefox 113+, Safari 16.4+) for decompression
- **Single HTML file** — includes minified CSS, minified JS, and compressed data
- **Responsive design** — adapts to container size when embedded via iframe
- **Keyboard-driven** — full navigation via keyboard, mouse clicks alternative

### Build Process

- Development: `npm install` installs esbuild (dev-only dependency)
- Build: `npm run build` generates minified template (`template/player.min.html`) using esbuild
- Minified template is committed to repo and included in npm releases
- If minified template unavailable, CLI falls back to unminified automatically

### Testing

- Unit tests via Node's built-in `--test` runner (`npm test`)
- End-to-end tests via Playwright (`npm run test:e2e`)
- Playwright config specified in `playwright.config.mjs`
- 32+ e2e test cases covering playback, stepping, expand/collapse, keyboard shortcuts, navbar, progress bar, speed control, chapters

## Installation and Usage

### Installation

```bash
npm install -g claude-replay
```

Or run directly with npx (zero install):

```bash
npx claude-replay
```

### Web Editor

Launch the browser-based editor (default behavior):

```bash
claude-replay
claude-replay --port 8080
```

### CLI Usage

Generate a replay from the command line:

```bash
# By session ID (auto-locates file)
claude-replay abc123def456 -o replay.html

# By file path
claude-replay ~/.claude/projects/-Users-me-myproject/session-id.jsonl -o replay.html

# Chain multiple sessions
claude-replay session1-id session2-id -o combined.html

# With options
claude-replay session.jsonl --turns 5-15 --speed 2.0 --no-thinking -o replay.html

# Filter by time range
claude-replay session.jsonl --from "2026-02-26T02:00" --to "2026-02-26T03:00" -o replay.html

# Use different theme
claude-replay session.jsonl --theme dracula -o replay.html

# Extract turns from previously generated replay
claude-replay extract replay.html -o turns.json
```

### Key Command-Line Options

- `-o, --output FILE` — output HTML file path
- `--turns N-M` — include only turns N through M
- `--exclude-turns N,N,...` — exclude specific turns by index
- `--from TIMESTAMP` — start filter (ISO 8601)
- `--to TIMESTAMP` — end filter (ISO 8601)
- `--speed N` — initial playback speed (default: 1.0)
- `--no-thinking` — hide thinking blocks by default
- `--no-tool-calls` — hide tool call blocks by default
- `--mark "N:Label"` — add bookmark/chapter at turn N (repeatable)
- `--no-auto-redact` — disable automatic secret redaction
- `--redact "text"` or `--redact "text=replacement"` — custom redaction
- `--theme NAME` — built-in theme name (default: tokyo-night)
- `--theme-file FILE` — custom theme JSON
- `--timing MODE` — auto | real | paced (default: auto)
- `--title TEXT` — page title
- `--description TEXT` — meta description for link previews
- `--og-image URL` — OG image URL for link previews
- `--list-themes` — list available built-in themes and exit
- `--no-minify` — use unminified template (larger output)
- `--no-compress` — embed raw JSON instead of compressed data
- `--open` — open generated HTML in default browser
- `-v, --version` — show version and exit

## Limitations and Caveats

**Privacy concern**: Replay files embed the **full session transcript**, including source code, file paths, tool inputs/outputs, thinking traces, and other session data. Secret redaction (enabled by default) catches common credential patterns but does NOT filter code, file contents, or other sensitive information. Users must review generated HTML before sharing publicly.

**Secret redaction is best-effort**: Pattern-based detection cannot catch every possible secret format. It is a safety net, not a guarantee. Always review output before public sharing.

**Data recovery**: Editing the player JavaScript to hide or filter turns only affects **rendering** — the original compressed data remains embedded in the HTML and can be recovered by extracting and decompressing the data blob. To exclude sensitive content, use CLI flags at generation time (`--turns`, `--exclude-turns`, `--redact`).

**Timestamp dependency**: Cursor transcripts lack timestamps, so paced timing is used by default. Codex CLI includes timestamps. Claude Code includes optional timestamps. When timestamps are absent, synthetic timing is generated based on content length.

**Browser compatibility for decompression**: Decompression uses native `DecompressionStream` API available in Chrome 80+, Firefox 113+, Safari 16.4+. For older browsers, use `--no-compress` to embed raw JSON (increases file size by 3-4x typically).

**File size**: Generated HTML files typically range from tens of KB (short sessions) to several MB (long sessions with many tool calls). Compression reduces typical session size by 60-70%.

## Relevance to Claude Code Development

claude-replay is directly relevant for:

1. **Documentation and guides** — embed interactive examples of Claude Code workflows in skill documentation or architecture guides
2. **Showcasing AI-assisted development** — visual demonstrations of how Claude Code completes complex tasks
3. **Bug reproduction** — attach annotated replays instead of raw JSONL logs to issues, making reproduction steps clear
4. **Teaching and training** — step through AI reasoning, tool usage, and decision-making in detail
5. **Session archival** — preserve and share significant sessions (feature implementations, incident investigation, etc.) without video recording overhead
6. **Integration with skill development** — record and share Claude Code sessions during skill prototyping and testing phases

The tool is particularly valuable for the Claude Skills repository because plugin and skill development often involves iterative agent work. Sharing these sessions as reproducible HTML replays enables knowledge transfer and serves as executable documentation.

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Cline](./cline.md) | coding-agents | integrates with Claude Code; alternative agent with session handling and approval workflows |
| [Tembo](./tembo.md) | coding-agents | orchestrates multiple Claude Code and Cursor agents; session documentation pairs with replay for team knowledge transfer |
| [Claude Pilot](./claude-pilot.md) | coding-agents | enforces quality gates on Claude Code sessions; persistent memory of sessions complements replay archival |
| [Claude-Mem](../context-management/claude-mem.md) | context-management | captures and stores session observations; hybrid approach to session documentation vs replay's shareable HTML format |
| [Pixel Agents](../developer-tools/pixel-agents.md) | developer-tools | visualizes Claude Code agent activity from JSONL transcripts; provides animated overlay while claude-replay creates shareable interactive replays |
| [Shpool](../developer-tools/shpool.md) | developer-tools | persists shell sessions with VT100 replay on reattach; shared concern with claude-replay on capturing and replaying terminal output |
| [Using tmux with Claude Code](../developer-tools/using-tmux-with-claude-code.md) | developer-tools | session capture and history navigation patterns for Claude Code workflows; tmux output capture complements replay's turn-level structuring |
| [tmuxp](../developer-tools/tmuxp.md) | developer-tools | freezes and restores tmux session state via YAML; replay serves similar archival purpose at transcript level with interactive playback |
| [Claude Conductor](../developer-tools/claude-conductor.md) | developer-tools | context-driven plugin for Claude Code; generated session replays serve as demonstration and teaching artifacts for plugin capabilities |
| [libtmux](../developer-tools/libtmux.md) | developer-tools | Python API for tmux session control and pane output capture; underlying technology for programmatic session interaction that replay automates for documentation |

---

## Freshness Tracking

**Last reviewed**: 2026-03-13

**Next review**: 2026-06-13 (3 months)

**Confidence levels**:

- Identity/Metadata: high (from GitHub API, package.json)
- Features: high (from README, CHANGELOG, source code inspection)
- Architecture: high (from source file structure and CLI entry point code)
- Usage Examples: high (from README examples, verified against package.json bin field)
- Limitations: high (from README privacy section, explicit documentation)

## References

- [GitHub Repository](https://github.com/es617/claude-replay)
- [npm Package](https://npmjs.com/package/claude-replay) — accessible via <https://www.npmjs.com/package/claude-replay>
- [Live Demo](https://es617.github.io/claude-replay/demo-redaction.html)
- [GitHub Releases](https://github.com/es617/claude-replay/releases) — v0.4.0 released 2026-03-13
- Repository metadata: 500 stars (as of 2026-03-13), 24 forks, 1 open issue, MIT License
- Source documentation: README.md, CHANGELOG.md, package.json (accessed 2026-03-13)
- Architecture: bin/claude-replay.mjs, src/ module files (accessed 2026-03-13)
