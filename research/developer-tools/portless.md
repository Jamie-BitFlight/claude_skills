---
title: "Portless"
research_date: "2026-02-26"
source_url: "https://github.com/vercel-labs/portless"
github_url: "https://github.com/vercel-labs/portless"
version_at_research: "v0.4.2"
license: "Apache-2.0"
last_verified: "2026-02-26"
version_at_verification: "v0.4.2"
next_review: "2026-05-26"
---

## Overview

Portless replaces numeric port numbers with stable, named `.localhost` URLs for local development servers. Instead of `http://localhost:3000`, each dev server gets a URL like `http://myapp.localhost:1355`, routed through a single long-running proxy daemon. The tool explicitly targets both humans and AI coding agents, citing agent port confusion in monorepos as a primary motivation.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Port conflicts (`EADDRINUSE`) when multiple projects default to the same port | Portless assigns a random free port (4000-4999) per app and exposes it via a named hostname instead |
| Memorizing which service runs on which port number | Named `.localhost` URLs (`api.myapp.localhost:1355`) replace arbitrary numbers |
| Browser tabs show the wrong app after a port is reused | Stable named URLs never collide across project restarts |
| AI coding agents guess or hardcode wrong ports, especially in monorepos | Deterministic named URLs give agents a reliable address to reference |
| Cookies and localStorage bleeding across apps sharing `localhost` | Each named subdomain provides isolated cookie/storage scope |
| CORS allowlists and OAuth redirect URIs hardcoded to specific port numbers | Named URLs remain stable across sessions, removing the need to update config |
| HTTP/1.1 connection limit (6 per host) bottlenecks unbundled dev servers (Vite, Nuxt) | Optional HTTP/2 over TLS multiplexes all requests on one connection per host |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 2,569 | 2026-02-26 |
| GitHub Forks | 84 | 2026-02-26 |
| npm Downloads (last 30 days) | 8,083 | 2026-02-26 |
| Contributors | 4 | 2026-02-26 |
| Latest Release | v0.4.2 | 2026-02-25 |
| Open Issues | 20 | 2026-02-26 |
| Repository Age | 11 days (created 2026-02-15) | 2026-02-26 |

---

## Key Features

### Named Localhost Routing

- Single proxy daemon listening on port 1355 routes all requests by `Host` header to the correct upstream app
- Subdomain depth is unrestricted: `api.myapp.localhost:1355`, `docs.myapp.localhost:1355`
- Proxy auto-starts when any `portless <name> <cmd>` is run; explicit `portless proxy start` also available
- Route state stored in `~/.portless/` (user-scoped, port >= 1024) or `/tmp/portless` (system-scoped, port < 1024 via sudo)

### HTTP/2 + TLS Support

- Optional `--https` flag generates a local CA and per-hostname TLS certificates automatically
- First run prompts once for sudo to add CA to system trust store; no subsequent prompts
- Per-hostname certificates with exact SAN match (RFC 2606 prohibits `*.localhost` wildcard certs)
- Forces SHA-256 for all CA and server certificates; detects and regenerates legacy SHA-1 certs
- Custom certificate paths supported via `--cert` and `--key` flags (compatible with mkcert output)

### Framework Port Injection

- Sets `PORT` and `HOST` environment variables; most frameworks (Next.js, Express, Nuxt) respect these automatically
- Auto-injects `--port` and `--host` flags for frameworks that ignore `PORT` (Vite, Astro, React Router, Angular)
- Shell script and version-manager shim resolution via `/bin/sh -c` execution with `node_modules/.bin` prepended to `PATH`

### Proxy Safety and Reliability

- Loop detection via `X-Portless-Hops` header; responds `508 Loop Detected` with actionable fix instructions
- Loop detection covers WebSocket upgrades in addition to HTTP requests
- `RouteConflictError` thrown if a hostname is already registered by a live process; `--force` flag overrides
- `stdin.setRawMode(false)` reset on SIGINT prevents terminal raw mode being left active after exit
- File locking on route state files with stale-lock detection (10-second threshold, 20-retry backoff)

### Agent-First Design

- Repository ships an `AGENTS.md` with coding agent rules (no emojis, pnpm usage, doc update requirements)
- Ships a `skills/portless/SKILL.md` AI skill file instructing agents how to use portless in projects
- Description explicitly calls out AI agent port confusion as a solved problem

---

## Technical Architecture

<eg>
Browser (myapp.localhost:1355)
        |
        v
