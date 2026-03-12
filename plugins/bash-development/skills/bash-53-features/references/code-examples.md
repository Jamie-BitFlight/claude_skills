# Code Examples

## check_service Function

```bash
check_service() {
    local service="${1}"
    local status

    ${| systemctl is-active "${service}" 2>/dev/null; }
    status="${REPLY}"

    if [[ "${status}" == "active" ]]; then
        echo "Service ${service} is running"
        return 0
    else
        echo "Service ${service} is not running"
        return 1
    fi
}

check_service "ssh"
```

## process_by_size Function

```bash
process_by_size() {
    local dir="${1}"

    GLOBSORT="-size"

    for file in "${dir}"/*; do
        [[ -f "${file}" ]] || continue

        size=$(stat -f%z "${file}" 2>/dev/null || stat -c%s "${file}" 2>/dev/null)
        printf 'Processing %s (%d bytes)\n' "${file}" "${size}"
        # Process file...
    done
}

process_by_size "/var/log"
```

## process_newest Function

```bash
process_newest() {
    local dir="${1}"
    local -a files

    GLOBSORT="-mtime"
    files=("${dir}"/*)

    echo "Processing files from newest to oldest:"
    for file in "${files[@]}"; do
        [[ -f "${file}" ]] || continue
        echo "  ${file}"
    done
}

process_newest "/tmp"
```

## get_available_commands Function

```bash
get_available_commands() {
    local prefix="${1}"
    local -a commands

    compgen -V commands -c "${prefix}"

    if [[ ${#commands[@]} -eq 0 ]]; then
        echo "No commands found starting with '${prefix}'"
        return 1
    fi

    printf 'Available commands (%d):\n' "${#commands[@]}"
    printf '  - %s\n' "${commands[@]}"
}

get_available_commands "git"
```

## load_library Function

```bash
load_library() {
    local lib_name="${1}"
    local -a search_paths=(
        "${HOME}/.local/lib"
        "/usr/local/lib"
        "/opt/lib"
    )

    local search_path
    search_path=$(IFS=:; echo "${search_paths[*]}")

    if source -p "${search_path}" "${lib_name}" 2>/dev/null; then
        echo "Loaded library: ${lib_name}"
        return 0
    else
        echo "Failed to load library: ${lib_name}" >&2
        return 1
    fi
}

load_library "common.sh"
```

## kv Builtin — load_env_config

```bash
load_env_config() {
    local config_file="${1}"
    declare -gA APP_CONFIG

    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "${key}" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${key}" ]] && continue

        # Trim whitespace
        key="${key#"${key%%[![:space:]]*}"}"
        value="${value#"${value%%[![:space:]]*}"}"

        APP_CONFIG["${key}"]="${value}"
    done < "${config_file}"
}
```

## strptime — parse_log_timestamp

```bash
parse_log_timestamp() {
    local log_line="${1}"
    local timestamp_str date_format timestamp

    # Extract timestamp from log line
    timestamp_str="${log_line%% *}"

    # Parse different date formats
    if [[ "${timestamp_str}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        date_format="%Y-%m-%d"
    elif [[ "${timestamp_str}" =~ ^[0-9]{2}/[0-9]{2}/[0-9]{4}$ ]]; then
        date_format="%m/%d/%Y"
    else
        echo "Unknown date format" >&2
        return 1
    fi

    timestamp=$(strptime "${date_format}" "${timestamp_str}")
    echo "${timestamp}"
}

parse_log_timestamp "2025-07-15 Application started"
```

## fltexpr — calculate_percentage

```bash
calculate_percentage() {
    local part="${1}"
    local total="${2}"
    local percentage

    percentage=$(fltexpr "(${part} / ${total}) * 100.0")
    printf '%.2f%%\n' "${percentage}"
}

calculate_percentage 75 200  # 37.50%
```

## validate_pattern Function

```bash
validate_pattern() {
    local pattern="${1}"
    local test_string="test"

    if [[ "${test_string}" =~ ${pattern} ]] 2>/dev/null; then
        echo "Pattern is valid"
        return 0
    else
        echo "Invalid regex pattern: ${pattern}" >&2
        return 1
    fi
}

validate_pattern "[a-z]+"  # Valid
validate_pattern "[a-z"    # Invalid
```
