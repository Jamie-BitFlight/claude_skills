---
name: code-review-web
description: Reviews browser-rendered HTML, CSS, JSX, TSX, JavaScript, and TypeScript for accessibility, XSS, forms, focus, rendering performance, styles, and lifecycle cleanup. Loaded by dh:code-reviewer when source or framework entrypoints establish frontend execution; composes with TypeScript checks.
user-invocable: false
---

# Web Frontend Code Review Patterns

Load these checks for browser-targeted HTML, CSS, JavaScript, TypeScript, JSX, and TSX. Confirm the
rendering/runtime path from source and relevant framework configuration; apply TypeScript checks
alongside these checks when applicable.

Read [Review principles](../../docs/review-principles.md) before applying these checks; it defines
authority, applicability, evidence, and blocking criteria.

## Accessibility

- Every interactive element (button, link, input, select) must have an accessible name — either visible text, `aria-label`, or `aria-labelledby`
- Verify focus behavior for the component's semantics: modal interaction needs appropriate containment and restoration; do not impose a modal focus trap on an ordinary nonmodal panel.
- Check text contrast and large-text eligibility against the target's applicable accessibility standard; record the actual foreground/background and sizing evidence rather than guessing from visual appearance.
- Icon-only buttons without visible text must have `aria-label` or a visually-hidden text span
- Verify form controls have programmatically associated names/labels appropriate to their semantics; visual proximity alone does not establish that relationship.
- Images conveying information must have descriptive `alt` text; decorative images use `alt=""`
- Keyboard navigation must work — focus order must follow visual order, no focus traps outside intentional modal patterns

## XSS Prevention

- `element.innerHTML = userValue` is a blocking finding — use `textContent` for plain text
- `dangerouslySetInnerHTML` (React) or equivalent without sanitization is a blocking finding
- User-controlled values used in `eval()`, `Function()`, or `setTimeout(string)` are a blocking finding
- Validate user-controlled URL schemes for the actual attribute and content context; prevent executable or unauthorized navigation/content while preserving deliberately supported media sources.

## Performance

- Investigate interleaved layout reads (`offsetWidth`, `getBoundingClientRect`) and style writes for repeated layout work; establish the affected rendering path and cost before assigning severity.
- Check that image layout reserves the required space through dimensions or an equivalent supported layout rule; report observed or source-established layout-shift risk.
- Review off-screen image loading against the critical rendering path and intended preload behavior; recommend lazy loading where it addresses a demonstrated cost.
- Check the actual script-loading semantics and critical rendering effect of large bundles; absence of a particular attribute alone does not establish a performance defect.
- Trace expensive render work to its input size, frequency, and user-visible cost before recommending memoization or another optimization.

## CSS

- Inspect `!important` for an actual cascade conflict or project-policy violation; a justified third-party override is not defective solely because of the keyword.
- Apply the project's design-token conventions where they exist; do not impose a new token system on unrelated styles.
- Trace undocumented `z-index` values to stacking behavior and project policy before requiring named tokens or a new scale.
- `position: fixed` or `position: sticky` without overflow and scroll container awareness is flagged
- Verify whether broad component selectors affect unintended descendants; identify the affected component and style consequence.

## Forms

- Verify user-operable fields have accessible names and any visible/programmatic labels required by their semantics and the target standard; preserve supported wrapping, association, or equivalent naming mechanisms.
- Where the target accessibility standard requires identifying input purpose, verify the field's purpose and relevant `autocomplete` metadata.
- Validation error messages must be associated with the field via `aria-describedby` — color alone is not sufficient to communicate errors
- Form submission must not clear field values without user confirmation when validation fails

## Event Listener Cleanup

- Verify listeners stop affecting the component when its lifetime ends, through explicit removal, supported abort/disposal behavior, or an equivalent lifetime guarantee.
- For `document.addEventListener`, trace the long-lived emitter and actual cleanup mechanism; report retained listeners or stale effects rather than requiring one cleanup spelling.
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
/* Investigate this value against the actual stacking contract. */
.modal { z-index: 9999; }

/* RIGHT: design token */
.modal { z-index: var(--z-modal); }

/* Investigate the override's scope and reason. */
.button { color: red !important; }

/* RIGHT: explained override */
/* Overrides third-party widget styles that cannot be targeted more specifically */
.widget-container .button { color: red !important; }
```
