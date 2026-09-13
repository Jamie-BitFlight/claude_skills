---
name: Lopaka
description: Lopaka is an open-source web-based graphics editor specifically designed for creating pixel-perfect graphics for embedded systems displays. It generates ready-to-use C/C++ code for popular embedded...
license: Apache License 2.0
metadata:
  topic: lopaka
  category: developer-tools
  source_url: https://lopaka.app
  github: sbrin/lopaka
  version: "v0.5"
  verified: "2026-02-20"
  next_review: "2026-05-20"
---

## Overview

Lopaka is an open-source web-based graphics editor specifically designed for creating pixel-perfect graphics for embedded systems displays. It generates ready-to-use C/C++ code for popular embedded graphics libraries including TFT_eSPI, U8g2, AdafruitGFX, and FlipperZero, enabling developers to design UI graphics visually and export them as uint8/uint32 variables without manual bitmap conversion.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Manual bitmap conversion for embedded displays is tedious and error-prone | Visual editor with automatic code generation for multiple graphics libraries |
| No unified tool supporting multiple embedded graphics frameworks | Single editor supporting TFT_eSPI, U8g2, AdafruitGFX, FlipperZero, M5GFX, LovyanGFX, and others |
| Difficult to preview graphics on embedded devices during development | FlipperZero live preview and multiple zoom scales for testing different screen sizes |
| Converting images to embedded-compatible formats requires manual processing | Drag-and-drop image import with automatic conversion to XBMP and C/C++ arrays |
| Designing pixel-perfect graphics for small screens (128x64, 240x320) is challenging | Pixel-perfect editor with various screen size presets and drawing tools |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 1,150 | 2026-02-20 |
| Forks | 78 | 2026-02-20 |
| Contributors | 13 | 2026-02-20 |
| Latest Release | v0.5 | 2025-02-25 |
| Language | C (frontend: Vue.js 3) | 2026-02-20 |
| Last Commit | 2026-01-12 | 2026-02-20 |
| Open Issues | 10 | 2026-02-20 |

---

## Key Features

### Visual Graphics Editor

- Pixel-perfect drawing tools for embedded screen design
- Multiple screen size presets (128x64, 240x320, and custom dimensions)
- Drawing shapes and tools (rectangle, circle, line, text, etc.)
- Layer-based editing with locking, alignment, and custom titles
- Zoom controls (25%, 50%, 100%, CTRL+ and CTRL- hotkeys)
- Undo/redo functionality
- Double-click to edit images in place

### Asset Management

- Drag-and-drop image import from desktop
- Multiple image import at once
- Custom font support from FreeFonts collection
- Auto-remembers last used font
- Draw and save icons for later reuse
- Byte array import for existing graphics
- Image editing directly within layers

### Code Generation

- Automatic C/C++ source code generation
- Platform-specific output for TFT_eSPI, U8g2, AdafruitGFX
- XBMP graphics format generation
- Font file includes in generated code
- Layer titles preserved in generated code comments
- Copy/paste code between sessions
- Importing code preserves existing layers

### Platform Support

- **TFT_eSPI** - Popular ESP32/STM32 graphics library
- **U8g2** - Universal monochrome graphics library
- **AdafruitGFX** - Adafruit's graphics library
- **FlipperZero** - With live preview support
- **Inkplate** - E-paper displays
- **Watchy** - E-paper smartwatch
- **M5GFX** - M5Stack graphics library
- **LovyanGFX** - High-performance graphics library

### Developer Experience

- Web-based (no installation required via lopaka.app)
- No registration required
- Docker and pnpm local installation options
- Platform-specific display lists for FlipperZero and Inkplate
- Keyboard shortcuts for common operations
- Two color options for monochrome displays (black/white)

---

## Technical Architecture

Lopaka is built as a web application using modern frontend technologies:

**Frontend Stack**:
- Vue.js 3 for reactive UI components
- Vite as the build tool for fast development
- Canvas API for pixel-perfect drawing operations
- Component-based architecture for editor tools

**Deployment**:
- Cloud version hosted on CloudFlare Pages (lopaka.app)
- Self-hosted via Docker Compose or pnpm
- Static site generation for offline usage

**Code Generation Pipeline**:
1. User creates graphics using visual editor
2. Layer data stored in internal representation
3. Export triggers platform-specific code generator
4. Outputs optimized C/C++ arrays and initialization code
5. Generated code includes proper header includes and data structures

