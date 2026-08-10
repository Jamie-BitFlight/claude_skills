---
name: ghost-desk
research_date: 2026-03-13
source_url: https://www.ghost-desk.app/
version_at_research: v1.0
license: Proprietary (free during launch, paid tiers available)
freshness_tracking:
  last_verified: 2026-03-13
  version_at_verification: v1.0 (launch March 2026)
  next_review: 2026-06-13
  confidence_map: "Overview: high, Identity: high, Core Features: high, Architecture: medium, Limitations: high, Pricing: high, References: high"
---

# Ghost Desk

## Overview

Ghost Desk is a Windows-exclusive AI assistant overlay that remains invisible to screen-sharing, recording, and video conferencing software while providing real-time code analysis, voice transcription, and vision-based screenshot interpretation. Powered by Llama 3.3 70B or GPT-4o depending on tier, it uses Windows OS-level APIs (SetWindowDisplayAffinity) to exclude itself from all screen-capture pipelines, enabling developers to access AI assistance during live interviews, meetings, and screenshares without revealing the tool to viewers. (SOURCE: <https://www.ghost-desk.app/>, accessed 2026-03-13)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI assistance during technical interviews reveals to proctors that candidate is using AI tools | OS-level invisibility via SetWindowDisplayAffinity API hides overlay from all screen-capture pipelines (Zoom, Teams, OBS, etc.) |
| Need for code reference/help during live coding sessions visible to viewers | Invisible overlay allows real-time access to code analysis, documentation lookup, and problem-solving without visible changes to screen share |
| Distraction from primary task when using separate AI tool window | Always-on-top floating interface with keyboard-only activation (Ctrl+Shift+Space) integrates assistance without task-switching |
| Voice transcription and analysis requires separate tools or manual context-switching | Integrated voice input/output and screenshot analysis in single overlay reduces cognitive load |

---

## Identity and Metadata

**Exact Name**: GhostDesk
**Description**: A screen-share invisible AI assistant overlay that floats above any Windows application, providing chat, vision analysis, voice transcription, and code understanding without appearing during screen shares, recordings, or video calls.

**Version**: 1.0 (launched March 2026)
**Product Launch**: March 2026 (free during launch, no credit card required)

**Availability**:
- Windows 10 (build 19041 or later) 64-bit recommended
- Windows 11
- Minimum requirements: 4GB RAM, 500MB free disk space
- macOS and Linux: Not supported; "being explored but there is no release date yet"

---

## Key Features

### 1. Always-On-Top Floating Interface

Ghost Desk maintains a persistent overlay that remains above every application on Windows. Two UI modes are available:

- **Taskbar Mode**: Minimal persistent indicator at screen edge
- **Chat Panel Mode**: Full-size conversation interface

The overlay floats above browsers, IDEs (Visual Studio Code examples shown), terminals, design tools, and note-taking applications. Users can toggle visibility using global keyboard shortcuts regardless of which application has focus.

### 2. Screen-Share Invisibility

The core distinguishing feature uses Windows SetWindowDisplayAffinity API at the OS level to exclude the overlay from all screen-capture pipelines. This means:

- **Zoom screen shares**: Ghost Desk overlay not visible to viewers
- **Microsoft Teams**: Overlay excluded from team member views
- **Google Meet**: Invisible during calls
- **OBS / Windows Game Bar / streaming software**: Not captured in recordings
- **Taskbar**: No icon appears; overlay not visible in Alt+Tab switcher
- **Task Manager**: Process not listed or findable by name
- **Screenshots**: Screenshots taken via Print Screen or Windows Snip tool exclude the overlay

**Verification**: Ghost Desk publishes daily verification status across 14+ platforms (Zoom, Teams, Google Meet, Amazon Chime, Cisco Webex, Lark/Feishu, Slack, Discord, Skype, GoTo Meeting, RingCentral, BlueJeans, Whereby, Jitsi Meet) with last-updated timestamps (e.g., "Last updated 8hrs ago" as of website access on 2026-03-13).

The overlay remains click-through — when the user hovers or clicks on Ghost Desk, the system and active applications do not detect the input. No focus shifts occur.

### 3. AI Chat and Conversation

The chat interface accepts typed queries and maintains conversation context within a session. Answers stream token-by-token as they are generated. Follow-up questions and conversation refinement are supported.

**Example interaction shown on website**:
- User: "How do I debounce this event handler?"
- Ghost Desk: Returns a clean debounce utility function
- User: "Add a leading edge option?"
- Ghost Desk: Provides follow-up with leading-edge configuration

### 4. Voice Activation and Transcription

Ghost Desk accepts voice input with the following characteristics:

- Natural speech is transcribed directly by the system
- Smart silence detection filters background noise automatically
- No wake words or push-to-talk required — continuous listening available
- Voice output streams responses back to the user in speech form

### 5. Screenshot Analysis and Vision AI

Users can capture any rectangular region of the screen directly from within Ghost Desk. The overlay reads and analyzes:

- Source code snippets
- Document text
- Diagrams and visual content
- Tables and structured data

The vision AI provides instant explanations or analysis without switching to external tools.

**Example use cases shown**:
- Analyzing Python class definitions from VS Code editor
- Explaining LeetCode problem statements from browser
- Understanding complex asynchronous code patterns

### 6. Keyboard-Native Controls

All interaction is possible via global keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+Space | Toggle Ghost Desk visibility |
| Ctrl+Shift+C | Enable click-through mode |
| Ctrl+Shift+Q | Quick quit |

All shortcuts are fully customizable in settings.

### 7. Streaming and Context Management

- Answers stream in real-time token-by-token
- Conversation context maintained within a session
- Users can change direction, refine answers, or ask follow-ups naturally
- Session context is not persisted between application restarts (no persistent memory)

---

## Installation & Usage

**Installation time**: Under 1 minute

1. **Download and install** the lightweight Windows installer
   - No external dependencies or runtime installs required
   - All functionality bundled into installer
   - No .NET Framework, Python runtime, or additional prerequisites needed

2. **Configure** (30 seconds)
   - Set global hotkeys (Ctrl+Shift+Space, Ctrl+Shift+C, Ctrl+Shift+Q are defaults)
   - Choose overlay position on screen
   - No API keys, authentication tokens, or external configuration required
   - AI is built-in — ready to use immediately after installation

3. **Use immediately**
   - Press hotkey to activate overlay
   - Overlay remains private and off-screen during calls/recordings
   - No account creation or sign-up required for free tier

---

## AI Models and Backend

### Free Tier (Launch Offering)

Uses open-source models via Groq API for inference:

- **Chat**: Llama 3.3 70B via Groq
- **Vision/Screenshot Analysis**: Llama 4 Scout via Groq Vision
- **Voice Transcription**: Deepgram Nova-3

### Paid Tiers

Upgrade to OpenAI models for higher quality:

- **Chat**: GPT-4o
- **Voice Transcription**: OpenAI Whisper

**Configuration**: No API key setup required on any tier. All API keys and infrastructure are managed by Ghost Desk and abstracted from the user.

---

## Technical Architecture

### Window Display Affinity Implementation

Ghost Desk uses the Windows SetWindowDisplayAffinity API to implement screen-share invisibility:

**Source mechanism** (quoted from FAQ): "GhostDesk uses the Windows SetWindowDisplayAffinity API to exclude its overlay from all screen-capture pipelines. This means any app that captures the screen — Zoom, Teams, OBS, Windows Game Bar — simply won't include the GhostDesk window. It's an OS-level privacy feature built into Windows."

The API function excludes the window from:
- Desktop Windows Manager (DWM) composition
- Screen capture pipelines used by recording software
- Video conference screen-sharing stacks
- Task managers and process enumerations

### Dual UI Architecture

Two rendering modes indicate layered application design:

- **Taskbar/persistent indicator**: Low-resource state
- **Full chat panel**: Rich UI for interaction

UI switching is instant and controlled by global hotkeys.

### Multimodal Processing Pipeline

The architecture processes three input types:

1. **Text input** → Chat model (Llama 3.3 or GPT-4o) → Streamed text response
2. **Voice input** → Transcription (Deepgram or Whisper) → Chat model → Voice synthesis output
3. **Screen region** → Vision model (Llama 4 Scout or GPT-4o Vision) → Chat model → Text/voice response

---

## Limitations and Caveats

### Platform Constraints

- **Windows-only**: No native support for macOS or Linux. The FAQ explicitly states "macOS and Linux versions are being explored but there is no release date yet."
- **Windows version minimum**: Requires Windows 10 build 19041 or later, or Windows 11. Earlier Windows versions cannot use Ghost Desk due to SetWindowDisplayAffinity API availability (introduced in Windows 7 but requires Desktop Windows Manager compositing on modern builds).
- **RAM requirement**: Minimum 4GB RAM specified; performance on lower-spec systems untested.

### Functionality Limitations

- **No persistent session memory**: Conversation context exists only within a single Ghost Desk session. When the application is restarted, conversation history is not retained.
- **Groq API rate limits** (free tier): Llama model inference via Groq is subject to Groq's API rate limits, which may affect high-frequency query usage.
- **Deepgram transcription limits**: Voice transcription is provided by Deepgram API; quality and speed depend on network connectivity and Deepgram service availability.
- **Screenshot scope**: Users must manually select the region to analyze; there is no automatic code detection or document boundary recognition.

### Documented Behavioral Notes

- **Legal responsibility**: The FAQ states "Whether its use is appropriate in a given context depends on your organization's policies. You are responsible for understanding and complying with any applicable rules." Ghost Desk is explicitly described as "similar to a sticky note app or a second monitor" — legal use depends on organizational policy and context.
- **No built-in privacy encryption**: The overlay communication is abstracted from the user, but no explicit statement about end-to-end encryption is made. Data sent to Groq and Deepgram APIs is subject to their privacy policies.

### Unsupported Features

- Persistent conversation history
- Multi-session context retention
- Offline operation (requires live Groq/Deepgram API access)
- macOS/Linux support
- Custom AI model loading

---

## Pricing and Plans

**Launch Pricing** (March 2026):

| Plan | Cost | Billing |
|------|------|---------|
| Launch Free | $0 | Free during launch (no credit card) |
| 1 Month | $15/mo | Monthly renewal, cancel anytime |
| 3 Months | $35 | ~$12/mo, billed as one payment, 22% discount |
| 6 Months | $55 | ~$9/mo, billed as one payment, best value |
| Lifetime | $99 | One-time payment, all future updates |

**Feature Parity**: Every plan includes all features. Distinction between free and paid is not feature-gated but rather backend model quality (free = Llama via Groq, paid = GPT-4o).

**No Trial Lock**: Free tier accessible without account creation or credit card.

---

## Relevance to Claude Code Development

Ghost Desk is relevant to agents and developers in the following contexts:

### 1. Invisible Code Assistance During Live Development

Agents operating on a developer's screen during presentations or live coding sessions can maintain an AI copilot overlay that remains invisible to viewers. This enables real-time problem-solving during demonstrations without revealing the AI assistance.

### 2. Meeting Assistance Without Visual Distraction

During technical interviews, code reviews, or pair programming sessions conducted via video conference, an AI overlay can provide suggestions, code analysis, or documentation lookups without appearing on the shared screen.

### 3. Research and Context Gathering During Coding

The vision capabilities allow automated screenshot analysis of code or error messages, enabling agents to understand context without requiring manual prompt input. An agent could:
- Capture a stack trace and immediately receive error analysis
- Screenshot a class definition and request refactoring suggestions
- Capture a design mockup and generate implementation code

### 4. Privacy-Preserving Development Assistance

For developers working with sensitive codebases or proprietary systems, the overlay's screen-share invisibility ensures that AI assistance (and the model being used) does not leak information during client presentations or team demos.

### 5. AI Skill Development for Agents

The technical architecture (SetWindowDisplayAffinity, Groq/OpenAI backend abstraction, vision processing pipeline) provides a reference implementation for developers building AI-powered Windows overlays or invisible assistants.

---

## Freshness Tracking and Confidence

**Last Reviewed**: 2026-03-13
**Next Review Recommended**: 2026-06-13 (3 months)

**Confidence by Section**:

| Section | Confidence | Notes |
|---------|-----------|-------|
| **Identity/Metadata** | High | Official website directly accessed; version and launch date confirmed as of 2026-03-13 |
| **Core Features** | High | Feature descriptions extracted directly from official website with visual examples shown |
| **Installation & Setup** | High | Step-by-step procedure documented on official site with exact time claims ("under a minute", "30 seconds") |
| **AI Models and Backend** | High | Model names (Llama 3.3 70B, Llama 4 Scout, GPT-4o, Whisper, Deepgram Nova-3) explicitly stated in FAQ |
| **Architecture** | Medium | SetWindowDisplayAffinity mechanism quoted from FAQ; dual UI modes inferred from website but not formally documented |
| **Limitations** | High | Platform constraints (Windows 10 build 19041+, macOS/Linux "being explored") explicitly stated; legal disclaimer directly quoted |
| **Pricing** | High | All tier prices and billing models extracted from official /pricing page |
| **Use Cases** | Medium | Relevance to Claude Code development inferred from feature set; not confirmed by Ghost Desk team |
| **Daily Verification Status** | High | 14+ platforms listed with daily verification timestamps (as of 2026-03-13) |

**Confidence Reduction Factors**:
- Closed-source product; no GitHub repository or technical documentation available
- Launch status means long-term stability and roadmap features unknown
- "Daily verification" of screen-share invisibility not independently audited (relying on Ghost Desk's own verification system)
- Architecture section relies on API documentation inference rather than source code review

**Confidence Increase Factors**:
- Official website accessed in full
- Specific model names and Groq/Deepgram APIs documented
- FAQ provides explicit answers to technical and legal questions
- Pricing, system requirements, and platform support are unambiguous and directly stated

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Piebald](./piebald.md) | developer-tools | Cross-platform agentic AI desktop client with persistent sessions; complements Ghost Desk's invisible overlay with a GUI-first integration surface for parallel agents |
| [Yume](./yume.md) | developer-tools | Claude Code desktop GUI wrapper addressing similar pain points (flicker-free rendering, crash recovery, parallel agents); both provide invisible/background agent orchestration abstractions |
| [Pixel Agents](./pixel-agents.md) | developer-tools | VS Code extension visualizing Claude Code agent activity in real time; contrasts with Ghost Desk's invisibility goal by making agent activity highly visible |
| [Claude Conductor](./claude-conductor.md) | developer-tools | Claude Code plugin implementing structured workflows; addresses the same ecosystem (Claude Code assistance during development) with a workflow-first approach instead of invisible overlay |
| [Off-Grid Mobile](./off-grid-mobile.md) | developer-tools | Offline on-device Whisper integration (same voice transcription stack as Ghost Desk); mobile-first alternative to Ghost Desk's Windows platform for privacy-preserving AI assistance |
| [Google AI Studio](./google-ai-studio.md) | developer-tools | Browser-based multimodal AI playground with vision/screenshot analysis capabilities; provides similar vision analysis features via cloud (vs Ghost Desk's on-device approach) |

---

## References

1. **Official Website**: <https://www.ghost-desk.app/> (accessed 2026-03-13)
   - Main landing page with feature descriptions, interactive demos, pricing
   - FAQ section covering legality, AI models, platform support

2. **SetWindowDisplayAffinity API Documentation**: Microsoft Learn — Windows API Reference
   - <https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity>
   - Technical documentation on the core privacy mechanism Ghost Desk uses

3. **Groq API**: <https://groq.com/> (inference provider for free tier)
   - Llama 3.3 70B and Llama 4 Scout models documentation

4. **OpenAI Models**: <https://openai.com/api/pricing/> (for GPT-4o and Whisper on paid tiers)

5. **Deepgram Nova-3**: <https://deepgram.com/> (voice transcription provider for free tier)

6. **Product Hunt Discovery**: Referenced via URL parameter `?ref=producthunt` indicating Product Hunt launch channel (not directly accessed; launch details on main website)

---

## Research Notes

**Data Collection Approach**:
- Full website content read via direct HTTP request
- All feature claims extracted from official marketing materials and FAQ
- Specific model names, API providers, and pricing pulled directly from source
- Platform verification status observed from website's real-time dashboard
- No reverse engineering or third-party analysis used

**Gaps and Uncertainties**:
- Exact architecture beyond API-level integration unknown (closed source)
- Long-term performance and stability untested (early launch product)
- User adoption metrics and testimonials not gathered
- Competitive landscape limited to feature comparison (see related: ScreenGeany AI, OverlayAI, DeskClaw for competing invisible overlay solutions)
- Roadmap for macOS/Linux support unavailable

**Related Products for Comparison**:
- **Ghostpad**: Invisible notes for screen sharing (simpler use case)
- **ScreenGeany AI**: macOS-only hotkey-based screen analysis (platform-complementary)
- **DeskClaw**: Open-source desktop agent with file operations (different architecture)
- **OverlayAI**: Mac-only overlay with focus timer and transcript features (platform-complementary)
