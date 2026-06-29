---
title: Prompt Optimizer
resource_url: "https://github.com/linshenkx/prompt-optimizer"
created_date: 2026-06-18
freshness_date: 2026-06-18
next_review: 2026-09-18
license: "AGPL-3.0"
---

## Overview

**Prompt Optimizer** is a comprehensive AI prompt optimization tool designed to help users write better AI prompts and improve the quality of AI outputs. It provides four deployment methods: web application, desktop application, Chrome extension, and Docker deployment. The tool supports both text and image generation modes, with integrated support for multiple AI model providers including OpenAI, Gemini, DeepSeek, Grok, Zhipu AI, and others.

**Repository**: <https://github.com/linshenkx/prompt-optimizer>
**Latest Version**: v2.11.6 (released 2026-06-08)
**GitHub Stars**: 31,009 (as of 2026-06-18)
**License**: AGPL-3.0
**Language**: TypeScript
**Active Development**: Yes — last commit 2026-06-09

## Problem Addressed

Prompt Optimizer solves two critical challenges in AI-driven workflows:

1. **Prompt Quality**: Helps users transform vague or generic AI prompts into clearer, more structured requests that produce more accurate and useful AI outputs across different model sizes and providers.

2. **Multi-Platform Accessibility**: Provides prompt optimization capabilities across browser, desktop, Chrome extension, and self-hosted deployments, eliminating vendor lock-in and enabling both cloud and local-first usage patterns.

**Source**: README.md lines 23-27 — "Prompt Optimizer is where those prompts are optimized, tested, evaluated, and saved as reusable prompt assets."

## Key Statistics

- **31,009 GitHub Stars** (as of 2026-06-18)
- **Chrome Web Store Users**: Active adoption via official Chrome extension at `cakkkhboolfnadechdlgdcnjammejlna`
- **Docker Support**: Published to Docker Hub at `linshen/prompt-optimizer` with automated builds
- **Monorepo Structure**: Five independent packages with coordinated versioning (`@prompt-optimizer/core`, `@prompt-optimizer/ui`, `@prompt-optimizer/web`, `@prompt-optimizer/desktop`, `@prompt-optimizer/extension`, `@prompt-optimizer/mcp-server`)
- **Package Manager**: pnpm 10.6.1+ required; Node.js 22.x
- **Last Active**: 2026-06-09 (v2.11.6 release)

**Source**: GitHub API response (2026-06-18), package.json lines 1-6, CHANGELOG.md lines 5-7

## Key Features

### 1. Dual-Mode Prompt Optimization
- **System Prompt Optimization**: Refine system-level instructions for LLM behavior
- **User Prompt Optimization**: Enhance user-facing queries for clarity and precision
- **Multi-Round Iteration**: One-click optimization with automatic iterative improvements

**Source**: README.md §Core Features lines 47-48 — "Support for both system prompt optimization and user prompt optimization to meet different usage scenarios"

### 2. Analysis & Evaluation Pipeline
- **Analysis Mode**: Single-pass evaluation of optimization effectiveness
- **Compare Evaluation**: Multi-result comparison with structured scoring
- **Structured Evaluation**: JSON-backed evaluation artifacts for reproducibility

**Source**: README.md line 49 — "Supports analysis, single-result evaluation, and multi-result compare evaluation"

### 3. Multi-Model Integration
Integrated adapters for:
- **OpenAI** (GPT-4, text + image models)
- **Gemini** (text + image generation)
- **DeepSeek** (text models)
- **Grok** (text + image, including built-in Chrome AI)
- **Zhipu AI** (GLM series)
- **SiliconFlow** (hosted OSS models)
- **MiniMax** (M3 text generation)
- **Chrome Built-In AI** (local on-device models when available)

**Mechanism**: `ITextProviderAdapter` and `IImageProviderAdapter` interfaces enable pluggable model providers with independent connection schemas (API keys, base URLs, parameters). `TextAdapterRegistry` and `ImageAdapterRegistry` manage provider discovery and instantiation.

**Source**: README.md line 50 — "Support for mainstream AI models including OpenAI, Gemini, DeepSeek, Grok, Zhipu AI, SiliconFlow, MiniMax", packages/core/src/index.ts lines 39-70

