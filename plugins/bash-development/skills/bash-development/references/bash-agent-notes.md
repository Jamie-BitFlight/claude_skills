# Notes for Bash Script Developer Agent

## Context-Aware Code Review

When reviewing shell scripts, especially internal tools and libraries, avoid knee-jerk reactions to common patterns. Consider the actual context and threat model before flagging issues.

## Eval Usage - A Nuanced Approach

### Stop the "Eval is Always Bad" Cargo Cult

Eval is a legitimate shell feature with valid use cases. Don't automatically flag every eval as dangerous without analyzing:

1. **Where the input comes from** - Is it user-supplied or internally controlled?
2. **The actual risk** - What's the threat model for this code?
3. **The alternatives** - Would avoiding eval make the code worse?

### When Eval IS Appropriate

- **Indirect variable expansion** in POSIX-compatible scripts (before bash 4.3 namerefs)
- **Dynamic variable name resolution** from controlled sources
- **Shell integration scripts** (like `eval "$(brew shellenv)"`)
- **Building complex commands** from trusted configuration

### When Eval IS Dangerous

- **User input** passed directly to eval
- **Network data** or file contents from untrusted sources
- **Web form input** or API parameters
- **Any external data** that hasn't been validated/sanitized

### Example of Safe Eval Usage

```bash
# Safe: Variable name built from controlled transformation
color_var_name="COLOR_$(echo "$1" | tr '[:lower:]' '[:upper:]')"
eval 'resolved_color="${'"${color_var_name}"':-}"'

# Safe: Shell integration from trusted tool
eval "$(starship init bash)"

# Safe: Dynamic variable assignment in controlled loop
for i in 1 2 3; do
    eval "var_${i}=value_${i}"
done
```

## Repository Context Matters

### Internal/Private Repositories

For internal tools in private repositories:

- The threat model is different from public-facing code
- Developers are trusted actors, not adversaries
- The focus should be on correctness and maintainability
- Security should be proportional to actual risk

### This Repository (Shlocksmith)

- **Private repository** used by a small internal team
- **Developer tool** for firmware development automation
- **CI/CD pipeline** usage with controlled inputs
- **Not exposed** to external users or untrusted input

## Design Patterns to Recognize

### Intentional Execution at Source Time

Some scripts are designed to execute code when sourced:

```bash
# bootstrap.sh - Sets up environment when sourced
shlocksmith_resolve_missing_environment_variables  # This is intentional!

# add_to_path.sh - Adds to PATH when sourced
add_to_path_if_missing "${HOME}/.local/bin"  # This is the whole point!
```

Don't flag these as issues - they're the primary purpose of these files.

### Dynamic Export Patterns

Libraries that generate many variables often use dynamic exports:

```bash
# Exporting all color variables without maintaining a manual list
for var in $(set | grep -E '^COLOR_' | cut -d= -f1); do
    export "${var}"
done
```

This is a reasonable pattern for maintaining large sets of related variables.

### Shell Detection Functions

Cross-shell compatible libraries often have "weird" shell detection:

```bash
# These patterns are intentional for shell detection
case "${-}" in
    *i*) INTERACTIVE=true ;;
esac

# Version detection across different shells
: "${BASH_VERSION:+bash}" "${ZSH_VERSION:+zsh}"
```

These aren't bugs - they're compatibility features.

## Review Principles

1. **Understand the purpose** before critiquing the implementation
2. **Consider the threat model** - not all code faces the internet
3. **Respect intentional design** - especially in library code
4. **Avoid cargo cult** - question "best practices" that don't apply
5. **Context matters** - internal tools != public web services

## Common False Positives to Avoid

- ❌ "Never use eval" - Sometimes it's the right tool
- ❌ "Don't execute at source time" - Some scripts are designed for this
- ❌ "All variables must be quoted" - Not in arithmetic contexts
- ❌ "Avoid dynamic variables" - Sometimes necessary for POSIX compatibility
- ❌ "Never use uppercase variables" - Fine for exported environment variables

## Remember

The goal is to improve code quality and catch real issues, not to enforce dogmatic rules that don't apply to the context. A good review considers:

- The intended use case
- The target environment
- The actual threat model
- The maintenance trade-offs
- The team's conventions

Be pragmatic, not dogmatic.
