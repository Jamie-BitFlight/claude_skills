# Language Manifest Template

Canonical starting point for language manifests. All Layer 1 plugins produce a manifest conforming to this structure before composing with the harness.

**Schema**: [language-manifest-schema.md](../../../skills/dh-meta-docs/references/language-manifest-schema.md)

---

## Template

```markdown
# Language Manifest: {Language Name}

## Role Fulfillment

- architect: @{plugin}:{agent-name}
- test-designer: @{plugin}:{agent-name}
- code-reviewer: @{plugin}:{agent-name}
- design-spec: @{plugin}:{agent-name}
- linting: /{plugin}:{skill-name}

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

- **Template file**: [plugins/development-harness/templates/language-manifest-template.md](../../../../plugins/development-harness/templates/language-manifest-template.md)
- **Schema**: [language-manifest-schema.md](../../../skills/dh-meta-docs/references/language-manifest-schema.md)
