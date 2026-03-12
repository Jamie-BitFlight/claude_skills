---
name: bash-logging
description: This skill should be used when the user asks to "add logging to bash script", "colorize output", "implement log levels", "CI/CD sections", "terminal colors in bash", or mentions logging functions, emoji output, collapsible CI sections, or shlocksmith.
---
# Bash Logging

Structured logging patterns for bash scripts with color support, emoji icons, and CI/CD integration.

## Basic Logging Functions

Simple, portable logging implementation:

```bash
# Color definitions
declare -A colors=(
    [green]=$'\033[0;32m'
    [red]=$'\033[0;31m'
    [yellow]=$'\033[1;33m'
    [blue]=$'\033[0;34m'
    [reset]=$'\033[0m'
)

declare -A emojis=(
    [success]='✅'
    [error]='❌'
    [warning]='⚠️'
    [info]='ℹ️'
    [debug]='🐛'
)

# Logging functions
print_success() {
    printf '%b %b%b%b\n' "${emojis[success]}" "${colors[green]}" "$*" "${colors[reset]}"
}

print_error() {
    printf '%b %b%b%b\n' "${emojis[error]}" "${colors[red]}" "$*" "${colors[reset]}" >&2
}

print_warning() {
    printf '%b %b%b%b\n' "${emojis[warning]}" "${colors[yellow]}" "$*" "${colors[reset]}"
}

print_info() {
    printf '%b %b\n' "${emojis[info]}" "$*"
}

print_debug() {
    [[ -n "${DEBUG:-}" ]] && printf '%b %b%b%b\n' "${emojis[debug]}" "${colors[blue]}" "$*" "${colors[reset]}"
}
```

## Log Levels

Implement configurable log levels.

[Code examples](./references/code-examples.md#log-levels)

## TTY Detection

Disable colors in non-interactive environments:

```bash
setup_colors() {
    if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
        # Terminal supports colors
        COLOR_RED=$'\033[0;31m'
        COLOR_GREEN=$'\033[0;32m'
        COLOR_YELLOW=$'\033[1;33m'
        COLOR_BLUE=$'\033[0;34m'
        COLOR_RESET=$'\033[0m'
    else
        # No color support
        COLOR_RED=''
        COLOR_GREEN=''
        COLOR_YELLOW=''
        COLOR_BLUE=''
        COLOR_RESET=''
    fi
}

# CI environments often support colors
detect_color_support() {
    if [[ -n "${CI:-}" ]] || [[ -n "${GITLAB_CI:-}" ]] || [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        return 0  # CI environment, enable colors
    elif [[ -t 1 ]]; then
        return 0  # Terminal, enable colors
    else
        return 1  # No color support
    fi
}
```

## GitLab CI Collapsible Sections

Create collapsible log sections in GitLab CI:

```bash
section_start() {
    local section_key="\${1:-section}"
    local section_header="\${2:-$section_key}"
    local collapsed="\${3:-true}"

    if [[ -n "${GITLAB_CI:-}" ]]; then
        printf "\e[0Ksection_start:%s:%s[collapsed=%s]\r\e[0K%s\n" \
            "$(date +%s)" "$section_key" "$collapsed" "$section_header"
    else
        printf '\n=== %s ===\n' "$section_header"
    fi
}

section_end() {
    local section_key="\${1:-section}"

    if [[ -n "${GITLAB_CI:-}" ]]; then
        printf "\e[0Ksection_end:%s:%s\r\e[0K" "$(date +%s)" "$section_key"
    else
        printf '\n'
    fi
}

# Usage
section_start "build" "Building Application"
make build
section_end "build"
```

## GitHub Actions Grouping

[Code examples](./references/code-examples.md#github-actions-grouping)

## Progress Indicators

[Code examples](./references/code-examples.md#progress-indicators)

## Structured Step Logging

[Code examples](./references/code-examples.md#structured-step-logging)

## Shlocksmith Logging Library

For comprehensive logging with full CI integration, use the shlocksmith logging library.

### Features

- 20+ log level functions (log_info, log_error, log_warning, etc.)
- Step-based logging (log_step_start, log_step_pass, log_step_fail)
- Color and emoji support with TTY detection
- GitLab CI section management
- Box drawing characters for TUI
- Key-value pair formatting

### Available Functions

```bash
# Basic logging
log_info "Informational message"
log_warning "Warning message"
log_error "Error message"
log_debug "Debug message"  # Only shown when DEBUG is set
log_notice "Notice message"
log_fatal "Fatal error"    # Exits script

# Step-based logging
log_start "Process name"
log_step_start "Step description"
log_step_pass "Success message"
log_step_fail "Failure message"
log_step_skip "Skipped message"
log_step_done "Completion message"
log_done "Process complete"

# Results
log_pass "Test passed"
log_fail "Test failed"
log_result "Result details"
log_success "Success message"

# CI sections
section_start "section_id" "Section Title"
section_end "section_id"
```

### Usage

```bash
#!/usr/bin/env bash
source /path/to/log_functions.sh

log_start "Deployment Process"

section_start "deps" "Installing Dependencies"
log_step_start "Installing packages"
if apt-get install -y package; then
    log_step_pass "Packages installed"
else
    log_step_fail "Package installation failed"
fi
section_end "deps"

log_done "Deployment complete"
```

## Additional Resources

### Scripts

- **[log_functions.sh](./scripts/log_functions.sh)** - Full shlocksmith logging library

### Color Reference

| Code         | Color        |
| ------------ | ------------ |
| `\033[0;30m` | Black        |
| `\033[0;31m` | Red          |
| `\033[0;32m` | Green        |
| `\033[0;33m` | Yellow       |
| `\033[0;34m` | Blue         |
| `\033[0;35m` | Magenta      |
| `\033[0;36m` | Cyan         |
| `\033[0;37m` | White        |
| `\033[1;XXm` | Bold variant |
| `\033[0m`    | Reset        |
