---
name: bash-51-features
description: Bash 5.1 release features and improvements with practical examples. Use when working with Bash 5.1 features, epoch time variables, redirection enhancements, or when user asks about Bash 5.1 changes, new features, or version-specific capabilities.
---
# Bash 5.1 Features and Improvements

Released in December 2020, Bash 5.1 introduced several notable features and improvements for modern shell scripting.

## New Shell Variables

### EPOCHSECONDS and EPOCHREALTIME

Two new special variables for accessing current time:

```bash
# Get current Unix timestamp in seconds
echo "Current timestamp: ${EPOCHSECONDS}"

# Get current Unix timestamp with microsecond precision
echo "High precision timestamp: ${EPOCHREALTIME}"

# Practical example: Simple benchmarking
start="${EPOCHREALTIME}"
# ... some operation ...
sleep 0.5
end="${EPOCHREALTIME}"
duration=$(awk "BEGIN {print ${end} - ${start}}")
echo "Operation took ${duration} seconds"

# Example: Log with precise timestamps
log_message() {
    printf '[%s.%06d] %s\n' \
        "$(date -d "@${EPOCHSECONDS}" '+%Y-%m-%d %H:%M:%S')" \
        "${EPOCHREALTIME#*.}" \
        "$*"
}

log_message "Starting process"
```

**Use cases:**
- Precise performance measurement
- High-resolution timestamps for logging
- Avoiding external `date` command calls
- Microsecond-precision timing in scripts

### SRANDOM Variable

Cryptographically strong random numbers:

```bash
# Generate secure random number (if available)
if [[ -n "${SRANDOM}" ]]; then
    secure_random="${SRANDOM}"
    echo "Secure random: ${secure_random}"
else
    echo "SRANDOM not available (requires getrandom/getentropy)"
fi

# Practical example: Generate temporary file with secure random name
temp_file="/tmp/secure_${SRANDOM}_${EPOCHSECONDS}.tmp"
```

**Note:** `SRANDOM` requires system support for `getrandom()` or `getentropy()` syscalls.

## Improved Redirection Syntax

### `{varname}` Redirection

Assign file descriptor to variable for better file handle management:

```bash
# Open file descriptor and store in variable
exec {fd}< input.txt
while IFS= read -r -u "${fd}" line; do
    echo "Read: ${line}"
done
exec {fd}<&-  # Close the file descriptor

# Practical example: Multiple file handles
exec {input_fd}< data.txt
exec {output_fd}> results.txt
exec {error_fd}> errors.txt

process_data() {
    while IFS= read -r -u "${input_fd}" line; do
        if validate_line "${line}"; then
            echo "Processed: ${line}" >&"${output_fd}"
        else
            echo "Error: ${line}" >&"${error_fd}"
        fi
    done
}

process_data
exec {input_fd}<&-
exec {output_fd}>&-
exec {error_fd}>&-
```

**Benefits:**
- Named file descriptors instead of magic numbers
- Automatic FD allocation avoids conflicts
- More readable and maintainable code
- Easier tracking of open file handles

## Array Enhancements

### Improved Associative Array Handling

Better support for complex array operations:

```bash
# Declare associative array with typeset
declare -A config=(
    [host]="localhost"
    [port]="8080"
    [debug]="true"
)

# Enhanced array expansion
for key in "${!config[@]}"; do
    printf '%s=%s\n' "${key}" "${config[${key}]}"
done

# Practical example: Configuration parser
parse_config() {
    declare -gA app_config
    local line key value

    while IFS='=' read -r key value; do
        [[ "${key}" =~ ^[[:space:]]*# ]] && continue  # Skip comments
        [[ -z "${key}" ]] && continue                  # Skip empty lines

        # Trim whitespace
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"

        app_config["${key}"]="${value}"
    done < config.ini
}
```

### Multidimensional Array Support

Improved handling of nested array structures.

