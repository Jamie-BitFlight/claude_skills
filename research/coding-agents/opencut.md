---
title: OpenCut
url: https://github.com/opencut-app/opencut
description: Free and open source video editor for web, desktop, and mobile
category: coding-agents
---

# OpenCut

## Identity & Metadata

**Name**: OpenCut
**Repository**: <https://github.com/opencut-app/opencut>
**License**: MIT
**Primary Language**: TypeScript
**Homepage**: <https://opencut.app>
**Latest Status**: Rewrite in progress (as of 2026-06-18)

## Overview

OpenCut is a free, open-source video editor available across web, desktop, and mobile platforms, positioned as an open-source alternative to proprietary video editors like CapCut. The project is currently undergoing a complete architectural rewrite from the ground up, introducing modern patterns including plugin-first architecture, MCP server integration for AI agents, cross-platform code sharing via a Rust core, and programmatic editing APIs. The previous stable version (OpenCut Classic) remains available in production; the rewrite is being developed separately at new.opencut.app.

**Current Status**: The rewrite introduces planned features including an Editor API, third-party plugin support, Rust-based cross-platform core, MCP server for AI agents, headless mode for automation, and built-in scripting capabilities. These features are announced but not yet fully implemented or documented in the current repository state (as of 2026-06-18).

**Source**: <https://github.com/opencut-app/opencut/blob/main/README.md> (accessed 2026-06-18)

## Key Statistics

- **GitHub Stars**: 56,388 (as of 2026-06-18)
- **GitHub Forks**: 6,127 (as of 2026-06-18)
- **Contributors**: 96 (as of 2026-06-18)
- **Repository Created**: 2025-06-22
- **Last Updated**: 2026-06-18
- **Current Production**: opencut.app (running classic version)
- **Rewrite Preview**: new.opencut.app

## Problem Addressed

