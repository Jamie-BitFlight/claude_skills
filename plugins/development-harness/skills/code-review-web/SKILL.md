---
name: code-review-web
description: Use when reviewing web frontend code — HTML, CSS, JSX, or browser-targeted JavaScript. Enforces accessibility (WCAG AA, aria labels, focus management), XSS prevention (innerHTML, dangerouslySetInnerHTML), performance (layout thrash, CLS, lazy loading), CSS design tokens, form labeling, and event listener cleanup. Loaded by dh:code-reviewer on *.html, *.css, *.jsx detection.
user-invocable: false
---

# Web Frontend Code Review Patterns

Stack-specific rules loaded by `dh:code-reviewer` when `*.html`, `*.css`, or `*.jsx` (browser-targeted) files are detected.

## Accessibility

- Every interactive element (button, link, input, select) must have an accessible name — either visible text, `aria-label`, or `aria-labelledby`
- Focus must be managed when modals, dialogs, or dynamic panels open — trap focus inside and restore it on close
- Color contrast ratio must meet WCAG AA — 4.5:1 for normal text, 3:1 for large text (18px+ or 14px+ bold)
- Icon-only buttons without visible text must have `aria-label` or a visually-hidden text span
- Form inputs must be associated with their label via `for`/`id` pairing or `aria-labelledby` — proximity alone is not sufficient
- Images conveying information must have descriptive `alt` text; decorative images use `alt=""`
- Keyboard navigation must work — focus order must follow visual order, no focus traps outside intentional modal patterns

## XSS Prevention

- `element.innerHTML = userValue` is a blocking finding — use `textContent` for plain text
- `dangerouslySetInnerHTML` (React) or equivalent without sanitization is a blocking finding
- User-controlled values used in `eval()`, `Function()`, or `setTimeout(string)` are a blocking finding
- URL values from user input used in `href`, `src`, or `action` attributes must be validated against an allowlist of schemes (block `javascript:`, `data:`)

## Performance

- Layout thrash — reading layout properties (`offsetWidth`, `getBoundingClientRect`) inside a loop that also writes styles — is a blocking finding
- Images must have explicit `width` and `height` attributes to prevent layout shift (CLS)
- Images below the fold must use `loading="lazy"` — eager loading of off-screen images delays critical rendering
- Large JavaScript bundles loaded synchronously in `<head>` without `defer` or `async` are a blocking finding
- Expensive computations inside render functions (React `render`, Vue template expressions) without memoization are a blocking finding

## CSS

- `!important` without an explanatory comment is a blocking finding
- Design tokens (colors, spacing, typography) must use CSS custom properties (`--color-primary`) — hardcoded hex values and px values are non-blocking but flagged
- Magic `z-index` values without a documented z-index scale are a blocking finding — use named tokens (`z-index: var(--z-modal)`)
- `position: fixed` or `position: sticky` without overflow and scroll container awareness is flagged
- `*` selectors in component styles that may bleed into child components are a blocking finding

## Forms

- Every `<input>`, `<select>`, and `<textarea>` must have an associated `<label>` (either wrapping or via `for`/`id`)
- `autocomplete` attributes must be set on inputs that collect personal data (name, email, address, payment) — required for WCAG 1.3.5
- Validation error messages must be associated with the field via `aria-describedby` — color alone is not sufficient to communicate errors
- Form submission must not clear field values without user confirmation when validation fails

## Event Listener Cleanup

- Event listeners added in component mount / setup must be removed in the corresponding unmount / cleanup
- `document.addEventListener` without a corresponding `removeEventListener` in the cleanup lifecycle is a blocking finding
- `AbortController` is preferred for fetch-and-cleanup patterns — pass the signal and abort on cleanup

## Anti-Patterns

```html
<!-- WRONG: no label, no accessible name -->
<input type="text" placeholder="Search..." />

<!-- RIGHT: associated label -->
<label for="search">Search</label>
<input type="text" id="search" autocomplete="off" />

<!-- WRONG: XSS vector -->
<div id="output"></div>
<script>
  document.getElementById("output").innerHTML = userInput;
</script>

<!-- RIGHT: safe text insertion -->
<script>
  document.getElementById("output").textContent = userInput;
</script>
```

```css
/* WRONG: magic z-index */
.modal { z-index: 9999; }

/* RIGHT: design token */
.modal { z-index: var(--z-modal); }

/* WRONG: unexplained !important */
.button { color: red !important; }

/* RIGHT: explained override */
/* Overrides third-party widget styles that cannot be targeted more specifically */
.widget-container .button { color: red !important; }
```
