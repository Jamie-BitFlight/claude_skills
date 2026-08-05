# Proactive Fix Gate (Required Before Any Self-Initiated Fix)

Before acting on any problem discovered during a session — regardless of how obvious the fix
appears — execute the following three steps in order. All three must complete before touching
any file.

**Step 1 — Domain skill loaded?**
Identify the plugin or subsystem that owns the affected file. Load its domain skill (e.g.,
`/holistic-linting:holistic-linting`, `/dh:work-backlog-item`) if not already active in this
session. Without the skill loaded, plugin markdown files are static documentation. With the
skill loaded, they are behavioral contracts. The quality judgment in Step 2 requires the skill.

Observable pass criterion: The skill's SKILL.md has been Read in this session, or the skill was
loaded via Skill() call. Name the skill you loaded.

Observable fail criterion: You cannot identify the owning skill, or the skill does not exist.
Action on fail: Proceed to Step 3 and route to planning — do not fix without domain context.

**Step 2 — Aligned with mission objective?**
Read the mission statement or design intent section of the affected plugin's SKILL.md. State
in one sentence how the fix improves or maintains alignment with the stated mission. If you
cannot produce this sentence, the fix is not ready — add it to the plan instead.

Observable pass criterion: You have produced and can state the one-sentence alignment claim.
Observable fail criterion: No mission statement is readable, or the fix's alignment is unclear.
Action on fail: Proceed to Step 3 and route to planning.

**Step 3 — Route by complexity**

Classify the fix using the criteria below, then route accordingly.

Trivial fix (route to `--quick`):
- Affects exactly one file
- Root cause is directly observable (a missing import, a broken link, an incorrect constant,
  a failing assertion with an obvious correction)
- Requires no design decision (the correct value or structure is unambiguous from context)
- Requires no new skill to be loaded beyond what Step 1 identified
- All changes fit inside a single Edit or Write call

Multi-file or design-decision fix (route to planning):
- Touches two or more files, OR
- Requires a judgment about which approach is correct (two or more valid implementations exist
  and the choice has design implications), OR
- Requires loading an additional skill beyond the one identified in Step 1, OR
- The root cause is a pattern repeated across multiple locations

When routed to `--quick`:
Invoke `/dh:work-backlog-item --quick {item title or #N}` whether or not a backlog item already
exists. The `--quick` workflow (quick/start.md Step 2) handles item creation internally when no
prior item exists — do not pre-create one.

Do NOT call `backlog_add` for a fix you are about to perform immediately — that creates
unnecessary grooming overhead for work already in flight.

When routed to planning:
Invoke `/dh:work-backlog-item create -- "{problem description}"` to register the item and defer
the fix to a planned session. Do not attempt the fix in the current session.

**Invocation mechanics**
The `--quick` path is invoked as a mode flag (`flags.quick = true`), not a registry command.
The parser translates `/dh:work-backlog-item --quick {title}` into `flags.quick = true` with
`item_ref = [{title}]`. Do not construct the invocation any other way.