### 4. Image Generation & Understanding
- **Text-to-Image (T2I)**: Generate images from text prompts
- **Image-to-Image (I2I)**: Transform and refine images from local files
- **Multi-Image Generation**: Use multiple reference images to constrain composition and semantics
- **Image Understanding**: Extract descriptive text and structural analysis from images

**Architecture**: `ImageService` manages T2I/I2I/multi-image workflows. `ImageStorageService` handles image persistence and format conversion (WebP, PNG, JPEG normalization). `ImageUnderstandingService` provides image-to-text extraction. Model providers expose image-specific parameters (size, style, quality).

**Source**: README.md §Advanced Features lines 62-69, packages/core/src/index.ts lines 84-120

### 5. Prompt Assets & Smart Favorites
- **Reusable Prompt Assets**: Save optimized prompts with version history
- **Media Attachment**: Embed images, examples, and reference materials
- **Source Binding**: Track prompt origins (manual, template, Prompt Garden import) without losing context
- **Resource-Aware Storage**: Complete backup/restore with all dependent resources

**Architecture**: `FavoriteManager` manages lifecycle (create, update, delete, export). `StorageGuards` enforce item-level and aggregate budget limits. Tags and metadata track provenance. Media is stored inline (data URLs) or as referenced `ImageRef` objects.

**Source**: README.md §Prompt Sources & Smart Favorites lines 71-76, packages/core/src/index.ts lines 252-267

### 6. Advanced Testing Mode
- **Context Variable Management**: Custom variables with batch replacement and preview
- **Multi-Turn Conversation Testing**: Test prompts in realistic multi-message dialogue scenarios
- **Function Calling Support**: Native integration with OpenAI and Gemini function-calling tools
- **Evaluation-Driven Rewrite**: Automatically refine prompts based on evaluation feedback

**Source**: README.md §Advanced Testing Mode lines 78-82

### 7. Multi-Platform Architecture
- **Web Application**: Pure frontend (Vite + Vue 3) deployed to Vercel or Cloudflare
- **Desktop Application** (Electron): Native cross-platform binary with auto-update
- **Chrome Extension**: Native browser integration at `cakkkhboolfnadechdlgdcnjammejlna`
- **Docker Deployment**: Multi-stage build supporting both HTTP and MCP server modes

**Deployment Paths**:
- Web: Vercel one-click or fork + import
- Desktop: GitHub Releases (`.exe`, `.dmg`, `.AppImage`)
- Extension: Chrome Web Store or manual load
- Docker: `docker run -p 8081:80 linshen/prompt-optimizer`

**Source**: README.md §Quick Start lines 86-188

### 8. MCP Protocol Support
Integrates with **Model Context Protocol** (MCP) for use with MCP-compatible AI applications like Claude Desktop.

**Architecture**: `@prompt-optimizer/mcp-server` package provides MCP server implementation. Deployed via separate Docker service at `/mcp` endpoint or standalone via `pnpm mcp:start`.

**Source**: README.md line 58 — "Supports Model Context Protocol (MCP), enabling integration with MCP-compatible AI applications like Claude Desktop"

### 9. Security & Privacy
- **Client-Side Processing**: No data sent to intermediate servers; users maintain direct control
- **Pure Frontend Storage**: All data persists locally in browser (IndexedDB/Dexie or LocalStorage)
- **Password Protection**: Optional authentication for self-hosted deployments
- **Environment-Variable API Keys**: API credentials configured at runtime, never embedded

**Source**: README.md lines 55, 57 — "Pure client-side processing with direct data interaction with AI service providers, bypassing intermediate servers" and "Password protection feature for secure deployment"

## Technical Architecture

### Core Package (`@prompt-optimizer/core`)

Exports unified service layer with **no UI dependencies**:

