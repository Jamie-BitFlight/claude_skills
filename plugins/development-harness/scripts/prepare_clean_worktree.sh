#!/usr/bin/env bash
set -euo pipefail

BRANCH_NAME="${1:-}"
if [ -z "$BRANCH_NAME" ]; then
    echo "error: usage: prepare_clean_worktree.sh <integration-branch>" >&2
    exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "error: uv is required but not found in PATH" >&2
    exit 2
fi

if [ -z "$(git status --porcelain)" ]; then
    exit 0
fi

printf "Stash uncommitted changes? [y/N] "
if ! read -r REPLY; then
    REPLY="N"
fi
if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
    echo "Aborting: working tree is dirty. Please stash or commit your changes, then re-run."
    exit 1
fi

git stash push -u -m "dh-auto-stash: pre-run ${BRANCH_NAME}" >/dev/null
STASH_REF="$(git rev-parse --verify 'stash@{0}')"

DH_STATE_HOME="${DH_STATE_HOME:-$HOME/.dh}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_SLUG="${REPO_ROOT//\//-}"
REPO_SLUG="${REPO_SLUG//\\/-}"
AUTO_STASH_FILE="${DH_STATE_HOME}/projects/${REPO_SLUG}/context/auto-stashes.json"
mkdir -p "$(dirname "${AUTO_STASH_FILE}")"

uv run python - "$AUTO_STASH_FILE" "$BRANCH_NAME" "$STASH_REF" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
branch = sys.argv[2]
stash_ref = sys.argv[3]

data: dict[str, str] = {}
if path.exists():
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        loaded = {}
    if isinstance(loaded, dict):
        data = {str(k): str(v) for k, v in loaded.items()}

data[branch] = stash_ref
path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "Auto-stash created: ${STASH_REF}"
