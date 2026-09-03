# Language Manifest Template

Canonical starting point for language manifests. All Layer 1 plugins produce a manifest conforming to this structure before composing with the harness.

**Schema**: [language-manifest-schema.md](../../../skills/dh-meta-docs/references/language-manifest-schema.md)

---

## Template

Agent resolution (architect, test-designer, code-reviewer, design-spec, linting) is not part of
this template — the harness resolves agents at runtime via `profile_list()`, matching task
content against every installed agent's own declared capability. See
[role-resolution-protocol.md](../../../skills/dh-meta-docs/references/role-resolution-protocol.md).
Nothing reads a "Role Fulfillment" section.

```markdown
# Language Manifest: {Language Name}

## Quality Gates

- format: `{format command} {files}`
- lint: `{lint command} {files}`
- typecheck: `{typecheck command} {files}` or `(none)` for non-typed languages
- test: `{test command}`
- standards: /{plugin}:{standards-skill}

## Project Detection

- markers: {config files that identify this language}
- source-patterns: {glob patterns for source files}
- test-patterns: {glob patterns for test files}

## Conventions (Optional)

- naming: {rules array}
- structure: {rules array}
- testing: {rules array}
- documentation: {rules array}

## Process Flow Override

(none — uses default harness flow)
```

---

## Quick Reference

- **Template file**: [plugins/development-harness/templates/language-manifest-template.md](../../../templates/language-manifest-template.md)
- **Schema**: [language-manifest-schema.md](../../../skills/dh-meta-docs/references/language-manifest-schema.md)