```typescript
// Template Management
export { TemplateManager, createTemplateManager } from './services/template/manager'
export { TemplateProcessor } from './services/template/processor'

// LLM Abstraction
export { LLMService, createLLMService } from './services/llm/service'
export { TextAdapterRegistry, createTextAdapterRegistry } from './services/llm/adapters/registry'

// Model Management
export { ModelManager, createModelManager } from './services/model/manager'

// Image Services
export { ImageService, createImageService } from './services/image/service'
export { ImageModelManager, createImageModelManager } from './services/image-model/manager'
export { ImageStorageService, createImageStorageService } from './services/image/storage'

// Prompt Management
export { PromptService } from './services/prompt/service'

// Evaluation & Comparison
export { EvaluationService, createEvaluationService } from './services/evaluation/service'
export { CompareService, createCompareService } from './services/compare/service'

// Data Layer
export { DataManager, createDataManager } from './services/data/manager'
export { FavoriteManager } from './services/favorite/manager'
export { PreferenceService, createPreferenceService } from './services/preference/service'

// Specialized Services
export { VariableExtractionService } from './services/variable-extraction/service'
export { VariableValueGenerationService } from './services/variable-value-generation/service'
export { ImageUnderstandingService } from './services/image-understanding/service'
```

**Service Layer Architecture**:
- **Adapters**: `TextAdapterRegistry` and `ImageAdapterRegistry` implement provider abstraction — each provider (OpenAI, Gemini, DeepSeek) is a pluggable adapter matching the `ITextProviderAdapter` or `IImageProviderAdapter` interface
- **Storage**: Factory pattern via `StorageFactory` supports multiple backends (Dexie for IndexedDB, LocalStorage, Memory, File for Electron)
- **IPC Proxies**: `ElectronLLMProxy`, `ElectronImageServiceProxy`, etc. serialize service calls across Electron main/renderer boundary

**Source**: packages/core/src/index.ts lines 1-291, packages/core/src/services/index.ts

### UI Package (`@prompt-optimizer/ui`)

Vue 3 + TypeScript component library built on Naive UI design system. Exports modular, reusable components:

```typescript
// Core Components
TestAreaPanel, TestInputSection, TestControlBar, TestResultSection
SelectWithConfig, ModelManagerUI, TemplateSelectUI, TemplateManagerUI
InputPanelUI, OutputDisplay, OutputDisplayFullscreen
MainLayoutUI, SidebarUI, HistoryPanelUI

// State Management
useNaiveTheme() — theme switching (light/dark)
installI18n(app) — bilingual support (English/Chinese)
```

**Architecture**: Composables for shared logic (conversation management, form state), stores for global state (Pinia), directives for DOM behaviors.

**Source**: packages/ui/README.md lines 1-120, packages/ui/src structure (components/, composables/, stores/, services/)

### Web Application (`@prompt-optimizer/web`)

Vue 3 + Vite frontend entry point. Consumes `@prompt-optimizer/core` (services) and `@prompt-optimizer/ui` (components).

**Build Pipeline**:

```bash
pnpm build:ui         # Compile UI library to ESM
pnpm build:web        # Vite build for static assets
pnpm dev:parallel     # Concurrent watch: ui + web dev server
```

**Environment Configuration**: API keys configured via `.env.local` or deploy-time `VITE_*` environment variables (Vercel/Cloudflare).

**Source**: package.json scripts, packages/web/

### Desktop Application (Electron)

Native cross-platform binary (Windows `.exe`, macOS `.dmg`, Linux `.AppImage`). Reuses web frontend + core services, adds Electron-specific features:

- **IPC Communication**: Main/renderer bridge for service layer (file I/O, native dialogs)
- **Auto-Update**: Built-in update checking and installation
- **Native Menu/Tray**: OS-level integration
- **CORS Bypass**: Direct API access without browser CORS constraints

**Build**: `pnpm build:desktop` → webpack → Electron builder → distributable

**Source**: packages/desktop/, README.md §Desktop Application lines 120-129

### Chrome Extension

Manifest V3 extension distributable from Chrome Web Store. Shares core + UI, adds:
- Background service worker
- Content scripts for in-page optimization
- Extension storage API

**Build**: `pnpm build:ext` → webpack → crx distribution

**Source**: packages/extension/, README.md §Chrome Extension lines 131-133

### MCP Server

Standalone MCP server enabling Prompt Optimizer integration with MCP-compatible applications (Claude Desktop, etc.).

**Architecture**: Express.js (or similar) server exposing MCP protocol endpoints. Runs as separate Docker service or standalone process.

**Source**: packages/mcp-server/, README.md line 58, MCP Deployment Guide docs/user/mcp-server_en.md

## Data Flow

