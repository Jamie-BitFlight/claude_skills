---
name: output-style-creator
description: Create, validate, and diagnose Claude Code output styles — the file that sets Claude's role, tone, and response format for every turn. Use when asked to write, bundle, or force an output style for a plugin, to set keep-coding-instructions or force-for-plugin, when a style is not taking effect or the wrong one applies, or when choosing between an output style, CLAUDE.md, a skill, and an agent for a persistent behavior change.
user-invocable: true
---

If the user's intent does not match the purpose of this skill, load `plugin-creator:plugin-lifecycle` to route to the right skill and process.

# Output Style Creator

Create output styles: markdown files whose body replaces Claude Code's default system instructions for every turn of a session. Setting `keep-coding-instructions: true` retains the built-in software engineering instructions alongside it. An output style sets role, tone, and default response format.

SOURCE: [Output styles](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

## Quick Reference

- [Output style schema](./references/output-style-schema.md) — frontmatter fields, install locations and resolution order, plugin packaging, subagent behavior, troubleshooting
- [Output style templates](./references/output-style-templates.md) — complete ready-to-adapt style files for common roles
- `plugin-creator:claude-plugins-reference-2026` — plugin manifest reference for `outputStyles` packaging

## Choose the Right Mechanism First

Pick the mechanism from this table before writing anything.

| Need | Mechanism | Why |
| --- | --- | --- |
| Different role, tone, or response shape on every turn | Output style | Replaces the default instructions for the whole session |
| Project conventions, architecture, codebase facts | `CLAUDE.md` | Adds a user message after the system prompt; changes nothing about the defaults |
| One-off addition at launch | `--append-system-prompt` | Appends without removing the defaults |
| A separately scoped helper for one focused task, or any behavior that must hold inside delegated work | Agent | Runs its own system prompt, model, and tools — an output style never reaches a subagent |
| A reusable workflow invoked when relevant | Skill | Loads task-specific instructions on demand |

An output style is the wrong answer to "Claude should know X". It is the right answer to "Claude should always answer like X".

SOURCE: [Output styles — Comparisons to related features](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

SOURCE: [Subagents](https://code.claude.com/docs/en/sub-agents) (accessed 2026-09-13)

## Built-in Styles — Check Before Creating

| Style | Behavior |
| --- | --- |
| Default | Standard software engineering instructions |
| Proactive | Executes immediately, assumes instead of pausing, prefers action over planning; stronger than auto mode's autonomous-execution guidance and independent of the permission mode, which still decides what runs without asking |
| Concise | Leads with the result, skips preamble, keeps responses short; full detail on request; always delivers error reports, security warnings, and destructive-action confirmations complete; requires Claude Code v2.1.237 or later |
| Explanatory | Adds educational "Insights" between engineering tasks |
| Learning | Shares insights and asks the user to write small strategic pieces; inserts `TODO(human)` markers |

SOURCE: [Output styles — Built-in output styles](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

## Your Workflow

<workflow>

### Phase 1: Discovery

1. RUN discovery:

   ```bash
   uv run "${CLAUDE_SKILL_DIR}/scripts/validate_output_style.py" discover --plugin '{plugin-path}'
   ```

   Omit `--plugin` when no plugin is in scope.

2. READ the styles it lists. A nearer `.claude/output-styles/` **shadows** a farther one, and a plugin's `outputStyles` key shadows the plugin's default `output-styles/` directory — so a style you cannot see may be the one in force, and a directory you can see may be scanned by nobody. Report anything under `plugin_manifest_problems`, `plugin_rejected_paths`, or `project_rejected_paths` as a defect in the manifest or repository that declares it. A plugin with a manifest problem reports no styles, because the declaration that would name them cannot be read — that is a broken manifest, not a plugin shipping nothing.
3. IDENTIFY whether the request is already served by a built-in style or an existing custom style. Adapting an existing style beats adding a near-duplicate.

### Phase 2: Requirements Gathering

ASK the user to settle these before writing, through whichever interaction mechanism the harness provides (`AskUserQuestion` in Claude Code, a plain question elsewhere):

1. Role — what is Claude acting as for the whole session?
2. Coding instructions — does the session still write and verify code? This sets `keep-coding-instructions`.
3. Response shape — what must every response contain, and in what order?
4. Scope — user, project, managed policy, or plugin-bundled.
5. Plugin activation — for a plugin style only: should it apply automatically when the plugin is enabled (`force-for-plugin`)?
6. Picker line — the one line that tells a user in the `/config` list when to pick this style over the others already installed. This becomes `description`.

Set `keep-coding-instructions: true` when the session is still software engineering and only the communication changes. Leave it out when Claude is doing something else entirely, such as writing or data analysis.

SOURCE: [Output styles — Create a custom output style](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

### Phase 3: Authoring

WRITE the file as frontmatter plus instructions. The filename becomes the style name unless `name` is set. Start from a worked style in [output-style-templates.md](./references/output-style-templates.md) rather than a blank file; its Selection Guide maps the `keep-coding-instructions` decision and the forced-plugin case onto a starting template.

Authoring rules:

- Write the body as a **system prompt**, not a README about the style. `Start with the conclusion, then the evidence` is a system prompt; `this style is concise` is a README.
- State the target behavior, not the ban. The body is re-sent as system instructions every turn, so a prohibition keeps the forbidden behavior loaded and half-reads as an instruction to perform it. `Deliver error text in full` beats `Never truncate error text`. Keep a prohibition only where the failure is silent and total, and pair it with the positive.
- Name the exception cases. A style that shortens output must say what stays complete — error text, security warnings, destructive-action confirmations.
- Keep the body proportionate. Every line is re-sent as input tokens on each request.
- Put project facts in `CLAUDE.md`. A style that names files or conventions stops being portable.
- Retain the default engineering instructions with `keep-coding-instructions: true` rather than paraphrasing them.

Full field semantics and defaults: [output-style-schema.md](./references/output-style-schema.md).

### Phase 4: Placement

| Scope | Path | Applies to |
| --- | --- | --- |
| User | `~/.claude/output-styles/{name}.md` | Every project for this user |
| Project | `.claude/output-styles/{name}.md` | This repository, checked into git |
| Managed policy | `.claude/output-styles/` inside the managed settings directory | Every user under the policy |
| Plugin | `{plugin-path}/output-styles/{name}.md` | Selectable in every session with the plugin enabled; applied without selection only with `force-for-plugin: true` |

For a plugin style, the `output-styles/` directory is auto-discovered. Do NOT add the `outputStyles` key to `plugin.json` for styles in that default directory — declaring the key replaces the default scan entirely and makes every style outside the declared paths invisible. Add the key only for non-default locations, and then list `./output-styles/` explicitly alongside them.

SOURCE: [Plugins reference — outputStyles](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-13)

### Phase 5: Validation

RUN this check on every style, at any scope:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/validate_output_style.py" check '{style-path}'
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

- [ ] `description` is one line and says when to pick this style, not what it is named
- [ ] `name` matches the intended display name, or is omitted deliberately so the filename supplies it
- [ ] `keep-coding-instructions` reflects whether the session still does engineering work
- [ ] `force-for-plugin` appears only in a plugin style, and only when automatic application is intended
- [ ] Body is imperative instruction to Claude, with no project-specific facts
- [ ] Exceptions are stated for anything the style suppresses or shortens
- [ ] Every rule in the body is observable in a response — a reader could tell whether it was followed
- [ ] For a plugin: `plugin.json` has no `outputStyles` key unless the styles live outside `output-styles/`

### Phase 6: Activation and Testing

ACTIVATE the style through `/config` in the terminal, the `/` command menu in the VS Code extension, or the `outputStyle` setting anywhere else. Never the standalone `/output-style` command, which was removed in v2.1.91. Per-surface steps, version floors, and the settings-precedence chain: [output-style-schema.md](./references/output-style-schema.md#selecting-a-style).

A style switch applies from the next message. In the terminal, style files are read at startup, so restart after creating or editing one mid-session; for a plugin-bundled style, `/reload-plugins` picks it up without a restart.

TEST all four prompts below, and record for each the prompt sent, the rule it exercises, and whether the rule held:

1. A request squarely in the style's domain — every ordering and formatting rule in the body holds.
2. A request outside it — the answer is still correct and complete, and the style's rules apply only where they fit.
3. An error case and a destructive-action case — the carve-outs are delivered verbatim and at full length.
4. If `keep-coding-instructions: true` — Claude still scopes the change and states how it verified the work.

A rule the four prompts never exercise is a rule you have not tested. Add a prompt until every rule in the body has been exercised at least once.

SOURCE: [Output styles — Change your output style](https://code.claude.com/docs/en/output-styles) (accessed 2026-09-13)

### Phase 7: Diagnosis

When a style does not take effect, DIAGNOSE it before re-authoring anything. Re-run Phase 1 discovery first — it shows every style in scope at every level, which settles most cases on its own: a second style of the same name in a nearer directory, or a managed-policy or plugin style you were not accounting for.

Then match the symptom in the troubleshooting table in [output-style-schema.md](./references/output-style-schema.md#troubleshooting). It covers a style absent from the picker, the wrong same-named style winning, and Claude no longer scoping or verifying code changes.

</workflow>
