# Agent Delegation — Path Conventions and Agent Selection

## Path Conventions

Use paths relative to current working directory when delegating to sub-agents.

```mermaid
flowchart TD
    Start([Construct path for sub-agent]) --> Q{Path starts with?}
    Q -->|"./ relative"| Use[Use as-is]
    Q -->|"/home/ or /usr/"| Abs["Convert to ../../relative/path"]
    Q -->|"~/.claude/skills/"| Sym["Convert to ~/.claude/skills/"]
    Abs -->|Why| Reason1[Absolute paths are verbose and non-portable]
    Sym -->|Why| Reason2[Symlink paths trigger manual approval on every file op]
    Use --> Done([Sub-agent inherits same working directory])
```

## Agent Selection

```mermaid
flowchart TD
    Start([Select agent for task]) --> Q1{Task requires reasoning, interpretation, or analysis?}
    Q1 -->|No — exact file pattern or keyword search| Explore[Explore agent acceptable]
    Q1 -->|Yes| Q2{Needs repo convention awareness?}
    Q2 -->|Yes| CG[context-gathering agent]
    Q2 -->|No — general interpretation| Q3{Prompt optimization or AI-facing content?}
    Q3 -->|Yes| CCO[contextual-ai-documentation-optimizer agent]
    Q3 -->|No| CG
    Explore -.->|⚠️ Haiku-based, unreliable on ambiguous queries| Warning[Never use for reasoning tasks]
```

**Never use Explore for reasoning tasks.** Its failure modes:
- Semantic ambiguity: matches the wrong domain concept (e.g. pre-commit hooks instead of Claude Code hooks)
- Premature termination: declares "not found" instead of searching deeper
- Fabricated implementations: suggests a technology/pattern the repo doesn't use
