---
name: output-style-creator
description: 'Create, validate, and ship Claude Code output styles — the markdown files that replace Claude Code default system instructions with a chosen role, tone, and response format. Use when asked to "create an output style", "make a custom output style", "change how Claude responds every turn", "add an output style to a plugin", "bundle output styles", "write keep-coding-instructions", "force an output style for a plugin", when an output style "is not taking effect", "does not show up in /config", or applies the wrong style, or when deciding between an output style, CLAUDE.md, a skill, or an agent for persistent behavior change.'
user-invocable: true
---

If the user's intent does not match the purpose of this skill, load `plugin-creator:plugin-lifecycle` to route to the right skill and process.

# Output Style Creator

Create output styles: markdown files whose body replaces Claude Code's default system instructions for every turn of a session. Setting `keep-coding-instructions: true` retains the built-in software engineering instructions alongside it. An output style sets role, tone, and default response format. It does not add knowledge and it does not run a workflow.

SOURCE: [Output styles](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

## Quick Reference

- [Output style schema](./references/output-style-schema.md) — frontmatter fields, install locations and resolution order, plugin packaging, subagent behavior, troubleshooting
- [Output style templates](./references/output-style-templates.md) — complete ready-to-adapt style files for common roles
- `plugin-creator:claude-skills-overview-2026` — skills system reference; its `resources/output-styles.md` mirrors this material from upstream
- `plugin-creator:skill-sync` — re-sync both files when the upstream output-styles documentation changes
- `plugin-creator:claude-plugins-reference-2026` — plugin manifest reference for `outputStyles` packaging

## Choose the Right Mechanism First

Do not create an output style when another mechanism fits. Each row below is mutually exclusive in intent.

| Need | Mechanism | Why |
| --- | --- | --- |
| Different role, tone, or response shape on every turn | Output style | Replaces the default instructions for the whole session |
| Project conventions, architecture, codebase facts | `CLAUDE.md` | Adds a user message after the system prompt; changes nothing about the defaults |
| One-off addition at launch | `--append-system-prompt` | Appends without removing the defaults |
| A separately scoped helper for one focused task | Agent | Runs its own system prompt, model, and tools |
| A reusable workflow invoked when relevant | Skill | Loads task-specific instructions on demand |

An output style is the wrong answer to "Claude should know X". It is the right answer to "Claude should always answer like X".

SOURCE: [Output styles — Comparisons to related features](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

## Built-in Styles — Check Before Creating

Confirm no built-in already covers the request:

| Style | Behavior |
| --- | --- |
| Default | Standard software engineering instructions |
| Proactive | Executes immediately, assumes instead of pausing, prefers action over planning; works without changing the permission mode, which still decides what runs without asking |
| Concise | Leads with the result, skips preamble, keeps responses short; full detail on request; requires Claude Code v2.1.237 or later |
| Explanatory | Adds educational "Insights" between engineering tasks |
| Learning | Shares insights and asks the user to write small strategic pieces; inserts `TODO(human)` markers |

SOURCE: [Output styles — Built-in output styles](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

## Your Workflow

<workflow>

### Phase 1: Discovery

1. RUN discovery. It lists user-level styles, managed-policy styles from this platform's managed settings directory, every `.claude/output-styles/` between the working directory and the repository root, and a plugin's styles at each path its `outputStyles` manifest key declares:

   ```bash
   SKILL_DIR='<absolute path of the directory holding this SKILL.md>'
   uv run "$SKILL_DIR/scripts/validate_output_style.py" discover --plugin '{plugin-path}'
   ```

   Substitute **absolute** paths in single quotes, as above; write each `'` inside a path as `'\''`. Omit `--plugin` when no plugin is in scope. `--start <directory>` walks up from somewhere other than the working directory.

2. READ the styles it lists. Claude Code loads every ancestor `.claude/output-styles/`, so a root-level style is in scope from a subdirectory, and a managed-policy style explains one in force that appears at no other level. A plugin's `outputStyles` key replaces the default scan, so a plugin shipping styles in `./extras/` has none in `output-styles/`. Report any path under `plugin_rejected_paths` or `project_rejected_paths` as a defect in the manifest or repository that declares it.
3. IDENTIFY whether the request is already served by a built-in style or an existing custom style. Adapting an existing style beats adding a near-duplicate.

### Phase 2: Requirements Gathering

ASK the user to settle these before writing, through whichever interaction mechanism the harness provides (`AskUserQuestion` in Claude Code, a plain question elsewhere):

1. Role — what is Claude acting as for the whole session?
2. Coding instructions — does the session still write and verify code? This sets `keep-coding-instructions`.
3. Response shape — what must every response contain, and in what order?
4. Scope — user, project, managed policy, or plugin-bundled.
5. Plugin activation — for a plugin style only: should it apply automatically when the plugin is enabled (`force-for-plugin`)?

Set `keep-coding-instructions: true` when the session is still software engineering and only the communication changes. Leave it out when Claude is doing something else entirely, such as writing or data analysis.

SOURCE: [Output styles — Create a custom output style](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

### Phase 3: Authoring

WRITE the file as frontmatter plus instructions. The filename becomes the style name unless `name` is set. Start from a worked style in [output-style-templates.md](./references/output-style-templates.md) rather than a blank file — six cover both `keep-coding-instructions` values and the forced-plugin case.

Authoring rules:

- Address Claude directly in the imperative. The body becomes system instructions, not documentation about the style.
- State what every response must do, not what the style is "for". "Start with the conclusion, then the evidence" is actionable; "this style is concise" is not.
- Name the exception cases. A style that shortens output must say what is never shortened — error text, security warnings, destructive-action confirmations.
- Keep the body proportionate. Every line is re-sent as input tokens on each request.
- Put project facts in `CLAUDE.md`, not here. A style that names files or conventions stops being portable.
- Do not restate Claude Code's default engineering instructions. Set `keep-coding-instructions: true` to retain them instead of paraphrasing them.

Full field semantics and defaults: [output-style-schema.md](./references/output-style-schema.md). Complete worked styles: [output-style-templates.md](./references/output-style-templates.md).

### Phase 4: Placement

| Scope | Path | Applies to |
| --- | --- | --- |
| User | `~/.claude/output-styles/{name}.md` | Every project for this user |
| Project | `.claude/output-styles/{name}.md` | This repository, checked into git |
| Managed policy | `.claude/output-styles/` inside the managed settings directory | Every user under the policy |
| Plugin | `{plugin-path}/output-styles/{name}.md` | Selectable in every session with the plugin enabled; applied without selection only with `force-for-plugin: true` |

Project styles load from every `.claude/output-styles/` between the working directory and the repository root; on a name collision the directory closest to the working directory wins. Exact per-scope paths: [output-style-schema.md](./references/output-style-schema.md#install-locations).

For a plugin style, the `output-styles/` directory is auto-discovered. Do NOT add the `outputStyles` key to `plugin.json` for styles in that default directory — declaring the key replaces the default scan entirely and makes every style outside the declared paths invisible. Add the key only for non-default locations, and then list `./output-styles/` explicitly alongside them.

SOURCE: [Plugins reference — outputStyles](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-13)

### Phase 5: Validation

RUN this check on every style, at any scope. It exits non-zero on failure and names each failure in `problems`, so a caller can gate on the exit code:

```bash
SKILL_DIR='<absolute path of the directory holding this SKILL.md>'
uv run "$SKILL_DIR/scripts/validate_output_style.py" check '{style-path}'
```

For a plugin-bundled style, also validate the containing plugin:

```bash
uvx skilllint@latest check '{plugin-path}'
if command -v claude >/dev/null; then
  claude plugin validate '{plugin-path}'
else
  echo 'SKIPPED: claude plugin validate — Claude Code CLI not installed'
fi
```

Report a skipped `claude plugin validate` in the completion report, with the manifest check still outstanding.

The script covers the frontmatter. A style with an empty body exits 0, so READ these yourself:

- [ ] `name` matches the intended display name, or is omitted deliberately so the filename supplies it
- [ ] `keep-coding-instructions` reflects whether the session still does engineering work
- [ ] `force-for-plugin` appears only in a plugin style, and only when automatic application is intended
- [ ] Body is imperative instruction to Claude, with no project-specific facts
- [ ] Exceptions are stated for anything the style suppresses or shortens
- [ ] For a plugin: `plugin.json` has no `outputStyles` key unless the styles live outside `output-styles/`

### Phase 6: Activation and Testing

ACTIVATE the style through `/config` in the terminal, the `/` command menu in the VS Code extension, or the `outputStyle` setting anywhere else. Never the standalone `/output-style` command, which was removed in v2.1.91 — do not document or script it. Per-surface steps, version floors, and the settings-precedence chain: [output-style-schema.md](./references/output-style-schema.md#selecting-a-style).

A style switch applies from the next message. In the terminal, style files are read at startup, so restart after creating or editing one mid-session; for a plugin-bundled style, `/reload-plugins` picks it up without a restart.

TEST with prompts that exercise the style's rules, not just its happy path:

1. A request squarely in the style's domain — does the shape hold?
2. A request outside it — does the style still produce sane output?
3. An error or destructive-action case — are the guaranteed-complete outputs still complete?
4. If `keep-coding-instructions: true` — does Claude still scope changes and verify work?

SOURCE: [Output styles — Change your output style](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

### Phase 7: Diagnosis

When a style does not take effect, DIAGNOSE it before re-authoring anything. Re-run Phase 1 discovery first — it shows every style in scope at every level, which settles most cases on its own: a second style of the same name in a nearer directory, or a managed-policy or plugin style you were not accounting for.

Then match the symptom in the troubleshooting table in [output-style-schema.md](./references/output-style-schema.md#troubleshooting). It covers a style absent from the picker, a style selected but with no behavior change, the wrong same-named style winning, a user selection overridden by `force-for-plugin`, plugin styles vanishing after a manifest edit, and Claude no longer scoping or verifying code changes.

</workflow>

## Anti-Patterns

<anti_patterns>

### Knowledge in a style

```markdown
# Wrong — belongs in CLAUDE.md
This project uses uv, prek, and ty. Tests live in tests/.

# Right — belongs in an output style
Lead every response with the command the user should run next.
```

### Describing the style instead of instructing Claude

```markdown
# Wrong
This output style makes Claude act like a technical writer.

# Right
You are a technical writer. Produce prose in second person, present tense. Never emit code
blocks unless the user asks for one.
```

### Expecting a style to reach subagents

Subagents run their own system prompt, so a style shapes only the main conversation and forks. A
behavior that must hold inside delegated work belongs in the agent definition.

SOURCE: [Subagents](https://code.claude.com/docs/en/sub-agents) (accessed 2026-09-13)

</anti_patterns>