portless proxy daemon (port 1355)
  - Node.js http/http2 server (no external proxy deps)
  - Routes by Host header (or :authority pseudo-header for HTTP/2)
  - Reads route registry from ~/.portless/<hostname>.json files
  - Injects X-Forwarded-For/Proto/Host/Port headers
  - Strips HTTP/1.1 hop-by-hop headers when bridging to HTTP/2 clients
        |
   +---------+----------+
   |                    |
   v                    v
:4123 (myapp)      :4567 (api.myapp)
  Next.js            Express
</eg>

The proxy is implemented entirely with Node.js built-in `http`, `http2`, and `net` modules -- no external proxy libraries. Route registration uses JSON files per hostname in the state directory, with file-based locking for safe concurrent access. The daemon runs as a background process (daemonized via child process detach), storing its PID in the state directory.

Certificate generation uses the `openssl` CLI for SHA-1 detection (Node.js < 24.9 compatibility) and Node.js `crypto` for key generation. The CA is self-signed; per-hostname leaf certificates are issued with exact SAN entries.

The monorepo uses pnpm workspaces with Turborepo. The publishable package lives in `packages/portless/`. Built with `tsup`, tested with `vitest`, typed with TypeScript 5.x, Node.js 20+ required.

---

## Installation & Usage

```bash
# Global install
npm install -g portless

# Start proxy (auto-starts on first app run)
portless proxy start

# Run an app with a named URL
portless myapp next dev
# -> http://myapp.localhost:1355

# Subdomain routing
portless api.myapp pnpm start
# -> http://api.myapp.localhost:1355

# Enable HTTP/2 + TLS
portless proxy start --https

# List active routes
portless list

# Stop proxy
portless proxy stop

# Override a conflicting route
portless myapp --force next dev

# Bypass portless entirely
PORTLESS=0 pnpm dev

# Proxy on privileged port (requires sudo)
sudo portless proxy start -p 80
```

```json
{
  "scripts": {
    "dev": "portless myapp next dev"
  }
}
```

```bash
# Environment variable configuration
export PORTLESS_HTTPS=1        # Always use HTTPS
export PORTLESS_PORT=8080      # Override default proxy port
export PORTLESS_STATE_DIR=/tmp/custom-portless  # Override state directory
```

---

## Relevance to Claude Code Development

### Applications

- Claude Code agents frequently encounter port confusion when working in monorepos with multiple concurrent dev servers; portless gives agents a stable URL contract to reference in instructions
- When spawning dev servers during automated testing or code generation tasks, agents can reference `http://<name>.localhost:1355` rather than scanning for an available port or reading process output for the assigned port
- The `PORTLESS=0` escape hatch allows agents to bypass portless when running in CI or environments where the proxy is not present

### Patterns Worth Adopting

- The `AGENTS.md` convention in the repo root -- machine-readable agent rules alongside human-readable `README.md` -- is a pattern applicable to Claude Code skill repositories and projects where agent behavior should be constrained
- The `skills/portless/SKILL.md` pattern (shipping an AI skill file within the tool's own repo) demonstrates how developer tools can package agent instructions alongside the tool itself
- Per-hostname state files with file locking is a robust pattern for any multi-process coordination without requiring a database or network service

### Integration Opportunities

- Claude Code skills that scaffold new projects could include portless setup in the dev environment initialization step, ensuring agents always have stable URLs for spawned servers
- A portless MCP server could expose `portless list` output as a resource, letting Claude Code query active named routes rather than asking the user what port a service is on
- The `X-Portless-Hops` loop detection header pattern could be adopted in multi-agent HTTP chains to detect and surface routing misconfiguration

---

## References

- [vercel-labs/portless README](https://github.com/vercel-labs/portless/blob/main/README.md) (accessed 2026-02-26)
- [vercel-labs/portless CHANGELOG](https://github.com/vercel-labs/portless/blob/main/CHANGELOG.md) (accessed 2026-02-26)
- [portless npm package](https://www.npmjs.com/package/portless) (accessed 2026-02-26)
- [GitHub API: vercel-labs/portless](https://api.github.com/repos/vercel-labs/portless) (accessed 2026-02-26)
- [GitHub API: vercel-labs/portless releases/latest](https://api.github.com/repos/vercel-labs/portless/releases/latest) (accessed 2026-02-26)
- [npm downloads API: portless](https://api.npmjs.org/downloads/point/last-month/portless) (accessed 2026-02-26)

---
