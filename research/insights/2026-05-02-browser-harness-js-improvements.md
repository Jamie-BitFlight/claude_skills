# Improvement Proposals: Browser Harness JS

**Research entry**: ./research/agent-frameworks/browser-harness-js.md
**Generated**: 2026-05-02
**Patterns assessed**: 6
**Backlog items created**: 0 (issues: none — see Deferred section)
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 3

---

## Notes on the Mapping

The research entry has no explicit "Patterns Worth Adopting" or "Integration Opportunities" sub-section. It does have a populated "Relevance to Claude Code Development" section (lines 316–334) and a "Key Features" section (lines 42–154) that names concrete patterns. These were used as the source of patterns to assess.

The closest local system to browser-harness-js is `.claude/skills/agent-browser/SKILL.md` — both are CLI bridges from Claude Code agents to Chromium browsers. Browser-harness-js is a thin CDP exposure layer; agent-browser is a Playwright-wrapped higher-level CLI. This is an architecturally different approach (raw protocol vs convenience helpers), so most "improvements" risk re-architecting the local skill rather than extending it.

For this reason, several patterns are deferred — the gaps are real but the appropriate fix would be philosophical (replace the abstraction model) rather than additive.

---

## Improvement 1: Document HTML5 drag-and-drop recipe for components that ignore Playwright's drag

