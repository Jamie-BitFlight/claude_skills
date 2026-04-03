#!/bin/bash
# Detect the active type checker for this project.
# Checks: .pre-commit-config.yaml → CI config → fallback to ty
set -euo pipefail

if [ -f .pre-commit-config.yaml ]; then
    if grep -q 'id: ty' .pre-commit-config.yaml 2>/dev/null; then
        echo "ty"
        exit 0
    fi
    if grep -q 'id: mypy' .pre-commit-config.yaml 2>/dev/null; then
        echo "mypy"
        exit 0
    fi
    if grep -q 'id: pyright\|id: basedpyright' .pre-commit-config.yaml 2>/dev/null; then
        echo "pyright"
        exit 0
    fi
fi

for ci_file in .github/workflows/*.yml .github/workflows/*.yaml .gitlab-ci.yml; do
    [ -f "$ci_file" ] || continue
    if grep -q 'uv run ty check\|uvx ty check' "$ci_file" 2>/dev/null; then
        echo "ty"
        exit 0
    fi
    if grep -q 'uv run mypy\|mypy' "$ci_file" 2>/dev/null; then
        echo "mypy"
        exit 0
    fi
done

# Fallback: ty for new work
echo "ty"
