---
title: "voxcii"
research_date: "2026-02-28"
source_url: "https://github.com/ashish0kumar/voxcii"
github_url: "https://github.com/ashish0kumar/voxcii"
version_at_research: "No tagged releases — latest commit 2026-02-27"
license: "GNU General Public License v3.0"
last_verified: "2026-02-28"
version_at_verification: "No tagged releases — commit 2026-02-27"
next_review: "2026-05-28"
---

## Overview

voxcii is a terminal-based ASCII 3D model viewer written in C++17 that renders OBJ and STL model files directly inside a terminal window using ASCII characters. It implements a software rasterizer with a Z-buffer and surface-normal-based shading to produce depth-correct, illuminated ASCII representations of 3D geometry. The viewer supports interactive rotation, zoom control, and optional ANSI color output via ncurses.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Inspecting 3D model files without a graphical desktop or 3D application | Renders OBJ and STL files as interactive ASCII art in any terminal |
| Verifying model orientation and geometry in headless or SSH environments | Z-buffer depth sorting and surface normal shading produce a readable 3D representation |
| Previewing models with material color data in text-only contexts | Optional `-c` flag activates ANSI color output sourced from `.mtl` material files |
| Handling 3D files with non-triangular polygon faces | Automatic polygon triangulation converts arbitrary OBJ faces to triangles at load time |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 81 | 2026-02-28 |
| Forks | 5 | 2026-02-28 |
| Contributors | 2 | 2026-02-28 |
| Latest Release | No tagged releases | 2026-02-28 |
| Latest Commit | 2026-02-27 | 2026-02-28 |
| Primary Language | C++ (99.3% by byte count) | 2026-02-28 |
| Repository Created | 2026-01-01 | 2026-02-28 |

SOURCE: [GitHub API — ashish0kumar/voxcii](https://api.github.com/repos/ashish0kumar/voxcii) (accessed 2026-02-28)

---

## Key Features

### 3D Model Format Support

- Loads `.obj` files including multi-face polygon meshes; applies polygon triangulation automatically for faces with more than 3 vertices
- Loads `.stl` files in both ASCII and binary variants
- Reads accompanying `.mtl` material files to extract per-face colors when color mode is active

### Rendering Pipeline

- Rotation matrices applied sequentially around Y then X axes using precomputed sine/cosine values
- Perspective-free orthographic projection maps 3D coordinates to 2D terminal cell positions via `mapToSurface()`: centers on terminal dimensions, inverts Y-axis for screen space, preserves Z depth
- Z-buffer (depth buffer) prevents occluded faces from overwriting visible ones

### ASCII Shading

- Per-triangle surface normals computed as cross product of two edge vectors: `(p2 - p1) x (p3 - p1)`
- Dot product of normal with a fixed light direction yields a brightness value in `[0, 1]`
- Brightness maps linearly to a 12-character intensity ramp: `".,':;!+*=#$@"` (`.` = shadow, `@` = highlight)
- `std::clamp()` ensures index stays within character set bounds

### Interaction and Display

- Auto-rotation mode (default): model spins continuously around Y and X axes
- Interactive mode (`-i`/`--interactive`): arrow keys control rotation, `+`/`-` control zoom, `q` exits
- Zoom initialized via `-z`/`--zoom <value>` flag (default: 100)
- Color mode (`-c`/`--color`): renders faces with ANSI terminal color sourced from material definitions
- Uses ncurses for terminal control: cursor hiding, real-time key polling, terminal dimension queries

### Build System

- Single-target Makefile for standard compilation
- Alternatively: `g++ -std=c++17 -O3 -Wall src/*.cpp -o voxcii -lncurses`
- Only external dependency: ncurses library (widely available on Linux and macOS)

---

## Technical Architecture

voxcii is a single-binary C++17 application structured around a software rasterizer loop:

```text
File Loading
  OBJParser / STLParser
      |
      v
Vertex normalization + polygon triangulation
      |
      v
Per-frame render loop
  Apply Y-rotation matrix -> Apply X-rotation matrix
      |
      v
  For each triangle:
    Project 3 vertices to 2D terminal coordinates (mapToSurface)
    Compute surface normal + dot product with light vector
    Map brightness to ASCII character
    Rasterize triangle pixels into character buffer with Z-buffer test
      |
      v
  Flush character buffer to ncurses screen
      |
      v
  Poll keyboard input (interactive mode) or advance auto-rotation angles
```

The character buffer is a 2D array matching terminal dimensions. Each cell stores a character and, in color mode, an ANSI color code derived from the `.mtl` file. The Z-buffer is a parallel float array; each rasterized pixel updates only if the new fragment's depth is less than the stored depth.

Vertex normalization scales loaded geometry to fit the terminal viewport, preventing models of vastly different real-world sizes from appearing too small or too large.

---

## Installation & Usage

```bash
# Install ncurses (Debian/Ubuntu)
sudo apt install libncurses5-dev

# Clone and build
git clone https://github.com/ashish0kumar/voxcii.git
cd voxcii
make
```

```bash
# Alternatively build manually
g++ -std=c++17 -O3 -Wall src/*.cpp -o voxcii -lncurses
```

```bash
# View a model with auto-rotation
./voxcii model.obj

# View with interactive rotation controls
./voxcii -i model.obj

# View with color rendering (requires .mtl file alongside .obj)
./voxcii -c model.obj

# Set initial zoom level (default 100)
./voxcii -z 150 model.obj

# Combined flags
./voxcii -i -c -z 120 model.stl
```

Keyboard controls in interactive mode:

```text
Arrow keys    Rotate model
+             Zoom in
-             Zoom out
q             Quit
```

---

## Relevance to Claude Code Development

### Applications

- Demonstrates a minimal, dependency-light C++ rendering architecture that could serve as a reference when implementing terminal-based visualizations in developer tools
- Illustrates how to display structured data (3D geometry) in text-only environments — a pattern applicable to terminal-based diagram or graph renderers for code analysis output

### Patterns Worth Adopting

- Character intensity ramp for brightness mapping (`".,':;!+*=#$@"`) is a reusable pattern for any terminal tool needing to convey numeric magnitude as text density
- Z-buffer pattern for layered terminal rendering: when drawing overlapping UI elements in ncurses-based TUIs, a depth buffer prevents incorrect draw order
- Separating the rendering loop from input polling (auto vs. interactive mode) is a clean architecture for CLI tools that need both scripted and interactive operation modes

### Integration Opportunities

- Could be invoked as a subprocess from a Claude Code skill that generates or validates 3D geometry files (e.g., verifying mesh output from a generative pipeline)
- The ASCII shading algorithm is self-contained and could be extracted as a reference implementation for any terminal visualization component in a Claude Code plugin that needs to render spatial data

---

## References

- [GitHub Repository — ashish0kumar/voxcii](https://github.com/ashish0kumar/voxcii) (accessed 2026-02-28)
- [GitHub API — repo metadata](https://api.github.com/repos/ashish0kumar/voxcii) (accessed 2026-02-28)
- [GitHub API — contributors](https://api.github.com/repos/ashish0kumar/voxcii/contributors) (accessed 2026-02-28)
- [GitHub API — languages](https://api.github.com/repos/ashish0kumar/voxcii/languages) (accessed 2026-02-28)
- [README.md — raw source](https://raw.githubusercontent.com/ashish0kumar/voxcii/main/README.md) (accessed 2026-02-28)
- [main.cpp — rendering implementation](https://github.com/ashish0kumar/voxcii/blob/main/src/main.cpp) (accessed 2026-02-28)

---
