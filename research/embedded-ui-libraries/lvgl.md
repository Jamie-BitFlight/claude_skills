---
title: "LVGL (Light and Versatile Graphics Library)"
research_date: "2026-03-05"
source_url: "https://lvgl.io"
github_url: "https://github.com/lvgl/lvgl"
version_at_research: "v9.5.0"
license: "MIT License"
last_verified: "2026-03-05"
version_at_verification: "v9.5.0"
next_review: "2026-06-05"
---

## Overview

LVGL is a free, open-source embedded graphics library written in C that provides everything needed
to create rich graphical UIs on microcontrollers and microprocessors. It runs on any MCU, MPU, OS,
or display type with minimal hardware requirements (64 kB Flash, 16 kB RAM minimum), making it the
most widely adopted embedded UI library. The project is vendor-neutral and royalty-free, with
official hardware partnerships covering Arm, NXP, STMicroelectronics, Espressif, Renesas, and
Texas Instruments.

SOURCE: [LVGL Homepage](https://lvgl.io) (accessed 2026-03-05)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Embedded displays need a GUI framework that fits in kilobytes, not megabytes | LVGL operates with as little as 64 kB Flash and 16 kB RAM, with a typical footprint of 180 kB Flash and 48 kB RAM for a feature-rich UI |
| Hardware-specific GUI toolkits lock developers into one vendor or OS | LVGL is hardware-independent: one driver function (pixel array copy) is the only platform requirement |
| Creating smooth, animated UIs on MCUs requires complex graphics programming | 30+ built-in widgets, CSS-like styles, flexbox/grid layouts, and animation APIs abstract rendering complexity |
| MicroPython developers need GUI access without C knowledge | `lv_binding_micropython` auto-generates Python bindings from LVGL's C headers, exposing the full API in Python |
| Iterating on embedded UI design requires physical hardware | PC simulator ports (SDL2-based) allow full LVGL development and testing on Linux/macOS/Windows |
| Fragmented RTOS ecosystems require UI porting work per OS | LVGL integrates with bare-metal, FreeRTOS, Zephyr, RT-Thread, NuttX, and Linux via a tick + timer handler interface |

SOURCE: [LVGL Introduction](https://docs.lvgl.io/9.2/intro/index.html) (accessed 2026-03-05),
[LVGL Homepage](https://lvgl.io) (accessed 2026-03-05)

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 22,884 | 2026-03-05 |
| GitHub Forks | 4,055 | 2026-03-05 |
| Contributors | 687 | 2026-03-05 |
| Open Issues | 120 | 2026-03-05 |
| Latest Release | v9.5.0 | 2026-03-05 |
| Release Date | 2026-02-18 | 2026-03-05 |
| Repository Age | Since 2016-06-08 | 2026-03-05 |
| MicroPython Binding Stars | 338 | 2026-03-05 |

SOURCE: [GitHub API: lvgl/lvgl](https://api.github.com/repos/lvgl/lvgl) (accessed 2026-03-05),
[GitHub API: releases/latest](https://api.github.com/repos/lvgl/lvgl/releases/latest) (accessed 2026-03-05),
[GitHub contributors pagination header](https://api.github.com/repos/lvgl/lvgl/contributors?per_page=1&anon=true) (accessed 2026-03-05)

---

## Key Features

### Widget Library

- 30+ built-in widgets: `lv_label`, `lv_button`, `lv_slider`, `lv_chart`, `lv_table`,
  `lv_arc`, `lv_animimg`, `lv_bar`, `lv_buttonmatrix`, `lv_calendar`, `lv_canvas`,
  `lv_checkbox`, `lv_dropdown`, `lv_image`, `lv_imagebutton`, `lv_keyboard`, `lv_led`,
  `lv_line`, `lv_list`, `lv_lottie`, `lv_menu`, `lv_msgbox`, `lv_roller`, `lv_scale`,
  `lv_span`, `lv_spinbox`, `lv_spinner`, `lv_switch`, `lv_tabview`, `lv_textarea`,
  `lv_tileview`, `lv_win`
- Each widget exposes part/state selectors for precise style targeting
  (e.g., `LV_PART_INDICATOR | LV_STATE_PRESSED`)

SOURCE: [LVGL Widgets index](https://docs.lvgl.io/9.2/widgets/index.html) (accessed 2026-03-05)

### Rendering and Graphics

- Anti-aliasing, opacity, smooth scrolling, and animation out of the box
- Single frame buffer operation even with layered transparency effects
- Support for 16-bit and 24-bit color TFTs, monochrome, grayscale, and LED matrix displays
- Hardware GPU acceleration support: Arm2D + Helium (Cortex-M), VG-Lite + PXP (NXP i.MX RT),
  Dave2D (Renesas), ST ChromART (STM32)
- Custom GPU draw backend via pluggable draw layer API

SOURCE: [LVGL Introduction](https://docs.lvgl.io/9.2/intro/index.html) (accessed 2026-03-05),
[LVGL Homepage](https://lvgl.io) (accessed 2026-03-05)

### Styling System

- CSS-inspired: 100+ style properties covering background, border, font, shadow, padding,
  transform, and more
- Styles stored as `lv_style_t` structs and applied per-part and per-state
- Theme system with built-in dark/light themes
- Web-inspired layout managers: Flexbox and Grid layout engines

SOURCE: [LVGL Quick Overview — Styles](https://docs.lvgl.io/9.2/get-started/quick-overview.html) (accessed 2026-03-05)

### Input Device Support

- Touchpad (capacitive and resistive), mouse pointer, keyboard, rotary encoder, button matrix
- Input device abstraction layer: register any input source via `lv_indev_create()`
- Group system for keyboard/encoder navigation between focusable widgets

SOURCE: [LVGL Introduction](https://docs.lvgl.io/9.2/intro/index.html) (accessed 2026-03-05),
[LVGL Porting — Input device interface](https://docs.lvgl.io/9.2/porting/index.html) (accessed 2026-03-05)

### Multi-Display and Multi-Language

- Multiple TFT and monochrome displays simultaneously on the same MCU
- UTF-8 text rendering with multi-language support
- Right-to-left (RTL) script direction support
- Bidirectional text support for Arabic/Hebrew

SOURCE: [LVGL Introduction](https://docs.lvgl.io/9.2/intro/index.html) (accessed 2026-03-05)

### OS and RTOS Integration

- Bare-metal (superloop), FreeRTOS, RT-Thread, Zephyr, NuttX, px5RTOS, Linux, Windows, macOS
- Thread-safety via mutex: `lv_timer_handler()` call must be protected in RTOS tasks
- External memory (PSRAM) and GPU supported but not required
- Tick source: either call `lv_tick_inc(x)` every x ms, or register `lv_tick_set_cb()`

SOURCE: [LVGL Quick Overview](https://docs.lvgl.io/9.2/get-started/quick-overview.html) (accessed 2026-03-05),
[LVGL Porting — OS and interrupts](https://docs.lvgl.io/9.2/porting/index.html) (accessed 2026-03-05)

### MicroPython Binding

- Repository: [lvgl/lv_binding_micropython](https://github.com/lvgl/lv_binding_micropython)
  (338 stars, 190 forks as of 2026-03-05)
- Auto-generated Python bindings from LVGL C headers using `pycparser`; full LVGL API
  available as `import lvgl as lv`
- Ports available: ESP32 (ILI9341/ILI9342/XPT2046/FT6336 drivers), Raspberry Pi Pico,
  Unix (SDL2 window), Windows, M5Stack Core2
- Display and input drivers can be implemented as pure Python, pure C, or hybrid
  (critical flush path in C, init in Python)
- Event callbacks use Python closures: `btn.set_event_cb(lambda obj, event: ...)`

SOURCE: [LVGL MicroPython binding README](https://github.com/lvgl/lv_binding_micropython) (accessed 2026-03-05)

### Developer Tooling Ecosystem

- **SquareLine Studio**: commercial drag-and-drop UI designer that exports LVGL C code
- **PC simulator**: SDL2-based simulator runs the full LVGL stack on Linux/macOS/Windows
  without any embedded hardware
- **lv_port_* repositories**: ready-to-use port projects for popular boards
  (search `github.com/lvgl?q=lv_port_`)
- **Arduino, PlatformIO, Tasmota** framework integrations
- **Espressif IDF component manager**: `idf.py add-dependency lvgl`

SOURCE: [LVGL Get Started](https://docs.lvgl.io/9.2/get-started/index.html) (accessed 2026-03-05),
[LVGL Homepage](https://lvgl.io) (accessed 2026-03-05)

---

## Technical Architecture

LVGL's runtime model centers on four integration points the host application must provide:

1. **Tick source** — call `lv_tick_inc(ms)` periodically (1–10 ms) or register a callback
   via `lv_tick_set_cb()`. LVGL uses this for animation, input debounce, and timers.

2. **Display driver** — register an `lv_display_t` with a flush callback. The flush callback
   receives a pixel buffer and destination rectangle; it must copy pixels to the physical
   display and call `lv_display_flush_ready()`.

3. **Input device driver** — register `lv_indev_t` with a read callback that reports pointer
   position/state, key events, or encoder direction.

4. **Timer handler** — call `lv_timer_handler()` in the main loop (or a dedicated RTOS task)
   at roughly 5 ms intervals. This drives all rendering, animations, and event dispatch.

The rendering pipeline uses a partial draw buffer (recommended: 1/10 screen pixels) to avoid
requiring a full frame buffer in MCU RAM. LVGL renders dirty regions into the buffer and calls
the flush callback once per dirty region. A full frame buffer in MCU SRAM or an external
display controller is also supported for double-buffering with DMA transfer.

The widget object tree inherits the `lv_obj_t` base object. Every widget is a child of a
screen (`lv_screen_active()`), forming a parent-child hierarchy where layout, events, and
style cascading follow the tree structure.

```text
lv_init()
   |
   +-- lv_display_create(width, height)
   |      |-- set draw buffer (lv_display_set_buffers)
   |      +-- set flush callback (lv_display_set_flush_cb)
   |
   +-- lv_indev_create()  [optional]
   |      +-- set read callback (lv_indev_set_read_cb)
   |
   +-- Widget tree built on lv_screen_active()
   |      lv_obj_t  (screen)
   |        +-- lv_obj_t  (container)
   |               +-- lv_label_t, lv_button_t, ...
   |
   +-- Main loop:
          lv_tick_inc(5);       // every 5 ms
          lv_timer_handler();   // drives rendering + events
```

SOURCE: [LVGL Quick Overview — Add LVGL into your project](https://docs.lvgl.io/9.2/get-started/quick-overview.html) (accessed 2026-03-05),
[LVGL Porting](https://docs.lvgl.io/9.2/porting/index.html) (accessed 2026-03-05)

---

## Installation & Usage

### C Project (copy-based, no package manager)

```bash
git clone https://github.com/lvgl/lvgl.git
# Copy lvgl/ into your project tree
cp lvgl/lv_conf_template.h lv_conf.h
# Edit lv_conf.h: set #if 0 -> #if 1, configure LV_COLOR_DEPTH
```

### ESP32 via IDF Component Manager

```bash
idf.py add-dependency lvgl
```

### Zephyr (west manifest)

```yaml
# west.yml
manifest:
  projects:
    - name: lvgl
      url: https://github.com/lvgl/lvgl
      revision: v9.5.0
```

### Minimal C initialization

```c
#include "lvgl/lvgl.h"

// 1. Initialize LVGL
lv_init();

// 2. Create display and set draw buffer (1/10 screen)
static lv_color_t buf[MY_HOR_RES * MY_VER_RES / 10];
lv_display_t *disp = lv_display_create(MY_HOR_RES, MY_VER_RES);
lv_display_set_buffers(disp, buf, NULL, sizeof(buf),
                       LV_DISPLAY_RENDER_MODE_PARTIAL);
lv_display_set_flush_cb(disp, my_flush_cb);

// 3. Create a label on the active screen
lv_obj_t *label = lv_label_create(lv_screen_active());
lv_label_set_text(label, "Hello world");
lv_obj_set_style_text_color(lv_screen_active(),
                             lv_color_hex(0xffffff), LV_PART_MAIN);
lv_obj_align(label, LV_ALIGN_CENTER, 0, 0);

// 4. Main loop (bare-metal)
while (1) {
    lv_tick_inc(5);
    lv_timer_handler();
    my_delay_ms(5);
}
```

SOURCE: [LVGL Quick Overview](https://docs.lvgl.io/9.2/get-started/quick-overview.html) (accessed 2026-03-05)

### MicroPython on ESP32 (ILI9341 + XPT2046)

```python
import lvgl as lv

# Register display driver (ILI9341)
from ili9XXX import ili9341
disp = ili9341()

# Register touch driver (XPT2046)
from xpt2046 import xpt2046
touch = xpt2046()

# Create UI
scr = lv.screen_active()
btn = lv.button(scr)
btn.set_size(120, 50)
btn.align(lv.ALIGN.CENTER, 0, 0)
label = lv.label(btn)
label.set_text("Press me")

# Event callback
def on_click(evt):
    label.set_text("Clicked!")

btn.add_event_cb(on_click, lv.EVENT.CLICKED, None)
```

SOURCE: [LVGL MicroPython binding README](https://github.com/lvgl/lv_binding_micropython) (accessed 2026-03-05)

### MicroPython on Unix (SDL2 window, for desktop development)

```python
import lvgl as lv
from lv_utils import event_loop

event_loop = event_loop()
disp = lv.sdl_window_create(480, 320)
mouse = lv.sdl_mouse_create()
keyboard = lv.sdl_keyboard_create()

label = lv.label(lv.screen_active())
label.set_text("Hello from LVGL on desktop")
label.align(lv.ALIGN.CENTER, 0, 0)
```

SOURCE: [LVGL MicroPython binding README](https://github.com/lvgl/lv_binding_micropython) (accessed 2026-03-05)

---

## Relevance to Claude Code Development

### Applications

LVGL is not directly applicable to Claude Code server-side or CLI tooling. However, it is
relevant in two specific contexts:

- **Embedded AI devices**: Claude-powered devices with physical displays (wearables, smart
  home panels, industrial HMIs) commonly use LVGL for the UI layer. Understanding LVGL's
  architecture helps when designing prompt workflows that generate or modify LVGL C/Python UI
  code.
- **MicroPython AI agents**: Projects combining MicroPython + LVGL + Claude API calls (e.g.,
  on ESP32-S3) use this stack for on-device AI UI. The `lv_binding_micropython` Python API
  is directly scriptable.

### Patterns Worth Adopting

- **Partial buffer rendering**: LVGL's dirty-region + partial-buffer approach — render only
  changed regions into a small buffer, flush, repeat — is a memory-efficient pattern
  applicable to any system where full in-memory state is expensive.
- **Hardware abstraction via callbacks**: LVGL's display and input driver model (register a
  struct of function pointers, no inheritance) is a clean C pattern for portable hardware
  abstraction without OOP overhead.
- **CSS-like style inheritance**: The part/state style selector model (`LV_PART_X |
  LV_STATE_Y`) maps directly to CSS pseudo-class selectors, making it learnable for web
  developers targeting embedded systems.
- **Auto-generated Python bindings from C headers**: `lv_binding_micropython` uses
  `pycparser` to parse LVGL headers and generate bindings automatically. This pattern is
  reusable for any C library that needs Python bindings without hand-writing FFI glue.

### Integration Opportunities

- **Code generation**: Claude Code can generate LVGL C or MicroPython UI code from natural
  language descriptions. The widget API is well-documented and consistent enough for reliable
  generation.
- **SquareLine Studio export review**: AI review of SquareLine-exported C files for style,
  correctness, and memory usage patterns.
- **Embedded skill**: A Claude Code skill for embedded UI development could include LVGL
  widget reference, porting checklist, and common MCU-specific configurations.

---

## References

- [LVGL Homepage](https://lvgl.io) (accessed 2026-03-05)
- [LVGL GitHub Repository (lvgl/lvgl)](https://github.com/lvgl/lvgl) (accessed 2026-03-05)
- [LVGL Documentation v9.2 — Introduction](https://docs.lvgl.io/9.2/intro/index.html) (accessed 2026-03-05)
- [LVGL Documentation v9.2 — Get Started](https://docs.lvgl.io/9.2/get-started/index.html) (accessed 2026-03-05)
- [LVGL Documentation v9.2 — Quick Overview](https://docs.lvgl.io/9.2/get-started/quick-overview.html) (accessed 2026-03-05)
- [LVGL Documentation v9.2 — Widgets](https://docs.lvgl.io/9.2/widgets/index.html) (accessed 2026-03-05)
- [LVGL Documentation v9.2 — Porting](https://docs.lvgl.io/9.2/porting/index.html) (accessed 2026-03-05)
- [LVGL MicroPython Binding (lvgl/lv_binding_micropython)](https://github.com/lvgl/lv_binding_micropython) (accessed 2026-03-05)
- [GitHub API — lvgl/lvgl repository metadata](https://api.github.com/repos/lvgl/lvgl) (accessed 2026-03-05)
- [GitHub API — lvgl/lvgl latest release](https://api.github.com/repos/lvgl/lvgl/releases/latest) (accessed 2026-03-05)

---
