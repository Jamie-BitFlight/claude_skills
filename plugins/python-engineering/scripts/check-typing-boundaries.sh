#!/bin/bash
# Check that Any/cast() usage is restricted to boundary modules.
set -euo pipefail

search_dir="${1:-.}"

any_files=$(grep -rl 'from typing import.*Any\|: Any\|-> Any\|cast(' --include='*.py' "$search_dir" 2>/dev/null || true)

if [ -z "$any_files" ]; then
    echo "PASS: No Any usage found"
    exit 0
fi

violations=""
while IFS= read -r file; do
    # Allow files in boundary/adapter/parser/validator directories
    if echo "$file" | grep -qE '(boundary|adapter|parser|validator|external|inbound)'; then
        continue
    fi
    # Allow files with approved naming
    basename=$(basename "$file")
    if echo "$basename" | grep -qE '(_boundary|_adapter|_parser|_validator|_external|_inbound)\.py$'; then
        continue
    fi
    violations="$violations$file
"
done <<<"$any_files"

if [ -n "$violations" ]; then
    echo "FAIL: Any/cast() found outside boundary modules:"
    echo "$violations"
    exit 1
fi

echo "PASS: Any usage restricted to boundary modules"
