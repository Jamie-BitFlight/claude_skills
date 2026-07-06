---
title: "cmux — Ghostty-based macOS Terminal for AI Coding Agents"
license: "AGPL-3.0-or-later (open source) + commercial license option"
---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [kernel-sh.md](../agent-infrastructure/kernel-sh.md) | agent-infrastructure | complementary cloud browser infrastructure for AI agents; kernel provides servers, cmux provides the client UI |
| [vibium.md](../agent-infrastructure/vibium.md) | agent-infrastructure | alternative W3C standard browser automation via WebDriver BiDi; cmux uses WKWebView with scriptable API |
| [using-tmux-with-claude-code.md](../developer-tools/using-tmux-with-claude-code.md) | developer-tools | terminal multiplexing workflow predecessor; cmux extends tmux's multi-pane coordination with native UI and notifications |
| [shpool.md](../developer-tools/shpool.md) | developer-tools | raw PTY session persistence without intermediate terminal rendering; cmux manages Ghostty-rendered surfaces with extended metadata |
| [byobu.md](../developer-tools/byobu.md) | developer-tools | terminal multiplexer wrapper with status bar UI; cmux replaces this pattern with native macOS app and agent-focused notifications |
| [yume.md](../developer-tools/yume.md) | developer-tools | native Tauri+Rust GUI for Claude Code CLI parallelizing agents; cmux focuses on terminal pane organization and visual agent attention signals |
| [orbstack.md](../developer-tools/orbstack.md) | developer-tools | native macOS VM and container management with resource optimization; cmux applies similar efficiency principles to terminal workspace organization |

---

**Entry Status**: Complete
**Created**: 2026-03-28
**Resource Name**: cmux
**Category**: agent-infrastructure
