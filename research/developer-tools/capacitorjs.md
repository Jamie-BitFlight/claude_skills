---
title: "Capacitor"
research_date: "2026-03-05"
source_url: "https://capacitorjs.com"
github_url: "https://github.com/ionic-team/capacitor"
version_at_research: "v8.1.0"
license: "MIT"
last_verified: "2026-03-05"
version_at_verification: "v8.1.0"
next_review: "2026-06-05"
---

## Overview

Capacitor is an open-source cross-platform native runtime that enables web developers to build iOS, Android, and Progressive Web Apps from a single JavaScript/HTML/CSS codebase. It acts as a bridge between web code and native device APIs, allowing web apps to access full native SDK functionality without abandoning web technologies. Maintained by the Ionic team, it positions itself as a modern successor to Apache Cordova with first-class support for contemporary web frameworks and tooling.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Web apps cannot access native device APIs (camera, GPS, haptics) | Plugin layer wraps native SDKs and exposes them as async JavaScript APIs |
| Building separate native apps per platform requires multiple codebases | Single web codebase compiles to iOS, Android, and PWA simultaneously |
| Cordova plugins and tooling are outdated and maintenance-heavy | Modern npm-based plugin system; native projects treated as source artifacts |
| Web developers lack iOS/Android expertise to ship to app stores | CLI handles native project scaffolding; `npx cap sync` keeps projects in sync |
| Custom native functionality requires deep platform knowledge | Plugin API allows writing Swift/Kotlin extensions exposed to JavaScript |
| Progressive Web Apps and app store apps require separate deployments | Same codebase targets app stores and mobile web via PWA support |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 15,200 | 2026-03-05 |
| Forks | 1,200 | 2026-03-05 |
| Watchers | 162 | 2026-03-05 |
| Used by (dependents) | 175,413 repos | 2026-03-05 |
| Total Releases | 178 | 2026-03-05 |
| Latest Release | v8.1.0 | 2026-02-11 |
| Repository Commits | 4,546 | 2026-03-05 |

