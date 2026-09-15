# Workflow Pattern Taxonomy

Each language plugin documents how common workflows map to agent chains and quality gates.

---

## Patterns

| Pattern | Agent Chain | Quality Gates |
|---------|-------------|---------------|
| **TDD-equivalent** | architect → test-designer → (implement) → code-reviewer | format, lint, typecheck, test |
| **Feature Addition** | architect → design-spec → (implement) → test-designer → code-reviewer | format, lint, typecheck, test, standards |
| **Code Review** | code-reviewer | format, lint, typecheck, test |
| **Refactoring** | architect → (implement) → test-designer → code-reviewer | format, lint, typecheck, test |
| **Debugging** | (implement) → test-designer | test |

---

## Notes

- **TDD-equivalent**: Test design before implementation; tests drive design
- **Feature Addition**: Full SAM flow; design-spec produces ADR/spec artifact
- **Code Review**: Standalone review; no implementation
- **Refactoring**: Architect approves structure; tests verify behavior preserved
- **Debugging**: Focus on test pass; minimal architect involvement
