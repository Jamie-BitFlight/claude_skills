# Code Examples

## Multidimensional Array Support

Improved handling of nested array structures:

```bash
# Simulate 2D array using associative arrays
declare -A matrix

set_cell() {
    local row="${1}" col="${2}" value="${3}"
    matrix["${row},${col}"]="${value}"
}

get_cell() {
    local row="${1}" col="${2}"
    echo "${matrix["${row},${col}"]}"
}

# Example usage
set_cell 0 0 "A"
set_cell 0 1 "B"
set_cell 1 0 "C"
set_cell 1 1 "D"

echo "Cell [0,1] = $(get_cell 0 1)"  # Outputs: B
```