**Supported Output Formats**:
- uint8_t arrays for monochrome displays
- uint32_t arrays for color displays
- XBMP format for cross-platform compatibility
- Platform-specific initialization code

---

## Installation & Usage

### Cloud Usage (No Installation)

<eg>
Visit https://lopaka.app
Start designing immediately with no registration
</eg>

### Local Installation - Docker

```bash
# Clone repository
git clone https://github.com/sbrin/lopaka.git
cd lopaka

# Run with Docker Compose
docker-compose up --build

# Access at http://localhost:5173
```

### Local Installation - pnpm

```bash
# Install pnpm if not available
npm install -g pnpm

# Clone and install dependencies
git clone https://github.com/sbrin/lopaka.git
cd lopaka
pnpm install

# Development server
pnpm dev

# Production build
pnpm build
```

### Basic Workflow

<eg>
1. Select target platform (TFT_eSPI, U8g2, AdafruitGFX, etc.)
2. Choose screen size or enter custom dimensions
3. Use drawing tools to create graphics:
   - Draw shapes (rectangle, circle, line)
   - Add text with supported fonts
   - Import images via drag-and-drop
   - Create layers and organize elements
4. Generate code using platform-specific export
5. Copy generated C/C++ code into Arduino/ESP32/STM32 project
6. Include necessary graphics library headers
7. Compile and flash to embedded device
</eg>

### Example Generated Code (TFT_eSPI)

```cpp
// Auto-generated by Lopaka
#include <TFT_eSPI.h>

const uint8_t myIcon[] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x18, 0x18, 0x00, 0x00, 0x18, 0x18, 0x00,
  // ... bitmap data
};

void drawIcon(TFT_eSPI &tft, int x, int y) {
  tft.drawBitmap(x, y, myIcon, 16, 16, TFT_WHITE);
}
```

---

## Relevance to Claude Code Development

### Applications

- **Developer tooling research**: Lopaka exemplifies domain-specific visual tooling that bridges design and code generation for specialized platforms
- **Code generation patterns**: Study how Lopaka generates platform-specific output from visual input for Claude Code code generation features
- **Web-based tooling**: Reference for building browser-based developer tools that require no installation
- **Multi-platform abstraction**: Learn from Lopaka's approach to supporting multiple embedded graphics libraries with a unified interface

### Patterns Worth Adopting

- **Visual-to-code workflow**: Transform visual designs into ready-to-use code, reducing manual translation errors
- **Platform-specific code generation**: Single source of truth (visual design) generates optimized code for multiple target platforms
- **No-registration cloud deployment**: Immediate accessibility via CloudFlare Pages without user barriers
- **Layer-based composition**: Organize complex designs into manageable layers with locking and alignment features
- **Inline editing**: Double-click to edit images directly within the canvas without external tools
- **Context preservation**: Importing code doesn't erase existing work, enabling iterative development

### Integration Opportunities

- **MCP server for embedded graphics**: Create MCP server that uses Lopaka's code generation patterns for embedded UI development assistance
- **Code-to-visual reverse engineering**: Integrate Lopaka-like visualization for understanding existing embedded graphics code
- **Template library**: Build reusable UI component library for common embedded display patterns (menus, icons, status bars)
- **AI-assisted design**: Use Claude Code to suggest optimal layouts for specific screen dimensions and use cases
- **Documentation generation**: Automatically document embedded UI components with screenshots and generated code examples

---

## References

- [Lopaka Official Website](https://lopaka.app) (accessed 2026-02-20)
- [Lopaka GitHub Repository](https://github.com/sbrin/lopaka) (accessed 2026-02-20)
- [Lopaka README](https://raw.githubusercontent.com/sbrin/lopaka/main/README.md) (accessed 2026-02-20)
- [Lopaka Release v0.5](https://github.com/sbrin/lopaka/releases/tag/0.5) (accessed 2026-02-20)
- [Lopaka Keyboard Shortcuts](https://github.com/sbrin/lopaka/wiki/Keyboard-shortcuts) (accessed 2026-02-20)
- [TFT_eSPI Library](https://github.com/Bodmer/TFT_eSPI) (accessed 2026-02-20)
- [U8g2 Library](https://github.com/olikraus/u8g2) (accessed 2026-02-20)
- [AdafruitGFX Library](https://github.com/adafruit/Adafruit-GFX-Library) (accessed 2026-02-20)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [tui-studio](./tui-studio.md) | developer-tools | referenced by tui-studio (developer-tools) |