**Source pattern**: "HTML5 DnD (`dragstart` / `drop` events) requires `Input.dispatchDragEvent`, not `Input.dispatchMouseEvent` alone" — research entry lines 104–117 (interaction-skills/drag-and-drop.md derivation)
**Local system**: `/home/user/claude_skills/.claude/skills/agent-browser/SKILL.md` and `/home/user/claude_skills/.claude/skills/agent-browser/references/commands.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: cannot directly observe whether `agent-browser drag @e1 @e2` (Playwright-backed) fires HTML5 dragstart/drop events without runtime testing on a real React DnD target

### Current state

`agent-browser drag @e1 @e2` is documented at `references/commands.md` line 48 with no caveat about HTML5 DnD limitations. Playwright's underlying `locator.dragTo()` is known in upstream documentation to dispatch mouse events without firing HTML5 drag events, breaking React-DnD, react-beautiful-dnd, and SortableJS targets. The skill provides no fallback recipe and no escape hatch documentation for these targets.

### Target state

`references/commands.md` includes a note adjacent to the `drag` command stating: "HTML5 DnD targets (React-DnD, react-beautiful-dnd, SortableJS) may not fire dragstart/drop events from this command. For these, use `--cdp` mode and the manual mouse+drag-event sequence documented at `references/html5-dnd-recipe.md`." A new file `references/html5-dnd-recipe.md` documents the explicit `Input.dispatchDragEvent` sequence (mouse press → wait dragIntercepted → dispatch dragEnter/dragOver/drop → mouse release).

### Measurable signal

Run: `grep -l 'dispatchDragEvent\|HTML5 DnD' /home/user/claude_skills/.claude/skills/agent-browser/references/*.md` returns at least one path. The `drag` command entry in `commands.md` contains a markdown link to the recipe file.

---

## Improvement 2: Add interaction-recipes index for non-obvious browser patterns

**Source pattern**: "Interaction Skills Library: Non-Obvious CDP Recipes ... 16 markdown files covering connection, cookies, dialogs, drag-and-drop, downloads, iframes, network waits, PDFs, screenshots, scrolling, shadow DOM, tabs, uploads, viewport" — research entry lines 100–121
**Local system**: `/home/user/claude_skills/.claude/skills/agent-browser/`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: agent-browser provides equivalents for many of these via its CLI (e.g., upload, screenshot, pdf, frame), so the gap is "named recipe coverage" rather than "missing capability". Verifying which recipes are missing vs which are covered requires a per-topic comparison.

### Current state

The agent-browser skill has reference files for `commands.md`, `snapshot-refs.md`, `session-management.md`, `authentication.md`, `video-recording.md`, `profiling.md`, and `proxy-support.md`. There is no reference file dedicated to non-obvious interaction patterns: shadow DOM traversal, iframe nesting, canvas-based apps (Figma, Excalidraw), drag-to-reorder, file download interception, or dialog handling. Agents hitting these scenarios fall back to general `eval` and trial-and-error.

### Target state

`references/interaction-recipes.md` exists, indexing one short recipe per non-obvious pattern (shadow DOM piercing, iframe activation via `agent-browser frame`, dialog dismissal, file download capture, canvas element click-by-coordinate). Each recipe is 15–40 lines with a runnable example.

### Measurable signal

Run: `ls /home/user/claude_skills/.claude/skills/agent-browser/references/interaction-recipes.md` returns the file. SKILL.md "Deep-Dive Documentation" table contains a row pointing to it.

---

## Improvement 3: Document the CDP escape hatch — when to drop from agent-browser to raw CDP

**Source pattern**: "the protocol is the API ... eliminates that boundary by making every CDP method available with full fidelity" — research entry lines 19–23, 316–334
**Local system**: `/home/user/claude_skills/.claude/skills/agent-browser/SKILL.md`
**Confidence**: Medium
**Impact**: Low
**Backlog**: Deferred — confidence Medium: the philosophical decision (Playwright-wrapped vs raw CDP) is upstream of this skill. Documenting an escape hatch is useful but its impact is bounded by how often agents actually hit Playwright's limits.

### Current state

SKILL.md lines 217–224 document `--cdp 9222` and `--auto-connect` for connecting to existing Chrome instances, but only as connection mechanisms. There is no section explaining when an agent should switch from agent-browser's high-level commands to raw CDP via `eval` or a separate tool, what the symptoms of "Playwright can't handle this" look like, or how to identify the underlying CDP method needed.

### Target state

SKILL.md adds a section "When to drop to raw CDP" listing concrete symptoms (HTML5 DnD silent failure, shadow DOM elements not appearing in snapshot, custom canvas drawings not responding to `click`, gesture sequences not triggering listeners) and pointing to the CDP reference (`https://chromedevtools.github.io/devtools-protocol/`). The section names the `eval` command as the in-skill escape (e.g., `agent-browser eval --stdin <<< "await window.cdp.send('Input.dispatchDragEvent', {...})"`).

### Measurable signal

Run: `grep -c 'When to drop to raw CDP\|chromedevtools.github.io/devtools-protocol' /home/user/claude_skills/.claude/skills/agent-browser/SKILL.md` returns a value greater than 0.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| HTML5 drag-and-drop recipe | Medium | Cannot observe Playwright's actual dragTo behavior on HTML5 DnD targets without runtime test against a React-DnD or SortableJS page. The research entry only proves the CDP recipe exists, not that Playwright fails. |
| Interaction recipes index | Medium | Per-topic gap analysis between the 16 external recipes and agent-browser's existing CLI commands not performed. Many topics (upload, screenshot, pdf, frame, scroll) are already covered as commands. |
| Raw CDP escape hatch documentation | Medium | The "Playwright can't handle this" failure modes are real but the frequency of occurrence in this repo's actual agent workflows is unverified. Adds documentation surface for an uncommon path. |

To raise any of these to High confidence: run a real React-DnD page through `agent-browser drag @e1 @e2` and observe whether the drop handler fires. If it does not, gap 1 becomes High confidence.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Auto-detect running Chromium browsers across profile dirs (research entry §2, lines 64–82) | Already covered — agent-browser's `--auto-connect` flag is documented at SKILL.md lines 217–223 and serves the same use case. |
| Persistent session with state routing by target ID (research entry §3, lines 85–98) | Already covered — agent-browser's named sessions (`--session`) and background daemon are documented at SKILL.md lines 168–213, 320–340. The mechanism differs (session name vs target ID) but the outcome is equivalent. |
| Codegen of typed wrappers from CDP JSON (research entry §1, "Technical Architecture") | Architecturally incompatible — agent-browser delegates protocol layer to Playwright; reimplementing 652 typed CDP wrappers would replace the local skill's foundation, not extend it. |