```
User Input (web/desktop/ext)
    ↓
UI Components (@prompt-optimizer/ui)
    ↓
Vue Stores (Pinia)
    ↓
Service Layer (@prompt-optimizer/core)
    ├── PromptService
    ├── TemplateManager
    ├── LLMService → TextAdapterRegistry → Provider Adapter (OpenAI/Gemini/etc.)
    ├── ImageService → ImageAdapterRegistry → Provider Adapter
    ├── EvaluationService
    ├── DataManager → StorageFactory → Backend (Dexie/LocalStorage/File)
    └── FavoriteManager
    ↓
AI Provider APIs (direct from browser/Electron)
```

**Electron-Specific**: Renderer → IPC → Main Process → Service Layer → Provider APIs

**Storage**: All user data (prompts, favorites, history, preferences) stored locally via configurable backend — no server sync by default (optional remote backup via Data Manager).

**Source**: package.json build scripts, packages/core/src/services structure, Electron proxy architecture (electron-proxy.ts files)

## Installation & Usage

### Web (Recommended for Quick Start)

```bash
# Online (no installation)
https://prompt.always200.com

# Self-hosted Vercel
1. Fork: https://github.com/linshenkx/prompt-optimizer
2. Import to Vercel
3. Set env: ACCESS_PASSWORD, VITE_OPENAI_API_KEY, etc.
```

### Desktop

```bash
1. Download from: https://github.com/linshenkx/prompt-optimizer/releases
2. Install (auto-update supported):
   - Windows: *.exe
   - macOS: *.dmg
   - Linux: *.AppImage
```

### Chrome Extension

```bash
Install from: https://chromewebstore.google.com/detail/prompt-optimizer/cakkkhboolfnadechdlgdcnjammejlna
```

### Docker

```bash
docker run -d -p 8081:80 \
  -e VITE_OPENAI_API_KEY=sk-... \
  -e ACCESS_PASSWORD=secure_password \
  linshen/prompt-optimizer
# Access at http://localhost:8081
```

### Local Development

```bash
git clone https://github.com/linshenkx/prompt-optimizer.git
cd prompt-optimizer

# Install dependencies
pnpm install

# Start dev server
pnpm dev              # Web + UI watch
pnpm dev:desktop      # Web + Desktop watch
pnpm dev:fresh        # Full reset + reinstall + dev
```

**Source**: README.md §Quick Start lines 86-188, docs/developer/development.md

## Limitations & Caveats

1. **Storage Backend Limits**: IndexedDB (Dexie) has browser quotas (~50-100MB typical, varies by browser). Large media attachments in favorites can exhaust quota. Mitigation: export/import backups, use desktop app for higher limits.

2. **CORS in Web Mode**: Browser deployment (Vercel/Cloudflare) subject to CORS restrictions. Some LLM providers with strict CORS policies may not work. Workaround: use desktop app (no CORS), or deploy to own domain with CORS proxy.

3. **Image Format Support**: Normalized to WebP/PNG internally. JPEG, GIF, and exotic formats converted on ingest, may lose quality. Mitigated by `ImageInputCompatibilityOptions`.

4. **Multi-Tab Synchronization**: Web app data stored locally per tab (LocalStorage) or per origin (IndexedDB). Changes in one tab may not reflect immediately in another. Workaround: reload page, use desktop app for centralized state.

5. **Extension Permissions**: Chrome extension requests broad host permissions for content-script injection. Requires explicit user approval; some corporate deployments block extensions entirely.

6. **MCP Server Deployment**: Requires separate infrastructure (Docker container or Node.js process). No built-in load balancing or clustering; single-instance deployment recommended for stable integrations.

**Source**: README.md does not explicitly document limitations; findings derived from architecture analysis and feature scope

## Relevance to Claude Code Development

### 1. **Prompt Engineering as Development Practice**
Prompt Optimizer directly supports the core development workflow described in Claude Code's `.claude/CLAUDE.md` and prompt engineering skill documentation. When building agents and skills, developers use structured prompts; this tool helps optimize those prompts for better agent behavior.

**Use Case**: Before shipping a skill or agent with complex instructions, use Prompt Optimizer to iteratively refine the prompt text, test with target models, and evaluate clarity/completeness — ensuring the instruction artifact is production-ready.

