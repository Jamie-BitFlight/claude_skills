#!/usr/bin/env bash
# fetch-and-transform-hooks-docs.sh
#
# Fetches AI assistant hook documentation from official sources and transforms
# each into one existing AI-facing reference file with a focused prompt.
#
# Usage: bash plugins/plugin-creator/skills/hooks-guide/scripts/fetch-and-transform-hooks-docs.sh
#
# Does NOT use set -euo pipefail — graceful partial execution: one platform
# failure should not abort the others. Each platform is handled independently.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SKILL_DIR=$(dirname "$SCRIPT_DIR")

# ---------------------------------------------------------------------------
# Platform definitions
# Each entry: "name|url|output_reference_file_relative_to_SKILL_DIR"
# ---------------------------------------------------------------------------
PLATFORMS=(
    "claude-code|https://code.claude.com/docs/en/hooks.md|references/claude-code.md"
    "inline-agent|https://code.claude.com/docs/en/sub-agents.md|references/inline-agent-hooks.md"
    "github-copilot|https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/use-hooks.md|references/github-copilot.md"
    "cursor|https://docs.cursor.com/context/rules|references/cursor.md"
    "windsurf|https://docs.windsurf.com/windsurf/memories|references/windsurf.md"
    "amp|https://ampcode.com/docs|references/amp.md"
)

# ---------------------------------------------------------------------------
# Tracking: accumulate failure flags for final exit code
# ---------------------------------------------------------------------------
any_failed=0

TODAY=$(date +%Y-%m-%d)

# ---------------------------------------------------------------------------
# Process each platform
# ---------------------------------------------------------------------------
for entry in "${PLATFORMS[@]}"; do
    # Parse the pipe-delimited entry
    platform=$(echo "$entry" | cut -d'|' -f1)
    url=$(echo "$entry" | cut -d'|' -f2)
    ref_rel=$(echo "$entry" | cut -d'|' -f3)

    # Absolute path to the output reference file
    output_path="${SKILL_DIR}/${ref_rel}"

    # Temp file for the fetched content
    tmp_file="/tmp/hooks-fetch-${platform}.md"

    # --- Step a: Fetch the URL ---
    curl --silent --fail --max-time 30 --output "$tmp_file" "$url"
    curl_exit=$?

    # --- Step b: Check for curl failure or empty file ---
    if [ "$curl_exit" -ne 0 ] || [ ! -s "$tmp_file" ]; then
        echo "SKIP ${platform}: fetch failed (curl exit ${curl_exit})"
        any_failed=1
        continue
    fi

    # --- Step c: Check minimum content size (500 bytes) ---
    file_size=$(wc -c <"$tmp_file")
    if [ "$file_size" -lt 500 ]; then
        echo "SKIP ${platform}: response too small (likely no hooks content) — ${file_size} bytes"
        any_failed=1
        continue
    fi

    CLAUDECODE='' claude -p \
        "Convert the human-facing documentation in the file at ${tmp_file} into one AI-facing reference file at ${output_path}. Rules: remove UX prose, preserve all code examples verbatim, add ToC, use imperative headings, group by concept." \
        2>&1
    claude_exit=$?

    # --- Step e: Check for transform failure ---
    if [ "$claude_exit" -ne 0 ]; then
        echo "FAIL ${platform}: transform failed (claude exit ${claude_exit})"
        any_failed=1
        continue
    fi

    # --- Step f: Log success ---
    echo "OK ${platform}: wrote ${output_path}"

    # --- Update platform-coverage.md: set Last verified date for this platform ---
    # The table rows contain the platform name in the first column.
    # Match rows whose output file column matches the ref_rel basename.
    ref_basename=$(basename "$ref_rel")
    coverage_file="${SKILL_DIR}/references/platform-coverage.md"
    if [ -f "$coverage_file" ]; then
        # Replace the date in any row containing the reference file name.
        # Pattern: match the row, replace the last | separated field (the date) with today.
        sed -i "/${ref_basename}/s/| [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} *|$/| ${TODAY} |/" \
            "$coverage_file"
        sed -i "/${ref_basename}/s/| Pending first run *|$/| ${TODAY} |/" \
            "$coverage_file"
    fi
done

# ---------------------------------------------------------------------------
# Final exit code: 0 if all attempted platforms succeeded, 1 if any failed
# ---------------------------------------------------------------------------
exit "$any_failed"