OpenCut is "a free and open source video editor for web, desktop, and mobile" designed as an open-source alternative to proprietary video editors. The project is currently undergoing a complete architectural rewrite from the ground up. The previous stable version (OpenCut Classic) remains available at [opencut-app/opencut-classic](https://github.com/opencut-app/opencut-classic) and powers the current production site; the new rewrite is being developed at new.opencut.app.

## Key Features

The rewritten version of OpenCut is introducing several architectural innovations:

1. **Editor API** — A documented, versioned API for programmatic video editing operations
2. **Plugin-First Architecture** — "First-class third party plugins (made possible by a plugin-first architecture)" allowing external developers to extend functionality
3. **Cross-Platform Monorepo** — "Desktop, mobile, and browser from one codebase (Rust core)" enabling shared logic across all platforms
4. **MCP Server** — "MCP server (for AI agents)" providing Claude and other AI agents with structured access to editor capabilities
5. **Headless Mode** — "Headless mode (automation, batch rendering)" for server-side video processing and batch operations
6. **Scripting Tab** — "A scripting tab directly in the editor" enabling users to write automation scripts

**Web UI Stack** (from @opencut/web):
- React 19.2.0 with React DevTools for interactive component debugging
- TanStack Router for client-side navigation
- TanStack React Start for server-side rendering and deployment orchestration
- Tailwind CSS 4.1.18 for utility-first styling
- Radix UI for unstyled, accessible component primitives
- Base UI for low-level component building
- React Hook Form with Zod for type-safe form state and validation
- Recharts for data visualization (timelines, effect previews)
- Embla Carousel for media gallery and timeline navigation
- Sonner for toast notifications
- Lucide React and Hugeicons for iconography

**Testing Framework**: Vitest with React Testing Library (@testing-library/react, @testing-library/dom) and jsdom for DOM simulation

## Technical Architecture

**Build & Package Management**:
- **Monorepo Structure**: Turbo workspaces with `apps/*` subdirectories
- **Package Manager**: Bun 1.3.11 (specified in root package.json, configured with 7-day minimum release age for package upgrades)
- **Deployment**: Cloudflare Workers via Wrangler CLI

**Frontend Architecture** (@opencut/web):
- **Build Tool**: Vite 8.0.0 with TypeScript 6.0.2
- **Dev Server**: `vite dev --port 5173`
- **Production Build**: `vite build` + `wrangler deploy` to Cloudflare Workers
- **Routing**: TanStack Router with auto-generated routeTree.gen.ts from filesystem routes
- **Module Imports**: Path alias `#/*` maps to `src/*` for clean internal imports

**Language & Type Safety**:
- TypeScript 6.0.2 as primary language for all source code
- End-to-end type safety via Zod runtime validation
- Biome-based linting and formatting via Ultracite configuration (.github/copilot-instructions.md)

**Code Quality Standards** (from Ultracite configuration):
- Zero configuration required
- Subsecond performance via Biome's Rust-based linter
- Strict accessibility (a11y) compliance
- React hooks discipline (proper dependencies, top-level calls)
- No TypeScript enums; use const declarations instead
- Comprehensive error handling; no swallowed exceptions
- Semantic HTML over ARIA roles where possible

**Component Library Patterns**:
- Base UI primitives (unstyled, headless components)
- Radix UI for accessible interactive patterns (popovers, dialogs, etc.)
- Tailwind CSS for responsive styling
- shadcn/ui for copyable component library

## Installation & Usage

**Development Setup**:

```bash
# Install dependencies with Bun
bun install

# Start development server
bun run dev:web  # or bun run dev for all workspaces

# Build for production
bun run build

# Run tests
cd apps/web && bun test
```

**Prerequisites**:
- Bun 1.3.11 or later
- Node.js 18+ (Bun is a drop-in replacement for npm/yarn)
- TypeScript 6.0.2 (included in devDependencies)

**Production Deployment**:

```bash
bun run build  # Outputs optimized Vite bundle
wrangler deploy  # Deploys to Cloudflare Workers
```

**Note**: The current production site (opencut.app) runs the Classic version. The rewritten version is available for preview at new.opencut.app.

## Limitations and Caveats

1. **Rewrite In Progress** — The repository is explicitly stated to be "being rewritten from the ground up." Many announced features (Editor API, third-party plugins, Rust core, MCP server, headless mode, scripting tab) are planned but not yet fully implemented or documented.

2. **No Production Stability** — The rewrite has not yet been promoted to the main production site. Users seeking a stable, feature-complete video editor should continue using OpenCut Classic (available at opencut-app/opencut-classic or opencut.app).

3. **Plugin System Undocumented** — While "first-class third party plugins" are described as a key architectural goal, no public plugin API documentation, plugin development guide, or plugin examples are currently available. The plugin registration mechanism and extension points are not yet exposed.

4. **Architecture Documentation Sparse** — No ARCHITECTURE.md, design documents, or technical specifications are currently published. Understanding the internals requires reading source code and Copilot instructions.

5. **Rust Core Not Yet Public** — The rewrite mentions "Desktop, mobile, and browser from one codebase (Rust core)" but the Rust implementation is not visible in this repository; it may be in a separate private or unreleased repository.

6. **Desktop and Mobile Apps Not Available** — Only the web application (@opencut/web) is present in this repository. Desktop and mobile implementations are announced but not yet released.

7. **MCP Server Incomplete** — The MCP server for AI agents is listed as a coming feature but no implementation, schema, or usage guide is currently available.

## Relevance to Claude Code Development

OpenCut is highly relevant to Claude Code development in several ways:

1. **Plugin-First Architecture Pattern** — OpenCut's announced plugin-first design aligns with Claude Code's own plugin ecosystem. Understanding how OpenCut intends to expose extension points could inform improvements to Claude Code's plugin registration and interop mechanisms.

2. **MCP Server as Integration Layer** — OpenCut's plan to provide an MCP server for AI agents directly parallels Claude Code's MCP integration strategy. This provides a concrete example of how a complex desktop/web application can expose an agent-friendly interface.

3. **Cross-Platform Monorepo via Shared Rust Core** — The monorepo pattern with Turbo and the Rust core approach could inform Claude Code's own cross-platform considerations (Claude Code currently targets web and VS Code; a native desktop runtime could follow OpenCut's pattern).

