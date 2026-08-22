# Anti-references

Patterns to refuse on sight. Each row is a match-and-rewrite rule: when about to write the pattern, restructure the element instead.

For register-specific refuse-lists (brand-CLI vs product-CLI permissions and bans), see [register-decision.md](./register-decision.md). The list below applies to both registers — these are absolute bans, not register choices.

## Match-and-refuse table

| Pattern | Why it fails | Rewrite as |
|---|---|---|
| Lolcat output (rainbow gradient via 24-bit ANSI on every line of stdout) | Reads as "AI generated" or as a one-trick novelty package; obscures status semantics by making every line equally bright. | Plain output for body text; reserve colour for status, identifiers, and one accent. Use the Restrained or Committed strategy from [colour-strategy.md](./colour-strategy.md). |
| Splash screen on every invocation | Punishes the power user; turns a tool into a billboard. Brand-CLI permission is "splash on first run or demo surface", not "splash on every command". | Splash only on first-run flow, `--demo`, or installer surfaces. Subsequent invocations land in the task. |
| Fake throbbers / spinners on operations under 200ms | Lies about progress. Users learn to distrust the UI. Any visible spinner implies the work is taking measurable time. | Show no indicator under 200ms; show a spinner with a label between 200ms and 2s; show progress text or a determinate bar over 2s. Cancellable on Ctrl-C. |
| Decorative panel borders on every output block | Visual noise floor that buries the content. The border becomes the signal of "this CLI tries hard", not of grouping. | Borders only when they group genuinely related items. A column of plain key-value pairs needs no border. Reserve `Panel` for sections with distinct identity. |
| Hacker green-on-black aesthetic | First-order training reflex for "DevOps" / "SRE" / "crypto" / "security" categories. Reads as costume. Fails the AI slop test at the first altitude. | Run the scene-sentence theme rule (see [theme-decision.md](./theme-decision.md)). Pick a palette the category does not predict. Default to terminal-default text + one accent (Restrained) until a brief forces otherwise. |
| Emoji-as-bullet for every list item | Shifts cognitive load from content to decoding glyphs; many emojis collapse to `?` on monospaced terminals or NO_COLOR pipelines; load-bearing emoji is an accessibility failure. | Plain text bullets, or status glyphs in column 0 only when the glyph carries meaning. Status by shape AND label, never shape alone. |
| Gradient banners via 24-bit ANSI | Pure decoration; degrades on 16-colour and 256-colour terminals; fails NO_COLOR; signals "AI made this". | Solid colour where colour is needed; PyFiglet only on opt-in surfaces; ASCII banner with a single brand colour for splash, never gradient. |
| Generic SaaS aesthetic in CLI form (rounded panel mimics, faux-card grids, startup-illustration ASCII art) | Imports a web template into a terminal where it has no affordance value; cards in a TUI become noise. | Honest CLI primitives: status columns, key-value tables, plain panels only when grouping is real. No card grids in a terminal. |
| Hacker aesthetic generally (Matrix-style green falling text, ASCII skulls, `[+]` / `[-]` security-tool theatre) | Intimidates beginners; second-order reflex for any tool brushing security or crypto categories; reads as costume. | Domain-specific palette chosen via scene sentence; status indicators by named state, not theatrical glyphs. |
| Electron bloat translated to CLI (heavy first-render, multi-second startup, full-screen redraw on minor state change) | The terminal is a working surface. Slowness is the loudest design failure. | First render under 200ms; partial updates over full redraws; lazy-load expensive imports; ship one fast subcommand before adding chrome. |
| Overly playful (mascots in every output, animation on every operation, exclamation marks everywhere, "Done! 🎉" on every completion) | Wears out within the first session; fatigues power users; conflicts with the dignity of long-running production tools. | Reserve personality for moments where it lands: first-run welcome, milestone completion, error recovery. Reliability carries the rest of the surface. |
| Decorative em dash use in copy | Em dashes in CLI output are a tell — they read as ChatGPT prose in a terminal that should sound terse. | Use commas, colons, semicolons, periods, or parentheses. Also not `--`. |

## Cross-register absolute bans

These apply to brand-CLI and product-CLI alike. They are inherited from the impeccable absolute-bans rule, with web-only entries removed because they have no terminal analogue.

- Lolcat-style rainbow output, gradient banners, and decorative full-line ANSI gradients
- Splash on every invocation
- Fake throbbers and spinners on instant operations
- Decorative borders on panels that group nothing
- Emoji-only status (status by shape alone, no label)
- Em dashes in CLI copy (and `--` as substitute)

## Web-only patterns explicitly NOT ported

The following web absolute bans from the impeccable system have no terminal equivalent and are not part of this list:

- Side-stripe `border-left` accents — terminals do not render thick coloured borders on individual cells
- Gradient text via `background-clip: text` — terminals cannot clip a gradient to glyph shape
- Glassmorphism — no transparency / backdrop-filter primitive in TCSS or Rich
- The hero-metric template (big number, small label, supporting stats) — no SaaS-cliche analogue
- Modal-as-first-thought — the terminal modal pattern is `questionary.confirm` and is rare by default

The CLI-native traps above replace these web-only entries. The twelve-row table is the authoritative match-and-rewrite list for terminal UI work.

## How to apply

1. Before writing any output line, scan the table for a pattern match against the line about to be produced.
2. On match, rewrite the structure using the right column. Do not patch around the pattern.
3. After implementation, re-check by running the audit dimension "Anti-Patterns & Slop" (see `./audit-checklist.md` Anti-Patterns & Slop dimension) and the AI slop test (see [ai-slop-test.md](./ai-slop-test.md)). Both gates must pass.
4. The first-altitude reflex check is the single fastest filter: if the design's theme + palette is guessable from the CLI category alone, the design has landed in a banned pattern even when no individual row of the table matched. Rework the scene sentence and colour strategy.
