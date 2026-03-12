# Code Examples

## Portable Utility Functions

```bash
# Command existence check (POSIX)
command_exists() {
    command -v "${1}" >/dev/null 2>&1
}

# Portable dirname
get_dirname() {
    case "${1}" in
        */*) echo "${1%/*}" ;;
        *)   echo "." ;;
    esac
}

# Portable basename
get_basename() {
    case "${1}" in
        */*) echo "${1##*/}" ;;
        *)   echo "${1}" ;;
    esac
}

# Portable absolute path
get_abs_path() {
    (cd "$(dirname "${1}")" && printf '%s/%s' "$(pwd)" "$(basename "${1}")")
}
```
