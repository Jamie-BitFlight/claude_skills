---
name: VERT - WebAssembly-Based File Converter
description: VERT is an open-source file conversion utility that uses WebAssembly to convert image, audio, and document files entirely in the browser, with no server-side processing. Video conversion is handled...
license: AGPL-3.0
metadata:
  topic: vert
  category: developer-tools
  source_url: https://github.com/vert
  github: VERT-sh/VERT
  version: "0.0.1"
  verified: "2026-02-08"
  next_review: "2026-05-08"
---

## Overview

VERT is an open-source file conversion utility that uses WebAssembly to convert image, audio, and document files entirely in the browser, with no server-side processing. Video conversion is handled by a separate self-hostable Rust daemon (`vertd`). The project supports 250+ file formats, has no file size limits, no ads, no tracking, and processes all non-video files on-device using WASM builds of FFmpeg, ImageMagick, and Pandoc.

---

## Problem Addressed

| Problem | VERT Solution |
|---------|---------------|
| Cloud file converters upload files to remote servers, creating privacy risks | All non-video conversion runs entirely on-device via WebAssembly |
| File converter services impose size limits and throttling | No file size limits; processing is local so no server bottleneck |
| Ad-driven file converters have poor UX and tracking | No ads, no tracking; optional Plausible analytics (privacy-focused, opt-out available) |
| Video conversion is too resource-intensive for browser WASM | Separate Rust-based daemon (`vertd`) handles video via native FFmpeg on host hardware |
| Self-hosting file conversion requires complex server infrastructure | Static site build (SvelteKit adapter-static) servable by any web server; Docker image available |
| Proprietary conversion tools lack transparency about file handling | Fully open source under AGPL-3.0; source code inspectable on GitHub |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 13,809 | 2026-02-08 |
| GitHub Forks | 713 | 2026-02-08 |
| GitHub Watchers | 44 | 2026-02-08 |
| Open Issues | 39 | 2026-02-08 |
| Contributors (top 5) | JovannMC (371), not-nullptr (219), RealmyTheMan (59), azurejelly (29), ofadev (6) | 2026-02-08 |
| Repository Created | 2024-11-11 | - |
| Last Push | 2026-02-05 | 2026-02-08 |
| Supported File Formats | 250+ | 2026-02-08 |
| vertd Stars | 391 | 2026-02-08 |

---

## Key Features

### Client-Side File Conversion

- **Image Conversion**: WebAssembly build of ImageMagick (`@imagemagick/magick-wasm`) for on-device image format conversion
- **Audio Conversion**: WebAssembly build of FFmpeg (`@ffmpeg/ffmpeg`, `@ffmpeg/util`) for on-device audio conversion
- **Document Conversion**: WebAssembly build of Pandoc (via `vert-wasm` package) for on-device document conversion
- **250+ Formats**: Broad format support across image, audio, and document categories
- **No File Size Limits**: Client-side processing eliminates server-imposed restrictions

### Video Conversion (Server-Side)

- **vertd Daemon**: Separate Rust-based FFmpeg wrapper (`github.com/VERT-sh/vertd`) for video conversion
- **Self-Hostable**: Users can run their own vertd instance for full privacy
- **Official Instance**: VERT hosts a public vertd instance with RTX 4000 Ada GPU acceleration
- **Automatic Cleanup**: Uploaded videos deleted after 1 hour or upon download

### Privacy and Transparency

- **No Tracking by Default**: No analytics unless opted in; uses Plausible (privacy-focused)
- **Open Source**: Full source available under AGPL-3.0
- **External Request Disable**: `PUB_DISABLE_ALL_EXTERNAL_REQUESTS=true` build flag eliminates all external requests except CDN-hosted FFmpeg WASM
- **Public Analytics**: Analytics dashboard publicly viewable at `ats.vert.sh/vert.sh`

### Progressive Web App

- **Installable PWA**: Web app manifest with mobile-web-app-capable flags
- **Responsive Design**: Tailwind CSS-based responsive layout for desktop and mobile
- **Dark Mode**: Theme toggle with system preference detection

### Deployment Options

- **Static Build**: SvelteKit adapter-static produces static files servable by any web server
- **Docker**: Official Dockerfile and docker-compose.yml; image available at `ghcr.io/vert-sh/vert:latest`
- **Build-Time Configuration**: Environment variables baked at build time for hostname, analytics, vertd URL, Stripe integration

### Internationalization

