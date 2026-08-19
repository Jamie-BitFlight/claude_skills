# Polish Checklist

Final-pass discipline for any CLI/TUI surface produced by `designing-ui-for-cli`. Catches the small details that separate good work from great work — the difference between shipped and polished.

**Polish is the last step, not the first.** Don't polish work that's not functionally complete.

---

## Design System Discovery

Aligning the feature to the design system is **not optional**. Polish without alignment is decoration on top of drift, and it makes the next person's job harder. Discovery comes before any other polish work.

1. **Find the design system**: Search for `DESIGN.TUI.md` first; fall back to `DESIGN.md` with `runtime: tui` marker; fall back to conventions visible in existing TCSS, Rich Console code, and Questionary `Style` definitions. Study the core patterns: design principles, target audience, colour tokens, cell-grid spacing, text-style hierarchy, component shapes (Panel borders, status symbols), motion conventions (TCSS transitions, spinner cadence).

2. **Note the conventions**: How are shared widgets imported (Textual `Container` patterns, Rich `Panel` factories)? What spacing scale is used (cell-grid integers: 1, 2, 4, 8)? Which colours come from TCSS variables vs hard-coded hex? Which from Rich theme keys vs inline markup? What status symbol set is canonical (`✓` `✗` `…` `!` vs `[ok]` `[fail]` `[wait]` `[warn]`)? What flow shapes are used for comparable actions (subcommand vs interactive prompt; one-shot output vs persistent dashboard)?

3. **Identify drift, then name the root cause**. For every deviation, classify it as one of:
   - **Missing token**: the value should exist in `DESIGN.TUI.md` but doesn't (e.g., a new status state without a token).
   - **One-off implementation**: a shared widget or Panel factory already exists but wasn't used (e.g., a hand-rolled panel border instead of the project's `Panel` helper).
   - **Conceptual misalignment**: the feature's flow, information architecture, or hierarchy doesn't match neighbouring features (e.g., a wizard pattern in a codebase of one-shot subcommands).

   The fix differs by category: patch the value, swap to the shared component, or rework the flow. Fixing the symptom without naming the cause is how drift compounds.

If a design system exists, polish **must** align the feature with it. If none exists, polish against the conventions visible in the codebase. **If anything about the system is ambiguous, ask. Never guess at design system principles.**

---

## Pre-Polish Assessment

Understand the current state and goals before touching anything:

1. **Review completeness**:
   - Is it functionally complete?
   - Are there known issues to preserve (mark with TODOs)?
   - What's the quality bar? (MVP vs flagship feature?)
   - When does it ship? (How much time for polish?)

2. **Think experience-first**: Who actually uses this, and what's the best possible experience for them? Effective design beats decorative polish; a feature that looks beautiful but fights the user's flow is not polished. Walk the path from their perspective before opening DevTools.

3. **Identify polish areas**:
   - Visual inconsistencies
   - Spacing and alignment issues
   - Interaction state gaps
   - Copy inconsistencies
   - Edge cases and error states
   - Loading and transition smoothness
   - Information architecture and flow drift (does this feature reveal complexity the way neighboring features do?)

