# Permissions — Detailed Reference

Complete reference for Claude Code permission rules, patterns, edge cases, and deployment configurations.

---

## Table of Contents

1. [Bash Permission Patterns](#bash-permission-patterns)
2. [Read and Edit Patterns](#read-and-edit-patterns)
3. [WebFetch Patterns](#webfetch-patterns)
4. [MCP Permission Patterns](#mcp-permission-patterns)
5. [Task Permission Patterns](#task-permission-patterns)
6. [Hook-Based Permission Extension](#hook-based-permission-extension)
7. [Example Configurations](#example-configurations)
8. [Common Pitfalls](#common-pitfalls)

---

## Bash Permission Patterns

### Wildcard Matching

The `*` wildcard can appear at any position:

| Pattern | Matches | Does NOT Match |
|---------|---------|----------------|
| `Bash(npm run build)` | Exact command `npm run build` | `npm run test` |
| `Bash(npm run *)` | `npm run build`, `npm run test` | `npm install` |
| `Bash(npm *)` | Any command starting with `npm` | `npx create-app` |
| `Bash(* install)` | `npm install`, `pip install` | `npm install -g` |
| `Bash(git * main)` | `git checkout main`, `git merge main` | `git checkout dev` |
| `Bash(* --version)` | `node --version`, `python --version` | `node --help` |

### Word Boundary Behavior

The space before `*` creates a word boundary:

- `Bash(ls *)` — matches `ls -la`, `ls src/` — does NOT match `lsof`
- `Bash(ls*)` — matches `ls -la`, `ls src/`, AND `lsof`

**Legacy syntax**: `Bash(ls:*)` is equivalent to `Bash(ls *)` but is deprecated.

### Shell Operator Awareness

Claude Code detects shell operators. Prefix match rules do NOT approve commands chained with operators:

- Rule: `Bash(safe-cmd *)`
- Matches: `safe-cmd --flag value`
- Does NOT match: `safe-cmd && malicious-cmd`

### Bash Pattern Fragility Warning

Patterns constraining command arguments are fragile. Example — `Bash(curl http://github.com/ *)` intends to restrict curl to GitHub URLs, but fails for:

- Options before URL: `curl -X GET http://github.com/...`
- Different protocol: `curl https://github.com/...`
- Redirects: `curl -L http://bit.ly/xyz` (redirects to github)
- Variables: `URL=http://github.com && curl $URL`
- Extra spaces: `curl  http://github.com`

**Better approaches**:
1. Deny `curl`/`wget` in Bash, use `WebFetch(domain:github.com)` for allowed domains
2. Implement PreToolUse hooks that validate URLs
3. Document allowed patterns in CLAUDE.md

**Note**: WebFetch alone does NOT prevent network access. If Bash is allowed, Claude can still use `curl`, `wget`, etc.

---

## Read and Edit Patterns

### Pattern Types (Gitignore Specification)

**Absolute paths** (from filesystem root):

<eg>
Read(//Users/alice/secrets/**)
Edit(//tmp/scratch.txt)
</eg>

The double-slash `//` prefix indicates absolute path. A single `/` is relative to the settings file.

**Home directory paths**:

<eg>
Read(~/Documents/*.pdf)
Read(~/.zshrc)
</eg>

**Settings-file-relative paths**:

<eg>
Edit(/src/**/*.ts)      # Relative to the settings file location
Edit(/docs/**)           # NOT the filesystem /docs/
</eg>

**Current-directory-relative paths**:

<eg>
Read(*.env)
Read(src/**)
Read(./config/*)
</eg>

### Glob Behavior

| Pattern | Matches |
|---------|---------|
| `*` | Files in a single directory |
| `**` | Files recursively across directories |
| `*.ts` | TypeScript files in current directory only |
| `**/*.ts` | TypeScript files in any subdirectory |

### Match All

Use tool name without parentheses to allow all file operations:

- `Read` — all file reads
- `Edit` — all file edits
- `Write` — all file writes

`Edit` rules apply to ALL built-in file editing tools. `Read` rules apply best-effort to all read tools including Grep and Glob.

---

## WebFetch Patterns

Currently supports domain-based matching:

<eg>
WebFetch(domain:example.com)
WebFetch(domain:api.github.com)
</eg>

---

## MCP Permission Patterns

Match by server name and optionally by tool name:

| Pattern | Matches |
|---------|---------|
| `mcp__puppeteer` | All tools from `puppeteer` server |
| `mcp__puppeteer__*` | Same (wildcard all tools) |
| `mcp__puppeteer__puppeteer_navigate` | Specific tool only |

The server name is the name configured in Claude Code MCP settings (not the npm package name).

---

## Task Permission Patterns

Control which subagents Claude can use:

| Pattern | Matches |
|---------|---------|
| `Agent(Explore)` | Built-in Explore agent |
| `Agent(Plan)` | Built-in Plan agent |
| `Agent(general-purpose)` | Built-in general-purpose agent |
| `Agent(my-custom-agent)` | Custom agent by name |

---

## Hook-Based Permission Extension

[Claude Code hooks](https://code.claude.com/docs/en/hooks-guide.md) can extend the permission system:

- PreToolUse hooks run before the permission system evaluates
- Hook output can approve or deny tool calls in place of the permission system
- Use for complex validation logic that cannot be expressed as static rules

Example: A PreToolUse hook that validates URLs in Bash commands against an allowlist, providing dynamic URL filtering that static Bash patterns cannot achieve.

---

## Example Configurations

### Development Team — Balanced

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Edit(/src/**)",
      "Edit(/tests/**)"
    ],
    "deny": [
      "Bash(git push *)",
      "Bash(git reset *)",
      "Bash(rm -rf *)",
      "Edit(//.env*)",
      "Read(//.env*)"
    ]
  }
}
```

### CI/CD — Restrictive

```json
{
  "defaultMode": "dontAsk",
  "permissions": {
    "allow": [
      "Bash(npm run build)",
      "Bash(npm run test)",
      "Bash(npm run lint)",
      "Read"
    ],
    "deny": [
      "Bash(npm publish *)",
      "Bash(git push *)",
      "Edit"
    ]
  }
}
```

### Organization Managed — Lockdown

Deploy as `managed-settings.json`:

```json
{
  "disableBypassPermissionsMode": "disable",
  "allowManagedPermissionRulesOnly": true,
  "allowManagedHooksOnly": true,
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(git *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl *)",
      "Bash(wget *)",
      "Edit(//etc/**)",
      "Read(//etc/shadow)"
    ]
  }
}
```

---

## Common Pitfalls

### Absolute Path Confusion

<eg>
Edit(/Users/alice/file)     # WRONG — relative to settings file
Edit(//Users/alice/file)    # CORRECT — absolute path
</eg>

Single `/` prefix means "relative to the settings file", not filesystem root.

### Bash Wildcard Without Space

<eg>
Bash(npm*)     # Matches: npm, npmrc, npm-audit — probably too broad
Bash(npm *)    # Matches: npm install, npm run — correct word boundary
</eg>

### Deny Rule Placement

Deny rules always win regardless of order, but for readability, list them explicitly:

```json
{
  "permissions": {
    "deny": ["Bash(git push --force *)"],
    "allow": ["Bash(git push *)"]
  }
}
```

### WebFetch Does Not Block Bash Network Access

Allowing `Bash` while denying `WebFetch` does NOT prevent network access:

```json
{
  "permissions": {
    "allow": ["Bash"],
    "deny": ["WebFetch"]
  }
}
```

Claude can still run `curl`, `wget`, `nc`, etc. via Bash. To restrict network access, deny those Bash commands too or use sandboxing.

---

## Sources

- [Claude Code Permissions Documentation](https://code.claude.com/docs/en/permissions.md) (accessed 2026-02-17)
- [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings.md) (accessed 2026-02-17)
- [Claude Code Sandboxing Documentation](https://code.claude.com/docs/en/sandboxing.md) (accessed 2026-02-17)
- [Example settings configurations](https://github.com/anthropics/claude-code/tree/main/examples/settings)