- **Paraglide.js**: Inlang-based i18n with `@inlang/paraglide-js` for multi-language support

---

## Technical Architecture

### Frontend Stack

<eg>
┌─────────────────────────────────────────────────────────┐
│                    VERT Web Application                  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              SvelteKit + TypeScript               │   │
│  │         (adapter-static, Vite build)              │   │
│  └─────────┬────────────────────────┬───────────────┘   │
│            │                        │                    │
│  ┌─────────v─────────┐  ┌─────────v──────────────┐    │
│  │   UI Framework     │  │   WASM Conversion       │    │
│  │                    │  │   Engines               │    │
│  │  - Svelte 5       │  │                          │    │
│  │  - Tailwind CSS   │  │  - @ffmpeg/ffmpeg        │    │
│  │  - Lucide Icons   │  │  - @imagemagick/         │    │
│  │  - Paraglide i18n │  │    magick-wasm           │    │
│  │                    │  │  - vert-wasm (Pandoc)    │    │
│  └────────────────────┘  └──────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Browser APIs                         │   │
│  │  - Web Workers (vite-plugin-top-level-await)     │   │
│  │  - WASI Shim (@bjorn3/browser_wasi_shim)        │   │
│  │  - File API (drag-and-drop, file input)          │   │
│  │  - client-zip (ZIP packaging for batch output)   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

          │ (video files only)
          v

┌─────────────────────────────────────────────────────────┐
│                  vertd (Rust Daemon)                      │
│                                                          │
│  - Native FFmpeg wrapper                                 │
│  - HTTP API on port 24153                                │
│  - Self-hostable or use official instance                │
│  - GPU-accelerated video conversion                      │
│  - License: GPL-3.0                                      │
└──────────────────────────────────────────────────────────┘
</eg>

### Conversion Pipeline

<eg>
User drops file(s)
       │
       ├── Image? ──> ImageMagick WASM ──> Converted file (in-browser)
       │
       ├── Audio? ──> FFmpeg WASM ──────> Converted file (in-browser)
       │
       ├── Document? ──> Pandoc WASM ──> Converted file (in-browser)
       │
       └── Video? ──> Upload to vertd ──> FFmpeg native ──> Download result
</eg>

### Key Dependencies

| Dependency | Purpose | Version |
|------------|---------|---------|
| `@ffmpeg/ffmpeg` | Audio/video conversion via WASM | 0.12.15 |
| `@imagemagick/magick-wasm` | Image conversion via WASM | 0.0.37 |
| `vert-wasm` | Pandoc document conversion via WASM | 0.0.2 |
| `@bjorn3/browser_wasi_shim` | WASI compatibility layer for browser | 0.4.2 |
| `client-zip` | Client-side ZIP file creation for batch downloads | 2.5.0 |
| `svelte` | UI framework | 5.43.14 |
| `vite-plugin-wasm` | Vite WASM loading support | 3.5.0 |
| `vite-plugin-top-level-await` | Top-level await support for WASM init | 1.6.0 |

---

## Installation and Usage

### Development Setup

```bash
# Prerequisites: Bun (https://bun.sh/)
git clone https://github.com/VERT-sh/VERT
cd VERT/
bun i
bun dev
# Open http://localhost:5173
```

### Production Build

```bash
bun run build
# Serve the `build/` directory with nginx or any static file server
```

### Docker Deployment

```bash
# Using GitHub Container Registry image
docker run -d --restart unless-stopped -p 3000:80 --name "vert" ghcr.io/vert-sh/vert:latest

# Or build locally with custom configuration
docker build -t vert-sh/vert \
    --build-arg PUB_ENV=production \
    --build-arg PUB_HOSTNAME=vert.example.com \
    --build-arg PUB_VERTD_URL=https://vertd.example.com \
    --build-arg PUB_DISABLE_ALL_EXTERNAL_REQUESTS=false .

docker run -d --restart unless-stopped -p 3000:80 --name "vert" vert-sh/vert
```

### Self-Hosted Video Conversion

<eg>
1. Download vertd from https://github.com/VERT-sh/vertd/releases
2. Run the vertd binary (HTTP server on port 24153 by default)
3. In VERT settings, set Instance URL to http://localhost:24153
</eg>

---

## Relevance to Claude Code Development

### Applications

