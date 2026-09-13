---
name: Google Stitch
description: Google Stitch is an AI-powered design tool that generates UI elements and code for mobile and web applications. Launched at Google I/O 2025, Stitch uses Google's Gemini 2.5 models to create app frontends from text prompts or images, outputting HTML/CSS and React code.
license: Proprietary (Google product)
metadata:
  topic: google-stitch
  category: ai-design-tools
  source_url: https://stitch.withgoogle.com
  version: "Beta (Stitch 2.0 as of Dec 2025)"
  verified: "2026-03-04"
  next_review: "2026-06-04"
---

## Overview

Google Stitch is an AI-powered design tool that generates UI elements and code for mobile and web applications. Launched at Google I/O 2025, Stitch uses Google's Gemini 2.5 models to create app frontends from text prompts or images, outputting HTML and CSS markup. The tool is positioned for rapid design ideation rather than as a full-fledged design platform like Figma or Adobe XD.

---

## Problem Addressed

| Problem                                      | Solution                                                         |
| -------------------------------------------- | ---------------------------------------------------------------- |
| UI design requires specialized skills        | AI generates professional UI from natural language descriptions  |
| Iteration from concept to prototype is slow  | Rapid generation of initial UI iterations in seconds             |
| Design-to-code handoff creates friction      | Direct code output (HTML/CSS) eliminates translation step        |
| Designers/developers use different tools     | Export to Figma + IDE-ready code bridges both workflows          |
| Communicating design changes is difficult    | Annotated screenshot feature (upcoming) enables visual feedback  |

---

## Key Statistics

| Metric                | Value                                      | Date Gathered |
| --------------------- | ------------------------------------------ | ------------- |
| Public GitHub Repo    | Not available (closed source)              | 2026-03-04    |
| Launch Date           | May 20, 2025 (Google I/O 2025)             | 2026-03-04    |
| Stitch 2.0 Release    | December 18, 2025                          | 2026-03-04    |
| Enterprise Rollout    | February 2026 (SOC2, team collaboration)   | 2026-03-04    |
| Hosting Platform      | Google Cloud (App Engine)                  | 2026-03-04    |
| AI Models Available   | Gemini 2.5 Pro (experimental), Gemini 2.5 Flash (standard) | 2026-03-04 |
| Code Output Formats   | HTML/CSS, React (free as of Dec 2025)      | 2026-03-04    |
| Pricing               | Free (beta, generation limits apply)       | 2026-03-04    |
| Origin                | Acquired from Galileo AI (2025)            | 2026-03-04    |

Note: Google Stitch is a closed-source Google product. No public GitHub repository, npm package, or open-source components are available.

---

## Key Features

### AI-Powered UI Generation

- Text-to-UI: Describe desired interface in natural language; Stitch generates full layout with components
- Image-to-UI: Upload whiteboard sketches, screenshots, or wireframes to generate corresponding digital UI
- Dual model modes: Standard Mode (Gemini 2.5 Flash, speed-optimized) and Experimental Mode (Gemini 2.5 Pro, higher fidelity)
- Multi-variant generation: Explore multiple layout variations from a single prompt

### Code Output

- HTML/CSS export: Clean, standards-compliant markup ready for direct use
- React code generation: Free React output added in Stitch 2.0 (December 2025)
- Production-ready: Code follows modern web standards for maintainability and scalability

### Design Workflow Integration

- Figma export: Single-click paste of entire interface into Figma with layout, components, and structure intact
- Interactive chat refinement: Adjust specific elements via follow-up prompts without regenerating the full UI
- Theme selectors: Change color palettes and visual style post-generation
- Responsive design: Support for mobile and web layouts

### Prototyping (added December 2025)

- Multi-screen prototyping: Stitch 2.0 introduced full prototype creation, moving beyond static screen generation
- Interactive flows: Link screens together for clickable prototype walkthrough

### Enterprise Features (February 2026)

- SOC2 compliance for enterprise data handling
- Team collaboration features
- API endpoints for custom integrations

### Input Methods

- Text prompts: Natural language UI requirements
- Image prompts: Reference designs, mockups, sketches
- Interactive chat: Iterative refinement after initial generation

### Example Use Cases (from Google demos)

- Mobile app UI for a reading/bookworm application
- Web dashboard for beekeeping data visualization
- Responsive layouts for various screen sizes

---

## Technical Architecture

### Stack Components (observed from production)

| Component      | Technology                                            |
| -------------- | ----------------------------------------------------- |
| Frontend       | Angular SPA (appcompanion-root)                       |
| Backend        | Google App Engine (app-companion)                     |
| AI Models      | Gemini 2.5 Pro (Experimental Mode), Gemini 2.5 Flash (Standard Mode) |
| Authentication | Google Account OAuth                                  |
| Analytics      | Google Tag Manager (G-1CD1CPGEYF)                     |
| CDN            | Google Static (gstatic.com)                           |

### Internal Codename

- Project codename: "Nemo" (observed in production JavaScript)

### Origin

- Built on technology acquired from Galileo AI (founded 2022, acquired by Google in 2025)
- Integrated into Google Labs ecosystem and powered by Gemini at acquisition

### Workflow

1. User authenticates via Google Account
2. User provides prompt (text description or image)
3. User selects AI model mode (Standard/Flash for speed, Experimental/Pro for fidelity)
4. Stitch generates UI preview with HTML/CSS and React code
5. User refines via chat, theme selectors, or variant generation
6. User exports to Figma or copies code for IDE
7. (Stitch 2.0+) Chain screens for multi-screen prototype flows

---

## Installation and Usage