4. **Type-Safe Plugin Contract** — OpenCut's use of TypeScript + Zod for runtime validation at component boundaries mirrors Claude Code's own stricter type safety goals for skill and hook contracts.

5. **Headless Mode and Scripting** — OpenCut's planned headless mode and in-editor scripting tab are architectural patterns worth studying for Claude Code's own automation and CLI tooling layers.

## References

- **GitHub Repository**: <https://github.com/opencut-app/opencut> (accessed 2026-06-18)
- **GitHub API**: repos/opencut-app/opencut metadata and contributors endpoint (accessed 2026-06-18)
- **README**: <https://github.com/opencut-app/opencut/blob/main/README.md> (accessed 2026-06-18)
- **LICENSE**: MIT, included in repository (accessed 2026-06-18)
- **Copilot Instructions**: .github/copilot-instructions.md — Ultracite configuration and code quality standards (accessed 2026-06-18)
- **Package Manifests**:
  - Root package.json (Turbo, Bun 1.3.11 configuration)
  - apps/web/package.json (React, TanStack, Tailwind, Zod dependencies)
  (accessed 2026-06-18)
- **Previous Version**: <https://github.com/opencut-app/opencut-classic>
- **Production Site**: <https://opencut.app> (runs OpenCut Classic)
- **Rewrite Preview**: <https://new.opencut.app>

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Pilot Shell](./pilot-shell.md) | coding-agents | Same architecture: MCP server for AI agents with plugin-first TypeScript monorepo |
| [Pi-Mono](./pi-mono.md) | coding-agents | Cross-platform monorepo pattern with unified LLM API and interactive CLI from single codebase |
| [Cline](./cline.md) | coding-agents | Autonomous coding agent with human-in-the-loop approvals; comparable agent architecture |
| [Maverick](./maverick.md) | coding-agents | Claude Code plugin with CLI wrapping; similar DevOps workflow integration approach |
| [1Code](./1code.md) | coding-agents | Electron desktop wrapper for coding agents with worktree isolation pattern |
| [Hyperagents](./hyperagents.md) | coding-agents | Multi-agent orchestration with MCP server integration for autonomous workflows |
| [Ruflo](../agent-frameworks/ruflo.md) | agent-frameworks | Multi-agent orchestration with 215+ MCP tools and 100+ specialized agents; MCP ecosystem alignment |
| [Compound Engineering Plugin](../research-agent-patterns/compound-engineering-plugin.md) | research-agent-patterns | 27-agent Claude Code plugin with Plan/Work/Review/Compound workflow; plugin-first architecture pattern |
| [OpenPencil](../ai-design-tools/open-pencil.md) | ai-design-tools | Open-source Figma alternative with native MCP server and 87+ AI tools; visual editor pattern with plugin system |

---

## Freshness Tracking

**Entry Created**: 2026-06-18
**Next Review**: 2026-09-18 (3 months)

### Confidence Summary

- **Identity/Metadata**: high — Official GitHub repository and API metadata
- **Key Statistics**: high — Sourced from GitHub API as of entry date
- **Problem Addressed**: high — Directly quoted from official README
- **Key Features**: high — Announced features directly quoted; web stack verified from package.json
- **Technical Architecture**: high — Monorepo structure, dependencies, and deployment verified from source files; Biome/Ultracite configuration from copilot-instructions.md
- **Installation & Usage**: medium — Development commands verified from package.json scripts; production note based on README; "Note" about Classic version directly sourced
- **Limitations**: medium — Rewrite status and feature gaps directly stated in README; plugin API undocumented is an observation from source; Rust core and desktop/mobile absence verified against repository contents
- **Relevance to Claude Code**: medium — Identified through architectural alignment with Claude Code's plugin and MCP strategy; speculative on future alignment

### Known Gaps

1. No Rust core implementation visible — cannot verify Rust architecture or performance characteristics
2. No plugin API documentation — cannot provide concrete extension point examples
3. No headless mode or MCP server implementation visible — cannot verify API contracts or capabilities
4. Limited git history (single commit) — repository appears freshly created or rebased; cannot assess development velocity or historical patterns
