# Audit Checklist

Run systematic technical quality checks across the dimensions below for any CLI/TUI surface. Document findings; do not fix in this stage. Re-run the audit after fixes are applied (see Re-run loop at the end of this file).

This is a code-level audit, not a design critique. Check what is measurable and verifiable in the implementation. Tag every issue with a P0-P3 severity. The aggregate /20 score is advisory; the blocking signal is per-issue P0 tagging.

## Diagnostic Scan — Dimensions

Run comprehensive checks across the dimensions below. Score each dimension 0-4 using the criteria in each section.

### 1. Inclusion & Accessibility

Check for:

- **Contrast**: Text contrast ratios ≥4.5:1 against likely terminal backgrounds (`#000`, `#1c1c1c`, `#fff`, `#f5f5f5`); ≥3:1 for large text and UI components
- **NO_COLOR honoured**: When `NO_COLOR=1` is set in the environment, every colour decision falls back to monochrome plus shape
- **Non-TTY fallback**: When stdout is not a TTY, ANSI is stripped, progress bars are suppressed, output is line-oriented
- **Status by shape, not colour alone**: Status indicators carry a non-colour signal (symbol, prefix, position) so colour-blind users can distinguish states
- **Terminal screen-reader caveats**: Output remains intelligible when read linearly; no information conveyed only through 2D layout that a screen reader cannot follow
- **Focus indicator**: Every Textual widget with `can_focus=True` has a visible focus border or `:focus` style; never remove the focus indicator without a replacement; minimum 3:1 contrast against adjacent colours; consistent across all interactive widgets
- **Keyboard navigation**: Tab order is logical; all interactive elements reachable from the keyboard; no keyboard traps
- **Roving tabindex for component groups**: tabs, menu items, and radio groups have one tabbable item; arrow keys move within the group. TUI translation: Textual `Container` with `can_focus_children=True` and arrow-key bindings.
- **Form labels**: Questionary prompts have visible labels; validation errors say what is wrong and how to fix it

Edge-case categories (port from the harden stage):

- **Long text**: cell-wrap behaviour at 80 / 100 / 120 / ≥160 cell tiers — does the layout survive long names, descriptions, and titles
- **Emoji and non-ASCII**: Unicode glyphs have a plain-ASCII fallback path when terminal does not support them
- **RTL text**: terminal direction support note — RTL languages may not render correctly in many terminals; document the limitation
- **Network errors**: CLI exits with a non-zero exit code, prints a structured error to stderr, suggests a recovery action
- **Large datasets**: pagination or virtual-list strategy for ≥1000 items; never load-and-render everything in a single pass

Cognitive load checklist (port verbatim):

- [ ] **Single focus**: Can the user complete their primary task without distraction from competing elements? (TUI: no competing terminal UI)
- [ ] **Chunking**: Is information presented in digestible groups (≤4 items per group)?
- [ ] **Grouping**: Are related items visually grouped together (proximity, borders, shared background)? (TUI: panel borders / spacing)
- [ ] **Visual hierarchy**: Is it immediately clear what's most important on the screen? (TUI: one element dominant per screen)
- [ ] **One thing at a time**: Can the user focus on a single decision before moving to the next? (TUI: wizard pattern)
- [ ] **Minimal choices**: Are decisions simplified (≤4 visible options at any decision point)?
- [ ] **Working memory**: Does the user need to remember information from a previous screen to act on the current one? (TUI: state shown in current view)
- [ ] **Progressive disclosure**: Is complexity revealed only when the user needs it? (TUI: `-v` / `-vv` levels)

**Cognitive load scoring**: 0-1 failures = low (good). 2-3 = moderate (address soon). 4+ = high (critical fix needed).

