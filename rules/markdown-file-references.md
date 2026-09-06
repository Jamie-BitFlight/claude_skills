# Markdown & File Reference Standards

## Code Fence Standards

Add a language specifier to every code fence, and surround every fenced code block with blank lines (MD031). Nested fences use 4 backticks on the outer fence and 3 on inner fences.

````markdown
# Section Title

This is a paragraph.

```python
def example():
    return True
```

This is another paragraph.
````

## Markdown Links

Use markdown links with relative paths starting with `./`. **Reason**: Enables Claude Code click-through, works regardless of installation location, and supports on-demand file loading.

**Syntax**: `[descriptive text](./path/to/file.md)`

**Directory Context:**
- From SKILL.md → references: `[text](./references/filename.md)`
- From references/file.md → same dir: `[text](./filename.md)`
- From references/file.md → subdir: `[text](./subdir/filename.md)`

Use a markdown link for any real relative path; a bare backticked path (`modern-modules/httpx.md`) and an absolute path (`/home/user/...`) both fail. External file: full URL with access date. The one path form that takes backticks instead is the substituted form below.

**Exception — `.claude/` and `rules/`:** these files are injected as raw text at the agent's cwd (repo root), never browsed via GitHub/editor click-through. Links there are repo-root-relative, no `./` prefix. Do not "fix" them back to file-relative.

**Exception — substituted paths in a `SKILL.md` body:** `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` substitute at load time throughout the rendered body, link targets included, so they resolve in any environment a plugin is installed into.

Write these as a **backticked path**, not a markdown link:

```markdown
`${CLAUDE_PLUGIN_ROOT}/docs/runtime-environment.md` — contains <what>; read before <when>.
```

The backtick is a workaround for a `skilllint` bug, not a property of the syntax. `skilllint` does expand both variables (`rules/lk_series.py`, `_STATICALLY_RESOLVABLE_CLAUDE_VARS`), but when it is invoked with a **relative** path it resolves the plugin root to a relative path too and then joins that onto the skill directory, producing `…/skills/<name>/plugins/<plugin>/…` and a false LK001. The same check passes when invoked with an absolute path. Pre-commit passes relative paths, so the link form cannot be committed until that is fixed upstream; revert to the markdown-link form once it is.

Keep the annotation contract — what the file contains, when to read it — that a link would have carried.

Does not apply inside `references/*.md`, which are never substituted; those keep real `./`-relative paths in markdown links. See `skill-substitution.md`.

## Skill Activation References

Reference other skills using activation syntax:

✅ `For comprehensive linting documentation, use the /holistic-linting:holistic-linting skill.`
❌ `See /holistic-linting:holistic-linting/SKILL.md for linting documentation`

## Subdirectory Namespaces — Skills Do NOT Support This

Skills in subdirectories under `skills/` silently fail to register. Subdirectory namespacing (`plugin:group:skill-name`) was a `commands/` feature only.

- `skills/testing/analyze-test-failures/SKILL.md` → **DEAD — not registered**
- `skills/analyze-test-failures/SKILL.md` → `/plugin:analyze-test-failures` — correct

All skill directories must sit directly under `skills/` — one level deep only. Do not create grouping subdirectories.
