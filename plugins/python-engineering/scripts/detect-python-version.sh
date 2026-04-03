#!/bin/bash
# Extract requires-python from pyproject.toml
set -euo pipefail

if [ ! -f pyproject.toml ]; then
    echo "unknown"
    exit 0
fi

version=$(grep -E 'requires-python' pyproject.toml 2>/dev/null | head -1 | sed 's/.*= *"//;s/".*//')

if [ -z "$version" ]; then
    echo "unknown"
else
    echo "$version"
fi
