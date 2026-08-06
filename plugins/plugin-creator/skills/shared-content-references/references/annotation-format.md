# Annotation Format — The Reference Contract

Every reference to a shared doc states two things: what the doc contains, and the condition
under which the reader must open it.

Wrong:

```markdown
See references/validation.md
```

Right:

```markdown
[validation](./references/validation.md) — the exact gate commands and expected exit codes;
read before claiming any task complete.
```

An unannotated link forces the reader to open the file to find out whether it needed to be
opened — that round trip is exactly the token cost this pattern exists to avoid.

## Contrast — an existing unannotated index

`plugin-creator-meta-docs/SKILL.md` emits a bare directory listing with no annotation:

```text
!`find ${CLAUDE_PLUGIN_ROOT}/docs -name '*.md' -type f | sort`
```

A reader of that listing learns filenames, not whether any of them applies to the task at
hand — it still has to open each file to find out. The annotation contract above is the
upgrade: it puts the "should I open this" decision at the reference site instead of inside the
target file.