Google Stitch is a web-based SaaS product. No local installation required.

### Getting Started

1. Visit <https://stitch.withgoogle.com>
2. Sign in with Google Account
3. Describe desired UI or upload reference image
4. Select Gemini model (Pro for quality, Flash for speed)
5. Generate and iterate on designs
6. Export to Figma or copy code

### No CLI or Local Tool

There is no command-line interface, API, or self-hosted option. The service operates entirely through the web interface.

### Requirements

- Google Account for authentication
- Modern web browser
- Active internet connection

---

## Comparison with Similar Tools

| Feature                  | Google Stitch  | v0 (Vercel) | Bolt.new  | Cursor    |
| ------------------------ | -------------- | ----------- | --------- | --------- |
| UI Generation            | Yes            | Yes         | Yes       | Limited   |
| Code Output              | HTML/CSS       | React/Next  | Multiple  | Multiple  |
| Image Input              | Yes            | Yes         | Yes       | No        |
| Figma Export             | Yes            | No          | No        | No        |
| Full App Development     | No             | Limited     | Yes       | Yes       |
| Model Selection          | Yes (Gemini)   | No          | No        | Yes       |
| Self-Hosted Option       | No             | No          | No        | Yes       |

---

## Relevance to Claude Code Development

### Direct Applications

1. **UI Prototyping Reference**: Demonstrates text-to-UI patterns that could inform Claude Code skill development for frontend generation tasks.

2. **Design Workflow Patterns**: Export-to-Figma workflow shows integration patterns between AI generation and professional design tools.

3. **Prompt Engineering Insights**: Text and image prompt handling for UI generation provides reference for multimodal prompt design.

### Patterns Worth Studying

1. **Model Selection UX**: Letting users choose between speed (Flash) and quality (Pro) models is a pattern applicable to agent tool selection.

2. **Iterative Refinement**: The fine-tune-after-generation workflow supports rapid iteration without starting over.

3. **Dual Output Formats**: Simultaneous visual preview and code output addresses both designer and developer needs.

4. **Screenshot Annotation** (upcoming): Visual feedback mechanism for modifications could inspire similar approaches in agentic workflows.

### Limitations for Claude Code

1. **Closed Source**: No codebase or API to study implementation details (though enterprise API endpoints were added in February 2026).

2. **Web-Only (currently)**: No CLI or local tool; PWA with offline capability planned for Q2 2026.

3. **Narrow Scope**: Focused on UI generation only; not a general coding assistant.

4. **Google Account Required**: Authentication dependency limits automation outside enterprise API tier.

### Integration Opportunities

1. **Workflow Inspiration**: "Describe UI, generate, refine, export" workflow is a clean pattern for agentic design tools.

2. **Competitive Benchmarking**: Compare UI generation quality when building similar capabilities.

3. **Figma Integration Pattern**: Export-to-Figma feature suggests integration patterns worth emulating.

---

## Related Google Tools

### Jules (AI Coding Agent)

Announced alongside Stitch at Google I/O 2025, Jules is Google's AI agent for code maintenance tasks:

- Bug fixing and code understanding
- Pull request creation on GitHub
- Node.js version upgrades and similar maintenance
- Currently in public beta
- Uses Gemini 2.5 Pro (multi-model support planned)

Jules complements Stitch by handling backend/infrastructure while Stitch focuses on frontend UI.

---

## References

| Source                        | URL                                                                                      | Accessed   |
| ----------------------------- | ---------------------------------------------------------------------------------------- | ---------- |
| Google Stitch Homepage        | <https://stitch.withgoogle.com>                                                          | 2026-03-04 |
| Google Developers Blog Launch | <https://developers.googleblog.com/stitch-a-new-way-to-design-uis/>                      | 2026-03-04 |
| TechCrunch Launch Article     | <https://techcrunch.com/2025/05/20/google-launches-stitch-an-ai-powered-tool-to-help-design-apps/> | 2026-03-04 |
| Stitch Web Manifest           | <https://stitch.withgoogle.com/_/Nemo/manifest.json>                                     | 2026-01-31 |
| Twitter Account               | <https://twitter.com/stitchbygoogle>                                                     | 2026-01-31 |
| Banani Review (features)      | <https://www.banani.co/blog/google-stitch-ai-review>                                     | 2026-03-04 |

**Research Method**: Information gathered from official Google Developers Blog announcement, TechCrunch exclusive coverage from Google I/O 2025, production homepage analysis, and third-party feature reviews. The site is an Angular SPA requiring authentication for full access. Stitch 2.0 details sourced from third-party review coverage of the December 18, 2025 update.

---

## Freshness Tracking

| Field                   | Value                                      |
| ----------------------- | ------------------------------------------ |
| Last Verified           | 2026-03-04                                 |
| Version at Verification | Beta (Stitch 2.0, released December 2025)  |
| Next Review Recommended | 2026-06-04                                 |

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [dark-design](./dark-design.md) | ai-design-tools | referenced by dark-design (ai-design-tools) |
| [godly](./godly.md) | ai-design-tools | referenced by godly (ai-design-tools) |
| [huashu-design](./huashu-design.md) | ai-design-tools | referenced by huashu-design (ai-design-tools) |
| [omma-build](./omma-build.md) | ai-design-tools | referenced by omma-build (ai-design-tools) |
| [open-pencil](./open-pencil.md) | ai-design-tools | referenced by open-pencil (ai-design-tools) |
| [prompt-optimizer](../prompt-engineering/prompt-optimizer.md) | prompt-engineering | referenced by prompt-optimizer (prompt-engineering) |