[Code examples](./references/code-examples.md#multidimensional-array-support)

## Readline 8.1 Integration

Enhanced text editing and command-line interaction:

### Key Bindings and History

```bash
# Configure readline in ~/.inputrc
# Enable case-insensitive completion
set completion-ignore-case on

# Enable visible stats for completions
set visible-stats on

# Show all completions immediately
set show-all-if-ambiguous on

# Use colors for completion matching
set colored-completion-prefix on
```

### Improved History Search

```bash
# In your script or .bashrc
# Bind Ctrl+R for reverse incremental search (default, but enhanced in 5.1)
bind '"\C-r": reverse-search-history'

# Bind Ctrl+S for forward incremental search
bind '"\C-s": forward-search-history'

# Improved history handling
shopt -s histappend           # Append to history
shopt -s cmdhist              # Multi-line commands as one entry
HISTCONTROL=ignoreboth        # Ignore duplicates and leading spaces
HISTSIZE=10000
HISTFILESIZE=20000
```

## Signal Handling Improvements

Better signal propagation in subshells and process substitutions:

```bash
# Enhanced trap handling in subshells
cleanup() {
    echo "Cleaning up..." >&2
    rm -f "${temp_file}"
    exit 130  # 128 + SIGINT
}

trap cleanup SIGINT SIGTERM

temp_file=$(mktemp)

# Signal properly propagates through pipelines
long_running_task | process_output &
pid=$!

# Wait for background job with proper signal handling
wait "${pid}" 2>/dev/null
exit_code=$?

if [[ ${exit_code} -gt 128 ]]; then
    signal=$((exit_code - 128))
    echo "Process terminated by signal ${signal}" >&2
fi
```

## Bug Fixes and Edge Cases

### Subshell Handling

Improved behavior when spawning subshells:

```bash
# More reliable subshell variable inheritance
outer_var="parent"

(
    # Subshell now more reliably inherits parent variables
    echo "In subshell: ${outer_var}"
    inner_var="child"
)

# outer_var still accessible, inner_var is not
echo "After subshell: ${outer_var}"
```

### Pattern Matching Edge Cases

Fixed edge cases in glob pattern matching:

```bash
# More reliable glob matching with special characters
shopt -s nullglob  # Empty expansion for non-matching globs
shopt -s extglob   # Extended pattern matching

# Example: Match files but handle no matches gracefully
files=(*.txt)
if [[ ${#files[@]} -eq 0 ]]; then
    echo "No .txt files found"
else
    printf 'Found: %s\n' "${files[@]}"
fi
```

## Performance Improvements

- Faster variable expansion in loops
- Optimized array operations
- Reduced memory usage for large arrays
- Improved efficiency in pattern matching

## Compatibility Notes

### Upgrading from Bash 5.0

Most scripts are compatible, but note:

- `EPOCHSECONDS` and `EPOCHREALTIME` are new - check for existence if targeting older versions
- `SRANDOM` may not be available on all systems
- Some obscure edge cases in expansion behavior were fixed

### Version Check

```bash
# Check Bash version before using 5.1 features
if [[ "${BASH_VERSINFO[0]}" -ge 5 ]] && [[ "${BASH_VERSINFO[1]}" -ge 1 ]]; then
    # Safe to use Bash 5.1 features
    timestamp="${EPOCHSECONDS}"
else
    # Fallback for older versions
    timestamp=$(date +%s)
fi
```

## References

- [Bash NEWS file](http://tiswww.case.edu/php/chet/bash/NEWS) - Official release notes
- [GNU Bash 5.1 Release](https://ftp.gnu.org/gnu/bash/bash-5.1.tar.gz) - Source distribution
- Bash man page: `man bash` (section on version-specific features)

## Additional Resources

For broader Bash development patterns and best practices, see:
- [../bash-development/SKILL.md](../bash-development/SKILL.md) - Core Bash development patterns
- [../bash-portability/SKILL.md](../bash-portability/SKILL.md) - Cross-version compatibility