**Source**: `.claude/CLAUDE.md` reference-notation guidelines, prompt-engineering rule compliance

### 2. **Multi-Model Evaluation**
The compare-evaluation feature aligns with the testing discipline required by `/dh:verify-done` and agent-review skills. Prompt Optimizer enables side-by-side testing against multiple models (OpenAI, Gemini, DeepSeek) to confirm prompt behavior is consistent across the target model set.

**Use Case**: Validate skill instructions against different Claude model tiers (Haiku, Sonnet, Opus) before committing to ensure consistent agent behavior regardless of model selection.

**Source**: README.md §Analysis & Evaluate Evaluation lines 49, CLAUDE.md model-selection rules

### 3. **Reproducible Examples & Favorites**
The smart favorites + asset versioning feature maps to the reproducibility requirements in `/dh:validation-protocol` and test-case documentation. Store a validated prompt + expected output as a reusable favorite, then reference it when refining similar prompts.

**Use Case**: Save a working agent instruction variant as a favorite with a reproducible test case; when iterating on a similar agent, import the favorite and adapt it — reducing iteration cycles.

**Source**: README.md §Prompt Sources & Smart Favorites lines 71-76

### 4. **Evaluation-Driven Development**
The structured evaluation pipeline (`analysis` → `evaluation` → `compare`) mirrors the T0/TN verification gates in SAM (Structured Agent-Managed) task workflows. Before shipping a major prompt refactor (e.g., in `/plugin-creator:subagent-refactorer`), use Prompt Optimizer to prove the new prompt produces better outputs than the baseline.

**Use Case**: When improving an agent instruction, run Prompt Optimizer's structured compare evaluation to quantify the improvement (e.g., "Before: 60% accuracy on edge cases, After: 85%"), then include the evidence in the commit message.

**Source**: CHANGELOG.md v2.7.0 "Structured compare evaluation", README.md lines 49

### 5. **Image-Based Prompt Design (AI Design Tools)**
For Claude Code users working with `/ai-design-tools` skills (visual design, wireframe generation, UI/UX refinement), Prompt Optimizer's text-to-image + image-to-image workflow enables rapid prototyping. Optimize a design brief → generate → refine → export.

**Use Case**: When a design-related skill requires image generation, delegate the iterative prompt refinement to Prompt Optimizer instead of embedding it in the skill logic.

**Source**: README.md §Image Generation Mode lines 62-69

## References

- **Official Website**: <https://always200.com> (project landing page)
- **Online Editor**: <https://prompt.always200.com> (live web app)
- **GitHub Repository**: <https://github.com/linshenkx/prompt-optimizer> (source code)
- **Documentation**: <https://docs.always200.com> (MkDocs bilingual docs)
- **Chrome Web Store**: <https://chromewebstore.google.com/detail/prompt-optimizer/cakkkhboolfnadechdlgdcnjammejlna>
- **Docker Hub**: <https://hub.docker.com/r/linshen/prompt-optimizer>
- **Prompt Garden** (companion resource): <https://garden.always200.com>
- **Development Docs**: docs/developer/development.md (in repository)
- **Deployment Guides**:
  - Vercel: docs/user/deployment/vercel_en.md
  - Cloudflare Pages: docs/user/deployment/cloudflare-pages_en.md
  - MCP Server: docs/user/mcp-server_en.md
- **Community Docs**:
  - DeepWiki: <https://deepwiki.com/linshenkx/prompt-optimizer>
  - ZRead: <https://zread.ai/linshenkx/prompt-optimizer>