SOURCE: [ionic-team/capacitor GitHub](https://github.com/ionic-team/capacitor) (accessed 2026-03-05)

---

## Key Features

### Cross-Platform Native Runtime

- Runs web apps natively on iOS, Android, and as Progressive Web Apps
- Single TypeScript/JavaScript codebase deploys to all three targets
- Native projects (Xcode, Android Studio) are treated as source artifacts, not build outputs — allowing full native customization

### Official Plugin API Suite (37+ plugins)

- Action Sheet, App Lifecycle, Background Runner, Barcode Scanner
- Browser, Camera, Clipboard, Cookies, Device info
- Dialog, Filesystem, File Transfer, File Viewer
- Geolocation, Google Maps, Haptics, HTTP client
- In-App Browser, Keyboard, Local Notifications, Motion (accelerometer)
- Network monitoring, Preferences (key-value storage), Privacy Screen
- Push Notifications, Screen Orientation, Screen Reader, Share
- Splash Screen, Status Bar, System Bars, Text Zoom, Toast
- Watch (experimental)

SOURCE: [Capacitor Official Plugins](https://capacitorjs.com/docs/apis) (accessed 2026-03-05)

### Custom Plugin Development

- Write custom native plugins in Swift (iOS) and Kotlin/Java (Android)
- JavaScript hooks auto-generated from native implementations
- Plugins can be shipped as npm packages for community distribution
- Compatible with existing Cordova plugins via compatibility layer

### Framework Agnostic Integration

- Drop-in compatible with any modern web framework: React, Angular, Vue, Svelte, Next.js, etc.
- No framework lock-in — works with any project that has a `package.json` and a built web asset directory

### Developer CLI

- `npx cap init` — initializes Capacitor config with app name and package ID
- `npx cap add ios/android` — scaffolds native platform projects
- `npx cap sync` — copies built web bundle to native projects and installs native dependencies
- `npx cap open ios/android` — opens native project in Xcode or Android Studio
- VS Code extension for GUI-based project management

---

## Technical Architecture

Capacitor consists of three runtime layers that cooperate to bridge web and native environments:

```text
┌─────────────────────────────────────────────┐
│               Web Layer                      │
│   React / Angular / Vue / Vanilla JS        │
│   @capacitor/core (JS runtime bridge)       │
└────────────────┬────────────────────────────┘
                 │  Plugin calls (JavaScript)
┌────────────────▼────────────────────────────┐
│          Capacitor Bridge                    │
│   WebView (WKWebView on iOS,                │
│            Android WebView)                  │
│   Message passing: JS ↔ Native              │
└────────────────┬────────────────────────────┘
                 │  Native method dispatch
┌────────────────▼────────────────────────────┐
│           Native Layer                       │
│   iOS: Swift / Obj-C plugins (CAPPlugin)    │
│   Android: Java / Kotlin plugins            │
│   Full access to platform SDKs              │
└─────────────────────────────────────────────┘
```

Key architectural decisions:

- **WebView host**: iOS uses WKWebView; Android uses the system WebView. Web code runs inside the WebView; native plugins run outside it.
- **Plugin dispatch**: JavaScript calls are serialized and passed through a bridge to the native plugin layer. Results return asynchronously as Promises.
- **Native project ownership**: Unlike Cordova, Capacitor does not regenerate native projects on each build. Developers check in their `ios/` and `android/` directories and modify them directly.
- **Monorepo structure**: Core repository uses Lerna/Nx and contains `core/`, `ios/`, `android/`, `cli/`, Cordova compatibility shims, and platform templates.
- **Languages by layer**: TypeScript (30.6%), Java (29.3%), Swift (23.1%), JavaScript (8.5%), Objective-C (7.7%)

---

## Installation & Usage

```bash
# Create a new Capacitor app
npm init @capacitor/app@latest

# Or add to an existing web project
npm i @capacitor/core
npm i -D @capacitor/cli

# Initialize config (prompts for app name and package ID)
npx cap init

# Install platform packages
npm i @capacitor/ios @capacitor/android

# Scaffold native projects
npx cap add ios
npx cap add android

# After each web build, sync to native projects
npx cap sync

# Open in native IDE
npx cap open ios      # opens Xcode
npx cap open android  # opens Android Studio
```

```typescript
// Using an official plugin (Geolocation example)
import { Geolocation } from '@capacitor/geolocation';

const position = await Geolocation.getCurrentPosition();
console.log(position.coords.latitude, position.coords.longitude);
```

```typescript
// Using Local Notifications plugin
import { LocalNotifications } from '@capacitor/local-notifications';

await LocalNotifications.schedule({
  notifications: [{
    title: "Reminder",
    body: "Don't forget your task!",
    id: 1,
    schedule: { at: new Date(Date.now() + 1000 * 60) },
  }]
});
```

```typescript
// Camera plugin
import { Camera, CameraResultType } from '@capacitor/camera';

const photo = await Camera.getPhoto({
  resultType: CameraResultType.Uri,
  quality: 90,
});
console.log(photo.webPath);
```

---

## Relevance to Claude Code Development

### Applications

- Capacitor enables web-first development teams to ship to app stores without native expertise — a pattern relevant to AI tool UIs that need mobile distribution
- The plugin bridge architecture (JS-to-native via async message passing) mirrors patterns used in MCP tool call dispatch
- Background Runner plugin enables JS execution outside the main thread — relevant for agents running background tasks on mobile

### Patterns Worth Adopting

- **Treat native projects as source artifacts**: Capacitor's decision to check in `ios/` and `android/` (rather than regenerating them) prevents silent config drift — the same principle applies to generated agent config files
- **Version-tagged npm distribution (`latest-X`)**: Capacitor's `@capacitor/camera@latest-7` tagging convention for major-version-pinned installs is a clean pattern for plugin versioning in Claude Skills
- **Plugin-as-npm-package**: Capacitor's model of packaging native extensions as npm modules with auto-generated JS stubs is directly analogous to MCP server packaging

### Integration Opportunities

- Claude Code skills that target mobile app development workflows can reference Capacitor as the recommended cross-platform bridge
- When building Claude-powered mobile apps, Capacitor is the lowest-friction path from a web-based Claude UI to a native iOS/Android deployment
- The `@capacitor/preferences` plugin (key-value storage) provides a simple persistence layer for mobile Claude apps that need to store session state or settings

---

## References

- [Capacitor Official Site](https://capacitorjs.com) (accessed 2026-03-05)
- [Getting Started Documentation](https://capacitorjs.com/docs/getting-started) (accessed 2026-03-05)
- [Official Plugins API Reference](https://capacitorjs.com/docs/apis) (accessed 2026-03-05)
- [Capacitor Plugins Overview](https://capacitorjs.com/docs/plugins) (accessed 2026-03-05)
- [ionic-team/capacitor GitHub Repository](https://github.com/ionic-team/capacitor) (accessed 2026-03-05)

---
