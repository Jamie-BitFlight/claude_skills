# Code Examples

## Error Handling

Trap-based error handling for robust scripts:

```bash
handle_error() {
    local line="${1}"
    local exit_code="${2:-1}"
    printf '%s\n' "Error on line ${line}" >&2
    exit "${exit_code}"
}

trap 'handle_error ${LINENO} $?' ERR

cleanup() {
    # Cleanup logic here
    rm -f "${TEMP_FILE:-}"
}

trap cleanup EXIT
```

## Argument Parsing

Standard argument parsing template:

```bash
usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS] <argument>

Options:
    -h, --help      Show this help message
    -v, --version   Show version information
    -d, --debug     Enable debug mode
    -f, --file      Specify input file

Examples:
    ${SCRIPT_NAME} file.txt
    ${SCRIPT_NAME} --debug file.txt
EOF
}

main() {
    local debug=0
    local input_file=""

    while [[ $# -gt 0 ]]; do
        case "${1}" in
            -h|--help) usage; exit 0 ;;
            -v|--version) printf '%s version %s\n' "${SCRIPT_NAME}" "${SCRIPT_VERSION}"; exit 0 ;;
            -d|--debug) debug=1; set -x; shift ;;
            -f|--file) input_file="${2}"; shift 2 ;;
            -*) printf 'Unknown option: %s\n' "${1}" >&2; usage; exit 1 ;;
            *) break ;;
        esac
    done

    # Validate required arguments
    if [[ $# -lt 1 ]]; then
        printf 'Missing required argument\n' >&2
        usage
        exit 1
    fi

    # Main logic here
}

main "$@"
```

## Utility Functions

```bash
# Check command existence
command_exists() {
    command -v "${1}" >/dev/null 2>&1
}

# Get script directory (resolves symlinks)
get_script_dir() {
    local source="${BASH_SOURCE[0]}"
    while [[ -L "${source}" ]]; do
        local dir=$(cd -P "$(dirname "${source}")" && pwd)
        source=$(readlink "${source}")
        [[ "${source}" != /* ]] && source="${dir}/${source}"
    done
    cd -P "$(dirname "${source}")" && pwd
}

# Conditional sudo
run_privileged() {
    if [[ "${EUID}" -eq 0 ]]; then
        "$@"
    elif command_exists sudo; then
        sudo "$@"
    else
        printf 'Error: root privileges required\n' >&2
        return 1
    fi
}
```