**Working memory rule**: humans can hold ≤4 items in working memory at once (Miller's Law revised by Cowan, 2001). Applied to CLI:

- Navigation menus: ≤5 top-level subcommands (group the rest under clear categories)
- Flag groups: ≤4 visible at one decision point
- Status indicators: ≤4 distinct states per screen
- Dashboard widgets: ≤4 key metrics visible without scrolling
- Decision points: ≤4 visible options (more causes analysis paralysis)

**Common cognitive load violations** (with TUI examples):

1. **Wall of Options** — `--help` listing 30 flags flat with no hierarchy. Fix: group into categories, highlight the most common, use progressive disclosure (`--help` shows top-level; `--help-all` shows everything).
2. **Memory Bridge** — output from one command must be remembered to act on the next; state not retained across invocations. Fix: keep relevant context visible, or surface it where it is needed.
3. **Hidden Navigation** — subcommand structure not discoverable from `--help`; user must build a mental map. Fix: list subcommands prominently in top-level help; surface current location in interactive flows.
4. **Jargon Barrier** — error messages with stack-trace internals or implementation-language terms. Fix: plain user-facing language; if domain terms are unavoidable, define them inline.
5. **Visual Noise Floor** — decorative borders on every output; every element has the same visual weight; nothing stands out. Fix: one primary element, 2-3 secondary, everything else muted (dim or terminal default).
6. **Inconsistent Pattern** — different status symbols across subcommands (`[OK]` here, `✓` there, `done` somewhere else). Fix: standardize the status vocabulary; same state = same symbol everywhere.
7. **Multi-Task Demand** — simultaneous prompts; user must process multiple inputs at once (reading + deciding + navigating). Fix: sequence the steps; one decision at a time.
8. **Context Switch** — required round-trip to docs to complete a single decision. Fix: co-locate the information needed for each decision; embed examples in `--help`.

**Score 0-4**: 0=Inaccessible (fails contrast, no NO_COLOR, no non-TTY fallback, no focus indicators), 1=Major gaps (some accommodations missing, clear barriers), 2=Partial (some inclusion effort, significant gaps), 3=Good (most criteria met, minor gaps), 4=Excellent (all criteria met, edge cases handled, screen-reader-friendly output).

### 2. Performance & Responsiveness

Check for:

- **First-render ≤200ms**: time from process start to first painted frame
- **No spinner on operations <200ms**: a spinner that flashes on and off is worse than no spinner
- **Input-to-feedback ≤50ms**: keystroke or click registers visible feedback within 50ms
- **No full-screen redraw when partial works**: surgical updates over `Live` regions or Textual reactive attributes; do not clear and reprint
- **Layout thrashing**: do not measure widget size in a render loop; batch reads then writes
- **Streaming over spinner**: progressive disclosure of partial output beats an indefinite spinner

Core Web Vitals → CLI translation:

| Web vital | CLI equivalent | Target |
|---|---|---|
| LCP (Largest Contentful Paint) | First-render | ≤200ms |
| INP (Interaction to Next Paint) | Input-to-feedback | ≤50ms |
| CLS (Cumulative Layout Shift) | No-reflow on second-pass output | first render does not shift on subsequent data arrival |

PyFiglet and other heavy display elements: opt-in only or gated to first run. Never render on every invocation.

**Score 0-4**: 0=Severe (multi-second first render, full-screen reflow, blocking I/O on main loop), 1=Major (slow first render, frequent reflow, naive spinner usage), 2=Partial (some optimization, gaps remain), 3=Good (mostly within targets, minor improvements possible), 4=Excellent (fast first render, surgical updates, streaming output).

### 3. Theming & Portability

Check for:

- **TCSS variables for `:dark` and `:light`**: theme switching uses TCSS theme variables (`$primary`, `$accent`, `$boost`, `$panel`, `$surface`); both modes have explicit definitions
- **No hard-coded colours**: colour values reference DESIGN.TUI.md / DESIGN.md tokens; no scattered hex literals
- **Works on iTerm2, Alacritty, Windows Terminal, GNOME Terminal, tmux, plain xterm**: layout and colour render correctly across the supported emulator matrix
- **Emoji has Unicode-only fallback**: every emoji has a plain-ASCII equivalent for terminals that do not render emoji
- **Theme switching is consistent**: every styled surface updates when the theme changes; no orphaned colours

**Score 0-4**: 0=No theming (hard-coded everything, breaks outside one emulator), 1=Minimal tokens (mostly hard-coded, no light variant), 2=Partial (tokens exist but inconsistently used), 3=Good (tokens used, dark/light both work, minor hard-coded values), 4=Excellent (full token system, both themes work, portable across emulator matrix).

### 4. Width & Adaptive Layout

Check for:

- **Renders at 80 / 100 / 120 / ≥160 cell tiers**: primary commands MUST render readably at 80 cells; wider tiers are progressive enhancement
- **No horizontal scroll on 80 cells for primary commands**: the most-used commands fit the narrowest tier without requiring scroll
- **Truncation strategy defined**: long values are truncated with a documented strategy (ellipsis, mid-truncation, head-truncation); never silently cut off mid-character
- **Piped output ignores width**: when stdout is not a TTY, output is line-oriented and width-independent; one logical record per line

**Score 0-4**: 0=Desktop-only (assumes ≥160 cells, breaks at 80), 1=Major (some tiers, frequent overflow), 2=Partial (works at 80, rough edges at wider tiers), 3=Good (all tiers render, minor truncation issues), 4=Excellent (fluid across all tiers, piped output correct, truncation strategy applied consistently).

### 5. Anti-Patterns & Slop (CRITICAL)

Run the two-altitude AI slop test from `./ai-slop-test.md`. Check against the full match-and-refuse table in `./anti-references.md`.

Copy:

- Every word earns its place
- No em dashes
- Status messages name what happened, not what the program is doing internally
- Error messages name the user-facing concept, not the implementation

**Score 0-4**: 0=AI slop gallery (5+ tells, both altitudes fail), 1=Heavy AI aesthetic (3-4 tells, first-altitude fails), 2=Some tells (1-2 noticeable), 3=Mostly clean (subtle issues only), 4=No AI tells (passes both altitudes of the slop test, distinctive intentional design).

## Generate Report

### Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|-------|-------------|
| 1 | Inclusion & Accessibility | ? | [most critical issue or "--"] |
| 2 | Performance & Responsiveness | ? | |
| 3 | Theming & Portability | ? | |
| 4 | Width & Adaptive Layout | ? | |
| 5 | Anti-Patterns & Slop | ? | |
| **Total** | | **??/20** | **[Rating band]** |

**Rating bands** (advisory, not blocking):

- 18-20 Excellent (minor polish)
- 14-17 Good (address weak dimensions)
- 10-13 Acceptable (significant work needed)
- 6-9 Poor (major overhaul)
- 0-5 Critical (fundamental issues)

The aggregate score is advisory. The blocking signal is per-issue P0 tagging — see the Hard-Gate Rule below.

### Anti-Patterns Verdict

Start here. Pass / fail: does this look AI-generated? List specific tells from the two-altitude slop test. Be brutally honest.

### Executive Summary

- Audit Health Score: **??/20** ([rating band])
- Total issues found, count by severity: P0 / P1 / P2 / P3
- Top 3-5 critical issues
- Recommended next steps

### Detailed Findings by Severity

Tag every issue with P0-P3 severity (verbatim from the impeccable source):

| Priority | Name | Description | Action |
|----------|------|-------------|--------|
| **P0** | Blocking | Prevents task completion entirely | Fix immediately; this is a showstopper |
| **P1** | Major | Causes significant difficulty or confusion | Fix before release |
| **P2** | Minor | Annoyance, but workaround exists | Fix in next pass |
| **P3** | Polish | Nice-to-fix, no real user impact | Fix if time permits |

**Tip**: If you're unsure between two levels, ask: "Would a user contact support about this?" If yes, it's at least P1.

For each issue, document:

- **[P?] Issue name**
- **Location**: Component, file, line
- **Category**: Inclusion / Performance / Theming / Width / Anti-Pattern
- **Impact**: How it affects users
- **Standard violated**: WCAG, NO_COLOR, the design contract, or the named project rule (if applicable)
- **Recommendation**: How to fix it

### Patterns & Systemic Issues

Identify recurring problems that indicate systemic gaps rather than one-off mistakes:

- "Hard-coded `cyan` appears in 12 panel definitions; should reference `$accent` from DESIGN.TUI.md"
- "Status symbols inconsistent across subcommands — `[OK]`, `✓`, `done` all used for the same state"
- "Spinners triggered for sub-100ms operations in 5 places"

### Positive Findings

Note what is working well: practices to maintain and replicate.

## Hard-Gate Rule

Any P0 issue blocks ship. Zero P0 issues = pass. Aggregate score remains advisory.

This rule is the gate. The /20 score is informational. A surface with score 18/20 and one P0 does not ship. A surface with score 13/20 and zero P0 does ship (with the understanding that P1/P2 items remain backlog and the rating band describes the polish gap).

## Re-run Loop

Re-run this skill's Stage 5 audit pass after applying fixes.

After applying fixes recommended by an audit pass, re-run the audit against the same target. The audit is the single source of truth for whether ship is unblocked — there is no "return to Implement" or "return to Shape" transition. The recovery path is fix → re-run audit → re-evaluate P0 count.

## Notes for Auditors

- Be thorough but actionable. Too many P3 issues creates noise. Focus on what actually matters.
- Report issues with explicit impact — why does this matter to the user
- Provide specific recommendations, not generic advice
- Do not skip positive findings; what works should be named so it can be preserved
- Prioritize honestly — not everything can be P0
- Verify before reporting; do not report false positives