4. **Triage cosmetic vs functional**: Classify each issue as **cosmetic** (looks off, doesn't impede the user) or **functional** (breaks, blocks, or confuses the experience). When polish time is tight, functional issues ship first; cosmetic ones can land in a follow-up. Quality should be consistent; never perfect one corner while leaving another rough.

**CRITICAL**: Polish is the last step, not the first. Don't polish work that's not functionally complete.

---

## The 22-Item Checklist

Go through systematically. Each item is binary — checked or not.

- [ ] Aligned to `DESIGN.TUI.md` / `DESIGN.md` (drift named and resolved by root cause)
- [ ] Information architecture and flow shape match neighboring features
- [ ] Column alignment perfect at 80/100/120/≥160 cell tiers
- [ ] Spacing uses TCSS variables / Rich theme keys consistently
- [ ] Text-style hierarchy consistent (bold/dim/italic roles)
- [ ] All Textual widget states implemented (default, hover, focus, pressed, disabled) where applicable
- [ ] TCSS transitions smooth at terminal redraw cadence; no stutter under normal load
- [ ] Copy is consistent and polished — no em dashes; every word earns its place
- [ ] Unicode glyphs and emoji are consistent; PyFiglet only where opted-in; no emoji as load-bearing semantics
- [ ] All Questionary prompts properly labelled and validated
- [ ] Error states are helpful
- [ ] Loading: spinner only when operation >200ms; progress text for >2s; cancellable
- [ ] Empty states are welcoming
- [ ] Keyboard targets reachable via Tab in logical order; Textual `can_focus` set on interactive widgets
- [ ] Contrast verified ≥4.5:1 against likely light AND dark terminal backgrounds
- [ ] Keyboard navigation works
- [ ] Textual focus border or `:focus` style visible
- [ ] No exceptions on common paths; tracebacks formatted via `rich.traceback` or Typer pretty exceptions
- [ ] First render does not reflow on subsequent data arrival
- [ ] Works on iTerm2, Alacritty, Windows Terminal, GNOME Terminal, tmux, plain xterm
- [ ] Respects `NO_COLOR=1` and `TERM=dumb`; non-TTY pipe strips ANSI
- [ ] Code is clean (no TODOs, console.logs, commented code)

### Hard-gate rule

Every applicable item must check, OR the unchecked item is explicitly marked **deferred to follow-up** with a recorded reason. No aggregate threshold. No silent skips.

A deferral entry takes the form:

```text
- [~] Column alignment perfect at 80/100/120/≥160 cell tiers
  Deferred to follow-up: 160-cell tier untested — no test harness for ultra-wide
  Tracked as: BACKLOG-1234
```

---

## Triage Cuts

When polish time is tight, reduce scope before sacrificing quality. Distillation principles applied to TUI:

| Dimension | Cut |
|---|---|
| Information architecture | Remove secondary actions; consolidate redundant flags; collapse optional output behind `-v` / `-vv` |
| Visual variation | One text-style hierarchy (bold / dim / regular); no Panel-in-Panel-in-Panel; remove decorative borders that don't serve grouping |
| Layout | Linear vertical flow over complex docked layouts; full-width over multi-column when content allows |
| Interaction | Smart defaults — make common choices automatic; reduce confirmation prompts; one obvious next step |
| Content | "Cut every sentence in half, then do it again." Active voice. Remove jargon, marketing fluff, hedging |
| Code | Remove unused TCSS rules, unused Rich theme keys, dead style imports; consolidate near-duplicate Panel factories |

Simplicity is not feature-removal — it is removing obstacles between users and their goals. Every element should justify its existence.

---

## Eight Interactive States

Every interactive Textual widget needs these states designed:

| State | When | TUI Treatment |
|---|---|---|
| **Default** | At rest | Base TCSS rule |
| **Hover** | Pointer over (not touch) | Subtle colour shift via `:hover` selector |
| **Focus** | Keyboard or programmatic focus | Visible focus border |
| **Active** | Being pressed | `:active` pressed-in styling |
| **Disabled** | Not interactive | Dim text, `can_focus=False` |
| **Loading** | Processing | Spinner or progress text |
| **Error** | Invalid state | Red border, status symbol, message |
| **Success** | Completed | Green check, confirmation |

**TUI applicability note**: Hover applies only when running in Textual with a mouse-capable terminal (iTerm2, Windows Terminal, modern macOS Terminal, most Linux emulators). In plain Rich/Typer CLI, or under `tmux` without mouse-mode, or piped output — hover does not apply and must not be the only affordance for an action.

**The common miss**: designing hover without focus, or vice versa. They are different. Keyboard users never see hover states.

---

## The Squint Test

Blur your eyes (or screenshot the terminal pane and apply blur). Can you still identify:

- The most important element?
- The second most important?
- Clear groupings?

If everything looks the same weight blurred, you have a hierarchy problem.

For TUI: the squint test runs against a screenshot of the rendered terminal output, not the source code. Capture at the primary width tier (the one named in the shape brief), apply blur, then ask those questions.

---

## Hierarchy Through Multiple Dimensions

Don't rely on size alone. Combine:

| Dimension | Strong Hierarchy (TUI) | Weak Hierarchy (TUI) |
|---|---|---|
| **Size** | PyFiglet header vs heading vs body (3:1 cell-height ratio or more) | Bold heading slightly larger than body (<2:1) |
| **Weight** | Bold vs regular vs dim | Regular vs regular |
| **Colour** | Full accent vs muted vs neutral terminal default | Two similar mid-tones |
| **Position** | Column 0 status symbols, top-left primary content | Buried mid-row, bottom-right |
| **Space** | Panel padding + blank rows around primary block | Tight grouping with no breathing room |

**The best hierarchy uses 2-3 dimensions at once**: a primary status line that is bolder, in an accent colour, AND positioned in column 0.

---

## UX Writing for CLIs

### The button label problem applies to confirmations

Never use generic confirmation prompts:

```python
# Wrong — ambiguous
questionary.confirm("Are you sure?")

# Wrong — what does Yes mean here?
questionary.confirm("Continue?")

# Right — names the action and consequence
questionary.confirm("Delete project? This cannot be undone")
questionary.confirm("Apply 5 migrations to production database?")
```

For destructive actions, name the destruction and the count: `"Delete 5 items"` not `"Delete selected"`.

### Error message formula

Every error answers these questions:

1. **What happened?** — the observable failure
2. **Why?** — the cause, in user vocabulary
3. **How to fix it?** — the next action

Templates:

| Situation | Template |
|---|---|
| **Format error** | `[Field] needs to be [format]. Example: [example]` |
| **Missing required** | `Please provide [what's missing]` |
| **Permission denied** | `You don't have access to [thing]. [What to do instead]` |
| **Network error** | `Could not reach [thing]. Check your connection and [action].` |
| **Server error** | `Something went wrong on our end. [Alternative action or retry guidance].` |

CLI errors include exit code, message, and recovery hint where applicable. Format tracebacks via `rich.traceback` or Typer's pretty exceptions — never let a raw Python traceback be the user's first experience of failure.

### Empty state formula

Steps:

1. **Acknowledge briefly** — confirm the empty state is real, not a bug
2. **Explain the value** — what completes when this fills
3. **Provide a clear action** — the literal next command to run

Example:

```text
No tasks yet. Create your first one with: todo add "buy milk"
```

Not just `"No items"`.

### Voice vs tone matrix

**Voice** is the project's personality, consistent everywhere. **Tone** adapts to the moment.

| Moment | Tone shift |
|---|---|
| Success | Celebratory, brief: `"Done. 5 files migrated."` |
| Error | Empathetic, helpful: `"That didn't work. Try [recovery action]."` |
| Loading | Reassuring: `"Building image…"` |
| Destructive confirm | Serious, clear: `"Delete this database? This can't be undone."` |

**Never use humour for errors.** Users are already frustrated. Be helpful, not cute.

### Terminology consistency

Pick one term and stick with it. Applies to flag names, subcommand verbs, status messages, help text:

| Inconsistent | Consistent |
|---|---|
| Delete / Remove / Trash | Delete |
| Settings / Preferences / Options / Config | Settings |
| Sign in / Log in / Authenticate | Sign in |
| Create / Add / New / Init | Create |
| List / Show / Get | List |

Build a project terminology glossary in `DESIGN.TUI.md` and enforce it. Variety creates confusion.

### Loading copy

Be specific. `"Saving draft…"` not `"Loading…"`. For long operations, set expectations: `"This usually takes 30 seconds"` or show progress text. Spinners are status, not entertainment.

---

## Final Verification

Before marking as done:

- **Use it yourself**: actually run the command, type into the prompt, watch the output scroll. Don't rely on snapshot tests alone.
- **Test on real terminals**: at minimum iTerm2 or Windows Terminal plus one of {Alacritty, GNOME Terminal} plus `tmux` plus `xterm` (for the no-truecolor fallback path).
- **Test the pipe**: `command | cat` — ANSI must strip, progress must suppress, output must remain useful.
- **Test `NO_COLOR=1` and `TERM=dumb`** — both must produce monochrome output that still conveys hierarchy via shape and position.
- **Ask someone else to review**: fresh eyes catch things, especially copy and terminology drift.
- **Compare to the shape brief**: each section the brief named must be visible in the output.
- **Check all states**: don't just test the happy path — exercise empty, loading, error, cancellation (Ctrl-C), and non-TTY paths.

---

## Clean Up

After polishing, ensure code quality:

- **Replace custom implementations**: if `DESIGN.TUI.md` or the codebase already provides a Panel factory, status symbol set, or Rich theme — switch to the shared version.
- **Remove orphaned code**: delete unused TCSS rules, unused Rich theme keys, orphaned style helpers made obsolete by polish.
- **Consolidate tokens**: if you introduced new colour values, border styles, or spacing constants, check whether they should be promoted to `DESIGN.TUI.md` tokens.
- **Verify DRY**: look for near-duplicate Panel factories, repeated status-symbol literals, or copy-pasted `Style()` calls introduced during polishing — consolidate them.

---

## Never

- Polish before the feature is functionally complete
- Polish without aligning to `DESIGN.TUI.md` / `DESIGN.md` — that is decoration on drift
- Guess at design system principles instead of asking when something is ambiguous
- Spend hours on polish if the work ships in 30 minutes — triage
- Introduce regressions while polishing — re-run the test suite after every batch
- Ignore systematic issues — if spacing is off in three commands, fix the shared helper, not just one command
- Perfect one screen while leaving another rough — consistent quality level across the surface
- Create one-off Panel factories or status symbol sets when shared equivalents exist
- Hard-code colour hex or border styles that should reference TCSS variables or Rich theme keys
- Introduce new flow shapes that diverge from established subcommand or wizard patterns
- Mark an unchecked item as "doesn't apply" without recording the reason — use the deferred-to-follow-up form

---

## Source

This checklist is ported from `impeccable@3.0.7/skills/impeccable/reference/polish.md` (lines 1-234) with TUI substitutions applied. SOURCE: Adapted from impeccable design system `polish.md` lines 176–198 (TUI substitutions applied). Distillation dimensions ported from `impeccable@3.0.7/skills/impeccable/reference/distill.md` lines 41-84. Eight interactive states from `interaction-design.md` lines 4-19. Squint test and hierarchy table from `spatial-design.md` lines 22-41. UX writing additions from `ux-writing.md` lines 4-86.
