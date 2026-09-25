---
name: review-accessibility-change
description: Review changed user-interface or CLI presentation behavior for accessibility failures. Use for an independent accessibility perspective on a defined change set.
---
# Review Accessibility Change

First determine whether the change affects an interactive UI or presentation where accessibility semantics apply; otherwise return SKIP. For relevant changes inspect accessible names/labels, semantic roles, keyboard/focus operation, dynamic announcements, meaningful image alternatives, color-only state, and CLI output whose meaning depends only on ANSI color. Evaluate native semantics before demanding ARIA. Return REJECT for demonstrated barriers that prevent equivalent operation or understanding; APPROVE when no blocker is found. Cite the affected element/output and evidence.
