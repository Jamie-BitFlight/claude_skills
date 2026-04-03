#!/bin/bash
# Validate plugin manifest and skill references.
set -euo pipefail

plugin_dir="${1:-$(dirname "$(dirname "$0")")}"
errors=0

# Check plugin.json exists and is valid
if [ ! -f "$plugin_dir/.claude-plugin/plugin.json" ]; then
    echo "FAIL: Missing .claude-plugin/plugin.json"
    exit 1
fi

if ! python3 -m json.tool "$plugin_dir/.claude-plugin/plugin.json" >/dev/null 2>&1; then
    echo "FAIL: Invalid JSON in plugin.json"
    exit 1
fi

# Check all skill directories have SKILL.md
for skill_dir in "$plugin_dir"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    if [ ! -f "$skill_dir/SKILL.md" ]; then
        echo "FAIL: Skill '$skill_name' missing SKILL.md"
        errors=$((errors + 1))
    fi
done

# Check all agent files exist
for agent_file in "$plugin_dir"/agents/*.md; do
    [ -f "$agent_file" ] || continue
    if ! head -5 "$agent_file" | grep -q '^---'; then
        echo "FAIL: Agent $(basename "$agent_file") missing YAML frontmatter"
        errors=$((errors + 1))
    fi
done

# Check no __pycache__ directories
if find "$plugin_dir" -name '__pycache__' -type d | grep -q .; then
    echo "FAIL: Found __pycache__ directories (should not ship)"
    errors=$((errors + 1))
fi

if [ $errors -eq 0 ]; then
    echo "PASS: Plugin manifest and layout valid"
else
    echo "FAIL: $errors issue(s) found"
    exit 1
fi