1. **WebAssembly Architecture Pattern**: VERT demonstrates a production-grade pattern for running heavyweight native libraries (FFmpeg, ImageMagick, Pandoc) in the browser via WASM. This pattern is applicable to any scenario where Claude Code users need to build client-side processing tools.

2. **Privacy-First Design Reference**: The architecture of processing everything locally except when technically infeasible (video), with a self-hostable fallback for the server component, is a design pattern worth studying for privacy-sensitive tool development.

3. **SvelteKit Static Site Pattern**: VERT uses SvelteKit with adapter-static to produce a fully static site with complex client-side functionality. This is a reference for building installable PWAs with no server runtime.

4. **Docker Build-Time Configuration**: The pattern of baking environment variables at build time (`PUB_*` prefix) rather than runtime is a useful reference for static site deployments with configurable behavior.

### Patterns Worth Adopting

1. **WASM for Heavy Computation**: Compiling native C/C++/Rust libraries to WebAssembly for in-browser execution eliminates server costs and latency for file processing.

2. **Hybrid Local/Remote Processing**: Client-side by default, server-side only when WASM is insufficient (video), with the server component being self-hostable.

3. **Progressive Enhancement**: File conversion works without any server at all for images/audio/documents; video support is additive.

4. **Build-Time Feature Flags**: `PUB_DISABLE_ALL_EXTERNAL_REQUESTS` completely removes external dependencies, demonstrating a compile-time privacy toggle.

### Integration Opportunities

1. **File Format Conversion in Workflows**: Claude Code agents that need to convert files (images, documents) could reference VERT's WASM approach or use VERT directly as a local tool.

2. **Self-Hosted Utility**: Teams working with file conversion needs could deploy VERT internally alongside their development infrastructure.

3. **WASM Pattern Reference**: When building MCP servers or tools that need client-side heavy computation, VERT's WASM integration patterns (WASI shim, top-level await, worker threading) serve as a reference implementation.

### Considerations

1. **Not an AI/Agentic Tool**: VERT is a general-purpose file converter. Its relevance to Claude Code development is primarily as an architectural pattern reference (WASM, privacy-first, hybrid local/remote), not as a direct integration.

2. **Bun Dependency**: Development requires Bun rather than Node.js, which differs from most JavaScript project conventions.

3. **AGPL-3.0 License**: The copyleft license requires derivative works to also be AGPL-3.0 licensed and source-available. This has implications for any integration beyond standalone usage.

4. **Build-Time Configuration Only**: All configuration is baked at build time, not runtime. Changing settings requires rebuilding the Docker image or static site.

---

## References

1. **VERT Website** - <https://vert.sh> (accessed 2026-02-08)
2. **VERT GitHub Repository** - <https://github.com/VERT-sh/VERT> (accessed 2026-02-08)
3. **VERT README** - <https://raw.githubusercontent.com/VERT-sh/VERT/main/README.md> (accessed 2026-02-08)
4. **VERT FAQ** - <https://raw.githubusercontent.com/VERT-sh/VERT/main/docs/FAQ.md> (accessed 2026-02-08)
5. **VERT Getting Started** - <https://raw.githubusercontent.com/VERT-sh/VERT/main/docs/GETTING_STARTED.md> (accessed 2026-02-08)
6. **VERT Docker Documentation** - <https://raw.githubusercontent.com/VERT-sh/VERT/main/docs/DOCKER.md> (accessed 2026-02-08)
7. **VERT Video Conversion Documentation** - <https://raw.githubusercontent.com/VERT-sh/VERT/main/docs/VIDEO_CONVERSION.md> (accessed 2026-02-08)
8. **VERT package.json** - <https://raw.githubusercontent.com/VERT-sh/VERT/main/package.json> (accessed 2026-02-08)
9. **GitHub API - VERT Repository Metadata** - <https://api.github.com/repos/VERT-sh/VERT> (accessed 2026-02-08)
10. **GitHub API - VERT Contributors** - <https://api.github.com/repos/VERT-sh/VERT/contributors> (accessed 2026-02-08)
11. **GitHub API - VERT Languages** - <https://api.github.com/repos/VERT-sh/VERT/languages> (accessed 2026-02-08)
12. **vertd Repository** - <https://github.com/VERT-sh/vertd> (accessed 2026-02-08, via GitHub API)
13. **VERT Website HTML Source** - <https://vert.sh> (accessed 2026-02-08, for meta tags and footer commit reference 897ae56)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [pyscript](./pyscript.md) | developer-tools | referenced by pyscript (developer-tools) |
