# Google Stitch

| Field         | Value                                                  |
| ------------- | ------------------------------------------------------ |
| Research Date | 2026-01-31                                             |
| Primary URL   | <https://stitch.withgoogle.com>                        |
| Announced     | Google I/O 2025 (May 20, 2025)                         |
| Version       | Beta (SaaS)                                            |
| License       | Proprietary (Google product)                           |
| Twitter       | [@stitchbygoogle](https://twitter.com/stitchbygoogle)  |

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

| Metric               | Value                           | Date Gathered |
| -------------------- | ------------------------------- | ------------- |
| Public GitHub Repo   | Not available (closed source)   | 2026-01-31    |
| Launch Date          | May 20, 2025 (Google I/O 2025)  | 2026-01-31    |
| Hosting Platform     | Google Cloud (App Engine)       | 2026-01-31    |
| AI Models Available  | Gemini 2.5 Pro, Gemini 2.5 Flash| 2026-01-31    |
| Pricing              | Free (beta)                     | 2026-01-31    |

Note: Google Stitch is a closed-source Google product. No public GitHub repository, npm package, or open-source components are available.

---

## Key Features

### AI-Powered UI Generation

- Text-to-UI: Describe desired interface in natural language
- Image-to-UI: Upload reference images to generate similar designs
- HTML/CSS output: Production-ready markup from AI generation
- Model selection: Choose between Gemini 2.5 Pro (higher quality) or Gemini 2.5 Flash (faster)

### Design Workflow Integration

- Figma export: Direct export of generated designs to Figma
- IDE compatibility: Expose code for refinement in development environments
- Element fine-tuning: Adjust individual UI components after generation
- Responsive design: Support for mobile and web layouts

### Input Methods

- Text prompts: Describe UI requirements in natural language
- Image prompts: Upload reference designs or mockups
- Screenshot annotation (upcoming): Mark changes on captured screens

### Example Use Cases (from Google demos)

- Mobile app UI for a bookworm/reading application
- Web dashboard for beekeeping data visualization
- Responsive layouts for various screen sizes

---

## Technical Architecture

### Stack Components (observed from production)

| Component      | Technology                              |
| -------------- | --------------------------------------- |
| Frontend       | Angular SPA (appcompanion-root)         |
| Backend        | Google App Engine (app-companion)       |
| AI Models      | Gemini 2.5 Pro, Gemini 2.5 Flash        |
| Authentication | Google Account OAuth                    |
| Analytics      | Google Tag Manager (G-1CD1CPGEYF)       |
| CDN            | Google Static (gstatic.com)             |

### Internal Codename

- Project codename: "Nemo" (observed in production JavaScript)

### Workflow

1. User authenticates via Google Account
2. User provides prompt (text description or image)
3. User selects AI model (Gemini 2.5 Pro or Flash)
4. Stitch generates UI preview and code
5. User refines elements or adjusts prompt
6. User exports to Figma or copies code for IDE

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

1. **Closed Source**: No codebase or API to study implementation details.

2. **Web-Only**: Cannot be integrated as a CLI tool, library, or MCP server.

3. **Narrow Scope**: Focused on UI generation only; not a general coding assistant.

4. **Google Account Required**: Authentication dependency limits automation.

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
| Google Stitch Homepage        | <https://stitch.withgoogle.com>                                                          | 2026-01-31 |
| TechCrunch Article            | <https://techcrunch.com/2025/05/20/google-launches-stitch-an-ai-powered-tool-to-help-design-apps/> | 2026-01-31 |
| Stitch Web Manifest           | <https://stitch.withgoogle.com/_/Nemo/manifest.json>                                     | 2026-01-31 |
| Twitter Account               | <https://twitter.com/stitchbygoogle>                                                     | 2026-01-31 |

**Research Method**: Information gathered from official homepage meta tags, TechCrunch exclusive coverage from Google I/O 2025, and production JavaScript bundle analysis. The site is an Angular SPA requiring authentication for full access.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | Beta (as of 2026-01-31)             |
| Launch Date        | May 20, 2025 (Google I/O 2025)      |
| Product Manager    | Kathy Korevec (Google)              |
| Next Review Date   | 2026-05-01                          |

**Review Triggers**:

- Exit from beta to general availability
- Public API or SDK release
- Addition of screenshot annotation feature
- New export format support (beyond Figma)
- Integration with other Google Workspace tools
- Pricing model announcement
