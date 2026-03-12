# Code Examples

## Log Levels

Implement configurable log levels:

```bash
LOG_LEVEL="${LOG_LEVEL:-INFO}"

declare -A LOG_LEVELS=(
    [DEBUG]=0
    [INFO]=1
    [WARN]=2
    [ERROR]=3
    [FATAL]=4
)

log() {
    local level="${1}"
    shift
    local message="$*"

    local current_level="${LOG_LEVELS[$LOG_LEVEL]:-1}"
    local msg_level="${LOG_LEVELS[$level]:-1}"

    if [[ $msg_level -ge $current_level ]]; then
        printf '[%s] [%-5s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$message"
    fi
}

log_debug() { log DEBUG "$@"; }
log_info()  { log INFO "$@"; }
log_warn()  { log WARN "$@" >&2; }
log_error() { log ERROR "$@" >&2; }
log_fatal() { log FATAL "$@" >&2; exit 1; }
```

## GitHub Actions Grouping

```bash
group_start() {
    local name="${1}"
    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        printf '::group::%s\n' "$name"
    else
        printf '\n=== %s ===\n' "$name"
    fi
}

group_end() {
    if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        printf '::endgroup::\n'
    fi
}

# GitHub Actions annotations
gh_notice()  { printf '::notice::%s\n' "$*"; }
gh_warning() { printf '::warning::%s\n' "$*"; }
gh_error()   { printf '::error::%s\n' "$*"; }

# Usage
group_start "Running tests"
./run_tests.sh
group_end
```

## Progress Indicators

```bash
spinner() {
    local pid="${1}"
    local message="${2:-Processing}"
    local delay=0.1
    local spinchars='|/-\'

    while kill -0 "$pid" 2>/dev/null; do
        for char in $spinchars; do
            printf '\r%s %c' "$message" "$char"
            sleep $delay
        done
    done
    printf '\r%s done\n' "$message"
}

# Usage
long_running_task &
spinner $! "Installing dependencies"

# Progress bar
progress_bar() {
    local current="${1}"
    local total="${2}"
    local width="${3:-50}"

    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf '\r['
    printf '%*s' "$filled" '' | tr ' ' '#'
    printf '%*s' "$empty" '' | tr ' ' '-'
    printf '] %3d%%' "$percent"
}

# Usage
for i in {1..100}; do
    progress_bar "$i" 100
    sleep 0.05
done
printf '\n'
```

## Structured Step Logging

```bash
step_start() {
    local step_name="${1}"
    printf '%b %s... ' "▶" "$step_name"
}

step_pass() {
    printf '%b\n' "${COLOR_GREEN}✓${COLOR_RESET}"
}

step_fail() {
    printf '%b\n' "${COLOR_RED}✗${COLOR_RESET}"
}

step_skip() {
    printf '%b\n' "${COLOR_YELLOW}⊘ skipped${COLOR_RESET}"
}

# Usage
step_start "Checking dependencies"
if check_deps; then
    step_pass
else
    step_fail
fi
```
