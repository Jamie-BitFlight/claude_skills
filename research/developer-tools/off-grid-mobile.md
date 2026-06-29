---
title: "Off Grid Mobile"
research_date: "2026-02-28"
source_url: "https://github.com/alichherawalla/off-grid-mobile"
github_url: "https://github.com/alichherawalla/off-grid-mobile"
version_at_research: "v0.0.58"
license: "MIT"
last_verified: "2026-02-28"
version_at_verification: "v0.0.58"
next_review: "2026-05-28"
---

## Overview

Off Grid Mobile is a privacy-first, fully offline AI suite for iOS and Android that runs LLM inference, image generation, voice transcription, and vision analysis entirely on the device. No data ever leaves the phone — there is no server, no cloud dependency, and no internet requirement after model download. Built with React Native and TypeScript, it exposes llama.cpp, Stable Diffusion, and Whisper capabilities through a polished mobile UI.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Cloud LLM services expose user data to third parties | All inference runs on-device; no data transmitted |
| Mobile LLM apps are single-capability (chat only) | Unified suite covering text, image generation, vision, and voice |
| On-device AI is hardware-gated and crashes on incompatible configs | SoC detection, GPU/flash-attention/KV-cache constraint enforcement, incompatibility badges |
| Image generation prompts require expertise | Automatic prompt enhancement via on-device text model |
| Offline AI on mobile requires technical setup | APK releases, App Store, and Play Store distribution with no-code model downloads |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 696 | 2026-02-28 |
| Downloads/month | Not published (APK download count: 362 for v0.0.58 APK) | 2026-02-28 |
| Contributors | 2 | 2026-02-28 |
| Latest Release | v0.0.58 | 2026-02-28 |
| Forks | 58 | 2026-02-28 |
| Open Issues | 13 | 2026-02-28 |
| Repository Created | 2026-01-29 | 2026-02-28 |

---

## Key Features

### Text Generation (LLM)

- Runs any GGUF model: Qwen 3, Llama 3.2, Gemma 3, Phi-4, and custom models
- Streaming responses with markdown rendering and thinking-mode support
- Performance: 15-30 tokens/second on flagship devices
- Configurable KV cache type: f16, q8_0, q4_0 — with cache-type nudge after first generation
- Bring-your-own GGUF file support

### Tool Calling

- Function calling for models that support it with automatic tool loop execution
- Built-in tools: web search, calculator, date/time retrieval, device information
- Runaway loop prevention guard
- Tool results rendered inline with clickable URLs

### Image Generation

- On-device Stable Diffusion with real-time preview
- NPU acceleration on Snapdragon devices: 5-10 seconds per image
- Core ML acceleration on iOS
- 20+ model options: Absolute Reality, DreamShaper, Anything V5, and more
- Automatic prompt enhancement via the active text model

### Vision

- Camera-to-query: point at objects and ask questions
- Supported models: SmolVLM, Qwen3-VL
- Inference time: approximately 7 seconds on flagship hardware
- Parallel mmproj download with main model

### Voice

- On-device Whisper integration for speech-to-text transcription
- Real-time processing, no audio leaves device

### Document Analysis

- PDF, code files, CSV attachments
- Native PDF text extraction on both platforms

---

## Technical Architecture

Off Grid Mobile is a React Native application (TypeScript 93.7%, Kotlin 3.5%, Swift 2.3%) wrapping three native inference engines:

- **llama.cpp** — GGUF model inference for text and vision; Android GPU and flash attention parameters are enforced at the app layer to prevent SIGSEGV/SIGABRT crashes from incompatible hardware configurations
- **Stable Diffusion** — image generation via native bindings with NPU backend selection per SoC (Qualcomm QNN vs. generic CPU/GPU path)
- **Whisper** — audio transcription running entirely on-device

Model downloads are managed by a background URLSession (iOS) / WorkManager (Android) system that supports parallel downloads of multimodal model components (e.g., main model + mmproj for vision). SoC detection at runtime selects the appropriate model variant and suppresses incompatible options in the UI.

Build requirements: Node.js 20+, JDK 17, Android SDK 36, NDK r27, Xcode 15+.

---

## Installation & Usage

```bash
# Clone and install dependencies
git clone https://github.com/alichherawalla/off-grid-mobile.git
cd off-grid-mobile
npm install

# Android
cd android && ./gradlew clean && cd ..
npm run android

# iOS
cd ios && pod install && cd ..
npm run ios
```

End users can install without building:

```text
- Apple App Store: search "Off Grid"
- Google Play Store: search "Off Grid"
- GitHub Releases: download app-release.apk from https://github.com/alichherawalla/off-grid-mobile/releases
```

---

## Relevance to Claude Code Development

### Applications

- Demonstrates a pattern for shipping LLM-backed features with zero cloud dependency — relevant when Claude Code skills need to work in air-gapped or privacy-restricted environments
- Shows how to gate AI features by hardware capability at runtime, preventing crashes from incompatible configurations — applicable to any agent that spawns compute-intensive subprocesses
- The tool-calling loop implementation (with runaway prevention) is a reference pattern for agent tool use with bounded execution

### Patterns Worth Adopting

- KV cache type selection exposed to user with sensible defaults and nudge UX — applicable to any configurable inference parameter in agent workflows
- SoC/hardware capability detection before feature exposure — prevents presenting options that will fail silently
- Background download management with cancellation and repair flow for large model assets
- Automatic prompt enhancement pipeline: simple user input passed through a fast model to generate a richer prompt before the primary model call

### Integration Opportunities

- The offline-first model management pattern could inform how Claude Code skills handle local model dependencies (e.g., embedding models, local validators) without assuming network access
- The test architecture (16 E2E flows covering tool calling, vision, document analysis) is a benchmark for what comprehensive agent feature testing looks like in a React Native context

---

## References

- [GitHub Repository — alichherawalla/off-grid-mobile](https://github.com/alichherawalla/off-grid-mobile) (accessed 2026-02-28)
- [GitHub API — Repository Metadata](https://api.github.com/repos/alichherawalla/off-grid-mobile) (accessed 2026-02-28)
- [GitHub Releases — v0.0.58](https://github.com/alichherawalla/off-grid-mobile/releases/tag/v0.0.58) (accessed 2026-02-28)
- [Community Slack](https://join.slack.com/t/off-grid-mobile/shared_invite/zt-3q7kj5gr6-rVzx5gl5LKPQh4mUE2CCvA) (accessed 2026-02-28)

---
