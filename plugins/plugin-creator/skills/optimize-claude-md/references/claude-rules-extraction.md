# Claude Rules Extraction Reference

## Table of Contents

1. [What is `.claude/rules/`](#what-is-clauderules)
2. [Rules file format](#rules-file-format)
3. [Path glob syntax](#path-glob-syntax)
4. [Detection heuristics](#detection-heuristics)
5. [Filename conventions](#filename-conventions)
6. [What to extract vs what to keep](#what-to-extract-vs-what-to-keep)
7. [Extraction procedure](#extraction-procedure)
8. [Replacement stub format](#replacement-stub-format)

---

## What is `.claude/rules/`

`.claude/rules/` is a Claude Code feature for modular, topic-specific project instructions. All `.md` files in `.claude/rules/` are automatically loaded as project memory. Files with a `paths` YAML frontmatter field are **conditional** — they only apply when Claude is working with files matching the specified glob patterns.

Canonical location: `.claude/rules/<slug>.md`

User-level rules (apply across all projects): `~/.claude/rules/<slug>.md`

SOURCE: <https://code.claude.com/docs/en/memory.md> (accessed 2026-02-24)

---

## Rules file format

```markdown
---
paths:
  - "src/**/*.ts"
  - "lib/**/*.ts"
---

# TypeScript Rules

- All functions must have explicit return types
- Use `unknown` instead of `any`
```

**Frontmatter fields:**
- `paths` (optional): YAML list of glob patterns. When present, rules only activate for matching files. When absent, rules apply unconditionally.

**No other frontmatter fields are used** in rules files. Do not add `name`, `description`, `model`, or other skill frontmatter fields.

---

## Path glob syntax

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | All files under `src/` |
| `*.md` | Markdown files in project root only |
| `src/components/*.tsx` | React components in a specific directory |
| `**/*.{ts,tsx}` | Both `.ts` and `.tsx` files (brace expansion) |
| `{src,lib}/**/*.ts` | TypeScript in either `src/` or `lib/` |
| `.github/workflows/**/*.yml` | All GitHub Actions workflow files |
| `**/scripts/**` | Any file under any `scripts/` directory |
| `pyproject.toml` | Specific file in project root |
| `**/*.py` | All Python files |

Brace expansion is supported. Multiple patterns are OR-combined (file matches if ANY pattern matches).

---

## Detection heuristics

A CLAUDE.md section is a candidate for extraction when it exhibits EITHER signal:

### Signal A — Content language

The section body contains phrases that scope rules to a specific file type, language, tool, path, or context. Examples:

- "When working with `*.py` files"
- "For TypeScript" / "In TypeScript code"
- "Python scripts in `plugins/**/scripts/`"
- "When the file is a `.yml` workflow"
- "In `src/api/`" / "Files under `src/`"
- "When editing GitHub Actions"
- "For scripts with shebangs"
- "`**/*.{ts,tsx}` files"

### Signal B — Heading signals

The section heading names a filetype, language, tool, or path area. Examples that qualify:

- `## Python Development Routing`
- `## CI Workflow Modification Protocol`
- `## GitHub Actions CI Workflow`
- `## TypeScript Standards`
- `## API Development Rules`
- `## Script Invocation`

### Disqualifying check (apply after either signal fires)

Even when a signal fires, DO NOT extract if the section content is **universally applicable** — i.e., the rules apply regardless of which file is being edited. Both signals must agree on scope. If the heading names Python but the rules inside apply everywhere, do not extract.

Examples of sections that should NOT be extracted despite heading signals:
- `## GitHub CLI (gh) Usage` — rules about using the `gh` CLI apply when doing any task, not just when editing `.github/` files
- `## Epistemic Identity` — applies universally
- `## Markdown Formatting Standards` — applies to all files Claude edits

---

## Filename conventions

Derive the rules filename from the section heading slug:

| Section heading | Filename |
|-----------------|----------|
| `## Python Development Routing` | `python-development.md` |
| `## CI Workflow Modification Protocol` | `ci-workflows.md` |
| `## GitHub Actions CI Workflow` | `github-actions.md` |
| `## TypeScript Standards` | `typescript.md` |
| `## Script Invocation` | `script-invocation.md` |
| `## API Development Rules` | `api-development.md` |

Rules:
- Lowercase only
- Hyphens between words, no underscores
- Drop generic suffixes: "Protocol", "Standards", "Rules", "Guidelines" → shorten to topic
- Drop "Modification", "Development", "Invocation" when heading has a clearer noun
- Max 30 characters
- Always `.md` extension

---

## What to extract vs what to keep

### Extract

Sections whose rules only apply when working with specific file types, paths, tools, or languages, and where both the heading and content agree on that scope:

- Python-specific coding rules (apply to `**/*.py`)
- CI/CD workflow rules (apply to `.github/workflows/**/*.yml`)
- TypeScript/JavaScript rules (apply to `**/*.{ts,tsx,js}`)
- API endpoint rules (apply to `src/api/**/*`)
- Test file rules (apply to `**/tests/**/*`, `**/*.test.*`)
- Script/shebang rules (apply to `**/scripts/**`)

### Keep in CLAUDE.md

- Identity and core protocol sections
- Universal behavioral rules that apply to all files — **short (≤5 lines, no procedure steps)**
- Rules about Claude's behavior, communication style, or epistemic stance
- Short sections where extraction adds overhead without benefit

**Note**: Longer processes, protocols, and procedures that are not path-scoped belong in
`docs/<slug>.md` with a one-line router entry, NOT inline in CLAUDE.md. This is the
index-routing mechanism. See [`./index-discipline.md`](./index-discipline.md) for the
discriminator flowchart and two-step saving format.

Specifically: rules about git, commits, PRs; delegation and orchestration patterns; and
sections referencing multiple unrelated file types — these are **not** exempt from extraction
when they contain substantial procedure content. Apply the discriminator:
- Short universal constraint (≤5 lines, no steps) → keep inline
- Substantial process/protocol → `docs/` via index-routing

---

## Extraction procedure

When a candidate section is identified:

1. **Determine `paths` glob** — derive from content language and heading. Be specific: `**/*.py` not `**/*`. Use brace expansion for multi-extension matches.

2. **Determine filename** — apply filename conventions above.

3. **Write the rules file** at `.claude/rules/<filename>.md`:
   - YAML frontmatter with `paths` list
   - Section heading as H1 title
   - Full section content (preserve all rules, examples, code blocks)

4. **Replace the section in CLAUDE.md** — substitute the extracted section with a compact cross-reference stub (see Replacement stub format below).

5. **Show diff** of both files after writing.

**ATOMIC**: Steps 3 and 4 happen together. Do not write one without the other.

---

## Replacement stub format

Replace the entire extracted section (heading + content) in CLAUDE.md with a single bullet reference:

```markdown
- <Topic label>: `.claude/rules/<filename>.md`
```

No heading. No "extracted to". No glob annotation. No blockquote. Just a plain bullet pointing to the file. Claude loading a fresh session has no context about what was previously there — the only useful information is where the rules live now.

---

## CoVe verification questions for extraction

After performing extraction, the CoVe post-check MUST include these additional questions:

1. **Content integrity**: Does the new rules file contain all rules from the original section verbatim?
2. **Reference accuracy**: Does the CLAUDE.md bullet point to the correct rules file path?
3. **Scope correctness**: Does the `paths` glob actually match the files the rules apply to?
4. **No universal rules extracted**: Were any rules that apply to all files accidentally moved to the rules file?
5. **CLAUDE.md coherence**: Does CLAUDE.md still read coherently after the extraction?
