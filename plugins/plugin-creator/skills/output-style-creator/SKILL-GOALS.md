# Skill Goals — output-style-creator

The purpose and explicit goals of the skill output-style-creator:

1. Decide whether an output style is the right mechanism at all — routing "Claude should know X" to
   `CLAUDE.md`, one-off launch additions to `--append-system-prompt`, focused delegated work to an
   agent, and reusable workflows to a skill — and confirm no built-in style or existing custom style
   already covers the request before authoring anything.
2. Author a valid output-style file: single-line-description YAML frontmatter, a body written as
   imperative instructions to Claude rather than third-person description of the style, no
   project-specific facts, stated exceptions for anything the style suppresses, and
   `keep-coding-instructions` set from whether the session is still software engineering.
3. Place and package the style at the correct scope — user, project, managed policy, or plugin —
   and, for a plugin style in the default `output-styles/` directory, leave the `outputStyles`
   manifest key out, because declaring it replaces that scan and hides every style not listed.
4. Activate the style through a current mechanism (`/config` or the `outputStyle` setting, never the
   removed `/output-style`), account for startup-time file reads, and test it against out-of-domain
   and error or destructive cases rather than only its happy path.
5. Diagnose a style that is not taking effect — absent from the picker, behavior unchanged, wrong
   same-named style applied, user selection overridden by `force-for-plugin`, plugin styles vanished
   after a manifest edit — from symptom to fix.

Extracted by `plugin-creator:skill-goal-extractor` from a fresh read by an agent that did not author
the skill, 2026-09-13.