**Repository Metadata** (verified 2026-06-18):
- License: AGPL-3.0
- Primary Language: TypeScript
- Package Manager: pnpm 10.6.1+
- Node.js: 22.x required
- Latest Release: v2.11.6 (2026-06-09)
- Topics: `ai-prompts`, `ai-tools`, `llm`, `prompt`, `prompt-engineering`, `prompt-optimization`, `prompt-testing`, `prompt-toolkit`, `prompt-tuning`

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [System Prompts & AI Tools](./system-prompts-ai-tools.md) | prompt-engineering | leaked system prompts and model configs for 30+ AI tools including Claude, Cursor, Windsurf; informs prompt analysis patterns and system instruction design |
| [Nano Banana Pro Prompting](./nano-banana-pro-prompting.md) | prompt-engineering | multi-model prompting techniques for Google Gemini; complementary strategy guide for prompt engineering across model families |
| [Prompt Engine](./prompt-engine.md) | prompt-engineering | SaaS prompt generator converting plain-language to professional prompts in <15s; alternative commercial tool in same domain |
| [ctxforge](./ctxforge.md) | prompt-engineering | protocol-based context engineering framework with 16 auto-loaded workflows; shares context-injection pattern with Prompt Optimizer's template system |
| [Claude Pilot](../developer-tools/claude-pilot.md) | developer-tools | quality-enforcement layer for Claude Code with TDD lifecycle hooks and persistent memory; enables prompt optimization via /spec workflow |
| [GrepAI](../developer-tools/grepai.md) | developer-tools | semantic code search and call graph analysis for AI agents; enables context-aware prompt refinement with codebase-grounded examples |
| [Ultra MCP](../mcp-ecosystem/ultra-mcp.md) | mcp-ecosystem | unified multi-model MCP interface (OpenAI/Gemini/Azure/Grok) with cost tracking and React dashboard; same provider abstraction pattern as Prompt Optimizer adapters |
| [Perplexity MCP Server](../mcp-ecosystem/perplexity-mcp-server.md) | mcp-ecosystem | real-time web search and reasoning MCP server; extends Prompt Optimizer with live information sources for grounding iterative refinement |
| [mcpskills-cli](../skill-generation-tools/mcpskills-cli.md) | skill-generation-tools | MCP-to-skill converter generating SKILL.md and polyglot call scripts; converts optimized prompts from Prompt Optimizer into reusable AI skills |
| [Dify](../agent-frameworks/dify.md) | agent-frameworks | open-source LLM application platform with visual workflow builder, RAG pipelines, 100+ model providers; integrates prompt optimization into end-to-end workflow systems |
| [TAKT](../research-agent-patterns/takt.md) | research-agent-patterns | multi-agent workflow engine with faceted prompting (persona/policy/knowledge/instruction); demonstrates advanced prompt decomposition pattern for specialized agent roles |
| [oh-my-opencode](../research-agent-patterns/oh-my-opencode.md) | research-agent-patterns | production-scale Claude Code orchestration with category-based model routing; shares multi-model evaluation pattern with Prompt Optimizer's compare feature |
| [Google Stitch](../ai-design-tools/google-stitch.md) | ai-design-tools | AI UI design tool generating app frontends from text/image prompts using Gemini 2.5; demonstrates image-to-code prompt optimization workflow |
| [Open Pencil](../ai-design-tools/open-pencil.md) | ai-design-tools | open-source Figma alternative with 87+ AI design tools and MCP server; extends Prompt Optimizer's image generation capabilities to design artifact creation |

---

## Freshness Tracking

**Last Verified**: 2026-06-18 (live repository inspection)

### Confidence by Section

| Section | Confidence | Notes |
|---------|------------|-------|
| Overview | high | README.md + GitHub metadata directly read |
| Problem Addressed | high | README.md official messaging |
| Key Statistics | high | GitHub API verified + CHANGELOG official |
| Key Features | high | README.md §Core Features + detailed code inspection of `packages/core/src/index.ts` |
| Technical Architecture | high | Source code read: `packages/core/src/index.ts`, `packages/ui/README.md`, monorepo structure verified via git |
| Installation & Usage | high | README.md §Quick Start + development.md official docs |
| Limitations & Caveats | medium | Derived from feature scope and code patterns; not explicitly documented in README |
| Relevance to Claude Code Development | medium | Inferred from alignment with CLAUDE.md methodology and skill ecosystem; verified through `/dh:verify-done` and agent patterns |
| References | high | All URLs verified as accessible (2026-06-18) |

### Next Review

**2026-09-18** (3 months from verification date)

**Trigger Review Earlier If**:
- Major version bump (v3.0.0+)
- Significant architecture refactor (MCP server becomes mandatory, storage backend changes)
- New deployment method or provider added
- License change or maintainer transition

**Source**: Research Curator Methodology §Freshness Tracking (fidelity-rules.md Rule 4)
